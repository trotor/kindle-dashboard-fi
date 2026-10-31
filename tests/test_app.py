import io
import json
import logging
import socket
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

import pytest
from PIL import Image

from saasahko.app import make_server, start_refresher
from saasahko.config import Config
from saasahko.store import DataStore
from tests.test_store import FMI, Fakes, prices_json

UTC = timezone.utc


@pytest.fixture
def served(tmp_path):
    cfg = Config(cache_dir=tmp_path / "cache")
    today = datetime.now(UTC).date()
    fakes = Fakes(prices_json(today))
    store = DataStore(cfg, fetch_prices=fakes.fetch_prices, fetch_weather=fakes.fetch_weather)
    store.refresh()
    server = make_server(cfg, store, host="127.0.0.1", port=0)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield server, fakes, store
    server.shutdown()
    server.server_close()


def get(server, path):
    url = f"http://127.0.0.1:{server.server_address[1]}{path}"
    try:
        return urllib.request.urlopen(url, timeout=10)
    except urllib.error.HTTPError as e:
        return e


def test_png_endpoint(served):
    server, fakes, _ = served
    r = get(server, "/kindle.png?batt=55")
    assert r.status == 200
    assert r.headers["Content-Type"] == "image/png"
    assert r.headers["Cache-Control"] == "no-store"
    img = Image.open(io.BytesIO(r.read()))
    assert img.size == (1072, 1448)
    assert img.mode == "L"


def test_png_does_not_fetch(served):
    server, fakes, _ = served
    before = (fakes.p_calls, fakes.w_calls)
    get(server, "/kindle.png").read()
    assert (fakes.p_calls, fakes.w_calls) == before


def test_bad_batt_ignored(served):
    server, _, _ = served
    assert get(server, "/kindle.png?batt=abc").status == 200


def test_health_ok(served):
    server, _, _ = served
    r = get(server, "/health")
    assert r.status == 200
    assert r.headers["Content-Type"] == "application/json"
    body = json.loads(r.read())
    assert body["last_error"] is None
    datetime.fromisoformat(body["weather_fetched_at"])
    datetime.fromisoformat(body["prices_fetched_at"])


def test_health_reports_error(tmp_path):
    cfg = Config(cache_dir=tmp_path / "cache")
    fakes = Fakes(prices_json())
    fakes.fail_prices = True
    store = DataStore(cfg, fetch_prices=fakes.fetch_prices, fetch_weather=fakes.fetch_weather)
    store.refresh()
    server = make_server(cfg, store, host="127.0.0.1", port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        body = json.loads(get(server, "/health").read())
    finally:
        server.shutdown()
        server.server_close()
    assert body["last_error"].startswith("hinnat:")
    assert body["prices_fetched_at"] is None


def test_404(served):
    server, _, _ = served
    assert get(server, "/x").status == 404


def test_refresher_survives_exception():
    class Flaky:
        calls = 0

        def refresh(self):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("boom")

    store = Flaky()
    t = start_refresher(store, interval_s=0.01)
    deadline = time.time() + 5
    while store.calls < 3 and time.time() < deadline:
        time.sleep(0.01)
    assert store.calls >= 3
    assert t.is_alive() and t.daemon


def test_handler_has_timeout(served):
    server, _, _ = served
    assert server.RequestHandlerClass.timeout == 30


def test_request_log_escapes_control_characters(served, caplog):
    server, _, _ = served
    with caplog.at_level(logging.INFO, logger="saasahko"):
        with socket.create_connection(server.server_address, timeout=10) as s:
            s.sendall(b"GET /a\x1b[2Jb\x7f HTTP/1.0\r\n\r\n")
            assert s.recv(100).startswith(b"HTTP/1.0 404")
    lines = [r.getMessage() for r in caplog.records if "GET /a" in r.getMessage()]
    assert lines
    assert all("\x1b" not in m and "\x7f" not in m for m in lines)
    assert any("\\x1b[2Jb\\x7f" in m for m in lines)
