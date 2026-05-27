"""Held-out split primitives and first scoring helpers for the v1.1 evaluation protocol.

This module starts Phase 5 with deterministic split builders over the
consolidated benchmark rows. The full held-out scoring/reporting layer
is a later step; this file provides the reusable fold assignments that
the later evaluation code will consume.
"""

from __future__ import annotations

import csv
import math
import pathlib
import random
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from ..benchmark.taxonomy import binary_observed as _binary_observed
from ..benchmark.taxonomy import phi_observed as _phi_observed
from ..classifiers.diagnostic_stats import BinaryStats, evaluate_binary, wilson_ci
from ..composition import parse_formula
from ..descriptors.data.elemental import covered_elements as _elemental_covered
from ..descriptors.data.pair_enthalpies import covered_elements as _pair_covered
from ..rules import king_phi, yang_omega, ye_phi, zhang_delta

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_DEFAULT_CSV = _REPO_ROOT / "data" / "consolidated" / "v0.1.0" / "consolidated.csv"
_SOURCE_LABEL_COLUMNS = ("borg_label", "pei_label", "peivaste_label")
_ZHANG_THRESHOLD_GRID = tuple(value / 10.0 for value in range(10, 121))
_YANG_THRESHOLD_GRID = tuple(value / 20.0 for value in range(1, 301))
# King Φ grid widened past the paper's textbook 1.0 because the v1.1
# raw-pair-enthalpy approximation of ΔG_max produces Φ values ~n/2
# times larger than King 2016's per-binary intermetallic convention.
_KING_THRESHOLD_GRID = tuple(value / 50.0 for value in range(25, 501))
# Ye φ grid widened past the textbook 20.0 because the held-out sweep
# at the previous (5..50) upper limit was saturating at the boundary.
_YE_THRESHOLD_GRID = tuple(value / 2.0 for value in range(10, 401))


@dataclass(frozen=True)
class FoldSplit:
    """One train/test split over row indices."""

    fold_index: int
    train_indices: tuple[int, ...]
    test_indices: tuple[int, ...]


@dataclass(frozen=True)
class FoldBinaryEvaluation:
    """One held-out fold's binary evaluation output."""

    split: FoldSplit
    stats: BinaryStats


@dataclass(frozen=True)
class BinaryCVSummary:
    """Aggregate summary over a set of held-out binary folds."""

    n_folds: int
    n_rows_total: int
    n_rows_scored: int
    positive_label: str
    accuracy_mean: float
    accuracy_se: float
    sensitivity_mean: float
    sensitivity_se: float
    specificity_mean: float
    specificity_se: float
    youden_j_mean: float
    youden_j_se: float
    folds: tuple[FoldBinaryEvaluation, ...]


@dataclass(frozen=True)
class DoubleScoredBinaryCVSummary:
    """Held-out summary under optimistic and pessimistic conflict scoring."""

    n_folds: int
    n_rows_total: int
    n_rows_scored: int
    positive_label: str
    any_match: BinaryCVSummary
    all_match: BinaryCVSummary


@dataclass(frozen=True)
class TunedFoldBinaryEvaluation:
    """One held-out fold evaluated with a threshold tuned on train only."""

    split: FoldSplit
    tuned_threshold: float
    stats: BinaryStats


@dataclass(frozen=True)
class TunedBinaryCVSummary:
    """Aggregate summary over held-out folds with per-fold tuned thresholds."""

    n_folds: int
    n_rows_total: int
    n_rows_scored: int
    positive_label: str
    default_threshold: float
    tuning_objective: str
    threshold_mean: float
    threshold_se: float
    accuracy_mean: float
    accuracy_se: float
    sensitivity_mean: float
    sensitivity_se: float
    specificity_mean: float
    specificity_se: float
    youden_j_mean: float
    youden_j_se: float
    folds: tuple[TunedFoldBinaryEvaluation, ...]


def binary_summary_to_dict(summary: BinaryCVSummary) -> dict:
    """Serialize a held-out binary summary for JSON-style reporting."""
    return {
        "n_folds": summary.n_folds,
        "n_rows_total": summary.n_rows_total,
        "n_rows_scored": summary.n_rows_scored,
        "positive_label": summary.positive_label,
        "accuracy_mean": summary.accuracy_mean,
        "accuracy_se": summary.accuracy_se,
        "sensitivity_mean": summary.sensitivity_mean,
        "sensitivity_se": summary.sensitivity_se,
        "specificity_mean": summary.specificity_mean,
        "specificity_se": summary.specificity_se,
        "youden_j_mean": summary.youden_j_mean,
        "youden_j_se": summary.youden_j_se,
    }


def double_scored_binary_summary_to_dict(summary: DoubleScoredBinaryCVSummary) -> dict:
    return {
        "n_folds": summary.n_folds,
        "n_rows_total": summary.n_rows_total,
        "n_rows_scored": summary.n_rows_scored,
        "positive_label": summary.positive_label,
        "any_match": binary_summary_to_dict(summary.any_match),
        "all_match": binary_summary_to_dict(summary.all_match),
    }


def tuned_binary_summary_to_dict(summary: TunedBinaryCVSummary) -> dict:
    return {
        "n_folds": summary.n_folds,
        "n_rows_total": summary.n_rows_total,
        "n_rows_scored": summary.n_rows_scored,
        "positive_label": summary.positive_label,
        "default_threshold": summary.default_threshold,
        "tuning_objective": summary.tuning_objective,
        "threshold_mean": summary.threshold_mean,
        "threshold_se": summary.threshold_se,
        "fold_thresholds": [fold.tuned_threshold for fold in summary.folds],
        "accuracy_mean": summary.accuracy_mean,
        "accuracy_se": summary.accuracy_se,
        "sensitivity_mean": summary.sensitivity_mean,
        "sensitivity_se": summary.sensitivity_se,
        "specificity_mean": summary.specificity_mean,
        "specificity_se": summary.specificity_se,
        "youden_j_mean": summary.youden_j_mean,
        "youden_j_se": summary.youden_j_se,
    }


def source_signature(row: Mapping[str, str]) -> str:
    """Stable semicolon-joined source signature for one benchmark row."""
    raw = (row.get("sources") or "").strip()
    if not raw:
        return ""
    return ";".join(sorted(part for part in raw.split(";") if part))


