"""Tests for the Peivaste source loader."""

from __future__ import annotations

import pathlib

import pytest

from hea_bench.benchmark.loaders import peivaste
from hea_bench.benchmark.taxonomy import PhaseClass

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "data" / "raw" / "peivaste" / "dataset11252_79.csv"


def test_missing_file_raises_with_helpful_message(tmp_path: pathlib.Path) -> None:
    """When the CSV hasn't been fetched, the loader must fail with an
    actionable error pointing at fetch.py."""
    missing = tmp_path / "nonexistent.csv"
    with pytest.raises(FileNotFoundError) as excinfo:
        list(peivaste.load(missing))
    msg = str(excinfo.value)
    assert "Peivaste is pointer-only" in msg
    assert "fetch.py" in msg
    # Path of the would-be fetch.py is included so the user can copy-paste
    assert str(tmp_path / "fetch.py") in msg


# The remaining tests need the actual fetched CSV. Skip if absent so the
# suite still passes in a fresh clone where the user hasn't fetched yet.
needs_csv = pytest.mark.skipif(
    not CSV_PATH.exists(),
    reason=f"Peivaste CSV not present at {CSV_PATH}; run data/raw/peivaste/fetch.py",
)


@needs_csv
def test_yields_expected_unique_formula_count() -> None:
    """11,252 upstream rows minus 3,505 duplicate formulas → 7,747 unique.
    Empirically determined 2026-05-20 against the upstream `main` snapshot."""
    rows = list(peivaste.load(CSV_PATH))
    assert len(rows) == 7747


@needs_csv
def test_canonical_phase_distribution() -> None:
    """Per-unique-formula canonical distribution. Empirically determined
    2026-05-20."""
    counts = {p: 0 for p in PhaseClass}
    for r in peivaste.load(CSV_PATH):
        counts[r.canonical_phase] += 1
    assert counts[PhaseClass.BCC] == 2325
    assert counts[PhaseClass.FCC] == 1726
    assert counts[PhaseClass.HCP] == 129
    assert counts[PhaseClass.MULTI] == 3567
    assert sum(counts.values()) == 7747


@needs_csv
def test_compositions_normalize_to_one() -> None:
    for r in peivaste.load(CSV_PATH):
        total = sum(r.composition.values())
        assert total == pytest.approx(1.0, abs=1e-12), (
            f"row {r.source_row_id} {r.formula_raw!r} sums to {total}"
        )


@needs_csv
def test_no_duplicate_formulas() -> None:
    rows = list(peivaste.load(CSV_PATH))
    formulas = [r.formula_raw for r in rows]
    assert len(formulas) == len(set(formulas))


@needs_csv
def test_source_labels_are_in_known_set() -> None:
    """Peivaste publishes 12 distinct phase categories. Anything else
    would be a sign of upstream schema drift."""
    expected = {
        "BCC", "FCC", "HCP",
        "AM", "IM",
        "BCC+FCC", "FCC+IM", "BCC+IM", "BCC+FCC+IM",
        "FCC+AM", "BCC+AM", "BCC+FCC+AM",
    }
    seen = {r.source_label for r in peivaste.load(CSV_PATH)}
    assert seen.issubset(expected), f"unexpected labels: {seen - expected}"


@needs_csv
def test_first_record_sanity() -> None:
    """The first row of the upstream CSV is AlAuCoCrCuNi (6-element equimolar)
    labeled FCC+IM — verify the loader handles the column-offset quirk and
    correctly maps the source label to MULTI."""
    rows = list(peivaste.load(CSV_PATH))
    first = rows[0]
    assert first.source == "peivaste"
    assert first.formula_raw == "AlAuCoCrCuNi"
    assert set(first.composition) == {"Al", "Au", "Co", "Cr", "Cu", "Ni"}
    # 6 elements equimolar → each gets 1/6
    for v in first.composition.values():
        assert v == pytest.approx(1 / 6, rel=1e-12)
    assert first.source_label == "FCC+IM"
    assert first.canonical_phase == PhaseClass.MULTI


@needs_csv
def test_records_have_no_processing_or_doi() -> None:
    """Peivaste has neither a processing column nor per-row DOIs. Both
    optional fields must be None."""
    rows = list(peivaste.load(CSV_PATH))
    for r in rows[:50]:  # sampling — 50 is plenty to catch a regression
        assert r.processing is None
        assert r.source_doi is None
