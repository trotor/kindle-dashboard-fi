"""Dashboard state: everything the renderer needs, derived from a Snapshot."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from saasahko.config import Config
from saasahko.fmt import fmt_clock, fmt_date
from saasahko.prices import cheapest_hours, hourly_prices, price_at
from saasahko.store import PRICES, Snapshot
from saasahko.symbols import describe
from saasahko.weather import DaySummary, HourForecast, current, daily_summaries, next_hours

MIN_HOURS_FOR_CHEAPEST = 20
WEATHER_STALE = timedelta(hours=2)
PRICES_STALE = timedelta(hours=7)
TOMORROW_EXPECTED_HOUR = 15


@dataclass
class DashboardState:
    now_local: datetime
    place: str
    current: HourForecast | None
    current_desc: str
    next_hours: list[HourForecast]
    days: list[DaySummary]
    prices_today: list[float | None]
    prices_tomorrow: list[float | None]
    cheapest_today: set[int]
    cheapest_tomorrow: set[int]
    price_now: float | None
    battery: int | None
    low_battery: bool
    note: str | None


def _cheapest(hourly: list[float | None], first_hour: int = 0) -> set[int]:
    """Cheapest hours among those >= first_hour (indices kept); needs data for most of the day."""
    if sum(p is not None for p in hourly) < MIN_HOURS_FOR_CHEAPEST:
        return set()
    remaining = [p if h >= first_hour else None for h, p in enumerate(hourly)]
    return cheapest_hours(remaining)


def _updated(what: str, at: datetime, tz: ZoneInfo, today: date) -> str:
    """'<what> päivitetty 14.05', with the date ('31.10. 14.05') when not today."""
    local = at.astimezone(tz)
    when = fmt_clock(local) if local.date() == today else f"{fmt_date(local)} {fmt_clock(local)}"
    return f"{what} päivitetty {when}"


def _prices_outdated(snap: Snapshot, now: datetime, local: datetime, tomorrow_missing: bool) -> bool:
    """Prices are old, or tomorrow's prices should be out but fetching them fails."""
    if snap.prices_fetched_at is None:
        return False
    if now - snap.prices_fetched_at > PRICES_STALE:
        return True
    return (
        local.hour >= TOMORROW_EXPECTED_HOUR
        and tomorrow_missing
        and (snap.last_error or "").startswith(f"{PRICES}:")
    )


def build_state(snap: Snapshot, cfg: Config, now: datetime, battery: int | None) -> DashboardState:
    tz = ZoneInfo(cfg.timezone)
    local = now.astimezone(tz)
    today = local.date()
    extra = cfg.margin_c + cfg.transfer_c
    prices_today = hourly_prices(snap.slots, today, tz, extra)
    prices_tomorrow = hourly_prices(snap.slots, today + timedelta(days=1), tz, extra)
    cur = current(snap.hours, now)

    if all(p is None for p in prices_today):
        note = "ei hintatietoja"
    elif _prices_outdated(snap, now, local, all(p is None for p in prices_tomorrow)):
        note = _updated("hinnat", snap.prices_fetched_at, tz, today)
    elif snap.weather_fetched_at is None:
        note = "ei säätietoja"
    elif now - snap.weather_fetched_at > WEATHER_STALE:
        note = _updated("sää", snap.weather_fetched_at, tz, today)
    else:
        note = None

    return DashboardState(
        now_local=local,
        place=cfg.place_name,
        current=cur,
        current_desc=describe(cur.symbol) if cur else "",
        next_hours=next_hours(snap.hours, now),
        days=daily_summaries(snap.hours, tz, today),
        prices_today=prices_today,
        prices_tomorrow=prices_tomorrow,
        cheapest_today=_cheapest(prices_today, first_hour=local.hour),
        cheapest_tomorrow=_cheapest(prices_tomorrow),
        price_now=price_at(snap.slots, now, extra),
        battery=battery,
        low_battery=battery is not None and battery < cfg.low_battery_percent,
        note=note,
    )
