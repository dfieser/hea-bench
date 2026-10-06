"""JSON bridge between the web app's in-browser engine and the library.

The web app and the desktop shell run this package unmodified in
Pyodide (``web/hea-engine-worker.js``) and reach it only through
:func:`call`: a method name and JSON arguments in, one JSON envelope
out. Every number the app shows for the dataset, the benchmark, phase
sets, hardness, the domain flag, the alloy search and campaigns is
therefore computed by the same code the Python API runs, not by a port.

Each method is a plain function over JSON-able values, so this module is
tested in CI like the rest of the library, and ``METHODS`` is the
registry the app-parity check reads.
"""

from __future__ import annotations

import csv
import io
import json
import math
import pathlib
import tempfile
from functools import lru_cache

from . import __version__

#: The bundled published baseline results (the engine archive carries
#: docs/benchmark-baselines.json at the same repo-relative path).
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_BASELINES_JSON = _REPO_ROOT / "docs" / "benchmark-baselines.json"

#: Largest dataset page the app may request in one call.
PAGE_CAP = 500

_progress = None


def set_progress(callback) -> None:
    """Install the worker's ``(message, fraction)`` progress callback."""
    global _progress
    _progress = callback


def _report(message: str, fraction: float) -> None:
    if _progress is not None:
        _progress(message, float(fraction))


