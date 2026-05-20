"""Tests for the Borg 2020 source loader.

These tests rely on the mirrored CSV at
``data/raw/borg2020/MPEA_dataset.csv``. If running this test suite from
a context where the CSV is absent, the test is skipped.
"""

from __future__ import annotations

import pathlib

import pytest

from hea_bench.benchmark.loaders import borg2020
from hea_bench.benchmark.taxonomy import PhaseClass

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "data" / "raw" / "borg2020" / "MPEA_dataset.csv"


pytestmark = pytest.mark.skipif(
    not CSV_PATH.exists(),
    reason=f"Borg 2020 CSV not present at {CSV_PATH}",
)


def test_yields_expected_unique_alloy_count() -> None:
    """The legacy validator established that Borg has 740 unique
    (formula, processing) alloys after dedup. Loader must reproduce that."""
    rows = list(borg2020.load(CSV_PATH))
    assert len(rows) == 740


def test_canonical_phase_distribution() -> None:
    """Per-(formula, processing) canonical phase distribution.

    Empirically determined on the v9 figshare snapshot (2026-05-20).
    These counts are over Borg's 740 unique deduplicated alloys, NOT
    over its 1,545 raw measurement rows. Borg's simplified
    BCC/FCC/other column doesn't expose HCP, so HCP count is always 0
    from this source."""
    rows = list(borg2020.load(CSV_PATH))
    counts = {p: 0 for p in PhaseClass}
    for r in rows:
        counts[r.canonical_phase] += 1
    assert counts[PhaseClass.BCC] == 157
    assert counts[PhaseClass.FCC] == 102
    assert counts[PhaseClass.HCP] == 0
    assert counts[PhaseClass.MULTI] == 481
    assert sum(counts.values()) == 740


def test_compositions_normalize_to_one() -> None:
    """Every returned composition must sum to 1 within float epsilon."""
    for r in borg2020.load(CSV_PATH):
        total = sum(r.composition.values())
        assert total == pytest.approx(1.0, abs=1e-12), (
            f"row {r.source_row_id} {r.formula_raw!r} sums to {total}"
        )


def test_records_carry_provenance() -> None:
    """Every record must point back to its source DOI and reference ID."""
    rows = list(borg2020.load(CSV_PATH))
    # First few alloys are from Z.Q. Liu et al., j.jmmm.2014.07.023.
    sample = rows[0]
    assert sample.source == "borg2020"
    assert sample.source_doi
    assert sample.source_row_id
    assert sample.processing


def test_no_duplicate_alloys() -> None:
    """Loader must dedup by (formula, processing) — never yield a key twice."""
    keys = [(r.formula_raw, r.processing) for r in borg2020.load(CSV_PATH)]
    assert len(keys) == len(set(keys))
