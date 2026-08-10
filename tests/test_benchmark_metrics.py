"""Tests for hea_bench.benchmark.metrics (imbalance-aware scoring)."""

import pytest

from hea_bench.benchmark.metrics import aggregate, score, standard_error


def test_perfect_predictions_score_one() -> None:
    labels = ["BCC", "FCC", "HCP", "multi-phase", "BCC"]
    got = score(labels, labels)
    assert got.accuracy == 1.0
    assert got.balanced_accuracy == 1.0
    assert got.macro_f1 == 1.0
    assert got.mcc == pytest.approx(1.0)


def test_majority_predictor_is_caught_by_balanced_accuracy() -> None:
    """The headline case for why accuracy alone is the wrong metric here.

    Nine of ten rows are multi-phase, so always guessing it looks 90%
    accurate while being worth nothing.
    """
    observations = ["multi-phase"] * 9 + ["BCC"]
    predictions = ["multi-phase"] * 10
    got = score(predictions, observations)
    assert got.accuracy == pytest.approx(0.9)
    assert got.balanced_accuracy == pytest.approx(0.5)
    assert got.mcc == 0.0


def test_balanced_accuracy_is_mean_per_class_recall() -> None:
    # BCC recall 1/2, FCC recall 2/2 -> 0.75
    observations = ["BCC", "BCC", "FCC", "FCC"]
    predictions = ["BCC", "FCC", "FCC", "FCC"]
    got = score(predictions, observations)
    assert got.balanced_accuracy == pytest.approx(0.75)
    assert got.accuracy == pytest.approx(0.75)


def test_mcc_is_negative_when_predictions_are_inverted() -> None:
    observations = ["BCC", "BCC", "FCC", "FCC"]
    predictions = ["FCC", "FCC", "BCC", "BCC"]
    assert score(predictions, observations).mcc == pytest.approx(-1.0)


def test_class_never_predicted_still_counts_against_the_model() -> None:
    """A missed class must not be silently dropped from the averages."""
    observations = ["BCC", "BCC", "HCP", "HCP"]
    predictions = ["BCC", "BCC", "BCC", "BCC"]
    got = score(predictions, observations)
    assert got.balanced_accuracy == pytest.approx(0.5)
    assert got.macro_f1 < 0.5


def test_confusion_matrix_is_observed_by_predicted() -> None:
    got = score(["FCC", "FCC"], ["BCC", "FCC"])
    assert got.confusion[("BCC", "FCC")] == 1
    assert got.confusion[("FCC", "FCC")] == 1
    assert got.confusion[("FCC", "BCC")] == 0


def test_score_rejects_mismatched_and_empty_input() -> None:
    with pytest.raises(ValueError, match="same length"):
        score(["BCC"], ["BCC", "FCC"])
    with pytest.raises(ValueError, match="empty"):
        score([], [])


def test_standard_error_is_zero_for_one_fold() -> None:
    assert standard_error([0.5]) == 0.0
    assert standard_error([]) == 0.0


def test_standard_error_matches_the_textbook_formula() -> None:
    # sample sd of (1,2,3,4) is sqrt(5/3); se divides by sqrt(4)
    assert standard_error([1.0, 2.0, 3.0, 4.0]) == pytest.approx((5 / 3) ** 0.5 / 2)


def test_aggregate_reports_mean_and_se_per_metric() -> None:
    folds = [
        score(["BCC", "FCC"], ["BCC", "FCC"]),
        score(["BCC", "BCC"], ["BCC", "FCC"]),
    ]
    summary = aggregate(folds)
    assert summary["n_folds"] == 2
    assert summary["n_scored"] == 4
    assert summary["accuracy_mean"] == pytest.approx(0.75)
    assert summary["accuracy_se"] > 0.0


def test_aggregate_rejects_zero_folds() -> None:
    with pytest.raises(ValueError, match="zero folds"):
        aggregate([])
