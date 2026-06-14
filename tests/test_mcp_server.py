"""Tests for the MCP tool surface (hea_bench.mcp_server).

The tool bodies are plain functions, so these tests run without the
optional ``mcp`` package installed. Values are pinned against the same
literature anchors as the rest of the suite, including the
Omega-sensitivity numbers for the near-ideal alloy
Co20Cu20Fe5Mn35Ni20.
"""

import math

import pytest

import hea_bench as hb
from hea_bench.mcp_server import (
    SOURCES,
    about,
    alloy_descriptors,
    alloy_rules,
    element_coverage,
    omega_sensitivity,
    oxide_report,
    parse_composition,
)

CANTOR = "CoCrFeMnNi"
NEAR_IDEAL = "Co20Cu20Fe5Mn35Ni20"


def test_parse_composition_normalizes_and_stamps():
    out = parse_composition(NEAR_IDEAL)
    assert out["hea_bench_version"] == hb.__version__
    comp = out["composition"]
    assert comp["Mn"] == pytest.approx(0.35)
    assert sum(comp.values()) == pytest.approx(1.0)


def test_parse_composition_structured_error():
    with pytest.raises(ValueError, match="could not parse"):
        parse_composition("not a formula 123!!")


def test_alloy_descriptors_batch_with_provenance():
    out = alloy_descriptors([CANTOR, NEAR_IDEAL])
    assert len(out["results"]) == 2
    cantor, near = out["results"]
    smix = cantor["descriptors"]["s_mix"]
    assert smix["value"] == pytest.approx(13.381, abs=1e-3)
    assert smix["unit"] == "J/(mol K)"
    assert smix["source"] in SOURCES
    assert near["descriptors"]["h_mix"]["value"] == pytest.approx(-0.52, abs=1e-2)
    assert near["descriptors"]["omega"]["value"] == pytest.approx(37.77, abs=0.05)
    assert cantor["warnings"] == []


def test_alloy_descriptors_out_of_table_element_warns():
    out = alloy_descriptors(["NaKFeNiCo"])
    result = out["results"][0]
    # entropy depends only on fractions and still computes
    assert result["descriptors"]["s_mix"]["value"] is not None
    # at least one table-dependent descriptor degrades to null + warning
    assert any(d["value"] is None for d in result["descriptors"].values())
    assert result["warnings"]


def test_alloy_descriptors_king_temperature_override():
    base = alloy_descriptors([CANTOR])["results"][0]["descriptors"]["phi_king"]["value"]
    hot = alloy_descriptors([CANTOR], king_temperature=300.0)["results"][0]["descriptors"]["phi_king"]["value"]
    assert base != hot


def test_alloy_rules_cantor_verdicts():
    out = alloy_rules([CANTOR])
    rules = out["results"][0]["rules"]
    assert rules["zhang_delta"]["verdict"] == "single-phase"
    assert rules["guo_vec"]["verdict"] == "FCC"
    assert rules["yang_omega"]["verdict"] == "single-phase"
    assert rules["king_phi"]["verdict"] == "solid_solution"
    assert rules["ye_phi"]["verdict"] == "solid_solution"
    assert rules["yeh_entropy"]["verdict"]
    assert rules["zhang_delta"]["threshold"] == 6.5
    assert rules["zhang_delta"]["value"] == pytest.approx(3.164, abs=1e-3)


def test_alloy_rules_unbounded_phi_is_json_safe():
    """HfNbTaTiZr has no competing binary intermetallic (every pair
    enthalpy >= 0), so King Phi diverges to +inf. The tool must null the
    magnitude, warn, keep the verdict, and emit valid JSON (no Infinity
    token, which strict MCP clients reject)."""
    import json

    out = alloy_rules(["HfNbTaTiZr"])
    phi = out["results"][0]["rules"]["king_phi"]
    assert phi["value"] is None
    assert phi["verdict"] == "solid_solution"
    warnings = out["results"][0]["warnings"]
    assert any("king_phi" in w and "unbounded" in w for w in warnings)
    # the raw descriptor genuinely diverges; the tool only sanitizes output
    assert math.isinf(hb.phi_king({"Hf": 0.2, "Nb": 0.2, "Ta": 0.2, "Ti": 0.2, "Zr": 0.2}))
    # strict serialization must succeed
    json.dumps(out, allow_nan=False)


def test_omega_sensitivity_matches_manuscript_numbers():
    out = omega_sensitivity(NEAR_IDEAL, perturbation_kj_mol=2.0)
    assert out["dominant_element"] == "Mn"
    assert out["h_mix_kj_mol"] == pytest.approx(-0.52, abs=1e-2)
    low, high = out["h_mix_range_kj_mol"]
    assert low == pytest.approx(-2.34, abs=0.01)
    assert high == pytest.approx(1.30, abs=0.01)
    endpoints = sorted(out["omega_at_range_endpoints"])
    assert endpoints[0] == pytest.approx(8.39, abs=0.05)
    assert endpoints[1] == pytest.approx(15.11, abs=0.05)
    assert out["diverges_within_range"] is True
    # the Mn-Ni pair dominates the mixing enthalpy
    biggest = out["pair_contributions"][0]
    assert biggest["pair"] == "Mn-Ni"
    assert biggest["contribution_kj_mol"] == pytest.approx(-2.24, abs=0.01)


def test_omega_sensitivity_zero_perturbation():
    out = omega_sensitivity(NEAR_IDEAL, perturbation_kj_mol=0.0)
    assert out["diverges_within_range"] is False
    low, high = out["h_mix_range_kj_mol"]
    assert low == pytest.approx(high)


def test_oxide_report_rock_salt_j14_anchor():
    out = oxide_report("rock_salt", "MgCoNiCuZn")
    assert out["oxidation_states"] == {"Co": 2, "Cu": 2, "Mg": 2, "Ni": 2, "Zn": 2}
    assert out["descriptors"]["s_config"] == pytest.approx(8.314462618 * math.log(5), rel=1e-9)
    assert "Rost2015" in out["sources"]
    assert out["hea_bench_version"] == hb.__version__


def test_oxide_report_perovskite_jiang_anchor():
    out = oxide_report("perovskite", "Sr", b_site_cations="ZrSnTiHfMn")
    assert out["descriptors"]["goldschmidt_t"] == pytest.approx(0.979, abs=1e-3)
    assert out["verdicts"]["bartel"] == "perovskite"


def test_oxide_report_fluorite_spiridigliozzi_anchor():
    out = oxide_report("fluorite", "CeZrNdYEr", oxygen_per_formula_unit=1.7)
    assert out["descriptors"]["radius_sigma"] == pytest.approx(0.0976, abs=5e-4)


def test_oxide_report_requires_b_site_for_pyrochlore():
    with pytest.raises(ValueError, match="b_site_cations"):
        oxide_report("pyrochlore", "LaCeNdSmEu")


def test_oxide_report_unknown_family():
    with pytest.raises(ValueError, match="unknown family"):
        oxide_report("spinel", "FeCoNi")


def test_element_coverage_counts():
    out = element_coverage()
    assert out["alloy_count"] == 37
    assert out["oxide_count"] == 94
    assert "Zr" in out["alloy_descriptors_and_rules"]
    assert "La" in out["oxide_shannon_table"]


def test_about_has_version_and_sources():
    out = about()
    assert out["hea_bench_version"] == hb.__version__
    assert out["license"] == "MIT"
    assert "Takeuchi2005" in out["sources"]
