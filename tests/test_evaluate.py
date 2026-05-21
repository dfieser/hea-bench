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

import pathlib

import pytest

from hea_bench.evaluate import build_report

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
V010 = REPO_ROOT / "data" / "consolidated" / "v0.1.0" / "consolidated.csv"

pytestmark = pytest.mark.skipif(not V010.exists(), reason=f"v0.1.0 CSV not at {V010}")


@pytest.fixture(scope="module")
def report():
    return build_report(V010)


# ---- Top-level loading ----

def test_loads_expected_non_conflict_rows(report):
    """v0.1.0 has 7,784 compositions; 100 have label conflicts (no
    canonical_phase); so 7,684 are usable as ground truth."""
    assert report["n_rows_loaded"] == 7684


# ---- Zhang δ < 6.5% (binary single vs multi) ----

def test_zhang_delta_accuracy_pinned(report):
    """Pinned 2026-05-20: accuracy 56.7% on 6,651 alloys with full
    ELEMENTAL_DATA coverage. This is the headline 'δ rule on the
    consolidated open benchmark' number."""
    z = report["rules"]["zhang_delta_6_5"]
    assert z["n"] == 6651
    assert z["accuracy"] == pytest.approx(0.5670, abs=0.0005)


def test_zhang_delta_sensitivity_high(report):
    """δ rule essentially never misses a single-phase alloy — high
    sensitivity is the rule's strength."""
    z = report["rules"]["zhang_delta_6_5"]
    assert z["sensitivity"] > 0.98


def test_zhang_delta_specificity_low(report):
    """δ rule almost never correctly identifies multi-phase alloys —
    low specificity is the rule's documented weakness on modern data."""
    z = report["rules"]["zhang_delta_6_5"]
    assert z["specificity"] < 0.10


def test_zhang_delta_weak_youden_j(report):
    """Youden's J = sens + spec - 1; well below 1.0 means weak
    classifier overall. Pinned for paper."""
    z = report["rules"]["zhang_delta_6_5"]
    assert z["youden_j"] == pytest.approx(0.0750, abs=0.001)


# ---- Yang Ω > 1.1 (binary single vs multi) ----

def test_yang_omega_accuracy_pinned(report):
    """Pinned 2026-05-20: accuracy 54.4% on 6,651 alloys with all 6
    descriptors covered."""
    y = report["rules"]["yang_omega_1_1"]
    assert y["n"] == 6651
    assert y["accuracy"] == pytest.approx(0.5443, abs=0.0005)


def test_yang_omega_high_sensitivity_low_specificity(report):
    """Same failure mode as Zhang δ — Ω rule also nearly always
    predicts single-phase."""
    y = report["rules"]["yang_omega_1_1"]
    assert y["sensitivity"] > 0.90
    assert y["specificity"] < 0.10


# ---- Guo-Liu VEC stratified to FCC|BCC observed ----

def test_guo_vec_stratified_accuracy(report):
    """VEC rule restricted to single-phase observed (BCC|FCC). Pinned
    2026-05-20: 66.9% on the 3,463 single-phase alloys.

    Note: this is lower than the 78.5% legacy validator reported on
    Borg alone, because the consolidated benchmark includes Pei +
    Peivaste, which contain many BCC compositions the canonical VEC
    bounds don't catch."""
    g = report["rules"]["guo_vec_stratified"]
    assert g["n_eval"] == 3463
    assert g["accuracy"] == pytest.approx(0.669, abs=0.001)


def test_guo_vec_fcc_strong_bcc_weak(report):
    """VEC rule is much better at identifying FCC than BCC on the
    consolidated benchmark — another publishable observation."""
    g = report["rules"]["guo_vec_stratified"]
    assert g["fcc_sensitivity"] > 0.90  # ~92.3%
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
