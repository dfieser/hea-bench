"""The paired benchmark: summary, live baselines, folds, scoring, coverage.

The MCP benchmark tools and the app's Benchmark tab both call these, so
the two return the same numbers. ``progress`` is an optional
``(message, fraction)`` callback, which the app's engine passes to drive
its progress bar.
"""

from __future__ import annotations

import csv
import io
import json
from functools import lru_cache

from .. import _paths
from ._payload import say


@lru_cache(maxsize=4)
def load(task: str, version: str):
    from ..benchmark import load_benchmark

    return load_benchmark(task=task, version=version)


@lru_cache(maxsize=4)
def finite_indices(task: str, version: str) -> tuple[int, ...]:
    from .._model_cache import cached
    from ..benchmark import finite_descriptor_indices

    return cached(
        f"finite-{task}-v{version}", lambda: finite_descriptor_indices(load(task, version))
    )


def summary(task: str = "single_vs_multi", version: str = "0.1.0", progress=None) -> dict:
    """Split balance, family overlap, digest check and the published table."""
    from ..benchmark.baselines import BASELINE_NAMES
    from ..benchmark.frozen import verify_split_digests

    say(progress, "loading the benchmark", 0.2)
    bench = load(task, version)
    published = None
    baselines = _paths.baselines_json()
    if version == "0.1.0" and baselines.exists():
        stored = json.loads(baselines.read_text(encoding="utf-8"))
        published = {
            "results": stored["results"].get(task),
            "coverage": stored["coverage"].get(task),
        }
    return {
        "described": bench.describe(),
        "digests": verify_split_digests(bench),
        "n_evaluated": len(finite_indices(task, version)),
        "baselines": list(BASELINE_NAMES[task]),
        "published": published,
    }


class _Counted:
    """A baseline wrapper that reports progress per fold fit and leaves predictions unchanged."""

    def __init__(self, model, total: int, progress=None) -> None:
        self._model = model
        self._total = total
        self._progress = progress
        self._done = 0
        self.name = getattr(model, "name", getattr(model, "__name__", "model"))

    def fit(self, compositions, labels):
        say(self._progress, f"fitting fold {self._done + 1} of {self._total}", self._done / self._total)
        self._model.fit(compositions, labels)
        self._done += 1
        return self

    def predict(self, compositions):
        return self._model.predict(compositions)


def run(model: str, task: str = "single_vs_multi", version: str = "0.1.0", progress=None) -> dict:
    """Score one published baseline live, on the same rows as the table."""
    from ..benchmark import evaluate
    from ..benchmark.baselines import baseline_model

    bench = load(task, version)
    baseline = baseline_model(task, model, n_jobs=None)
    if hasattr(baseline, "fit"):
        baseline = _Counted(baseline, 2 * len(bench.grouped.folds), progress)
    report = evaluate(baseline, bench, indices=finite_indices(task, version), model_name=model)
    say(progress, "done", 1.0)
    return report.to_dict()


def folds_csv(task: str = "single_vs_multi", version: str = "0.1.0") -> dict:
    """Every benchmark row with its fold under both schemes, for offline models."""
    bench = load(task, version)
    finite = set(finite_indices(task, version))
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


def score_csv(
    csv_text: str, task: str = "single_vs_multi", version: str = "0.1.0", model_name: str = ""
) -> dict:
    """Score uploaded predictions (composition_key, grouped, random columns)."""
    from ..benchmark import score_predictions

    reader = csv.DictReader(io.StringIO(csv_text))
    needed = {"composition_key", "grouped", "random"}
    missing = needed - set(reader.fieldnames or ())
    if missing:
        raise ValueError(
            f"the predictions file needs the columns composition_key, grouped and random. "
            f"Missing: {sorted(missing)}"
        )
    predictions: dict = {"grouped": {}, "random": {}}
    for record in reader:
        key = (record["composition_key"] or "").strip()
        for scheme in ("grouped", "random"):
            label = (record[scheme] or "").strip()
            if key and label:
                predictions[scheme][key] = label
    report = score_predictions(
        load(task, version), predictions, model_name=model_name or "uploaded predictions"
    )
    return report.to_dict()


def coverage(task: str = "single_vs_multi", version: str = "0.1.0", progress=None) -> dict:
    """The conformal coverage study, live (several minutes in the browser)."""
    from ..uncertainty.coverage import coverage_study

    return coverage_study(task, version=version, progress=progress)
