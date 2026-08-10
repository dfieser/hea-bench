"""Classification metrics for the benchmark, computed with the standard library.

Four metrics are reported for every fold, chosen because the corpus is
imbalanced (multi-phase is about half of it) and a single accuracy
number would hide that.

``accuracy``
    Fraction of rows predicted correctly. Easy to read, and easy to
    inflate by always predicting the majority class.
``balanced_accuracy``
    Mean per-class recall. A majority-class predictor scores ``1/C`` on
    a ``C``-class task no matter how skewed the corpus is, which is why
    this is the headline number rather than accuracy.
``macro_f1``
    Unweighted mean of the per-class F1 scores. Penalizes a model that
    reaches high recall on a rare class by over-predicting it.
``mcc``
    Matthews correlation coefficient, multiclass form. Ranges from -1 to
    1 with 0 at chance, and stays honest under class imbalance.

All four are computed from one confusion matrix so a caller can check
them against each other.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class FoldMetrics:
    """Scores for one fold's held-out predictions."""

    n: int
    accuracy: float
    balanced_accuracy: float
    macro_f1: float
    mcc: float
    confusion: dict[tuple[str, str], int]

    def to_dict(self) -> dict:
        """Serialize without the confusion matrix's tuple keys."""
        return {
            "n": self.n,
            "accuracy": self.accuracy,
            "balanced_accuracy": self.balanced_accuracy,
            "macro_f1": self.macro_f1,
            "mcc": self.mcc,
        }


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def standard_error(values: Sequence[float]) -> float:
    """Standard error of the mean across folds. Zero for a single fold."""
    if len(values) <= 1:
        return 0.0
    mean = _mean(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance / len(values))


def score(predictions: Sequence[str], observations: Sequence[str]) -> FoldMetrics:
    """Score one fold's predictions against its observed labels.

    Classes are taken from the union of predicted and observed labels, so
    a model that never emits a rare class is still penalized for missing
    it rather than having that class quietly dropped.

    Raises
    ------
    ValueError
        If the two sequences differ in length or are empty.
    """
    if len(predictions) != len(observations):
        raise ValueError("predictions and observations must have the same length")
    if not predictions:
        raise ValueError("cannot score an empty fold")

    classes = sorted({*predictions, *observations})
    confusion = {(obs, pred): 0 for obs in classes for pred in classes}
    for pred, obs in zip(predictions, observations):
        confusion[(obs, pred)] += 1

    n = len(predictions)
    correct = sum(confusion[(cls, cls)] for cls in classes)

    observed_totals = Counter(observations)
    predicted_totals = Counter(predictions)

    recalls: list[float] = []
    f1s: list[float] = []
    for cls in classes:
        true_positive = confusion[(cls, cls)]
        n_observed = observed_totals[cls]
        n_predicted = predicted_totals[cls]
        # A class nobody observed contributes no recall term; scoring it
        # as zero would punish a model for a class the fold cannot test.
        if n_observed:
            recall = true_positive / n_observed
            recalls.append(recall)
        else:
            recall = 0.0
        precision = true_positive / n_predicted if n_predicted else 0.0
        if n_observed or n_predicted:
            denominator = precision + recall
            f1s.append(2 * precision * recall / denominator if denominator else 0.0)

    return FoldMetrics(
        n=n,
        accuracy=correct / n,
        balanced_accuracy=_mean(recalls),
        macro_f1=_mean(f1s),
        mcc=_matthews(confusion, classes, n),
        confusion=confusion,
    )


def _matthews(
    confusion: dict[tuple[str, str], int],
    classes: Sequence[str],
    n: int,
) -> float:
    """Multiclass Matthews correlation coefficient from a confusion matrix.

    Uses the Gorodkin (2004) generalization. Returns 0.0 when either
    variance term vanishes, which happens when predictions or
    observations are all one class and the coefficient is undefined.
    """
    observed = {cls: sum(confusion[(cls, pred)] for pred in classes) for cls in classes}
    predicted = {cls: sum(confusion[(obs, cls)] for obs in classes) for cls in classes}
    correct = sum(confusion[(cls, cls)] for cls in classes)

    covariance = correct * n - sum(observed[cls] * predicted[cls] for cls in classes)
    observed_variance = n * n - sum(observed[cls] ** 2 for cls in classes)
    predicted_variance = n * n - sum(predicted[cls] ** 2 for cls in classes)

    denominator = math.sqrt(observed_variance) * math.sqrt(predicted_variance)
    return covariance / denominator if denominator else 0.0


METRIC_NAMES = ("accuracy", "balanced_accuracy", "macro_f1", "mcc")


def aggregate(folds: Sequence[FoldMetrics]) -> dict:
    """Mean and standard error of each metric across folds.

    The mean is unweighted across folds rather than pooled across rows.
    Folds are near-equal in size by construction, and an unweighted mean
    keeps the standard error interpretable as fold-to-fold variability.
    """
    if not folds:
        raise ValueError("cannot aggregate zero folds")
    summary: dict = {"n_folds": len(folds), "n_scored": sum(fold.n for fold in folds)}
    for name in METRIC_NAMES:
        values = [getattr(fold, name) for fold in folds]
        summary[f"{name}_mean"] = _mean(values)
        summary[f"{name}_se"] = standard_error(values)
    return summary


__all__ = [
    "METRIC_NAMES",
    "FoldMetrics",
    "aggregate",
    "score",
    "standard_error",
]