def _clean(value):
    """Strict-JSON copy: non-finite floats become None, tuples lists."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(key): _clean(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    return value


def _composition(value) -> dict[str, float]:
    """A formula string or a mole-fraction dict, normalized."""
    from .composition import normalize, parse_formula

    if isinstance(value, str):
        try:
            return dict(parse_formula(value))
        except Exception as error:
            raise ValueError(
                f"could not read the composition {value!r}: {error}. Write element "
                f"symbols with optional amounts, for example CoCrFeMnNi or Al0.3CoCrFeNi."
            ) from None
    return dict(normalize(value))


# -- engine -------------------------------------------------------------------


def engine_info() -> dict:
    """Versions, which corpora are built, and the hardness processing routes."""
    import platform
    from collections import Counter

    import sklearn

    from .benchmark.consolidate import SOURCES_BY_VERSION
    from .properties.borg import hardness_records

    return {
        "hea_bench_version": __version__,
        "python": platform.python_version(),
        "scikit_learn": sklearn.__version__,
        "corpus_versions": list(SOURCES_BY_VERSION),
        "built": dataset_status()["built"],
        "hardness_processing": dict(
            Counter(record.processing for record in hardness_records() if record.processing)
        ),
    }


# -- dataset ------------------------------------------------------------------


def dataset_status() -> dict:
    """Which corpus versions are built in this engine."""
    from .benchmark.consolidate import SOURCES_BY_VERSION
    from .corpus import corpus_location

    return {
        "built": {
            version: (corpus_location(version) / "consolidated.csv").exists()
            for version in SOURCES_BY_VERSION
        }
    }


def peivaste_source() -> dict:
    """Where the unlicensed Peivaste CSV comes from, its pinned hash, and
    whether it is in place. The recipe is data/raw/peivaste/fetch.py."""
    recipe = _peivaste_recipe()
    return {
        "url": recipe["UPSTREAM_URL"],
        "sha256": recipe["EXPECTED_SHA256"],
        "bytes": recipe["EXPECTED_BYTES"],
        "installed": recipe["TARGET"].exists(),
    }


def _peivaste_recipe() -> dict:
    import runpy

    return runpy.run_path(str(_REPO_ROOT / "data" / "raw" / "peivaste" / "fetch.py"))


def peivaste_install(path: str) -> dict:
    """Verify a downloaded Peivaste file against the pinned SHA-256 and put
    it where the corpus build reads it. Refuses different bytes."""
    import hashlib

    recipe = _peivaste_recipe()
    data = pathlib.Path(path).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != recipe["EXPECTED_SHA256"]:
        raise ValueError(
            f"the downloaded Peivaste file has SHA-256 {digest}, not the pinned "
            f"{recipe['EXPECTED_SHA256']}. The upstream file changed, so the frozen corpus "
            f"cannot be rebuilt from it; please report this at "
            f"https://github.com/dfieser/hea-bench/issues"
        )
    target = recipe["TARGET"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return {"installed": True, "bytes": len(data)}


def dataset_build(version: str = "0.1.0") -> dict:
    """Build one corpus version from the raw sources, exactly as the CLI
    does, into the directory the loaders read (which honours
    HEA_BENCH_BENCHMARK_DIR, where the app keeps its persistent copy)."""
    from .benchmark.consolidate import build
    from .corpus import corpus_location

    _report(f"building corpus v{version}", 0.1)
    manifest = build(version, out_dir=corpus_location(version))
    _clear_caches()
    _report("done", 1.0)
    return manifest


def _clear_caches() -> None:
    from .uncertainty import applicability, phase

    _corpus.cache_clear()
    _benchmark.cache_clear()
    _finite.cache_clear()
    phase._fitted.cache_clear()
    phase._domain_for.cache_clear()
    applicability.default_domain.cache_clear()


@lru_cache(maxsize=2)
def _corpus(version: str):
    from .corpus import load_corpus

    return load_corpus(version=version)


def _slice(version: str, filters: dict | None):
    filters = dict(filters or {})
    n_min = filters.pop("n_elements_min", None)
    n_max = filters.pop("n_elements_max", None)
    if n_min is not None or n_max is not None:
        filters["n_elements"] = (n_min or 1, n_max or 99)
    allowed = {
        "elements", "contains", "excludes", "n_elements", "phase", "source",
        "family", "labelled", "has_conflict", "descriptor_ready",
    }
    unknown = sorted(set(filters) - allowed)
    if unknown:
        raise ValueError(f"unknown dataset filters {unknown}; expected {sorted(allowed)}")
    return _corpus(version).query(**{k: v for k, v in filters.items() if v not in (None, [], "")})


def _row_payload(row) -> dict:
    return {
        "composition_key": row.composition_key,
        "composition": dict(row.composition),
        "n_elements": row.n_elements,
        "family": row.family,
        "canonical_phase": row.canonical_phase,
        "has_conflict": row.has_conflict,
        "sources": list(row.sources),
        "labels": dict(row.labels),
        "raw_labels": dict(row.raw_labels),
        "processing": row.processing,
        "doi": row.doi,
        "source_row_ids": dict(row.source_row_ids),
        "descriptor_ready": row.descriptor_ready,
    }


def dataset_query(
    filters: dict | None = None, version: str = "0.1.0", offset: int = 0, limit: int = 100
) -> dict:
    """One page of a filtered corpus slice, every row with full provenance."""
    subset = _slice(version, filters)
    limit = max(0, min(int(limit), PAGE_CAP))
    offset = max(0, int(offset))
    return {
        "corpus_version": version,
        "n_matching": len(subset),
        "offset": offset,
        "rows": [_row_payload(row) for row in subset.rows[offset : offset + limit]],
    }


def dataset_describe(filters: dict | None = None, version: str = "0.1.0") -> dict:
    """Counts by phase, element count, source and family for a slice."""
    return _slice(version, filters).describe()


def dataset_csv(filters: dict | None = None, version: str = "0.1.0") -> dict:
    """The slice in the consolidated-CSV schema, as text for a download."""
    subset = _slice(version, filters)
    handle = io.StringIO(newline="")
    writer = csv.writer(handle)
    writer.writerow(subset.columns)
    for record in subset.records:
        writer.writerow([record.get(column, "") for column in subset.columns])
    return {
        "filename": f"hea-bench-corpus-v{version}.csv",
        "n_rows": len(subset),
        "text": handle.getvalue(),
    }


# -- measured properties (Borg 2020) -------------------------------------------


def measured_properties(prop: str = "hardness", contains: list | None = None) -> dict:
    """The Borg 2020 measurements the hardness model trains on, or the
    measured densities the rule-of-mixtures estimate is checked against,
    optionally only alloys that contain every element in ``contains``."""
    from .properties.borg import experimental_density_records, hardness_records

    loaders = {
        "hardness": (hardness_records, "HV"),
        "density": (experimental_density_records, "g/cm^3"),
    }
    if prop not in loaders:
        raise ValueError(f"unknown property {prop!r}: use 'hardness' or 'density'")
    load, unit = loaders[prop]
    records = load()
    wanted = {str(symbol) for symbol in (contains or [])}
    rows = [
        {
            "composition": dict(record.composition),
            "formula_raw": record.formula_raw,
            "value": record.value,
            "processing": record.processing,
            "doi": record.doi,
            "reference_id": record.reference_id,
            "year": record.year,
        }
        for record in records
        if wanted <= set(record.composition)
    ]
    return {
        "property": prop,
        "unit": unit,
        "n_total": len(records),
        "n_matching": len(rows),
        "rows": rows[:PAGE_CAP],
        "source": "Borg et al. (2020), Sci. Data 7, 430, doi:10.1038/s41597-020-00768-9, CC BY 4.0",
    }


# -- single-composition predictions --------------------------------------------


def properties(
    composition, alpha: float = 0.1, processing: str | None = None, names: list | None = None
) -> dict:
    """Every property for one composition; a property that cannot be
    computed carries its reason instead of hiding the others."""
    from .properties import (
        PropertyUnavailableError,
        available_properties,
        cost_breakdown,
        predict_property,
    )

    comp = _composition(composition)
    results: dict = {}
    for name in names or sorted(available_properties()):
        try:
            processing_arg = processing if name == "hardness" else None
            results[name] = predict_property(
                comp, name, alpha=alpha, processing=processing_arg
            ).to_dict()
        except PropertyUnavailableError as error:
            results[name] = {"error": str(error)}
    try:
        breakdown = cost_breakdown(comp)
    except ValueError:
        breakdown = None
    return {
        "composition": comp,
        "properties": results,
        "cost_breakdown": breakdown,
    }


def applicability(composition, version: str = "0.1.0") -> dict:
    """The corpus domain flag and its novelty components."""
    from .uncertainty.phase import _corpus_domain

    comp = _composition(composition)
    payload = dict(_corpus_domain(version).novelty(comp))
    payload["composition"] = comp
    payload["corpus_version"] = version
    return payload


def phase_prediction(
    composition, task: str = "single_vs_multi", alpha: float = 0.1, version: str = "0.1.0"
) -> dict:
    """Conformal phase prediction set for one composition."""
    from .uncertainty.phase import predict_phase_set

    _report("fitting the phase model (first call per task only)", 0.2)
    return predict_phase_set(_composition(composition), task=task, alpha=alpha, version=version)


# -- design ---------------------------------------------------------------------


def search(**params) -> dict:
    """The constrained alloy search, with the MCP tool's caps and schema."""
    from .mcp_server import design_search

    _report("screening the composition lattice", 0.1)
    return design_search(**params)


