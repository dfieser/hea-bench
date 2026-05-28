"""Tests for the Phase 5 held-out split primitives."""

from __future__ import annotations

import csv
import pathlib
from collections import Counter, defaultdict

import pytest

from hea_bench.evaluation.holdout import (
    build_binary_holdout_report,
    build_binary_single_split_report,
    build_double_scored_binary_holdout_report,
    build_double_scored_binary_single_split_report,
    build_tuned_binary_holdout_report,
    build_tuned_binary_single_split_report,
    evaluate_binary_kfold,
    evaluate_binary_kfold_double_scored,
    evaluate_binary_kfold_tuned,
    evaluate_binary_single_split,
    evaluate_zhang_delta_holdout,
    evaluate_zhang_delta_holdout_double_scored,
    evaluate_zhang_delta_holdout_tuned,
    load_holdout_rows,
    phase_source_stratum,
    source_signature,
    strict_consensus_rows,
    stratified_kfold_splits,
    stratified_single_split,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
V010 = REPO_ROOT / "data" / "consolidated" / "v0.1.0" / "consolidated.csv"


def _row(canonical_phase: str, sources: str) -> dict[str, str]:
    return {
        "canonical_phase": canonical_phase,
        "sources": sources,
    }


def test_source_signature_sorted() -> None:
    assert source_signature({"sources": "pei2020;borg2020"}) == "borg2020;pei2020"


def test_phase_source_stratum_uses_conflict_bucket() -> None:
    row = {"canonical_phase": "", "sources": "borg2020;peivaste"}
    assert phase_source_stratum(row) == ("conflict", "borg2020;peivaste")


def test_stratified_kfold_assigns_each_row_once() -> None:
    rows = [_row("BCC", "borg2020") for _ in range(10)] + [_row("FCC", "pei2020") for _ in range(10)]
    splits = stratified_kfold_splits(rows, k=5, seed=7)

    seen = []
    for split in splits:
        seen.extend(split.test_indices)

    assert sorted(seen) == list(range(len(rows)))


def test_stratified_kfold_balances_each_stratum() -> None:
    rows = (
        [_row("BCC", "borg2020") for _ in range(11)]
        + [_row("FCC", "pei2020") for _ in range(7)]
        + [_row("", "borg2020;peivaste") for _ in range(6)]
    )
    splits = stratified_kfold_splits(rows, k=5, seed=3)

    counts_by_stratum: dict[tuple[str, str], list[int]] = defaultdict(list)
    for split in splits:
        test_rows = [rows[i] for i in split.test_indices]
        test_counts = Counter(phase_source_stratum(row) for row in test_rows)
        for stratum in {phase_source_stratum(row) for row in rows}:
            counts_by_stratum[stratum].append(test_counts.get(stratum, 0))

    for counts in counts_by_stratum.values():
        assert max(counts) - min(counts) <= 1


def test_stratified_single_split_is_deterministic() -> None:
    rows = [_row("BCC", "borg2020") for _ in range(10)] + [_row("FCC", "pei2020") for _ in range(10)]
    a = stratified_single_split(rows, test_fraction=0.3, seed=11)
    b = stratified_single_split(rows, test_fraction=0.3, seed=11)
    assert a == b
    assert len(a.test_indices) == 6


def test_stratified_single_split_keeps_singletons_in_train() -> None:
    rows = [_row("BCC", "borg2020"), _row("FCC", "pei2020"), _row("FCC", "pei2020")]
    split = stratified_single_split(rows, test_fraction=0.3, seed=0)
    assert 0 in split.train_indices
    assert 0 not in split.test_indices


def test_strict_consensus_rows_filters_conflicts() -> None:
    rows = [_row("BCC", "borg2020"), _row("", "pei2020")]
    filtered = strict_consensus_rows(rows)
    assert filtered == [_row("BCC", "borg2020")]


def test_evaluate_binary_kfold_scores_all_strict_consensus_rows() -> None:
    rows = [
        {"canonical_phase": "BCC", "sources": "borg2020", "pred": "solid_solution", "obs": "solid_solution"},
        {"canonical_phase": "FCC", "sources": "borg2020", "pred": "solid_solution", "obs": "solid_solution"},
        {"canonical_phase": "multi-phase", "sources": "pei2020", "pred": "intermetallic", "obs": "intermetallic"},
        {"canonical_phase": "multi-phase", "sources": "pei2020", "pred": "intermetallic", "obs": "intermetallic"},
        {"canonical_phase": "", "sources": "pei2020;peivaste", "pred": "solid_solution", "obs": None},
    ]

    summary = evaluate_binary_kfold(
        rows,
        predict_row=lambda row: str(row["pred"]),
        observed_label=lambda row: row["obs"],
        positive_label="solid_solution",
        k=2,
        seed=0,
    )

    assert summary.n_folds == 2
    assert summary.n_rows_total == 5
    assert summary.n_rows_scored == 4
    assert summary.accuracy_mean == pytest.approx(1.0)
    assert all(fold.stats.accuracy == pytest.approx(1.0) for fold in summary.folds)


def test_evaluate_binary_single_split_scores_all_strict_consensus_rows() -> None:
    rows = [
        {"canonical_phase": "BCC", "sources": "borg2020", "pred": "solid_solution", "obs": "solid_solution"},
        {"canonical_phase": "BCC", "sources": "borg2020", "pred": "solid_solution", "obs": "solid_solution"},
        {"canonical_phase": "multi-phase", "sources": "pei2020", "pred": "intermetallic", "obs": "intermetallic"},
        {"canonical_phase": "multi-phase", "sources": "pei2020", "pred": "intermetallic", "obs": "intermetallic"},
        {"canonical_phase": "", "sources": "pei2020;peivaste", "pred": "solid_solution", "obs": None},
    ]

    summary = evaluate_binary_single_split(
        rows,
        predict_row=lambda row: str(row["pred"]),
        observed_label=lambda row: row["obs"],
        positive_label="solid_solution",
        test_fraction=0.5,
        seed=0,
    )

    assert summary.n_folds == 1
    assert summary.n_rows_total == 5
    assert summary.n_rows_scored == 2
    assert summary.accuracy_mean == pytest.approx(1.0)


def test_evaluate_binary_kfold_double_scored_bounds_conflict_rows() -> None:
    rows = [
        {
            "canonical_phase": "",
            "sources": "borg2020;peivaste",
            "borg_label": "FCC",
            "pei_label": "",
            "peivaste_label": "multi-phase",
            "pred": "single-phase",
        },
        {
            "canonical_phase": "",
            "sources": "pei2020;peivaste",
            "borg_label": "",
            "pei_label": "multi-phase",
            "peivaste_label": "FCC",
            "pred": "multi-phase",
        },
    ]

    summary = evaluate_binary_kfold_double_scored(
        rows,
        predict_row=lambda row: str(row["pred"]),
        observed_label_set=lambda row: frozenset(
            label for label in (
                "single-phase" if row.get("borg_label") == "FCC" else "",
                "single-phase" if row.get("peivaste_label") == "FCC" else "",
                "multi-phase" if row.get("pei_label") == "multi-phase" else "",
                "multi-phase" if row.get("peivaste_label") == "multi-phase" else "",
            ) if label
        ),
        positive_label="single-phase",
        k=2,
        seed=0,
    )

    assert summary.n_rows_scored == 2
    assert summary.any_match.accuracy_mean == pytest.approx(1.0)
    assert summary.all_match.accuracy_mean == pytest.approx(0.0)


def test_evaluate_binary_kfold_tuned_uses_train_only_thresholds() -> None:
    rows = [
        {"canonical_phase": "BCC", "sources": "borg2020", "value": 1.0, "obs": "single-phase"},
        {"canonical_phase": "BCC", "sources": "borg2020", "value": 1.2, "obs": "single-phase"},
        {"canonical_phase": "multi-phase", "sources": "pei2020", "value": 2.8, "obs": "multi-phase"},
        {"canonical_phase": "multi-phase", "sources": "pei2020", "value": 3.0, "obs": "multi-phase"},
    ]

    summary = evaluate_binary_kfold_tuned(
        rows,
        descriptor_row=lambda row: float(row["value"]),
        predict_from_value=lambda value, threshold: "single-phase" if value < threshold else "multi-phase",
        observed_label=lambda row: row["obs"],
        positive_label="single-phase",
        thresholds=(0.5, 2.0, 3.5),
        default_threshold=6.5,
        k=2,
        seed=0,
    )

    assert summary.n_rows_scored == 4
    assert summary.accuracy_mean == pytest.approx(1.0)
    assert summary.threshold_mean == pytest.approx(2.0)


pytestmark_v010 = pytest.mark.skipif(not V010.exists(), reason=f"v0.1.0 CSV not at {V010}")


@pytestmark_v010
def test_real_benchmark_kfold_covers_all_rows_once() -> None:
    with V010.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    splits = stratified_kfold_splits(rows, k=5, seed=0)
    test_indices = sorted(index for split in splits for index in split.test_indices)
    assert test_indices == list(range(len(rows)))


@pytestmark_v010
def test_real_benchmark_kfold_balances_phase_source_strata() -> None:
    with V010.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    splits = stratified_kfold_splits(rows, k=5, seed=0)
    strata = {phase_source_stratum(row) for row in rows}

    counts_by_stratum: dict[tuple[str, str], list[int]] = defaultdict(list)
    for split in splits:
        test_counts = Counter(phase_source_stratum(rows[i]) for i in split.test_indices)
        for stratum in strata:
            counts_by_stratum[stratum].append(test_counts.get(stratum, 0))

    for counts in counts_by_stratum.values():
        assert max(counts) - min(counts) <= 1


@pytestmark_v010
def test_real_benchmark_binary_kfold_summary_is_deterministic() -> None:
    from hea_bench.composition import parse_formula
    from hea_bench.descriptors.data.elemental import covered_elements
    from hea_bench.evaluate import _binary_observed
    from hea_bench.rules import zhang_delta

    with V010.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    filtered = []
    for row in rows:
        canonical = (row.get("canonical_phase") or "").strip()
        if not canonical:
            continue
        row = dict(row)
        row["_composition"] = parse_formula(row["composition_key"])
        filtered.append(row)

    elemental = covered_elements()

    summary_a = evaluate_binary_kfold(
        filtered,
        predict_row=lambda row: zhang_delta.predict(row["_composition"]),
        observed_label=lambda row: _binary_observed(str(row["canonical_phase"])),
        row_is_scorable=lambda row: set(row["_composition"]).issubset(elemental),
        positive_label="single-phase",
        k=5,
        seed=0,
    )
    summary_b = evaluate_binary_kfold(
        filtered,
        predict_row=lambda row: zhang_delta.predict(row["_composition"]),
        observed_label=lambda row: _binary_observed(str(row["canonical_phase"])),
        row_is_scorable=lambda row: set(row["_composition"]).issubset(elemental),
        positive_label="single-phase",
        k=5,
        seed=0,
    )

    assert summary_a == summary_b
    assert summary_a.n_rows_scored == 6922
    assert 0.0 <= summary_a.accuracy_mean <= 1.0


@pytestmark_v010
def test_load_holdout_rows_keeps_conflicts() -> None:
    rows = load_holdout_rows(V010)
    assert len(rows) == 7784
    assert any((row.get("canonical_phase") or "") == "" for row in rows)


@pytestmark_v010
def test_rule_specific_holdout_summary_matches_generic_shape() -> None:
    rows = load_holdout_rows(V010)
    summary = evaluate_zhang_delta_holdout(rows, k=5, seed=0)
    assert summary.n_folds == 5
    assert summary.n_rows_total == 7784
    assert summary.n_rows_scored == 6922
    assert 0.0 <= summary.accuracy_mean <= 1.0


@pytestmark_v010
def test_build_binary_holdout_report_includes_phi_when_requested() -> None:
    report = build_binary_holdout_report(V010, include_phi=True, k=5, seed=0)
    assert report["protocol"] == "strict_consensus_kfold"
    assert report["k"] == 5
    assert report["seed"] == 0
    assert set(report["rules"]) == {
        "zhang_delta_6_5",
        "yang_omega_1_1",
        "king_phi_1_0",
        "ye_phi_20_0",
    }


@pytestmark_v010
def test_build_binary_single_split_report_includes_phi_when_requested() -> None:
    report = build_binary_single_split_report(V010, include_phi=True, test_fraction=0.3, seed=0)
    assert report["protocol"] == "strict_consensus_single_split"
    assert report["test_fraction"] == pytest.approx(0.3)
    assert report["seed"] == 0
    assert set(report["rules"]) == {
        "zhang_delta_6_5",
        "yang_omega_1_1",
        "king_phi_1_0",
        "ye_phi_20_0",
    }


@pytestmark_v010
def test_build_binary_holdout_report_pinned_metrics() -> None:
    report = build_binary_holdout_report(V010, include_phi=True, k=5, seed=0)

    z = report["rules"]["zhang_delta_6_5"]
    assert z["accuracy_mean"] == pytest.approx(0.57108, abs=0.0005)
    assert z["youden_j_mean"] == pytest.approx(0.09389, abs=0.0005)

    y = report["rules"]["yang_omega_1_1"]
    assert y["accuracy_mean"] == pytest.approx(0.54161, abs=0.0005)
    assert y["youden_j_mean"] == pytest.approx(0.03605, abs=0.0005)

    k = report["rules"]["king_phi_1_0"]
    assert k["accuracy_mean"] == pytest.approx(0.48888, abs=0.0005)
    assert k["youden_j_mean"] == pytest.approx(-0.06132, abs=0.0005)

    p = report["rules"]["ye_phi_20_0"]
    assert p["accuracy_mean"] == pytest.approx(0.49119, abs=0.0005)
    assert p["youden_j_mean"] == pytest.approx(-0.01197, abs=0.0005)


@pytestmark_v010
def test_build_double_scored_holdout_report_includes_phi_when_requested() -> None:
    report = build_double_scored_binary_holdout_report(V010, include_phi=True, k=5, seed=0)
    assert report["protocol"] == "double_scored_kfold"
    assert set(report["rules"]) == {
        "zhang_delta_6_5",
        "yang_omega_1_1",
        "king_phi_1_0",
        "ye_phi_20_0",
    }


@pytestmark_v010
def test_build_double_scored_single_split_report_includes_phi_when_requested() -> None:
    report = build_double_scored_binary_single_split_report(V010, include_phi=True, test_fraction=0.3, seed=0)
    assert report["protocol"] == "double_scored_single_split"
    assert report["test_fraction"] == pytest.approx(0.3)
    assert set(report["rules"]) == {
        "zhang_delta_6_5",
        "yang_omega_1_1",
        "king_phi_1_0",
        "ye_phi_20_0",
    }


@pytestmark_v010
def test_rule_specific_double_scored_summary_has_expected_bounds() -> None:
    rows = load_holdout_rows(V010)
    summary = evaluate_zhang_delta_holdout_double_scored(rows, k=5, seed=0)
    assert summary.n_rows_total == 7784
    assert summary.n_rows_scored >= 6922
    assert summary.any_match.accuracy_mean >= summary.all_match.accuracy_mean


@pytestmark_v010
def test_build_double_scored_holdout_report_pinned_metrics() -> None:
    report = build_double_scored_binary_holdout_report(V010, include_phi=True, k=5, seed=0)

    z = report["rules"]["zhang_delta_6_5"]
    assert z["any_match"]["accuracy_mean"] == pytest.approx(0.57713, abs=0.0005)
    assert z["all_match"]["accuracy_mean"] == pytest.approx(0.56303, abs=0.0005)

    y = report["rules"]["yang_omega_1_1"]
    assert y["any_match"]["accuracy_mean"] == pytest.approx(0.54807, abs=0.0005)
    assert y["all_match"]["accuracy_mean"] == pytest.approx(0.53397, abs=0.0005)

    k = report["rules"]["king_phi_1_0"]
    assert k["any_match"]["accuracy_mean"] == pytest.approx(0.49608, abs=0.0005)
    assert k["all_match"]["accuracy_mean"] == pytest.approx(0.48198, abs=0.0005)

    p = report["rules"]["ye_phi_20_0"]
    assert p["any_match"]["accuracy_mean"] == pytest.approx(0.49836, abs=0.0005)
    assert p["all_match"]["accuracy_mean"] == pytest.approx(0.48426, abs=0.0005)


@pytestmark_v010
def test_rule_specific_tuned_summary_has_expected_shape() -> None:
    rows = load_holdout_rows(V010)
    summary = evaluate_zhang_delta_holdout_tuned(rows, k=5, seed=0)
    assert summary.n_folds == 5
    assert summary.n_rows_total == 7784
    assert summary.n_rows_scored == 6922
    assert len(summary.folds) == 5
    assert all(isinstance(fold.tuned_threshold, float) for fold in summary.folds)


@pytestmark_v010
def test_build_tuned_binary_holdout_report_includes_phi_when_requested() -> None:
    report = build_tuned_binary_holdout_report(V010, include_phi=True, k=5, seed=0)
    assert report["protocol"] == "strict_consensus_kfold_tuned"
    assert set(report["rules"]) == {
        "zhang_delta_tuned",
        "yang_omega_tuned",
        "king_phi_tuned",
        "ye_phi_tuned",
    }


@pytestmark_v010
def test_build_tuned_binary_single_split_report_includes_phi_when_requested() -> None:
    report = build_tuned_binary_single_split_report(V010, include_phi=True, test_fraction=0.3, seed=0)
    assert report["protocol"] == "strict_consensus_single_split_tuned"
    assert report["test_fraction"] == pytest.approx(0.3)
    assert set(report["rules"]) == {
        "zhang_delta_tuned",
        "yang_omega_tuned",
        "king_phi_tuned",
        "ye_phi_tuned",
    }


@pytestmark_v010
def test_build_tuned_binary_holdout_report_pinned_metrics() -> None:
    report = build_tuned_binary_holdout_report(V010, include_phi=True, k=5, seed=0)

    z = report["rules"]["zhang_delta_tuned"]
    assert z["accuracy_mean"] == pytest.approx(0.54320, abs=0.0005)
    assert z["threshold_mean"] == pytest.approx(2.58, abs=0.0005)
    assert z["fold_thresholds"] == pytest.approx([2.5, 2.6, 2.5, 2.6, 2.7])

    y = report["rules"]["yang_omega_tuned"]
    assert y["accuracy_mean"] == pytest.approx(0.52716, abs=0.0005)
    assert y["threshold_mean"] == pytest.approx(9.64, abs=0.0005)
    assert y["fold_thresholds"] == pytest.approx([10.1, 10.05, 7.95, 10.1, 10.0])

    k = report["rules"]["king_phi_tuned"]
    assert k["accuracy_mean"] == pytest.approx(0.51344, abs=0.0005)
    assert k["threshold_mean"] == pytest.approx(4.196, abs=0.0005)
    assert k["fold_thresholds"] == pytest.approx([4.24, 4.24, 4.18, 4.14, 4.18])

    p = report["rules"]["ye_phi_tuned"]
    assert p["accuracy_mean"] == pytest.approx(0.52138, abs=0.0005)
    assert p["threshold_mean"] == pytest.approx(51.6, abs=0.0005)
    assert p["fold_thresholds"] == pytest.approx([49.5, 49.5, 56.0, 53.5, 49.5])