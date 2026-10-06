"""Regression coverage for the JS core's Miedema decomposition.

The SS/amorphous/compound decomposition has no Python counterpart (it is
a web-surface feature), so this is a pinned-value regression suite
rather than a Python parity test: the values below were computed from
the generated MIEDEMA_TABLE (vendored matminer Miedema.csv) at the
moment the decomposition moved into the core, and any change to the
table, the sync script, or the formulas must show up here.
"""

from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE_SNAPSHOT_SCRIPT = ROOT / "tests" / "web_miedema_snapshot.cjs"

#: Elements carrying a Miedema decomposition row (the curated class map
#: in tests/data/_sync_js_tables.py drives this count).
EXPECTED_TABLE_SIZE = 37

#: case -> section -> field -> pinned value (kJ/mol).
EXPECTED = {
    "cantor": {
        "compound": {"H_form": -15.491564372803719},
        "solidSolution": {
            "H_chem": -4.1378908512607016,
            "H_elast": 0.1541029309904455,
            "H_struct": -5.499999999999997,
            "H_total": -9.483787920270252,
        },
        "amorphous": {
            "H_chem": -4.1378908512607016,
            "H_topo": 25.2168,
            "H_total": 21.0789091487393,
        },
    },
    "al_cocrfeni": {
        "compound": {"H_form": -69.44085396951897},
        "solidSolution": {
            "H_chem": -18.95464491454676,
            "H_elast": 1.3467407415192663,
            "H_struct": -12.799999999999999,
            "H_total": -30.40790417302749,
        },
        "amorphous": {
            "H_chem": -18.95464491454676,
            "H_topo": 23.577316000000003,
            "H_total": 4.622671085453245,
        },
    },
    "cu_zr": {
        "compound": {"H_form": -30.78018257439789},
        "solidSolution": {
            "H_chem": -22.292416482868795,
            "H_elast": 18.506888962784934,
            "H_struct": -4.25,
            "H_total": -8.03552752008386,
        },
        "amorphous": {
            "H_chem": -22.292416482868795,
            "H_topo": 6.1000974999999995,
            "H_total": -16.192318982868795,
        },
    },
    "ti_al": {
        "compound": {"H_form": -60.68504146638662},
        "solidSolution": {
            "H_chem": -40.48051274809574,
            "H_elast": 0.11674205528331663,
            "H_struct": -1.5,
            "H_total": -41.86377069281242,
        },
        "amorphous": {
            "H_chem": -40.48051274809574,
            "H_topo": 5.0303225000000005,
            "H_total": -35.45019024809574,
        },
    },
    "ni_si": {
        "compound": {"H_form": -26.452645260736837},
        "solidSolution": {
            "H_chem": -26.455054266837475,
            "H_elast": 2.3131499308857983,
            "H_struct": -6.875,
            "H_total": -31.016904335951676,
        },
        "amorphous": {
            "H_chem": -26.455054266837475,
            "H_topo": 6.012125,
            "H_total": -20.442929266837474,
        },
    },
    "refractory": {
        "compound": {"H_form": 9.91631216464374},
        "solidSolution": {
            "H_chem": 2.666299310788083,
            "H_elast": 1.3403903280807967,
            "H_struct": -41.2,
            "H_total": -37.193310361131125,
        },
        "amorphous": {
            "H_chem": 2.666299310788083,
            "H_topo": 35.322,
            "H_total": 37.988299310788086,
        },
    },
}

EXPECTED_CU_ZR_DETAILS = {
    "gammaAB": -19.722087321425345,
    "H_inter_AinB": -78.1010101071196,
    "H_inter_BinA": -109.9789242900414,
    "P": 14.2,
    "Q": 133.48,
    "R_val": 0,
}


def _assert_close(expected: float, actual: float, label: str) -> None:
    assert math.isclose(expected, actual, rel_tol=1e-9, abs_tol=1e-12), (
        f"{label}: expected {expected}, got {actual}"
    )


def test_miedema_decomposition_matches_pinned_values(node_snapshot) -> None:
    snapshot = node_snapshot(NODE_SNAPSHOT_SCRIPT)
    assert snapshot["table_size"] == EXPECTED_TABLE_SIZE

    for case, sections in EXPECTED.items():
        actual = snapshot["cases"][case]
        assert actual["warnings"] == [], f"{case}: unexpected warnings"
        for section, fields in sections.items():
            for field, expected in fields.items():
                _assert_close(expected, actual[section][field], f"{case}.{section}.{field}")

    details = snapshot["cu_zr_details"]
    assert details["pairType"] == "TM-TM"
    for field, expected in EXPECTED_CU_ZR_DETAILS.items():
        _assert_close(expected, details[field], f"cu_zr_details.{field}")


def test_uncovered_element_degrades_with_warning_not_silence(node_snapshot) -> None:
    snapshot = node_snapshot(NODE_SNAPSHOT_SCRIPT)
    result = snapshot["cases"]["with_uncovered"]
    assert result["compound"] is None
    assert result["solidSolution"] is None
    assert result["amorphous"] is None
    assert len(result["warnings"]) == 1
    warning = result["warnings"][0]
    assert "2 element pairs lack Miedema parameters" in warning
    assert "Bi–Co" in warning and "Bi–Ni" in warning


#: The snapshot's compositions, for the Python implementation.
PYTHON_CASES = {
    "cantor": {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2},
    "al_cocrfeni": {"Al": 0.2, "Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Ni": 0.2},
    "cu_zr": {"Cu": 0.5, "Zr": 0.5},
    "ti_al": {"Ti": 0.5, "Al": 0.5},
    "ni_si": {"Ni": 0.75, "Si": 0.25},
    "refractory": {"Hf": 0.2, "Nb": 0.2, "Ta": 0.2, "Ti": 0.2, "Zr": 0.2},
}
_PY_SECTION = {"compound": "compound", "solidSolution": "solid_solution", "amorphous": "amorphous"}


def test_python_decomposition_matches_the_same_pinned_values() -> None:
    """Four-surface parity: the library, and so the MCP server, compute what the app shows."""
    from hea_bench.descriptors.miedema_decomposition import (
        MIEDEMA_CLASSES,
        miedema_decomposition,
        pair_details,
    )

    assert len(MIEDEMA_CLASSES) == EXPECTED_TABLE_SIZE
    for case, sections in EXPECTED.items():
        actual = miedema_decomposition(PYTHON_CASES[case])
        assert actual["warnings"] == [], f"{case}: unexpected warnings"
        for section, fields in sections.items():
            for field, expected in fields.items():
                _assert_close(expected, actual[_PY_SECTION[section]][field], f"python {case}.{section}.{field}")
    details = pair_details("Cu", "Zr")
    assert details["pairType"] == "TM-TM"
    for field, expected in EXPECTED_CU_ZR_DETAILS.items():
        _assert_close(expected, details[field], f"python cu_zr_details.{field}")


def test_python_decomposition_degrades_like_the_app() -> None:
    from hea_bench.descriptors.miedema_decomposition import miedema_decomposition

    result = miedema_decomposition({"Bi": 0.2, "Co": 0.4, "Ni": 0.4})
    assert result["compound"] is None and result["solid_solution"] is None and result["amorphous"] is None
    assert len(result["warnings"]) == 1
    assert "2 element pairs lack Miedema parameters" in result["warnings"][0]
    assert "Bi–Co" in result["warnings"][0] and "Bi–Ni" in result["warnings"][0]