def campaign_suggest(campaign: dict, n: int = 5, strategy: str = "ei") -> dict:
    """Next suggestions for a campaign file's contents (schema 1).

    Observation compositions may be formulas; they are normalized here.
    The response carries the campaign back in canonical form, which is
    what the app saves.
    """
    from .design.campaign import Campaign
    from .mcp_server import campaign_suggest as suggest_from_file

    payload = dict(campaign)
    payload["observations"] = [
        {**obs, "composition": _composition(obs["composition"])}
        for obs in payload.get("observations", [])
    ]
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder) / "campaign.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        canonical = pathlib.Path(folder) / "canonical.json"
        Campaign.load(path).save(canonical)
        _report("fitting the campaign surrogate", 0.2)
        result = suggest_from_file(str(path), n=n, strategy=strategy)
        result["campaign"] = json.loads(canonical.read_text(encoding="utf-8"))
    result.pop("campaign_path", None)
    return result


# -- benchmark ------------------------------------------------------------------


@lru_cache(maxsize=4)
def _benchmark(task: str, version: str):
    from .benchmark import load_benchmark

    return load_benchmark(task=task, version=version)


@lru_cache(maxsize=4)
def _finite(task: str, version: str) -> tuple[int, ...]:
    from .benchmark import finite_descriptor_indices

    return finite_descriptor_indices(_benchmark(task, version))


def benchmark_summary(task: str = "single_vs_multi", version: str = "0.1.0") -> dict:
    """Split balance, family overlap, digest check and the published table."""
    from .benchmark.baselines import BASELINE_NAMES
    from .benchmark.frozen import verify_split_digests

    _report("loading the benchmark", 0.2)
    bench = _benchmark(task, version)
    published = None
    if version == "0.1.0" and _BASELINES_JSON.exists():
        stored = json.loads(_BASELINES_JSON.read_text(encoding="utf-8"))
        published = {
            "results": stored["results"].get(task),
            "coverage": stored["coverage"].get(task),
        }
    return {
        "described": bench.describe(),
        "digests": verify_split_digests(bench),
        "n_evaluated": len(_finite(task, version)),
        "baselines": list(BASELINE_NAMES[task]),
        "published": published,
    }


