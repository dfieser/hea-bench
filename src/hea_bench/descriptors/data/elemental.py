"""Per-element physical properties used by descriptor computations.

Three properties are exposed for each element:

- ``radius_pm``  : atomic radius in picometres (metallic, 12-coordinated
                   where applicable; Pauling table values otherwise)
- ``melting_K``  : melting point in kelvin at 1 atm (CRC Handbook
                   reference values rounded to two decimals)
- ``valence``    : valence-electron count (s + d for transition metals,
                   following the convention used in Guo & Liu 2011 for
                   the VEC rule)

Coverage and limitations
------------------------

This table mirrors the 24-element set already battle-tested in the
legacy ``thermo-descriptor-calculator/validation/validate_rules.py``
work — every value here matches the legacy table byte-for-byte. The
empirical agreement with the legacy validator (Cantor alloy VEC = 8.0,
δ within the literature range, etc.) is the strongest available
ground truth.

The current 24 elements cover ≈ 670/740 of Borg's alloys and a similar
fraction of Pei / Peivaste, missing C, Sn, Mg, Zn, Li, B, Re, Ca, Sc,
Nd, Ga, and a handful of others that appear in the consolidated
benchmark. Expanding coverage is its own Phase 2 sub-step.

Adding an element
-----------------

Add a row below with a ``# source: <citation>`` comment. Prefer:

- CRC Handbook for melting points and atomic radii
- de Boer 1988 *Cohesion in Metals* for Miedema parameters (later phase)
- Standard textbooks for valence-electron counts

If multiple sources give different values, choose the one the HEA
literature most commonly uses and note the alternative in a comment.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ElementProperties:
    """Frozen per-element property bundle.

    Frozen-ness is enforced so that values can be safely shared at
    module scope without callers accidentally mutating them.
    """

    radius_pm: float
    melting_K: float
    valence: int


# 24 elements, alphabetically by symbol. Values mirror the legacy
# ELEMENT_DATA table from thermo-descriptor-calculator. Per-element
# provenance is the same legacy reference; do NOT alter individual
# numbers without paired tests.
ELEMENTAL_DATA: dict[str, ElementProperties] = {
    "Ag": ElementProperties(radius_pm=144.0, melting_K=1234.93, valence=11),
    "Al": ElementProperties(radius_pm=143.0, melting_K= 933.47, valence= 3),
    "Co": ElementProperties(radius_pm=125.0, melting_K=1768.00, valence= 9),
    "Cr": ElementProperties(radius_pm=129.0, melting_K=2180.00, valence= 6),
    "Cu": ElementProperties(radius_pm=128.0, melting_K=1357.77, valence=11),
    "Fe": ElementProperties(radius_pm=126.0, melting_K=1811.00, valence= 8),
    "Hf": ElementProperties(radius_pm=159.0, melting_K=2506.00, valence= 4),
    "Ir": ElementProperties(radius_pm=136.0, melting_K=2719.00, valence= 9),
    "Mn": ElementProperties(radius_pm=135.7, melting_K=1519.00, valence= 7),
    "Mo": ElementProperties(radius_pm=139.0, melting_K=2896.00, valence= 6),
    "Nb": ElementProperties(radius_pm=147.0, melting_K=2750.00, valence= 5),
    "Ni": ElementProperties(radius_pm=125.0, melting_K=1728.00, valence=10),
    "Os": ElementProperties(radius_pm=135.0, melting_K=3306.00, valence= 8),
    "Pd": ElementProperties(radius_pm=137.0, melting_K=1828.00, valence=10),
    "Pt": ElementProperties(radius_pm=139.0, melting_K=2041.40, valence=10),
    "Rh": ElementProperties(radius_pm=134.0, melting_K=2237.00, valence= 9),
    "Ru": ElementProperties(radius_pm=134.0, melting_K=2607.00, valence= 8),
    "Si": ElementProperties(radius_pm=111.0, melting_K=1687.00, valence= 4),
    "Ta": ElementProperties(radius_pm=147.0, melting_K=3290.00, valence= 5),
    "Ti": ElementProperties(radius_pm=147.0, melting_K=1941.00, valence= 4),
    "V":  ElementProperties(radius_pm=135.0, melting_K=2183.00, valence= 5),
    "W":  ElementProperties(radius_pm=141.0, melting_K=3695.00, valence= 6),
    "Y":  ElementProperties(radius_pm=182.0, melting_K=1799.00, valence= 3),
    "Zr": ElementProperties(radius_pm=160.0, melting_K=2128.00, valence= 4),
}


def covered_elements() -> set[str]:
    """Return the set of element symbols this table covers."""
    return set(ELEMENTAL_DATA)


def missing_elements(composition_elements: set[str]) -> set[str]:
    """Return any elements in ``composition_elements`` not in the table."""
    return composition_elements - covered_elements()
