"""The version single-source-of-truth stays consistent and round-trips.

These tests exercise tools/version.py directly (they do not import the
installed package), so they pass in any environment as long as the working
tree is internally consistent.
"""
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_PY = ROOT / "tools" / "version.py"


def _load():
    spec = importlib.util.spec_from_file_location("hb_version_tool", VERSION_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_check_passes_on_repo():
    r = subprocess.run(
        [sys.executable, str(VERSION_PY), "--check"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_all_targets_currently_agree():
    mod = _load()
    assert mod.check(mod.ROOT) == []


def test_roundtrip_set_on_copy(tmp_path):
    mod = _load()
    files = list(mod.VERSION_TARGETS) + ["src-tauri/tauri.conf.json"]
    for rel in files:
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(mod.ROOT / rel, dst)
    mod.set_version("9.9.9", tmp_path)
    assert mod.canonical(tmp_path) == "9.9.9"
    assert mod.check(tmp_path) == []