class _Counted:
    """A baseline that reports progress per fold fit; predictions unchanged."""

    def __init__(self, model, total: int) -> None:
        self._model = model
        self._total = total
        self._done = 0
        self.name = getattr(model, "name", getattr(model, "__name__", "model"))

    def fit(self, compositions, labels):
        _report(f"fitting fold {self._done + 1} of {self._total}", self._done / self._total)
        self._model.fit(compositions, labels)
        self._done += 1
        return self

    def predict(self, compositions):
        return self._model.predict(compositions)


def benchmark_run(model: str, task: str = "single_vs_multi", version: str = "0.1.0") -> dict:
    """Score one published baseline live, on the same rows as the table."""
    from .benchmark import evaluate
    from .benchmark.baselines import baseline_model

    bench = _benchmark(task, version)
    baseline = baseline_model(task, model, n_jobs=None)
    if hasattr(baseline, "fit"):
        baseline = _Counted(baseline, 2 * len(bench.grouped.folds))
    report = evaluate(baseline, bench, indices=_finite(task, version), model_name=model)
    _report("done", 1.0)
    return report.to_dict()


def benchmark_folds_csv(task: str = "single_vs_multi", version: str = "0.1.0") -> dict:
    """Every benchmark row with its fold under both schemes, for offline models."""
    bench = _benchmark(task, version)
    finite = set(_finite(task, version))
    fold_of = {}
    for name, scheme in (("grouped", bench.grouped), ("random", bench.random)):
        for fold in scheme.folds:
            for index in fold.test:
                fold_of[(name, index)] = fold.index
    handle = io.StringIO(newline="")
    writer = csv.writer(handle)
    writer.writerow(
        ["composition_key", "family", "label", "grouped_fold", "random_fold",
         "n_elements", "descriptors_finite"]
    )
    for index, row in enumerate(bench.rows):
        writer.writerow(
            [row.composition_key, row.family, row.label,
             fold_of[("grouped", index)], fold_of[("random", index)], row.n_elements,
             int(index in finite)]
        )
    return {
        "filename": f"hea-bench-v{version}-{task}-folds.csv",
        "n_rows": len(bench),
        "text": handle.getvalue(),
    }


def benchmark_score(
    csv_text: str, task: str = "single_vs_multi", version: str = "0.1.0", model_name: str = ""
) -> dict:
    """Score uploaded predictions (composition_key, grouped, random columns)."""
    from .benchmark import score_predictions

    reader = csv.DictReader(io.StringIO(csv_text))
    needed = {"composition_key", "grouped", "random"}
    missing = needed - set(reader.fieldnames or ())
    if missing:
        raise ValueError(
            f"the predictions file needs the columns composition_key, grouped and random; "
            f"missing {sorted(missing)}"
        )
    predictions: dict = {"grouped": {}, "random": {}}
    for record in reader:
        key = (record["composition_key"] or "").strip()
        for scheme in ("grouped", "random"):
            label = (record[scheme] or "").strip()
            if key and label:
                predictions[scheme][key] = label
    report = score_predictions(
        _benchmark(task, version), predictions, model_name=model_name or "uploaded predictions"
    )
    return report.to_dict()


def coverage(task: str = "single_vs_multi", version: str = "0.1.0") -> dict:
    """The conformal coverage study, live (several minutes in the browser)."""
    from .uncertainty.coverage import coverage_study

    return coverage_study(task, version=version, progress=_report)


#: Method name -> function, the whole surface the app can call.
METHODS = {
    function.__name__: function
    for function in (
        engine_info,
        dataset_status,
        peivaste_source,
        peivaste_install,
        dataset_build,
        dataset_query,
        dataset_describe,
        dataset_csv,
        measured_properties,
        properties,
        applicability,
        phase_prediction,
        search,
        campaign_suggest,
        benchmark_summary,
        benchmark_run,
        benchmark_folds_csv,
        benchmark_score,
        coverage,
    )
}


def call(method: str, params_json: str = "{}") -> str:
    """The worker's one entry point: a JSON envelope, never a traceback.

    Returns ``{"ok": true, "result": ...}`` or ``{"ok": false, "error":
    message, "type": exception class}``. Errors carry the library's own
    messages, which already name the fix.
    """
    try:
        if method not in METHODS:
            raise ValueError(f"unknown engine method {method!r}")
        params = json.loads(params_json or "{}")
        result = METHODS[method](**params)
        return json.dumps({"ok": True, "result": _clean(result)}, allow_nan=False)
    except Exception as error:  # noqa: BLE001 - the envelope IS the error channel
        return json.dumps({"ok": False, "error": str(error), "type": type(error).__name__})


__all__ = ["METHODS", "PAGE_CAP", "call", "set_progress"]
