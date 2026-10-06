"""Python <-> JS parity for tier A properties, ceramics and the Omega check.

The browser core computes density, raw-material cost, the ceramics
descriptors and the Omega pair-table sensitivity instantly, without the
engine; this asserts they equal the Python library for every covered pure
element, a set of alloys (including rows a table cannot price), the
ceramics fixtures, and the MCP ``omega_sensitivity`` tool.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from hea_bench import ceramics
from hea_bench.mcp_server import omega_sensitivity
from hea_bench.descriptors.data.elemental import ELEMENTAL_DATA
from hea_bench.properties import cost_breakdown, cost_per_kg, density

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "tests" / "data" / "web_properties_parity_cases.json").read_text())
SNAPSHOT = ROOT / "tests" / "web_properties_snapshot.cjs"

DESCRIBE = {
    "rock_salt_carbide": ceramics.describe_rock_salt_carbide,
    "rock_salt_nitride": ceramics.describe_rock_salt_nitride,
    "diboride": ceramics.describe_diboride,
}


def _same(expected, actual, label: str) -> None:
    if isinstance(expected, dict):
        assert isinstance(actual, dict) and set(actual) == set(expected), f"{label}: keys differ"
        for key in expected:
            _same(expected[key], actual[key], f"{label}.{key}")
    elif isinstance(expected, (list, tuple)):
        assert len(actual) == len(expected), f"{label}: length differs"
        for index, (left, right) in enumerate(zip(expected, actual)):
            _same(left, right, f"{label}[{index}]")
    elif isinstance(expected, float) or (isinstance(expected, int) and not isinstance(expected, bool)):
        assert isinstance(actual, (int, float)), f"{label}: expected number, got {actual!r}"
        assert math.isclose(expected, actual, rel_tol=1e-12, abs_tol=1e-12), (
            f"{label}: {expected} vs {actual}"
        )
    else:
        assert expected == actual, f"{label}: {expected!r} vs {actual!r}"


def _breakdown(comp):
    try:
        return cost_breakdown(comp)
    except ValueError:
        return None


def test_browser_properties_and_ceramics_match_python(node_snapshot) -> None:
    js = node_snapshot(SNAPSHOT)
    expected = [{el: 1} for el in sorted(ELEMENTAL_DATA)] + CASES["alloys"]
    assert sorted(json.dumps(e["composition"], sort_keys=True) for e in js["properties"]) == sorted(
        json.dumps(comp, sort_keys=True) for comp in expected
    )
    for entry in js["properties"]:
        comp = entry["composition"]
        label = json.dumps(comp, sort_keys=True)
        _same(density(comp), entry["density"], f"density {label}")
        _same(cost_per_kg(comp), entry["cost_per_kg"], f"cost {label}")
        _same(_breakdown(comp), entry["cost_breakdown"], f"breakdown {label}")
    for case, report in zip(CASES["ceramics"], js["ceramics"], strict=True):
        _same(DESCRIBE[case["structure"]](case["metals"]), report, case["structure"])
    for case, report in zip(CASES["omega_sensitivity"], js["omega_sensitivity"], strict=True):
        expected = omega_sensitivity(case["formula"], case["perturbation"])
        # The MCP tool adds its own request echo and version stamp.
        assert set(expected) - set(report) == {"input", "hea_bench_version"}
        _same({key: expected[key] for key in report}, report, f"omega {case['formula']}")
