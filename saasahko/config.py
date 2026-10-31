import tomllib
from dataclasses import dataclass, fields
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class Config:
    place_name: str = "TOIVALA"
    lat: float = 62.9876
    lon: float = 27.7216
    port: int = 8088
    margin_c: float = 0.0
    transfer_c: float = 0.0
    low_battery_percent: int = 20
    cache_dir: Path = Path("cache")
    timezone: str = "Europe/Helsinki"


def _coerce(key: str, typ: type, value: object) -> int | float:
    """Value as `typ` (int or float); bools and fractional values for ints are rejected."""
    bad = ValueError(f"Virheellinen asetus {key}: {value!r}")
    if isinstance(value, bool):
        raise bad
    try:
        out = typ(value)
    except (TypeError, ValueError):
        raise bad from None
    if isinstance(value, float) and out != value:
        raise bad
    return out


def _check_timezone(value: object) -> None:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError, TypeError, OSError):
        raise ValueError(f"Virheellinen asetus timezone: {value!r}") from None


def load_config(path: Path) -> Config:
    path = Path(path)
    with path.open("rb") as f:
        data = tomllib.load(f)
    known = {f.name for f in fields(Config)}
    unknown = sorted(set(data) - known)
    if unknown:
        raise ValueError(f"Tuntemattomat asetukset: {', '.join(unknown)}")
    for f in fields(Config):
        if f.name in data and f.type in (int, float):
            data[f.name] = _coerce(f.name, f.type, data[f.name])
    if "timezone" in data:
        _check_timezone(data["timezone"])
    if "cache_dir" in data:
        data["cache_dir"] = path.parent / Path(data["cache_dir"])
    else:
        data["cache_dir"] = path.parent / Config.cache_dir
    return Config(**data)
