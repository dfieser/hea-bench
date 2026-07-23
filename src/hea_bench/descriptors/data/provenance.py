"""Structured provenance for the element table and the bibliography.

This module is the single source of truth behind the web app's Data
view and provenance drawer (generated into ``web/index.html`` by
``tests/data/_sync_js_provenance.py``). Nothing here feeds any
computation; it exists so every number the app shows can point at
where it came from, including the places where good sources disagree.

Conventions documented once, referenced per element:

- Radius: Goldschmidt-style 12-coordinate metallic radius. Declared
  authority for v2.1 additions: Teatum, Gschneidner & Waber, LA-4003
  (1968) Table I (read from the OSTI scan on 2026-07-22). The legacy
  24 came to us through Housecroft & Sharpe's digitization of the
  same convention and match LA-4003 where checked. Exceptions (Si,
  Ge) use covalent-scale radii, flagged in their rows.
- Cross-check radii: Miracle & Senkov 2017, Table 3 (their sources:
  Pearson's Handbook / MacGillavry / WebElements). Those radii are
  lattice-native (CN8 for bcc metals), so bcc elements read a few
  percent below the CN12-converted values by construction; that gap
  is a convention difference, not an error. Read from the article
  scan to about +/-0.1 pm; display-only.
- Melting: CRC Handbook (Haynes 2016), 1 atm.
- Valence (VEC): Guo s+d convention; lanthanides 3; divalent Yb 2;
  U 6 (Zachariasen metallic valence, via LA-4003); Th 4.
- Electronegativity: Pauling scale, WebElements consistent set
  (Pauling 1960; reproduced in CRC).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Ref:
    """One bibliography entry (short form; full prose lives in the
    References view)."""

    authors: str
    title: str
    venue: str
    year: int
    doi: str = ""
    url: str = ""


@dataclass(frozen=True)
class PropertySource:
    """Column-level source statement for one elemental property."""

    statement: str
    source_keys: tuple[str, ...]


@dataclass(frozen=True)
class ElementSources:
    """Per-element provenance notes for the Data view."""

    radius_source_key: str
    crosscheck_radius_pm: float | None = None
    crosscheck_source_key: str = "ms2017"
    crosscheck_note: str = ""
    notes: str = ""
    flags: tuple[str, ...] = field(default_factory=tuple)


REFERENCES: dict[str, Ref] = {
    # --- foundations (mirrors the References view) ---
    "cantor2004": Ref("Cantor, B., Chang, I. T. H., Knight, P. & Vincent, A. J. B.", "Microstructural development in equiatomic multicomponent alloys", "Mater. Sci. Eng. A 375-377, 213", 2004, doi="10.1016/j.msea.2003.10.257"),
    "yeh2004": Ref("Yeh, J.-W. et al.", "Nanostructured high-entropy alloys with multiple principal elements", "Adv. Eng. Mater. 6, 299", 2004, doi="10.1002/adem.200300567"),
    "humerothery1934": Ref("Hume-Rothery, W. & Powell, H. M.", "On the theory of super-lattice structures in alloys", "Z. Kristallogr. 91, 23", 1934, doi="10.1524/zkri.1935.91.1.23"),
    "murty2019": Ref("Murty, B. S., Yeh, J.-W., Ranganathan, S. & Bhattacharjee, P. P.", "High-Entropy Alloys (2nd ed.)", "Elsevier", 2019, doi="10.1016/C2017-0-03317-7"),
    "senkov2010": Ref("Senkov, O. N., Wilks, G. B., Miracle, D. B., Chuang, C. P. & Liaw, P. K.", "Refractory high-entropy alloys", "Intermetallics 18, 1758", 2010, doi="10.1016/j.intermet.2010.05.014"),
    "zhang2014pms": Ref("Zhang, Y. et al.", "Microstructures and properties of high-entropy alloys", "Prog. Mater. Sci. 61, 1", 2014, doi="10.1016/j.pmatsci.2013.10.001"),
    # --- descriptors & rules ---
    "zhang2008": Ref("Zhang, Y., Zhou, Y. J., Lin, J. P., Chen, G. L. & Liaw, P. K.", "Solid-solution phase formation rules for multi-component alloys", "Adv. Eng. Mater. 10, 534", 2008, doi="10.1002/adem.200700240"),
    "yang2012": Ref("Yang, X. & Zhang, Y.", "Prediction of high-entropy stabilized solid-solution in multi-component alloys", "Mater. Chem. Phys. 132, 233", 2012, doi="10.1016/j.matchemphys.2011.11.021"),
    "guo2011pnsmi": Ref("Guo, S. & Liu, C. T.", "Phase stability in high entropy alloys: formation of solid-solution phase or amorphous phase", "Prog. Nat. Sci.: Mater. Int. 21, 433", 2011, doi="10.1016/S1002-0071(12)60080-X"),
    "guo2011vec": Ref("Guo, S., Ng, C., Lu, J. & Liu, C. T.", "Effect of valence electron concentration on stability of fcc or bcc phase in high entropy alloys", "J. Appl. Phys. 109, 103505", 2011, doi="10.1063/1.3587228"),
    "senkovmiracle2001": Ref("Senkov, O. N. & Miracle, D. B.", "Effect of the atomic size distribution on glass forming ability of amorphous metallic alloys", "Mater. Res. Bull. 36, 2183", 2001, doi="10.1016/S0025-5408(01)00715-2"),
    "king2016": Ref("King, D. J. M., Middleburgh, S. C., McGregor, A. G. & Cortie, M. B.", "Predicting the formation and stability of single phase high-entropy alloys", "Acta Mater. 104, 172", 2016, doi="10.1016/j.actamat.2015.11.040"),
    "ye2015phi": Ref("Ye, Y. F., Wang, Q., Lu, J., Liu, C. T. & Yang, Y.", "Design of high entropy alloys: a single-parameter thermodynamic rule", "Scripta Mater. 104, 53", 2015, doi="10.1016/j.scriptamat.2015.03.023"),
    "mansoori1971": Ref("Mansoori, G. A., Carnahan, N. F., Starling, K. E. & Leland, T. W.", "Equilibrium thermodynamic properties of the mixture of hard spheres", "J. Chem. Phys. 54, 1523", 1971, doi="10.1063/1.1675048"),
    "takeuchi2000": Ref("Takeuchi, A. & Inoue, A.", "Calculations of mixing enthalpy and mismatch entropy for ternary amorphous alloys", "Mater. Trans. JIM 41, 1372", 2000, doi="10.2320/matertrans1989.41.1372"),
    "singh2014": Ref("Singh, A. K., Kumar, N., Dwivedi, A. & Subramaniam, A.", "A geometrical parameter for the formation of disordered solid solutions in multi-component alloys", "Intermetallics 53, 112", 2014, doi="10.1016/j.intermet.2014.04.019"),
    "wang2015": Ref("Wang, Z., Huang, Y., Yang, Y., Wang, J. & Liu, C. T.", "Atomic-size effect and solid solubility of multicomponent alloys", "Scripta Mater. 94, 28", 2015, doi="10.1016/j.scriptamat.2014.09.010"),
    "senkov2016": Ref("Senkov, O. N. & Miracle, D. B.", "A new thermodynamic parameter to predict formation of solid solution or intermetallic phases in high entropy alloys", "J. Alloys Compd. 658, 603", 2016, doi="10.1016/j.jallcom.2015.10.279"),
    "andreoli2019": Ref("Andreoli, A. F., Orava, J., Liaw, P. K., Weber, H., de Oliveira, M. F., Nielsch, K. & Kaban, I.", "The elastic-strain energy criterion of phase formation for complex concentrated alloys", "Materialia 5, 100222", 2019, doi="10.1016/j.mtla.2019.100222"),
    "tsai2013": Ref("Tsai, M.-H., Tsai, K.-Y., Tsai, C.-W., Lee, C., Juan, C.-C. & Yeh, J.-W.", "Criterion for sigma phase formation in Cr- and V-containing high-entropy alloys", "Mater. Res. Lett. 1, 207", 2013, doi="10.1080/21663831.2013.831382"),
    "sheikh2016": Ref("Sheikh, S., Shafeie, S., Hu, Q., Ahlstrom, J., Persson, C., Vesely, J., Zyka, J., Klement, U. & Guo, S.", "Alloy design for intrinsically ductile refractory high-entropy alloys", "J. Appl. Phys. 120, 164902", 2016, doi="10.1063/1.4966659"),
    "pickering2016": Ref("Pickering, E. J. & Jones, N. G.", "High-entropy alloys: a critical assessment of their founding principles and future prospects", "Int. Mater. Rev. 61, 183", 2016, doi="10.1080/09506608.2016.1180020"),
    # --- Miedema model ---
    "deboer1988": Ref("de Boer, F. R., Boom, R., Mattens, W. C. M., Miedema, A. R. & Niessen, A. K.", "Cohesion in Metals: Transition Metal Alloys", "North-Holland, Amsterdam", 1988, url="https://search.worldcat.org/title/17743197"),
    "miedema1980": Ref("Miedema, A. R., de Chatel, P. F. & de Boer, F. R.", "Cohesion in alloys - fundamentals of a semi-empirical model", "Physica B+C 100, 1", 1980, doi="10.1016/0378-4363(80)90054-6"),
    "miedema1973": Ref("Miedema, A. R.", "The electronegativity parameter for transition metals", "J. Less-Common Met. 32, 117", 1973, doi="10.1016/0022-5088(73)90078-7"),
    "niessen1983": Ref("Niessen, A. K. et al.", "Model predictions for the enthalpy of formation of transition metal alloys II", "CALPHAD 7, 51", 1983, doi="10.1016/0364-5916(83)90030-5"),
    "loeff1988": Ref("Loeff, P. I., Weeber, A. W. & Miedema, A. R.", "Diagrams of formation enthalpies of amorphous alloys", "J. Less-Common Met. 140, 299", 1988, doi="10.1016/0022-5088(88)90391-8"),
    "eshelby1957": Ref("Eshelby, J. D.", "The determination of the elastic field of an ellipsoidal inclusion", "Proc. R. Soc. A 241, 376", 1957, doi="10.1098/rspa.1957.0133"),
    "friedel1954": Ref("Friedel, J.", "Electronic structure of primary solid solutions in metals", "Adv. Phys. 3, 446", 1954, doi="10.1080/00018735400101233"),
    "bakker1998": Ref("Bakker, H.", "Enthalpies in Alloys: Miedema's Semi-Empirical Model", "Trans Tech Publications", 1998, url="https://www.scientific.net/MSFo.1"),
    "takeuchi2005": Ref("Takeuchi, A. & Inoue, A.", "Classification of bulk metallic glasses by atomic size difference, heat of mixing and period of constituent elements", "Mater. Trans. 46, 2817", 2005, doi="10.2320/matertrans.46.2817"),
    "zhangrf2016": Ref("Zhang, R. F., Zhang, S. H., He, Z. J., Jing, J. & Sheng, S. H.", "Miedema Calculator: a thermodynamic platform for predicting formation enthalpies", "Comput. Phys. Commun. 209, 58", 2016, doi="10.1016/j.cpc.2016.08.013"),
    # --- element data ---
    "la4003": Ref("Teatum, E. T., Gschneidner, K. A., Jr. & Waber, J. T.", "Compilation of calculated data useful in predicting metallurgical behavior of the elements in binary alloy systems", "Los Alamos report LA-4003 (supersedes LA-2345)", 1968, url="https://www.osti.gov/biblio/4789465"),
    "gschneidner1966": Ref("Gschneidner, K. A., Jr.", "Physical properties of the rare earth metals", "Trans. Vacuum Metallurgy Conf. 1965, Am. Vac. Soc.", 1966, url="https://www.osti.gov/biblio/4789465"),
    "ms2017": Ref("Miracle, D. B. & Senkov, O. N.", "A critical review of high entropy alloys and related concepts", "Acta Mater. 122, 448 (Table 3)", 2017, doi="10.1016/j.actamat.2016.08.081"),
    "crc": Ref("Haynes, W. M. (ed.)", "CRC Handbook of Chemistry and Physics, 97th ed.", "CRC Press, Boca Raton", 2016, url="https://www.routledge.com/CRC-Handbook-of-Chemistry-and-Physics/Haynes/p/book/9781498754286"),
    "pauling1960": Ref("Pauling, L.", "The Nature of the Chemical Bond, 3rd ed.", "Cornell University Press", 1960, url="https://search.worldcat.org/title/545520"),
    "housecroft2018": Ref("Housecroft, C. E. & Sharpe, A. G.", "Inorganic Chemistry, 5th ed., Appendix 6 (metallic radii, CN12)", "Pearson", 2018, url="https://www.pearson.com/en-gb/subject-catalog/p/inorganic-chemistry/P200000004526"),
    "matminer2018": Ref("Ward, L., Dunn, A., Faghaninia, A. et al.", "Matminer: an open source toolkit for materials data mining", "Comput. Mater. Sci. 152, 60", 2018, doi="10.1016/j.commatsci.2018.05.018"),
    "koskenmaki1978": Ref("Koskenmaki, D. C. & Gschneidner, K. A., Jr.", "Cerium (Handbook on the Physics and Chemistry of Rare Earths, Vol. 1, Ch. 4)", "North-Holland", 1978, doi="10.1016/S0168-1273(78)01008-9"),
    # --- high-entropy oxides ---
    "rost2015": Ref("Rost, C. M. et al.", "Entropy-stabilized oxides", "Nat. Commun. 6, 8485", 2015, doi="10.1038/ncomms9485"),
    "shannon1976": Ref("Shannon, R. D.", "Revised effective ionic radii and systematic studies of interatomic distances in halides and chalcogenides", "Acta Crystallogr. A 32, 751", 1976, doi="10.1107/S0567739476001551"),
    "goldschmidt1926": Ref("Goldschmidt, V. M.", "Die Gesetze der Krystallochemie", "Naturwissenschaften 14, 477", 1926, doi="10.1007/BF01507527"),
    "bartel2019": Ref("Bartel, C. J. et al.", "New tolerance factor to predict the stability of perovskite oxides and halides", "Sci. Adv. 5, eaav0693", 2019, doi="10.1126/sciadv.aav0693"),
    "jiang2018": Ref("Jiang, S. et al.", "A new class of high-entropy perovskite oxides", "Scripta Mater. 142, 116", 2018, doi="10.1016/j.scriptamat.2017.08.040"),
    "spiridigliozzi2021": Ref("Spiridigliozzi, L., Ferone, C., Cioffi, R. & Dell'Agli, G.", "A simple and effective predictor to design novel fluorite-structured high entropy oxides (HEOs)", "Acta Mater. 202, 181", 2021, doi="10.1016/j.actamat.2020.10.061"),
    "spiridigliozzi2023": Ref("Spiridigliozzi, L., Bortolotti, M. & Dell'Agli, G.", "On the effect of standard deviation of cationic radii on the transition temperature in fluorite-structured entropy-stabilized oxides", "Materials 16, 2219", 2023, doi="10.3390/ma16062219"),
    "subramanian1983": Ref("Subramanian, M. A., Aravamudan, G. & Subba Rao, G. V.", "Oxide pyrochlores - a review", "Prog. Solid State Chem. 15, 55", 1983, doi="10.1016/0079-6786(83)90001-8"),
    "manchon2025": Ref("Manchon-Gordon, A. F., Panadero-Medianero, P. & Blazquez, J. S.", "Descriptors for predicting single- and multi-phase formation in high-entropy oxides", "Materials 18, 3862", 2025, doi="10.3390/ma18163862"),
    # --- software / archive ---
    "heabench2026": Ref("Fieser, D.", "HEA-Bench: an open, parity-tested calculator of high-entropy alloy and oxide descriptors", "Materials 19, 3075", 2026, doi="10.3390/ma19143075"),
    "zenodo": Ref("Fieser, D.", "HEA-Bench (all versions)", "Zenodo concept record", 2026, doi="10.5281/zenodo.20346287"),
}


PROPERTY_SOURCES: dict[str, PropertySource] = {
    "radius_pm": PropertySource(
        statement=(
            "Goldschmidt-style 12-coordinate metallic radius. v2.1 additions read "
            "from Teatum, Gschneidner & Waber LA-4003 (1968) Table I; the legacy "
            "rows follow the same convention via Housecroft & Sharpe's Appendix 6 "
            "digitization. Rare-earth radii trace to Gschneidner (1966). "
            "Exceptions: Si and Ge use covalent-scale radii (flagged in their "
            "rows). Cross-check column: Miracle & Senkov 2017 Table 3, whose "
            "lattice-native radii sit a few percent below CN12 conversions for "
            "bcc metals by construction."
        ),
        source_keys=("la4003", "housecroft2018", "gschneidner1966", "ms2017"),
    ),
    "melting_K": PropertySource(
        statement="Melting point at 1 atm, CRC Handbook (Haynes 2016) consistent set.",
        source_keys=("crc",),
    ),
    "valence": PropertySource(
        statement=(
            "Valence electron count for the VEC rule: s+d electrons for "
            "transition metals (Cu 11, Zn 12), group number for s/p-block, "
            "lanthanides 3, divalent Yb 2, Th 4 and U 6 after Zachariasen "
            "via LA-4003."
        ),
        source_keys=("guo2011vec", "la4003", "ms2017"),
    ),
    "electronegativity": PropertySource(
        statement=(
            "Pauling-scale electronegativity, WebElements consistent set "
            "(primary reference Pauling 1960; reproduced in the CRC Handbook). "
            "Yb is approximate (printed as 1.1)."
        ),
        source_keys=("pauling1960", "crc"),
    ),
}


def _legacy(crosscheck: float | None, note: str = "", extra_notes: str = "", flags: tuple[str, ...] = ()) -> ElementSources:
    return ElementSources(
        radius_source_key="housecroft2018",
        crosscheck_radius_pm=crosscheck,
        crosscheck_note=note or ("Miracle & Senkov 2017 Table 3; lattice-native convention." if crosscheck is not None else ""),
        notes=extra_notes,
        flags=flags,
    )


def _la4003(crosscheck: float | None, note: str = "", extra_notes: str = "", flags: tuple[str, ...] = ()) -> ElementSources:
    return ElementSources(
        radius_source_key="la4003",
        crosscheck_radius_pm=crosscheck,
        crosscheck_note=note or ("Miracle & Senkov 2017 Table 3." if crosscheck is not None else ""),
        notes=extra_notes,
        flags=flags,
    )


_BCC_NOTE = "M&S Table 3 prints the CN8 lattice-native radius; ~3% below the CN12 conversion by construction."

ELEMENT_SOURCES: dict[str, ElementSources] = {
    # legacy 24 + v1.2/v1.3 (Housecroft & Sharpe digitization of the CN12 convention)
    "Ag": _legacy(144.47),
    "Al": _legacy(143.17),
    "Au": _legacy(144.2),
    "Be": _legacy(112.8),
    "Ca": _legacy(197.6),
    "Ce": _legacy(182.47, extra_notes="Valence 3 (gamma-Ce, ambient); shifts to 4 only under pressure/low T (Koskenmaki & Gschneidner 1978)."),
    "Co": _legacy(125.10),
    "Cr": _legacy(124.91, note=_BCC_NOTE),
    "Cu": _legacy(127.8),
    "Fe": _legacy(124.12, note=_BCC_NOTE),
    "Gd": _legacy(180.13),
    "Hf": _legacy(157.75),
    "In": _legacy(165.9),
    "Ir": _legacy(135.73),
    "La": _legacy(187.9),
    "Li": _legacy(151.94, note="M&S print 151.94; compilations spread 152-157 for soft bcc Li.", flags=("radius spread 152-157 pm across compilations",)),
    "Mg": _legacy(160.13),
    "Mn": _legacy(135.0, extra_notes="LA-4003 tabulates dual-valence Mn(5)/Mn(7); our 7 follows the s+d convention."),
    "Mo": _legacy(136.26, note=_BCC_NOTE),
    "Nb": _legacy(142.9, note=_BCC_NOTE),
    "Ni": _legacy(124.59),
    "Os": _legacy(135.23),
    "Pd": _legacy(137.54),
    "Pt": _legacy(138.7),
    "Re": _legacy(137.5),
    "Rh": _legacy(134.5),
    "Ru": _legacy(133.84),
    "Sc": _legacy(164.1),
    "Si": _legacy(115.3, note="M&S print 115.3 (their covalent-scale family).", extra_notes="Covalent-scale radius (111), deliberate exception to the metallic CN12 convention; LA-4003's CN12 equivalent is 132.2.", flags=("covalent-scale radius, see notes",)),
    "Sn": _legacy(162.0, extra_notes="beta-Sn; LA-4003 tabulates Sn(2)/Sn(4) dual valence, ours is 4."),
    "Ta": _legacy(143.0, note=_BCC_NOTE),
    "Ti": _legacy(146.15),
    "V": _legacy(131.6, note=_BCC_NOTE),
    "W": _legacy(136.7, note=_BCC_NOTE),
    "Y": _legacy(180.15, extra_notes="LA-4003 deliberately lists Y at 177.3 (alloying-behavior-adjusted) instead of the 180.1 lattice value; our 182 follows the legacy digitization."),
    "Zn": _legacy(139.45, flags=("hcp-anisotropic; compilations spread 134-139 pm",)),
    "Zr": _legacy(160.25),
    # v2.1 additions (LA-4003 Table I read 2026-07-22)
    "Bi": _la4003(160.0, note="M&S print the covalent-scale 160.", extra_notes="LA-4003 168.9 via Pauling bond-number conversion (A7 structure); Takeuchi-Inoue-style tables use ~170.", flags=("radius spread 160-170 pm across conventions",)),
    "Dy": _la4003(177.4),
    "Er": _la4003(175.58),
    "Ga": _la4003(139.2, note="M&S print 139.2; classic Goldschmidt tables 141.", extra_notes="LA-4003 135.3 via Pauling bond-number conversion (A11 structure); chosen for consistency with Al/In which match LA-4003 exactly.", flags=("radius spread 135-141 pm across conventions",)),
    "Ge": ElementSources(radius_source_key="ms2017", crosscheck_radius_pm=None, crosscheck_note="", notes="Covalent-scale 124 (M&S Table 3) to stay consistent with our Si 111; LA-4003's CN12 equivalent is 137.8.", flags=("covalent-scale radius, deliberate exception",)),
    "Ho": _la4003(176.61, extra_notes="CRC melting 1745 K; WebElements-derived tables print 1734 K."),
    "Lu": _la4003(173.49, extra_notes="CRC melting 1936 K; some tables print 1925 K."),
    "Nd": _la4003(164.0, note="M&S print 164, an evident misprint (their Ce is 182.47, Sm 181).", flags=("M&S Table 3 radius is a misprint; LA-4003/Gschneidner 182.2 is correct",)),
    "Pb": _la4003(174.97),
    "Pr": _la4003(165.0, note="M&S print 165, an evident misprint (neighbors Ce 182.47, Nd ~182).", flags=("M&S Table 3 radius is a misprint; LA-4003/Gschneidner 182.8 is correct",)),
    "Sb": _la4003(145.0, note="M&S print the covalent-scale 145.", extra_notes="LA-4003 157.1 via Pauling bond-number conversion; keeps Sb consistent with metallic In 167 / Sn 158 in solder alloys.", flags=("radius spread 145-157 pm across conventions",)),
    "Sm": _la4003(181.0),
    "Sr": _la4003(215.2),
    "Tb": _la4003(178.14, extra_notes="CRC melting 1632 K; WebElements-derived tables print 1629 K. chi 1.10 as printed (non-monotonic vs Gd 1.20 / Dy 1.22)."),
    "Th": _la4003(None, extra_notes="Not in M&S Table 3 (stops at Bi). CRC melting 2023 K; some compilations print 2115 K - a genuine literature spread, CRC/LA-4003 agree on ~2023.", flags=("melting-point literature spread 2023 vs 2115 K",)),
    "Tm": _la4003(156.0, note="M&S print 156, an evident misprint (neighbors Er 175.58, Lu 173.49).", flags=("M&S Table 3 radius is a misprint; LA-4003/Gschneidner 174.7 is correct",)),
    "U": _la4003(None, extra_notes="Not in M&S Table 3. Radius via Pauling bond-number conversion (alpha-U). VEC 6 is the Zachariasen metallic valence adopted by LA-4003; the strict s+d count would give 3.", flags=("VEC convention choice: 6 (Zachariasen) vs 3 (strict s+d); 6 adopted",)),
    "Yb": _la4003(170.0, note="M&S print 170 with lanthanide VEC 3.", extra_notes="Metallic Yb is divalent (4f14 6s2, fcc): radius 193.9 = LA-4003 Yb(2), VEC 2 for consistency with that state. LA-4003's trivalent Yb(3) 174.1 is an author interpolation. chi 1.1 approximate.", flags=("divalent metal: VEC 2 here, M&S assign 3", "chi approximate (1.1)")),
}
