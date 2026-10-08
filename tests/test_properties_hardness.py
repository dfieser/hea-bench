"""Tests for the property-prediction API and the tier B hardness surrogate."""

import sys

import pytest

from hea_bench.properties import (
    PropertyPrediction,
    PropertyUnavailableError,
    available_properties,
    predict_property,
    predict_property_batch,
)

CANTOR = {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}
AL_CANTOR = {"Al": 0.2, "Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Ni": 0.2}


def test_available_properties_lists_tiers_and_needs() -> None:
    info = available_properties()
    assert info["density"]["tier"] == "A"
    assert info["melting_temperature"]["tier"] == "A"
    assert info["hardness"]["tier"] == "B"
    assert "hea-bench[properties]" in info["hardness"]["needs"]


def test_unknown_property_is_a_typed_error_listing_choices() -> None:
    with pytest.raises(PropertyUnavailableError, match="hardness"):
        predict_property(CANTOR, "toughness")


def test_density_prediction_is_tier_a_shape() -> None:
    prediction = predict_property(CANTOR, "density")
    assert isinstance(prediction, PropertyPrediction)
    assert prediction.tier == "A"
    assert prediction.unit == "g/cm^3"
    assert prediction.interval is None
    assert prediction.value == pytest.approx(8.0, abs=0.25)
    assert any("closed form" in warning for warning in prediction.warnings)


def test_melting_prediction_is_tier_a_shape() -> None:
    prediction = predict_property(CANTOR, "melting_temperature")
    assert prediction.unit == "K"
    assert prediction.value == pytest.approx(1801.2, abs=1.0)


def test_density_missing_table_rows_raise_typed() -> None:
    with pytest.raises(PropertyUnavailableError, match="Fr"):
        predict_property({"Fr": 0.5, "Co": 0.5}, "density")


def test_missing_sklearn_is_a_typed_error(monkeypatch) -> None:
    import hea_bench.properties.hardness as hardness_mod

    monkeypatch.setitem(sys.modules, "sklearn", None)
    monkeypatch.setitem(sys.modules, "sklearn.ensemble", None)
    hardness_mod._fitted.cache_clear()
    try:
        with pytest.raises(PropertyUnavailableError, match=r"hea-bench\[properties\]"):
            predict_property(CANTOR, "hardness")
    finally:
        hardness_mod._fitted.cache_clear()


# --- the fitted surrogate (needs scikit-learn) -----------------------------

pytest.importorskip("sklearn")


def test_hardness_prediction_carries_interval_and_domain() -> None:
    prediction = predict_property(AL_CANTOR, "hardness", alpha=0.1)
    assert prediction.tier == "B"
    assert prediction.unit == "HV"
    low, high = prediction.interval
    assert low <= prediction.value <= high
    assert prediction.alpha == 0.1
    assert prediction.n_training >= 300
    assert isinstance(prediction.in_domain, bool)
    assert prediction.novelty is not None
    assert prediction.model_card == "docs/property-hardness.md"
    assert 100.0 <= prediction.value <= 1200.0


def test_hardness_is_deterministic() -> None:
    assert predict_property(CANTOR, "hardness") == predict_property(CANTOR, "hardness")


def test_processing_conditioning_shrinks_the_training_set() -> None:
    pooled = predict_property(CANTOR, "hardness")
    cast = predict_property(CANTOR, "hardness", processing="CAST")
    assert cast.n_training < pooled.n_training
    assert cast.n_training >= 50
    assert any("processing" in warning for warning in pooled.warnings)


def test_processing_floor_refuses_rather_than_pretending() -> None:
    with pytest.raises(PropertyUnavailableError, match="WROUGHT"):
        predict_property(CANTOR, "hardness", processing="WROUGHT")


def test_unscorable_composition_is_typed() -> None:
    with pytest.raises(PropertyUnavailableError, match="descriptor"):
        predict_property({"Fr": 0.5, "Co": 0.5}, "hardness")


def test_batch_matches_single_predictions_row_for_row() -> None:
    unscorable = {"Fr": 0.5, "Co": 0.5}
    batch = predict_property_batch([CANTOR, unscorable, AL_CANTOR], "hardness")
    assert batch[0] == predict_property(CANTOR, "hardness")
    assert batch[2] == predict_property(AL_CANTOR, "hardness")
    assert isinstance(batch[1], PropertyUnavailableError)
    density_batch = predict_property_batch([CANTOR, AL_CANTOR], "density")
    assert density_batch == [predict_property(CANTOR, "density"), predict_property(AL_CANTOR, "density")]


def test_the_fitted_forest_predicts_on_one_thread() -> None:
    """Prediction threads add the trees in whatever order they finish, so a
    prediction's last digit would change between calls (_model_cache.serial)."""
    from hea_bench.properties.hardness import _fitted

    assert _fitted(None)[0].n_jobs is None
