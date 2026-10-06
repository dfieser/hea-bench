"""The app works when a person uses it, tab by tab, in a real browser.

tests/app_smoke.cjs opens the built site (web/, with the engine from
tools/build_web_engine.py) in headless Chrome or Edge with a fresh
profile, a first-time visitor, and goes through every tab the way a user
does: the calculator in its three modes, the predictions panel (engine
start, dataset build, hardness, phase sets), the dataset tab with its CSV
and measured records, the benchmark tab (frozen digests, a live baseline,
the example predictions file uploaded and scored with the gap, the
coverage study), the design tab (search, experiment planning, campaign
file) and the typeset equations. Any uncaught error, console error or
failed load in the page or its engine worker fails the test. The engine's
Peivaste download is answered from the local file, so the run never
depends on the network.

Skips without Node 22+, a Chromium browser (or HEA_BENCH_BROWSER), the
engine build, or the Peivaste file, unless HEA_BENCH_REQUIRE_ENGINE=1
(set by the CI web-engine job), where a skip would hide a broken app and
fails instead.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

import hea_bench
from hea_bench import webapp

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "tests" / "app_smoke.cjs"
PEIVASTE = ROOT / "data" / "raw" / "peivaste" / "dataset11252_79.csv"
REQUIRED = os.environ.get("HEA_BENCH_REQUIRE_ENGINE") == "1"
BROWSERS = (
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "chrome",
    "msedge",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


def _skip(reason: str) -> None:
    if REQUIRED:
        pytest.fail(f"{reason} (HEA_BENCH_REQUIRE_ENGINE=1)")
    pytest.skip(reason)


def _browser() -> str | None:
    if os.environ.get("HEA_BENCH_BROWSER"):
        return os.environ["HEA_BENCH_BROWSER"]
    for name in BROWSERS:
        path = shutil.which(name) or (name if os.path.isfile(name) else None)
        if path:
            return path
    return None


def _free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _wait(what: str, check, seconds: float):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        value = check()
        if value:
            return value
        time.sleep(0.2)
    pytest.fail(f"timed out after {seconds:.0f} s waiting for {what}")


def _serving(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2):
            return True
    except OSError:
        return False


def test_every_tab_works_in_a_browser() -> None:
    node = shutil.which("node")
    browser = _browser()
    if node is None:
        _skip("Node.js not available")
    if browser is None:
        _skip("no Chrome, Chromium or Edge found; set HEA_BENCH_BROWSER")
    if not (ROOT / "web" / "engine" / "manifest.json").exists():
        _skip("engine not built; run python tools/build_web_engine.py")
    if not PEIVASTE.exists():
        _skip("Peivaste file missing; run python data/raw/peivaste/fetch.py")

    http_port = _free_port()
    app_url = f"http://127.0.0.1:{http_port}/"
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(http_port), "--bind", "127.0.0.1", "--directory", str(ROOT / "web")],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        args = [
            browser,
            "--headless=new",
            f"--user-data-dir={profile}",
            "--remote-debugging-port=0",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
            "--window-size=1280,900",
            "about:blank",
        ]
        if sys.platform.startswith("linux"):
            # Ubuntu 24.04 blocks the unprivileged namespaces Chrome's
            # sandbox needs; the page under test is our own local build.
            args += ["--no-sandbox", "--disable-dev-shm-usage"]
        chrome = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            _wait("the static server", lambda: _serving(app_url), 20)
            port_file = Path(profile) / "DevToolsActivePort"
            devtools = _wait(
                "the browser's DevTools port",
                lambda: port_file.exists() and port_file.read_text().split("\n")[0].strip(),
                60,
            )
            completed = subprocess.run(
                [node, str(DRIVER), devtools, app_url, str(PEIVASTE), webapp.peivaste_source()["url"], hea_bench.__version__],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=1800,
            )
        finally:
            chrome.terminate()
            server.terminate()
            chrome.wait(timeout=30)
            server.wait(timeout=30)

    check_report(completed, "the browser")


def check_report(completed: subprocess.CompletedProcess, where: str) -> None:
    """Fail on anything app_smoke.cjs saw go wrong; shared with the desktop test."""
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    print(json.dumps(result, indent=1, ensure_ascii=False))  # shown by pytest on failure
    if "skip" in result:
        _skip(result["skip"])
    assert "fatal" not in result, result.get("fatal")
    failed = [f"{s['name']}: {s['detail']}" for s in result["steps"] if not s["ok"]]
    assert not failed, f"steps failed in {where}:\n" + "\n".join(failed)
    assert result["peivaste_served"] >= 1, "the engine never requested the Peivaste file"
    assert not result["problems"], "the page reported errors:\n" + "\n".join(result["problems"])
