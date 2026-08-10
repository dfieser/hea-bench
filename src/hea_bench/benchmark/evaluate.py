"""Paired evaluation: the same model, the same folds, two partition rules.

:func:`evaluate` runs a model twice over the same rows with the same
fold count, once under the composition-family-grouped split and once
under the random split, and reports both side by side. The difference
between them is the headline output. A model that scores far better
under the random split is not better at predicting phases, it is better
at interpolating between stoichiometries it has already seen.

What counts as a model
----------------------
Two shapes are accepted.

A **trainable model** exposes ``fit(compositions, labels)`` and
``predict(compositions)``, where ``compositions`` is a sequence of
mole-fraction dicts. It is refitted from scratch on each fold's training
rows. Any featurization is the model's own business, which keeps this
module free of both a feature contract and a numerical dependency.
:func:`hea_bench.benchmark.descriptor_matrix` is there for models that
want this package's descriptors.

A **fixed predictor** is any callable mapping one composition to one
label, which is what the empirical rules are. It is never fitted.

Reading the numbers for a fixed predictor
-----------------------------------------
A predictor with nothing to learn produces the same label for a given
alloy no matter which fold that alloy is in, so its grouped and random
scores agree to within fold-composition noise and its inflation gap is
near zero. That is not evidence the rule generalizes well. It only says
a rule with no fitted parameters has nothing to leak. The gap measures
leakage, and an unfitted rule cannot leak. Compare rules against models
on the grouped column, and read the gap only for models that learn.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .. import __version__
from ..composition import Composition
from . import metrics as _metrics
from .corpus import Benchmark, load_benchmark
from .metrics import METRIC_NAMES, FoldMetrics
from .splits import SplitScheme


@dataclass(frozen=True)
class SchemeResult:
    """One split scheme's per-fold and aggregate scores."""

    scheme: str
    digest: str
    folds: tuple[FoldMetrics, ...]
    summary: dict

    def to_dict(self) -> dict:
        return {
            "scheme": self.scheme,
            "digest": self.digest,
            "folds": [fold.to_dict() for fold in self.folds],
            **self.summary,
        }


@dataclass(frozen=True)
class EvaluationReport:
    """Paired grouped and random results, with the inflation between them.

    ``inflation`` is ``random - grouped`` per metric. Positive means the
    random split flattered the model.
    """

    model_name: str
    task: str
    corpus_version: str
    hea_bench_version: str
    n_rows_evaluated: int
    grouped: SchemeResult
    random: SchemeResult
    inflation: dict

    def to_dict(self) -> dict:
        return {
            "model": self.model_name,
            "task": self.task,
            "corpus_version": self.corpus_version,
            "hea_bench_version": self.hea_bench_version,
            "n_rows_evaluated": self.n_rows_evaluated,
            "grouped": self.grouped.to_dict(),
            "random": self.random.to_dict(),
            "inflation": self.inflation,
        }

    def table(self) -> str:
        """Side-by-side text table, the intended way to read one report."""
        header = (
            f"{self.model_name}  |  task={self.task}  "
            f"corpus=v{self.corpus_version}  n={self.n_rows_evaluated}"
        )
        lines = [
            header,
            "-" * len(header),
            f"{'metric':<20}{'grouped (honest)':>22}{'random (inflated)':>22}{'gap':>10}",
        ]
        for name in METRIC_NAMES:
            grouped_mean = self.grouped.summary[f"{name}_mean"]
            grouped_se = self.grouped.summary[f"{name}_se"]
            random_mean = self.random.summary[f"{name}_mean"]
            random_se = self.random.summary[f"{name}_se"]
            lines.append(
                f"{name:<20}"
                f"{grouped_mean:>15.3f} +-{grouped_se:<5.3f}"
                f"{random_mean:>15.3f} +-{random_se:<5.3f}"
                f"{self.inflation[name]:>+10.3f}"
            )
        return "\n".join(lines)


def _is_trainable(model: object) -> bool:
    return callable(getattr(model, "fit", None)) and callable(getattr(model, "predict", None))


def _model_name(model: object) -> str:
    name = getattr(model, "name", None)
    if isinstance(name, str) and name:
        return name
    return type(model).__name__ if _is_trainable(model) else getattr(model, "__name__", repr(model))


def _predict_fold(
    model: object,
    train_compositions: Sequence[Composition],
    train_labels: Sequence[str],
    test_compositions: Sequence[Composition],
) -> list[str]:
    if _is_trainable(model):
        # Refit from scratch on this fold. A model whose fit does not
        # fully reset prior state would carry the previous fold's
        # training rows into this one, which is leakage of a second kind.
        model.fit(list(train_compositions), list(train_labels))
        return [str(label) for label in model.predict(list(test_compositions))]
    predictor: Callable[[Composition], str] = model  # type: ignore[assignment]
    return [str(predictor(composition)) for composition in test_compositions]


