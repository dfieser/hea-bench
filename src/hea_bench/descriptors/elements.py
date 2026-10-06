"""The numbers behind the calculator, per element, with their sources.

The library side of the app's Element data tab: every tabulated value
the descriptors are computed from, its unit, where it comes from, the
places where good sources disagree, which features each element
supports, and the SHA-256 of the data files.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path

from .data.elemental import ELEMENTAL_DATA
from .data.mechanics import mechanics
from .data.pair_enthalpies import covered_elements as pair_table_elements
from .data.provenance import ELEMENT_SOURCES, PROPERTY_SOURCES, REFERENCES

_DATA_DIR = Path(__file__).resolve().parent / "data"
_DATA_FILES = ("elemental.py", "pair_enthalpies.tsv", "miedema_parameters.csv", "provenance.py")

UNITS = {
    "radius_pm": "pm",
    "melting_K": "K",
    "valence": "electrons",
    "electronegativity": "Pauling",
    "molar_volume_cm3": "cm^3/mol",
    "bulk_modulus_gpa": "GPa",
    "shear_modulus_gpa": "GPa",
}


@lru_cache(maxsize=1)
def _file_hashes() -> dict[str, str]:
    # LF line endings, as git stores the files, so a Windows checkout, the
    # wheel and the app's Element data tab all report the same hashes.
    return {
        name: hashlib.sha256((_DATA_DIR / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        for name in _DATA_FILES
    }


def _reference(key: str) -> dict:
    ref = REFERENCES[key]
    return {
        "authors": ref.authors,
        "title": ref.title,
        "venue": ref.venue,
        "year": ref.year,
        "doi": ref.doi or None,
        "url": ref.url or None,
    }


def element_data(elements: Iterable[str] | None = None) -> dict:
    """Tabulated values per element, with units, sources and coverage.

    Parameters
    ----------
    elements
        Symbols to report; all 55 curated elements when omitted. Unknown
        symbols raise ``ValueError`` naming them.

    Returns
    -------
    dict
        ``elements`` (symbol -> values, the radius source and its
        cross-check, notes and flags, and ``supports``: which features
        can use the element), ``units``, ``property_sources`` (one
        statement and its reference keys per column), ``references``
        (the cited keys only) and ``data_files`` (SHA-256 per file).
    """
    from .miedema_decomposition import MIEDEMA_CLASSES
    from ..oxides._data import OXIDE_ELEMENTS

    wanted = sorted(ELEMENTAL_DATA) if elements is None else list(elements)
    unknown = sorted(set(wanted) - set(ELEMENTAL_DATA))
    if unknown:
        raise ValueError(
            f"not in the 55-element table: {unknown}. hea_bench.custom_data defines "
            f"custom elements."
        )
    pair_elements = pair_table_elements()
    out = {}
    cited = set()
    for symbol in wanted:
        values = ELEMENTAL_DATA[symbol]
        sources = ELEMENT_SOURCES[symbol]
        mech = mechanics(symbol)
        cited.update(k for k in (sources.radius_source_key, sources.crosscheck_source_key) if k)
        out[symbol] = {
            "radius_pm": values.radius_pm,
            "melting_K": values.melting_K,
            "valence": values.valence,
            "electronegativity": values.electronegativity,
            "molar_volume_cm3": mech.molar_volume_cm3 if mech else None,
            "bulk_modulus_gpa": mech.bulk_modulus_gpa if mech else None,
            "shear_modulus_gpa": mech.shear_modulus_gpa if mech else None,
            "radius_source": sources.radius_source_key,
            "crosscheck_radius_pm": sources.crosscheck_radius_pm,
            "crosscheck_source": sources.crosscheck_source_key if sources.crosscheck_radius_pm else None,
            "crosscheck_note": sources.crosscheck_note or None,
            "notes": sources.notes or None,
            "flags": list(sources.flags),
            "supports": {
                "core_descriptors_and_rules": True,
                "mixing_enthalpy_pairs": symbol in pair_elements,
                "elastic_strain_energy": bool(
                    mech and mech.bulk_modulus_gpa > 0 and mech.molar_volume_cm3 > 0
                ),
                "miedema_decomposition": symbol in MIEDEMA_CLASSES,
                "oxide_cation": symbol in OXIDE_ELEMENTS,
            },
        }
    property_sources = {
        name: {"statement": source.statement, "sources": list(source.source_keys)}
        for name, source in PROPERTY_SOURCES.items()
    }
    for source in PROPERTY_SOURCES.values():
        cited.update(source.source_keys)
    return {
        "elements": out,
        "units": dict(UNITS),
        "property_sources": property_sources,
        "references": {key: _reference(key) for key in sorted(cited) if key in REFERENCES},
        "data_files": _file_hashes(),
    }


__all__ = ["element_data"]
