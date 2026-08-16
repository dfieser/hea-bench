"""Shared pytest fixtures for the test suite."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _node_executable() -> str | None:
    path = shutil.which("node")
    if path:
        return path
    try:
        import nodejs  # type: ignore
    except ImportError:
        return None
    candidate = getattr(nodejs, "path", None)
    return str(candidate) if candidate else None


@pytest.fixture
def node_snapshot():
    """Run a .cjs snapshot script under Node and return its JSON output.

    The web parity suites drive the browser core headlessly through
    these scripts; the fixture skips the calling test when no Node.js
    runtime is available (PATH or the optional nodejs wheel).
    """

    def run(script: Path) -> dict:
        node = _node_executable()
        if node is None:
            pytest.skip("Node.js executable not available for parity snapshot")
        completed = subprocess.run(
            [node, str(script)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            # Node writes UTF-8 regardless of the console codepage; without
            # this, non-ASCII warning text mojibakes under Windows cp1252.
            encoding="utf-8",
        )
        return json.loads(completed.stdout)

    return run