def _run_scheme(
    model: object,
    benchmark: Benchmark,
    scheme: SplitScheme,
    active: Sequence[int],
) -> SchemeResult:
    active_set = set(active)
    rows = benchmark.rows
    fold_scores: list[FoldMetrics] = []

    for fold in scheme.folds:
        test_indices = [index for index in fold.test if index in active_set]
        train_indices = [index for index in fold.train if index in active_set]
        if not test_indices or not train_indices:
            raise ValueError(
                f"{scheme.name} fold {fold.index} has {len(train_indices)} train and "
                f"{len(test_indices)} test rows after filtering; the filter removed too much "
                f"to evaluate"
            )
        predictions = _predict_fold(
            model,
            [rows[index].composition for index in train_indices],
            [rows[index].label for index in train_indices],
            [rows[index].composition for index in test_indices],
        )
        observations = [rows[index].label for index in test_indices]
        if len(predictions) != len(observations):
            raise ValueError(
                f"model returned {len(predictions)} predictions for "
                f"{len(observations)} test rows in {scheme.name} fold {fold.index}"
            )
        fold_scores.append(_metrics.score(predictions, observations))

    return SchemeResult(
        scheme=scheme.name,
        digest=scheme.digest,
        folds=tuple(fold_scores),
        summary=_metrics.aggregate(fold_scores),
    )


def evaluate(
    model: object,
    benchmark: Benchmark | None = None,
    *,
    descriptor_ready_only: bool = False,
    indices: Sequence[int] | None = None,
    model_name: str | None = None,
) -> EvaluationReport:
    """Score a model under both split schemes and report the gap.

    Parameters
    ----------
    model
        A trainable model (``fit`` and ``predict``) or a callable mapping
        one composition to one label. See the module docstring.
    benchmark
        A loaded benchmark. Loaded with defaults if omitted.
    descriptor_ready_only
        Restrict to rows whose elements are covered by both the element
        table and the Miedema pair table. Fold membership is unaffected:
        rows are removed from folds, never moved between them, so a
        filtered run is still testing on the same partition of chemistry.
    indices
        Explicit row positions to evaluate on, overriding
        ``descriptor_ready_only``. Use
        :func:`hea_bench.benchmark.finite_descriptor_indices` for models
        fitted on descriptors, since element coverage alone still admits
        rows where Omega is singular. Computing it once and passing it
        here also avoids recomputing every descriptor per model.
    model_name
        Label for the report. Taken from the model's ``name`` attribute
        or its type if omitted.

    Raises
    ------
    ValueError
        If the model is neither trainable nor callable, or if filtering
        empties a fold.
    """
    if not _is_trainable(model) and not callable(model):
        raise ValueError(
            "model must expose fit/predict or be callable on a single composition"
        )
    if benchmark is None:
        benchmark = load_benchmark()

    if indices is None:
        active = benchmark.subset_indices(descriptor_ready_only=descriptor_ready_only)
    else:
        active = tuple(indices)
        if not active:
            raise ValueError("indices is empty; nothing to evaluate")
    grouped = _run_scheme(model, benchmark, benchmark.grouped, active)
    randomized = _run_scheme(model, benchmark, benchmark.random, active)

    inflation = {
        name: randomized.summary[f"{name}_mean"] - grouped.summary[f"{name}_mean"]
        for name in METRIC_NAMES
    }

    return EvaluationReport(
        model_name=model_name or _model_name(model),
        task=benchmark.task,
        corpus_version=benchmark.corpus_version,
        hea_bench_version=__version__,
        n_rows_evaluated=len(active),
        grouped=grouped,
        random=randomized,
        inflation=inflation,
    )


class MajorityClass:
    """The floor every other model has to clear.

    Predicts whichever label was most common in the training fold. On an
    imbalanced corpus its accuracy looks respectable and its balanced
    accuracy is ``1/C``, which is the clearest demonstration of why
    accuracy alone is the wrong headline metric here.
    """

    name = "majority-class"

    def __init__(self) -> None:
        self._label: str | None = None

    def fit(self, compositions: Sequence[Composition], labels: Sequence[str]) -> MajorityClass:
        counts: dict[str, int] = {}
        for label in labels:
            counts[label] = counts.get(label, 0) + 1
        # Alphabetical tie-break so a tie cannot make the result depend
        # on dict ordering.
        self._label = max(sorted(counts), key=lambda label: counts[label])
        return self

    def predict(self, compositions: Sequence[Composition]) -> list[str]:
        if self._label is None:
            raise ValueError("MajorityClass.predict called before fit")
        return [self._label] * len(compositions)


__all__ = [
    "EvaluationReport",
    "MajorityClass",
    "SchemeResult",
    "evaluate",
]
