"""Tests for hea_bench.benchmark.coverage."""

import pathlib

import pytest

from hea_bench.benchmark import coverage

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
V010_CSV = REPO_ROOT / "data" / "consolidated" / "v0.1.0" / "consolidated.csv"


# ---- Unit test against a tiny synthetic CSV ----

def test_analyze_on_synthetic_csv(tmp_path: pathlib.Path) -> None:
    """Three compositions: one fully covered, one missing from
    ELEMENTAL_DATA but in pair table, one missing from both.

    He and Ne are used for the third row because they are valid
    periodic-table symbols (so the formula parser accepts them) but
    are absent from both the elemental data table and the metallic
    Miedema pair table, which is exactly the case the coverage
    analyser must classify as ``in_neither``.

    Ga-Nd is the in-pair-table-but-not-in-ELEMENTAL_DATA row: both are
    in the matminer Miedema pair table but neither is in the
    37-element property table.
    """
    csv_path = tmp_path / "synthetic.csv"
    csv_path.write_text(
        "composition_key,n_elements,sources,canonical_phase,has_conflict,"
        "borg_label,pei_label,peivaste_label,borg_raw_label,pei_raw_label,"
        "peivaste_raw_label,borg_processing,borg_doi,source_row_ids\n"
        "Co0.2000Cr0.2000Fe0.2000Mn0.2000Ni0.2000,5,test,FCC,0,,,,,,,,,test:1\n"
        "Ga0.5000Nd0.5000,2,test,multi-phase,0,,,,,,,,,test:2\n"
        "He0.5000Ne0.5000,2,test,multi-phase,0,,,,,,,,,test:3\n",
        encoding="utf-8",
    )
    r = coverage.analyze(csv_path)
    assert r["total"] == 3
    assert r["in_basic"] == 1      # only Cantor
    assert r["in_miedema"] == 2    # Cantor and Be-Ca (both in matminer pair table)
    assert r["in_both"] == 1       # just Cantor
    assert r["in_neither"] == 1    # He-Ne (real elements, in neither HEA table)


# ---- Integration test against the v0.1.0 release ----

pytestmark_v010 = pytest.mark.skipif(
    not V010_CSV.exists(),
    reason=f"v0.1.0 CSV not present at {V010_CSV}",
)


@pytestmark_v010
def test_v010_overall_coverage_pinned() -> None:
    """Headline coverage numbers for the paper. Pinned for the v1.3
    37-element table (Be, Ca, Ce, Gd, In, La, Sc added to the v1.2
    30-element set) to catch any drift in either ELEMENTAL_DATA or
    the vendored Miedema pair table."""
    r = coverage.analyze(V010_CSV)
    assert r["total"] == 7784
    assert r["in_basic"] == 7227       # 92.8% with the 37-element table
    assert r["in_miedema"] == 7752     # 99.6% with vendored pair table
    assert r["in_both"] == 7227
    assert r["in_neither"] == 32       # 0.4% completely unscorable


@pytestmark_v010
def test_v010_top_missing_element_is_carbon() -> None:
    """With Mg now in the table, the largest remaining single coverage
    gap is carbon (98 alloys). C is deliberately not added: it has no
    1-atm melting point and no metallic radius (see elemental.py). The
    top missing elements are all in the pair table already, so any
    future expansion is just sourcing per-element scalars."""
    r = coverage.analyze(V010_CSV)
    top = sorted(r["missing_from_basic"].items(), key=lambda kv: -kv[1])
    assert top[0] == ("C", 98)


@pytestmark_v010
def test_v010_all_top_gaps_already_in_pair_table() -> None:
    """The first 10 elements in the next-best-add ranking should all
    be flagged YES (already in the pair table) — meaning expanding
    ELEMENTAL_DATA is just sourcing atomic radii."""
    r = coverage.analyze(V010_CSV)
    for el, _cnt, in_pair_table in r["next_best_adds"][:10]:
        assert in_pair_table is True, f"{el} unexpectedly outside pair table"


# ---- Report formatting ----

def test_format_report_contains_key_sections() -> None:
    report = {
        "csv_path": "fake.csv",
        "total": 100,
        "in_basic": 80,
        "in_miedema": 95,
        "in_both": 78,
        "in_neither": 3,
        "missing_from_basic": {"Mg": 10, "B": 5},
        "missing_from_miedema": {"Xx": 5},
        "next_best_adds": [("Mg", 10, True), ("B", 5, True)],
    }
    text = coverage.format_report(report)
    assert "Coverage report" in text
    assert "ELEMENTAL_DATA" in text
    assert "Miedema pair table" in text
    assert "Mg" in text and "10" in text
