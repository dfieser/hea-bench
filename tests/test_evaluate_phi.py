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
    assert k["n"] == 7127


def test_ye_phi_baseline_pinned(report_phi) -> None:
    y = report_phi["rules"]["ye_phi_20_0"]
    assert y["n"] == 7127