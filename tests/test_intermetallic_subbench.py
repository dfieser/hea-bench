"""Regression tests for the intermetallic-aware sub-benchmark.

The sub-benchmark scores the two phi-family rules against Peivaste's
12-class side-channel labels projected to a binary solid_solution
versus intermetallic ground truth. The pinned numbers below are the
v1.1.0 headline values from the live evaluator on the v0.1.0
consolidated CSV.
"""

from __future__ import annotations

import pathlib

import pytest

from hea_bench.benchmark.taxonomy import peivaste_intermetallic_label
from hea_bench.evaluate import (
    _load_intermetallic_subbench,
    build_intermetallic_subbench_report,
    evaluate_king_phi_intermetallic,
    evaluate_ye_phi_intermetallic,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
V010 = REPO_ROOT / "data" / "consolidated" / "v0.1.0" / "consolidated.csv"

pytestmark = pytest.mark.skipif(not V010.exists(), reason=f"v0.1.0 CSV not at {V010}")


# ---- Label projector --------------------------------------------------

def test_peivaste_intermetallic_label_solid_solution_classes() -> None:
    assert peivaste_intermetallic_label("BCC") == "solid_solution"
    assert peivaste_intermetallic_label("FCC") == "solid_solution"
    assert peivaste_intermetallic_label("HCP") == "solid_solution"
    assert peivaste_intermetallic_label("BCC+FCC") == "solid_solution"


def test_peivaste_intermetallic_label_intermetallic_classes() -> None:
    assert peivaste_intermetallic_label("IM") == "intermetallic"
    assert peivaste_intermetallic_label("FCC+IM") == "intermetallic"
    assert peivaste_intermetallic_label("BCC+IM") == "intermetallic"
    assert peivaste_intermetallic_label("BCC+FCC+IM") == "intermetallic"


def test_peivaste_intermetallic_label_excludes_amorphous() -> None:
    assert peivaste_intermetallic_label("AM") is None
    assert peivaste_intermetallic_label("FCC+AM") is None
    assert peivaste_intermetallic_label("BCC+AM") is None
    assert peivaste_intermetallic_label("BCC+FCC+AM") is None


def test_peivaste_intermetallic_label_empty_and_unknown() -> None:
    assert peivaste_intermetallic_label("") is None
    assert peivaste_intermetallic_label("   ") is None
    assert peivaste_intermetallic_label("not-a-real-label") is None


# ---- Sub-benchmark loader ---------------------------------------------

def test_subbench_loader_row_count() -> None:
    rows = _load_intermetallic_subbench(V010)
    assert len(rows) == 5930


def test_subbench_loader_marks_observed_label() -> None:
    rows = _load_intermetallic_subbench(V010)
    observed = {row["_intermetallic_observed"] for row in rows}
    assert observed == {"solid_solution", "intermetallic"}


def test_subbench_loader_overwrites_canonical_phase_for_stratification() -> None:
    """Each loaded row gets ``canonical_phase`` set to its sub-benchmark
    label so the held-out stratifier balances folds against the sub-
    benchmark ground truth rather than the main benchmark's coarse
    taxonomy."""
    rows = _load_intermetallic_subbench(V010)
    for row in rows:
        assert row["canonical_phase"] == row["_intermetallic_observed"]


# ---- In-sample headline numbers --------------------------------------

def test_king_phi_intermetallic_in_sample_pinned() -> None:
    rows = _load_intermetallic_subbench(V010)
    stats = evaluate_king_phi_intermetallic(rows)
    assert stats.n == 5481
    assert stats.accuracy == pytest.approx(0.7375, abs=0.0005)
    assert stats.sensitivity == pytest.approx(0.8456, abs=0.0005)
    assert stats.specificity == pytest.approx(0.1147, abs=0.0005)
    assert stats.youden_j == pytest.approx(-0.0397, abs=0.0005)


def test_ye_phi_intermetallic_in_sample_pinned() -> None:
    rows = _load_intermetallic_subbench(V010)
    stats = evaluate_ye_phi_intermetallic(rows)
    assert stats.n == 5481
    assert stats.accuracy == pytest.approx(0.4862, abs=0.0005)
    assert stats.sensitivity == pytest.approx(0.4443, abs=0.0005)
    assert stats.specificity == pytest.approx(0.7275, abs=0.0005)
    assert stats.youden_j == pytest.approx(0.1718, abs=0.0005)


# ---- Combined report (in-sample + held-out fixed + held-out tuned) ----

def test_build_intermetallic_subbench_report_shape() -> None:
    report = build_intermetallic_subbench_report(V010)
    assert report["n_rows_loaded"] == 5930
    assert report["ground_truth"] == "peivaste_intermetallic"
    assert set(report) >= {"in_sample", "holdout_fixed", "holdout_tuned"}
    assert set(report["in_sample"]) == {"king_phi_1_0", "ye_phi_20_0"}
    assert set(report["holdout_fixed"]) == {"king_phi_1_0", "ye_phi_20_0"}
    assert set(report["holdout_tuned"]) == {"king_phi_tuned", "ye_phi_tuned"}


def test_build_intermetallic_subbench_holdout_fixed_pinned() -> None:
    report = build_intermetallic_subbench_report(V010)

    king = report["holdout_fixed"]["king_phi_1_0"]
    assert king["accuracy_mean"] == pytest.approx(0.7375, abs=0.0005)
    assert king["youden_j_mean"] == pytest.approx(-0.0397, abs=0.0005)

    ye = report["holdout_fixed"]["ye_phi_20_0"]
    assert ye["accuracy_mean"] == pytest.approx(0.4862, abs=0.0005)
    assert ye["youden_j_mean"] == pytest.approx(0.1718, abs=0.0005)


def test_build_intermetallic_subbench_holdout_tuned_pinned() -> None:
    report = build_intermetallic_subbench_report(V010)

    king = report["holdout_tuned"]["king_phi_tuned"]
    assert king["accuracy_mean"] == pytest.approx(0.3215, abs=0.0005)
    assert king["youden_j_mean"] == pytest.approx(0.0119, abs=0.0005)
    assert king["threshold_mean"] == pytest.approx(2.696, abs=0.0005)

    ye = report["holdout_tuned"]["ye_phi_tuned"]
    assert ye["accuracy_mean"] == pytest.approx(0.6497, abs=0.0005)
    assert ye["youden_j_mean"] == pytest.approx(0.1812, abs=0.0005)
    assert ye["threshold_mean"] == pytest.approx(10.900, abs=0.0005)
