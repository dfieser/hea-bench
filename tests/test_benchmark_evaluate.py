"""Tests for hea_bench.benchmark.evaluate (paired grouped vs random scoring)."""

import pytest

from hea_bench.benchmark.corpus import Benchmark, BenchmarkRow
from hea_bench.benchmark.evaluate import MajorityClass, evaluate
from hea_bench.benchmark.splits import family_of, grouped_split, random_split


def _synthetic_benchmark(n_families: int = 20, per_family: int = 6) -> Benchmark:
    """A corpus where the label is a pure function of the alloy family.

    Every family gets one label, so a model that memorizes families can
    score perfectly under the random split, where it always sees a
    family in training, and no better than chance on families it has
    never seen. That is dependence on close training relatives in its purest
    form and makes the two schemes provably disagree.
    """
    elements = ["Al", "Co", "Cr", "Fe", "Ni", "Ti", "V", "Zr", "Nb", "Mo"]
    rows = []
    for family_index in range(n_families):
        first = elements[family_index % len(elements)]
        second = elements[(family_index // len(elements) + 1) % len(elements)]
        label = "single-phase" if family_index % 2 else "multi-phase"
        for variant in range(per_family):
            amount = 0.1 + 0.1 * variant
            composition = {first: amount, second: 1.0 - amount}
            rows.append(
                BenchmarkRow(
                    composition_key=f"{first}{amount:.4f}{second}{1 - amount:.4f}",
                    composition=composition,
                    family=family_of(composition),
                    label=label,
                    canonical_phase=label,
                    sources=("synthetic",),
                    n_elements=2,
                    descriptor_ready=True,
                )
            )
    labels = [row.label for row in rows]
    families = [row.family for row in rows]
    return Benchmark(
        corpus_version="test",
        task="single_vs_multi",
        rows=tuple(rows),
        grouped=grouped_split(families, labels, k=5),
        random=random_split(labels, k=5, seed=0),
        manifest={},
    )


class FamilyLookup:
    """Memorizes each training family's label; guesses a constant otherwise.

    A deliberately extreme stand-in for a model that has learned the
    corpus rather than the physics.
    """

    name = "family-lookup"

    def __init__(self) -> None:
        self._table: dict[str, str] = {}

    def fit(self, compositions, labels) -> "FamilyLookup":
        self._table = {}
        for composition, label in zip(compositions, labels):
            self._table[family_of(composition)] = label
        return self

    def predict(self, compositions) -> list[str]:
        return [self._table.get(family_of(c), "multi-phase") for c in compositions]


# --- the paired contrast ---------------------------------------------------


def test_random_split_rewards_a_family_memorizer() -> None:
    """The behaviour the whole benchmark exists to measure."""
    report = evaluate(FamilyLookup(), _synthetic_benchmark())
    # Not exactly 1.0: a family whose variants all happen to land in one
    # test fold is unseen in that fold's training rows even under the
    # random split, so the memorizer falls back there.
    assert report.random.summary["balanced_accuracy_mean"] > 0.90
    assert report.grouped.summary["balanced_accuracy_mean"] < 0.75
    assert report.gap["balanced_accuracy"] > 0.25


def test_both_schemes_score_the_same_rows() -> None:
    bench = _synthetic_benchmark()
    report = evaluate(FamilyLookup(), bench)
    assert report.grouped.summary["n_scored"] == report.random.summary["n_scored"] == len(bench)


def test_report_carries_its_provenance() -> None:
    bench = _synthetic_benchmark()
    report = evaluate(FamilyLookup(), bench)
    assert report.grouped.digest == bench.grouped.digest
    assert report.random.digest == bench.random.digest
    assert report.corpus_version == "test"
    assert report.task == "single_vs_multi"
    assert report.hea_bench_version


def test_a_fixed_predictor_shows_no_gap() -> None:
    """A rule has no fitted parameters, so it has nothing to leak."""

    def always_multi(composition) -> str:
        return "multi-phase"

    report = evaluate(always_multi, _synthetic_benchmark())
    assert report.gap["balanced_accuracy"] == pytest.approx(0.0, abs=1e-9)


# --- model protocol --------------------------------------------------------


def test_majority_class_scores_chance_on_balanced_accuracy() -> None:
    report = evaluate(MajorityClass(), _synthetic_benchmark())
    assert report.grouped.summary["balanced_accuracy_mean"] == pytest.approx(0.5)
    assert report.grouped.summary["mcc_mean"] == pytest.approx(0.0)


def test_majority_class_breaks_ties_alphabetically() -> None:
    model = MajorityClass().fit([{"Al": 1.0}, {"Ni": 1.0}], ["FCC", "BCC"])
    assert model.predict([{"Al": 1.0}]) == ["BCC"]


def test_majority_class_refuses_to_predict_before_fit() -> None:
    with pytest.raises(ValueError, match="before fit"):
        MajorityClass().predict([{"Al": 1.0}])


def test_evaluate_rejects_a_model_that_is_neither_callable_nor_trainable() -> None:
    with pytest.raises(ValueError, match="fit/predict"):
        evaluate(object(), _synthetic_benchmark())


def test_evaluate_rejects_an_empty_index_list() -> None:
    with pytest.raises(ValueError, match="empty"):
        evaluate(MajorityClass(), _synthetic_benchmark(), indices=[])


def test_evaluate_catches_a_model_returning_the_wrong_count() -> None:
    class Truncating(FamilyLookup):
        def predict(self, compositions) -> list[str]:
            return super().predict(compositions)[:-1]

    with pytest.raises(ValueError, match="predictions for"):
        evaluate(Truncating(), _synthetic_benchmark())


def test_explicit_indices_restrict_the_rows_without_moving_folds() -> None:
    bench = _synthetic_benchmark()
    subset = tuple(index for index in range(len(bench)) if index % 2 == 0)
    report = evaluate(MajorityClass(), bench, indices=subset)
    assert report.n_rows_evaluated == len(subset)
    assert report.grouped.summary["n_scored"] == len(subset)
    # Fold identity is unchanged, so the digest still describes the split.
    assert report.grouped.digest == bench.grouped.digest


def test_table_renders_both_columns_and_the_gap() -> None:
    text = evaluate(MajorityClass(), _synthetic_benchmark()).table()
    assert "grouped (extrapolative)" in text
    assert "random (interpolative)" in text
    assert "balanced_accuracy" in text
