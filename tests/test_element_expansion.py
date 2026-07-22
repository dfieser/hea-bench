"""Tests for the v2.1 element expansion (37 -> 55).

Every new value was read from the primary sources during the v2.1
design verification (2026-07-22): radii from Teatum, Gschneidner &
Waber, LA-4003 (1968) Table I (except Ge, covalent-scale by the
table's Si convention, per Miracle & Senkov 2017 Table 3); melting
points from the CRC Handbook consistent set; VEC per the Guo s+d
convention (lanthanides 3, Yb divalent 2, U Zachariasen 6, Th 4);
electronegativities from the Pauling/WebElements consistent set.
"""

import pytest

from hea_bench.descriptors.data.elemental import (
    ELEMENTAL_DATA,
    covered_elements,
    missing_elements,
)

# (radius_pm, melting_K, valence, electronegativity)
NEW_ELEMENTS = {
    "Bi": (168.9, 544.55, 5, 2.02),
    "Dy": (177.5, 1685.0, 3, 1.22),
    "Er": (175.8, 1802.0, 3, 1.24),
    "Ga": (135.3, 302.91, 3, 1.81),
    "Ge": (124.0, 1211.40, 4, 2.01),
    "Ho": (176.7, 1745.0, 3, 1.23),
    "Lu": (173.5, 1936.0, 3, 1.27),
    "Nd": (182.2, 1289.0, 3, 1.14),
    "Pb": (175.0, 600.61, 4, 2.33),
    "Pr": (182.8, 1204.0, 3, 1.13),
    "Sb": (157.1, 903.78, 5, 2.05),
    "Sm": (180.2, 1345.0, 3, 1.17),
    "Sr": (215.1, 1050.0, 2, 0.95),
    "Tb": (178.3, 1632.0, 3, 1.10),
    "Th": (179.8, 2023.0, 4, 1.30),
    "Tm": (174.7, 1818.0, 3, 1.25),
    "U": (154.3, 1408.0, 6, 1.38),
    "Yb": (193.9, 1097.0, 2, 1.10),
}


def test_table_has_55_elements() -> None:
    assert len(ELEMENTAL_DATA) == 55
    assert len(covered_elements()) == 55


@pytest.mark.parametrize("symbol", sorted(NEW_ELEMENTS))
def test_new_element_values(symbol: str) -> None:
    radius, melting, valence, chi = NEW_ELEMENTS[symbol]
    props = ELEMENTAL_DATA[symbol]
    assert props.radius_pm == pytest.approx(radius, abs=1e-9)
    assert props.melting_K == pytest.approx(melting, abs=1e-9)
    assert props.valence == valence
    assert props.electronegativity == pytest.approx(chi, abs=1e-9)


def test_rare_earth_block_is_complete() -> None:
    """The experimentally active REHEA palette is fully covered."""
    rehea = {"Sc", "Y", "La", "Ce", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Lu", "Nd", "Pr", "Sm", "Yb"}
    assert not missing_elements(rehea)


def test_original_37_untouched() -> None:
    """Spot-check legacy values are byte-identical after the expansion."""
    assert ELEMENTAL_DATA["Al"].radius_pm == 143.0
    assert ELEMENTAL_DATA["Al"].melting_K == 933.47
    assert ELEMENTAL_DATA["Fe"].valence == 8
    assert ELEMENTAL_DATA["Y"].radius_pm == 182.0
    assert ELEMENTAL_DATA["Zn"].valence == 12
    assert ELEMENTAL_DATA["Si"].radius_pm == 111.0


def test_lanthanide_vec_convention() -> None:
    """Lanthanides carry VEC 3 (LA-4003 / M&S convention); metallic Yb is
    the deliberate divalent exception, documented in the table."""
    for el in ("La", "Ce", "Pr", "Nd", "Sm", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Lu"):
        assert ELEMENTAL_DATA[el].valence == 3, el
    assert ELEMENTAL_DATA["Yb"].valence == 2
