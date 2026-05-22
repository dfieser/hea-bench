"""Tests for hea_bench.classifiers.diagnostic_stats."""

import pytest

from hea_bench.classifiers.diagnostic_stats import (
    confusion_matrix,
    evaluate_binary,
    roc_sweep,
    wilson_ci,
)


# ---- wilson_ci ----

def test_wilson_ci_handles_zero_total() -> None:
    assert wilson_ci(0, 0) == (0.0, 0.0)


def test_wilson_ci_at_perfect_accuracy() -> None:
    """All success: upper bound = 1.0, lower bound < 1.0 (Wilson is
    conservative at boundaries)."""
    lo, hi = wilson_ci(10, 10)
    assert 0.7 < lo < 1.0
    assert hi == 1.0


def test_wilson_ci_at_zero_accuracy() -> None:
    lo, hi = wilson_ci(0, 10)
    assert lo == 0.0
    assert 0.0 < hi < 0.3


def test_wilson_ci_known_value() -> None:
    """80/100 — Wilson 95% CI is approximately [0.71, 0.87]."""
    lo, hi = wilson_ci(80, 100)
    assert 0.70 < lo < 0.72
    assert 0.86 < hi < 0.88


def test_wilson_ci_narrows_with_more_data() -> None:
    """Same proportion (80%) at larger n → narrower CI."""
    lo_small, hi_small = wilson_ci(80, 100)
    lo_large, hi_large = wilson_ci(800, 1000)
    assert (hi_large - lo_large) < (hi_small - lo_small)


# ---- confusion_matrix ----

def test_confusion_matrix_simple() -> None:
    preds = ["A", "A", "B", "B"]
    obs   = ["A", "B", "B", "A"]
    cm = confusion_matrix(preds, obs)
    assert cm == {("A", "A"): 1, ("A", "B"): 1, ("B", "B"): 1, ("B", "A"): 1}


def test_confusion_matrix_length_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        confusion_matrix(["A"], ["A", "B"])


# ---- evaluate_binary ----

def test_evaluate_binary_perfect_classifier() -> None:
    preds = ["pos", "pos", "neg", "neg"]
    obs   = ["pos", "pos", "neg", "neg"]
    s = evaluate_binary(preds, obs, "pos")
    assert s.accuracy == 1.0
    assert s.sensitivity == 1.0
    assert s.specificity == 1.0
    assert s.youden_j == 1.0
    assert s.true_positive == 2 and s.true_negative == 2
    assert s.false_positive == 0 and s.false_negative == 0


def test_evaluate_binary_always_positive_classifier() -> None:
    """Always predicts positive — sensitivity = 1, specificity = 0,
    Youden's J = 0 (no skill)."""
    preds = ["pos"] * 4
    obs   = ["pos", "pos", "neg", "neg"]
    s = evaluate_binary(preds, obs, "pos")
    assert s.sensitivity == 1.0
    assert s.specificity == 0.0
    assert s.youden_j == 0.0
    assert s.accuracy == 0.5


def test_evaluate_binary_realistic_imbalanced() -> None:
    """High sensitivity but low specificity — the canonical δ-rule
    failure mode the legacy validator observed (~97% sens, ~15% spec)."""
    # Build a 1000-row dataset: 250 single-phase observed, 750 multi-phase.
    # Predict single for 240 of the singles + 600 of the multis.
    preds = (
        ["single"] * 240 + ["multi"] * 10        # singles
        + ["single"] * 600 + ["multi"] * 150     # multis
    )
    obs = ["single"] * 250 + ["multi"] * 750
    s = evaluate_binary(preds, obs, "single")
    assert s.n == 1000
    assert s.n_positive_observed == 250
    assert s.true_positive == 240
    assert s.false_negative == 10
    assert s.sensitivity == pytest.approx(0.96, abs=0.001)
    assert s.specificity == pytest.approx(0.2, abs=0.001)


def test_evaluate_binary_length_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        evaluate_binary(["A"], ["A", "B"], "A")


# ---- roc_sweep ----

def test_roc_sweep_finds_optimal_threshold() -> None:
    """Synthetic dataset: positives cluster at low descriptor values,
    negatives at high values. The sweep should find a threshold
    between them with high sens + high spec."""
    descriptor_values = [1.0, 2.0, 3.0, 4.0, 7.0, 8.0, 9.0, 10.0]
    obs               = ["pos","pos","pos","pos","neg","neg","neg","neg"]
    thresholds = [0.0, 2.5, 5.5, 10.5]
    points = roc_sweep(descriptor_values, obs, thresholds, "pos", positive_below_threshold=True)
    # Threshold 0 → all predicted neg → sens=0
    assert points[0].sensitivity == 0.0
    # Threshold 5.5 → perfect separation
    perfect = points[2]
    assert perfect.sensitivity == 1.0
    assert perfect.specificity == 1.0
    assert perfect.youden_j == 1.0
    # Threshold 10.5 → all predicted pos → spec=0
    assert points[3].specificity == 0.0


def test_roc_sweep_above_threshold_convention() -> None:
    """For the Ω-rule convention (predict positive when value > thr),
    positive_below_threshold=False inverts the comparison."""
    descriptor_values = [10.0, 9.0, 8.0, 7.0, 4.0, 3.0, 2.0, 1.0]
    obs               = ["pos","pos","pos","pos","neg","neg","neg","neg"]
    points = roc_sweep(descriptor_values, obs, [5.5], "pos", positive_below_threshold=False)
    assert points[0].sensitivity == 1.0
    assert points[0].specificity == 1.0
