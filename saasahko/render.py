"""Render a DashboardState into the 1072×1448 grayscale Kindle image."""
import math
from datetime import timedelta
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from saasahko.fmt import MINUS, fmt_header, fmt_price, fmt_temp, fmt_weekday
from saasahko.icons import draw_icon
from saasahko.state import DashboardState
from saasahko.symbols import icon_kind, is_night

W, H = 1072, 1448
M = 40
WHITE, BLACK = 255, 0
PAST, CHEAP, BAR, GRID = 0xCC, 0x00, 0x88, 0xBB

CHART_X0, CHART_X1 = 92, W - M
CHART_Y0, CHART_Y1 = 930, 1370
BAR_GAP = 2
_SLOT = (CHART_X1 - CHART_X0) / 48

_FONT_DIR = "/System/Library/Fonts/Supplemental/"


@lru_cache(maxsize=None)
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(_FONT_DIR + ("Arial Bold.ttf" if bold else "Arial.ttf"), size)


def _hour_x(t: float) -> int:
    """x of the left edge of hour slot t (0–48, fractional allowed)."""
    return CHART_X0 + round(t * _SLOT)


def bar_x(i: int) -> tuple[int, int]:
    """Inclusive x range of bar i (0–47), leaving BAR_GAP px before the next slot."""
    return _hour_x(i), _hour_x(i + 1) - BAR_GAP - 1


def value_y(v: float, top: float, bottom: float) -> int:
    return round(CHART_Y1 - (v - bottom) * (CHART_Y1 - CHART_Y0) / (top - bottom))


AXIS_STEPS = (5, 10, 20, 50, 100, 200, 500)
MAX_AXIS_LABELS = 8
AXIS_MIN_TOP = 10


def _round_out(lo: float, hi: float, step: int) -> tuple[int, int]:
    """(top, bottom): the axis range [min(0, lo), max(10, hi)] rounded out to `step`."""
    top = math.ceil(max(AXIS_MIN_TOP, hi) / step) * step
    bottom = math.floor(min(0, lo) / step) * step
    return top, bottom


def axis_step(lo: float, hi: float) -> int:
    """Smallest step in AXIS_STEPS giving at most MAX_AXIS_LABELS labels."""
    for step in AXIS_STEPS:
        top, bottom = _round_out(lo, hi, step)
        if (top - bottom) // step + 1 <= MAX_AXIS_LABELS:
            return step
    return AXIS_STEPS[-1]


def axis_bounds(prices: list[float | None]) -> tuple[int, int, int]:
    """(top, bottom, step) of the price axis; empty data gives (10, 0, 5)."""
    vals = [p for p in prices if p is not None]
    lo, hi = (min(vals), max(vals)) if vals else (0, 0)
    step = axis_step(lo, hi)
    return (*_round_out(lo, hi, step), step)


def _int_label(v: int) -> str:
    return f"{MINUS}{-v}" if v < 0 else str(v)


def _draw_header(d: ImageDraw.ImageDraw, s: DashboardState) -> None:
    mid = 45
    d.text((M, mid), s.place, font=_font(40, True), fill=BLACK, anchor="lm")
    place_right = M + d.textlength(s.place, font=_font(40, True))

    right = W - M
    header = fmt_header(s.now_local)
    d.text((right, mid), header, font=_font(36), fill=BLACK, anchor="rm")
    right -= d.textlength(header, font=_font(36))
    if s.low_battery and s.battery is not None:
        pct = f"{s.battery} %"
        right -= 24
        d.text((right, mid), pct, font=_font(36), fill=BLACK, anchor="rm")
        right -= d.textlength(pct, font=_font(36)) + 10
        bw, bh, lw = 46, 24, 3
        x1, y0 = right - 6, mid - bh // 2
        x0 = x1 - bw
        d.rectangle((x1, mid - 5, x1 + 5, mid + 5), fill=BLACK)  # nub
        d.rectangle((x0, y0, x1, y0 + bh), outline=BLACK, width=lw)
        level = round((bw - 2 * lw - 2) * s.battery / 100)
        d.rectangle((x0 + lw + 1, y0 + lw + 1, x0 + lw + 1 + level, y0 + bh - lw - 1), fill=BLACK)
        right = x0

    if s.note:
        pad_x, gap = 16, 12
        for size in (30, 28, 26, 24, 22):
            f = _font(size)
            tw = d.textlength(s.note, font=f)
            if tw + 2 * (pad_x + gap) <= right - place_right:
                break
        cx = (place_right + right) / 2
        d.rounded_rectangle(
            (cx - tw / 2 - pad_x, mid - 24, cx + tw / 2 + pad_x, mid + 24), radius=8, fill=BLACK
        )
        d.text((cx, mid), s.note, font=f, fill=WHITE, anchor="mm")

    d.rectangle((M, 89, W - M, 91), fill=BLACK)


def _draw_current(d: ImageDraw.ImageDraw, s: DashboardState) -> None:
    cur = s.current
    if cur is None:
        return
    draw_icon(d, icon_kind(cur.symbol, is_night(s.now_local)), (M, 108, M + 240, 348))
    d.text((M + 270, 318), fmt_temp(cur.temp), font=_font(200, True), fill=BLACK, anchor="ls")

    parts = [s.current_desc] if s.current_desc else []
    parts += [f"tuntuu kuin {fmt_temp(cur.feels_like)}", f"tuuli {math.floor(cur.wind + 0.5)} m/s"]
    line = " · ".join(parts)
    line = line[:1].upper() + line[1:]
    for size in (38, 34, 30, 26):
        if d.textlength(line, font=_font(size)) <= W - 2 * M:
            break
    d.text((M, 392), line, font=_font(size), fill=BLACK, anchor="ls")


