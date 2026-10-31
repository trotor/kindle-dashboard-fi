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
