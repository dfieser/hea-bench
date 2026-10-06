"""Tests for the web app's engine bridge, phase sets and the coverage study.

The bridge is what the browser engine calls, so these tests are the
CPython half of app parity: the same calls, the same envelopes, the same
numbers the Python API gives. Corpus-backed tests skip on a bare
checkout; the CI ``web-engine`` job builds the corpus and runs them.
"""

import json
import math
import pathlib

import pytest

from hea_bench import webapp
from hea_bench._json import strict_json

_DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "data" / "consolidated"
needs_corpus = pytest.mark.skipif(
    not (_DATA_DIR / "v0.1.0" / "consolidated.csv").exists(),
    reason="benchmark corpus not built",
)


def _call(method: str, **params):
    envelope = json.loads(webapp.call(method, json.dumps(params)))
    assert set(envelope) in ({"ok", "result"}, {"ok", "error", "type"})
    return envelope


def test_unknown_method_is_an_envelope_not_a_traceback() -> None:
    envelope = _call("no_such_method")
    assert envelope["ok"] is False
    assert "no_such_method" in envelope["error"]


def test_bad_composition_error_names_the_fix() -> None:
    envelope = _call("properties", composition="Qq")
    assert envelope["ok"] is False
    assert "CoCrFeMnNi" in envelope["error"]


def test_non_finite_floats_become_null() -> None:
    assert strict_json({"a": (math.inf, 1.0), "b": math.nan}) == {"a": [None, 1.0], "b": None}


def test_one_unavailable_property_does_not_hide_the_others() -> None:
    result = _call("properties", composition="CoCrFeMnNi", names=["density", "cost_per_kg"])
    assert result["ok"]
    props = result["result"]["properties"]
    assert props["density"]["unit"] == "g/cm^3"
    assert set(result["result"]["cost_breakdown"]) == {"Co", "Cr", "Fe", "Mn", "Ni"}
    failed = _call("properties", composition={"Fr": 0.5, "Co": 0.5}, names=["density"])
    assert "Fr" in failed["result"]["properties"]["density"]["error"]


@needs_corpus
def test_dataset_pages_are_capped_and_carry_provenance() -> None:
    first = _call("dataset_query", filters={"contains": ["Al"]}, limit=10_000)["result"]
    assert len(first["rows"]) == webapp.PAGE_CAP
    assert first["n_matching"] > webapp.PAGE_CAP
    row = first["rows"][0]
    assert {"labels", "raw_labels", "source_row_ids", "sources"} <= set(row)
    second = _call("dataset_query", filters={"contains": ["Al"]}, offset=1, limit=1)["result"]
    assert second["rows"][0] == first["rows"][1]
    csv_text = _call("dataset_csv", filters={"elements": ["Co", "Cr", "Fe", "Mn", "Ni"]})
    assert csv_text["result"]["text"].startswith("composition_key,")


@needs_corpus
def test_uploaded_fold_predictions_match_evaluate() -> None:
    pytest.importorskip("sklearn")
    import csv
    import io

    from hea_bench.benchmark import evaluate, load_benchmark

    folds = _call("benchmark_folds_csv")["result"]
    rows = list(csv.DictReader(io.StringIO(folds["text"])))
    assert len(rows) == folds["n_rows"]
    upload = "composition_key,grouped,random\n" + "".join(
        f"{row['composition_key']},multi-phase,multi-phase\n" for row in rows
    )
    scored = _call("benchmark_score", csv_text=upload)["result"]
    direct = evaluate(lambda composition: "multi-phase", load_benchmark(task="single_vs_multi"))
    assert scored["gap"] == pytest.approx(direct.gap)
    assert scored["grouped"]["digest"] == direct.grouped.digest


@needs_corpus
def test_benchmark_summary_verifies_the_frozen_digests() -> None:
    summary = _call("benchmark_summary", task="phase4")["result"]
    assert summary["digests"]["verified"] is True
    assert summary["published"]["coverage"]["n_evaluated"] == summary["n_evaluated"]


@needs_corpus
def test_live_rule_baseline_reproduces_the_published_row() -> None:
    live = _call("benchmark_run", model="rule:zhang_delta")["result"]
    published = json.loads(
        (pathlib.Path(__file__).resolve().parents[1] / "docs" / "benchmark-baselines.json")
        .read_text(encoding="utf-8")
    )["results"]["single_vs_multi"]
    row = next(entry for entry in published if entry["model"] == "rule:zhang_delta")
    assert live["gap"] == pytest.approx(row["gap"])
    assert live["grouped"]["balanced_accuracy_mean"] == pytest.approx(
        row["grouped"]["balanced_accuracy_mean"]
    )


@needs_corpus
def test_phase_set_for_the_cantor_alloy() -> None:
    pytest.importorskip("sklearn")
    result = _call("phase_prediction", composition="CoCrFeMnNi")["result"]
    assert "single-phase" in result["prediction_set"]
    assert sum(result["probabilities"].values()) == pytest.approx(1.0)
    assert result["in_domain"] is True
    assert result["target_coverage"] == pytest.approx(0.9)


