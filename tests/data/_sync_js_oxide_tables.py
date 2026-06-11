"""Regenerate the OXIDE_ELEMENT_DATA block in web/hea-calculator-core.js.

Reads the vendored ``src/hea_bench/oxides/data/oxide_elements.json``
(the single source of truth, itself extracted from pymatgen by
``_vendor_oxide_data.py``) and rewrites the generated block between the
``BEGIN/END GENERATED: OXIDE_ELEMENT_DATA`` markers in the JS core, so
the Python and JS oxide surfaces cannot drift.

Coordination keys are converted from roman numerals to integers here
(only the standard I..XIV keys are emitted, matching the Python
runtime's filtering of square-planar/pyramidal variants); oxidation
states and spin labels are kept verbatim.

Run from the repo root:

    PYTHONPATH=src python tests/data/_sync_js_oxide_tables.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "src" / "hea_bench" / "oxides" / "data" / "oxide_elements.json"
CORE_PATH = ROOT / "web" / "hea-calculator-core.js"

ROMAN_TO_INT = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7,
    "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12, "XIII": 13, "XIV": 14,
}


def _num(value: float) -> str:
    return json.dumps(value)


def _element_line(symbol: str, entry: dict) -> str:
    chi = "null" if entry["chi"] is None else _num(entry["chi"])
    common = "[" + ", ".join(str(q) for q in entry["common_oxidation_states"]) + "]"
    icsd = "[" + ", ".join(str(q) for q in entry["icsd_oxidation_states"]) + "]"

    charge_parts = []
    for charge in sorted(entry["shannon_radii"], key=int):
        cns = entry["shannon_radii"][charge]
        cn_parts = []
        for cn_key in sorted((k for k in cns if k in ROMAN_TO_INT), key=ROMAN_TO_INT.get):
            spins = cns[cn_key]
            spin_parts = ", ".join(
                f'{json.dumps(spin)}: {_num(spins[spin])}' for spin in sorted(spins)
            )
            cn_parts.append(f'"{ROMAN_TO_INT[cn_key]}": {{ {spin_parts} }}')
        if cn_parts:
            charge_parts.append(f'"{charge}": {{ {", ".join(cn_parts)} }}')
    radii = "{ " + ", ".join(charge_parts) + " }"
    return f"      {symbol}: {{ chi: {chi}, common: {common}, icsd: {icsd}, radii: {radii} }}"


def main() -> None:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    elements = payload["elements"]
    provenance = payload["_provenance"]

    lines = [_element_line(sym, elements[sym]) for sym in sorted(elements)]
    block = (
        f"    // {len(elements)}-element oxide table: Pauling electronegativity,\n"
        f"    // common/ICSD oxidation states, and Shannon (1976) effective ionic\n"
        f"    // radii (angstroms) nested as charge -> coordination number -> spin.\n"
        f"    // Generated from the Python library's vendored oxide_elements.json\n"
        f"    // (pymatgen {provenance['pymatgen_version']}, MIT) by\n"
        f"    // tests/data/_sync_js_oxide_tables.py — do not edit by hand; the\n"
        f"    // oxide parity test asserts the two implementations agree.\n"
        f"    var OXIDE_ELEMENT_DATA = {{\n" + ",\n".join(lines) + "\n    };"
    )

    core = CORE_PATH.read_text(encoding="utf-8")
    pattern = re.compile(
        r"    // BEGIN GENERATED: OXIDE_ELEMENT_DATA\n.*?\n    // END GENERATED: OXIDE_ELEMENT_DATA",
        re.DOTALL,
    )
    replacement = (
        "    // BEGIN GENERATED: OXIDE_ELEMENT_DATA\n"
        + block
        + "\n    // END GENERATED: OXIDE_ELEMENT_DATA"
    )
    new_core, count = pattern.subn(lambda _m: replacement, core)
    if count != 1:
        raise SystemExit(f"expected exactly one OXIDE_ELEMENT_DATA block, found {count}")
    CORE_PATH.write_text(new_core, encoding="utf-8", newline="\n")
    print(f"wrote OXIDE_ELEMENT_DATA ({len(elements)} elements) into {CORE_PATH}")


if __name__ == "__main__":
    main()
