"""Loader for the vendored oxide element table.

``data/oxide_elements.json`` is extracted from pymatgen's compiled
periodic table (MIT license) by ``tests/data/_vendor_oxide_data.py``.
Per element it carries the Shannon (1976) effective ionic radii
(charge -> coordination -> spin -> angstroms, on the r(O2-, VI) = 1.40 A
scale), the common and ICSD-observed oxidation states, and the Pauling
electronegativity. See ``data/README.md`` for provenance and the
SHA-256 pin.
"""

from __future__ import annotations

import json
from pathlib import Path

_DATA_PATH = Path(__file__).parent / "data" / "oxide_elements.json"

with open(_DATA_PATH, encoding="utf-8") as _fh:
    _PAYLOAD = json.load(_fh)

#: element symbol -> {"chi", "common_oxidation_states",
#: "icsd_oxidation_states", "shannon_radii"}
OXIDE_ELEMENTS: dict[str, dict] = _PAYLOAD["elements"]


def missing_oxide_elements(symbols: set[str]) -> set[str]:
    """Subset of ``symbols`` absent from the vendored oxide element table."""
    return {s for s in symbols if s not in OXIDE_ELEMENTS}