def _draw_hours(d: ImageDraw.ImageDraw, s: DashboardState) -> None:
    cw = (W - 2 * M) / 6
    for k, h in enumerate(s.next_hours[:6]):
        local = h.time.astimezone(s.now_local.tzinfo)
        cx = round(M + cw * (k + 0.5))
        d.text((cx, 425), f"{local.hour:02d}", font=_font(34), fill=BLACK, anchor="ma")
        draw_icon(d, icon_kind(h.symbol, is_night(local)), (cx - 40, 468, cx + 40, 548))
        d.text((cx, 558), fmt_temp(h.temp), font=_font(46, True), fill=BLACK, anchor="ma")


def _draw_days(d: ImageDraw.ImageDraw, s: DashboardState) -> None:
    d.rectangle((M, 624, W - M, 625), fill=0x88)
    cw = (W - 2 * M) / 3
    mid = 684
    for k, day in enumerate(s.days[:3]):
        name = fmt_weekday(day.day)
        temps = f"{fmt_temp(day.tmax)} / {fmt_temp(day.tmin)}"
        wn = d.textlength(name, font=_font(38, True))
        wt = d.textlength(temps, font=_font(38))
        gap = 14
        x = M + cw * (k + 0.5) - (wn + gap + 60 + gap + wt) / 2
        d.text((x, mid), name, font=_font(38, True), fill=BLACK, anchor="lm")
        x += wn + gap
        draw_icon(d, icon_kind(day.symbol, False), (round(x), mid - 30, round(x) + 60, mid + 30))
        x += 60 + gap
        d.text((x, mid), temps, font=_font(38), fill=BLACK, anchor="lm")


def _draw_price_header(d: ImageDraw.ImageDraw, s: DashboardState) -> None:
    d.rectangle((M, 758, W - M, 762), fill=BLACK)
    d.text((M, 782), "SÄHKÖ", font=_font(40, True), fill=BLACK, anchor="la")
    base = 892
    x = W - M
    unit = " c/kWh"
    d.text((x, base), unit, font=_font(34), fill=BLACK, anchor="rs")
    x -= d.textlength(unit, font=_font(34))
    price = fmt_price(s.price_now) if s.price_now is not None else "–"
    d.text((x, base), price, font=_font(100, True), fill=BLACK, anchor="rs")
    x -= d.textlength(price, font=_font(100, True)) + 16
    d.text((x, base), "nyt", font=_font(34), fill=BLACK, anchor="rs")


def _draw_chart(d: ImageDraw.ImageDraw, s: DashboardState) -> None:
    prices = s.prices_today + s.prices_tomorrow
    top, bottom, step = axis_bounds(prices)
    y_zero = value_y(0, top, bottom)

    for v in range(bottom, top + 1, step):
        y = value_y(v, top, bottom)
        if v != 0:
            d.line((CHART_X0, y, CHART_X1, y), fill=GRID, width=1)
        d.text((CHART_X0 - 10, y), _int_label(v), font=_font(26), fill=BLACK, anchor="rm")

    for i, p in enumerate(prices):
        if p is None:
            continue
        if i < 24 and i < s.now_local.hour:
            color = PAST
        elif (i < 24 and i in s.cheapest_today) or (i >= 24 and i - 24 in s.cheapest_tomorrow):
            color = CHEAP
        else:
            color = BAR
        x0, x1 = bar_x(i)
        y = value_y(p, top, bottom)
        if y < y_zero:
            d.rectangle((x0, y, x1, y_zero - 1), fill=color)
        elif y > y_zero:
            d.rectangle((x0, y_zero, x1, y), fill=color)

    d.rectangle((CHART_X0, y_zero - 1, CHART_X1, y_zero), fill=BLACK)
    x_day = _hour_x(24)
    d.rectangle((x_day - BAR_GAP, CHART_Y0, x_day - 1, CHART_Y1), fill=BLACK)

    x_now = _hour_x(s.now_local.hour + s.now_local.minute / 60)
    for y in range(CHART_Y0, CHART_Y1, 20):
        d.line((x_now, y, x_now, min(y + 11, CHART_Y1)), fill=BLACK, width=3)
    d.text((x_now, CHART_Y0 - 6), "nyt", font=_font(28, True), fill=BLACK, anchor="ms")

    if all(p is None for p in s.prices_tomorrow):
        cx, cy = (x_day + CHART_X1) / 2, (CHART_Y0 + CHART_Y1) / 2
        d.rectangle((cx - 150, cy - 50, cx + 150, cy + 50), fill=WHITE)  # hide gridlines
        d.text((cx, cy - 6), "huomisen hinnat", font=_font(34), fill=BLACK, anchor="md")
        d.text((cx, cy + 6), "n. klo 14", font=_font(34), fill=BLACK, anchor="ma")

    tomorrow = fmt_weekday(s.now_local.date() + timedelta(days=1))
    labels = ["00", "06", "12", "18", f"{tomorrow} 00", "06", "12", "18", "24"]
    for k, label in enumerate(labels):
        anchor = "la" if k == 0 else "ra" if k == len(labels) - 1 else "ma"
        d.text((_hour_x(6 * k), 1380), label, font=_font(28), fill=BLACK, anchor=anchor)


def render(state: DashboardState) -> Image.Image:
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    _draw_header(d, state)
    _draw_current(d, state)
    _draw_hours(d, state)
    _draw_days(d, state)
    _draw_price_header(d, state)
    _draw_chart(d, state)
    return img
