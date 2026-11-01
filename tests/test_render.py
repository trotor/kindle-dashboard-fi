from dataclasses import replace

import pytest
from PIL import Image, ImageDraw

from saasahko.icons import draw_icon
from saasahko.render import (
    CHART_X0, CHART_X1, CHART_Y0, CHART_Y1, axis_bounds, axis_step, bar_x, render, value_y,
)
from tests.sample_state import PRICES_TODAY, PRICES_TOMORROW, sample_state

ALL = PRICES_TODAY + PRICES_TOMORROW
TOP, BOTTOM, _ = axis_bounds(ALL)


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
    top, bottom, _ = axis_bounds(PRICES_TODAY)
    y_zero = value_y(0, top, bottom)
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


def _dark_columns(img, y0, y1, x0=0, x1=1072):
    return [x for x in range(x0, x1) if min(img.getpixel((x, y)) for y in range(y0, y1)) < 128]


@pytest.mark.parametrize("note", ["hinnat päivitetty 31.10. 14.05", "sää päivitetty 31.10. 14.05"])
def test_long_note_fits_between_place_and_battery(note):
    base = sample_state(battery=12, low_battery=True)
    plain = render(base)
    dark = _dark_columns(plain, 21, 70)
    place_right = max(x for x in dark if x < 400)
    battery_left = min(x for x in dark if x > place_right)
    noted = render(replace(base, note=note))
    box = _dark_columns(noted, 25, 26)  # row above all header glyphs: only the note box
    assert box
    assert place_right < min(box) and max(box) < battery_left


@pytest.mark.parametrize("lo,hi,step", [(0, 13, 5), (0, 47, 10), (0, 230, 50), (-3, 13, 5), (-1.2, 14.9, 5)])
def test_axis_step(lo, hi, step):
    assert axis_step(lo, hi) == step


@pytest.mark.parametrize("values,expected", [
    ([2.0, 13.0], (15, 0, 5)),
    ([2.0, 47.0], (50, 0, 10)),
    ([2.0, 230.0], (250, 0, 50)),
    ([-3.0, 8.0], (10, -5, 5)),
    ([1.0, 2.0], (10, 0, 5)),
    ([None, None], (10, 0, 5)),
    ([], (10, 0, 5)),
])
def test_axis_bounds(values, expected):
    assert axis_bounds(values) == expected


@pytest.mark.parametrize("values", [[13.0], [47.0], [230.0], [-40.0, 230.0], [900.0], [-3.0]])
def test_axis_has_at_most_8_labels(values):
    top, bottom, step = axis_bounds(values)
    assert (top - bottom) % step == 0 and (top - bottom) // step + 1 <= 8
    assert top >= max(10, *values) and bottom <= min(0, *values)


def test_spike_day_gridlines_use_step():
    spike = list(PRICES_TODAY)
    spike[18] = 230.0
    top, bottom, step = axis_bounds(spike + PRICES_TOMORROW)
    assert step == 50
    img = render(sample_state(prices_today=spike))
    x = CHART_X0 + 2  # left of the first bar, only gridlines here
    y100 = value_y(100, top, bottom)
    assert img.getpixel((x, y100)) != 255
    assert img.getpixel((x, value_y(5, top, bottom))) == 255


def test_tomorrow_text_shown_when_only_first_hour_known():
    only_first = [PRICES_TOMORROW[0]] + [None] * 23
    x_mid = bar_x(24)[0]
    cx, cy = (x_mid + CHART_X1) // 2, (CHART_Y0 + CHART_Y1) // 2
    text_box = (cx - 150, cy - 50, cx + 150, cy + 50)
    none = render(sample_state(prices_tomorrow=[None] * 24, cheapest_tomorrow=set()))
    first = render(sample_state(prices_tomorrow=only_first, cheapest_tomorrow=set()))
    assert first.crop(text_box).tobytes() == none.crop(text_box).tobytes()


def _hour_wind_box(k: int) -> tuple[int, int, int, int]:
    cw = (1072 - 2 * 40) / 6
    cx = round(40 + cw * (k + 0.5))
    return (cx - 70, 600, cx + 70, 632)


def test_hour_wind_drawn_under_temperature():
    state = sample_state()
    calm = [replace(h, wind=0.0) for h in state.next_hours]
    windy = [replace(h, wind=12.0) for h in state.next_hours]
    a = render(replace(state, next_hours=calm)).crop(_hour_wind_box(0))
    b = render(replace(state, next_hours=windy)).crop(_hour_wind_box(0))
    assert a.tobytes() != b.tobytes()


def test_day_wind_drawn():
    state = sample_state()
    box = (40, 708, 1072 - 40, 748)
    calm = [replace(d, wind_min=0.0, wind_max=1.0) for d in state.days]
    windy = [replace(d, wind_min=8.0, wind_max=15.0) for d in state.days]
    a = render(replace(state, days=calm)).crop(box)
    b = render(replace(state, days=windy)).crop(box)
    assert a.tobytes() != b.tobytes()
