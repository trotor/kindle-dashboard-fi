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
