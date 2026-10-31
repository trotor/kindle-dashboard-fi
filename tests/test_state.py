from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from saasahko.config import Config
from saasahko.prices import PriceSlot
from saasahko.state import build_state
from saasahko.store import Snapshot
from saasahko.weather import HourForecast

UTC = timezone.utc
HEL = ZoneInfo("Europe/Helsinki")
CFG = Config()


def day_slots(d, price=5.0, hours=range(24)):
    return [
        PriceSlot(datetime(d.year, d.month, d.day, h, q * 15, tzinfo=HEL).astimezone(UTC), price)
        for h in hours
        for q in range(4)
    ]


def hf(t):
    return HourForecast(time=t, temp=1.0, symbol=1, wind=2.0, feels_like=-1.0)


def snap(slots=(), hours=(), pf=None, wf=None, err=None):
    return Snapshot(list(slots), list(hours), pf, wf, err)


def test_state_midnight_rollover():
    sat, sun = date(2026, 11, 7), date(2026, 11, 8)
    slots = day_slots(sat, 3.0) + day_slots(sun, 7.0)
    now = datetime(2026, 11, 8, 0, 5, tzinfo=HEL).astimezone(UTC)
    st = build_state(snap(slots), CFG, now, None)
    assert st.prices_today == [7.0] * 24
    assert st.prices_tomorrow == [None] * 24
    assert st.now_local.date() == sun
    assert st.cheapest_tomorrow == set()


def test_state_tomorrow_missing_before_14():
    today = date(2026, 11, 8)
    now = datetime(2026, 11, 8, 12, 0, tzinfo=HEL).astimezone(UTC)
    st = build_state(snap(day_slots(today)), CFG, now, None)
    assert st.prices_tomorrow == [None] * 24
    assert st.cheapest_tomorrow == set()
    assert len(st.cheapest_today) == 3


def test_cheapest_requires_20_hours():
    today = date(2026, 11, 8)
    now = datetime(2026, 11, 8, 12, 0, tzinfo=HEL).astimezone(UTC)
    st = build_state(snap(day_slots(today, hours=range(19))), CFG, now, None)
    assert st.cheapest_today == set()
    st = build_state(snap(day_slots(today, hours=range(20))), CFG, now, None)
    assert len(st.cheapest_today) == 3


def test_state_extra_cost_applied():
    cfg = Config(margin_c=0.23, transfer_c=5.0)
    today = date(2026, 11, 8)
    now = datetime(2026, 11, 8, 12, 0, tzinfo=HEL).astimezone(UTC)
    st = build_state(snap(day_slots(today, 4.0)), cfg, now, None)
    assert abs(st.price_now - 9.23) < 1e-9
    assert abs(st.prices_today[3] - 9.23) < 1e-9


def test_state_forecast_fields():
    now = datetime(2026, 11, 8, 12, 0, tzinfo=HEL).astimezone(UTC)
    hours = [hf(now + timedelta(hours=i)) for i in range(0, 80)]
    st = build_state(snap(day_slots(date(2026, 11, 8)), hours, now, now), CFG, now, 50)
    assert st.current == hours[0] and st.current_desc == "selkeää"
    assert len(st.next_hours) == 6 and st.next_hours[0] == hours[1]
    assert len(st.days) == 3 and st.place == "TOIVALA"
    assert st.battery == 50


def test_state_no_forecast():
    now = datetime(2026, 11, 8, 12, 0, tzinfo=HEL).astimezone(UTC)
    st = build_state(snap(day_slots(date(2026, 11, 8))), CFG, now, None)
    assert st.current is None and st.current_desc == "" and st.next_hours == []


def test_state_note_priorities():
    now = datetime(2026, 11, 8, 12, 0, tzinfo=HEL).astimezone(UTC)
    slots = day_slots(date(2026, 11, 8))
    # 1. no prices wins over everything
    assert build_state(snap(), CFG, now, None).note == "ei hintatietoja"
    # 2. stale weather
    old = now - timedelta(hours=3)  # 09.00 local
    assert build_state(snap(slots, wf=old), CFG, now, None).note == "sää päivitetty 9.00"
    assert build_state(snap(slots), CFG, now, None).note == "ei säätietoja"
    # 3. fresh
    fresh = now - timedelta(hours=1)
    assert build_state(snap(slots, wf=fresh), CFG, now, None).note is None
    # exactly 2 h is not "over" 2 h
    assert build_state(snap(slots, wf=now - timedelta(hours=2)), CFG, now, None).note is None


def test_low_battery_flag():
    now = datetime(2026, 11, 8, 12, 0, tzinfo=HEL).astimezone(UTC)
    s = snap(day_slots(date(2026, 11, 8)))
    assert build_state(s, CFG, now, 15).low_battery is True
    assert build_state(s, CFG, now, 20).low_battery is False
    assert build_state(s, CFG, now, None).low_battery is False
