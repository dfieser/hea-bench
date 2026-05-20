"""Tests for hea_bench.descriptors.entropy."""

import math

import pytest

from hea_bench.constants import R
from hea_bench.descriptors.entropy import smix


def test_smix_cantor_equimolar() -> None:
    """5-element equimolar → ΔS_mix = R·ln(5) ≈ 13.38 J/(mol·K)."""
    got = smix({"Co": 1, "Cr": 1, "Fe": 1, "Mn": 1, "Ni": 1})
    expected = R * math.log(5)
    assert got == pytest.approx(expected, rel=1e-12)


def test_smix_binary_equimolar() -> None:
    """50/50 binary → ΔS_mix = R·ln(2)."""
    got = smix({"A": 0.5, "B": 0.5})
    assert got == pytest.approx(R * math.log(2), rel=1e-12)


def test_smix_pure_element_is_zero() -> None:
    """Single component → entropy is exactly 0 (no mixing)."""
    assert smix({"Fe": 1.0}) == 0.0


def test_smix_normalization_is_internal() -> None:
    """Non-normalized inputs (e.g. Al0.3CoCrFeNi) must give the same answer
    as their normalized counterparts."""
    raw = {"Al": 0.3, "Co": 1, "Cr": 1, "Fe": 1, "Ni": 1}
    total = sum(raw.values())
    normalized = {k: v / total for k, v in raw.items()}
    assert smix(raw) == pytest.approx(smix(normalized), rel=1e-15)


def test_smix_rejects_zero_total() -> None:
    with pytest.raises(ValueError):
        smix({"Fe": 0})


def test_smix_rejects_empty() -> None:
    with pytest.raises(ValueError):
        smix({})
