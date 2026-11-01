"""Data store: fetch scheduling, on-disk cache and failure fallback."""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from saasahko.config import Config
from saasahko.prices import PUBLISHED_FROM_HOUR, PriceSlot, fetch_porssisahko, parse_porssisahko
from saasahko.weather import HourForecast, build_fmi_url, fetch_fmi, parse_fmi

log = logging.getLogger("saasahko")
UTC = timezone.utc
WEATHER_MAX_AGE = timedelta(minutes=30)
PRICES_MAX_AGE = timedelta(hours=6)
AFTERNOON_POLL = timedelta(minutes=15)
BACKOFF = timedelta(minutes=5)

PRICES = "hinnat"
WEATHER = "sää"


@dataclass
class Snapshot:
    slots: list[PriceSlot]
    hours: list[HourForecast]
    prices_fetched_at: datetime | None
    weather_fetched_at: datetime | None
    last_error: str | None


@dataclass
class _Source:
    fetched_at: datetime | None = None
    failed_at: datetime | None = None
    error: str | None = None


class DataStore:
    def __init__(
        self,
        cfg: Config,
        fetch_prices=fetch_porssisahko,
        fetch_weather=fetch_fmi,
        clock=lambda: datetime.now(UTC),
    ):
        self._cfg = cfg
        self._tz = ZoneInfo(cfg.timezone)
        self._fetch_prices = fetch_prices
        self._fetch_weather = fetch_weather
        self._clock = clock
        self._lock = threading.Lock()
        self._slots: list[PriceSlot] = []
        self._hours: list[HourForecast] = []
        self._src = {PRICES: _Source(), WEATHER: _Source()}
        self._load_cache()

    # --- cache -----------------------------------------------------------
    def _load_cache(self) -> None:
        d = self._cfg.cache_dir
        try:
            meta = json.loads((d / "meta.json").read_text())
        except (OSError, ValueError):
            return
        try:
            slots = parse_porssisahko(json.loads((d / "prices.json").read_text()))
            at = datetime.fromisoformat(meta["prices_fetched_at"])
        except Exception:
            pass
        else:
            if slots:
                self._slots, self._src[PRICES].fetched_at = slots, at
        try:
            hours = parse_fmi((d / "weather.xml").read_text())
            at = datetime.fromisoformat(meta["weather_fetched_at"])
        except Exception:
            pass
        else:
            if hours:
                self._hours, self._src[WEATHER].fetched_at = hours, at

    def _save_cache(self, name: str, raw: str) -> None:
        d = self._cfg.cache_dir
        try:
            d.mkdir(parents=True, exist_ok=True)
            (d / name).write_text(raw)
            meta = {
                "prices_fetched_at": _iso(self._src[PRICES].fetched_at),
                "weather_fetched_at": _iso(self._src[WEATHER].fetched_at),
            }
            (d / "meta.json").write_text(json.dumps(meta))
        except OSError:
            pass  # cache is best effort

    # --- scheduling ------------------------------------------------------
    def _backing_off(self, src: _Source, now: datetime) -> bool:
        return src.failed_at is not None and now - src.failed_at < BACKOFF

    def _tomorrow_present(self, now: datetime) -> bool:
        tomorrow = now.astimezone(self._tz).date() + timedelta(days=1)
        return any(
            (loc := s.start.astimezone(self._tz)).date() == tomorrow and loc.hour >= PUBLISHED_FROM_HOUR
            for s in self._slots
        )

    def _weather_due(self, now: datetime) -> bool:
        src = self._src[WEATHER]
        if self._backing_off(src, now):
            return False
        return src.fetched_at is None or now - src.fetched_at > WEATHER_MAX_AGE

    def _prices_due(self, now: datetime) -> bool:
        src = self._src[PRICES]
        if self._backing_off(src, now):
            return False
        if src.fetched_at is None or now - src.fetched_at > PRICES_MAX_AGE:
            return True
        local = now.astimezone(self._tz)
        return (
            13 <= local.hour < 18
            and not self._tomorrow_present(now)
            and now - src.fetched_at > AFTERNOON_POLL
        )

    # --- fetching --------------------------------------------------------
    def refresh(self) -> None:
        now = self._clock()
        with self._lock:
            weather_due = self._weather_due(now)
            prices_due = self._prices_due(now)
        if weather_due:
            self._refresh_weather(now)
        if prices_due:
            self._refresh_prices(now)

    def _refresh_weather(self, now: datetime) -> None:
        start = now.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
        url = build_fmi_url(self._cfg.lat, self._cfg.lon, start, hours=100)
        try:
            raw = self._fetch_weather(url)
            hours = parse_fmi(raw)
            if not hours:
                raise ValueError("tyhjä ennuste")
        except Exception as e:  # never let a fetch problem escape
            self._fail(WEATHER, now, e)
            return
        with self._lock:
            self._hours = hours
            self._succeed(WEATHER, now)
            self._save_cache("weather.xml", raw)

    def _refresh_prices(self, now: datetime) -> None:
        try:
            raw = self._fetch_prices()
            slots = parse_porssisahko(raw)
            if not slots:
                raise ValueError("tyhjä hintalista")
        except Exception as e:
            self._fail(PRICES, now, e)
            return
        with self._lock:
            self._slots = slots
            self._succeed(PRICES, now)
            self._save_cache("prices.json", json.dumps(raw))

    def _fail(self, name: str, now: datetime, err: Exception) -> None:
        msg = f"{name}: {err}"
        log.warning("fetch failed: %s", msg)
        with self._lock:
            src = self._src[name]
            src.failed_at, src.error = now, msg

    def _succeed(self, name: str, now: datetime) -> None:
        src = self._src[name]
        src.fetched_at, src.failed_at, src.error = now, None, None

    def snapshot(self) -> Snapshot:
        with self._lock:
            errors = [(s.failed_at, s.error) for s in self._src.values() if s.error]
            err = max(errors)[1] if errors else None
            return Snapshot(
                slots=list(self._slots),
                hours=list(self._hours),
                prices_fetched_at=self._src[PRICES].fetched_at,
                weather_fetched_at=self._src[WEATHER].fetched_at,
                last_error=err,
            )


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None
