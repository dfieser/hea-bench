"""Element lookups that honour :func:`hea_bench.custom_data`.

Every descriptor reads per-element values through :func:`element` and
checks coverage with :func:`missing_elements`, so a custom element
defined in a ``custom_data`` block works everywhere the curated ones do.
Kept apart from ``data/elemental.py`` so that file, whose SHA-256 is part
of the published data fingerprint, changes only when the data does.
"""

from __future__ import annotations

from .. import _overrides
from .data.elemental import ELEMENTAL_DATA, ElementProperties, covered_elements


def element(symbol: str) -> ElementProperties:
    """One element's properties: a custom element's when one is active,
    the curated table's otherwise."""
    custom = _overrides.ELEMENTS.get()
    if custom and symbol in custom:
        return custom[symbol]
    return ELEMENTAL_DATA[symbol]


def missing_elements(composition_elements: set[str]) -> set[str]:
    """Elements in ``composition_elements`` with neither a table row nor a
    custom definition."""
    return composition_elements - covered_elements() - _overrides.custom_labels()
