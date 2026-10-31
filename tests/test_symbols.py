from datetime import datetime

import pytest

from saasahko.symbols import describe, icon_kind, is_night


@pytest.mark.parametrize(
    "code,kind",
    [(1, "sun"), (2, "partly"), (3, "cloud"), (22, "rain"), (32, "rain"), (42, "snow"),
     (52, "snow"), (63, "thunder"), (72, "sleet"), (82, "sleet"), (92, "fog"), (999, "cloud")],
)
def test_icon_kind_day(code, kind):
    assert icon_kind(code, night=False) == kind


def test_icon_kind_night():
    assert icon_kind(1, True) == "moon" and icon_kind(2, True) == "partly_night"
    assert icon_kind(22, True) == "rain"


def test_describe():
    assert describe(3) == "pilvistä" and describe(999) == ""
    assert describe(1) == "selkeää" and describe(92) == "sumua"


def test_is_night():
    assert is_night(datetime(2026, 11, 1, 6, 59))
    assert not is_night(datetime(2026, 11, 1, 7, 0))
    assert not is_night(datetime(2026, 11, 1, 18, 59))
    assert is_night(datetime(2026, 11, 1, 19, 0))