@needs_corpus
def test_campaign_round_trips_formula_observations() -> None:
    pytest.importorskip("sklearn")
    campaign = {
        "schema": 1,
        "objective": "hardness",
        "direction": "maximize",
        "palette": ["Al", "Co", "Cr", "Fe", "Ni"],
        "constraints": [{"type": "DomainConstraint", "in_domain": None}],
        "seed": 0,
        "step": 0.25,
        "n_elements": [4, 5],
        "warm_start": True,
        "observations": [
            {"composition": "AlCoCrFe", "value": 480.0, "processing": None, "uncertainty": None}
        ],
    }
    result = _call("campaign_suggest", campaign=campaign, n=2)["result"]
    assert len(result["suggestions"]) == 2
    assert result["campaign"]["observations"][0]["composition"] == {
        "Al": 0.25, "Co": 0.25, "Cr": 0.25, "Fe": 0.25
    }


@needs_corpus
def test_coverage_study_reproduces_the_published_table() -> None:
    pytest.importorskip("sklearn")
    from hea_bench.uncertainty.coverage import coverage_study

    study = coverage_study("single_vs_multi", alphas=(0.1,))
    overall = study["levels"][0]["groups"]["all"]
    assert study["n_rows"] == 7217
    assert study["n_out_of_domain"] == 615
    assert round(overall["coverage"], 3) == 0.882
    assert len(overall["fold_coverage"]) == 5


def test_peivaste_install_refuses_different_bytes(tmp_path) -> None:
    wrong = tmp_path / "peivaste.csv"
    wrong.write_bytes(b"not the pinned file")
    envelope = _call("peivaste_install", path=str(wrong))
    assert envelope["ok"] is False
    assert "pinned" in envelope["error"]
    source = _call("peivaste_source")["result"]
    assert source["sha256"] == "655a43e521003f5c8973050b5f7c0a5d4b9ab902ca4ecc9c8a7d9813b2b0ba10"


def test_measured_properties_are_the_training_records() -> None:
    from hea_bench.properties.borg import experimental_density_records, hardness_records

    hardness = _call("measured_properties")["result"]
    assert hardness["unit"] == "HV"
    assert hardness["n_total"] == hardness["n_matching"] == len(hardness_records())
    with_al = _call("measured_properties", prop="hardness", contains=["Al"])["result"]
    assert 0 < with_al["n_matching"] < hardness["n_total"]
    assert all("Al" in row["composition"] for row in with_al["rows"])
    density = _call("measured_properties", prop="density")["result"]
    assert density["n_total"] == len(experimental_density_records())
    assert density["rows"][0]["doi"]
    wrong = _call("measured_properties", prop="yield_strength")
    assert wrong["ok"] is False
    assert "'hardness' or 'density'" in wrong["error"]


def test_every_method_is_registered() -> None:
    assert set(webapp.METHODS) == {
        "engine_info", "dataset_status", "peivaste_source", "peivaste_install",
        "dataset_build", "dataset_query",
        "dataset_describe", "dataset_csv", "measured_properties", "properties", "applicability",
        "phase_prediction", "search", "campaign_suggest", "benchmark_summary",
        "benchmark_run", "benchmark_folds_csv", "benchmark_score", "coverage",
        "warm_next", "warm",
    }


@needs_corpus
def test_background_preparation_runs_every_step_once(monkeypatch, tmp_path) -> None:
    pytest.importorskip("sklearn")
    from hea_bench.properties import hardness

    monkeypatch.setenv("HEA_BENCH_MODEL_CACHE", str(tmp_path))
    # Fits earlier tests left in memory would skip the disk cache.
    webapp._clear_caches()
    hardness._fitted.cache_clear()
    steps = []
    while (step := _call("warm_next")["result"]) is not None:
        assert _call("warm", step=step)["ok"] is True
        steps.append(step)
    assert len(steps) == len(set(steps))
    assert {"hardness", "phase:single_vs_multi", "phase:phase4"} <= set(steps)
    # The fitted models are on disk for the next visit.
    names = {path.name.split("-")[0] for path in tmp_path.glob("*.pickle.gz")}
    assert {"phase", "hardness", "domain"} <= names
    unknown = _call("warm", step="nonsense")
    assert unknown["ok"] is False


def test_model_cache_round_trips_and_isolates_custom_data(monkeypatch, tmp_path) -> None:
    pytest.importorskip("sklearn")
    import hea_bench as hb
    from hea_bench import _model_cache, _overrides

    seen = []

    def fit():
        seen.append(_overrides.PAIRS.get())
        return {"fitted": len(seen)}

    monkeypatch.setenv("HEA_BENCH_MODEL_CACHE", str(tmp_path))
    with hb.custom_data(pair_enthalpies={"Co-Cr": -20.0}):
        assert _model_cache.cached("probe", fit) == {"fitted": 1}
    assert seen == [None]  # the fit never saw the caller's pair values
    assert _model_cache.cached("probe", fit) == {"fitted": 1}  # loaded, not refit
    (stored,) = tmp_path.glob("probe-*.pickle.gz")
    stored.write_bytes(b"torn")
    assert _model_cache.cached("probe", fit) == {"fitted": 2}  # a bad file is refit
    monkeypatch.delenv("HEA_BENCH_MODEL_CACHE")
    assert _model_cache.cached("probe", fit) == {"fitted": 3}
