"""Tests for the closed-form (tier A) property estimates."""

import pytest

from hea_bench.properties.data.atomic_masses import ATOMIC_MASS_G_MOL
from hea_bench.properties.tier_a import density

CANTOR = {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}


def test_pure_element_density_is_mass_over_volume() -> None:
    """The rule of mixtures must collapse to the elemental ratio."""
    from hea_bench.descriptors.data.mechanics import mechanics

    iron = mechanics("Fe")
    expected = ATOMIC_MASS_G_MOL["Fe"] / iron.molar_volume_cm3
    assert density({"Fe": 1.0}) == pytest.approx(expected)


def test_cantor_density_lands_near_the_experimental_value() -> None:
    """Rule-of-mixtures over vendored tables; experiment is near 8.0 g/cm3."""
    assert density(CANTOR) == pytest.approx(8.0, abs=0.25)


def test_density_normalizes_proportional_amounts() -> None:
    assert density({"Co": 1, "Cr": 1, "Fe": 1, "Mn": 1, "Ni": 1}) == pytest.approx(
        density(CANTOR)
    )


def test_density_returns_none_for_uncovered_elements() -> None:
    """Typed absence, never a guess: Fr has no mass/volume row."""
    assert density({"Fr": 0.5, "Co": 0.5}) is None


def test_density_returns_none_where_mechanics_has_no_row() -> None:
    """Oxygen has a mass but no molar-volume row; the answer is None."""
    assert density({"O": 0.5, "Co": 0.5}) is None


def test_atomic_mass_table_is_sane() -> None:
    assert ATOMIC_MASS_G_MOL["Fe"] == pytest.approx(55.845, abs=0.001)
    assert ATOMIC_MASS_G_MOL["W"] == pytest.approx(183.84, abs=0.01)
    assert len(ATOMIC_MASS_G_MOL) >= 70