def phase_source_stratum(row: Mapping[str, str]) -> tuple[str, str]:
    """Joint phase × source stratum key.

    Conflict rows have blank ``canonical_phase`` in the consolidated CSV;
    they are routed into an explicit ``conflict`` bucket so the later
    double-scoring logic can keep them visible instead of dropping them.
    """
    phase = (row.get("canonical_phase") or "").strip() or "conflict"
    return (phase, source_signature(row))


def _indices_by_stratum(rows: Sequence[Mapping[str, str]]) -> dict[tuple[str, str], list[int]]:
    grouped: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        grouped[phase_source_stratum(row)].append(index)
    return grouped


def stratified_kfold_splits(
    rows: Sequence[Mapping[str, str]],
    *,
    k: int = 5,
    seed: int = 0,
) -> list[FoldSplit]:
    """Deterministic phase × source stratified k-fold splits.

    Rows are shuffled only within their stratum, then assigned to folds
    in round-robin order. That guarantees each row appears in exactly one
    test fold and that each stratum's per-fold counts differ by at most 1.
    """
    if k < 2:
        raise ValueError("k must be at least 2")

    rng = random.Random(seed)
    grouped = _indices_by_stratum(rows)
    test_buckets: list[list[int]] = [[] for _ in range(k)]
    next_fold = 0

    for stratum in sorted(grouped):
        indices = list(grouped[stratum])
        rng.shuffle(indices)
        start_fold = next_fold % k
        for offset, index in enumerate(indices):
            test_buckets[(start_fold + offset) % k].append(index)
        next_fold += len(indices)

    universe = set(range(len(rows)))
    splits: list[FoldSplit] = []
    for fold_index, bucket in enumerate(test_buckets):
        test = tuple(sorted(bucket))
        train = tuple(sorted(universe.difference(bucket)))
        splits.append(FoldSplit(fold_index=fold_index, train_indices=train, test_indices=test))
    return splits


def stratified_single_split(
    rows: Sequence[Mapping[str, str]],
    *,
    test_fraction: float = 0.3,
    seed: int = 0,
) -> FoldSplit:
    """Deterministic stratified single train/test split.

    For strata of size 2 or more, the split keeps at least one row in
    train and one in test. Singleton strata stay in train.
    """
    if not 0.0 < test_fraction < 1.0:
        raise ValueError("test_fraction must be between 0 and 1")

    rng = random.Random(seed)
    grouped = _indices_by_stratum(rows)
    test_indices: list[int] = []

    for stratum in sorted(grouped):
        indices = list(grouped[stratum])
        rng.shuffle(indices)

        if len(indices) == 1:
            n_test = 0
        else:
            n_test = int(round(len(indices) * test_fraction))
            n_test = min(max(n_test, 1), len(indices) - 1)

        test_indices.extend(indices[:n_test])

    test = tuple(sorted(test_indices))
    train = tuple(sorted(set(range(len(rows))).difference(test_indices)))
    return FoldSplit(fold_index=0, train_indices=train, test_indices=test)


def strict_consensus_rows(rows: Sequence[Mapping[str, str]]) -> list[Mapping[str, str]]:
    """Return only rows with a non-blank canonical phase label."""
    return [row for row in rows if (row.get("canonical_phase") or "").strip()]


def load_holdout_rows(csv_path: pathlib.Path = _DEFAULT_CSV) -> list[dict]:
    """Load the consolidated benchmark for held-out evaluation.

    Unlike the in-sample evaluator, this loader keeps conflict rows so the
    later double-scoring layer can operate on them. Rows whose composition
    cannot be parsed are skipped.
    """
    out: list[dict] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                comp = parse_formula(row["composition_key"])
            except (KeyError, ValueError):
                continue
            item = dict(row)
            item["_composition"] = comp
            out.append(item)
    return out


