import math

import pytest
from PIL import Image, ImageDraw

from saasahko.icons import draw_icon
from saasahko.render import CHART_X0, CHART_X1, CHART_Y0, CHART_Y1, bar_x, render, value_y
from tests.sample_state import PRICES_TODAY, PRICES_TOMORROW, sample_state

ALL = PRICES_TODAY + PRICES_TOMORROW
TOP = max(10, math.ceil(max(ALL) / 5) * 5)
BOTTOM = min(0, math.floor(min(ALL) / 5) * 5)


def bar_center(i: int, price: float) -> tuple[int, int]:
    x0, x1 = bar_x(i)
    y_val, y_zero = value_y(price, TOP, BOTTOM), value_y(0, TOP, BOTTOM)
    return (x0 + x1) // 2, (y_val + y_zero) // 2


def test_size_and_mode():
    img = render(sample_state())
    assert img.size == (1072, 1448) and img.mode == "L"


def test_cheapest_bar_is_black():
    state = sample_state()
    h = min(state.cheapest_tomorrow, key=lambda k: PRICES_TOMORROW[k])
    img = render(state)
    assert img.getpixel(bar_center(24 + h, PRICES_TOMORROW[h])) == 0


def test_past_bar_is_light():
    img = render(sample_state())
    assert img.getpixel(bar_center(3, PRICES_TODAY[3])) == 0xCC


def test_current_hour_is_not_past():
    img = render(sample_state())
    x0, x1 = bar_x(14)
    # Sample just left of the dashed "nyt" line (at 14.5) to avoid hitting it.
    assert img.getpixel((x0 + 2, bar_center(14, PRICES_TODAY[14])[1])) == 0x88


def test_negative_bar_below_zero_line():
    h = PRICES_TOMORROW.index(min(PRICES_TOMORROW))
    img = render(sample_state())
    x, _ = bar_center(24 + h, PRICES_TOMORROW[h])
    y_zero, y_val = value_y(0, TOP, BOTTOM), value_y(PRICES_TOMORROW[h], TOP, BOTTOM)
    assert y_val > y_zero + 10
    assert img.getpixel((x, y_val - 3)) != 255  # bar reaches down to its value
    assert img.getpixel((x, y_val + 3)) == 255  # and stops there


def test_no_tomorrow_shows_text_and_no_bars():
    img = render(sample_state(prices_tomorrow=[None] * 24, cheapest_tomorrow=set()))
    x_mid = bar_x(24)[0]
    y_zero = value_y(0, max(10, math.ceil(max(PRICES_TODAY) / 5) * 5), 0)
    # Every drawn bar touches the zero line. The band just above it must be
    # empty: the whole right-half area can't be checked pixel-exactly, because
    # antialiased text produces arbitrary grays (including 0x88).
    band = img.crop((x_mid, y_zero - 4, CHART_X1 + 1, y_zero - 1))
    assert band.histogram()[255] == band.width * band.height
    # The "huomisen hinnat / n. klo 14" text box, centred in the right half.
    cx, cy = (x_mid + CHART_X1) // 2, (CHART_Y0 + CHART_Y1) // 2
    text_box = (cx - 150, cy - 50, cx + 150, cy + 50)
    with_text = img.crop(text_box).histogram()[0]
    with_bars = render(sample_state()).crop(text_box).histogram()[0]
    assert with_text > 500
    assert with_bars == 0


def test_missing_weather_does_not_crash():
    img = render(sample_state(current=None, current_desc="", next_hours=[], days=[]))
    assert img.size == (1072, 1448)


def test_no_prices_at_all_does_not_crash():
    img = render(
        sample_state(
            prices_today=[None] * 24, prices_tomorrow=[None] * 24,
            cheapest_today=set(), cheapest_tomorrow=set(), price_now=None,
        )
    )
    assert img.size == (1072, 1448)


def test_low_battery_does_not_crash():
    render(sample_state(battery=12, low_battery=True, note="sää päivitetty 12.30"))


def test_note_drawn_inverted():
    center = (380, 10, 690, 80)
    plain = render(sample_state()).crop(center).histogram()[0]
    noted = render(sample_state(note="ei hintatietoja")).crop(center).histogram()[0]
    assert plain == 0
    assert noted > 1000


@pytest.mark.parametrize(
    "kind", ["sun", "moon", "partly", "partly_night", "cloud", "rain", "sleet", "snow", "thunder", "fog"]
)
def test_icon_draws_something(kind):
    img = Image.new("L", (100, 100), 255)
    draw_icon(ImageDraw.Draw(img), kind, (0, 0, 100, 100))
    assert sum(img.histogram()[:255]) >= 200
