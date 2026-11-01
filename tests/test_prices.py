from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from saasahko.prices import (
    PriceSlot,
    cheapest_hours,
    hourly_prices,
    parse_porssisahko,
    price_at,
)

HEL = ZoneInfo("Europe/Helsinki")
UTC = timezone.utc


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def make_slots(start_utc, prices):
    """Build API-shaped dict, ascending 15-min slots from start_utc."""
    items = []
    for i, p in enumerate(prices):
        s = start_utc + timedelta(minutes=15 * i)
        e = s + timedelta(minutes=15) - timedelta(milliseconds=1)
        items.append(
            {
                "price": p,
                "startDate": _iso(s),
                "endDate": e.strftime("%Y-%m-%dT%H:%M:%S.999Z"),
            }
        )
    return {"prices": items}


def slots_from(start_utc, prices):
    return parse_porssisahko(make_slots(start_utc, prices))


def test_parse_sorted_and_utc():
    data = make_slots(datetime(2026, 10, 30, 22, 0, tzinfo=UTC), [1, 2, 3])
    data["prices"].reverse()
    slots = parse_porssisahko(data)
    assert [s.price_c for s in slots] == [1, 2, 3]
    assert all(s.start.tzinfo == UTC for s in slots)
    assert slots[0].start == datetime(2026, 10, 30, 22, 0, tzinfo=UTC)
    assert isinstance(slots[0], PriceSlot)


def test_hourly_average_of_quarters():
    slots = slots_from(datetime(2026, 10, 30, 22, 0, tzinfo=UTC), [1, 2, 3, 4])
    assert hourly_prices(slots, date(2026, 10, 31), HEL)[0] == 2.5


def test_hourly_extra_added():
    slots = slots_from(datetime(2026, 10, 30, 22, 0, tzinfo=UTC), [1, 2, 3, 4])
    assert hourly_prices(slots, date(2026, 10, 31), HEL, extra_c=0.23)[0] == 2.5 + 0.23


def test_missing_hours_are_none():
    slots = slots_from(datetime(2026, 10, 30, 22, 0, tzinfo=UTC), [1.0] * 14 * 4)
    h = hourly_prices(slots, date(2026, 10, 31), HEL)
    assert len(h) == 24
    assert all(v is not None for v in h[:14])
    assert all(v is None for v in h[14:])


def test_incomplete_hour_still_averaged():
    slots = slots_from(datetime(2026, 10, 30, 22, 0, tzinfo=UTC), [2, 4])
    assert hourly_prices(slots, date(2026, 10, 31), HEL)[0] == 3.0


def test_dst_25h_day():
    # 2026-10-25 00:00 Helsinki (EEST) = 2026-10-24T21:00Z; day lasts 25 h
    start = datetime(2026, 10, 24, 21, 0, tzinfo=UTC)
    prices = [1.0] * 4 * 3 + [10.0] * 4 + [20.0] * 4 + [1.0] * 4 * 22
    slots = slots_from(start, prices)
    h = hourly_prices(slots, date(2026, 10, 25), HEL)
    assert len(h) == 24
    assert h[3] == 15.0  # avg of eight quarters (10 and 20)
    assert h[4] == 1.0


def test_dst_23h_day():
    # 2027-03-28 00:00 Helsinki (EET) = 2027-03-27T22:00Z; 03 local missing
    start = datetime(2027, 3, 27, 22, 0, tzinfo=UTC)
    slots = slots_from(start, [1.0] * 4 * 23)
    h = hourly_prices(slots, date(2027, 3, 28), HEL)
    assert len(h) == 24
    assert h[3] is None
    assert h[2] == 1.0 and h[4] == 1.0 and h[23] == 1.0


def test_price_at_quarter_boundary():
    slots = slots_from(datetime(2026, 10, 30, 22, 0, tzinfo=UTC), [1, 2, 3, 4])
    assert price_at(slots, datetime(2026, 10, 30, 22, 15, tzinfo=UTC)) == 2
    assert price_at(slots, datetime(2026, 10, 30, 22, 14, 59, tzinfo=UTC)) == 1
    assert price_at(slots, datetime(2026, 10, 30, 22, 15, tzinfo=UTC), extra_c=0.5) == 2.5
    assert price_at(slots, datetime(2026, 10, 30, 23, 0, tzinfo=UTC)) is None
    assert price_at(slots, datetime(2026, 10, 30, 21, 59, tzinfo=UTC)) is None


def test_cheapest_includes_negative():
    assert cheapest_hours([5, -0.4, 3, None, 0.0, 7]) == {1, 2, 4}


def test_cheapest_tie_prefers_earlier():
    assert cheapest_hours([1, 1, 1, 1], n=3) == {0, 1, 2}


def test_day_published():
    from saasahko.prices import day_published

    assert not day_published([None] * 24)
    assert not day_published([1.0] + [None] * 23)  # only 00-01 from the CET auction
    assert day_published([1.0] * 24)
    assert day_published([None] * 12 + [1.0] * 12)
