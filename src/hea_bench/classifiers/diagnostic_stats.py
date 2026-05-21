"""Diagnostic statistics for binary classifiers.

The empirical phase-prediction rules in :mod:`hea_bench.rules` are
*classifiers*, and the right way to characterize a classifier on a
benchmark is by its diagnostic statistics — accuracy, sensitivity,
specificity, Wilson 95% CIs, ROC curve, Youden's J.

This module provides those statistics in dependency-free pure Python.

API surface
-----------
- :func:`wilson_ci` — 95% binomial-proportion confidence interval
- :func:`confusion_matrix` — count (predicted, observed) pairs
- :class:`BinaryStats` — accuracy/sens/spec/Youden's J + confusion + CIs
- :func:`evaluate_binary` — main entry: given prediction/observation
  vectors and a positive-label name, return :class:`BinaryStats`
- :func:`roc_sweep` — for a tunable rule, sweep the threshold and
  return a list of (threshold, sens, spec, J, accuracy) tuples
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field


def wilson_ci(success: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95% CI for a binomial proportion.

    Conservative compared to the naïve normal approximation, well-
    behaved at the boundaries (p = 0 or 1), and correct for small n.
    Robust enough to be the default for HEA-scale (n in the hundreds
    to low thousands) benchmark reports.

    >>> low, high = wilson_ci(80, 100)
    >>> 0.70 < low < 0.72 and 0.86 < high < 0.88
    True
    """
    if total <= 0:
        return (0.0, 0.0)
    p = success / total
    denom = 1.0 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def confusion_matrix(
    predictions: Sequence[str], observations: Sequence[str]
) -> dict[tuple[str, str], int]:
    """Count of (predicted, observed) pairs. Order: rows = predicted,
    cols = observed."""
    if len(predictions) != len(observations):
        raise ValueError(
            f"predictions ({len(predictions)}) and observations "
            f"({len(observations)}) must have the same length"
        )
    counts: dict[tuple[str, str], int] = {}
    for p, o in zip(predictions, observations):
        key = (p, o)
        counts[key] = counts.get(key, 0) + 1
    return counts


@dataclass(frozen=True)
class BinaryStats:
    """Diagnostic statistics for a binary classifier.

    ``positive_label`` is whatever string represents the positive
    class (e.g. ``"single-phase"``). Anything else in the prediction
    or observation streams is treated as negative.
    """

    n: int
    n_positive_observed: int
    n_negative_observed: int
    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int
    accuracy: float
    sensitivity: float    # recall on positive class
    specificity: float    # recall on negative class
    youden_j: float       # sens + spec - 1
    accuracy_ci95: tuple[float, float] = field(default=(0.0, 0.0))
    positive_label: str = ""
    confusion: dict[tuple[str, str], int] = field(default_factory=dict)


def evaluate_binary(
    predictions: Sequence[str],
    observations: Sequence[str],
    positive_label: str,
) -> BinaryStats:
    """Compute :class:`BinaryStats` from prediction and observation streams.

    Both inputs are sequences of string labels (any vocabulary); a
    label counts as positive iff it equals ``positive_label``.
    """
    if len(predictions) != len(observations):
        raise ValueError("predictions and observations must be the same length")

    n = len(predictions)
    tp = fp = tn = fn = 0
    for p, o in zip(predictions, observations):
        pred_pos = (p == positive_label)
        obs_pos = (o == positive_label)
        if pred_pos and obs_pos:
            tp += 1
        elif pred_pos and not obs_pos:
            fp += 1
        elif (not pred_pos) and (not obs_pos):
            tn += 1
        else:
            fn += 1

    n_positive_observed = tp + fn
    n_negative_observed = tn + fp
    correct = tp + tn
    accuracy = correct / n if n else 0.0
    sensitivity = tp / n_positive_observed if n_positive_observed else 0.0
    specificity = tn / n_negative_observed if n_negative_observed else 0.0
    youden = sensitivity + specificity - 1.0
    acc_ci = wilson_ci(correct, n)

    return BinaryStats(
        n=n,
        n_positive_observed=n_positive_observed,
        n_negative_observed=n_negative_observed,
        true_positive=tp,
        false_positive=fp,
        true_negative=tn,
        false_negative=fn,
        accuracy=accuracy,
        sensitivity=sensitivity,
        specificity=specificity,
        youden_j=youden,
        accuracy_ci95=acc_ci,
        positive_label=positive_label,
        confusion=confusion_matrix(predictions, observations),
    )


@dataclass(frozen=True)
class ROCPoint:
    """One point on a ROC sweep — the binary stats at a given threshold."""

    threshold: float
    sensitivity: float
    specificity: float
    youden_j: float
    accuracy: float


def roc_sweep(
    descriptor_values: Sequence[float],
    observations: Sequence[str],
    thresholds: Iterable[float],
    positive_label: str,
    *,
    positive_below_threshold: bool = True,
) -> list[ROCPoint]:
    """For a tunable rule, sweep the threshold and return ROC points.

    Parameters
    ----------
    descriptor_values
        One descriptor value per alloy (e.g. δ for the Zhang rule).
    observations
        Ground-truth labels, same length, same order.
    thresholds
        Threshold candidates to evaluate.
    positive_label
        Which observation label counts as the positive class.
    positive_below_threshold
        ``True`` (default) means "predict positive when descriptor <
        threshold" — the Zhang δ convention. Set ``False`` for rules
        where the positive class is *above* the threshold (e.g. the
        Ω > 1.1 rule).

    Returns
    -------
    list[ROCPoint]
        One point per threshold, in input order.
    """
    if len(descriptor_values) != len(observations):
        raise ValueError("descriptor_values and observations must be the same length")

    out: list[ROCPoint] = []
    obs = list(observations)
    for thr in thresholds:
        if positive_below_threshold:
            preds = ["__pos__" if v < thr else "__neg__" for v in descriptor_values]
        else:
            preds = ["__pos__" if v > thr else "__neg__" for v in descriptor_values]
        translated_obs = ["__pos__" if o == positive_label else "__neg__" for o in obs]
        stats = evaluate_binary(preds, translated_obs, "__pos__")
        out.append(
            ROCPoint(
                threshold=thr,
                sensitivity=stats.sensitivity,
                specificity=stats.specificity,
                youden_j=stats.youden_j,
                accuracy=stats.accuracy,
            )
        )
    return out
