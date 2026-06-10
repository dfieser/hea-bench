"""Regenerate the JS core's element and pair tables from the Python data.

The Python library's ``ELEMENTAL_DATA`` and pair-enthalpy table are the
source of truth. This script rewrites the ``DEFAULT_ELEMENT_DATA`` and
``PAIR_ENTHALPIES`` blocks (and their lead comments) inside
``web/hea-calculator-core.js`` so the JS core carries byte-identical
values for every covered element and every binary pair. Run it after any
element-table change, then regenerate the parity fixture and run
``tests/test_web_parity.py``.

Run from the repo root::

    PYTHONPATH=src python tests/data/_sync_js_tables.py
"""

from __future__ import annotations

import pathlib
import re
from itertools import combinations

from hea_bench.descriptors.data.elemental import ELEMENTAL_DATA
from hea_bench.descriptors.data.pair_enthalpies import pair_enthalpy

CORE = pathlib.Path(__file__).resolve().parents[2] / "web" / "hea-calculator-core.js"


def _num(value: float | int) -> str:
    """Format a number the way the JS file writes it (floats keep .0)."""
    if isinstance(value, int):
        return str(value)
    return repr(float(value))


def element_block() -> str:
    lines = []
    for sym in sorted(ELEMENTAL_DATA):
        d = ELEMENTAL_DATA[sym]
        lines.append(
            f"      {sym}: {{ radius: {_num(float(d.radius_pm))}, "
            f"melting: {_num(float(d.melting_K))}, valence: {int(d.valence)}, "
            f"chi: {_num(float(d.electronegativity))} }}"
        )
    return ",\n".join(lines)


def pair_block() -> str:
    lines = []
    for a, b in combinations(sorted(ELEMENTAL_DATA), 2):
        v = pair_enthalpy(a, b)
        lines.append(f'      "{a}|{b}": {_num(float(v))}')
    return ",\n".join(lines)


def main() -> None:
    n = len(ELEMENTAL_DATA)
    n_pairs = n * (n - 1) // 2
    text = CORE.read_text(encoding="utf-8")

    elem_comment = (
        f"    // {n}-element coverage (atomic radius, melting point, valence,\n"
        f"    // Pauling electronegativity).\n"
        f"    // Generated from the Python library's ELEMENTAL_DATA by\n"
        f"    // tests/data/_sync_js_tables.py — do not edit by hand; the\n"
        f"    // parity test asserts the two tables agree.\n"
    )
    pair_comment = (
        f"    // {n_pairs} pairs = C({n}, 2). Matminer-derived Miedema binary mixing\n"
        f"    // enthalpies for the {n} elements covered by ELEMENTAL_DATA.\n"
        f"    // Generated from the Python pair table by tests/data/_sync_js_tables.py.\n"
    )

    text, n1 = re.subn(
        r"(?s)    //[^\n]*\n(?:    //[^\n]*\n)*    var DEFAULT_ELEMENT_DATA = \{.*?\n    \};",
        elem_comment + "    var DEFAULT_ELEMENT_DATA = {\n" + element_block() + "\n    };",
        text,
        count=1,
    )
    text, n2 = re.subn(
        r"(?s)    //[^\n]*\n(?:    //[^\n]*\n)*    var PAIR_ENTHALPIES = \{.*?\n    \};",
        pair_comment + "    var PAIR_ENTHALPIES = {\n" + pair_block() + "\n    };",
        text,
        count=1,
    )
    if n1 != 1 or n2 != 1:
        raise SystemExit(f"block replacement failed (element={n1}, pair={n2})")

    CORE.write_text(text, encoding="utf-8", newline="\n")
    print(f"synced {CORE.name}: {n} elements, {n_pairs} pairs")


if __name__ == "__main__":
    main()
