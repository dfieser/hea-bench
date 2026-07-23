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
                   All values are the WebElements consistent set (Yb approximate, flagged in its row comment), whose
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
convention (Teatum, Gschneidner & Waber; see below); melting points
are from the CRC Handbook (Haynes 2016). Cerium's valence is taken
as 3 (gamma-phase, ambient conditions) following Koskenmaki &
Gschneidner (1978); it shifts to 4 only under high pressure or low
temperature (alpha-Ce).

v2.1 expands the table from 37 to 55 elements. The declared radius
authority is the Los Alamos compilation LA-4003: E. T. Teatum,
K. A. Gschneidner Jr., J. T. Waber, "Compilation of calculated data
useful in predicting metallurgical behavior of the elements in
binary alloy systems," LA-4003 (1968), which supersedes LA-2345
(1960). (Earlier comments in this file cited "Teatum & Waber 1967";
LA-4003 (1968) is the precise citation, and every v2.1 radius was
read from its Table I scan on 2026-07-22.) The additions close the
experimentally active rare-earth HEA palette (Pr, Nd, Sm, Tb, Dy,
Ho, Er, Tm, Yb, Lu), the nuclear-HEA corner (U, Th), HE-BMG formers
(Sr, Yb), solder/thermoelectric metals (Ge, Sb, Bi, Pb), and Ga.
Cross-check values from Miracle & Senkov 2017 (Acta Mater. 122, 448,
Table 3) are recorded in ``provenance.py``; note that M&S's printed
lanthanide radii for Pr (165), Nd (164), and Tm (156) are evident
misprints, inconsistent with their own neighboring entries.

Deliberately excluded, with reasons:

- B and C (unchanged policy): no metallic radius (B), no 1-atm
  melting point (C sublimes); either would corrupt δ and Tm.
- N, H: interstitial gases; nitride/hydride HEAs are interstitial
  chemistry outside this table's substitutional model.
- As (sublimes at 1 atm), P (allotrope-dependent melting, covalent
  glass former): no clean CRC melting point or metallic radius.
- Na, K, Rb, Cs, Ba: no metallic-HEA literature; alkali radii also
  disagree 5-8 pm between compilations.
- Eu, Pm: Eu has no reliable Pauling chi and a divalent/trivalent
  radius ambiguity with no alloy demand; Pm is radioactive and its
  LA-4003 radius is an author interpolation.
- Cd, Tl, Hg: no metallic-HEA usage (toxicity aside); Hg is liquid
  at RT and breaks the s+d VEC pattern in M&S's own table.
- Tc: clean data but modeling-only demand (fission-product epsilon
  phase); revisit if experimental work appears.
- Po, Pa, At: radioactive, zero alloy literature (At lacks even an
  LA-4003 radius).

Adding an element
-----------------

Add a row below with a per-element source comment. Conventions:

- Atomic radius: Goldschmidt 12-coordinate metallic radius, to match
  the original 24. Since v2.1 the declared primary authority is
  Teatum, Gschneidner & Waber, LA-4003 (1968) Table I; cross-check
  Miracle & Senkov 2017 Table 3 and record both in provenance.py
  (compilations disagree by a few pm for soft / anisotropic metals,
  and M&S carry the CN-native, not CN12-converted, values for bcc
  metals). Housecroft & Sharpe Appendix 6 was the digitized source
  for the legacy rows and remains the recorded source for them.
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


