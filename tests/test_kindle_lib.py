import shlex
import subprocess

import pytest


def run(call, env=None):
    r = subprocess.run(
        ["sh", "-c", f". kindle/saa-ja-sahko/lib.sh; {call}"],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


@pytest.mark.parametrize("h,m,s", [
    (5, 30, "1800"), (4, 0, "7200"), (23, 0, "7200"), (5, 59, "60"), (14, 0, "1800"),
    ("08", "09", "1800"), ("05", "08", "3120"), ("00", "00", "7200"), (6, 0, "1800"),
    (22, 59, "1800"),
])
def test_sleep_seconds(h, m, s):
    assert run(f"sleep_seconds {h} {m}") == s


@pytest.mark.parametrize("url,host", [
    ("http://192.168.0.157:8088/kindle.png", "192.168.0.157"),
    ("http://mac.local/x.png", "mac.local"),
    ("https://user@mac.local:8443", "mac.local"),
    ("192.168.0.157", ""),
    ("ei osoite", ""),
    ("http://", ""),
    ("", ""),
])
def test_host_from_url(url, host):
    assert run(f"host_from_url {shlex.quote(url)}") == host


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
