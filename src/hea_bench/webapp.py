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

import json

from . import __version__, service
from ._json import strict_json
from .service._payload import PAGE_CAP, stamp

_progress = None


def set_progress(callback) -> None:
    """Install the worker's ``(message, fraction)`` progress callback."""
    global _progress
    _progress = callback


def _report(message: str, fraction: float) -> None:
    if _progress is not None:
        _progress(message, float(fraction))


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
    return service.dataset.status()


def dataset_build(version: str = "0.2.0") -> dict:
    """Build one corpus version from the raw sources, exactly as the CLI
    does. The build goes into the directory the loaders read, which
    honours HEA_BENCH_BENCHMARK_DIR, where the app keeps its persistent
    copy."""
    manifest = service.dataset.build(version, progress=_report)
    _WARMED.clear()
    return manifest


def _clear_caches() -> None:
    _WARMED.clear()
    service.dataset.clear_caches()


def dataset_query(
    filters: dict | None = None, version: str = "0.2.0", offset: int = 0, limit: int = 100
) -> dict:
    """One page of a filtered corpus slice, every row with full provenance."""
    return service.dataset.page(filters, version, offset, limit)


def dataset_describe(filters: dict | None = None, version: str = "0.2.0") -> dict:
    """Counts by phase, element count, source and family for a slice."""
    return service.dataset.describe(filters, version)


def dataset_csv(filters: dict | None = None, version: str = "0.2.0") -> dict:
    """The slice in the consolidated-CSV schema, as text for a download."""
    return service.dataset.csv_text(filters, version)


# -- measured properties (Borg 2020) -------------------------------------------


def measured_properties(prop: str = "hardness", contains: list | None = None) -> dict:
    """The Borg 2020 measurements the hardness model trains on, or the
    measured densities the rule-of-mixtures estimate is checked against,
    optionally only alloys that contain every element in ``contains``."""
    return service.dataset.measured(prop, contains)


# -- single-composition predictions --------------------------------------------


def properties(
    composition, alpha: float = 0.1, processing: str | None = None, names: list | None = None
) -> dict:
    """Every property for one composition. A property that cannot be
    computed carries its reason instead of hiding the others."""
    return service.predictions.properties(composition, alpha, processing, names)


def applicability(composition, version: str = "0.1.0") -> dict:
    """The corpus domain flag and its novelty components."""
    return service.predictions.applicability(composition, version)


def phase_prediction(
    composition, task: str = "single_vs_multi", alpha: float = 0.1, version: str = "0.1.0"
) -> dict:
    """Conformal phase prediction set for one composition."""
    return service.predictions.phase_prediction(composition, task, alpha, version, progress=_report)


# -- design ---------------------------------------------------------------------


def search(**params) -> dict:
    """The constrained alloy search, with the MCP tool's caps and schema."""
    _report("screening the composition lattice", 0.1)
    return stamp(service.design.design_search(**params))


def campaign_suggest(campaign: dict, n: int = 5, strategy: str = "ei") -> dict:
    """Next suggestions for a campaign file's contents (schema 1).

    Observation compositions may be formulas, which this function
    normalizes. The response carries the campaign back in canonical
    form, which is what the app saves.
    """
    return service.design.suggest_inline(campaign, n, strategy, progress=_report)


# -- benchmark ------------------------------------------------------------------


def benchmark_summary(task: str = "single_vs_multi", version: str = "0.1.0") -> dict:
    """Split balance, family overlap, digest check and the published table."""
    return service.benchmark.summary(task, version, progress=_report)


def benchmark_run(model: str, task: str = "single_vs_multi", version: str = "0.1.0") -> dict:
    """Score one published baseline live, on the same rows as the table."""
    return service.benchmark.run(model, task, version, progress=_report)


def benchmark_folds_csv(task: str = "single_vs_multi", version: str = "0.1.0") -> dict:
    """Every benchmark row with its fold under both schemes, for offline models."""
    return service.benchmark.folds_csv(task, version)


def benchmark_score(
    csv_text: str, task: str = "single_vs_multi", version: str = "0.1.0", model_name: str = ""
) -> dict:
    """Score uploaded predictions (composition_key, grouped, random columns)."""
    return service.benchmark.score_csv(csv_text, task, version, model_name)


def coverage(task: str = "single_vs_multi", version: str = "0.1.0") -> dict:
    """The conformal coverage study, live (several minutes in the browser)."""
    return service.benchmark.coverage(task, version, progress=_report)


# -- background preparation -------------------------------------------------------
#
# The worker runs one step whenever no request from the page is waiting,
# so the tabs find their data loaded and their models fitted, and a click
# never waits behind more than one step. Models land in
# HEA_BENCH_MODEL_CACHE, so a returning visitor loads them instead.

_WARMED: set[str] = set()


def _warm_plan() -> list[str]:
    from .benchmark.consolidate import SOURCES_BY_VERSION

    built = dataset_status()["built"]
    # Builds first: a build clears every cache the later steps fill.
    plan = [f"build:{v}" for v in SOURCES_BY_VERSION if not built[v]]
    return plan + [
        "hardness", "phase:single_vs_multi", "phase:phase4", "dataset:0.2.0", "benchmark:single_vs_multi",
    ]


def warm_next() -> str | None:
    """The next background preparation step, or None when all are done."""
    return next((step for step in _warm_plan() if step not in _WARMED), None)


def warm(step: str) -> dict:
    """Run one background preparation step named by :func:`warm_next`."""
    kind, _, arg = step.partition(":")
    try:
        if kind == "build":
            dataset_build(arg)
        elif kind == "hardness":
            from .properties.hardness import fitted_model

            fitted_model(None)
        elif kind == "phase":
            from .uncertainty import phase

            phase.fitted_model(arg, "0.1.0")
            phase.corpus_domain("0.1.0")
        elif kind == "benchmark":
            service.benchmark.finite_indices(arg, "0.1.0")
        elif kind == "dataset":
            service.dataset.cached_corpus(arg)
        else:
            raise ValueError(f"unknown preparation step {step!r}")
    finally:
        # Done or failed, never retried in the background: a failing step
        # reports its error when the page asks for that feature.
        _WARMED.add(step)
    return {"step": step}


#: Method name -> function, the whole surface the app can call.
METHODS = {
    function.__name__: function
    for function in (
        engine_info,
        dataset_status,
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
        warm_next,
        warm,
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
        return json.dumps({"ok": True, "result": strict_json(result)}, allow_nan=False)
    except Exception as error:  # noqa: BLE001 - the envelope IS the error channel
        return json.dumps({"ok": False, "error": str(error), "type": type(error).__name__})


__all__ = ["METHODS", "PAGE_CAP", "call", "set_progress"]
