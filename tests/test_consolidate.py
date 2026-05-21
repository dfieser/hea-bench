"""Tests for hea_bench.benchmark.consolidate."""

from __future__ import annotations

import csv
import json
import pathlib

import pytest

from hea_bench.benchmark import consolidate as C
from hea_bench.benchmark.loaders import AlloyRecord
from hea_bench.benchmark.taxonomy import PhaseClass

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
V010 = REPO_ROOT / "data" / "consolidated" / "v0.1.0"


# ---- canonical_formula_key ----

def test_key_is_alphabetically_sorted() -> None:
    """Elements sort by symbol regardless of insertion order."""
    a = C.canonical_formula_key({"Fe": 0.5, "Co": 0.5})
    b = C.canonical_formula_key({"Co": 0.5, "Fe": 0.5})
    assert a == b == "Co0.5000Fe0.5000"


def test_key_handles_float_noise() -> None:
    """Compositions differing only by float epsilon hash to the same key."""
    a = C.canonical_formula_key({"Co": 0.5, "Fe": 0.5})
    b = C.canonical_formula_key({"Co": 0.500000001, "Fe": 0.499999999})
    assert a == b


def test_key_distinguishes_genuinely_different_compositions() -> None:
    """A 5% shift in a fraction must produce a different key."""
    a = C.canonical_formula_key({"Al": 0.10, "Fe": 0.90})
    b = C.canonical_formula_key({"Al": 0.15, "Fe": 0.85})
    assert a != b


# ---- consolidate() with synthetic records ----

def _rec(source: str, formula: str, comp: dict, phase: PhaseClass, raw: str = "", processing=None, doi=None):
    return AlloyRecord(
        source=source,
        source_row_id="0",
        formula_raw=formula,
        composition=comp,
        canonical_phase=phase,
        source_label=raw or phase.value,
        processing=processing,
        source_doi=doi,
    )


def test_consolidate_single_source_passes_through() -> None:
    rows = C.consolidate([_rec("borg2020", "CoCrFeMnNi", {"Co":0.2,"Cr":0.2,"Fe":0.2,"Mn":0.2,"Ni":0.2}, PhaseClass.FCC)])
    assert len(rows) == 1
    r = rows[0]
    assert r.canonical_phase == PhaseClass.FCC
    assert r.has_conflict is False
    assert r.sources == ["borg2020"]
    assert r.n_elements == 5


def test_consolidate_agreement_across_sources_no_conflict() -> None:
    comp = {"Co": 0.5, "Fe": 0.5}
    rows = C.consolidate([
        _rec("borg2020", "CoFe", comp, PhaseClass.BCC),
        _rec("pei2020",  "CoFe", comp, PhaseClass.BCC),
        _rec("peivaste", "CoFe", comp, PhaseClass.BCC),
    ])
    assert len(rows) == 1
    r = rows[0]
    assert r.has_conflict is False
    assert r.canonical_phase == PhaseClass.BCC
    assert r.sources == ["borg2020", "pei2020", "peivaste"]


def test_consolidate_disagreement_flags_conflict() -> None:
    comp = {"Co": 0.5, "Fe": 0.5}
    rows = C.consolidate([
        _rec("borg2020", "CoFe", comp, PhaseClass.BCC),
        _rec("pei2020",  "CoFe", comp, PhaseClass.FCC),
    ])
    assert len(rows) == 1
    r = rows[0]
    assert r.has_conflict is True
    assert r.canonical_phase is None
    assert r.per_source_canonical["borg2020"] == PhaseClass.BCC
    assert r.per_source_canonical["pei2020"] == PhaseClass.FCC


def test_consolidate_distinct_compositions_stay_separate() -> None:
    rows = C.consolidate([
        _rec("borg2020", "CoFe",  {"Co": 0.5, "Fe": 0.5}, PhaseClass.BCC),
        _rec("pei2020",  "CoFe2", {"Co": 1/3, "Fe": 2/3}, PhaseClass.BCC),
    ])
    assert len(rows) == 2


def test_consolidate_borg_processing_preserved() -> None:
    rows = C.consolidate([
        _rec("borg2020", "CoFe", {"Co":0.5,"Fe":0.5}, PhaseClass.BCC,
             processing="CAST", doi="10.1/foo"),
        _rec("pei2020",  "CoFe", {"Co":0.5,"Fe":0.5}, PhaseClass.BCC),
    ])
    assert rows[0].borg_processing == "CAST"
    assert rows[0].borg_doi == "10.1/foo"


# ---- Integration tests against the committed v0.1.0 release ----

pytestmark_v010 = pytest.mark.skipif(
    not (V010 / "consolidated.csv").exists(),
    reason=f"v0.1.0 release not built at {V010}",
)


@pytestmark_v010
def test_v010_csv_row_count_matches_manifest() -> None:
    manifest = json.loads((V010 / "manifest.json").read_text())
    with (V010 / "consolidated.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == manifest["totals"]["unique_compositions"]


@pytestmark_v010
def test_v010_canonical_distribution_sums_to_total() -> None:
    """canonical_distribution counts must sum to the total composition count."""
    m = json.loads((V010 / "manifest.json").read_text())
    dist = m["totals"]["canonical_distribution"]
    assert sum(dist.values()) == m["totals"]["unique_compositions"]


@pytestmark_v010
def test_v010_overlap_buckets_sum_to_total() -> None:
    m = json.loads((V010 / "manifest.json").read_text())
    ov = m["totals"]["by_source_overlap"]
    assert ov["single_source"] + ov["two_sources"] + ov["three_sources"] == m["totals"]["unique_compositions"]


@pytestmark_v010
def test_v010_has_conflict_column_consistent_with_canonical_phase() -> None:
    """has_conflict=1 ↔ canonical_phase column is empty, and vice versa."""
    with (V010 / "consolidated.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["has_conflict"] == "1":
                assert row["canonical_phase"] == ""
            else:
                assert row["canonical_phase"] != ""


@pytestmark_v010
def test_v010_committed_numbers() -> None:
    """Empirically pinned 2026-05-20 for the v0.1.0 release. These are the
    headline numbers that should appear in the paper."""
    m = json.loads((V010 / "manifest.json").read_text())
    assert m["totals"]["unique_compositions"] == 7784
    assert m["totals"]["canonical_distribution"]["BCC"] == 2118
    assert m["totals"]["canonical_distribution"]["FCC"] == 1556
    assert m["totals"]["canonical_distribution"]["HCP"] == 123
    assert m["totals"]["canonical_distribution"]["multi-phase"] == 3887
    assert m["totals"]["canonical_distribution"]["conflict"] == 100
    assert m["totals"]["by_source_overlap"] == {
        "single_source": 6783,
        "two_sources": 890,
        "three_sources": 111,
    }
