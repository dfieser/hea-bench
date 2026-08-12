"""Tests for the domain-of-applicability layer."""

import pathlib

import pytest

from hea_bench.corpus import CorpusRow, load_corpus
from hea_bench.uncertainty import DomainModel, fit_domain, novelty_score

_DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "data" / "consolidated"

needs_corpus = pytest.mark.skipif(
    not (_DATA_DIR / "v0.1.0" / "consolidated.csv").exists(),
    reason="benchmark corpus not built",
)


def _row(composition, ready=True):
    from hea_bench.composition import family_of

    return CorpusRow(
        composition_key="x",
        composition=composition,
        n_elements=len(composition),
        family=family_of(composition),
        sources=("synthetic",),
        canonical_phase="FCC",
        has_conflict=False,
        labels={},
        raw_labels={},
        processing=None,
        doi=None,
        source_row_ids={},
        descriptor_ready=ready,
    )


@pytest.fixture()
def tiny_domain() -> DomainModel:
    rows = [
        _row({"Co": 0.5, "Fe": 0.5}),
        _row({"Co": 0.6, "Fe": 0.4}),
        _row({"Al": 0.4, "Co": 0.3, "Cr": 0.3}),
    ]
    return fit_domain(rows)


def test_seen_family_scores_as_in_domain(tiny_domain) -> None:
    novelty = tiny_domain.novelty({"Co": 0.55, "Fe": 0.45})
    assert novelty["element_set_seen"] is True
    assert novelty["family_count"] == 2
    assert novelty["nearest_family_distance"] == 0.0
    assert novelty["element_coverage"] is True
    assert novelty["descriptor_distance"] is not None
    assert novelty["in_domain"] is True


def test_adjacent_family_distance_is_jaccard(tiny_domain) -> None:
    novelty = tiny_domain.novelty({"Co": 0.4, "Fe": 0.4, "Ni": 0.2})
    assert novelty["element_set_seen"] is False
    assert novelty["family_count"] == 0
    assert novelty["nearest_family_distance"] == pytest.approx(1.0 / 3.0)


def test_uncovered_elements_fail_typed_not_loud(tiny_domain) -> None:
    novelty = tiny_domain.novelty({"Fr": 0.5, "Ra": 0.5})
    assert novelty["element_coverage"] is False
    assert novelty["descriptor_distance"] is None
    assert novelty["in_domain"] is False


def test_components_ship_alongside_the_scalar_rule(tiny_domain) -> None:
    """The single boolean is a convenience; the components are the signal."""
    novelty = tiny_domain.novelty({"Co": 0.5, "Fe": 0.5})
    for key in (
        "element_set_seen",
        "family_count",
        "nearest_family_distance",
        "descriptor_distance",
        "descriptor_distance_threshold",
        "family_distance_threshold",
        "element_coverage",
        "in_domain",
    ):
        assert key in novelty


def test_domain_model_round_trips_through_json(tiny_domain) -> None:
    clone = DomainModel.from_json(tiny_domain.to_json())
    query = {"Co": 0.55, "Fe": 0.45}
    assert clone.novelty(query) == tiny_domain.novelty(query)


def test_fit_domain_needs_at_least_two_scorable_rows() -> None:
    with pytest.raises(ValueError, match="rows"):
        fit_domain([_row({"Co": 0.5, "Fe": 0.5})])


@needs_corpus
def test_cantor_is_in_domain_on_the_real_corpus() -> None:
    corpus = load_corpus()
    domain = fit_domain(corpus)
    cantor = domain.novelty({"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2})
    assert cantor["element_set_seen"] is True
    assert cantor["family_count"] > 100
    assert cantor["in_domain"] is True

    strange = domain.novelty({"Yb": 0.5, "U": 0.5})
    assert strange["element_set_seen"] is False
    assert strange["in_domain"] is False


@needs_corpus
def test_novelty_score_convenience_matches_fit_domain() -> None:
    corpus = load_corpus().query(n_elements=(2, 3), descriptor_ready=True)
    query = {"Co": 0.5, "Fe": 0.5}
    assert novelty_score(query, corpus) == fit_domain(corpus).novelty(query)
