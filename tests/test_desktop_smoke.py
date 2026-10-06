"""The desktop exe runs the whole app, engine included, tab by tab.

The exe is the site's web/ folder in a Tauri (WebView2) window, so this
runs the same steps as tests/test_app_smoke.py inside the real exe: it
starts the exe with WebView2's DevTools port open and an empty profile
folder (a first-time user), attaches tests/app_smoke.cjs to the page the
exe shows, and uses every tab, the in-page engine and its corpus build
included. Any step that fails, and any error in the page or its engine
worker, fails the test.

Opt-in, Windows only: HEA_BENCH_DESKTOP_EXE=<path to the built exe>. The
release workflow's desktop-build job sets it right after building, so a
broken exe opens the desktop-build issue instead of being attached to
the release.
"""

from __future__ import annotations

import contextlib
import ctypes
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

import pytest

import hea_bench
from hea_bench import webapp

from .test_app_smoke import DRIVER, PEIVASTE, _free_port, check_report

EXE = os.environ.get("HEA_BENCH_DESKTOP_EXE")

pytestmark = pytest.mark.skipif(
    not EXE, reason="opt-in: set HEA_BENCH_DESKTOP_EXE to the built exe (Windows)"
)


def _devtools_ready(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2):
            return True
    except OSError:
        return False


# WebView2 ignores WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS and the per-user
# policy when the exe runs elevated, as on GitHub's Windows runners, but
# honors this machine-wide policy, keyed by the exe's file name:
# https://learn.microsoft.com/microsoft-edge/webview2/concepts/security
POLICY = r"Software\Policies\Microsoft\Edge\WebView2\AdditionalBrowserArguments"


@contextlib.contextmanager
def _machine_policy(exe_name: str, browser_args: str):
    """Sets the machine-wide browser arguments for the exe while elevated,
    and removes them afterwards. Not elevated, the variable alone works."""
    if not ctypes.windll.shell32.IsUserAnAdmin():
        yield
        return
    import winreg

    with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, POLICY) as key:
        winreg.SetValueEx(key, exe_name, 0, winreg.REG_SZ, browser_args)
    try:
        yield
    finally:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, POLICY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, exe_name)


def _webview_processes() -> str:
    """The running WebView2 processes' command lines, for a failure message:
    they show whether the browser started and which arguments reached it."""
    query = (
        "Get-CimInstance Win32_Process -Filter \"Name='msedgewebview2.exe'\" | "
        "ForEach-Object { $_.CommandLine }"
    )
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", query],
            capture_output=True, text=True, timeout=60,
        ).stdout
    except (OSError, subprocess.SubprocessError) as error:
        return f"(could not list them: {error})"
    lines = [line.strip()[:400] for line in out.splitlines() if line.strip()]
    return "\n".join(lines[:4]) or "(none running)"


def test_every_tab_works_in_the_desktop_exe(tmp_path) -> None:
    node = shutil.which("node")
    assert node, "Node.js 22 or newer is needed to drive the exe"
    assert Path(EXE).is_file(), f"no exe at {EXE}"
    assert PEIVASTE.exists(), "run python data/raw/peivaste/fetch.py first"
    port = _free_port()
    # The app fetches the Peivaste file at launch, before the driver can
    # hook the page. Failing that host's DNS makes the launch fetch fail as
    # it would offline; the driver then reloads the hooked page and answers
    # the second fetch from the local file.
    browser_args = (
        f"--remote-debugging-port={port} "
        '--host-resolver-rules="MAP raw.githubusercontent.com ~NOTFOUND"'
    )
    env = dict(
        os.environ,
        WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=browser_args,
        WEBVIEW2_USER_DATA_FOLDER=str(tmp_path / "profile"),
    )
    with _machine_policy(Path(EXE).name, browser_args):
        app = subprocess.Popen([EXE], env=env)
        try:
            until = time.monotonic() + 120
            while not _devtools_ready(port):
                if app.poll() is not None:
                    pytest.fail(f"the exe exited with code {app.returncode} before opening its DevTools port")
                if time.monotonic() > until:
                    pytest.fail(
                        "timed out after 120 s waiting for the exe's DevTools port. "
                        f"WebView2 processes:\n{_webview_processes()}"
                    )
                time.sleep(0.2)
            completed = subprocess.run(
                [node, str(DRIVER), str(port), "attach", str(PEIVASTE), webapp.peivaste_source()["url"],
                 hea_bench.__version__],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=1800,
            )
        finally:
            app.kill()
            app.wait(timeout=30)
    check_report(completed, "the desktop exe")
