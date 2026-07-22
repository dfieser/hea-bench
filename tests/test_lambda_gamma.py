"""Tests for the Singh Lambda and Wang gamma geometric descriptors."""

import math

import pytest

from hea_bench.descriptors.gamma import _gamma_from_radii, wang_gamma
from hea_bench.descriptors.lam import singh_lambda
from hea_bench.descriptors.entropy import smix
from hea_bench.descriptors.size import delta

CANTOR = {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}


# ---- Lambda (Singh et al. 2014) ----

def test_lambda_is_smix_over_delta_squared() -> None:
    """Structural identity: Lambda = S_mix / delta^2 with delta in %."""
    lam = singh_lambda(CANTOR)
    assert lam == pytest.approx(smix(CANTOR) / delta(CANTOR) ** 2, rel=1e-12)


def test_lambda_cantor_is_single_ss_band() -> None:
    """Cantor is the canonical single-phase SS; Singh's window is
    Lambda > 0.96 (Intermetallics 53 (2014) 112, Fig. 2)."""
    lam = singh_lambda(CANTOR)
    assert lam > 0.96
    # regression pin: 13.3809 / 3.1641^2 with our radii/entropy
    assert lam == pytest.approx(1.3365, abs=2e-4)


def test_lambda_zero_mismatch_is_documented_infinity() -> None:
    """Ag-Au share radius 144.0 pm exactly, so delta = 0 and Lambda is
    unbounded; the documented convention is math.inf."""
    assert singh_lambda({"Ag": 0.5, "Au": 0.5}) == math.inf


# ---- gamma (Wang et al. 2015) ----

def test_gamma_equal_radii_is_exactly_one() -> None:
    assert wang_gamma({"Ag": 0.5, "Au": 0.5}) == pytest.approx(1.0, rel=1e-12)


def test_gamma_hand_computed_two_element_case() -> None:
    """r = (100, 200) pm equiatomic: r_bar = 150.
    omega_S = 1 - sqrt(((100+150)^2 - 150^2)/(100+150)^2) = 0.2
    omega_L = 1 - sqrt(((200+150)^2 - 150^2)/(200+150)^2)
            = 1 - sqrt(100000/122500)
    gamma = omega_S / omega_L
    """
    omega_l = 1.0 - math.sqrt(100000.0 / 122500.0)
    expected = 0.2 / omega_l
    got = _gamma_from_radii({"A": 0.5, "B": 0.5}, {"A": 100.0, "B": 200.0})
    assert got == pytest.approx(expected, rel=1e-12)
    assert got == pytest.approx(2.0727, abs=2e-4)


def test_gamma_cantor_below_threshold() -> None:
    """Cantor's tight radius spread must land well below Wang's 1.175
    solid-solution ceiling (Scripta Mater. 94 (2015) 28)."""
    g = wang_gamma(CANTOR)
    assert 1.0 < g < 1.175


def test_gamma_large_mismatch_exceeds_threshold() -> None:
    """SrCaYbMgZn (the HE-BMG) mixes 215 pm Sr with 137 pm Zn; the
    packing ratio must land above the crystalline-SS ceiling."""
    g = wang_gamma({"Sr": 0.2, "Ca": 0.2, "Yb": 0.2, "Mg": 0.2, "Zn": 0.2})
    assert g > 1.175
