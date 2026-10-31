import pytest

from saasahko.config import load_config


def test_defaults_when_keys_missing(tmp_path):
    p = tmp_path / "c.toml"; p.write_text('margin_c = 0.23\n')
    c = load_config(p)
    assert c.margin_c == 0.23 and c.lat == 62.9876 and c.port == 8088
    assert c.cache_dir == tmp_path / "cache"


def test_unknown_key_rejected(tmp_path):
    p = tmp_path / "c.toml"; p.write_text('marginaali = 1\n')
    with pytest.raises(ValueError): load_config(p)


def _load(tmp_path, text):
    p = tmp_path / "c.toml"
    p.write_text(text)
    return load_config(p)


def test_numeric_fields_coerced(tmp_path):
    c = _load(tmp_path, 'lat = 63\nlon = "27.5"\nmargin_c = 0\ntransfer_c = "5.0"\n'
              'port = "8090"\nlow_battery_percent = 15.0\n')
    assert c.lat == 63.0 and type(c.lat) is float
    assert c.lon == 27.5 and type(c.margin_c) is float and c.transfer_c == 5.0
    assert c.port == 8090 and type(c.port) is int
    assert c.low_battery_percent == 15 and type(c.low_battery_percent) is int


@pytest.mark.parametrize("line,key", [
    ('margin_c = "abc"', "margin_c"),
    ('lat = []', "lat"),
    ('port = "x"', "port"),
    ('port = 8088.5', "port"),
    ('low_battery_percent = true', "low_battery_percent"),
    ('transfer_c = false', "transfer_c"),
])
def test_bad_numeric_value_names_key(tmp_path, line, key):
    with pytest.raises(ValueError, match=key):
        _load(tmp_path, line + "\n")


@pytest.mark.parametrize("tz", ["Europe/Helsinkii", "Europe", "", "../etc/passwd"])
def test_unknown_timezone_rejected(tmp_path, tz):
    with pytest.raises(ValueError, match="timezone"):
        _load(tmp_path, f'timezone = "{tz}"\n')


def test_non_string_timezone_rejected(tmp_path):
    with pytest.raises(ValueError, match="timezone"):
        _load(tmp_path, 'timezone = 3\n')
