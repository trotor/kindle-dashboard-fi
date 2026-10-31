import tomllib
from dataclasses import dataclass, fields
from pathlib import Path


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


def load_config(path: Path) -> Config:
    path = Path(path)
    with path.open("rb") as f:
        data = tomllib.load(f)
    known = {f.name for f in fields(Config)}
    unknown = sorted(set(data) - known)
    if unknown:
        raise ValueError(f"Tuntemattomat asetukset: {', '.join(unknown)}")
    if "cache_dir" in data:
        data["cache_dir"] = path.parent / Path(data["cache_dir"])
    else:
        data["cache_dir"] = path.parent / Config.cache_dir
    return Config(**data)
