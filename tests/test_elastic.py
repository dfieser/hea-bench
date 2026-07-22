"""Tests for the Andreoli elastic-strain energy criterion (Materialia 5, 100222)."""

import pytest

from hea_bench.descriptors.elastic import _h_elastic_from_tables, h_elastic

CANTOR = {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}


def test_hand_computed_two_element_case() -> None:
    """B = (100, 200) GPa, V = (10, 8) cm3/mol, equiatomic.
    V_bar = (0.5*100*10 + 0.5*200*8) / (0.5*100 + 0.5*200) = 1300/150
    H_el  = 0.5*100*(10 - V_bar)^2/(2*10) + 0.5*200*(8 - V_bar)^2/(2*8)
          = 4.4444... + 2.7777... = 7.2222... kJ/mol
    (GPa * cm3/mol = kJ/mol exactly, no unit factor needed.)
    """
    got = _h_elastic_from_tables(
        {"A": 0.5, "B": 0.5}, {"A": 100.0, "B": 200.0}, {"A": 10.0, "B": 8.0}
    )
    assert got == pytest.approx(65.0 / 9.0, rel=1e-12)


def test_pure_element_is_zero() -> None:
    assert h_elastic({"Fe": 1.0}) == pytest.approx(0.0, abs=1e-12)


def test_cantor_lands_in_fcc_window() -> None:
    """Andreoli computes 2.98 kJ/mol for CoCrFeMnNi with their B/V
    sources; with the matminer-vendored moduli we must land in the
    same fcc-SS window (0..6.05 kJ/mol), not necessarily on their
    exact number."""
    got = h_elastic(CANTOR)
    assert got is not None
    assert 0.0 < got < 6.05


def test_bcc_refractory_lands_in_bcc_window() -> None:
    """HfNbTaTiZr: Andreoli prints 11.13 kJ/mol (bcc window 6.05..22)."""
    got = h_elastic({"Hf": 0.2, "Nb": 0.2, "Ta": 0.2, "Ti": 0.2, "Zr": 0.2})
    assert got is not None
    assert 6.05 < got < 22.0


def test_missing_mechanics_returns_none(monkeypatch) -> None:
    import hea_bench.descriptors.elastic as elastic_mod

    monkeypatch.setattr(elastic_mod, "mechanics", lambda sym: None)
    assert h_elastic(CANTOR) is None
