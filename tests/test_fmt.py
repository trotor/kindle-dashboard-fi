from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from saasahko.fmt import fmt_clock, fmt_header, fmt_price, fmt_temp, fmt_weekday


@pytest.mark.parametrize("t,s", [(4.2,"+4°"), (-6.4,"−6°"), (-0.3,"0°"), (0.4,"0°"), (12.5,"+13°"), (-2.5,"−3°")])
def test_fmt_temp(t, s): assert fmt_temp(t) == s


@pytest.mark.parametrize("c,s", [(6.43,"6,4"), (12.06,"12,1"), (-0.44,"−0,4"), (0.0,"0,0")])
def test_fmt_price(c, s): assert fmt_price(c) == s


def test_fmt_header():
    dt = datetime(2026,10,31,14,30, tzinfo=ZoneInfo("Europe/Helsinki"))
    assert fmt_header(dt) == "la 31.10. · 14.30"
    assert fmt_clock(dt) == "14.30" and fmt_weekday(dt.date()) == "la"
