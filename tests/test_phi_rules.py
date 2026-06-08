"""Tests for the v1.1 phi-family rule wrappers."""

from hea_bench.descriptors.phi import phi_king, phi_ye
from hea_bench.rules import king_phi, ye_phi

_CANTOR = {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}


def test_king_phi_rule_defaults_to_solid_solution_for_pure_element() -> None:
    assert king_phi.predict({"Fe": 1.0}) == "solid_solution"


def test_king_phi_rule_matches_descriptor_thresholding() -> None:
    value = phi_king(_CANTOR)
    expected = "solid_solution" if value > king_phi.DEFAULT_THRESHOLD else "intermetallic"
    assert king_phi.predict(_CANTOR) == expected


def test_king_phi_rule_temperature_override_changes_verdict() -> None:
    # At T = T_m the Cantor alloy is comfortably above the rule's
    # default threshold; cooling the alloy enough makes the entropic
    # term in ΔG_ss small enough that the rule flips to intermetallic.
    assert king_phi.predict(_CANTOR, temperature_policy=200.0) == "intermetallic"
    assert king_phi.predict(_CANTOR, temperature_policy=2000.0) == "solid_solution"


def test_king_phi_rule_threshold_is_tunable() -> None:
    value = phi_king(_CANTOR)
    assert king_phi.predict(_CANTOR, threshold=value + 1.0) == "intermetallic"
    assert king_phi.predict(_CANTOR, threshold=value - 1.0) == "solid_solution"


def test_ye_phi_rule_defaults_to_solid_solution_for_pure_element() -> None:
    assert ye_phi.predict({"Fe": 1.0}) == "solid_solution"


def test_ye_phi_rule_matches_descriptor_thresholding() -> None:
    value = phi_ye(_CANTOR)
    expected = "solid_solution" if value > ye_phi.DEFAULT_THRESHOLD else "intermetallic"
    assert ye_phi.predict(_CANTOR) == expected


def test_ye_phi_rule_threshold_is_tunable() -> None:
    value = phi_ye(_CANTOR)
    assert ye_phi.predict(_CANTOR, threshold=value + 1.0) == "intermetallic"
    assert ye_phi.predict(_CANTOR, threshold=value - 1.0) == "solid_solution"