"""Python <-> JS parity for the oxide module.

Runs every curated case in ``tests/data/web_oxide_parity_cases.json``
through both the Python ``hea_bench.oxides`` package and the JS core
(under Node), and asserts the full reports agree: numerics to rel
5e-4, and oxidation states, coordination, verdicts, and warning
strings exactly.
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

from hea_bench import oxides

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "tests" / "data" / "web_oxide_parity_cases.json"
NODE_SNAPSHOT_SCRIPT = ROOT / "tests" / "web_oxides_snapshot.cjs"


def _load_cases() -> list[dict]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


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


def _python_report(case: dict) -> dict:
    kwargs: dict = {}
    if "spin" in case:
        kwargs["spin"] = case["spin"]
    if "states" in case:
        kwargs["states"] = case["states"]
    family = case["family"]
    if family == "rock_salt":
        return oxides.describe_rock_salt(case["cations"], **kwargs)
    if family == "fluorite":
        if "oxygen" in case:
            kwargs["oxygen"] = case["oxygen"]
        return oxides.describe_fluorite(case["cations"], **kwargs)
    if family == "perovskite":
        return oxides.describe_perovskite(case["a_site"], case["b_site"], **kwargs)
    if family == "pyrochlore":
        return oxides.describe_pyrochlore(case["a_site"], case["b_site"], **kwargs)
    raise ValueError(f"unknown family: {family}")


def _js_snapshot() -> dict[str, dict]:
    node = _node_executable()
    if node is None:
        pytest.skip("Node.js executable not available for oxide parity snapshot")
    completed = subprocess.run(
        [node, str(NODE_SNAPSHOT_SCRIPT)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _assert_matches(expected, actual, label: str) -> None:
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{label}: expected dict, got {type(actual)}"
        assert set(actual) == set(expected), (
            f"{label}: key mismatch {sorted(actual)} vs {sorted(expected)}"
        )
        for key in expected:
            _assert_matches(expected[key], actual[key], f"{label}.{key}")
    elif isinstance(expected, list):
        assert actual == expected, f"{label}: expected {expected!r}, got {actual!r}"
    elif isinstance(expected, bool) or expected is None or isinstance(expected, str):
        assert actual == expected, f"{label}: expected {expected!r}, got {actual!r}"
    elif isinstance(expected, (int, float)):
        assert isinstance(actual, (int, float)), f"{label}: expected number, got {actual!r}"
        assert math.isclose(float(expected), float(actual), rel_tol=5e-4, abs_tol=5e-6), (
            f"{label}: expected {expected}, got {actual}"
        )
    else:  # pragma: no cover - fixture schema guard
        raise AssertionError(f"{label}: unhandled type {type(expected)}")


def test_browser_oxides_match_python() -> None:
    js_snapshot = _js_snapshot()
    cases = _load_cases()
    assert set(js_snapshot) == {case["name"] for case in cases}

    for case in cases:
        expected = _python_report(case)
        _assert_matches(expected, js_snapshot[case["name"]], case["name"])
