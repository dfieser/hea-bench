"""Tests for hea_bench.descriptors.miedema and .omega."""

import math

import pytest

from hea_bench.descriptors.miedema import mixing_enthalpy
from hea_bench.descriptors.omega import omega

# Canonical HEA compositions used as ground-truth probes.
_CANTOR     = {"Co": 0.2,  "Cr": 0.2,  "Fe": 0.2,  "Mn": 0.2,  "Ni": 0.2}
_MO_NB_TA_W = {"Mo": 0.25, "Nb": 0.25, "Ta": 0.25, "W":  0.25}
_CU_NI      = {"Cu": 0.5,  "Ni": 0.5}
_MO_NB      = {"Mo": 0.5,  "Nb": 0.5}


# ---- ΔH_mix (Miedema multi-component) ----
#
# Honesty note: the values pinned below are computed by our standard
# Miedema formula (ΔH_mix = Σ_{i<j} 4 c_i c_j ΔH^pair_{ij}) applied to
# the matminer-vendored Takeuchi-Inoue 2005 pair-enthalpy table. They
# are NOT the only published values for these alloys — different
# methods (e.g. Gao et al.'s sub-regular solution model on the same
# Takeuchi-Inoue base) yield slightly different aggregate values
# (e.g. Cantor at -3.75 vs our -4.16). These are method differences,
# not bugs. The tests pin the value our code actually produces; the
# value is consistent with the standard 4-c_i-c_j-prefactor convention
# in widespread HEA-literature use.

def test_hmix_cantor_canonical_value() -> None:
    """Cantor ΔH_mix from our Miedema formula on matminer Takeuchi-Inoue
    pair enthalpies. Independently verified by pair-by-pair walkthrough."""
    assert mixing_enthalpy(_CANTOR) == pytest.approx(-4.16, abs=0.01)


def test_hmix_refractory_monbtaw_canonical_value() -> None:
    """MoNbTaW refractory HEA via our Miedema formula on the same pair
    table. Cited as -6.5 kJ/mol in multiple HEA reviews; matches what
    our code produces."""
    assert mixing_enthalpy(_MO_NB_TA_W) == pytest.approx(-6.5, abs=0.01)


def test_hmix_cu_ni_binary_equals_pair_value() -> None:
    """At equimolar binary, the 4 c_A c_B prefactor reduces to 1.0
    so ΔH_mix equals the tabulated pair value (Cu-Ni = +4 kJ/mol)."""
    assert mixing_enthalpy(_CU_NI) == 4.0


def test_hmix_pure_element_is_zero() -> None:
    """Single component → no pair contributions → ΔH_mix = 0."""
    for sym in ("Fe", "Cr", "Co", "Al", "Mo", "W"):
        assert mixing_enthalpy({sym: 1.0}) == 0.0


def test_hmix_normalizes_proportional_input() -> None:
    """Same physical alloy expressed proportionally must yield the
    same ΔH_mix as the normalized version."""
    norm = mixing_enthalpy(_CANTOR)
    prop = mixing_enthalpy({"Co": 1, "Cr": 1, "Fe": 1, "Mn": 1, "Ni": 1})
    assert prop == pytest.approx(norm, rel=1e-12)


def test_hmix_missing_element_raises() -> None:
    with pytest.raises(ValueError, match="not in Miedema pair table"):
        mixing_enthalpy({"Fe": 0.5, "Xe": 0.5})


def test_hmix_empty_raises() -> None:
    with pytest.raises(ValueError):
        mixing_enthalpy({})


# ---- Ω (Yang–Zhang) ----

def test_omega_cantor_well_above_threshold() -> None:
    """Cantor is a canonical stable single-phase HEA; Ω must clearly
    exceed the Yang–Zhang 1.1 threshold."""
    assert omega(_CANTOR) == pytest.approx(5.79, abs=0.01)


def test_omega_refractory_above_threshold() -> None:
    """MoNbTaW is also a known single-phase BCC refractory HEA."""
    assert omega(_MO_NB_TA_W) == pytest.approx(5.60, abs=0.01)


def test_omega_cu_ni_above_threshold() -> None:
    """Cu-Ni has positive ΔH_mix but Ω still > 1.1 (entropy wins at T_m).
    Note: this is the kind of case where the Ω rule succeeds but
    the alloy in reality phase-separates at lower temperatures."""
    assert omega(_CU_NI) == pytest.approx(2.22, abs=0.01)


def test_omega_pure_element_is_infinite() -> None:
    """Pure element has ΔS_mix = 0 AND ΔH_mix = 0 → 0/0; our convention
    is +inf (ideal-mixing limit). Documented in the docstring."""
    assert math.isinf(omega({"Fe": 1.0}))
    assert omega({"Fe": 1.0}) > 0


def test_omega_normalizes_proportional_input() -> None:
    norm = omega(_CANTOR)
    prop = omega({"Co": 1, "Cr": 1, "Fe": 1, "Mn": 1, "Ni": 1})
    assert prop == pytest.approx(norm, rel=1e-12)


def test_omega_missing_element_raises() -> None:
    """Propagated from the underlying descriptors."""
    with pytest.raises(ValueError):
        omega({"Fe": 0.5, "Xe": 0.5})


# ---- Cross-consistency between descriptors ----

def test_omega_decomposition_matches_inputs() -> None:
    """Sanity-check Ω = T_m · ΔS_mix / |ΔH_mix·1000| against the
    pieces computed individually."""
    from hea_bench.descriptors.entropy import smix
    from hea_bench.descriptors.melting import melting_temperature

    tm = melting_temperature(_CANTOR)
    s = smix(_CANTOR)
    h = mixing_enthalpy(_CANTOR)
    expected = tm * s / (abs(h) * 1000.0)
    assert omega(_CANTOR) == pytest.approx(expected, rel=1e-15)
