"""Integration tests for hea_bench.evaluate on the v0.1.0 release.

These tests pin the headline benchmark numbers — the actual scientific
output of the project. Any future drift in:
- the consolidated dataset
- the descriptor computations
- the rule thresholds
- the elemental data table
- the matminer-vendored pair-enthalpy table

will surface as a failing test here.
"""

import json

import pathlib

import pytest

from hea_bench.evaluate import build_evaluation_report, build_report, main

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
V010 = REPO_ROOT / "data" / "consolidated" / "v0.1.0" / "consolidated.csv"

pytestmark = pytest.mark.skipif(not V010.exists(), reason=f"v0.1.0 CSV not at {V010}")


@pytest.fixture(scope="module")
def report():
    return build_report(V010)


@pytest.fixture(scope="module")
def evaluation_report_phi():
    return build_evaluation_report(V010, include_phi=True)


@pytest.fixture(scope="module")
def evaluation_report_single_split_phi():
    return build_evaluation_report(V010, include_phi=True, holdout_mode="single_split", seed=0)


# ---- Top-level loading ----

def test_loads_expected_non_conflict_rows(report):
    """v0.1.0 has 7,784 compositions; 100 have label conflicts (no
    canonical_phase); so 7,684 are usable as ground truth."""
    assert report["n_rows_loaded"] == 7684


# ---- Zhang δ < 6.5% (binary single vs multi) ----

def test_zhang_delta_accuracy_pinned(report):
    """Pinned for the v1.2 30-element table: accuracy 57.1% on 6,922
    alloys with full ELEMENTAL_DATA coverage. This is the headline
    'δ rule on the consolidated open benchmark' number."""
    z = report["rules"]["zhang_delta_6_5"]
    assert z["n"] == 6922
    assert z["accuracy"] == pytest.approx(0.5711, abs=0.0005)


def test_zhang_delta_sensitivity_high(report):
    """δ rule essentially never misses a single-phase alloy — high
    sensitivity is the rule's strength."""
    z = report["rules"]["zhang_delta_6_5"]
    assert z["sensitivity"] > 0.98


def test_zhang_delta_specificity_low(report):
    """δ rule almost never correctly identifies multi-phase alloys —
    low specificity is the rule's documented weakness on modern data."""
    z = report["rules"]["zhang_delta_6_5"]
    assert z["specificity"] < 0.12


def test_zhang_delta_weak_youden_j(report):
    """Youden's J = sens + spec - 1; well below 1.0 means weak
    classifier overall. Pinned for paper."""
    z = report["rules"]["zhang_delta_6_5"]
    assert z["youden_j"] == pytest.approx(0.0939, abs=0.001)


# ---- Yang Ω > 1.1 (binary single vs multi) ----

def test_yang_omega_accuracy_pinned(report):
    """Pinned for the v1.2 30-element table: accuracy 54.2% on 6,922
    alloys with all six descriptors covered."""
    y = report["rules"]["yang_omega_1_1"]
    assert y["n"] == 6922
    assert y["accuracy"] == pytest.approx(0.5416, abs=0.0005)


def test_yang_omega_high_sensitivity_low_specificity(report):
    """Same failure mode as Zhang δ — Ω rule also nearly always
    predicts single-phase."""
    y = report["rules"]["yang_omega_1_1"]
    assert y["sensitivity"] > 0.90
    assert y["specificity"] < 0.10


# ---- Guo-Liu VEC stratified to FCC|BCC observed ----

def test_guo_vec_stratified_accuracy(report):
    """VEC rule restricted to single-phase observed (BCC|FCC). Pinned
    for the v1.2 30-element table: 67.4% on the 3,556 single-phase
    alloys.

    Note: this is lower than the 78.5% legacy validator reported on
    Borg alone, because the consolidated benchmark includes Pei +
    Peivaste, which contain many BCC compositions the canonical VEC
    bounds don't catch."""
    g = report["rules"]["guo_vec_stratified"]
    assert g["n_eval"] == 3556
    assert g["accuracy"] == pytest.approx(0.674, abs=0.001)


def test_guo_vec_fcc_strong_bcc_weak(report):
    """VEC rule is much better at identifying FCC than BCC on the
    consolidated benchmark — another publishable observation."""
    g = report["rules"]["guo_vec_stratified"]
    assert g["fcc_sensitivity"] > 0.90  # ~92.4%
    assert g["bcc_sensitivity"] < 0.55  # ~48.3%


# ---- Yeh ΔS_mix descriptive ----

def test_yeh_descriptive_fractions(report):
    """About half the consolidated benchmark is HEA-class by the 1.5R
    threshold; about a third is MEA-class."""
    s = report["rules"]["yeh_smix_descriptive"]
    assert s["n"] == 7684
    assert 0.45 < s["fraction_HEA"] < 0.50
    assert 0.35 < s["fraction_MEA"] < 0.40
    assert 0.15 < s["fraction_dilute"] < 0.18


