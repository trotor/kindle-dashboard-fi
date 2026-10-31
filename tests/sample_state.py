"""Mockup B data: la 31.10.2026 klo 14.30, +4°, pilvistä, invented 48 h prices."""
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from saasahko.prices import cheapest_hours
from saasahko.state import DashboardState
from saasahko.weather import DaySummary, HourForecast

HEL = ZoneInfo("Europe/Helsinki")
NOW = datetime(2026, 10, 31, 14, 30, tzinfo=HEL)

PRICES_TODAY = [
    2.1, 1.9, 1.7, 1.6, 1.8, 2.4, 4.8, 9.2, 11.5, 8.7, 7.1, 6.3,
    5.9, 5.6, 6.4, 7.0, 8.9, 12.8, 13.6, 10.4, 7.2, 4.9, 3.1, 2.0,
]
# Tomorrow 03-04 is negative (windy night).
PRICES_TOMORROW = [
    1.8, 1.5, 1.3, -1.2, 1.2, 1.4, 3.9, 10.8, 14.9, 9.6, 6.8, 5.2,
    4.1, 4.0, 4.6, 5.8, 8.1, 11.9, 12.4, 9.0, 6.1, 3.8, 2.6, 2.2,
]

# (hours after 14.00 local, temp, symbol)
_NEXT = [(1, 4.0, 3), (2, 3.6, 3), (3, 3.2, 3), (4, 2.9, 3), (5, 2.4, 1), (6, 1.8, 1)]


def _hour(k: int, temp: float, symbol: int) -> HourForecast:
    t = (NOW.replace(minute=0) + timedelta(hours=k)).astimezone(timezone.utc)
    return HourForecast(time=t, temp=temp, symbol=symbol, wind=3.6, feels_like=temp - 3.0)


def sample_state(**overrides) -> DashboardState:
    state = DashboardState(
        now_local=NOW,
        place="TOIVALA",
        current=_hour(0, 4.2, 3),
        current_desc="pilvistä",
        next_hours=[_hour(k, t, s) for k, t, s in _NEXT],
        days=[
            DaySummary(day=date(2026, 11, 1), tmin=0.0, tmax=5.0, symbol=31),
            DaySummary(day=date(2026, 11, 2), tmin=-4.0, tmax=3.0, symbol=1),
            DaySummary(day=date(2026, 11, 3), tmin=-6.0, tmax=1.0, symbol=51),
        ],
        prices_today=list(PRICES_TODAY),
        prices_tomorrow=list(PRICES_TOMORROW),
        cheapest_today=cheapest_hours(PRICES_TODAY),
        cheapest_tomorrow=cheapest_hours(PRICES_TOMORROW),
        price_now=6.4,
        battery=80,
        low_battery=False,
        note=None,
    )
    return replace(state, **overrides)
