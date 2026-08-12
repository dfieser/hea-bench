"""Tests for the constrained composition search."""

import json
import pathlib

import pytest

from hea_bench.design import (
    CompositionConstraint,
    DomainConstraint,
    Maximize,
    Minimize,
    PropertyConstraint,
    RuleConstraint,
    search,
)

_DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "data" / "consolidated"

needs_corpus = pytest.mark.skipif(
    not (_DATA_DIR / "v0.1.0" / "consolidated.csv").exists(),
    reason="benchmark corpus not built (the default domain constraint needs it)",
)

# The tests opt out of the corpus-backed domain gate where they only
# exercise mechanics, so they run on a bare checkout too.
NO_DOMAIN = DomainConstraint(in_domain=None)


def _tiny_search(**overrides):
    settings = dict(
        elements=["Al", "Fe", "W"],
        n_elements=(2, 3),
        constraints=(NO_DOMAIN,),
        objectives=(Minimize("density"), Minimize("cost_per_kg")),
        step=0.2,
        seed=0,
    )
    settings.update(overrides)
    return search(**settings)


def test_search_is_deterministic_given_a_seed() -> None:
    first = _tiny_search()
    second = _tiny_search()
    assert first.to_json() == second.to_json()
    assert first.seed == 0
    assert first.settings["step"] == 0.2


def test_front_is_mutually_non_dominated() -> None:
    result = _tiny_search()
    assert result.n_feasible > 0
    values = [
        (
            candidate.objective_values["density"],
            candidate.objective_values["cost_per_kg"],
        )
        for candidate in result.candidates
    ]
    for i, a in enumerate(values):
        for j, b in enumerate(values):
            if i == j:
                continue
            assert not (b[0] <= a[0] and b[1] <= a[1] and b != a), (a, b)


def test_candidates_carry_full_receipts() -> None:
    result = _tiny_search()
    candidate = result.candidates[0]
    assert abs(sum(candidate.composition.values()) - 1.0) < 1e-9
    assert candidate.descriptors["smix"] is not None
    assert len(candidate.rules) == 9
    assert candidate.properties["density"].unit == "g/cm^3"
    assert candidate.novelty is None or "in_domain" in candidate.novelty


def test_composition_constraint_bounds_the_lattice() -> None:
    result = _tiny_search(
        constraints=(NO_DOMAIN, CompositionConstraint("W", max=0.4)),
    )
    assert result.n_feasible > 0
    for candidate in result.candidates:
        assert candidate.composition.get("W", 0.0) <= 0.4 + 1e-9


def test_property_constraint_filters_the_front() -> None:
    result = _tiny_search(
        constraints=(NO_DOMAIN, PropertyConstraint("density", max=8.0)),
    )
    for candidate in result.candidates:
        assert candidate.properties["density"].value <= 8.0 + 1e-9


def test_rule_constraint_matches_verdicts() -> None:
    result = search(
        elements=["Co", "Cr", "Fe", "Mn", "Ni"],
        n_elements=(5, 5),
        constraints=(NO_DOMAIN, RuleConstraint("guo_vec", satisfied="FCC")),
        objectives=(Minimize("cost_per_kg"),),
        step=0.2,
    )
    assert result.n_feasible > 0
    for candidate in result.candidates:
        assert candidate.rules["guo_vec"] == "FCC"


def test_uncovered_palette_element_is_typed() -> None:
    with pytest.raises(ValueError, match="Fr"):
        _tiny_search(elements=["Fe", "Fr"])


def test_budget_cap_refuses_rather_than_truncating() -> None:
    with pytest.raises(ValueError, match="max_evaluations"):
        search(
            elements=["Al", "Co", "Cr", "Cu", "Fe", "Mn", "Ni", "Ti"],
            n_elements=(5, 8),
            constraints=(NO_DOMAIN,),
            objectives=(Minimize("density"),),
            step=0.05,
            max_evaluations=100,
        )


def test_n_candidates_truncation_is_recorded_not_silent() -> None:
    result = _tiny_search(n_candidates=2)
    assert len(result.candidates) <= 2
    assert result.n_front >= len(result.candidates)


def test_result_round_trips_through_json() -> None:
    payload = json.loads(_tiny_search().to_json())
    assert payload["seed"] == 0
    assert payload["n_evaluated"] > 0
    assert payload["candidates"][0]["objective_values"]


@needs_corpus
def test_domain_constraint_is_on_by_default() -> None:
    result = search(
        elements=["Co", "Cr", "Fe", "Mn", "Ni"],
        n_elements=(4, 5),
        objectives=(Minimize("cost_per_kg"),),
        step=0.25,
    )
    assert result.n_feasible > 0
    for candidate in result.candidates:
        assert candidate.in_domain is True


def test_hardness_objective_uses_conservative_bound() -> None:
    pytest.importorskip("sklearn")
    result = search(
        elements=["Al", "Co", "Cr", "Fe", "Ni"],
        n_elements=(4, 5),
        constraints=(NO_DOMAIN,),
        objectives=(Maximize("hardness"), Minimize("density")),
        step=0.25,
        optimize_bound="lower",
    )
    assert result.n_feasible > 0
    candidate = result.candidates[0]
    low, high = candidate.properties["hardness"].interval
    assert candidate.objective_values["hardness"] == pytest.approx(low)
