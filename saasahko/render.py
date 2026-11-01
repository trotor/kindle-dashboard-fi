"""Render a DashboardState into the 1072×1448 grayscale Kindle image."""
import math
from datetime import timedelta
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from saasahko.fmt import MINUS, fmt_header, fmt_price, fmt_temp, fmt_weekday, fmt_wind
from saasahko.icons import draw_icon
from saasahko.prices import day_published
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


def axis_bounds(prices: list[float | None], headroom: float = 1.0) -> tuple[int, int, int]:
    """(top, bottom, step) of the price axis; empty data gives (10, 0, 5).

    `headroom` > 1 leaves room above the highest bar (for the expensive-hours bracket).
    """
    vals = [p for p in prices if p is not None]
    lo, hi = (min(vals), max(vals) * headroom) if vals else (0, 0)
    step = axis_step(lo, hi)
    return (*_round_out(lo, hi, step), step)


def expensive_runs(prices: list[float | None], first: int, limit: float) -> list[tuple[int, int]]:
    """Half-open [a, b) runs of hours >= `first` whose price is at least `limit` (0 = off)."""
    if limit <= 0:
        return []
    runs: list[tuple[int, int]] = []
    start = None
    for i in range(first, len(prices) + 1):
        hot = i < len(prices) and prices[i] is not None and prices[i] >= limit
        if hot and start is None:
            start = i
        elif not hot and start is not None:
            runs.append((start, i))
            start = None
    return runs


def _num(v: float) -> str:
    return str(int(v)) if v == int(v) else fmt_price(v)


@lru_cache(maxsize=1)
def _hatch() -> Image.Image:
    """Full-size diagonal stripes; expensive bar parts are cropped from this."""
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    for k in range(-H, W, 12):
        d.line((k, H, k + H, 0), fill=BLACK, width=3)
    return img


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
    parts += [f"tuntuu kuin {fmt_temp(cur.feels_like)}", f"tuuli {fmt_wind(cur.wind)}"]
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
        draw_icon(d, icon_kind(h.symbol, is_night(local)), (cx - 36, 464, cx + 36, 536))
        d.text((cx, 542), fmt_temp(h.temp), font=_font(46, True), fill=BLACK, anchor="ma")
        d.text((cx, 598), fmt_wind(h.wind), font=_font(28), fill=BLACK, anchor="ma")


def _draw_days(d: ImageDraw.ImageDraw, s: DashboardState) -> None:
    d.rectangle((M, 640, W - M, 641), fill=0x88)
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
        d.text((M + cw * (k + 0.5), 730), f"tuuli {fmt_wind(day.wind_min, day.wind_max)}",
               font=_font(28), fill=BLACK, anchor="mm")


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
    _draw_price_summary(d, s)


def _draw_price_summary(d: ImageDraw.ImageDraw, s: DashboardState) -> None:
    """Tomorrow's average, max and min once published, otherwise today's."""
    if day_published(s.prices_tomorrow):
        label, day = "huomenna", s.prices_tomorrow
    else:
        label, day = "tänään", s.prices_today
    vals = [p for p in day if p is not None]
    if not vals:
        return
    avg = sum(vals) / len(vals)
    d.text((M, 858), f"{label} ka {fmt_price(avg)}", font=_font(30, True), fill=BLACK, anchor="ls")
    d.text((M, 894), f"kallein {fmt_price(max(vals))} · halvin {fmt_price(min(vals))}",
           font=_font(28), fill=BLACK, anchor="ls")


