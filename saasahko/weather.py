import math
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

_NS = {"wfs": "http://www.opengis.net/wfs/2.0", "BsWfs": "http://xml.fmi.fi/schema/wfs/2.0"}
_PARAMS = ("Temperature", "WeatherSymbol3", "WindSpeedMS", "FeelsLike")
_QUERY = "fmi::forecast::edited::weather::scandinavia::point::simple"
_MAX_CURRENT_GAP = timedelta(minutes=90)


@dataclass(frozen=True)
class HourForecast:
    time: datetime
    temp: float
    symbol: int
    wind: float
    feels_like: float


@dataclass(frozen=True)
class DaySummary:
    day: date
    tmin: float
    tmax: float
    symbol: int


def _iso_z(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_fmi_url(lat: float, lon: float, start: datetime, hours: int = 100) -> str:
    return (
        "https://opendata.fmi.fi/wfs?service=WFS&version=2.0.0&request=getFeature"
        f"&storedquery_id={_QUERY}"
        f"&latlon={lat},{lon}"
        f"&parameters={','.join(_PARAMS)}"
        "&timestep=60"
        f"&starttime={_iso_z(start)}"
        f"&endtime={_iso_z(start + timedelta(hours=hours))}"
    )


def fetch_fmi(url: str, timeout: float = 20) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def parse_fmi(xml: str) -> list[HourForecast]:
    root = ET.fromstring(xml)
    by_time: dict[datetime, dict[str, float]] = {}
    for el in root.iterfind("wfs:member/BsWfs:BsWfsElement", _NS):
        name = el.findtext("BsWfs:ParameterName", namespaces=_NS)
        if name not in _PARAMS:
            continue
        try:
            t = datetime.fromisoformat(el.findtext("BsWfs:Time", namespaces=_NS).strip().replace("Z", "+00:00"))
            value = float(el.findtext("BsWfs:ParameterValue", namespaces=_NS))
        except (AttributeError, ValueError):
            continue
        if math.isnan(value):
            continue
        by_time.setdefault(t, {})[name] = value
    return [
        HourForecast(
            time=t,
            temp=v["Temperature"],
            symbol=int(v["WeatherSymbol3"]),
            wind=v["WindSpeedMS"],
            feels_like=v["FeelsLike"],
        )
        for t, v in sorted(by_time.items())
        if all(p in v for p in _PARAMS)
    ]


def current(hours: list[HourForecast], now: datetime) -> HourForecast | None:
    if not hours:
        return None
    best = min(hours, key=lambda h: abs(h.time - now))
    return best if abs(best.time - now) <= _MAX_CURRENT_GAP else None


def next_hours(hours: list[HourForecast], now: datetime, n: int = 6) -> list[HourForecast]:
    return [h for h in hours if h.time > now][:n]


def daily_summaries(hours: list[HourForecast], tz: ZoneInfo, today: date, n: int = 3) -> list[DaySummary]:
    out = []
    for i in range(1, n + 1):
        day = today + timedelta(days=i)
        noon = datetime(day.year, day.month, day.day, 12, tzinfo=tz)
        day_hours = [h for h in hours if h.time.astimezone(tz).date() == day]
        if not day_hours:
            continue
        rep = min(day_hours, key=lambda h: abs(h.time - noon))
        out.append(
            DaySummary(
                day=day,
                tmin=min(h.temp for h in day_hours),
                tmax=max(h.temp for h in day_hours),
                symbol=rep.symbol,
            )
        )
    return out
