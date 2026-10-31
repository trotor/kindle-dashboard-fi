"""HTTP server and background refresher."""
from __future__ import annotations

import io
import json
import logging
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from saasahko.config import Config
from saasahko.render import render
from saasahko.state import build_state
from saasahko.store import DataStore

log = logging.getLogger("saasahko")
UTC = timezone.utc
REQUEST_TIMEOUT_S = 30
# C0 and C1 control characters -> \xNN, so a request can't forge log lines
_CONTROL_ESCAPES = str.maketrans(
    {c: f"\\x{c:02x}" for c in (*range(0x20), *range(0x7F, 0xA0))}
)


def _parse_battery(query: str) -> int | None:
    try:
        value = int(parse_qs(query).get("batt", [""])[0])
    except ValueError:
        return None
    return value if 0 <= value <= 100 else None


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def make_server(
    cfg: Config, store: DataStore, host: str = "0.0.0.0", port: int | None = None
) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        timeout = REQUEST_TIMEOUT_S

        def _send(self, status: int, ctype: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            url = urlsplit(self.path)
            try:
                if url.path == "/kindle.png":
                    state = build_state(
                        store.snapshot(), cfg, datetime.now(UTC), _parse_battery(url.query)
                    )
                    buf = io.BytesIO()
                    render(state).save(buf, "PNG")
                    self._send(200, "image/png", buf.getvalue())
                elif url.path == "/health":
                    snap = store.snapshot()
                    body = {
                        "weather_fetched_at": _iso(snap.weather_fetched_at),
                        "prices_fetched_at": _iso(snap.prices_fetched_at),
                        "last_error": snap.last_error,
                    }
                    self._send(200, "application/json", json.dumps(body).encode())
                else:
                    self._send(404, "text/plain; charset=utf-8", b"not found")
            except Exception:
                log.exception("request failed: %s", self.path.translate(_CONTROL_ESCAPES))
                self._send(500, "text/plain; charset=utf-8", b"internal error")

        def log_message(self, format: str, *args) -> None:
            log.info("%s %s", self.address_string(), (format % args).translate(_CONTROL_ESCAPES))

    return ThreadingHTTPServer((host, cfg.port if port is None else port), Handler)


def start_refresher(store: DataStore, interval_s: float = 300) -> threading.Thread:
    def loop() -> None:
        while True:
            try:
                store.refresh()
            except Exception:
                log.exception("refresh failed")
            time.sleep(interval_s)

    t = threading.Thread(target=loop, name="refresher", daemon=True)
    t.start()
    return t
