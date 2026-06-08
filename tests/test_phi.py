"""Tests for the v1.1 phi-family descriptors.

The Cantor regression targets below are measured from the live code on
2026-05-24 and pinned. They are characterisations of what this
implementation produces given the matminer Miedema pair table and the
24-element radius/Tm table — not claims that any specific number
matches a value published by King 2016 or Ye 2015.
"""

import math

import pytest

from hea_bench.constants import PACKING_FRACTION_BCC, PACKING_FRACTION_FCC
from hea_bench.descriptors.entropy import smix
from hea_bench.descriptors.melting import melting_temperature
from hea_bench.descriptors.miedema import mixing_enthalpy
from hea_bench.descriptors.phi import (
    delta_g_max,
    delta_g_ss,
    delta_h_ss,
    phi_king,
    phi_ye,
    s_excess,
)

_CANTOR = {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}


def test_delta_h_ss_matches_miedema() -> None:
    assert delta_h_ss(_CANTOR) == mixing_enthalpy(_CANTOR)


def test_delta_h_ss_cantor_pinned() -> None:
    assert delta_h_ss(_CANTOR) == pytest.approx(-4.160, abs=5e-4)


def test_delta_g_ss_defaults_to_tm() -> None:
    expected = mixing_enthalpy(_CANTOR) - melting_temperature(_CANTOR) * smix(_CANTOR) / 1000.0
    assert delta_g_ss(_CANTOR) == pytest.approx(expected, rel=1e-15)


def test_delta_g_ss_cantor_pinned() -> None:
    assert delta_g_ss(_CANTOR) == pytest.approx(-28.2616, abs=5e-4)


def test_delta_g_max_is_negative_for_cantor() -> None:
    assert delta_g_max(_CANTOR) < 0


def test_delta_g_max_cantor_pinned() -> None:
    """Most negative Miedema pair enthalpy across all Cantor binaries.
    Cr-Ni at -8.0 kJ/mol is the strongest competitor in this set."""
    assert delta_g_max(_CANTOR) == pytest.approx(-8.0, abs=5e-4)


def test_s_excess_defaults_to_average_of_bcc_and_fcc() -> None:
    bcc = s_excess(_CANTOR, PACKING_FRACTION_BCC)
    fcc = s_excess(_CANTOR, PACKING_FRACTION_FCC)
    assert s_excess(_CANTOR) == pytest.approx((bcc + fcc) / 2.0, rel=1e-15)


def test_s_excess_cantor_pinned() -> None:
    assert s_excess(_CANTOR, PACKING_FRACTION_BCC) == pytest.approx(0.2476, abs=5e-4)
    assert s_excess(_CANTOR, PACKING_FRACTION_FCC) == pytest.approx(0.3883, abs=5e-4)
    assert s_excess(_CANTOR) == pytest.approx(0.3179, abs=5e-4)


def test_s_excess_pure_element_is_zero() -> None:
    assert s_excess({"Fe": 1.0}) == 0.0


def test_phi_king_defaults_to_tm() -> None:
    explicit = phi_king(_CANTOR, temperature=melting_temperature(_CANTOR))
    assert phi_king(_CANTOR) == pytest.approx(explicit, rel=1e-15)


def test_phi_king_cantor_pinned() -> None:
    assert phi_king(_CANTOR) == pytest.approx(3.5327, abs=5e-4)


def test_phi_king_is_finite_for_cantor() -> None:
    assert math.isfinite(phi_king(_CANTOR))


def test_phi_ye_cantor_pinned() -> None:
    assert phi_ye(_CANTOR) == pytest.approx(34.8219, abs=5e-4)


def test_phi_ye_is_finite_for_cantor() -> None:
    assert math.isfinite(phi_ye(_CANTOR))


def test_phi_missing_element_raises() -> None:
    with pytest.raises(ValueError, match="not in elemental data table"):
        phi_ye({"Fe": 0.5, "Xe": 0.5})