def _draw_chart(img: Image.Image, d: ImageDraw.ImageDraw, s: DashboardState) -> None:
    prices = s.prices_today + s.prices_tomorrow
    limit = s.price_limit
    runs = expensive_runs(prices, s.now_local.hour, limit)
    top, bottom, step = axis_bounds(prices, headroom=1.2 if runs else 1.0)
    y_zero = value_y(0, top, bottom)
    y_limit = value_y(limit, top, bottom) if limit > 0 else None

    for v in range(bottom, top + 1, step):
        y = value_y(v, top, bottom)
        if v != 0:
            d.line((CHART_X0, y, CHART_X1, y), fill=GRID, width=1)
        d.text((CHART_X0 - 10, y), _int_label(v), font=_font(26), fill=BLACK, anchor="rm")

    for i, p in enumerate(prices):
        if p is None:
            continue
        past = i < 24 and i < s.now_local.hour
        if past:
            color = PAST
        elif (i < 24 and i in s.cheapest_today) or (i >= 24 and i - 24 in s.cheapest_tomorrow):
            color = CHEAP
        else:
            color = BAR
        x0, x1 = bar_x(i)
        y = value_y(p, top, bottom)
        if not past and y_limit is not None and p > limit and y < y_limit:
            d.rectangle((x0, y_limit, x1, y_zero - 1), fill=color)
            box = (x0, y, x1 + 1, y_limit + 1)
            img.paste(_hatch().crop(box), box[:2])
            d.rectangle((x0, y, x1, y_limit), outline=BLACK, width=3)
        elif y < y_zero:
            d.rectangle((x0, y, x1, y_zero - 1), fill=color)
        elif y > y_zero:
            d.rectangle((x0, y_zero, x1, y), fill=color)

    d.rectangle((CHART_X0, y_zero - 1, CHART_X1, y_zero), fill=BLACK)
    x_day = _hour_x(24)
    d.rectangle((x_day - BAR_GAP, CHART_Y0, x_day - 1, CHART_Y1), fill=BLACK)

    if y_limit is not None and bottom <= limit <= top:
        for x in range(CHART_X0, CHART_X1, 24):
            d.line((x, y_limit, min(x + 14, CHART_X1), y_limit), fill=BLACK, width=3)
        px_per_c = (CHART_Y1 - CHART_Y0) / (top - bottom)
        nearest = min(abs(limit - v) for v in range(bottom, top + 1, step))
        if nearest * px_per_c >= 28:
            d.text((CHART_X0 - 10, y_limit), _num(limit), font=_font(26, True), fill=BLACK, anchor="rm")

    x_now = _hour_x(s.now_local.hour + s.now_local.minute / 60)
    for y in range(CHART_Y0, CHART_Y1, 20):
        d.line((x_now, y, x_now, min(y + 11, CHART_Y1)), fill=BLACK, width=3)
    d.text((x_now, CHART_Y0 - 6), "nyt", font=_font(28, True), fill=BLACK, anchor="ms")

    _draw_runs(d, s, prices, runs, top, bottom)

    if not day_published(s.prices_tomorrow):
        cx, cy = (x_day + CHART_X1) / 2, (CHART_Y0 + CHART_Y1) / 2
        d.rectangle((cx - 150, cy - 50, cx + 150, cy + 50), fill=WHITE)  # hide gridlines
        d.text((cx, cy - 6), "huomisen hinnat", font=_font(34), fill=BLACK, anchor="md")
        d.text((cx, cy + 6), "n. klo 14", font=_font(34), fill=BLACK, anchor="ma")

    tomorrow = fmt_weekday(s.now_local.date() + timedelta(days=1))
    labels = ["00", "06", "12", "18", f"{tomorrow} 00", "06", "12", "18", "24"]
    for k, label in enumerate(labels):
        anchor = "la" if k == 0 else "ra" if k == len(labels) - 1 else "ma"
        d.text((_hour_x(6 * k), 1380), label, font=_font(28), fill=BLACK, anchor=anchor)


BRACKET_Y = CHART_Y0 + 4


def _draw_runs(d, s: DashboardState, prices, runs, top: int, bottom: int) -> None:
    """Bracket and label over each expensive run, and the peak value above its bar."""
    f = _font(28, True)
    for a, b in runs:
        xa, xb = _hour_x(a), _hour_x(b) - BAR_GAP
        d.line((xa, BRACKET_Y + 16, xa, BRACKET_Y), fill=BLACK, width=3)
        d.line((xa, BRACKET_Y, xb, BRACKET_Y), fill=BLACK, width=3)
        d.line((xb, BRACKET_Y, xb, BRACKET_Y + 16), fill=BLACK, width=3)
        ha, hb = a % 24, b if b <= 24 else b - 24
        span = f"{ha:02d}–{hb:02d}"
        for text in (f"klo {span} yli {_num(s.price_limit)} c", f"{span} yli {_num(s.price_limit)} c", span):
            w = d.textlength(text, font=f)
            if w + 2 * 24 <= xb - xa:
                cx = (xa + xb) / 2
                d.rectangle((cx - w / 2 - 8, BRACKET_Y - 18, cx + w / 2 + 8, BRACKET_Y + 18), fill=WHITE)
                d.text((cx, BRACKET_Y), text, font=f, fill=BLACK, anchor="mm")
                break

    if runs:
        k = max((i for a, b in runs for i in range(a, b)), key=lambda i: prices[i])
        pk = prices[k]
        y = value_y(pk, top, bottom) - 6
        if y - 26 > BRACKET_Y + 20:
            x0, x1 = bar_x(k)
            d.text(((x0 + x1) / 2, y), str(math.floor(pk + 0.5)), font=_font(26, True), fill=BLACK, anchor="ms")


def render(state: DashboardState) -> Image.Image:
    img = Image.new("L", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    _draw_header(d, state)
    _draw_current(d, state)
    _draw_hours(d, state)
    _draw_days(d, state)
    _draw_price_header(d, state)
    _draw_chart(img, d, state)
    return img
