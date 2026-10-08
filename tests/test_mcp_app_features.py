"""The MCP tools that bring the server to the app's feature set (v2.7.0).

Same convention as test_mcp_server.py: the tool bodies are plain
functions, so nothing here needs the optional mcp package.
"""

import csv
import pathlib

import pytest

import hea_bench as hb
from hea_bench.mcp_server import (
    about,
    alloy_descriptors,
    alloy_rules,
    benchmark_folds,
    benchmark_run,
    benchmark_score,
    benchmark_summary,
    campaign_suggest,
    ceramic_report,
    corpus_build,
    corpus_export,
    element_data,
    measured_properties,
    omega_sensitivity,
    predict_phase_set,
)

_REPO = pathlib.Path(__file__).resolve().parents[1]
_DATA_DIR = _REPO / "data" / "consolidated"
_PEIVASTE = _REPO / "data" / "raw" / "peivaste" / "dataset11252_79.csv"

needs_corpus = pytest.mark.skipif(
    not (_DATA_DIR / "v0.1.0" / "consolidated.csv").exists(),
    reason="benchmark corpus not built",
)

_XX = {"Xx": {"radius_pm": 140.0, "melting_K": 1800.0, "valence": 6, "electronegativity": 1.7}}
_XX_PAIRS = {"Co-Xx": -5.0, "Cr-Xx": -3.0, "Fe-Xx": -4.0, "Ni-Xx": -6.0}


# -- calculator ---------------------------------------------------------------


def test_alloy_descriptors_carry_the_miedema_decomposition() -> None:
    entry = alloy_descriptors(["CuZr"])["results"][0]
    miedema = entry["miedema_enthalpies"]
    assert miedema["unit"] == "kJ/mol"
    assert miedema["compound"]["H_form"] == pytest.approx(-30.78, abs=0.01)
    assert miedema["amorphous"]["H_total"] == pytest.approx(-16.19, abs=0.01)
    assert set(miedema["solid_solution"]) == {"H_chem", "H_elast", "H_struct", "H_total"}


def test_custom_element_works_like_the_app_editor() -> None:
    out = alloy_descriptors(["CoCrFeNiXx"], custom_elements=_XX, pair_enthalpies=_XX_PAIRS)
    entry = out["results"][0]
    assert entry["composition"]["Xx"] == pytest.approx(0.2)
    assert entry["descriptors"]["vec"]["value"] == pytest.approx((9 + 6 + 8 + 10 + 6) / 5)
    assert entry["descriptors"]["omega"]["value"] is not None
    # No Miedema parameters for a made-up element: unavailable, said so.
    assert entry["miedema_enthalpies"]["compound"] is None
    assert any("Miedema" in warning for warning in entry["warnings"])

    rules = alloy_rules(["CoCrFeNiXx"], custom_elements=_XX, pair_enthalpies=_XX_PAIRS)
    assert rules["results"][0]["rules"]["guo_vec"]["verdict"] is not None

    sensitivity = omega_sensitivity("CoCrFeNiXx", custom_elements=_XX, pair_enthalpies=_XX_PAIRS)
    assert sensitivity["omega"] is not None


def test_custom_element_without_pair_values_is_a_warning_not_a_number() -> None:
    entry = alloy_descriptors(["CoCrFeNiXx"], custom_elements=_XX)["results"][0]
    assert entry["descriptors"]["h_mix"]["value"] is None
    assert any("h_mix" in warning for warning in entry["warnings"])


def test_custom_element_is_scoped_to_one_call() -> None:
    alloy_descriptors(["CoCrFeNiXx"], custom_elements=_XX, pair_enthalpies=_XX_PAIRS)
    with pytest.raises(ValueError, match="Xx"):
        alloy_descriptors(["CoCrFeNiXx"])


def test_pair_enthalpy_override_changes_the_mixing_enthalpy() -> None:
    base = alloy_descriptors(["CoCr"])["results"][0]["descriptors"]["h_mix"]["value"]
    shifted = alloy_descriptors(["CoCr"], pair_enthalpies={"Co-Cr": -20.0})
    assert shifted["results"][0]["descriptors"]["h_mix"]["value"] == pytest.approx(-20.0)
    assert base != pytest.approx(-20.0)


def test_ceramic_report_matches_the_library() -> None:
    from hea_bench.ceramics import describe_rock_salt_carbide

    out = ceramic_report("rock_salt_carbide", "HfNbTaTiZr")
    expected = describe_rock_salt_carbide(hb.parse_formula("HfNbTaTiZr"))
    assert out["entropy"] == expected["entropy"]
    assert out["vec_per_formula_unit"] == pytest.approx(expected["vec_per_formula_unit"])
    assert "vec_per_formula_unit" not in ceramic_report("diboride", "HfNbTaTiZr")
    with pytest.raises(ValueError, match="diboride"):
        ceramic_report("perovskite", "HfNbTaTiZr")


