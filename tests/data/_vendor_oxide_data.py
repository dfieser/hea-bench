"""Vendor the oxide-module element data from the installed pymatgen.

Extracts, for every element that has Shannon (1976) ionic radii in
pymatgen's compiled ``periodic_table.json.gz``:

- the full Shannon effective ionic radius table, nested as
  charge -> coordination (roman) -> spin ("" / "High Spin" / "Low Spin")
  -> ionic radius in angstroms (the effective radius on the
  r(O2-, VI) = 1.40 A scale; the crystal_radius variant is dropped),
- the "Common oxidation states" and "ICSD oxidation states" lists,
- the Pauling electronegativity ("X").

and writes ``src/hea_bench/oxides/data/oxide_elements.json``.

Run from the repo root:

    PYTHONPATH=src python tests/data/_vendor_oxide_data.py

The output is deterministic (sorted keys) so re-runs against the same
pymatgen version are byte-identical. The script asserts a set of
well-known values from the Shannon 1976 paper before writing anything;
a failed assertion means the upstream table changed and must be
re-reviewed, not silently re-vendored.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
from importlib.metadata import version

import pymatgen.core

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_PATH = os.path.join(REPO_ROOT, "src", "hea_bench", "oxides", "data", "oxide_elements.json")

# Hand-checked against Shannon (1976), Acta Cryst. A32, 751: effective
# ionic radii. (element, charge, CN, spin) -> angstroms.
INTEGRITY_PINS = [
    ("Mg", "2", "VI", "", 0.72),
    ("Sr", "2", "XII", "", 1.44),
    ("Ti", "4", "VI", "", 0.605),
    ("Zr", "4", "VIII", "", 0.84),
    ("Ce", "4", "VIII", "", 0.97),
    ("Mn", "4", "VI", "", 0.53),
    ("Co", "2", "VI", "High Spin", 0.745),
    ("O", "-2", "VI", "", 1.40),
]


def main() -> None:
    src = os.path.join(os.path.dirname(pymatgen.core.__file__), "periodic_table.json.gz")
    with gzip.open(src, "rt", encoding="utf-8") as fh:
        table = json.load(fh)

    out: dict[str, dict] = {}
    for el, props in table.items():
        if el.startswith("_"):  # metadata entries like "_unit"
            continue
        if el in ("D", "T"):  # hydrogen isotopes, not elements
            continue
        shannon = props.get("Shannon radii")
        if not shannon:
            continue
        radii = {}
        for charge, cns in shannon.items():
            try:
                int(charge)  # upstream has a malformed "" charge key on Eu; drop such rows
            except ValueError:
                continue
            radii[charge] = {
                cn: {spin: entry["ionic_radius"] for spin, entry in spins.items()}
                for cn, spins in cns.items()
            }
        out[el] = {
            "chi": props.get("X"),
            "common_oxidation_states": props.get("Common oxidation states", []),
            "icsd_oxidation_states": props.get("ICSD oxidation states", []),
            "shannon_radii": radii,
        }

    for el, charge, cn, spin, expected in INTEGRITY_PINS:
        got = out[el]["shannon_radii"][charge][cn][spin]
        assert abs(got - expected) < 1e-9, f"{el}{charge}+ {cn} {spin!r}: {got} != {expected}"

    payload = {
        "_provenance": {
            "source": "pymatgen periodic_table.json.gz (MIT license)",
            "pymatgen_version": version("pymatgen"),
            "upstream": "https://github.com/materialsproject/pymatgen",
            "radii_primary_source": "Shannon, Acta Cryst. A32, 751 (1976), effective ionic radii",
            "extracted_by": os.path.basename(__file__),
        },
        "elements": dict(sorted(out.items())),
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
        fh.write("\n")

    digest = hashlib.sha256(open(OUT_PATH, "rb").read()).hexdigest()
    print(f"wrote {OUT_PATH}")
    print(f"elements: {len(out)}")
    print(f"sha256: {digest}")


if __name__ == "__main__":
    main()
