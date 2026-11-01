import os
import subprocess


def deploy(vol, *args):
    r = subprocess.run(
        ["scripts/deploy-kindle.sh", *args],
        capture_output=True, text=True, env={**os.environ, "KINDLE_VOLUME": str(vol)},
    )
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_deploy_skips_and_removes_dev_scriptlet(tmp_path):
    docs = tmp_path / "documents"
    docs.mkdir()
    (docs / "kehitysyhteys.sh").write_text("vanha")
    out = deploy(tmp_path)
    assert (docs / "saa-ja-sahko.sh").exists()
    assert not (docs / "kehitysyhteys.sh").exists()
    assert "kehitysyhteys.sh" in out
    assert (tmp_path / "saa-ja-sahko" / "dash.sh").exists()


def test_deploy_dev_copies_dev_scriptlet(tmp_path):
    deploy(tmp_path, "--dev")
    assert (tmp_path / "documents" / "kehitysyhteys.sh").exists()
    assert (tmp_path / "documents" / "saa-ja-sahko.sh").exists()


def test_deploy_rejects_unknown_argument(tmp_path):
    r = subprocess.run(
        ["scripts/deploy-kindle.sh", "--kehitys"],
        capture_output=True, text=True, env={**os.environ, "KINDLE_VOLUME": str(tmp_path)},
    )
    assert r.returncode == 2
    assert not (tmp_path / "documents").exists()


def test_install_service_print_fills_template():
    r = subprocess.run(
        ["scripts/install-mac-service.sh", "--print"],
        capture_output=True, text=True, env={**os.environ, "UV": "/x/uv"},
    )
    assert r.returncode == 0, r.stderr
    assert "__" not in r.stdout
    assert "<string>/x/uv</string>" in r.stdout
    assert f"<string>{os.getcwd()}</string>" in r.stdout
    assert "Library/Logs/saasahko.log" in r.stdout


def test_deploy_writes_conf_with_mac_ip(tmp_path):
    r = subprocess.run(
        ["scripts/deploy-kindle.sh"],
        capture_output=True, text=True,
        env={**os.environ, "KINDLE_VOLUME": str(tmp_path), "MAC_IP": "10.1.2.3"},
    )
    assert r.returncode == 0, r.stderr
    conf = (tmp_path / "saa-ja-sahko.conf").read_text()
    assert "URL=http://10.1.2.3:8088/kindle.png" in conf


def test_deploy_keeps_existing_conf(tmp_path):
    (tmp_path / "saa-ja-sahko.conf").write_text("URL=http://oma/k.png\n")
    deploy(tmp_path)
    assert (tmp_path / "saa-ja-sahko.conf").read_text() == "URL=http://oma/k.png\n"
