"""The app's in-browser engine computes exactly what CPython computes.

Runs the vendored engine (web/engine/, the Pyodide runtime, wheels and
package zip the app ships) under Node through hea_bench.webapp, the same
way hea-engine-worker.js does, and compares every call in
tests/data/web_engine_calls.json with CPython. Pyodide ships
scikit-learn 1.7.0 where the library pins 1.7.2, so this is also the
proof that the two give the same forests.

Skips without Node or the engine build, unless
HEA_BENCH_REQUIRE_ENGINE=1 (set by the CI web-engine job), where a skip
would hide a broken app and fails instead.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import pytest

from hea_bench import webapp

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "tests" / "web_engine_snapshot.cjs"
CALLS = json.loads((ROOT / "tests" / "data" / "web_engine_calls.json").read_text(encoding="utf-8"))
REQUIRED = os.environ.get("HEA_BENCH_REQUIRE_ENGINE") == "1"
#: Keys whose values legitimately differ between the two runtimes.
VOLATILE = {"hea_bench_version", "python", "scikit_learn"}


def _skip(reason: str) -> None:
    if REQUIRED:
        pytest.fail(f"{reason} (HEA_BENCH_REQUIRE_ENGINE=1)")
    pytest.skip(reason)


def _same(expected, actual, label: str) -> None:
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{label}: expected an object, got {actual!r}"
        keys = set(expected) - VOLATILE
        assert keys == set(actual) - VOLATILE, f"{label}: keys {sorted(keys ^ (set(actual) - VOLATILE))} differ"
        for key in keys:
            _same(expected[key], actual[key], f"{label}.{key}")
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(actual) == len(expected), f"{label}: list differs"
        for index, (left, right) in enumerate(zip(expected, actual)):
            _same(left, right, f"{label}[{index}]")
    elif isinstance(expected, float) and isinstance(actual, (int, float)):
        assert math.isclose(expected, actual, rel_tol=1e-9, abs_tol=1e-12), f"{label}: {expected} vs {actual}"
    else:
        assert expected == actual, f"{label}: {expected!r} vs {actual!r}"


def test_engine_matches_cpython(node_snapshot) -> None:
    if not (ROOT / "web" / "engine" / "manifest.json").exists():
        _skip("engine not built; run python tools/build_web_engine.py")
    js = node_snapshot(SNAPSHOT)
    for entry in CALLS:
        expected = json.loads(webapp.call(entry["method"], json.dumps(entry["params"])))
        _same(expected, js["results"][entry["name"]], entry["name"])
