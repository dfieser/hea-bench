"""Regression tests for the browser-compatible descriptor helpers."""

import math

import pytest

from hea_bench import browser_mixing_enthalpy, browser_omega
from hea_bench.descriptors.browser_compat import browser_pair_enthalpy


_CANTOR = {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}
_CU_NI = {"Cu": 0.5, "Ni": 0.5}
_EXAMPLE = {"Cu": 0.2, "Co": 0.2, "Mn": 0.35, "Ni": 0.2, "Fe": 0.05}


def test_browser_mixing_enthalpy_example_matches_calculator() -> None:
    assert browser_mixing_enthalpy(_EXAMPLE) == pytest.approx(
        -2.7705212729265263, rel=1e-12
    )


def test_browser_omega_example_matches_calculator() -> None:
    assert browser_omega(_EXAMPLE) == pytest.approx(7.088589944660232, rel=1e-12)


def test_browser_cantor_matches_legacy_calculator_path() -> None:
    assert browser_mixing_enthalpy(_CANTOR) == pytest.approx(
        -16.661502045296054, rel=1e-12
    )
    assert browser_omega(_CANTOR) == pytest.approx(1.4465452887621288, rel=1e-12)


def test_browser_binary_reduces_to_pair_enthalpy() -> None:
    assert browser_mixing_enthalpy(_CU_NI) == pytest.approx(
        browser_pair_enthalpy("Cu", "Ni"), rel=1e-12
    )


def test_browser_pure_element_is_zero_and_infinite() -> None:
    assert browser_mixing_enthalpy({"Fe": 1.0}) == 0.0
    assert math.isinf(browser_omega({"Fe": 1.0}))


def test_browser_missing_element_raises() -> None:
    with pytest.raises(ValueError, match="browser Miedema calculator data"):
        browser_mixing_enthalpy({"Fe": 0.5, "Xe": 0.5})