"""Tests for the elemental data table and the simple descriptors
(δ, VEC, T_m). Miedema-based descriptors live in their own test file
once Phase 2c lands."""

import pytest

from hea_bench.descriptors.data.elemental import (
    ELEMENTAL_DATA,
    covered_elements,
    missing_elements,
)
from hea_bench.descriptors.melting import melting_temperature
from hea_bench.descriptors.size import delta
from hea_bench.descriptors.vec import vec

# Cantor alloy, the field's canonical sanity check.
_CANTOR = {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}


# ---- elemental data table ----

def test_table_has_37_elements() -> None:
    """The original 24 legacy elements plus the six v1.2 additions
    (Mg, Zn, Sn, Re, Au, Li) plus the seven v1.3 additions
    (Be, Ca, Ce, Gd, In, La, Sc). B, C, and N are deliberately
    excluded; see the elemental.py docstring."""
    assert len(ELEMENTAL_DATA) == 37


def test_v12_v13_additions_present_bcn_absent() -> None:
    """The v1.2 and v1.3 metals are in the table; the three problematic
    non-metals are not."""
    assert {"Mg", "Zn", "Sn", "Re", "Au", "Li"} <= covered_elements()
    assert {"Be", "Ca", "Ce", "Gd", "In", "La", "Sc"} <= covered_elements()
    assert "B" not in covered_elements()
    assert "C" not in covered_elements()
    assert "N" not in covered_elements()


def test_v12_added_element_values_pinned() -> None:
    """Cross-verified per-element scalars for the six v1.2 additions.

    Radii are Goldschmidt 12-coordinate metallic radii (Housecroft &
    Sharpe Appendix 6, matching the original 24's convention); melting
    points are CRC; valences follow the s+d / group-number convention
    used throughout the table. See elemental.py for the per-element
    source comments and noted alternatives."""
    expected = {
        "Mg": (160.0, 923.15, 2),
        "Zn": (137.0, 692.68, 12),
        "Sn": (158.0, 505.08, 4),
        "Re": (137.0, 3459.15, 7),
        "Au": (144.0, 1337.33, 11),
        "Li": (157.0, 453.65, 1),
    }
    for sym, (radius, melting, valence) in expected.items():
        props = ELEMENTAL_DATA[sym]
        assert props.radius_pm == pytest.approx(radius, abs=1e-9), sym
        assert props.melting_K == pytest.approx(melting, abs=1e-9), sym
        assert props.valence == valence, sym


def test_covered_elements_matches_table_keys() -> None:
    assert covered_elements() == set(ELEMENTAL_DATA)


def test_missing_elements_set_difference() -> None:
    assert missing_elements({"Fe", "Co", "Xx"}) == {"Xx"}
    assert missing_elements({"Fe", "Co"}) == set()


def test_element_properties_frozen() -> None:
    """ElementProperties should be immutable so module-scope values
    can't be mutated accidentally."""
    fe = ELEMENTAL_DATA["Fe"]
    with pytest.raises(AttributeError):
        fe.melting_K = 1800  # type: ignore[misc]


# ---- δ atomic-size mismatch ----

def test_delta_cantor_alloy() -> None:
    """Pinned value against the package's Pauling-style radii. Literature
    reports δ for Cantor at 3.0-3.5% depending on radius source; the value
    we report is internally consistent with our table."""
    assert delta(_CANTOR) == pytest.approx(3.1641, abs=0.0001)


def test_delta_pure_element_is_zero() -> None:
    """Single component → no size mismatch."""
    assert delta({"Fe": 1.0}) == 0.0


def test_delta_normalizes_proportional_inputs() -> None:
    """Same physical composition expressed proportionally must agree."""
    norm = delta({"Co": 0.5, "Fe": 0.5})
    prop = delta({"Co": 5.0, "Fe": 5.0})
    assert prop == pytest.approx(norm, rel=1e-12)


def test_delta_missing_element_raises() -> None:
    with pytest.raises(ValueError, match="not in elemental data table"):
        delta({"Co": 0.5, "Xe": 0.5})


def test_delta_empty_raises() -> None:
    with pytest.raises(ValueError):
        delta({})


# ---- VEC ----

def test_vec_cantor_is_eight() -> None:
    """Guo & Liu (2011) canonical: Cantor VEC = (9+6+8+7+10)/5 = 8.0 exactly."""
    assert vec(_CANTOR) == 8.0


def test_vec_pure_fe() -> None:
    """Fe has valence 8 in the Guo/Liu convention (s+d for TMs)."""
    assert vec({"Fe": 1.0}) == 8.0


def test_vec_binary_al_fe() -> None:
    """Al (3) + Fe (8) at 50/50 → 5.5."""
    assert vec({"Al": 0.5, "Fe": 0.5}) == 5.5


def test_vec_proportional_input_normalizes() -> None:
    eq = vec({"Co": 1, "Cr": 1, "Fe": 1, "Mn": 1, "Ni": 1})
    assert eq == 8.0


def test_vec_missing_element_raises() -> None:
    with pytest.raises(ValueError, match="not in elemental data table"):
        vec({"Co": 0.5, "Xe": 0.5})


# ---- T_m (melting temperature) ----

def test_melting_cantor_is_1801_2() -> None:
    """Linear ROM average of Co/Cr/Fe/Mn/Ni melting points."""
    assert melting_temperature(_CANTOR) == pytest.approx(1801.2, abs=0.01)


def test_melting_pure_fe() -> None:
    assert melting_temperature({"Fe": 1.0}) == 1811.0


def test_melting_proportional_input_normalizes() -> None:
    norm = melting_temperature({"Al": 0.5, "Fe": 0.5})
    prop = melting_temperature({"Al": 2.0, "Fe": 2.0})
    assert prop == pytest.approx(norm, rel=1e-12)


def test_melting_missing_element_raises() -> None:
    with pytest.raises(ValueError, match="not in elemental data table"):
        melting_temperature({"Co": 0.5, "Xe": 0.5})
