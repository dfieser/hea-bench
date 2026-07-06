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

import pytest

ROOT = Path(__file__).resolve().parent.parent
VERSION_PY = ROOT / "tools" / "version.py"


def _load():
    spec = importlib.util.spec_from_file_location("hb_version_tool", VERSION_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mirror(mod, tmp_path):
    """Copy every file check()/set_version() touch into a scratch tree."""
    files = list(mod.VERSION_TARGETS) + ["src-tauri/tauri.conf.json", ".zenodo.json"]
    for rel in files:
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(mod.ROOT / rel, dst)
    return tmp_path


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
    root = _mirror(mod, tmp_path)
    mod.set_version("9.9.9", root)
    assert mod.canonical(root) == "9.9.9"
    assert mod.check(root) == []


def test_set_requires_a_version_argument():
    r = subprocess.run([sys.executable, str(VERSION_PY), "--set"], capture_output=True, text=True)
    assert r.returncode != 0


def test_unknown_flag_is_rejected():
    r = subprocess.run([sys.executable, str(VERSION_PY), "--st", "9.9.9"], capture_output=True, text=True)
    assert r.returncode != 0


def test_set_fails_loudly_on_a_drifted_pattern(tmp_path):
    mod = _load()
    root = _mirror(mod, tmp_path)
    web = root / "web/index.html"
    web.write_text(web.read_text(encoding="utf-8").replace("const VERSION =", "const APP_VERSION ="), encoding="utf-8")
    with pytest.raises(SystemExit):
        mod.set_version("9.9.9", root)


def test_check_flags_author_parity_drift(tmp_path):
    mod = _load()
    root = _mirror(mod, tmp_path)
    zj = root / ".zenodo.json"
    # drop one creator's ORCID so .zenodo.json and CITATION.cff disagree
    text = zj.read_text(encoding="utf-8").replace("0009-0006-6400-9356", "0000-0000-0000-0000")
    zj.write_text(text, encoding="utf-8")
    assert any("ORCID" in p for p in mod.check(root))
