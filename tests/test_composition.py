"""Tests for hea_bench.benchmark.composition."""

import pytest

from hea_bench.benchmark.composition import (
    from_element_columns,
    normalize,
    parse_formula,
)


def test_parse_unit_amounts_cantor() -> None:
    """Each Cantor element gets equal 0.2 fraction."""
    got = parse_formula("CoCrFeMnNi")
    assert got == {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}


def test_parse_borg_style_with_spaces() -> None:
    """Borg's 'Al0.25 Co1 Fe1 Ni1' parses to proportional amounts then normalizes."""
    got = parse_formula("Al0.25 Co1 Fe1 Ni1")
    # 0.25 + 1 + 1 + 1 = 3.25 total
    assert got["Al"] == pytest.approx(0.25 / 3.25, rel=1e-12)
    assert got["Co"] == pytest.approx(1.0 / 3.25, rel=1e-12)
    assert sum(got.values()) == pytest.approx(1.0, abs=1e-12)


def test_parse_pei_style_no_spaces() -> None:
    """Pei's 'Al0.15Cr0.85' parses with already-summing-to-1 fractions."""
    got = parse_formula("Al0.15Cr0.85")
    assert got == pytest.approx({"Al": 0.15, "Cr": 0.85}, rel=1e-12)


def test_parse_mixed_implicit_explicit_coefficients() -> None:
    """Mix of implicit (=1) and explicit coefficients."""
    got = parse_formula("AlCoCrCu0.5Fe")
    # totals: 1+1+1+0.5+1 = 4.5
    assert got["Al"] == pytest.approx(1 / 4.5, rel=1e-12)
    assert got["Cu"] == pytest.approx(0.5 / 4.5, rel=1e-12)
    assert sum(got.values()) == pytest.approx(1.0, abs=1e-12)


def test_parse_duplicate_element_accumulates() -> None:
    """If the same element appears twice in a formula, sum the amounts."""
    got = parse_formula("Fe1Co1Fe1")
    assert got == pytest.approx({"Fe": 2 / 3, "Co": 1 / 3}, rel=1e-12)


def test_parse_rejects_empty() -> None:
    with pytest.raises(ValueError):
        parse_formula("")


def test_parse_rejects_no_elements() -> None:
    with pytest.raises(ValueError):
        parse_formula("12345")


def test_normalize_skips_zero_elements() -> None:
    got = normalize({"Fe": 1.0, "Co": 0.0, "Ni": 1.0})
    assert got == {"Fe": 0.5, "Ni": 0.5}


def test_normalize_rejects_all_zero() -> None:
    with pytest.raises(ValueError):
        normalize({"Fe": 0.0, "Co": 0.0})


def test_from_element_columns_basic() -> None:
    """Peivaste-style parsing: each element is its own column."""
    row = {"Al": "0.0", "Co": "0.2", "Cr": "0.2", "Fe": "0.2", "Mn": "0.2", "Ni": "0.2"}
    got = from_element_columns(row, ["Al", "Co", "Cr", "Fe", "Mn", "Ni"])
    assert got == {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}


def test_from_element_columns_ignores_missing_and_nonnumeric() -> None:
    row = {"Fe": "0.5", "Co": "0.5", "Ni": "", "Cr": "n/a"}
    got = from_element_columns(row, ["Fe", "Co", "Ni", "Cr", "Mn"])
    assert got == {"Fe": 0.5, "Co": 0.5}
