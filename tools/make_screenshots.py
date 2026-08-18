#!/usr/bin/env python3
"""Capture the README screenshots of the web app, light and dark.

Screenshots rot: the UI moves, the numbers change, and a hand-captured
PNG quietly becomes a picture of software that no longer exists. This
script re-captures them from the current web/ sources in one command, so
refreshing them is never a reason to open a screenshot tool::

    python tools/make_screenshots.py

Serves web/ on a scratch port, drives the calculator to a real result
for the canonical Cantor alloy, and writes the light and dark pair that
docs/assets feeds to the README's <picture> elements.

Needs Playwright (``pip install playwright && playwright install
chromium``). tools/preflight.py checks the outputs exist and are the
right shape, but does not re-run this, because CI has no browser.
"""

from __future__ import annotations

import contextlib
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "docs" / "assets"

#: The Cantor alloy: the single most recognisable HEA composition, so a
#: reader knows at a glance what they are looking at.
COMPOSITION = "CoCrFeMnNi"

VIEWPORT = {"width": 1360, "height": 900}
SCALE = 2  # emit at 2x so the shot stays sharp on a high-density display

DRIVE_CALCULATOR = """() => {
    const f = document.getElementById('formula-input');
    f.value = %r;
    f.dispatchEvent(new Event('input', {bubbles: true}));
    document.getElementById('parse-formula').click();
    document.getElementById('calculate').click();
}""" % COMPOSITION


def _free_port() -> int:
    with contextlib.closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit(
            "screenshots need Playwright; run: python -m pip install playwright "
            "&& python -m playwright install chromium"
        )

    ASSETS.mkdir(parents=True, exist_ok=True)
    port = _free_port()
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "-d", str(ROOT / "web")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1.5)
    written = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for theme in ("light", "dark"):
                page = browser.new_page(viewport=VIEWPORT, device_scale_factor=SCALE)
                # The app is hash-routed; #calculator is the view, not the landing page.
                page.goto(f"http://localhost:{port}/#calculator", wait_until="networkidle")
                page.evaluate(
                    "t => document.documentElement.setAttribute('data-theme', t)", theme
                )
                page.evaluate(DRIVE_CALCULATOR)
                page.wait_for_timeout(1400)  # let MathJax and the result render settle
                out = ASSETS / f"screenshot-calculator-{theme}.png"
                page.screenshot(path=out)
                written.append(out.name)
                page.close()
            browser.close()
    finally:
        server.terminate()

    print(f"wrote {', '.join(written)} to {ASSETS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
