import subprocess

import pytest


def run(call, env=None):
    r = subprocess.run(
        ["sh", "-c", f". kindle/saa-ja-sahko/lib.sh; {call}"],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


@pytest.mark.parametrize("h,s", [
    (0, "7200"), (5, "7200"), (6, "1800"), (14, "1800"), (22, "1800"), (23, "7200"),
    ("00", "7200"), ("05", "7200"), ("06", "1800"), ("08", "1800"), ("09", "1800"),
])
def test_interval(h, s):
    assert run(f"interval_for_hour {h}") == s


def test_build_url():
    assert run("build_url http://x/k.png 70") == "http://x/k.png?batt=70"


def test_build_url_bad_batt():
    assert run('build_url http://x/k.png ""') == "http://x/k.png"
    assert run("build_url http://x/k.png abc") == "http://x/k.png"
    assert run("build_url http://x/k.png 7a") == "http://x/k.png"


def test_fail_text():
    assert run("fail_text 1530") == "yhteysvirhe 15.30"


def test_log_line_format(tmp_path):
    import os
    import re

    log = tmp_path / "t.log"
    run("log hei", env={**os.environ, "LOG_FILE": str(log)})
    assert re.fullmatch(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d hei\n", log.read_text())


def test_log_rotates(tmp_path):
    import os

    log = tmp_path / "t.log"
    env = {**os.environ, "LOG_FILE": str(log), "LOG_MAX": "50"}
    for i in range(3):
        run(f"log rivi{i}-pitka-viesti", env=env)
    assert (tmp_path / "t.log.1").exists()
    assert log.stat().st_size < 50
