"""Suomenkielinen muotoilu: desimaalipilkku, U+2212-miinus, kellonaika 14.30."""
import math
from datetime import date, datetime

MINUS = "−"
WEEKDAYS = ("ma", "ti", "ke", "to", "pe", "la", "su")


def _round_half_away(x: float, digits: int = 0) -> int:
    """Pyöristys, jossa .5 menee poispäin nollasta. Palauttaa luvun * 10**digits."""
    scaled = abs(x) * 10 ** digits
    n = math.floor(scaled + 0.5)
    return -n if x < 0 else n


def fmt_temp(t: float) -> str:
    n = _round_half_away(t)
    if n == 0:
        return "0°"
    return f"+{n}°" if n > 0 else f"{MINUS}{-n}°"


def fmt_wind(lo: float, hi: float | None = None) -> str:
    """Tuuli kokonaisina m/s: "4 m/s" tai vaihteluväli "2–8 m/s"."""
    a = _round_half_away(lo)
    b = a if hi is None else _round_half_away(hi)
    return f"{a} m/s" if a == b else f"{a}–{b} m/s"


def fmt_price(c: float) -> str:
    n = _round_half_away(c, 1)
    whole, frac = divmod(abs(n), 10)
    sign = MINUS if n < 0 else ""
    return f"{sign}{whole},{frac}"


def fmt_clock(dt: datetime) -> str:
    return f"{dt.hour}.{dt.minute:02d}"


def fmt_weekday(d: date) -> str:
    return WEEKDAYS[d.weekday()]


def fmt_date(d: date) -> str:
    return f"{d.day}.{d.month}."


def fmt_header(dt: datetime) -> str:
    return f"{fmt_weekday(dt.date())} {fmt_date(dt.date())} · {fmt_clock(dt)}"
