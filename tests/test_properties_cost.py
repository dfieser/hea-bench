"""Tests for the indicative cost estimate."""

import pytest

from hea_bench.properties import PropertyUnavailableError, predict_property
from hea_bench.properties.data.atomic_masses import ATOMIC_MASS_G_MOL
from hea_bench.properties.data.element_prices import PRICE_ASOF, PRICES_USD_PER_KG
from hea_bench.properties.tier_a import cost_breakdown, cost_per_kg

CANTOR = {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}


def test_cost_is_mass_weighted_from_the_table() -> None:
    """Hand-checkable two-element case computed from the same tables."""
    comp = {"Fe": 0.5, "Au": 0.5}
    mass_gold = ATOMIC_MASS_G_MOL["Au"]
    mass_iron = ATOMIC_MASS_G_MOL["Fe"]
    weight_gold = mass_gold / (mass_gold + mass_iron)
    expected = (1 - weight_gold) * PRICES_USD_PER_KG["Fe"][0] + weight_gold * PRICES_USD_PER_KG[
        "Au"
    ][0]
    assert cost_per_kg(comp) == pytest.approx(expected)


def test_cantor_cost_is_an_ordinary_alloy_number() -> None:
    value = cost_per_kg(CANTOR)
    assert 5.0 < value < 60.0


def test_cost_returns_none_for_unpriced_elements() -> None:
    assert cost_per_kg({"Fr": 0.5, "Co": 0.5}) is None


def test_cost_breakdown_carries_basis_and_sums_to_total(monkeypatch) -> None:
    breakdown = cost_breakdown(CANTOR)
    total = sum(entry["contribution_usd_per_kg"] for entry in breakdown.values())
    assert total == pytest.approx(cost_per_kg(CANTOR))
    assert breakdown["Co"]["basis"]
    assert breakdown["Co"]["asof"]
    assert sum(entry["mass_fraction"] for entry in breakdown.values()) == pytest.approx(1.0)


def test_predict_property_cost_is_date_stamped_and_hedged() -> None:
    prediction = predict_property(CANTOR, "cost_per_kg")
    assert prediction.tier == "A"
    assert prediction.unit == "USD/kg"
    assert prediction.asof == PRICE_ASOF
    assert any("indicative" in warning for warning in prediction.warnings)


def test_predict_property_cost_unpriced_is_typed() -> None:
    with pytest.raises(PropertyUnavailableError, match="Fr"):
        predict_property({"Fr": 0.5, "Co": 0.5}, "cost_per_kg")


def test_every_priced_row_is_positive_and_documented() -> None:
    for symbol, (price, basis, asof, source) in PRICES_USD_PER_KG.items():
        assert price > 0, symbol
        assert basis and asof and source, symbol
