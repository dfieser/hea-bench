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

The original 24 elements mirror the set battle-tested in the legacy
``thermo-descriptor-calculator/validation/validate_rules.py`` work;
every original value matches the legacy table byte-for-byte. The
empirical agreement with the legacy validator (Cantor alloy VEC = 8.0,
δ within the literature range, etc.) is the strongest available
ground truth. The original radii follow the Goldschmidt
12-coordinate metallic-radius convention (verified against
Housecroft & Sharpe, *Inorganic Chemistry*, Appendix 6: Al 143,
Ti 147, V 135, Cr 129, Fe 126, Co 125, Ni 125, Cu 128 all match).

v1.2 expands the table from 24 to 30 elements by adding Mg, Zn, Sn,
Re, Au, and Li. These six are well-defined metallic elements; their
radii are sourced from the same Goldschmidt CN12 convention as the
original 24 (see per-element comments). This lifts scorable coverage
of the consolidated benchmark from 86.7 % to 90.2 %.

B and C are deliberately **not** added. Boron is a metalloid with no
metallic radius (covalent only), and carbon has no melting point at
1 atm (it sublimes) and no metallic radius. Including either would
mix radius conventions within the δ calculation and, for carbon,
require inventing a rule-of-mixtures melting temperature, both of
which would silently corrupt every descriptor for alloys containing
them. Remaining unscorable alloys also contain Ca, Sc, Nd, Ga, and
others outside the present set.

Adding an element
-----------------

Add a row below with a per-element source comment. Conventions:

- Atomic radius: Goldschmidt 12-coordinate metallic radius, to match
  the original 24. Housecroft & Sharpe Appendix 6 is the primary
  digitized source; cross-check a second table (the values disagree
  by a few pm between compilations for soft / anisotropic metals).
- Melting point: CRC Handbook, 1 atm.
- Valence: s + d electrons for transition metals (so Cu = 11,
  Zn = 12), group number for s- and p-block, following Guo & Liu 2011.

If multiple sources give different values, choose the one consistent
with the original 24's convention and note the alternative in a
comment. Do not interpolate from neighbouring elements.
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


# 30 elements, alphabetically by symbol. The original 24 mirror the
# legacy ELEMENT_DATA table from thermo-descriptor-calculator; do NOT
# alter those individual numbers without paired tests. The six added
# in v1.2 (Au, Li, Mg, Re, Sn, Zn) carry per-element source comments.
ELEMENTAL_DATA: dict[str, ElementProperties] = {
    "Ag": ElementProperties(radius_pm=144.0, melting_K=1234.93, valence=11),
    "Al": ElementProperties(radius_pm=143.0, melting_K= 933.47, valence= 3),
    # Au (v1.2): radius Goldschmidt CN12 = 144 (Wikipedia + Goldschmidt
    # tables agree; equals our Ag). mp CRC 1064.18 C. valence 5d10+6s1
    # = 11 (matches our Ag convention).
    "Au": ElementProperties(radius_pm=144.0, melting_K=1337.33, valence=11),
    "Co": ElementProperties(radius_pm=125.0, melting_K=1768.00, valence= 9),
    "Cr": ElementProperties(radius_pm=129.0, melting_K=2180.00, valence= 6),
    "Cu": ElementProperties(radius_pm=128.0, melting_K=1357.77, valence=11),
    "Fe": ElementProperties(radius_pm=126.0, melting_K=1811.00, valence= 8),
    "Hf": ElementProperties(radius_pm=159.0, melting_K=2506.00, valence= 4),
    "Ir": ElementProperties(radius_pm=136.0, melting_K=2719.00, valence= 9),
    # Li (v1.2): radius Goldschmidt CN12 = 157 (Housecroft & Sharpe
    # Appendix 6; note Wikipedia metallic column gives 152). mp CRC
    # 180.50 C. valence group 1 = 1.
    "Li": ElementProperties(radius_pm=157.0, melting_K= 453.65, valence= 1),
    # Mg (v1.2): radius Goldschmidt CN12 = 160 (all sources agree).
    # mp CRC 650.0 C. valence group 2 = 2.
    "Mg": ElementProperties(radius_pm=160.0, melting_K= 923.15, valence= 2),
    "Mn": ElementProperties(radius_pm=135.7, melting_K=1519.00, valence= 7),
    "Mo": ElementProperties(radius_pm=139.0, melting_K=2896.00, valence= 6),
    "Nb": ElementProperties(radius_pm=147.0, melting_K=2750.00, valence= 5),
    "Ni": ElementProperties(radius_pm=125.0, melting_K=1728.00, valence=10),
    "Os": ElementProperties(radius_pm=135.0, melting_K=3306.00, valence= 8),
    "Pd": ElementProperties(radius_pm=137.0, melting_K=1828.00, valence=10),
    "Pt": ElementProperties(radius_pm=139.0, melting_K=2041.40, valence=10),
    # Re (v1.2): radius Goldschmidt CN12 = 137 (Goldschmidt + Wikipedia
    # agree; no allotrope ambiguity). mp CRC 3186 C. valence 5d5+6s2 = 7.
    "Re": ElementProperties(radius_pm=137.0, melting_K=3459.15, valence= 7),
    "Rh": ElementProperties(radius_pm=134.0, melting_K=2237.00, valence= 9),
    "Ru": ElementProperties(radius_pm=134.0, melting_K=2607.00, valence= 8),
    "Si": ElementProperties(radius_pm=111.0, melting_K=1687.00, valence= 4),
    # Sn (v1.2): radius Goldschmidt CN12 = 158 (Housecroft & Sharpe
    # Appendix 6, beta-Sn; note Wikipedia's 140 is a different,
    # non-CN12 convention). mp CRC 231.93 C (white tin). valence
    # group 14 = 4 (matches our Si).
    "Sn": ElementProperties(radius_pm=158.0, melting_K= 505.08, valence= 4),
    "Ta": ElementProperties(radius_pm=147.0, melting_K=3290.00, valence= 5),
    "Ti": ElementProperties(radius_pm=147.0, melting_K=1941.00, valence= 4),
    "V":  ElementProperties(radius_pm=135.0, melting_K=2183.00, valence= 5),
    "W":  ElementProperties(radius_pm=141.0, melting_K=3695.00, valence= 6),
    "Y":  ElementProperties(radius_pm=182.0, melting_K=1799.00, valence= 3),
    # Zn (v1.2): radius Goldschmidt CN12 = 137 (Housecroft & Sharpe
    # Appendix 6; note Wikipedia gives 134, some Goldschmidt tables
    # 139 -- Zn is hcp-anisotropic so compilations differ). mp CRC
    # 419.53 C. valence 3d10+4s2 = 12 (matches our Cu = 11 convention).
    "Zn": ElementProperties(radius_pm=137.0, melting_K= 692.68, valence=12),
    "Zr": ElementProperties(radius_pm=160.0, melting_K=2128.00, valence= 4),
}


def covered_elements() -> set[str]:
    """Return the set of element symbols this table covers."""
    return set(ELEMENTAL_DATA)


def missing_elements(composition_elements: set[str]) -> set[str]:
    """Return any elements in ``composition_elements`` not in the table."""
    return composition_elements - covered_elements()
