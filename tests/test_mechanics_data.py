"""Tests for the per-element mechanics loader (miedema_parameters.csv).

The upstream matminer ``Miedema.csv`` column named ``compressibility``
actually holds the bulk modulus in GPa (Fe = 168.3, Al = 72.18); the
loader re-labels it honestly. ``molar_volume`` is cm3/mol.
"""

import pytest

from hea_bench.descriptors.data.elemental import ELEMENTAL_DATA
from hea_bench.descriptors.data.mechanics import covered_mechanics, mechanics


def test_fe_values() -> None:
    m = mechanics("Fe")
    assert m is not None
    assert m.molar_volume_cm3 == pytest.approx(7.09)
    assert m.bulk_modulus_gpa == pytest.approx(168.3)
    assert m.shear_modulus_gpa == pytest.approx(81.52)


def test_al_and_sr_values() -> None:
    al = mechanics("Al")
    assert al.molar_volume_cm3 == pytest.approx(10.0)
    assert al.bulk_modulus_gpa == pytest.approx(72.18)
    sr = mechanics("Sr")
    assert sr.molar_volume_cm3 == pytest.approx(33.93)
    assert sr.bulk_modulus_gpa == pytest.approx(11.62)
    assert sr.shear_modulus_gpa == pytest.approx(5.229)


def test_unknown_element_returns_none() -> None:
    assert mechanics("Xx") is None


def test_all_55_elements_covered() -> None:
    """Every element in ELEMENTAL_DATA has usable B and V (needed so
    the Andreoli elastic term is computable across the whole table)."""
    for sym in ELEMENTAL_DATA:
        m = mechanics(sym)
        assert m is not None, sym
        assert m.molar_volume_cm3 > 0, sym
        assert m.bulk_modulus_gpa > 0, sym
    assert set(ELEMENTAL_DATA) <= covered_mechanics()
