"""Finnish spot electricity prices (api.porssisahko.net)."""
from __future__ import annotations

import json
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

PORSSISAHKO_URL = "https://api.porssisahko.net/v2/latest-prices.json"
SLOT = timedelta(minutes=15)


@dataclass(frozen=True)
class PriceSlot:
    start: datetime  # UTC, aware
    price_c: float  # c/kWh incl. VAT


def parse_porssisahko(data: dict) -> list[PriceSlot]:
    slots = []
    for item in data["prices"]:
        start = datetime.fromisoformat(item["startDate"].replace("Z", "+00:00"))
        slots.append(PriceSlot(start.astimezone(timezone.utc), float(item["price"])))
    slots.sort(key=lambda s: s.start)
    return slots


def hourly_prices(
    slots: list[PriceSlot], day: date, tz: ZoneInfo, extra_c: float = 0.0
) -> list[float | None]:
    groups: dict[int, list[float]] = defaultdict(list)
    for s in slots:
        local = s.start.astimezone(tz)
        if local.date() == day:
            groups[local.hour].append(s.price_c)
    return [
        sum(groups[h]) / len(groups[h]) + extra_c if groups.get(h) else None
        for h in range(24)
    ]


def price_at(
    slots: list[PriceSlot], at: datetime, extra_c: float = 0.0
) -> float | None:
    for s in slots:
        if s.start <= at < s.start + SLOT:
            return s.price_c + extra_c
    return None


def cheapest_hours(hourly: list[float | None], n: int = 3) -> set[int]:
    valid = [(p, h) for h, p in enumerate(hourly) if p is not None]
    valid.sort()  # price, then earlier hour on ties
    return {h for _, h in valid[:n]}


def fetch_porssisahko(timeout: float = 15) -> dict:
    req = urllib.request.Request(
        PORSSISAHKO_URL, headers={"User-Agent": "saasahko-kindle"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)
