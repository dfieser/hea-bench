"""Tests for the Chizhevskiy 2026 LLM-extracted HEA loader.

The normalizer tests (``chizhevskiy_canonical_phase``) are pure functions and
always run. The loader tests depend on the mirrored CSV at
``data/raw/chizhevskiy2026/database_of_HEAs.csv`` and skip if it is absent.
"""

from __future__ import annotations

import pathlib

import pytest

from hea_bench.benchmark.loaders import chizhevskiy2026
from hea_bench.benchmark.taxonomy import PhaseClass, chizhevskiy_canonical_phase

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CSV_PATH = REPO_ROOT / "data" / "raw" / "chizhevskiy2026" / "database_of_HEAs.csv"

requires_csv = pytest.mark.skipif(
    not CSV_PATH.exists(), reason=f"Chizhevskiy CSV not present at {CSV_PATH}"
)


# ---------------------------------------------------------------------------
# Pure-function normalizer tests (no CSV needed)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("BCC", PhaseClass.BCC),
        ("FCC", PhaseClass.FCC),
        ("HCP", PhaseClass.HCP),
        ("fcc", PhaseClass.FCC),                       # case-insensitive
        (" FCC ", PhaseClass.FCC),                     # whitespace-tolerant
        ("BCC + FCC", PhaseClass.MULTI),               # multi-phase SS mixture
        ("BCC B2 + FCC L12", PhaseClass.MULTI),        # ordered IMs
        ("C14 Laves phase + FCC", PhaseClass.MULTI),   # geometric IM
        ("BCC B2 (Intermetallic) + FCC", PhaseClass.MULTI),
        ("amorphous", PhaseClass.MULTI),
        ("sigma", PhaseClass.MULTI),                   # single-phase IM → MULTI
        ("FCC + sigma", PhaseClass.MULTI),
    ],
)
def test_canonical_phase_known_mappings(raw: str, expected: PhaseClass) -> None:
    assert chizhevskiy_canonical_phase(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "nan", "not specified", "Not specified", "unknown", "cubic",
     "FCC + HCP martensite", "n/a"],
)
def test_canonical_phase_skips_uninformative(raw: str) -> None:
    assert chizhevskiy_canonical_phase(raw) is None


def test_named_intermetallics_never_count_as_single_phase() -> None:
    """The crux: any B2/L12/Laves/sigma marker must collapse to multi-phase,
    never to a clean SS class — otherwise the SS-vs-IM benchmark is corrupted."""
    for raw in ("BCC B2", "FCC L12", "Laves", "C15 Laves phase", "BCC + B2"):
        assert chizhevskiy_canonical_phase(raw) == PhaseClass.MULTI


# ---------------------------------------------------------------------------
# Loader tests (require the CSV)
# ---------------------------------------------------------------------------

@requires_csv
def test_yields_expected_unique_alloy_count() -> None:
    """3,300 unique-composition alloys from the 12,427-row v1 snapshot
    (acquired 2026-06-06). Locks the dedup + skip behaviour."""
    rows = list(chizhevskiy2026.load(CSV_PATH))
    assert len(rows) == 3300


@requires_csv
def test_canonical_phase_distribution() -> None:
    """Canonical 4-class distribution over the 3,300 unique alloys.
    All named intermetallics collapse into multi-phase by design."""
    rows = list(chizhevskiy2026.load(CSV_PATH))
    counts = {p: 0 for p in PhaseClass}
    for r in rows:
        counts[r.canonical_phase] += 1
    assert counts[PhaseClass.BCC] == 598
    assert counts[PhaseClass.FCC] == 924
    assert counts[PhaseClass.HCP] == 56
    assert counts[PhaseClass.MULTI] == 1722
    assert sum(counts.values()) == 3300


@requires_csv
def test_compositions_normalize_to_one() -> None:
    for r in chizhevskiy2026.load(CSV_PATH):
        total = sum(r.composition.values())
        assert total == pytest.approx(1.0, abs=1e-9), (
            f"row {r.source_row_id} {r.formula_raw!r} sums to {total}"
        )


@requires_csv
def test_no_duplicate_compositions() -> None:
    """Dedup is composition-level: no composition key appears twice."""
    keys = [
        chizhevskiy2026._composition_key(r.composition)
        for r in chizhevskiy2026.load(CSV_PATH)
    ]
    assert len(keys) == len(set(keys))


@requires_csv
def test_records_carry_provenance_and_raw_label() -> None:
    rows = list(chizhevskiy2026.load(CSV_PATH))
    sample = rows[0]
    assert sample.source == "chizhevskiy2026"
    assert sample.source_row_id                 # the upstream `id`
    assert sample.source_label                  # raw Phase string preserved
    assert sample.processing is None            # no processing column
    assert sample.source_doi is None            # no per-row DOI in main file
