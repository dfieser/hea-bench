"""Tests for the Senkov-Miracle kappa criterion and the Tsai sigma /
Sheikh ductility VEC windows."""

import pytest

from hea_bench.rules import senkov_kappa, sheikh_ductility, tsai_sigma

CANTOR = {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}


# ---- kappa (Senkov & Miracle, J. Alloys Compd. 658 (2016) 603) ----

def test_kappa_hand_case_im_favored(monkeypatch) -> None:
    """dH_ss = -10, dH_IM = -20 kJ/mol, S = 13.38 J/(mol K), T = 1000 K.
    k1 = 2.0;  k1_cr = 1 + 0.4*1000*13.38/(1000*10) = 1.5352  -> IM.
    Direct Gibbs check: G_ss = -23.38, G_im = -28.028 kJ/mol -> IM."""
    monkeypatch.setattr(senkov_kappa, "mixing_enthalpy", lambda c: -10.0)
    monkeypatch.setattr(senkov_kappa, "delta_g_max", lambda c: -20.0)
    monkeypatch.setattr(senkov_kappa, "smix", lambda c: 13.38)
    got = senkov_kappa.predict(CANTOR, temperature=1000.0)
    assert got.k1 == pytest.approx(2.0, rel=1e-12)
    assert got.k1_cr == pytest.approx(1.5352, rel=1e-4)
    assert got.g_ss_kj == pytest.approx(-23.38, rel=1e-12)
    assert got.g_im_kj == pytest.approx(-28.028, rel=1e-12)
    assert got.ss_favored is False
    assert got.verdict == "intermetallic"


def test_kappa_hand_case_ss_favored_at_higher_t(monkeypatch) -> None:
    """Same alloy at T = 3000 K: k1_cr = 1 + 0.4*3000*13.38/(1000*10)
    = 2.6056 > k1 = 2.0 -> SS; Gibbs check agrees."""
    monkeypatch.setattr(senkov_kappa, "mixing_enthalpy", lambda c: -10.0)
    monkeypatch.setattr(senkov_kappa, "delta_g_max", lambda c: -20.0)
    monkeypatch.setattr(senkov_kappa, "smix", lambda c: 13.38)
    got = senkov_kappa.predict(CANTOR, temperature=3000.0)
    assert got.k1_cr == pytest.approx(2.6056, rel=1e-4)
    assert got.ss_favored is True
    assert got.verdict == "solid_solution"


def test_kappa_positive_h_ss_defined_by_gibbs_only(monkeypatch) -> None:
    """When dH_ss >= 0 the k1 parameterization is undefined (division
    by a non-negative enthalpy flips the inequality); the verdict must
    come from the direct Gibbs comparison and k1/k1_cr must be None."""
    monkeypatch.setattr(senkov_kappa, "mixing_enthalpy", lambda c: 2.0)
    monkeypatch.setattr(senkov_kappa, "delta_g_max", lambda c: -20.0)
    monkeypatch.setattr(senkov_kappa, "smix", lambda c: 13.38)
    got = senkov_kappa.predict(CANTOR, temperature=1000.0)
    assert got.k1 is None and got.k1_cr is None
    # G_ss = 2 - 13.38 = -11.38; G_im = -20 - 0.6*13.38 = -28.028 -> IM
    assert got.ss_favored is False


def test_kappa_no_stable_compound_is_trivially_ss(monkeypatch) -> None:
    """dH_IM >= 0 means no binary wants to form a compound at all."""
    monkeypatch.setattr(senkov_kappa, "mixing_enthalpy", lambda c: -1.0)
    monkeypatch.setattr(senkov_kappa, "delta_g_max", lambda c: 4.0)
    monkeypatch.setattr(senkov_kappa, "smix", lambda c: 13.38)
    got = senkov_kappa.predict(CANTOR, temperature=1000.0)
    assert got.ss_favored is True


def test_kappa_cantor_at_1000k_is_ss() -> None:
    """Real-table regression: the Cantor alloy anneal-stabilizes as SS."""
    got = senkov_kappa.predict(CANTOR, temperature=1000.0)
    assert got.ss_favored is True
    assert got.temperature_K == 1000.0


def test_kappa_default_temperature_is_melting() -> None:
    from hea_bench.descriptors.melting import melting_temperature

    got = senkov_kappa.predict(CANTOR)
    assert got.temperature_K == pytest.approx(melting_temperature(CANTOR))


# ---- Tsai sigma window (Mater. Res. Lett. 1 (2013) 207) ----

def test_sigma_alcocrfeni_flagged() -> None:
    """AlCoCrFeNi: VEC = (3+9+6+8+10)/5 = 7.2, contains Cr, inside
    6.88..7.84 -> sigma-prone."""
    got = tsai_sigma.predict({"Al": 0.2, "Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Ni": 0.2})
    assert got.applies is True
    assert got.in_window is True
    assert got.vec == pytest.approx(7.2)
    assert got.verdict == "sigma_prone"


def test_sigma_cantor_outside_window() -> None:
    got = tsai_sigma.predict(CANTOR)  # VEC 8.0, has Cr
    assert got.applies is True
    assert got.in_window is False
    assert got.verdict == "sigma_unlikely"


def test_sigma_rule_does_not_apply_without_cr_or_v() -> None:
    got = tsai_sigma.predict({"Cu": 0.5, "Ni": 0.5})
    assert got.applies is False
    assert got.verdict == "not_applicable"


# ---- Sheikh ductility (J. Appl. Phys. 120 (2016) 164902) ----

def test_ductility_hfnbtatizr_ductile() -> None:
    got = sheikh_ductility.predict({"Hf": 0.2, "Nb": 0.2, "Ta": 0.2, "Ti": 0.2, "Zr": 0.2})
    assert got.vec == pytest.approx(4.4)
    assert got.verdict == "ductile"


def test_ductility_monbtaw_brittle() -> None:
    got = sheikh_ductility.predict({"Mo": 0.25, "Nb": 0.25, "Ta": 0.25, "W": 0.25})
    assert got.vec == pytest.approx(5.5)
    assert got.verdict == "brittle"


def test_ductility_borderline_band() -> None:
    # Ti0.5V0.5: VEC = 4.5 exactly -> borderline (4.5 <= VEC < 4.6)
    got = sheikh_ductility.predict({"Ti": 0.5, "V": 0.5})
    assert got.vec == pytest.approx(4.5)
    assert got.verdict == "borderline"