def test_build_evaluation_report_adds_heldout_sections(evaluation_report_phi) -> None:
    assert evaluation_report_phi["holdout_mode"] == "kfold"
    assert evaluation_report_phi["in_sample"]["n_rows_loaded"] == 7684
    assert evaluation_report_phi["holdout_strict_consensus_fixed"]["protocol"] == "strict_consensus_kfold"
    assert evaluation_report_phi["holdout_double_scored_fixed"]["protocol"] == "double_scored_kfold"
    assert evaluation_report_phi["holdout_strict_consensus_tuned"]["protocol"] == "strict_consensus_kfold_tuned"
    assert "king_phi_1_0" in evaluation_report_phi["holdout_strict_consensus_fixed"]["rules"]
    assert "ye_phi_tuned" in evaluation_report_phi["holdout_strict_consensus_tuned"]["rules"]


def test_build_evaluation_report_single_split_uses_documented_seed(evaluation_report_single_split_phi) -> None:
    assert evaluation_report_single_split_phi["holdout_mode"] == "single_split"
    assert evaluation_report_single_split_phi["seed"] == 0
    assert evaluation_report_single_split_phi["test_fraction"] == pytest.approx(0.3)
    assert (
        evaluation_report_single_split_phi["holdout_strict_consensus_fixed"]["protocol"]
        == "strict_consensus_single_split"
    )
    assert (
        evaluation_report_single_split_phi["holdout_double_scored_fixed"]["protocol"]
        == "double_scored_single_split"
    )
    assert (
        evaluation_report_single_split_phi["holdout_strict_consensus_tuned"]["protocol"]
        == "strict_consensus_single_split_tuned"
    )


def test_main_default_writes_combined_report(tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = tmp_path / "evaluation-report.json"
    code = main(["--include-phi", "--single-split", "--output", str(output)])
    captured = capsys.readouterr()

    assert code == 0
    assert "Held-out strict-consensus fixed thresholds" in captured.out
    data = json.loads(output.read_text(encoding="utf-8"))
    assert "in_sample" in data
    assert "holdout_strict_consensus_fixed" in data
    assert "holdout_double_scored_fixed" in data
    assert "holdout_strict_consensus_tuned" in data


def test_main_in_sample_only_preserves_legacy_shape(tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = tmp_path / "rule-baselines.json"
    code = main(["--in-sample-only", "--output", str(output)])
    captured = capsys.readouterr()

    assert code == 0
    assert "Held-out strict-consensus fixed thresholds" not in captured.out
    data = json.loads(output.read_text(encoding="utf-8"))
    assert "rules" in data
    assert "in_sample" not in data


def _zhang_roc_points():
    """Reproduce the Zhang delta ROC sweep used by the paper figure:
    extract delta and binary observations from the benchmark, sweep
    1.0% to 12.0% in 0.1% steps. Shared by the tests below."""
    import csv

    from hea_bench.classifiers.diagnostic_stats import roc_sweep
    from hea_bench.composition import parse_formula
    from hea_bench.descriptors.data.elemental import covered_elements
    from hea_bench.descriptors.size import delta
    from hea_bench.evaluate import _binary_observed

    elemental = covered_elements()
    deltas, obs = [], []
    with V010.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            canonical = (row.get("canonical_phase") or "").strip()
            if not canonical:
                continue
            comp = parse_formula(row["composition_key"])
            if not set(comp).issubset(elemental):
                continue
            deltas.append(delta(comp))
            obs.append(_binary_observed(canonical))
    thresholds = [t / 10.0 for t in range(10, 121)]
    return roc_sweep(deltas, obs, thresholds, "single-phase",
                     positive_below_threshold=True)


def test_zhang_roc_recalibration_finding(report):
    """Pin the headline recalibration result reported in the paper and
    the figure. On the consolidated benchmark with the v1.2
    30-element table, the balance-optimal Zhang delta threshold is
    2.6% with Youden's J = 0.123, far tighter than the canonical 6.5%
    (J = 0.094). The qualitative finding (the dataset-optimal cutoff
    is ~2.5x tighter than the textbook value) is unchanged from
    v0.1.0; only the exact numbers shift with the wider element
    coverage."""
    points = _zhang_roc_points()
    canonical = min(points, key=lambda p: abs(p.threshold - 6.5))
    best_j = max(points, key=lambda p: p.youden_j)

    assert canonical.threshold == pytest.approx(6.5, abs=1e-9)
    assert canonical.youden_j == pytest.approx(0.094, abs=0.001)

    assert best_j.threshold == pytest.approx(2.6, abs=1e-9)
    assert best_j.youden_j == pytest.approx(0.123, abs=0.001)
    # The optimum trades sensitivity for specificity relative to canonical.
    assert best_j.sensitivity == pytest.approx(0.260, abs=0.005)
    assert best_j.specificity == pytest.approx(0.863, abs=0.005)
