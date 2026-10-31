from datetime import datetime

_DESCRIPTIONS = {
    1: "selkeää", 2: "puolipilvistä", 3: "pilvistä",
    21: "heikkoja sadekuuroja", 22: "sadekuuroja", 23: "voimakkaita sadekuuroja",
    31: "heikkoa vesisadetta", 32: "vesisadetta", 33: "voimakasta vesisadetta",
    41: "heikkoja lumikuuroja", 42: "lumikuuroja", 43: "voimakkaita lumikuuroja",
    51: "heikkoa lumisadetta", 52: "lumisadetta", 53: "voimakasta lumisadetta",
    61: "ukkoskuuroja", 62: "voimakkaita ukkoskuuroja", 63: "ukkosta", 64: "voimakasta ukkosta",
    71: "heikkoja räntäkuuroja", 72: "räntäkuuroja", 73: "voimakkaita räntäkuuroja",
    81: "heikkoa räntäsadetta", 82: "räntäsadetta", 83: "voimakasta räntäsadetta",
    91: "utua", 92: "sumua",
}


def describe(code: int) -> str:
    return _DESCRIPTIONS.get(code, "")


def icon_kind(code: int, night: bool) -> str:
    if code == 1:
        return "moon" if night else "sun"
    if code == 2:
        return "partly_night" if night else "partly"
    if 21 <= code <= 33:
        return "rain"
    if 41 <= code <= 53:
        return "snow"
    if 61 <= code <= 64:
        return "thunder"
    if 71 <= code <= 83:
        return "sleet"
    if 91 <= code <= 92:
        return "fog"
    return "cloud"


def is_night(local: datetime) -> bool:
    return local.hour < 7 or local.hour >= 19
