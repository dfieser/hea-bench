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
from hea_bench.descriptors.data.pair_enthalpies import missing_pairs as _missing_pairs

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
    # v2.1 expansion coverage: REHEA, nuclear, solder, HE-BMG, Ga/Ge alloys.
    {"name": "ygdtbdyho", "composition": {"Y": 1.0, "Gd": 1.0, "Tb": 1.0, "Dy": 1.0, "Ho": 1.0}},
    {"name": "gdtbdyhoer", "composition": {"Gd": 1.0, "Tb": 1.0, "Dy": 1.0, "Ho": 1.0, "Er": 1.0}},
    {"name": "gdtbdytmlu", "composition": {"Gd": 1.0, "Tb": 1.0, "Dy": 1.0, "Tm": 1.0, "Lu": 1.0}},
    {"name": "prndsmgdy", "composition": {"Pr": 1.0, "Nd": 1.0, "Sm": 1.0, "Gd": 1.0, "Y": 1.0}},
    {"name": "unbzrtimo", "composition": {"U": 1.0, "Nb": 1.0, "Zr": 1.0, "Ti": 1.0, "Mo": 1.0}},
    {"name": "nbtamowth", "composition": {"Nb": 1.0, "Ta": 1.0, "Mo": 1.0, "W": 1.0, "Th": 1.0}},
    {"name": "snpbinbisb", "composition": {"Sn": 1.0, "Pb": 1.0, "In": 1.0, "Bi": 1.0, "Sb": 1.0}},
    {"name": "srcaybmgzn", "composition": {"Sr": 1.0, "Ca": 1.0, "Yb": 1.0, "Mg": 1.0, "Zn": 1.0}},
    {"name": "cocrfeniga", "composition": {"Co": 1.0, "Cr": 1.0, "Fe": 1.0, "Ni": 1.0, "Ga": 1.0}},
    {"name": "cocrfenige", "composition": {"Co": 1.0, "Cr": 1.0, "Fe": 1.0, "Ni": 1.0, "Ge": 1.0}},
    {"name": "unbzrtimo_1200k", "composition": {"U": 1.0, "Nb": 1.0, "Zr": 1.0, "Ti": 1.0, "Mo": 1.0}, "king_temperature": 1200.0},
]


def _binary_cases() -> list[dict]:
    """One equiatomic binary case per (i, j) pair in the elemental table.

    The case name is ``binary_{a}_{b}`` with elements alphabetised so the
    JSON is stable across regenerations.
    """
    elements = sorted(_elemental())
    pair_covered = _pair()
    gaps = _missing_pairs(set(elements))
    out: list[dict] = []
    for a, b in combinations(elements, 2):
        if a not in pair_covered or b not in pair_covered:
            # Defensive: skip rather than crash if a future element
            # addition has no pair data at all.
            continue
        if frozenset((a, b)) in gaps:
            # The vendored table's known gap (Th-U): the Python library
            # raises for this pair by design, so it cannot be a parity
            # case; both surfaces document the gap instead.
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
