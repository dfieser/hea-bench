"""Per-element physical properties used by descriptor computations.

Four properties are exposed for each element:

- ``radius_pm``  : atomic radius in picometres (metallic, 12-coordinated
                   where applicable; Pauling table values otherwise)
- ``melting_K``  : melting point in kelvin at 1 atm (CRC Handbook
                   reference values rounded to two decimals)
- ``valence``    : valence-electron count (s + d for transition metals,
                   following the convention used in Guo & Liu 2011 for
                   the VEC rule)
- ``electronegativity`` : Pauling-scale electronegativity (dimensionless).
                   All 37 values are the WebElements consistent set, whose
                   primary reference is Pauling, *The Nature of the Chemical
                   Bond*, 3rd ed. (Cornell Univ. Press, 1960); the CRC
                   Handbook (Haynes 2016) reproduces the same set. Because
                   the values come from one consistent compilation there is
                   no per-element ambiguity to flag, so they carry no
                   per-element source comments.

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

v1.3 expands the table from 30 to 37 elements by adding Be, Ca, Ce,
Gd, In, La, and Sc. All radii follow the same Goldschmidt CN12
convention (Teatum & Waber 1967); melting points are from the CRC
Handbook (Haynes 2016). Cerium's valence is taken as 3 (gamma-phase,
ambient conditions) following Koskenmaki & Gschneidner (1978);
it shifts to 4 only under high pressure or low temperature (alpha-Ce).
These seven elements cover the dominant contributors to the unscorable
residue identified in figure 2 of the companion manuscript (excluding
B, C, and N, which cannot be added; see below).

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
- Electronegativity: Pauling scale, WebElements consistent set
  (Pauling 1960; reproduced in CRC Handbook, Haynes 2016). Take the
  value from that set; do not mix scales (Allen, Mulliken) within the
  table.

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
    electronegativity: float


# 30 elements, alphabetically by symbol. The original 24 mirror the
# legacy ELEMENT_DATA table from thermo-descriptor-calculator; do NOT
# alter those individual numbers without paired tests. The six added
# in v1.2 (Au, Li, Mg, Re, Sn, Zn) carry per-element source comments.
ELEMENTAL_DATA: dict[str, ElementProperties] = {
    "Ag": ElementProperties(radius_pm=144.0, melting_K=1234.93, valence=11, electronegativity=1.93),
    "Al": ElementProperties(radius_pm=143.0, melting_K= 933.47, valence= 3, electronegativity=1.61),
    # Au (v1.2): radius Goldschmidt CN12 = 144 (Wikipedia + Goldschmidt
    # tables agree; equals our Ag). mp CRC 1064.18 C. valence 5d10+6s1
    # = 11 (matches our Ag convention).
    "Au": ElementProperties(radius_pm=144.0, melting_K=1337.33, valence=11, electronegativity=2.54),
    # Be (v1.3): radius Goldschmidt CN12 = 112 (Teatum & Waber 1967).
    # mp CRC 1560 K (Haynes 2016). valence group 2 = 2.
    "Be": ElementProperties(radius_pm=112.0, melting_K=1560.00, valence= 2, electronegativity=1.57),
    # Ca (v1.3): radius Goldschmidt CN12 = 197 (Teatum & Waber 1967).
    # mp CRC 1115 K (Haynes 2016). valence group 2 = 2.
    "Ca": ElementProperties(radius_pm=197.0, melting_K=1115.00, valence= 2, electronegativity=1.00),
    # Ce (v1.3): radius Goldschmidt CN12 = 182 (Teatum & Waber 1967).
    # mp CRC 1071 K (Haynes 2016). valence = 3 by convention
    # (gamma-phase, ambient conditions; Koskenmaki & Gschneidner 1978).
    "Ce": ElementProperties(radius_pm=182.0, melting_K=1071.00, valence= 3, electronegativity=1.12),
    "Co": ElementProperties(radius_pm=125.0, melting_K=1768.00, valence= 9, electronegativity=1.88),
    "Cr": ElementProperties(radius_pm=129.0, melting_K=2180.00, valence= 6, electronegativity=1.66),
    "Cu": ElementProperties(radius_pm=128.0, melting_K=1357.77, valence=11, electronegativity=1.90),
    "Fe": ElementProperties(radius_pm=126.0, melting_K=1811.00, valence= 8, electronegativity=1.83),
    # Gd (v1.3): radius Goldschmidt CN12 = 180.2 (Teatum & Waber 1967).
    # mp CRC 1585 K (Haynes 2016). valence = 3.
    "Gd": ElementProperties(radius_pm=180.2, melting_K=1585.00, valence= 3, electronegativity=1.20),
    "Hf": ElementProperties(radius_pm=159.0, melting_K=2506.00, valence= 4, electronegativity=1.30),
    # In (v1.3): radius Goldschmidt CN12 = 167 (Teatum & Waber 1967).
    # mp CRC 429.7 K (Haynes 2016). valence group 13 = 3.
    "In": ElementProperties(radius_pm=167.0, melting_K= 429.70, valence= 3, electronegativity=1.78),
    "Ir": ElementProperties(radius_pm=136.0, melting_K=2719.00, valence= 9, electronegativity=2.20),
    # La (v1.3): radius Goldschmidt CN12 = 188 (Teatum & Waber 1967).
    # mp CRC 1193 K (Haynes 2016). valence = 3.
    "La": ElementProperties(radius_pm=188.0, melting_K=1193.00, valence= 3, electronegativity=1.10),
    # Li (v1.2): radius Goldschmidt CN12 = 157 (Housecroft & Sharpe
    # Appendix 6; note Wikipedia metallic column gives 152). mp CRC
    # 180.50 C. valence group 1 = 1.
    "Li": ElementProperties(radius_pm=157.0, melting_K= 453.65, valence= 1, electronegativity=0.98),
    # Mg (v1.2): radius Goldschmidt CN12 = 160 (all sources agree).
    # mp CRC 650.0 C. valence group 2 = 2.
    "Mg": ElementProperties(radius_pm=160.0, melting_K= 923.15, valence= 2, electronegativity=1.31),
    "Mn": ElementProperties(radius_pm=135.7, melting_K=1519.00, valence= 7, electronegativity=1.55),
    "Mo": ElementProperties(radius_pm=139.0, melting_K=2896.00, valence= 6, electronegativity=2.16),
    "Nb": ElementProperties(radius_pm=147.0, melting_K=2750.00, valence= 5, electronegativity=1.60),
    "Ni": ElementProperties(radius_pm=125.0, melting_K=1728.00, valence=10, electronegativity=1.91),
    "Os": ElementProperties(radius_pm=135.0, melting_K=3306.00, valence= 8, electronegativity=2.20),
    "Pd": ElementProperties(radius_pm=137.0, melting_K=1828.00, valence=10, electronegativity=2.20),
    "Pt": ElementProperties(radius_pm=139.0, melting_K=2041.40, valence=10, electronegativity=2.28),
    # Re (v1.2): radius Goldschmidt CN12 = 137 (Goldschmidt + Wikipedia
    # agree; no allotrope ambiguity). mp CRC 3186 C. valence 5d5+6s2 = 7.
    "Re": ElementProperties(radius_pm=137.0, melting_K=3459.15, valence= 7, electronegativity=1.90),
    "Rh": ElementProperties(radius_pm=134.0, melting_K=2237.00, valence= 9, electronegativity=2.28),
    "Ru": ElementProperties(radius_pm=134.0, melting_K=2607.00, valence= 8, electronegativity=2.20),
    # Sc (v1.3): radius Goldschmidt CN12 = 164 (Teatum & Waber 1967).
    # mp CRC 1814 K (Haynes 2016). valence = 3 (s2d1).
    "Sc": ElementProperties(radius_pm=164.0, melting_K=1814.00, valence= 3, electronegativity=1.36),
    "Si": ElementProperties(radius_pm=111.0, melting_K=1687.00, valence= 4, electronegativity=1.90),
    # Sn (v1.2): radius Goldschmidt CN12 = 158 (Housecroft & Sharpe
    # Appendix 6, beta-Sn; note Wikipedia's 140 is a different,
    # non-CN12 convention). mp CRC 231.93 C (white tin). valence
    # group 14 = 4 (matches our Si).
    "Sn": ElementProperties(radius_pm=158.0, melting_K= 505.08, valence= 4, electronegativity=1.96),
    "Ta": ElementProperties(radius_pm=147.0, melting_K=3290.00, valence= 5, electronegativity=1.50),
    "Ti": ElementProperties(radius_pm=147.0, melting_K=1941.00, valence= 4, electronegativity=1.54),
    "V":  ElementProperties(radius_pm=135.0, melting_K=2183.00, valence= 5, electronegativity=1.63),
    "W":  ElementProperties(radius_pm=141.0, melting_K=3695.00, valence= 6, electronegativity=2.36),
    "Y":  ElementProperties(radius_pm=182.0, melting_K=1799.00, valence= 3, electronegativity=1.22),
    # Zn (v1.2): radius Goldschmidt CN12 = 137 (Housecroft & Sharpe
    # Appendix 6; note Wikipedia gives 134, some Goldschmidt tables
    # 139 -- Zn is hcp-anisotropic so compilations differ). mp CRC
    # 419.53 C. valence 3d10+4s2 = 12 (matches our Cu = 11 convention).
    "Zn": ElementProperties(radius_pm=137.0, melting_K= 692.68, valence=12, electronegativity=1.65),
    "Zr": ElementProperties(radius_pm=160.0, melting_K=2128.00, valence= 4, electronegativity=1.33),
}


def covered_elements() -> set[str]:
    """Return the set of element symbols this table covers."""
    return set(ELEMENTAL_DATA)


def missing_elements(composition_elements: set[str]) -> set[str]:
    """Return any elements in ``composition_elements`` not in the table."""
    return composition_elements - covered_elements()
