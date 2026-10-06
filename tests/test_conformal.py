"""Tests for the stdlib split-conformal wrappers.

The fake models make the arithmetic checkable by hand: the classifier
fake treats each input row as its own probability vector, the regressor
fake always predicts zero, so calibration scores and quantiles are
exactly the numbers written in the tests.
"""

import math

import pytest

from hea_bench.uncertainty import ConformalClassifier, ConformalRegressor


class _ProbabilityEcho:
    """predict_proba returns the input rows unchanged."""

    classes_ = ("A", "B", "C")

    def predict_proba(self, X):
        return [list(row) for row in X]


class _AlwaysZero:
    def predict(self, X):
        return [0.0 for _ in X]


def _fitted_classifier(alpha_unused=None) -> ConformalClassifier:
    # p(true) = 0.9, 0.8, 0.7, 0.6 -> scores 0.1, 0.2, 0.3, 0.4
    X_cal = [
        [0.9, 0.05, 0.05],
        [0.8, 0.10, 0.10],
        [0.7, 0.20, 0.10],
        [0.6, 0.30, 0.10],
    ]
    return ConformalClassifier(_ProbabilityEcho()).fit_calibrate(X_cal, ["A", "A", "A", "A"])


def test_classifier_prediction_set_from_hand_computed_quantile() -> None:
    conformal = _fitted_classifier()
    # alpha 0.2, n 4: k = ceil(5 * 0.8) = 4 -> qhat = 0.4 -> keep p >= 0.6.
    sets = conformal.predict_set([[0.7, 0.25, 0.05], [0.61, 0.3, 0.09]], alpha=0.2)
    assert sets == [{"A"}, {"A"}]
    # alpha 0.5: k = ceil(5 * 0.5) = 3 -> qhat = 0.3 -> keep p >= 0.7.
    sets = conformal.predict_set([[0.7, 0.25, 0.05], [0.65, 0.3, 0.05]], alpha=0.5)
    assert sets == [{"A"}, set()]


def test_classifier_set_can_be_empty_and_that_is_documented_honesty() -> None:
    conformal = _fitted_classifier()
    sets = conformal.predict_set([[0.4, 0.35, 0.25]], alpha=0.5)
    assert sets == [set()]


def test_classifier_degenerate_alpha_returns_full_set() -> None:
    conformal = _fitted_classifier()
    # alpha 0.1, n 4: k = ceil(5 * 0.9) = 5 > n -> guarantee unreachable.
    assert conformal.degenerate(alpha=0.1) is True
    assert conformal.degenerate(alpha=0.5) is False
    sets = conformal.predict_set([[0.99, 0.005, 0.005]], alpha=0.1)
    assert sets == [{"A", "B", "C"}]


def test_regressor_interval_from_hand_computed_quantile() -> None:
    conformal = ConformalRegressor(_AlwaysZero()).fit_calibrate(
        [[0], [1], [2], [3]], [1.0, -2.0, 3.0, -4.0]
    )
    # residuals 1, 2, 3, 4; alpha 0.5: k = 3 -> qhat = 3.
    intervals = conformal.predict_interval([[10], [11]], alpha=0.5)
    assert intervals == [(-3.0, 3.0), (-3.0, 3.0)]


def test_regressor_degenerate_alpha_returns_unbounded_interval() -> None:
    conformal = ConformalRegressor(_AlwaysZero()).fit_calibrate(
        [[0], [1], [2], [3]], [1.0, -2.0, 3.0, -4.0]
    )
    intervals = conformal.predict_interval([[10]], alpha=0.1)
    assert intervals == [(-math.inf, math.inf)]
    assert conformal.degenerate(alpha=0.1) is True


def test_alpha_bounds_and_empty_calibration_are_rejected() -> None:
    with pytest.raises(ValueError, match="calibration"):
        ConformalClassifier(_ProbabilityEcho()).fit_calibrate([], [])
    conformal = _fitted_classifier()
    for bad in (0.0, 1.0, -0.1, 1.5):
        with pytest.raises(ValueError, match="alpha"):
            conformal.predict_set([[0.9, 0.05, 0.05]], alpha=bad)


def test_predict_before_calibration_is_an_error() -> None:
    with pytest.raises(ValueError, match="fit_calibrate"):
        ConformalClassifier(_ProbabilityEcho()).predict_set([[0.9, 0.05, 0.05]])
    with pytest.raises(ValueError, match="fit_calibrate"):
        ConformalRegressor(_AlwaysZero()).predict_interval([[0]])


def test_calibration_label_missing_from_classes_is_rejected() -> None:
    with pytest.raises(ValueError, match="classes"):
        ConformalClassifier(_ProbabilityEcho()).fit_calibrate([[0.9, 0.05, 0.05]], ["D"])


def test_sklearn_random_forest_reaches_nominal_coverage() -> None:
    """End-to-end with a real estimator: empirical coverage near nominal."""
    sklearn_ensemble = pytest.importorskip("sklearn.ensemble")
    import random

    rng = random.Random(0)
    # Two noisy blobs in 2d, labels by blob.
    X = [[rng.gauss(0, 1), rng.gauss(0, 1)] for _ in range(200)]
    X += [[rng.gauss(2.0, 1), rng.gauss(2.0, 1)] for _ in range(200)]
    y = ["low"] * 200 + ["high"] * 200
    paired = list(zip(X, y))
    rng.shuffle(paired)
    train, calibrate, test = paired[:200], paired[200:300], paired[300:]

    model = sklearn_ensemble.RandomForestClassifier(n_estimators=100, random_state=0)
    model.fit([x for x, _ in train], [label for _, label in train])
    conformal = ConformalClassifier(model).fit_calibrate(
        [x for x, _ in calibrate], [label for _, label in calibrate]
    )
    sets = conformal.predict_set([x for x, _ in test], alpha=0.1)
    covered = sum(1 for s, (_, label) in zip(sets, test) if label in s)
    assert covered / len(test) >= 0.85


def test_measured_coverage_matches_the_coverage_card() -> None:
    """The figures the phase-set result quotes (and the app shows next to
    the domain flag) are the ones docs/uncertainty-coverage.md publishes."""
    import re
    from pathlib import Path

    from hea_bench.uncertainty.coverage import MEASURED_COVERAGE

    card = (Path(__file__).resolve().parents[1] / "docs" / "uncertainty-coverage.md").read_text(
        encoding="utf-8"
    )
    published: dict[str, dict[float, tuple[float, float]]] = {}
    for section in re.split(r"^## Task: ", card, flags=re.M)[1:]:
        task = section.split("\n", 1)[0].strip()
        for row in re.finditer(r"^\| (\d+)% \| \d+ \| [\d.]+ \| ([\d.]+) \| ([\d.]+) \|", section, re.M):
            published.setdefault(task, {})[int(row.group(1)) / 100] = (
                float(row.group(2)),
                float(row.group(3)),
            )
    assert published == MEASURED_COVERAGE, (
        "docs/uncertainty-coverage.md and MEASURED_COVERAGE in "
        "src/hea_bench/uncertainty/coverage.py disagree; copy the card's in-domain and "
        "out-of-domain columns into MEASURED_COVERAGE"
    )
