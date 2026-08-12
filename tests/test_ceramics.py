"""Tests for the high-entropy ceramics descriptors."""

import pytest

from hea_bench.ceramics import (
    describe_diboride,
    describe_rock_salt_carbide,
    describe_rock_salt_nitride,
)

FIVE = {"Ti": 1, "Zr": 1, "Hf": 1, "Nb": 1, "Ta": 1}
R = 8.314462618


def test_carbide_entropy_reports_all_three_normalizations() -> None:
    report = describe_rock_salt_carbide(FIVE)
    entropy = report["entropy"]
    assert entropy["per_mole_cation_r_units"] == pytest.approx(1.6094, abs=1e-3)
    assert entropy["per_mole_cation_j_mol_k"] == pytest.approx(R * 1.6094, abs=1e-2)
    # Rock salt has one anion per cation: per mole of atoms is half.
    assert entropy["per_mole_atoms_j_mol_k"] == pytest.approx(R * 1.6094 / 2, abs=1e-2)
    assert "normalization" in entropy["note"] or "convention" in entropy["note"]


def test_diboride_entropy_divides_by_three_atoms() -> None:
    report = describe_diboride(FIVE)
    entropy = report["entropy"]
    assert entropy["per_mole_atoms_j_mol_k"] == pytest.approx(R * 1.6094 / 3, abs=1e-2)


def test_carbide_vec_matches_the_published_anchors() -> None:
    """(TiZrHfNbTa)C is the literature's 8.4; (VNbTaMoW)C its 9.4."""
    low = describe_rock_salt_carbide(FIVE)
    assert low["vec_per_formula_unit"] == pytest.approx(8.4)
    high = describe_rock_salt_carbide({"V": 1, "Nb": 1, "Ta": 1, "Mo": 1, "W": 1})
    assert high["vec_per_formula_unit"] == pytest.approx(9.4)


def test_nitride_vec_adds_five_anion_electrons() -> None:
    report = describe_rock_salt_nitride(FIVE)
    assert report["vec_per_formula_unit"] == pytest.approx(9.4)


def test_reference_points_are_annotations_not_verdicts() -> None:
    report = describe_rock_salt_carbide(FIVE)
    assert "verdicts" not in report
    points = report["vec_reference_points"]
    assert any("Jhi" in point["source"] for point in points)
    assert all("value" in point and "marks" in point for point in points)


def test_size_mismatch_is_explicitly_deferred() -> None:
    report = describe_rock_salt_carbide(FIVE)
    assert "size_mismatch" not in report
    assert any("mismatch" in note for note in report["notes"])


def test_uncovered_metal_degrades_typed() -> None:
    report = describe_rock_salt_carbide({"Ti": 1, "Fr": 1})
    assert report["vec_per_formula_unit"] is None
    assert any("Fr" in warning for warning in report["warnings"])


def test_metals_normalize_and_count() -> None:
    report = describe_diboride({"Ti": 2, "Zr": 2})
    assert report["metals"] == {"Ti": 0.5, "Zr": 0.5}
    assert report["n_metals"] == 2


def test_sources_carry_citations() -> None:
    report = describe_rock_salt_carbide(FIVE)
    assert any("Sangiovanni" in source for source in report["sources"].values())
    assert any("Oses" in source for source in report["sources"].values())
