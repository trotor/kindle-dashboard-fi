from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from saasahko.weather import (
    HourForecast,
    build_fmi_url,
    current,
    daily_summaries,
    next_hours,
    parse_fmi,
)

HEL = ZoneInfo("Europe/Helsinki")
UTC = timezone.utc
FIX = (Path(__file__).parent / "fixtures" / "fmi_toivala.xml").read_text()
NAN_TIME = datetime(2026, 11, 1, 6, 0, tzinfo=UTC)  # Temperature hand-edited to NaN
T0 = datetime(2026, 11, 1, 0, 0, tzinfo=UTC)


def hf(t, temp=1.0, symbol=1):
    return HourForecast(time=t, temp=temp, symbol=symbol, wind=2.0, feels_like=temp - 2)


H = [hf(T0 + timedelta(hours=i)) for i in range(10)]


def test_parse_fixture():
    hours = parse_fmi(FIX)
    assert len(hours) > 60 and all(h.time.tzinfo for h in hours)
    assert [h.time for h in hours] == sorted(h.time for h in hours)
    first = hours[0]
    assert first.time == datetime(2026, 10, 31, 22, 0, tzinfo=UTC)
    assert first.temp == 4.69 and isinstance(first.symbol, int)


def test_nan_hour_skipped():
    assert NAN_TIME not in [h.time for h in parse_fmi(FIX)]


def test_url_uses_latlon():
    u = build_fmi_url(62.9876, 27.7216, T0)
    assert "latlon=62.9876,27.7216" in u and "place=" not in u
    assert "fmi::forecast::edited::weather::scandinavia::point::simple" in u
    assert "parameters=Temperature,WeatherSymbol3,WindSpeedMS,FeelsLike" in u
    assert "timestep=60" in u
    assert "starttime=2026-11-01T00:00:00Z" in u
    assert "endtime=2026-11-05T04:00:00Z" in u


def test_current_nearest_and_none_when_far():
    assert current(H, T0 + timedelta(minutes=20)).time == T0
    assert current(H, T0 + timedelta(minutes=40)).time == T0 + timedelta(hours=1)
    assert current(H, T0 - timedelta(minutes=60)).time == T0
    assert current(H, T0 - timedelta(minutes=91)) is None
    assert current(H, H[-1].time + timedelta(hours=3)) is None
    assert current([], T0) is None


def test_next_hours_strictly_after_now():
    assert [h.time for h in next_hours(H, T0 + timedelta(minutes=30))][0] == T0 + timedelta(hours=1)
    assert next_hours(H, T0 + timedelta(hours=1))[0].time == T0 + timedelta(hours=2)
    assert len(next_hours(H, T0, n=3)) == 3


def _local_day_hours(day, symbol_at_noon=7):
    out = []
    for i in range(24):
        t = datetime(day.year, day.month, day.day, i, tzinfo=HEL).astimezone(UTC)
        out.append(hf(t, temp=i - 10, symbol=symbol_at_noon if i == 12 else 1))
    return out


def test_daily_summary_minmax_local_day():
    hours = _local_day_hours(date(2026, 11, 1))
    res = daily_summaries(hours, HEL, today=date(2026, 10, 31))
    assert len(res) == 1
    d = res[0]
    assert d.day == date(2026, 11, 1) and d.tmin == -10 and d.tmax == 13 and d.symbol == 7


def test_daily_summary_skips_empty_days():
    hours = _local_day_hours(date(2026, 11, 2))
    res = daily_summaries(hours, HEL, today=date(2026, 10, 31))
    assert [d.day for d in res] == [date(2026, 11, 2)]


def test_daily_summary_symbol_nearest_noon_and_excludes_today():
    hours = [hf(datetime(2026, 11, 1, h, tzinfo=HEL).astimezone(UTC), symbol=h) for h in (8, 14, 15)]
    hours.append(hf(datetime(2026, 10, 31, 12, tzinfo=HEL).astimezone(UTC), symbol=99))
    res = daily_summaries(hours, HEL, today=date(2026, 10, 31))
    assert len(res) == 1 and res[0].symbol == 14
