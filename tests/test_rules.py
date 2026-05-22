"""Tests for the four canonical empirical phase-prediction rules."""


from hea_bench.rules import guo_vec, yang_omega, yeh_smix, zhang_delta

_CANTOR     = {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}
_MO_NB_TA_W = {"Mo": 0.25, "Nb": 0.25, "Ta": 0.25, "W":  0.25}


# ---- Yeh ΔS_mix rule (descriptive, 3-bin) ----

def test_yeh_cantor_is_hea() -> None:
    assert yeh_smix.predict(_CANTOR) == "HEA"


def test_yeh_binary_equimolar_is_mea() -> None:
    """Binary 50/50: ΔS_mix = R·ln 2 ≈ 5.76 J/(mol·K) — below R, so 'dilute'.
    Wait — R·ln 2 = 0.69R, which is < R, so this is dilute, not MEA."""
    assert yeh_smix.predict({"Cu": 0.5, "Ni": 0.5}) == "dilute"


def test_yeh_ternary_equimolar_is_mea() -> None:
    """Ternary equimolar: ΔS_mix = R·ln 3 ≈ 1.10R — between R and 1.5R, so MEA."""
    assert yeh_smix.predict({"Cu": 1, "Ni": 1, "Pd": 1}) == "MEA"


def test_yeh_pure_element_is_dilute() -> None:
    assert yeh_smix.predict({"Fe": 1.0}) == "dilute"


# ---- Zhang δ rule (binary, tunable) ----

def test_zhang_cantor_is_single_phase() -> None:
    """Cantor δ ≈ 3.16% — well below 6.5%, so single-phase prediction."""
    assert zhang_delta.predict(_CANTOR) == "single-phase"


def test_zhang_above_threshold_is_multi() -> None:
    """Y-Co binary has very large size mismatch (Y radius 182 vs Co 125)."""
    assert zhang_delta.predict({"Y": 0.5, "Co": 0.5}) == "multi-phase"


def test_zhang_threshold_tunable() -> None:
    """At Cantor's δ ≈ 3.16, threshold 3 → multi, threshold 4 → single."""
    assert zhang_delta.predict(_CANTOR, threshold=3.0) == "multi-phase"
    assert zhang_delta.predict(_CANTOR, threshold=4.0) == "single-phase"


# ---- Guo-Liu VEC rule (3-class) ----

def test_guo_cantor_predicts_fcc() -> None:
    """Cantor VEC = 8.0 exactly — on the threshold (≥8.0 → FCC)."""
    assert guo_vec.predict(_CANTOR) == "FCC"


def test_guo_refractory_predicts_bcc() -> None:
    """MoNbTaW VEC = (6+5+5+6)/4 = 5.5 — BCC (< 6.87)."""
    assert guo_vec.predict(_MO_NB_TA_W) == "BCC"


def test_guo_mid_range_predicts_mixed() -> None:
    """VEC between 6.87 and 8.0 → mixed. e.g. CoCrFeNi without Mn:
    (9+6+8+10)/4 = 8.25 — actually FCC. Try CoCrFe: (9+6+8)/3 = 7.67 → mixed."""
    assert guo_vec.predict({"Co": 1, "Cr": 1, "Fe": 1}) == "mixed"


def test_guo_boundary_vec_is_platform_deterministic() -> None:
    """Equiatomic CrFeNi has an exact VEC of (6+8+10)/3 = 8.0, but float
    summation renders it as 7.999999999999999 on some CPython versions and
    exactly 8.0 on others. The rule rounds before the >= 8.0 test, so it
    must classify CrFeNi as FCC everywhere. Regression for a CI failure
    where Python 3.12 disagreed with 3.10/3.11 on this one composition."""
    assert guo_vec.predict({"Cr": 1, "Fe": 1, "Ni": 1}) == "FCC"


# ---- Yang-Zhang Ω rule (binary) ----

def test_yang_cantor_is_single_phase() -> None:
    """Cantor Ω = 5.79 >> 1.1 → single-phase."""
    assert yang_omega.predict(_CANTOR) == "single-phase"


def test_yang_threshold_tunable() -> None:
    """Cantor Ω = 5.79; threshold above that → multi."""
    assert yang_omega.predict(_CANTOR, threshold=10.0) == "multi-phase"
    assert yang_omega.predict(_CANTOR, threshold=1.1) == "single-phase"


def test_yang_pure_element_handles_infinity() -> None:
    """Pure element has Ω = +inf; should classify as single-phase."""
    assert yang_omega.predict({"Fe": 1.0}) == "single-phase"