def _source_observed_label_set(
    row: Mapping[str, object],
    mapper: Callable[[str], str | None],
) -> frozenset[str]:
    labels: set[str] = set()
    for column in _SOURCE_LABEL_COLUMNS:
        canonical = str(row.get(column) or "").strip()
        if not canonical:
            continue
        mapped = mapper(canonical)
        if mapped is not None:
            labels.add(mapped)
    return frozenset(labels)


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _sample_standard_error(values: Sequence[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mean = _mean(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance / len(values))


def _build_binary_stats(
    tp: int,
    fp: int,
    tn: int,
    fn: int,
    positive_label: str,
) -> BinaryStats:
    n = tp + fp + tn + fn
    n_positive_observed = tp + fn
    n_negative_observed = tn + fp
    correct = tp + tn
    accuracy = correct / n if n else 0.0
    sensitivity = tp / n_positive_observed if n_positive_observed else 0.0
    specificity = tn / n_negative_observed if n_negative_observed else 0.0
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
        youden_j=sensitivity + specificity - 1.0,
        accuracy_ci95=wilson_ci(correct, n),
        positive_label=positive_label,
        confusion={},
    )


def _summarize_fold_results(
    rows_total: int,
    positive_label: str,
    fold_results: Sequence[FoldBinaryEvaluation],
) -> BinaryCVSummary:
    accuracies = [fold.stats.accuracy for fold in fold_results]
    sensitivities = [fold.stats.sensitivity for fold in fold_results]
    specificities = [fold.stats.specificity for fold in fold_results]
    youden_js = [fold.stats.youden_j for fold in fold_results]

    return BinaryCVSummary(
        n_folds=len(fold_results),
        n_rows_total=rows_total,
        n_rows_scored=sum(fold.stats.n for fold in fold_results),
        positive_label=positive_label,
        accuracy_mean=_mean(accuracies),
        accuracy_se=_sample_standard_error(accuracies),
        sensitivity_mean=_mean(sensitivities),
        sensitivity_se=_sample_standard_error(sensitivities),
        specificity_mean=_mean(specificities),
        specificity_se=_sample_standard_error(specificities),
        youden_j_mean=_mean(youden_js),
        youden_j_se=_sample_standard_error(youden_js),
        folds=tuple(fold_results),
    )


def _summarize_tuned_fold_results(
    rows_total: int,
    positive_label: str,
    default_threshold: float,
    fold_results: Sequence[TunedFoldBinaryEvaluation],
) -> TunedBinaryCVSummary:
    thresholds = [fold.tuned_threshold for fold in fold_results]
    accuracies = [fold.stats.accuracy for fold in fold_results]
    sensitivities = [fold.stats.sensitivity for fold in fold_results]
    specificities = [fold.stats.specificity for fold in fold_results]
    youden_js = [fold.stats.youden_j for fold in fold_results]

    return TunedBinaryCVSummary(
        n_folds=len(fold_results),
        n_rows_total=rows_total,
        n_rows_scored=sum(fold.stats.n for fold in fold_results),
        positive_label=positive_label,
        default_threshold=default_threshold,
        tuning_objective="train_fold_youden_j",
        threshold_mean=_mean(thresholds),
        threshold_se=_sample_standard_error(thresholds),
        accuracy_mean=_mean(accuracies),
        accuracy_se=_sample_standard_error(accuracies),
        sensitivity_mean=_mean(sensitivities),
        sensitivity_se=_sample_standard_error(sensitivities),
        specificity_mean=_mean(specificities),
        specificity_se=_sample_standard_error(specificities),
        youden_j_mean=_mean(youden_js),
        youden_j_se=_sample_standard_error(youden_js),
        folds=tuple(fold_results),
    )


def _select_tuned_threshold(
    descriptor_values: Sequence[float],
    observations: Sequence[str],
    *,
    positive_label: str,
    thresholds: Sequence[float],
    default_threshold: float,
    predictor: Callable[[float, float], str],
) -> float:
    """Choose the train-fold threshold that maximizes Youden's J.

    Ties are broken by proximity to the rule's default threshold, then by
    the smaller threshold value for determinism.
    """
    if not descriptor_values:
        raise ValueError("descriptor_values must be non-empty")
    if len(descriptor_values) != len(observations):
        raise ValueError("descriptor_values and observations must have the same length")
    if not thresholds:
        raise ValueError("thresholds must be non-empty")

    best_threshold = None
    best_key = None
    for threshold in thresholds:
        predictions = [predictor(value, threshold) for value in descriptor_values]
        stats = evaluate_binary(predictions, observations, positive_label=positive_label)
        key = (stats.youden_j, -abs(threshold - default_threshold), -threshold)
        if best_key is None or key > best_key:
            best_key = key
            best_threshold = threshold

    return float(best_threshold)


def evaluate_binary_kfold(
    rows: Sequence[Mapping[str, object]],
    *,
    predict_row: Callable[[Mapping[str, object]], str],
    observed_label: Callable[[Mapping[str, object]], str | None],
    row_is_scorable: Callable[[Mapping[str, object]], bool] | None = None,
    positive_label: str,
    k: int = 5,
    seed: int = 0,
    include_conflicts: bool = False,
) -> BinaryCVSummary:
    """Evaluate a binary rule over deterministic held-out folds.

    In the current Phase 5 slice, ``include_conflicts`` defaults to
    ``False`` so the scorer operates on strict-consensus rows only.
    The later conflict-row double-scoring layer will build on the same
    split primitive with ``include_conflicts=True``.
    """
    if include_conflicts:
        working_rows = list(rows)
    else:
        working_rows = strict_consensus_rows(rows)

    if row_is_scorable is not None:
        working_rows = [row for row in working_rows if row_is_scorable(row)]

    splits = stratified_kfold_splits(working_rows, k=k, seed=seed)
    fold_results: list[FoldBinaryEvaluation] = []

    for split in splits:
        predictions: list[str] = []
        observations: list[str] = []
        for index in split.test_indices:
            row = working_rows[index]
            observed = observed_label(row)
            if observed is None:
                continue
            predictions.append(predict_row(row))
            observations.append(observed)
        stats = evaluate_binary(predictions, observations, positive_label=positive_label)
        fold_results.append(FoldBinaryEvaluation(split=split, stats=stats))

    return _summarize_fold_results(len(rows), positive_label, fold_results)


def evaluate_binary_single_split(
    rows: Sequence[Mapping[str, object]],
    *,
    predict_row: Callable[[Mapping[str, object]], str],
    observed_label: Callable[[Mapping[str, object]], str | None],
    row_is_scorable: Callable[[Mapping[str, object]], bool] | None = None,
    positive_label: str,
    test_fraction: float = 0.3,
    seed: int = 0,
    include_conflicts: bool = False,
) -> BinaryCVSummary:
    """Evaluate a binary rule on one deterministic stratified split."""
    if include_conflicts:
        working_rows = list(rows)
    else:
        working_rows = strict_consensus_rows(rows)

    if row_is_scorable is not None:
        working_rows = [row for row in working_rows if row_is_scorable(row)]

    split = stratified_single_split(working_rows, test_fraction=test_fraction, seed=seed)
    predictions: list[str] = []
    observations: list[str] = []
    for index in split.test_indices:
        row = working_rows[index]
        observed = observed_label(row)
        if observed is None:
            continue
        predictions.append(predict_row(row))
        observations.append(observed)

    fold_result = FoldBinaryEvaluation(
        split=split,
        stats=evaluate_binary(predictions, observations, positive_label=positive_label),
    )
    return _summarize_fold_results(len(rows), positive_label, [fold_result])


def evaluate_binary_kfold_double_scored(
    rows: Sequence[Mapping[str, object]],
    *,
    predict_row: Callable[[Mapping[str, object]], str],
    observed_label_set: Callable[[Mapping[str, object]], frozenset[str]],
    row_is_scorable: Callable[[Mapping[str, object]], bool] | None = None,
    positive_label: str,
    k: int = 5,
    seed: int = 0,
) -> DoubleScoredBinaryCVSummary:
    """Evaluate a binary rule with conflict rows scored two ways.

    ``any_match`` counts a conflict row as correct when the prediction
    matches at least one source label. ``all_match`` counts it as correct
    only when the prediction matches every source label.
    """
    working_rows = list(rows)
    if row_is_scorable is not None:
        working_rows = [row for row in working_rows if row_is_scorable(row)]

    splits = stratified_kfold_splits(working_rows, k=k, seed=seed)
    any_results: list[FoldBinaryEvaluation] = []
    all_results: list[FoldBinaryEvaluation] = []

    for split in splits:
        any_tp = any_fp = any_tn = any_fn = 0
        all_tp = all_fp = all_tn = all_fn = 0

        for index in split.test_indices:
            row = working_rows[index]
            allowed = observed_label_set(row)
            if not allowed:
                continue
            prediction = predict_row(row)
            pred_positive = prediction == positive_label

            if pred_positive:
                if positive_label in allowed:
                    any_tp += 1
                else:
                    any_fp += 1

                if allowed == frozenset({positive_label}):
                    all_tp += 1
                else:
                    all_fp += 1
            else:
                if prediction in allowed:
                    any_tn += 1
                else:
                    any_fn += 1

                if positive_label not in allowed and prediction in allowed:
                    all_tn += 1
                else:
                    all_fn += 1

        any_results.append(
            FoldBinaryEvaluation(
                split=split,
                stats=_build_binary_stats(any_tp, any_fp, any_tn, any_fn, positive_label),
            )
        )
        all_results.append(
            FoldBinaryEvaluation(
                split=split,
                stats=_build_binary_stats(all_tp, all_fp, all_tn, all_fn, positive_label),
            )
        )

    any_summary = _summarize_fold_results(len(rows), positive_label, any_results)
    all_summary = _summarize_fold_results(len(rows), positive_label, all_results)
    return DoubleScoredBinaryCVSummary(
        n_folds=len(any_results),
        n_rows_total=len(rows),
        n_rows_scored=any_summary.n_rows_scored,
        positive_label=positive_label,
        any_match=any_summary,
        all_match=all_summary,
    )


def evaluate_binary_single_split_double_scored(
    rows: Sequence[Mapping[str, object]],
    *,
    predict_row: Callable[[Mapping[str, object]], str],
    observed_label_set: Callable[[Mapping[str, object]], frozenset[str]],
    row_is_scorable: Callable[[Mapping[str, object]], bool] | None = None,
    positive_label: str,
    test_fraction: float = 0.3,
    seed: int = 0,
) -> DoubleScoredBinaryCVSummary:
    """Evaluate a binary rule on one stratified split with conflict double scoring."""
    working_rows = list(rows)
    if row_is_scorable is not None:
        working_rows = [row for row in working_rows if row_is_scorable(row)]

    split = stratified_single_split(working_rows, test_fraction=test_fraction, seed=seed)
    any_tp = any_fp = any_tn = any_fn = 0
    all_tp = all_fp = all_tn = all_fn = 0

    for index in split.test_indices:
        row = working_rows[index]
        allowed = observed_label_set(row)
        if not allowed:
            continue
        prediction = predict_row(row)
        pred_positive = prediction == positive_label

        if pred_positive:
            if positive_label in allowed:
                any_tp += 1
            else:
                any_fp += 1

            if allowed == frozenset({positive_label}):
                all_tp += 1
            else:
                all_fp += 1
        else:
            if prediction in allowed:
                any_tn += 1
            else:
                any_fn += 1

            if positive_label not in allowed and prediction in allowed:
                all_tn += 1
            else:
                all_fn += 1

    any_result = FoldBinaryEvaluation(
        split=split,
        stats=_build_binary_stats(any_tp, any_fp, any_tn, any_fn, positive_label),
    )
    all_result = FoldBinaryEvaluation(
        split=split,
        stats=_build_binary_stats(all_tp, all_fp, all_tn, all_fn, positive_label),
    )
    any_summary = _summarize_fold_results(len(rows), positive_label, [any_result])
    all_summary = _summarize_fold_results(len(rows), positive_label, [all_result])
    return DoubleScoredBinaryCVSummary(
        n_folds=1,
        n_rows_total=len(rows),
        n_rows_scored=any_summary.n_rows_scored,
        positive_label=positive_label,
        any_match=any_summary,
        all_match=all_summary,
    )


def evaluate_binary_kfold_tuned(
    rows: Sequence[Mapping[str, object]],
    *,
    descriptor_row: Callable[[Mapping[str, object]], float],
    predict_from_value: Callable[[float, float], str],
    observed_label: Callable[[Mapping[str, object]], str | None],
    row_is_scorable: Callable[[Mapping[str, object]], bool] | None = None,
    positive_label: str,
    thresholds: Sequence[float],
    default_threshold: float,
    k: int = 5,
    seed: int = 0,
    include_conflicts: bool = False,
) -> TunedBinaryCVSummary:
    """Evaluate a binary rule with threshold tuning on the training folds only."""
    if include_conflicts:
        working_rows = list(rows)
    else:
        working_rows = strict_consensus_rows(rows)

    if row_is_scorable is not None:
        working_rows = [row for row in working_rows if row_is_scorable(row)]

    splits = stratified_kfold_splits(working_rows, k=k, seed=seed)
    fold_results: list[TunedFoldBinaryEvaluation] = []

    for split in splits:
        train_values: list[float] = []
        train_obs: list[str] = []
        for index in split.train_indices:
            row = working_rows[index]
            observed = observed_label(row)
            if observed is None:
                continue
            train_values.append(descriptor_row(row))
            train_obs.append(observed)

        tuned_threshold = _select_tuned_threshold(
            train_values,
            train_obs,
            positive_label=positive_label,
            thresholds=thresholds,
            default_threshold=default_threshold,
            predictor=predict_from_value,
        )

        test_predictions: list[str] = []
        test_observations: list[str] = []
        for index in split.test_indices:
            row = working_rows[index]
            observed = observed_label(row)
            if observed is None:
                continue
            test_predictions.append(predict_from_value(descriptor_row(row), tuned_threshold))
            test_observations.append(observed)

        fold_results.append(
            TunedFoldBinaryEvaluation(
                split=split,
                tuned_threshold=tuned_threshold,
                stats=evaluate_binary(test_predictions, test_observations, positive_label=positive_label),
            )
        )

    return _summarize_tuned_fold_results(len(rows), positive_label, default_threshold, fold_results)


def evaluate_binary_single_split_tuned(
    rows: Sequence[Mapping[str, object]],
    *,
    descriptor_row: Callable[[Mapping[str, object]], float],
    predict_from_value: Callable[[float, float], str],
    observed_label: Callable[[Mapping[str, object]], str | None],
    row_is_scorable: Callable[[Mapping[str, object]], bool] | None = None,
    positive_label: str,
    thresholds: Sequence[float],
    default_threshold: float,
    test_fraction: float = 0.3,
    seed: int = 0,
    include_conflicts: bool = False,
) -> TunedBinaryCVSummary:
    """Evaluate a binary rule on one split with threshold tuning on train only."""
    if include_conflicts:
        working_rows = list(rows)
    else:
        working_rows = strict_consensus_rows(rows)

    if row_is_scorable is not None:
        working_rows = [row for row in working_rows if row_is_scorable(row)]

    split = stratified_single_split(working_rows, test_fraction=test_fraction, seed=seed)
    train_values: list[float] = []
    train_obs: list[str] = []
    for index in split.train_indices:
        row = working_rows[index]
        observed = observed_label(row)
        if observed is None:
            continue
        train_values.append(descriptor_row(row))
        train_obs.append(observed)

    tuned_threshold = _select_tuned_threshold(
        train_values,
        train_obs,
        positive_label=positive_label,
        thresholds=thresholds,
        default_threshold=default_threshold,
        predictor=predict_from_value,
    )

    test_predictions: list[str] = []
    test_observations: list[str] = []
    for index in split.test_indices:
        row = working_rows[index]
        observed = observed_label(row)
        if observed is None:
            continue
        test_predictions.append(predict_from_value(descriptor_row(row), tuned_threshold))
        test_observations.append(observed)

    fold_result = TunedFoldBinaryEvaluation(
        split=split,
        tuned_threshold=tuned_threshold,
        stats=evaluate_binary(test_predictions, test_observations, positive_label=positive_label),
    )
    return _summarize_tuned_fold_results(len(rows), positive_label, default_threshold, [fold_result])


def evaluate_zhang_delta_holdout(
    rows: Sequence[Mapping[str, object]],
    *,
    threshold: float = zhang_delta.DEFAULT_THRESHOLD,
    k: int = 5,
    seed: int = 0,
) -> BinaryCVSummary:
    elemental = _elemental_covered()
    return evaluate_binary_kfold(
        rows,
        predict_row=lambda row: zhang_delta.predict(row["_composition"], threshold=threshold),
        observed_label=lambda row: _binary_observed(str(row["canonical_phase"])),
        row_is_scorable=lambda row: set(row["_composition"]).issubset(elemental),
        positive_label="single-phase",
        k=k,
        seed=seed,
    )


def evaluate_yang_omega_holdout(
    rows: Sequence[Mapping[str, object]],
    *,
    threshold: float = yang_omega.DEFAULT_THRESHOLD,
    k: int = 5,
    seed: int = 0,
) -> BinaryCVSummary:
    needed = _elemental_covered() & _pair_covered()
    return evaluate_binary_kfold(
        rows,
        predict_row=lambda row: yang_omega.predict(row["_composition"], threshold=threshold),
        observed_label=lambda row: _binary_observed(str(row["canonical_phase"])),
        row_is_scorable=lambda row: set(row["_composition"]).issubset(needed),
        positive_label="single-phase",
        k=k,
        seed=seed,
    )


def evaluate_king_phi_holdout(
    rows: Sequence[Mapping[str, object]],
    *,
    threshold: float = king_phi.DEFAULT_THRESHOLD,
    temperature_policy: float | None = None,
    k: int = 5,
    seed: int = 0,
) -> BinaryCVSummary:
    needed = _elemental_covered() & _pair_covered()
    return evaluate_binary_kfold(
        rows,
        predict_row=lambda row: king_phi.predict(
            row["_composition"],
            threshold=threshold,
            temperature_policy=temperature_policy,
        ),
        observed_label=lambda row: _phi_observed(str(row["canonical_phase"])),
        row_is_scorable=lambda row: set(row["_composition"]).issubset(needed),
        positive_label="solid_solution",
        k=k,
        seed=seed,
    )


def evaluate_ye_phi_holdout(
    rows: Sequence[Mapping[str, object]],
    *,
    threshold: float = ye_phi.DEFAULT_THRESHOLD,
    k: int = 5,
    seed: int = 0,
) -> BinaryCVSummary:
    needed = _elemental_covered() & _pair_covered()
    return evaluate_binary_kfold(
        rows,
        predict_row=lambda row: ye_phi.predict(row["_composition"], threshold=threshold),
        observed_label=lambda row: _phi_observed(str(row["canonical_phase"])),
        row_is_scorable=lambda row: set(row["_composition"]).issubset(needed),
        positive_label="solid_solution",
        k=k,
        seed=seed,
    )


def evaluate_zhang_delta_holdout_tuned(
    rows: Sequence[Mapping[str, object]],
    *,
    thresholds: Sequence[float] = _ZHANG_THRESHOLD_GRID,
    default_threshold: float = zhang_delta.DEFAULT_THRESHOLD,
    k: int = 5,
    seed: int = 0,
) -> TunedBinaryCVSummary:
    from ..descriptors.size import delta

    elemental = _elemental_covered()
    return evaluate_binary_kfold_tuned(
        rows,
        descriptor_row=lambda row: delta(row["_composition"]),
        predict_from_value=lambda value, threshold: "single-phase" if value < threshold else "multi-phase",
        observed_label=lambda row: _binary_observed(str(row["canonical_phase"])),
        row_is_scorable=lambda row: set(row["_composition"]).issubset(elemental),
        positive_label="single-phase",
        thresholds=thresholds,
        default_threshold=default_threshold,
        k=k,
        seed=seed,
    )


def evaluate_yang_omega_holdout_tuned(
    rows: Sequence[Mapping[str, object]],
    *,
    thresholds: Sequence[float] = _YANG_THRESHOLD_GRID,
    default_threshold: float = yang_omega.DEFAULT_THRESHOLD,
    k: int = 5,
    seed: int = 0,
) -> TunedBinaryCVSummary:
    from ..descriptors.omega import omega

    needed = _elemental_covered() & _pair_covered()
    return evaluate_binary_kfold_tuned(
        rows,
        descriptor_row=lambda row: omega(row["_composition"]),
        predict_from_value=lambda value, threshold: "single-phase" if value > threshold else "multi-phase",
        observed_label=lambda row: _binary_observed(str(row["canonical_phase"])),
        row_is_scorable=lambda row: set(row["_composition"]).issubset(needed),
        positive_label="single-phase",
        thresholds=thresholds,
        default_threshold=default_threshold,
        k=k,
        seed=seed,
    )


def evaluate_king_phi_holdout_tuned(
    rows: Sequence[Mapping[str, object]],
    *,
    thresholds: Sequence[float] = _KING_THRESHOLD_GRID,
    default_threshold: float = king_phi.DEFAULT_THRESHOLD,
    temperature_policy: float | None = None,
    k: int = 5,
    seed: int = 0,
) -> TunedBinaryCVSummary:
    from ..descriptors.phi import phi_king

    needed = _elemental_covered() & _pair_covered()
    return evaluate_binary_kfold_tuned(
        rows,
        descriptor_row=lambda row: phi_king(row["_composition"], temperature=temperature_policy),
        predict_from_value=lambda value, threshold: "solid_solution" if value > threshold else "intermetallic",
        observed_label=lambda row: _phi_observed(str(row["canonical_phase"])),
        row_is_scorable=lambda row: set(row["_composition"]).issubset(needed),
        positive_label="solid_solution",
        thresholds=thresholds,
        default_threshold=default_threshold,
        k=k,
        seed=seed,
    )


def evaluate_ye_phi_holdout_tuned(
    rows: Sequence[Mapping[str, object]],
    *,
    thresholds: Sequence[float] = _YE_THRESHOLD_GRID,
    default_threshold: float = ye_phi.DEFAULT_THRESHOLD,
    k: int = 5,
    seed: int = 0,
) -> TunedBinaryCVSummary:
    from ..descriptors.phi import phi_ye

    needed = _elemental_covered() & _pair_covered()
    return evaluate_binary_kfold_tuned(
        rows,
        descriptor_row=lambda row: phi_ye(row["_composition"]),
        predict_from_value=lambda value, threshold: "solid_solution" if value > threshold else "intermetallic",
        observed_label=lambda row: _phi_observed(str(row["canonical_phase"])),
        row_is_scorable=lambda row: set(row["_composition"]).issubset(needed),
        positive_label="solid_solution",
        thresholds=thresholds,
        default_threshold=default_threshold,
        k=k,
        seed=seed,
    )


def evaluate_zhang_delta_holdout_double_scored(
    rows: Sequence[Mapping[str, object]],
    *,
    threshold: float = zhang_delta.DEFAULT_THRESHOLD,
    k: int = 5,
    seed: int = 0,
) -> DoubleScoredBinaryCVSummary:
    elemental = _elemental_covered()
    return evaluate_binary_kfold_double_scored(
        rows,
        predict_row=lambda row: zhang_delta.predict(row["_composition"], threshold=threshold),
        observed_label_set=lambda row: _source_observed_label_set(row, _binary_observed),
        row_is_scorable=lambda row: set(row["_composition"]).issubset(elemental),
        positive_label="single-phase",
        k=k,
        seed=seed,
    )


def evaluate_yang_omega_holdout_double_scored(
    rows: Sequence[Mapping[str, object]],
    *,
    threshold: float = yang_omega.DEFAULT_THRESHOLD,
    k: int = 5,
    seed: int = 0,
) -> DoubleScoredBinaryCVSummary:
    needed = _elemental_covered() & _pair_covered()
    return evaluate_binary_kfold_double_scored(
        rows,
        predict_row=lambda row: yang_omega.predict(row["_composition"], threshold=threshold),
        observed_label_set=lambda row: _source_observed_label_set(row, _binary_observed),
        row_is_scorable=lambda row: set(row["_composition"]).issubset(needed),
        positive_label="single-phase",
        k=k,
        seed=seed,
    )


def evaluate_king_phi_holdout_double_scored(
    rows: Sequence[Mapping[str, object]],
    *,
    threshold: float = king_phi.DEFAULT_THRESHOLD,
    temperature_policy: float | None = None,
    k: int = 5,
    seed: int = 0,
) -> DoubleScoredBinaryCVSummary:
    needed = _elemental_covered() & _pair_covered()
    return evaluate_binary_kfold_double_scored(
        rows,
        predict_row=lambda row: king_phi.predict(
            row["_composition"],
            threshold=threshold,
            temperature_policy=temperature_policy,
        ),
        observed_label_set=lambda row: _source_observed_label_set(row, _phi_observed),
        row_is_scorable=lambda row: set(row["_composition"]).issubset(needed),
        positive_label="solid_solution",
        k=k,
        seed=seed,
    )


def evaluate_ye_phi_holdout_double_scored(
    rows: Sequence[Mapping[str, object]],
    *,
    threshold: float = ye_phi.DEFAULT_THRESHOLD,
    k: int = 5,
    seed: int = 0,
) -> DoubleScoredBinaryCVSummary:
    needed = _elemental_covered() & _pair_covered()
    return evaluate_binary_kfold_double_scored(
        rows,
        predict_row=lambda row: ye_phi.predict(row["_composition"], threshold=threshold),
        observed_label_set=lambda row: _source_observed_label_set(row, _phi_observed),
        row_is_scorable=lambda row: set(row["_composition"]).issubset(needed),
        positive_label="solid_solution",
        k=k,
        seed=seed,
    )


def build_binary_holdout_report(
    csv_path: pathlib.Path = _DEFAULT_CSV,
    *,
    include_phi: bool = False,
    k: int = 5,
    seed: int = 0,
) -> dict:
    """Build the first strict-consensus held-out report for binary rules."""
    rows = load_holdout_rows(csv_path)
    rules = {
        "zhang_delta_6_5": binary_summary_to_dict(evaluate_zhang_delta_holdout(rows, k=k, seed=seed)),
        "yang_omega_1_1": binary_summary_to_dict(evaluate_yang_omega_holdout(rows, k=k, seed=seed)),
    }
    if include_phi:
        rules["king_phi_1_0"] = binary_summary_to_dict(evaluate_king_phi_holdout(rows, k=k, seed=seed))
        rules["ye_phi_20_0"] = binary_summary_to_dict(evaluate_ye_phi_holdout(rows, k=k, seed=seed))
    return {
        "csv_path": str(csv_path),
        "protocol": "strict_consensus_kfold",
        "k": k,
        "seed": seed,
        "rules": rules,
    }


def build_binary_single_split_report(
    csv_path: pathlib.Path = _DEFAULT_CSV,
    *,
    include_phi: bool = False,
    test_fraction: float = 0.3,
    seed: int = 0,
) -> dict:
    """Build the strict-consensus single-split report for binary rules."""
    rows = load_holdout_rows(csv_path)
    elemental = _elemental_covered()
    needed = elemental & _pair_covered()
    rules = {
        "zhang_delta_6_5": binary_summary_to_dict(
            evaluate_binary_single_split(
                rows,
                predict_row=lambda row: zhang_delta.predict(row["_composition"], threshold=zhang_delta.DEFAULT_THRESHOLD),
                observed_label=lambda row: _binary_observed(str(row["canonical_phase"])),
                row_is_scorable=lambda row: set(row["_composition"]).issubset(elemental),
                positive_label="single-phase",
                test_fraction=test_fraction,
                seed=seed,
            )
        ),
        "yang_omega_1_1": binary_summary_to_dict(
            evaluate_binary_single_split(
                rows,
                predict_row=lambda row: yang_omega.predict(row["_composition"], threshold=yang_omega.DEFAULT_THRESHOLD),
                observed_label=lambda row: _binary_observed(str(row["canonical_phase"])),
                row_is_scorable=lambda row: set(row["_composition"]).issubset(needed),
                positive_label="single-phase",
                test_fraction=test_fraction,
                seed=seed,
            )
        ),
    }
    if include_phi:
        rules["king_phi_1_0"] = binary_summary_to_dict(
            evaluate_binary_single_split(
                rows,
                predict_row=lambda row: king_phi.predict(row["_composition"], threshold=king_phi.DEFAULT_THRESHOLD),
                observed_label=lambda row: _phi_observed(str(row["canonical_phase"])),
                row_is_scorable=lambda row: set(row["_composition"]).issubset(needed),
                positive_label="solid_solution",
                test_fraction=test_fraction,
                seed=seed,
            )
        )
        rules["ye_phi_20_0"] = binary_summary_to_dict(
            evaluate_binary_single_split(
                rows,
                predict_row=lambda row: ye_phi.predict(row["_composition"], threshold=ye_phi.DEFAULT_THRESHOLD),
                observed_label=lambda row: _phi_observed(str(row["canonical_phase"])),
                row_is_scorable=lambda row: set(row["_composition"]).issubset(needed),
                positive_label="solid_solution",
                test_fraction=test_fraction,
                seed=seed,
            )
        )
    return {
        "csv_path": str(csv_path),
        "protocol": "strict_consensus_single_split",
        "test_fraction": test_fraction,
        "seed": seed,
        "rules": rules,
    }


def build_double_scored_binary_holdout_report(
    csv_path: pathlib.Path = _DEFAULT_CSV,
    *,
    include_phi: bool = False,
    k: int = 5,
    seed: int = 0,
) -> dict:
    """Build the conflict-aware held-out report with any/all scoring."""
    rows = load_holdout_rows(csv_path)
    rules = {
        "zhang_delta_6_5": double_scored_binary_summary_to_dict(
            evaluate_zhang_delta_holdout_double_scored(rows, k=k, seed=seed)
        ),
        "yang_omega_1_1": double_scored_binary_summary_to_dict(
            evaluate_yang_omega_holdout_double_scored(rows, k=k, seed=seed)
        ),
    }
    if include_phi:
        rules["king_phi_1_0"] = double_scored_binary_summary_to_dict(
            evaluate_king_phi_holdout_double_scored(rows, k=k, seed=seed)
        )
        rules["ye_phi_20_0"] = double_scored_binary_summary_to_dict(
            evaluate_ye_phi_holdout_double_scored(rows, k=k, seed=seed)
        )
    return {
        "csv_path": str(csv_path),
        "protocol": "double_scored_kfold",
        "k": k,
        "seed": seed,
        "rules": rules,
    }


def build_double_scored_binary_single_split_report(
    csv_path: pathlib.Path = _DEFAULT_CSV,
    *,
    include_phi: bool = False,
    test_fraction: float = 0.3,
    seed: int = 0,
) -> dict:
    """Build the conflict-aware single-split report with any/all scoring."""
    rows = load_holdout_rows(csv_path)
    elemental = _elemental_covered()
    needed = elemental & _pair_covered()
    rules = {
        "zhang_delta_6_5": double_scored_binary_summary_to_dict(
            evaluate_binary_single_split_double_scored(
                rows,
                predict_row=lambda row: zhang_delta.predict(row["_composition"], threshold=zhang_delta.DEFAULT_THRESHOLD),
                observed_label_set=lambda row: _source_observed_label_set(row, _binary_observed),
                row_is_scorable=lambda row: set(row["_composition"]).issubset(elemental),
                positive_label="single-phase",
                test_fraction=test_fraction,
                seed=seed,
            )
        ),
        "yang_omega_1_1": double_scored_binary_summary_to_dict(
            evaluate_binary_single_split_double_scored(
                rows,
                predict_row=lambda row: yang_omega.predict(row["_composition"], threshold=yang_omega.DEFAULT_THRESHOLD),
                observed_label_set=lambda row: _source_observed_label_set(row, _binary_observed),
                row_is_scorable=lambda row: set(row["_composition"]).issubset(needed),
                positive_label="single-phase",
                test_fraction=test_fraction,
                seed=seed,
            )
        ),
    }
    if include_phi:
        rules["king_phi_1_0"] = double_scored_binary_summary_to_dict(
            evaluate_binary_single_split_double_scored(
                rows,
                predict_row=lambda row: king_phi.predict(row["_composition"], threshold=king_phi.DEFAULT_THRESHOLD),
                observed_label_set=lambda row: _source_observed_label_set(row, _phi_observed),
                row_is_scorable=lambda row: set(row["_composition"]).issubset(needed),
                positive_label="solid_solution",
                test_fraction=test_fraction,
                seed=seed,
            )
        )
        rules["ye_phi_20_0"] = double_scored_binary_summary_to_dict(
            evaluate_binary_single_split_double_scored(
                rows,
                predict_row=lambda row: ye_phi.predict(row["_composition"], threshold=ye_phi.DEFAULT_THRESHOLD),
                observed_label_set=lambda row: _source_observed_label_set(row, _phi_observed),
                row_is_scorable=lambda row: set(row["_composition"]).issubset(needed),
                positive_label="solid_solution",
                test_fraction=test_fraction,
                seed=seed,
            )
        )
    return {
        "csv_path": str(csv_path),
        "protocol": "double_scored_single_split",
        "test_fraction": test_fraction,
        "seed": seed,
        "rules": rules,
    }


def build_tuned_binary_holdout_report(
    csv_path: pathlib.Path = _DEFAULT_CSV,
    *,
    include_phi: bool = False,
    k: int = 5,
    seed: int = 0,
) -> dict:
    """Build the strict-consensus held-out report with train-fold tuned thresholds.

    This report deliberately coexists with the fixed-threshold held-out
    report rather than replacing it, so the optimism gap from tuning can
    be reported explicitly.
    """
    rows = load_holdout_rows(csv_path)
    rules = {
        "zhang_delta_tuned": tuned_binary_summary_to_dict(evaluate_zhang_delta_holdout_tuned(rows, k=k, seed=seed)),
        "yang_omega_tuned": tuned_binary_summary_to_dict(evaluate_yang_omega_holdout_tuned(rows, k=k, seed=seed)),
    }
    if include_phi:
        rules["king_phi_tuned"] = tuned_binary_summary_to_dict(evaluate_king_phi_holdout_tuned(rows, k=k, seed=seed))
        rules["ye_phi_tuned"] = tuned_binary_summary_to_dict(evaluate_ye_phi_holdout_tuned(rows, k=k, seed=seed))
    return {
        "csv_path": str(csv_path),
        "protocol": "strict_consensus_kfold_tuned",
        "k": k,
        "seed": seed,
        "rules": rules,
    }


def build_tuned_binary_single_split_report(
    csv_path: pathlib.Path = _DEFAULT_CSV,
    *,
    include_phi: bool = False,
    test_fraction: float = 0.3,
    seed: int = 0,
) -> dict:
    """Build the strict-consensus single-split report with tuned thresholds."""
    rows = load_holdout_rows(csv_path)
    elemental = _elemental_covered()
    needed = elemental & _pair_covered()
    from ..descriptors.omega import omega
    from ..descriptors.phi import phi_king, phi_ye
    from ..descriptors.size import delta

    rules = {
        "zhang_delta_tuned": tuned_binary_summary_to_dict(
            evaluate_binary_single_split_tuned(
                rows,
                descriptor_row=lambda row: delta(row["_composition"]),
                predict_from_value=lambda value, threshold: "single-phase" if value < threshold else "multi-phase",
                observed_label=lambda row: _binary_observed(str(row["canonical_phase"])),
                row_is_scorable=lambda row: set(row["_composition"]).issubset(elemental),
                positive_label="single-phase",
                thresholds=_ZHANG_THRESHOLD_GRID,
                default_threshold=zhang_delta.DEFAULT_THRESHOLD,
                test_fraction=test_fraction,
                seed=seed,
            )
        ),
        "yang_omega_tuned": tuned_binary_summary_to_dict(
            evaluate_binary_single_split_tuned(
                rows,
                descriptor_row=lambda row: omega(row["_composition"]),
                predict_from_value=lambda value, threshold: "single-phase" if value > threshold else "multi-phase",
                observed_label=lambda row: _binary_observed(str(row["canonical_phase"])),
                row_is_scorable=lambda row: set(row["_composition"]).issubset(needed),
                positive_label="single-phase",
                thresholds=_YANG_THRESHOLD_GRID,
                default_threshold=yang_omega.DEFAULT_THRESHOLD,
                test_fraction=test_fraction,
                seed=seed,
            )
        ),
    }
    if include_phi:
        rules["king_phi_tuned"] = tuned_binary_summary_to_dict(
            evaluate_binary_single_split_tuned(
                rows,
                descriptor_row=lambda row: phi_king(row["_composition"]),
                predict_from_value=lambda value, threshold: "solid_solution" if value > threshold else "intermetallic",
                observed_label=lambda row: _phi_observed(str(row["canonical_phase"])),
                row_is_scorable=lambda row: set(row["_composition"]).issubset(needed),
                positive_label="solid_solution",
                thresholds=_KING_THRESHOLD_GRID,
                default_threshold=king_phi.DEFAULT_THRESHOLD,
                test_fraction=test_fraction,
                seed=seed,
            )
        )
        rules["ye_phi_tuned"] = tuned_binary_summary_to_dict(
            evaluate_binary_single_split_tuned(
                rows,
                descriptor_row=lambda row: phi_ye(row["_composition"]),
                predict_from_value=lambda value, threshold: "solid_solution" if value > threshold else "intermetallic",
                observed_label=lambda row: _phi_observed(str(row["canonical_phase"])),
                row_is_scorable=lambda row: set(row["_composition"]).issubset(needed),
                positive_label="solid_solution",
                thresholds=_YE_THRESHOLD_GRID,
                default_threshold=ye_phi.DEFAULT_THRESHOLD,
                test_fraction=test_fraction,
                seed=seed,
            )
        )
    return {
        "csv_path": str(csv_path),
        "protocol": "strict_consensus_single_split_tuned",
        "test_fraction": test_fraction,
        "seed": seed,
        "rules": rules,
    }


__all__ = [
    "BinaryCVSummary",
    "DoubleScoredBinaryCVSummary",
    "FoldBinaryEvaluation",
    "FoldSplit",
    "TunedBinaryCVSummary",
    "TunedFoldBinaryEvaluation",
    "binary_summary_to_dict",
    "build_binary_holdout_report",
    "build_binary_single_split_report",
    "build_double_scored_binary_holdout_report",
    "build_double_scored_binary_single_split_report",
    "build_tuned_binary_holdout_report",
    "build_tuned_binary_single_split_report",
    "double_scored_binary_summary_to_dict",
    "evaluate_binary_kfold",
    "evaluate_binary_kfold_double_scored",
    "evaluate_binary_kfold_tuned",
    "evaluate_binary_single_split",
    "evaluate_binary_single_split_double_scored",
    "evaluate_binary_single_split_tuned",
    "evaluate_king_phi_holdout",
    "evaluate_king_phi_holdout_double_scored",
    "evaluate_king_phi_holdout_tuned",
    "evaluate_yang_omega_holdout",
    "evaluate_yang_omega_holdout_double_scored",
    "evaluate_yang_omega_holdout_tuned",
    "evaluate_ye_phi_holdout",
    "evaluate_ye_phi_holdout_double_scored",
    "evaluate_ye_phi_holdout_tuned",
    "evaluate_zhang_delta_holdout",
    "evaluate_zhang_delta_holdout_double_scored",
    "evaluate_zhang_delta_holdout_tuned",
    "load_holdout_rows",
    "phase_source_stratum",
    "source_signature",
    "strict_consensus_rows",
    "stratified_kfold_splits",
    "stratified_single_split",
    "tuned_binary_summary_to_dict",
]