# 55 elements, alphabetically by symbol. The original 24 mirror the
# legacy ELEMENT_DATA table from thermo-descriptor-calculator; do NOT
# alter those individual numbers without paired tests. Elements added
# later (v1.2: Au, Li, Mg, Re, Sn, Zn; v1.3: Be, Ca, Ce, Gd, In, La,
# Sc; v2.1: Bi, Dy, Er, Ga, Ge, Ho, Lu, Nd, Pb, Pr, Sb, Sm, Sr, Tb,
# Th, Tm, U, Yb) carry per-element source comments.
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
    # Bi (v2.1): radius CN12 = 168.9 (LA-4003 Table I, 1.689 A, via
    # Pauling bond-number conversion for the A7 structure; M&S 2017
    # print 160, Takeuchi-Inoue-style tables ~170 -- LA-4003 chosen as
    # the declared authority). mp CRC 271.40 C = 544.55 K. valence
    # group 15 = 5. Demand: high-entropy solders (SnPbInBiSb).
    "Bi": ElementProperties(radius_pm=168.9, melting_K= 544.55, valence= 5, electronegativity=2.02),
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
    # Dy (v2.1): radius CN12 = 177.5 (LA-4003 Table I / Gschneidner
    # 1966; M&S 2017 print 177.4, agree within 0.1 pm). mp CRC 1412 C
    # = 1685 K (WebElements/pymatgen print 1680; CRC chosen). valence
    # lanthanide = 3. Demand: REHEA magnetocaloric family (GdTbDyHoEr).
    "Dy": ElementProperties(radius_pm=177.5, melting_K=1685.00, valence= 3, electronegativity=1.22),
    # Er (v2.1): radius CN12 = 175.8 (LA-4003; M&S 175.58). mp CRC
    # 1529 C = 1802 K. valence lanthanide = 3.
    "Er": ElementProperties(radius_pm=175.8, melting_K=1802.00, valence= 3, electronegativity=1.24),
    "Fe": ElementProperties(radius_pm=126.0, melting_K=1811.00, valence= 8, electronegativity=1.83),
    # Ga (v2.1): radius CN12 = 135.3 (LA-4003 Table I, Pauling
    # bond-number conversion for the A11 structure; note the spread:
    # M&S 2017 print 139.2, classic Goldschmidt tables 141 -- LA-4003
    # chosen for consistency with our Al 143 / In 167, which match
    # LA-4003 exactly). mp CRC 29.76 C = 302.91 K. valence group 13
    # = 3. Demand: FeCoNiCrGa, magnetic/shape-memory HEAs.
    "Ga": ElementProperties(radius_pm=135.3, melting_K= 302.91, valence= 3, electronegativity=1.81),
    # Gd (v1.3): radius Goldschmidt CN12 = 180.2 (Teatum & Waber 1967).
    # mp CRC 1585 K (Haynes 2016). valence = 3.
    "Gd": ElementProperties(radius_pm=180.2, melting_K=1585.00, valence= 3, electronegativity=1.20),
    # Ge (v2.1): radius = 124 COVALENT-SCALE (M&S 2017 Table 3), the
    # deliberate exception to the LA-4003 rule: our legacy Si = 111 is
    # covalent-scale, and Ge sits in the same diamond-cubic family, so
    # 124 keeps the Si:Ge pair internally consistent. LA-4003's
    # CN12-equivalent is 137.8; using it against Si 111 would skew
    # delta for Si+Ge alloys. mp CRC 938.25 C = 1211.40 K. valence
    # group 14 = 4 (matches Si, Sn). Demand: CoCrFeNiGe_x.
    "Ge": ElementProperties(radius_pm=124.0, melting_K=1211.40, valence= 4, electronegativity=2.01),
    "Hf": ElementProperties(radius_pm=159.0, melting_K=2506.00, valence= 4, electronegativity=1.30),
    # Ho (v2.1): radius CN12 = 176.7 (LA-4003; M&S 176.61). mp CRC
    # 1472 C = 1745 K (WebElements-derived tables print 1734; CRC
    # chosen). valence lanthanide = 3.
    "Ho": ElementProperties(radius_pm=176.7, melting_K=1745.00, valence= 3, electronegativity=1.23),
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
    # Lu (v2.1): radius CN12 = 173.5 (LA-4003; M&S 173.49). mp CRC
    # 1663 C = 1936 K (some tables print 1925; CRC chosen). valence
    # lanthanide = 3. Demand: YGdTbDyLu, GdTbDyTmLu single-phase hcp
    # REHEAs (Takeuchi 2014).
    "Lu": ElementProperties(radius_pm=173.5, melting_K=1936.00, valence= 3, electronegativity=1.27),
    # Mg (v1.2): radius Goldschmidt CN12 = 160 (all sources agree).
    # mp CRC 650.0 C. valence group 2 = 2.
    "Mg": ElementProperties(radius_pm=160.0, melting_K= 923.15, valence= 2, electronegativity=1.31),
    "Mn": ElementProperties(radius_pm=135.7, melting_K=1519.00, valence= 7, electronegativity=1.55),
    "Mo": ElementProperties(radius_pm=139.0, melting_K=2896.00, valence= 6, electronegativity=2.16),
    "Nb": ElementProperties(radius_pm=147.0, melting_K=2750.00, valence= 5, electronegativity=1.60),
    # Nd (v2.1): radius CN12 = 182.2 (LA-4003 / Gschneidner 1966;
    # M&S 2017 print 164, an evident misprint -- inconsistent with
    # their own Ce 182.47 and Sm 181). mp CRC 1016 C = 1289 K
    # (Wikipedia-derived tables print 1297; CRC + LA-4003 + M&S agree
    # on 1289). valence lanthanide = 3.
    "Nd": ElementProperties(radius_pm=182.2, melting_K=1289.00, valence= 3, electronegativity=1.14),
    "Ni": ElementProperties(radius_pm=125.0, melting_K=1728.00, valence=10, electronegativity=1.91),
    "Os": ElementProperties(radius_pm=135.0, melting_K=3306.00, valence= 8, electronegativity=2.20),
    # Pb (v2.1): radius CN12 = 175.0 (LA-4003 Table I, fcc read
    # directly; M&S 174.97 -- all sources agree). mp CRC 327.46 C =
    # 600.61 K. valence group 14 = 4. chi = 2.33 is the revised
    # Pauling value used by the WebElements consistent set (the older
    # Pauling table printed 1.87; do not mix). Demand: HE solders,
    # PbSnTeSe thermoelectrics.
    "Pb": ElementProperties(radius_pm=175.0, melting_K= 600.61, valence= 4, electronegativity=2.33),
    "Pd": ElementProperties(radius_pm=137.0, melting_K=1828.00, valence=10, electronegativity=2.20),
    # Pr (v2.1): radius CN12 = 182.8 (LA-4003 / Gschneidner 1966; M&S
    # print 165, an evident misprint). mp CRC 931 C = 1204 K. valence
    # lanthanide = 3. Demand: PrGdTbHoEr magnetocaloric REHEA.
    "Pr": ElementProperties(radius_pm=182.8, melting_K=1204.00, valence= 3, electronegativity=1.13),
    "Pt": ElementProperties(radius_pm=139.0, melting_K=2041.40, valence=10, electronegativity=2.28),
    # Re (v1.2): radius Goldschmidt CN12 = 137 (Goldschmidt + Wikipedia
    # agree; no allotrope ambiguity). mp CRC 3186 C. valence 5d5+6s2 = 7.
    "Re": ElementProperties(radius_pm=137.0, melting_K=3459.15, valence= 7, electronegativity=1.90),
    "Rh": ElementProperties(radius_pm=134.0, melting_K=2237.00, valence= 9, electronegativity=2.28),
    "Ru": ElementProperties(radius_pm=134.0, melting_K=2607.00, valence= 8, electronegativity=2.20),
    # Sb (v2.1): radius CN12 = 157.1 (LA-4003 Table I, Pauling
    # bond-number conversion for the A7 structure; M&S print the
    # covalent-scale 145. 157.1 keeps Sb consistent with our metallic
    # In 167 / Sn 158 in solder-type alloys). mp CRC 630.63 C =
    # 903.78 K. valence group 15 = 5. Demand: SnPbInBiSb HE solders.
    "Sb": ElementProperties(radius_pm=157.1, melting_K= 903.78, valence= 5, electronegativity=2.05),
    # Sc (v1.3): radius Goldschmidt CN12 = 164 (Teatum & Waber 1967).
    # mp CRC 1814 K (Haynes 2016). valence = 3 (s2d1).
    "Sc": ElementProperties(radius_pm=164.0, melting_K=1814.00, valence= 3, electronegativity=1.36),
    "Si": ElementProperties(radius_pm=111.0, melting_K=1687.00, valence= 4, electronegativity=1.90),
    # Sm (v2.1): radius CN12 = 180.2 (LA-4003 / Gschneidner 1966; M&S
    # print 181, agree within 1 pm). mp CRC 1072 C = 1345 K. valence
    # lanthanide = 3.
    "Sm": ElementProperties(radius_pm=180.2, melting_K=1345.00, valence= 3, electronegativity=1.17),
    # Sn (v1.2): radius Goldschmidt CN12 = 158 (Housecroft & Sharpe
    # Appendix 6, beta-Sn; note Wikipedia's 140 is a different,
    # non-CN12 convention). mp CRC 231.93 C (white tin). valence
    # group 14 = 4 (matches our Si).
    "Sn": ElementProperties(radius_pm=158.0, melting_K= 505.08, valence= 4, electronegativity=1.96),
    # Sr (v2.1): radius CN12 = 215.1 (LA-4003 Table I, alpha-Sr fcc
    # read directly; M&S 215.2). mp CRC 777 C = 1050 K. valence
    # group 2 = 2. Demand: Sr20Ca20Yb20Mg20Zn20 high-entropy bulk
    # metallic glass.
    "Sr": ElementProperties(radius_pm=215.1, melting_K=1050.00, valence= 2, electronegativity=0.95),
    "Ta": ElementProperties(radius_pm=147.0, melting_K=3290.00, valence= 5, electronegativity=1.50),
    # Tb (v2.1): radius CN12 = 178.3 (LA-4003 / Gschneidner 1966;
    # M&S 178.14). mp CRC 1359 C = 1632 K (WebElements-derived tables
    # print 1629; CRC chosen). valence lanthanide = 3. chi = 1.10 as
    # printed in the CRC/WebElements set (non-monotonic against
    # Gd 1.20 / Dy 1.22; taken as printed, no interpolation).
    "Tb": ElementProperties(radius_pm=178.3, melting_K=1632.00, valence= 3, electronegativity=1.10),
    # Th (v2.1): radius CN12 = 179.8 (LA-4003 Table I, alpha-Th fcc
    # read directly). mp CRC 1750 C = 2023 K -- NOTE the genuine
    # literature spread: some compilations print 2115 K (1842 C);
    # CRC/LA-4003 agree on ~2023 and CRC is our declared authority.
    # valence = 4 (Zachariasen, via LA-4003). Demand: (NbTa)(MoWTh)
    # superconducting HEA (Sci. Rep. 2023).
    "Th": ElementProperties(radius_pm=179.8, melting_K=2023.00, valence= 4, electronegativity=1.30),
    "Ti": ElementProperties(radius_pm=147.0, melting_K=1941.00, valence= 4, electronegativity=1.54),
    # Tm (v2.1): radius CN12 = 174.7 (LA-4003 / Gschneidner 1966; M&S
    # print 156, an evident misprint -- inconsistent with their own
    # Er 175.58 / Lu 173.49). mp CRC 1545 C = 1818 K. valence
    # lanthanide = 3. Demand: GdTbDyTmLu, octonary REHEAs.
    "Tm": ElementProperties(radius_pm=174.7, melting_K=1818.00, valence= 3, electronegativity=1.25),
    # U (v2.1): radius CN12 = 154.3 (LA-4003 Table I, alpha-U via
    # Pauling bond-number conversion). mp CRC 1135 C = 1408 K.
    # valence = 6, the Zachariasen metallic valence adopted by
    # LA-4003 (itinerant 5f electrons); the strict Guo s+d count
    # (6d1 7s2) would give 3 -- documented alternative, choose 6 for
    # consistency with the radius/valence state. chi = 1.38 (Pauling
    # set). Demand: UMoNbTaTi / UNbZrTiMo nuclear HEAs.
    "U":  ElementProperties(radius_pm=154.3, melting_K=1408.00, valence= 6, electronegativity=1.38),
    "V":  ElementProperties(radius_pm=135.0, melting_K=2183.00, valence= 5, electronegativity=1.63),
    "W":  ElementProperties(radius_pm=141.0, melting_K=3695.00, valence= 6, electronegativity=2.36),
    "Y":  ElementProperties(radius_pm=182.0, melting_K=1799.00, valence= 3, electronegativity=1.22),
    # Yb (v2.1): radius CN12 = 193.9 (LA-4003 Table I, Yb(2): metallic
    # Yb is DIVALENT, 4f14 6s2, fcc). valence = 2 to stay consistent
    # with the divalent metallic state the radius describes; note M&S
    # 2017 assign lanthanide-3 (and print radius 170) -- documented
    # alternative. The trivalent estimate Yb(3) = 174.1 in LA-4003 is
    # an author interpolation, not a measured lattice value. chi =
    # 1.10 is approximate ("1.1" in CRC; outside the strict
    # WebElements consistent set -- flagged). mp CRC 824 C = 1097 K.
    # Demand: SrCaYbMgZn high-entropy bulk metallic glass.
    "Yb": ElementProperties(radius_pm=193.9, melting_K=1097.00, valence= 2, electronegativity=1.10),
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
