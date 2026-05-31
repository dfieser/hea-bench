"""Regenerate ``web_parity_cases.json``.

The parity-test fixture lists every composition that the Python and
JavaScript implementations must agree on. The fixture exercises every
binary pair in the supported element table so the parity guarantee is
exhaustive across the calculator's element coverage. v1.1 introduced
this with 24 elements (276 binaries); v1.3 expands it to 30 elements
(435 binaries) after the JS browser core was brought to parity with
the v1.2 elemental-table additions (Au, Li, Mg, Re, Sn, Zn).

Run from the repo root::

    python tests/data/_build_parity_cases.py

The script is idempotent: every run produces the same JSON file given
the same property table.
"""

from __future__ import annotations

import json
import pathlib
from itertools import combinations

from hea_bench.descriptors.data.elemental import covered_elements as _elemental
from hea_bench.descriptors.data.pair_enthalpies import covered_elements as _pair

# Curated multi-element compositions kept from the earlier hand-built fixture.
# These exercise compositions of real scientific interest (Cantor, refractory,
# Senkov, the author's Langmuir paper) in addition to the exhaustive binaries.
_CURATED_CASES = [
    {"name": "cantor_default", "composition": {"Co": 1.0, "Cr": 1.0, "Fe": 1.0, "Mn": 1.0, "Ni": 1.0}},
    {"name": "cantor_1000k", "composition": {"Co": 1.0, "Cr": 1.0, "Fe": 1.0, "Mn": 1.0, "Ni": 1.0}, "king_temperature": 1000.0},
    {"name": "cocrfeni_default", "composition": {"Co": 1.0, "Cr": 1.0, "Fe": 1.0, "Ni": 1.0}},
    {"name": "alcocrfeni_default", "composition": {"Al": 1.0, "Co": 1.0, "Cr": 1.0, "Fe": 1.0, "Ni": 1.0}},
    {"name": "al03_cocrfeni", "composition": {"Al": 0.3, "Co": 1.0, "Cr": 1.0, "Fe": 1.0, "Ni": 1.0}},
    {"name": "cucomn175nife025", "composition": {"Cu": 1.0, "Co": 1.0, "Mn": 1.75, "Ni": 1.0, "Fe": 0.25}},
    {"name": "monbtaw", "composition": {"Mo": 1.0, "Nb": 1.0, "Ta": 1.0, "W": 1.0}},
    {"name": "hfnbtatizr", "composition": {"Hf": 1.0, "Nb": 1.0, "Ta": 1.0, "Ti": 1.0, "Zr": 1.0}},
    {"name": "alcocrcufeni", "composition": {"Al": 1.0, "Co": 1.0, "Cr": 1.0, "Cu": 1.0, "Fe": 1.0, "Ni": 1.0}},
    {"name": "cocrcufeni", "composition": {"Co": 1.0, "Cr": 1.0, "Cu": 1.0, "Fe": 1.0, "Ni": 1.0}},
]


def _binary_cases() -> list[dict]:
    """One equiatomic binary case per (i, j) pair in the elemental table.

    The case name is ``binary_{a}_{b}`` with elements alphabetised so the
    JSON is stable across regenerations.
    """
    elements = sorted(_elemental())
    pair_covered = _pair()
    out: list[dict] = []
    for a, b in combinations(elements, 2):
        if a not in pair_covered or b not in pair_covered:
            # Defensive: every covered pair is currently in matminer's
            # Miedema table, but skip rather than crash if that ever
            # changes (e.g. if a future element addition has no pair data).
            continue
        out.append(
            {
                "name": f"binary_{a}_{b}".lower(),
                "composition": {a: 1.0, b: 1.0},
            }
        )
    return out


def build_cases() -> list[dict]:
    """Build the full parity fixture (curated + every-binary)."""
    return [*_CURATED_CASES, *_binary_cases()]


def main() -> None:
    cases = build_cases()
    target = pathlib.Path(__file__).resolve().parent / "web_parity_cases.json"
    target.write_text(json.dumps(cases, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(cases)} cases to {target}")


if __name__ == "__main__":
    main()
