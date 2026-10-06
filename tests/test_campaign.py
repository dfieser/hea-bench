"""Tests for the active-learning campaign loop."""

import json

import pytest

from hea_bench.design import DomainConstraint
from hea_bench.design.campaign import Campaign, ColdStartError, Suggestion

PALETTE = ["Al", "Co", "Cr", "Fe", "Ni"]
NO_DOMAIN = DomainConstraint(in_domain=None)


def _campaign(**overrides):
    settings = dict(
        objective="hardness",
        palette=PALETTE,
        constraints=(NO_DOMAIN,),
        seed=1,
        step=0.25,
        n_elements=(4, 5),
    )
    settings.update(overrides)
    return Campaign(**settings)


def test_campaign_round_trips_through_json(tmp_path) -> None:
    campaign = _campaign(warm_start=False)
    campaign.observe({"Al": 0.25, "Co": 0.25, "Cr": 0.25, "Fe": 0.25}, 480.0)
    campaign.observe(
        {"Co": 0.25, "Cr": 0.25, "Fe": 0.25, "Ni": 0.25}, 150.0, processing="CAST"
    )
    path = tmp_path / "campaign.json"
    campaign.save(path)

    loaded = Campaign.load(path)
    second = tmp_path / "again.json"
    loaded.save(second)
    assert path.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == 1
    assert payload["objective"] == "hardness"
    assert len(payload["observations"]) == 2
    assert payload["observations"][1]["processing"] == "CAST"


def test_cold_start_floor_refuses(tmp_path) -> None:
    campaign = _campaign(objective="my_quantity", warm_start=False)
    for index in range(3):
        campaign.observe(
            {"Al": 0.25, "Co": 0.25, "Cr": 0.25, "Fe": 0.25 - 0.01 * index, "Ni": 0.01 * index},
            100.0 + index,
        )
    with pytest.raises(ColdStartError, match="10"):
        campaign.suggest(n=2)


def test_unknown_strategy_is_rejected() -> None:
    pytest.importorskip("sklearn")
    campaign = _campaign()
    with pytest.raises(ValueError, match="strategy"):
        campaign.suggest(n=1, strategy="magic")


def test_warm_start_reaches_the_floor_without_user_data() -> None:
    pytest.importorskip("sklearn")
    campaign = _campaign()
    assert campaign.n_informative() >= 10
    suggestions = campaign.suggest(n=3)
    assert len(suggestions) == 3
    seen = set()
    for suggestion in suggestions:
        assert isinstance(suggestion, Suggestion)
        assert set(suggestion.composition) <= set(PALETTE)
        low, high = suggestion.interval
        assert low <= suggestion.mean <= high
        key = tuple(sorted(suggestion.composition.items()))
        assert key not in seen
        seen.add(key)


def test_suggestion_repr_carries_interval_and_domain() -> None:
    pytest.importorskip("sklearn")
    suggestion = _campaign().suggest(n=1)[0]
    text = repr(suggestion)
    assert "in_domain" in text
    assert "interval" in text


def test_suggestions_are_deterministic_given_seed() -> None:
    pytest.importorskip("sklearn")
    first = _campaign().suggest(n=2)
    second = _campaign().suggest(n=2)
    assert [s.composition for s in first] == [s.composition for s in second]


def test_observed_points_are_not_resuggested() -> None:
    pytest.importorskip("sklearn")
    campaign = _campaign()
    first = campaign.suggest(n=1)[0]
    campaign.observe(first.composition, 500.0)
    second = campaign.suggest(n=1)[0]
    assert second.composition != first.composition


def test_ucb_strategy_runs() -> None:
    pytest.importorskip("sklearn")
    suggestions = _campaign().suggest(n=2, strategy="ucb")
    assert len(suggestions) == 2
    assert all(s.strategy == "ucb" for s in suggestions)


def test_property_constraint_bounds_the_pool_and_suggestions() -> None:
    pytest.importorskip("sklearn")
    from hea_bench.design import PropertyConstraint
    from hea_bench.properties import density

    unbounded = _campaign()._pool()
    bounded_campaign = _campaign(
        constraints=(NO_DOMAIN, PropertyConstraint("density", max=7.0))
    )
    bounded = bounded_campaign._pool()
    assert 0 < len(bounded) < len(unbounded)
    assert all(density(comp) <= 7.0 for comp in bounded)
    for suggestion in bounded_campaign.suggest(n=2):
        assert density(suggestion.composition) <= 7.0
