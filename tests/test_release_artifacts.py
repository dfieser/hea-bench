"""Guard against drift between the committed v0.1.0 release artifacts
and a fresh recomputation.

The release directory ships three machine-readable artifacts
(rule_baselines.json, coverage_report.json, manifest.json) that are
derived from the consolidated benchmark plus the library code. If the
code or the data changes but the artifacts are not regenerated and
re-committed, the documentation and paper that quote those artifacts
go stale silently. These tests recompute the headline statistics and
assert they match the committed JSON, so any such drift breaks the
build.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from hea_bench.benchmark.coverage import analyze
from hea_bench.evaluate import build_report

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
V010 = REPO_ROOT / "data" / "consolidated" / "v0.1.0"
CSV = V010 / "consolidated.csv"

pytestmark = pytest.mark.skipif(not CSV.exists(), reason=f"v0.1.0 CSV not at {CSV}")


def test_committed_rule_baselines_matches_fresh_build() -> None:
    """rule_baselines.json must equal a fresh build_report() on the
    committed benchmark, compared on the rule statistics (the csv_path
    field is an absolute path and is excluded from the comparison)."""
    committed = json.loads((V010 / "rule_baselines.json").read_text(encoding="utf-8"))
    fresh = build_report(CSV)
    assert committed["n_rows_loaded"] == fresh["n_rows_loaded"]
    assert committed["rules"] == fresh["rules"]


def test_committed_coverage_report_matches_fresh_analyze() -> None:
    """coverage_report.json must equal a fresh analyze() on the
    committed benchmark, on the headline coverage counts."""
    committed = json.loads((V010 / "coverage_report.json").read_text(encoding="utf-8"))
    fresh = analyze(CSV)
    for key in ("total", "in_basic", "in_miedema", "in_both", "in_neither"):
        assert committed[key] == fresh[key], f"coverage field {key!r} drifted"


def test_manifest_totals_match_benchmark() -> None:
    """manifest.json's stated unique-composition total must match the
    actual row count of the consolidated CSV."""
    import csv

    manifest = json.loads((V010 / "manifest.json").read_text(encoding="utf-8"))
    with CSV.open(newline="", encoding="utf-8") as f:
        n_rows = sum(1 for _ in csv.DictReader(f))
    assert manifest["totals"]["unique_compositions"] == n_rows
