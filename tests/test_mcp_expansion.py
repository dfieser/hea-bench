"""Tests for the expanded MCP tool surface (corpus, properties, design).

Same convention as test_mcp_server.py: the tool bodies are plain
functions, so nothing here needs the optional mcp package.
"""

import pathlib

import pytest

import hea_bench as hb
from hea_bench.mcp_server import (
    about,
    campaign_suggest,
    check_applicability,
    corpus_describe,
    corpus_query,
    design_search,
    predict_properties,
)

_DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "data" / "consolidated"

needs_corpus = pytest.mark.skipif(
    not (_DATA_DIR / "v0.1.0" / "consolidated.csv").exists(),
    reason="benchmark corpus not built",
)


@needs_corpus
def test_corpus_query_returns_counts_and_a_capped_sample() -> None:
    out = corpus_query(contains=["Al"], phase="BCC", limit=5)
    assert out["hea_bench_version"] == hb.__version__
    assert out["n_matching"] > 0
    assert len(out["sample"]) <= 5
    row = out["sample"][0]
    assert "composition_key" in row
    assert "raw_labels" in row
    assert "sources" in row


@needs_corpus
def test_corpus_query_sample_cap_is_hard() -> None:
    out = corpus_query(limit=5000)
    assert len(out["sample"]) <= 50
    assert out["sample_capped_at"] == 50


@needs_corpus
def test_corpus_describe_summarizes_a_slice() -> None:
    out = corpus_describe(contains=["Co", "Cr"], labelled=True)
    assert out["n_rows"] > 0
    assert "by_phase" in out
    assert "multi_source_agreement_rate" in out


def test_corpus_query_missing_corpus_is_structured(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HEA_BENCH_BENCHMARK_DIR", str(tmp_path))
    with pytest.raises(ValueError, match="consolidate"):
        corpus_query(contains=["Al"])


def test_predict_properties_top_level_uncertainty_fields() -> None:
    out = predict_properties(["AlCoCrFeNi"], properties=["density", "cost_per_kg"])
    entry = out["results"][0]
    density = entry["properties"]["density"]
    assert density["value"] > 0
    assert density["unit"] == "g/cm^3"
    assert density["tier"] == "A"
    assert "in_domain" in density
    assert "interval" in density
    assert isinstance(density["warnings"], list)
    cost = entry["properties"]["cost_per_kg"]
    assert cost["asof"]


def test_predict_properties_unknown_property_is_structured() -> None:
    with pytest.raises(ValueError, match="unknown property"):
        predict_properties(["CoCrFeMnNi"], properties=["toughness"])


def test_predict_properties_hardness_carries_interval() -> None:
    pytest.importorskip("sklearn")
    out = predict_properties(["AlCoCrFeNi"], properties=["hardness"])
    hardness = out["results"][0]["properties"]["hardness"]
    assert hardness["tier"] == "B"
    low, high = hardness["interval"]
    assert low <= hardness["value"] <= high
    assert isinstance(hardness["in_domain"], bool)
    assert hardness["n_training"] >= 300


@needs_corpus
def test_check_applicability_reports_components() -> None:
    out = check_applicability("CoCrFeMnNi")
    for key in (
        "element_set_seen",
        "family_count",
        "nearest_family_distance",
        "descriptor_distance",
        "element_coverage",
        "in_domain",
    ):
        assert key in out
    assert out["in_domain"] is True


def test_design_search_refuses_an_oversized_palette() -> None:
    with pytest.raises(ValueError, match="10"):
        design_search(
            ["Al", "Co", "Cr", "Cu", "Fe", "Mn", "Ni", "Ti", "V", "W", "Zr"],
            objectives=[["minimize", "density"]],
        )


def test_design_search_refuses_too_many_candidates() -> None:
    with pytest.raises(ValueError, match="20"):
        design_search(
            ["Al", "Fe", "W"],
            objectives=[["minimize", "density"]],
            max_candidates=100,
        )


def test_design_search_refuses_too_fine_a_step() -> None:
    with pytest.raises(ValueError, match="0.05"):
        design_search(
            ["Al", "Fe", "W"],
            objectives=[["minimize", "density"]],
            step=0.01,
        )


def test_design_search_runs_and_stamps() -> None:
    out = design_search(
        ["Al", "Fe", "W"],
        n_elements_min=2,
        n_elements_max=3,
        step=0.2,
        objectives=[["minimize", "density"], ["minimize", "cost_per_kg"]],
        include_out_of_domain=True,
    )
    assert out["hea_bench_version"] == hb.__version__
    assert out["n_front"] >= len(out["candidates"]) > 0
    candidate = out["candidates"][0]
    assert candidate["objective_values"]["density"] > 0
    assert "properties" in candidate


def test_campaign_suggest_operates_on_a_user_file(tmp_path) -> None:
    pytest.importorskip("sklearn")
    from hea_bench.design import DomainConstraint
    from hea_bench.design.campaign import Campaign

    path = tmp_path / "campaign.json"
    Campaign(
        "hardness",
        ["Al", "Co", "Cr", "Fe", "Ni"],
        (DomainConstraint(in_domain=None),),
        seed=1,
        step=0.25,
        n_elements=(4, 5),
    ).save(path)

    out = campaign_suggest(str(path), n=2)
    assert len(out["suggestions"]) == 2
    suggestion = out["suggestions"][0]
    assert suggestion["interval"][0] <= suggestion["mean"] <= suggestion["interval"][1]
    assert "in_domain" in suggestion
    assert out["objective"] == "hardness"


def test_campaign_suggest_caps_the_batch(tmp_path) -> None:
    with pytest.raises(ValueError, match="10"):
        campaign_suggest(str(tmp_path / "missing.json"), n=50)


def test_campaign_suggest_missing_file_is_structured(tmp_path) -> None:
    with pytest.raises(ValueError, match="campaign"):
        campaign_suggest(str(tmp_path / "missing.json"), n=2)


def test_about_lists_capability_availability() -> None:
    capabilities = about()["capabilities"]
    for key in ("corpus", "properties_tier_b", "design_search", "campaigns", "interop"):
        assert key in capabilities
        assert isinstance(capabilities[key], bool)
