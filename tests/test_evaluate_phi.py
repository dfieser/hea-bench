"""Regression tests for the opt-in v1.1 phi evaluation path."""

import pathlib

import pytest

from hea_bench.evaluate import build_report

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
V010 = REPO_ROOT / "data" / "consolidated" / "v0.1.0" / "consolidated.csv"

pytestmark = pytest.mark.skipif(not V010.exists(), reason=f"v0.1.0 CSV not at {V010}")


@pytest.fixture(scope="module")
def report_phi():
    return build_report(V010, include_phi=True)


def test_phi_rules_are_opt_in() -> None:
    base = build_report(V010)
    assert "king_phi_1_0" not in base["rules"]
    assert "ye_phi_20_0" not in base["rules"]


def test_phi_rules_present_when_requested(report_phi) -> None:
    assert "king_phi_1_0" in report_phi["rules"]
    assert "ye_phi_20_0" in report_phi["rules"]


def test_king_phi_baseline_pinned(report_phi) -> None:
    k = report_phi["rules"]["king_phi_1_0"]
    assert k["n"] == 6922
    assert k["accuracy"] == pytest.approx(0.4889, abs=0.0005)
    assert k["sensitivity"] == pytest.approx(0.8271, abs=0.0005)
    assert k["specificity"] == pytest.approx(0.1116, abs=0.0005)
    assert k["youden_j"] == pytest.approx(-0.0613, abs=0.0005)


def test_ye_phi_baseline_pinned(report_phi) -> None:
    y = report_phi["rules"]["ye_phi_20_0"]
    assert y["n"] == 6922
    assert y["accuracy"] == pytest.approx(0.4912, abs=0.0005)
    assert y["sensitivity"] == pytest.approx(0.4422, abs=0.0005)
    assert y["specificity"] == pytest.approx(0.5458, abs=0.0005)
    assert y["youden_j"] == pytest.approx(-0.0120, abs=0.0005)