"""Tests for the high-entropy-oxide descriptor module.

The pinned numbers fall into two classes:

- Literature anchors, asserted against the published values: the
  Spiridigliozzi F-ESO sample SDs (Materials 16, 2219, 2023, Table 1),
  the Jiang 2018 Sr(Zr,Sn,Ti,Hf,Mn)O3 tolerance-factor cluster, and
  the J14 rock-salt entropy R ln 5.
- Regression pins, derived from the vendored Shannon table at first
  implementation. A changed value means the data or the math drifted;
  explain it, do not silence it.
"""

from __future__ import annotations

import math

import pytest

from hea_bench import oxides

J14 = {"Mg": 1, "Co": 1, "Ni": 1, "Cu": 1, "Zn": 1}
R = oxides.R_GAS


# ---------------------------------------------------------------- radii

def test_shannon_radius_exact_values():
    assert oxides.shannon_radius("Co", 2, 6)[0] == pytest.approx(0.745)
    assert oxides.shannon_radius("Co", 2, 6, spin="low")[0] == pytest.approx(0.65)
    assert oxides.shannon_radius("Sr", 2, 12)[0] == pytest.approx(1.44)
    assert oxides.shannon_radius("O", -2, 6)[0] == pytest.approx(1.40)


def test_shannon_radius_cn_fallback_warns():
    radius, warnings = oxides.shannon_radius("Mn", 4, 12)
    assert radius == pytest.approx(0.53)  # nearest tabulated is CN=6
    assert any("CN=12" in w and "CN=6" in w for w in warnings)


def test_shannon_radius_unknown_state_raises():
    with pytest.raises(ValueError, match="oxidation state"):
        oxides.shannon_radius("Mg", 3, 6)


# --------------------------------------------------------------- solver

def test_solver_j14_all_divalent():
    states, warnings = oxides.assign_oxidation_states(
        {el: 0.2 for el in J14}, target_charge=2.0
    )
    assert states == {"Mg": 2, "Co": 2, "Ni": 2, "Cu": 2, "Zn": 2}
    assert warnings == []


def test_solver_prefers_uniform_sublattices():
    # (La,Ce,Nd,Sm,Eu)2Zr2O7: Ce4+/Eu2+ also balances, but the uniform
    # all-3+ A site must win the tie-break.
    moles = {el: 0.4 for el in ("La", "Ce", "Nd", "Sm", "Eu")}
    moles["Zr"] = 2.0
    groups = {el: "A" for el in ("La", "Ce", "Nd", "Sm", "Eu")}
    groups["Zr"] = "B"
    states, _ = oxides.assign_oxidation_states(moles, 14.0, groups=groups)
    assert states == {"La": 3, "Ce": 3, "Nd": 3, "Sm": 3, "Eu": 3, "Zr": 4}


def test_solver_unreachable_charge_raises():
    with pytest.raises(ValueError, match="closest achievable"):
        oxides.assign_oxidation_states({"La": 1.0}, target_charge=2.0)


def test_solver_allowed_pins_states():
    states, _ = oxides.assign_oxidation_states(
        {"Ce": 0.5, "Zr": 0.5}, 3.5, allowed={"Ce": [3]}
    )
    assert states == {"Ce": 3, "Zr": 4}


# ------------------------------------------------------ rock salt (J14)

def test_j14_rock_salt_report():
    r = oxides.describe_rock_salt(J14)
    d = r["descriptors"]
    assert d["s_config"] == pytest.approx(R * math.log(5), rel=1e-9)
    assert d["delta_r"] == pytest.approx(2.688771, rel=1e-5)  # regression pin
    assert d["mean_chi"] == pytest.approx(1.73, rel=1e-6)
    assert d["delta_chi"] == pytest.approx(0.230911, rel=1e-5)
    assert r["verdicts"]["entropy"] == "high-entropy"
    assert r["oxidation_states"]["Cu"] == 2
    assert r["warnings"] == []


# ------------------------------------------------- perovskite (Jiang 2018)

def test_jiang_perovskite_anchor():
    r = oxides.describe_perovskite(
        {"Sr": 1}, {"Zr": 1, "Sn": 1, "Ti": 1, "Hf": 1, "Mn": 1}
    )
    d = r["descriptors"]
    # Jiang et al. 2018 report t ~ 0.98-1.02 for their single-phase set.
    assert d["goldschmidt_t"] == pytest.approx(0.979124, rel=1e-5)
    assert d["octahedral_mu"] == pytest.approx(0.465, rel=1e-5)
    assert d["bartel_tau"] == pytest.approx(3.72306, rel=1e-5)
    assert r["oxidation_states"] == {"Sr": 2, "Zr": 4, "Sn": 4, "Ti": 4, "Hf": 4, "Mn": 4}
    assert r["verdicts"]["goldschmidt"] == "within-window"
    assert r["verdicts"]["octahedral"] == "within-window"
    assert r["verdicts"]["bartel"] == "perovskite"
    # high entropy on the B sublattice (1.61 R) even though per total
    # cation site the value is half that — the HEO convention.
    assert r["verdicts"]["entropy"] == "high-entropy"
    assert d["s_config_per_site"]["B"] == pytest.approx(R * math.log(5), rel=1e-9)
    assert d["s_config_per_cation"] == pytest.approx(R * math.log(5) / 2, rel=1e-9)


