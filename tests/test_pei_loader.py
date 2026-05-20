"""Tests for the Pei 2020 source loader."""

from __future__ import annotations

import pathlib

import pytest

from hea_bench.benchmark.loaders import pei2020
from hea_bench.benchmark.taxonomy import PhaseClass

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "data" / "raw" / "pei2020" / "pei2020_alloys_phases.csv"

pytestmark = pytest.mark.skipif(
    not CSV_PATH.exists(),
    reason=f"Pei 2020 CSV not present at {CSV_PATH}",
)


def test_loader_runs_and_yields_records() -> None:
    rows = list(pei2020.load(CSV_PATH))
    # 1,252 upstream rows minus 43 duplicate formulas → 1,209 unique.
    # (Empirically determined 2026-05-20 against the mirrored CSV;
    # recorded here as ground truth so future drift fails the test.)
    assert len(rows) == 1209


def test_phase_classes_only_four() -> None:
    """No record may end up with a canonical phase outside the 4-class taxonomy."""
    rows = list(pei2020.load(CSV_PATH))
    seen = {r.canonical_phase for r in rows}
    assert seen.issubset({PhaseClass.BCC, PhaseClass.FCC, PhaseClass.HCP, PhaseClass.MULTI})


def test_canonical_phase_distribution() -> None:
    """Per-unique-formula canonical distribution.

    Upstream raw counts (over 1,252 rows) were bcc=261, fcc=218,
    hcp=146, multi-phase=627. After dedup-by-formula (43 duplicate
    formulas removed) the empirical 2026-05-20 distribution is:"""
    counts = {p: 0 for p in PhaseClass}
    for r in pei2020.load(CSV_PATH):
        counts[r.canonical_phase] += 1
    assert counts[PhaseClass.BCC] == 258
    assert counts[PhaseClass.FCC] == 206
    assert counts[PhaseClass.HCP] == 121
    assert counts[PhaseClass.MULTI] == 624
    assert sum(counts.values()) == 1209


def test_compositions_normalize_to_one() -> None:
    for r in pei2020.load(CSV_PATH):
        total = sum(r.composition.values())
        assert total == pytest.approx(1.0, abs=1e-12), (
            f"row {r.source_row_id} {r.formula_raw!r} sums to {total}"
        )


def test_no_duplicate_formulas() -> None:
    rows = list(pei2020.load(CSV_PATH))
    formulas = [r.formula_raw for r in rows]
    assert len(formulas) == len(set(formulas))


def test_records_carry_source_label_verbatim() -> None:
    """source_label is the upstream string, not the canonical class."""
    rows = list(pei2020.load(CSV_PATH))
    # All upstream labels are lower-case in Pei; canonical labels are upper-case.
    for r in rows:
        assert r.source_label == r.source_label.lower()
        # Source label must be one of Pei's 4
        assert r.source_label in {"bcc", "fcc", "hcp", "multi-phase"}


def test_cantor_alloy_is_fcc() -> None:
    """Known result check: CoCrFeMnNi is FCC per Pei (and per every other source)."""
    rows = list(pei2020.load(CSV_PATH))
    # Find the Cantor alloy if present (Pei's formula syntax: 'CoCrFeMnNi').
    cantor = [r for r in rows if set(r.composition) == {"Co", "Cr", "Fe", "Mn", "Ni"}]
    if cantor:
        # If multiple compositions of the Cantor system appear, the
        # equimolar one should be FCC. Look for the equimolar entry.
        equimolar = [
            r for r in cantor
            if all(abs(v - 0.2) < 1e-9 for v in r.composition.values())
        ]
        if equimolar:
            assert equimolar[0].canonical_phase == PhaseClass.FCC