def test_element_data_reports_values_sources_and_hashes() -> None:
    out = element_data(["Co", "Cr"])
    assert set(out["elements"]) == {"Co", "Cr"}
    cobalt = out["elements"]["Co"]
    assert cobalt["radius_pm"] > 0 and cobalt["supports"]["miedema_decomposition"] is True
    assert out["units"]["radius_pm"] == "pm"
    assert set(out["data_files"]) >= {"elemental.py", "pair_enthalpies.tsv"}
    assert len(element_data()["elements"]) == 55
    with pytest.raises(ValueError, match="Qq"):
        element_data(["Qq"])


def test_measured_properties_counts_exactly_and_caps_the_sample() -> None:
    out = measured_properties("hardness", contains=["Al"], limit=3)
    assert out["unit"] == "HV"
    assert out["n_matching"] > 3
    assert len(out["rows"]) == 3
    assert all("Al" in row["composition"] for row in out["rows"])
    assert len(measured_properties("density", limit=500)["rows"]) <= 50
    with pytest.raises(ValueError, match="hardness"):
        measured_properties("toughness")


# -- dataset ------------------------------------------------------------------


@needs_corpus
def test_corpus_export_writes_the_slice_and_never_overwrites(tmp_path) -> None:
    target = tmp_path / "al.csv"
    out = corpus_export(str(target), contains=["Al"], version="0.1.0")
    with target.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert out["n_rows"] == len(rows) > 0
    assert all("Al" in row["composition_key"] for row in rows)
    with pytest.raises(ValueError, match="already exists"):
        corpus_export(str(target))


@pytest.mark.skipif(not _PEIVASTE.exists(), reason="Peivaste CSV not fetched")
def test_corpus_build_builds_where_the_tools_read(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HEA_BENCH_BENCHMARK_DIR", str(tmp_path))
    out = corpus_build(versions=["0.1.0"], peivaste_csv=str(_PEIVASTE))
    assert out["built"]["0.1.0"]["totals"]["unique_compositions"] == 7783
    assert (tmp_path / "v0.1.0" / "consolidated.csv").exists()
    assert about()["corpus_versions_built"]["0.1.0"] is True


# -- predictions and benchmark ------------------------------------------------


@needs_corpus
def test_predict_phase_set_batches_and_reports_per_entry_errors() -> None:
    pytest.importorskip("sklearn")
    # Po parses as an element but has no tabulated data: an entry error.
    out = predict_phase_set(["CoCrFeMnNi", "CoCrFeNiPo"], task="single_vs_multi")
    good, bad = out["results"]
    assert set(good["prediction_set"]) <= {"single-phase", "multi-phase"}
    assert good["prediction_set"]
    assert isinstance(good["in_domain"], bool)
    # Five elements: calibrated on the four-or-more group's scores only.
    assert 0 < good["n_calibration"] < good["n_training"]
    assert "cross-validation" in good["model"]
    assert "descriptor" in bad["error"]
    with pytest.raises(ValueError, match="phase4"):
        predict_phase_set(["CoCrFeMnNi"], task="phase9")


@needs_corpus
def test_benchmark_tools_match_the_app_bridge(tmp_path) -> None:
    summary = benchmark_summary()
    assert summary["digests"]["verified"] is True
    assert "majority-class" in summary["baselines"]

    report = benchmark_run("majority-class")
    assert "gap" in report

    folds_path = tmp_path / "folds.csv"
    folds = benchmark_folds(str(folds_path))
    with pytest.raises(ValueError, match="already exists"):
        benchmark_folds(str(folds_path))
    with folds_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == folds["n_rows"]

    # Predict multi-phase everywhere and score it like an uploaded model.
    predictions = tmp_path / "predictions.csv"
    with predictions.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["composition_key", "grouped", "random"])
        for row in rows:
            writer.writerow([row["composition_key"], "multi-phase", "multi-phase"])
    scored = benchmark_score(str(predictions), model_name="all multi")
    assert scored["model"] == "all multi"
    assert "gap" in scored
    with pytest.raises(ValueError, match="no predictions file"):
        benchmark_score(str(tmp_path / "missing.csv"))


def test_campaign_suggest_accepts_the_campaign_inline(tmp_path) -> None:
    pytest.importorskip("sklearn")
    import json

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
    campaign = json.loads(path.read_text(encoding="utf-8"))
    campaign["observations"] = [{"composition": "AlCoCrFeNi", "value": 500.0}]
    out = campaign_suggest(campaign=campaign, n=2)
    assert len(out["suggestions"]) == 2
    assert out["campaign"]["objective"] == "hardness"
    with pytest.raises(ValueError, match="exactly one"):
        campaign_suggest()


def test_about_reports_every_corpus_version() -> None:
    out = about()
    assert set(out["corpus_versions_built"]) == {"0.1.0", "0.2.0"}
    assert "corpus_build" in out["capability_notes"]["corpus"]