def test_perovskite_shared_element_raises():
    with pytest.raises(ValueError, match="both sublattices"):
        oxides.describe_perovskite({"La": 1}, {"La": 1, "Mn": 1})


def test_bartel_tau_requires_larger_a():
    with pytest.raises(ValueError, match="rA > rB"):
        oxides.bartel_tau(0.6, 0.9, 2.0)


# --------------------------------------- fluorite (Spiridigliozzi F-ESO)

def test_spiridigliozzi_low_sd_sample():
    # (Ce,Zr,Nd,Y,Er)O1.7, published SD = 0.0976 A (Materials 16, 2219).
    r = oxides.describe_fluorite(
        {"Ce": 1, "Zr": 1, "Nd": 1, "Y": 1, "Er": 1}, oxygen=1.7
    )
    assert r["oxidation_states"] == {"Ce": 4, "Zr": 4, "Nd": 3, "Y": 3, "Er": 3}
    assert r["descriptors"]["radius_sigma"] == pytest.approx(0.0976, abs=5e-5)
    assert r["verdicts"]["spiridigliozzi"] == "fluorite"


def test_spiridigliozzi_high_sd_sample():
    # (Ce,Zr,La,Nd,Sm)O1.7, published SD = 0.128 A.
    r = oxides.describe_fluorite(
        {"Ce": 1, "Zr": 1, "La": 1, "Nd": 1, "Sm": 1}, oxygen=1.7
    )
    assert r["descriptors"]["radius_sigma"] == pytest.approx(0.128, abs=5e-4)
    assert r["verdicts"]["spiridigliozzi"] == "fluorite"


def test_fluorite_below_threshold_is_not_fluorite():
    # (Ce,Zr,Hf,Sn,Ti)O2 (Chen et al. 2018): entropy-stabilized only at
    # high temperature; sigma sits below the 0.095 A threshold.
    r = oxides.describe_fluorite({"Ce": 1, "Zr": 1, "Hf": 1, "Sn": 1, "Ti": 1})
    assert r["descriptors"]["radius_sigma"] == pytest.approx(0.0835, abs=5e-4)
    assert r["verdicts"]["spiridigliozzi"] == "bixbyite-or-multiphase"


def test_fluorite_non_equimolar_warns():
    r = oxides.describe_fluorite({"Ce": 3, "Zr": 1}, oxygen=2.0)
    assert any("equimolar" in w for w in r["warnings"])


# ------------------------------------------------------------ pyrochlore

def test_pyrochlore_zirconate_anchor():
    r = oxides.describe_pyrochlore(
        {"La": 1, "Ce": 1, "Nd": 1, "Sm": 1, "Eu": 1}, {"Zr": 1}
    )
    assert r["descriptors"]["radius_ratio"] == pytest.approx(1.543611, rel=1e-5)
    assert r["verdicts"]["radius_ratio"] == "pyrochlore"
    assert r["verdicts"]["entropy"] == "high-entropy"
    assert r["oxidation_states"]["Eu"] == 3


def test_pyrochlore_ratio_windows():
    assert oxides.radius_ratio(1.0, 0.72) < 1.46  # defect-fluorite side
    # A small A cation drops the verdict out of the pyrochlore window.
    r = oxides.describe_pyrochlore({"Y": 1}, {"Zr": 1})
    assert r["verdicts"]["radius_ratio"] == "defect-fluorite"


# ------------------------------------------------------ descriptor units

def test_size_disorder_matches_alloy_convention():
    # Equal radii -> zero; result is in percent.
    assert oxides.size_disorder({"A": 1, "B": 1}, {"A": 1.0, "B": 1.0}) == 0.0
    delta = oxides.size_disorder({"A": 1, "B": 1}, {"A": 1.0, "B": 1.1})
    assert 0.0 < delta < 10.0


def test_sublattice_entropy_per_conventions():
    subl = {"A": {"La": 0.5, "Y": 0.5}, "B": {"Zr": 1.0}}
    mult = {"A": 2.0, "B": 2.0}
    s_formula = oxides.sublattice_entropy(subl, mult)
    assert s_formula == pytest.approx(2.0 * R * math.log(2), rel=1e-9)
    s_cation = oxides.sublattice_entropy(subl, mult, per="cation")
    assert s_cation == pytest.approx(s_formula / 4.0, rel=1e-9)
