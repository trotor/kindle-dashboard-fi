import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from saasahko.config import Config
from saasahko.store import DataStore

UTC = timezone.utc
HEL = ZoneInfo("Europe/Helsinki")
FMI = (Path(__file__).parent / "fixtures" / "fmi_toivala.xml").read_text()


def prices_json(*days):
    """Raw porssisahko payload with 4 quarter-hour slots per local date in `days`."""
    items = []
    for d in days:
        for h in range(24):
            for q in range(4):
                t = datetime(d.year, d.month, d.day, h, q * 15, tzinfo=HEL).astimezone(UTC)
                items.append(
                    {
                        "startDate": t.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                        "endDate": (t + timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                        "price": 5.0,
                    }
                )
    return {"prices": items}


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


class Fakes:
    def __init__(self, prices, weather=FMI):
        self.prices, self.weather = prices, weather
        self.p_calls = self.w_calls = 0
        self.fail_prices = self.fail_weather = False
        self.urls = []

    def fetch_prices(self):
        self.p_calls += 1
        if self.fail_prices:
            raise OSError("boom")
        return self.prices

    def fetch_weather(self, url):
        self.w_calls += 1
        self.urls.append(url)
        if self.fail_weather:
            raise OSError("fmi down")
        return self.weather


def make(tmp_path, now, prices=None, **kw):
    clock = Clock(now)
    f = Fakes(prices if prices is not None else prices_json(now.astimezone(HEL).date()))
    cfg = Config(cache_dir=tmp_path / "cache")
    return DataStore(cfg, f.fetch_prices, f.fetch_weather, clock), f, clock


T = datetime(2026, 11, 1, 10, 0, tzinfo=UTC)  # 12.00 local


def test_first_refresh_fetches_both_and_persists(tmp_path):
    s, f, _ = make(tmp_path, T)
    s.refresh()
    snap = s.snapshot()
    assert (f.p_calls, f.w_calls) == (1, 1)
    assert snap.slots and snap.hours
    assert snap.prices_fetched_at == T and snap.weather_fetched_at == T
    assert snap.last_error is None
    cache = tmp_path / "cache"
    assert json.loads((cache / "prices.json").read_text()) == f.prices
    assert (cache / "weather.xml").read_text() == FMI
    assert "meta.json" in {p.name for p in cache.iterdir()}
    assert "latlon=62.9876,27.7216" in f.urls[0]


def test_weather_not_refetched_within_30min(tmp_path):
    s, f, c = make(tmp_path, T)
    s.refresh()
    c.t = T + timedelta(minutes=29)
    s.refresh()
    assert f.w_calls == 1
    c.t = T + timedelta(minutes=31)
    s.refresh()
    assert f.w_calls == 2


def test_prices_polled_every_15min_in_afternoon_until_tomorrow_present(tmp_path):
    t0 = datetime(2026, 11, 1, 11, 0, tzinfo=UTC)  # 13.00 local
    s, f, c = make(tmp_path, t0)
    s.refresh()  # initial fetch, today only
    assert f.p_calls == 1
    c.t = t0 + timedelta(minutes=10)  # 13.10
    s.refresh()
    assert f.p_calls == 1
    c.t = t0 + timedelta(minutes=16)  # 13.16
    s.refresh()
    assert f.p_calls == 2
    c.t = t0 + timedelta(minutes=26)  # 13.26
    s.refresh()
    assert f.p_calls == 2
    c.t = t0 + timedelta(minutes=32)  # 13.32
    f.prices = prices_json(datetime(2026, 11, 1).date(), datetime(2026, 11, 2).date())
    s.refresh()
    assert f.p_calls == 3
    c.t = t0 + timedelta(minutes=120)  # tomorrow present now -> no more polling
    s.refresh()
    assert f.p_calls == 3
    c.t = t0 + timedelta(hours=6, minutes=40)  # > 6 h since fetch
    s.refresh()
    assert f.p_calls == 4


def test_no_afternoon_polling_outside_window(tmp_path):
    t0 = datetime(2026, 11, 1, 6, 0, tzinfo=UTC)  # 08.00 local
    s, f, c = make(tmp_path, t0)
    s.refresh()
    c.t = t0 + timedelta(hours=2)  # 10.00 local, still no tomorrow
    s.refresh()
    assert f.p_calls == 1


def test_failure_keeps_old_data_and_sets_error(tmp_path):
    s, f, c = make(tmp_path, T)
    s.refresh()
    before = s.snapshot()
    f.fail_prices = f.fail_weather = True
    c.t = T + timedelta(hours=7)
    s.refresh()
    after = s.snapshot()
    assert after.slots == before.slots and after.hours == before.hours
    assert after.prices_fetched_at == T and after.weather_fetched_at == T
    assert after.last_error and ("hinnat" in after.last_error or "sää" in after.last_error)
    assert "boom" in after.last_error or "fmi down" in after.last_error


def test_failure_error_format_and_clear(tmp_path):
    s, f, c = make(tmp_path, T)
    f.fail_prices = True
    s.refresh()
    assert s.snapshot().last_error == "hinnat: boom"
    f.fail_prices = False
    c.t = T + timedelta(minutes=6)
    s.refresh()
    assert s.snapshot().last_error is None


def test_failure_backoff_5min(tmp_path):
    s, f, c = make(tmp_path, T)
    f.fail_prices = True
    s.refresh()
    assert f.p_calls == 1
    c.t = T + timedelta(minutes=4)
    s.refresh()
    assert f.p_calls == 1
    c.t = T + timedelta(minutes=5, seconds=1)
    s.refresh()
    assert f.p_calls == 2


def test_malformed_or_empty_data_counts_as_failure(tmp_path):
    s, f, _ = make(tmp_path, T, prices={"prices": [{"startDate": "x"}]})
    f.weather = "<empty/>"
    s.refresh()
    snap = s.snapshot()
    assert snap.slots == [] and snap.hours == []
    assert snap.prices_fetched_at is None and snap.weather_fetched_at is None
    assert snap.last_error
    assert not (tmp_path / "cache" / "prices.json").exists()


def test_loads_cache_on_init(tmp_path):
    s, f, c = make(tmp_path, T)
    s.refresh()
    cfg = Config(cache_dir=tmp_path / "cache")
    f2 = Fakes(prices_json())
    s2 = DataStore(cfg, f2.fetch_prices, f2.fetch_weather, Clock(T + timedelta(minutes=1)))
    snap = s2.snapshot()
    assert snap.slots and snap.hours
    assert snap.prices_fetched_at == T and snap.weather_fetched_at == T
    s2.refresh()
    assert (f2.p_calls, f2.w_calls) == (0, 0)


def test_corrupt_cache_ignored(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "prices.json").write_text("not json")
    (cache / "meta.json").write_text("{")
    s, f, _ = make(tmp_path, T)
    assert s.snapshot().slots == []
    s.refresh()
    assert f.p_calls == 1
