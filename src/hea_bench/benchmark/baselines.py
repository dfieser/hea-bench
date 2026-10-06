"""The published baseline models, as library objects.

Four kinds of baseline, each scored under both frozen splits by
:func:`hea_bench.benchmark.evaluate`:

``majority-class``
    The floor. Predicts the most common training label.
``rule:*``
    The canonical empirical screens already in this package, used as
    published, with no fitting (Zhang delta and Yang Omega for the
    single-phase task, Guo VEC for the phase-structure task).
``random-forest`` and ``gradient-boosting``
    scikit-learn defaults apart from a fixed seed, fitted on this
    package's own fourteen descriptors, so the comparison is against the
    same physics the rules use rather than a different feature set.

``tools/benchmark_baselines.py`` writes the committed results table from
these objects, and the web app re-runs them in the browser, so both run
the same code. Needs scikit-learn for the two fitted models
(``pip install "hea-bench[benchmark]"``).
"""

from __future__ import annotations

from collections.abc import Sequence

from ..composition import Composition
from ..rules import guo_vec, yang_omega, zhang_delta
from .corpus import descriptor_matrix
from .evaluate import MajorityClass

#: Fixed so a rerun reproduces the table. Any change here changes every
#: number below it.
FOREST_SEED = 0

#: Composition (as a sorted item tuple) -> descriptor row. Every fold of
#: every scheme of every fitted model featurizes the same ~7k corpus
#: compositions; computing each row once cuts minutes from a run without
#: touching a single value.
_MATRIX_CACHE: dict[tuple, list[float]] = {}


def _cached_matrix(compositions: Sequence[Composition]) -> list[list[float]]:
    rows = []
    for comp in compositions:
        key = tuple(sorted(comp.items()))
        row = _MATRIX_CACHE.get(key)
        if row is None:
            row = descriptor_matrix([comp])[0]
            _MATRIX_CACHE[key] = row
        rows.append(row)
    return rows


class DescriptorModel:
    """Adapter fitting any scikit-learn classifier on this package's descriptors."""

    def __init__(self, estimator, name: str) -> None:
        self.estimator = estimator
        self.name = name

    def fit(self, compositions: Sequence[Composition], labels: Sequence[str]) -> DescriptorModel:
        self.estimator.fit(_cached_matrix(compositions), list(labels))
        return self

    def predict(self, compositions: Sequence[Composition]) -> list[str]:
        return list(self.estimator.predict(_cached_matrix(compositions)))


def _rule_single_vs_multi(rule) -> object:
    def predict(composition: Composition) -> str:
        return rule.predict(composition)

    predict.__name__ = f"rule:{rule.__name__.rsplit('.', 1)[-1]}"
    return predict


def _rule_guo_phase4(composition: Composition) -> str:
    # Guo's VEC bounds emit FCC, BCC, or mixed. "mixed" is the rule
    # saying no single phase is expected, which is what multi-phase
    # means in this taxonomy. The rule cannot emit HCP at all, so it
    # scores zero recall on that class by construction.
    verdict = guo_vec.predict(composition)
    return "multi-phase" if verdict == "mixed" else verdict


_rule_guo_phase4.__name__ = "rule:guo_vec"

#: Baseline names per task, in table order.
BASELINE_NAMES = {
    "single_vs_multi": (
        "majority-class",
        "rule:zhang_delta",
        "rule:yang_omega",
        "random-forest",
        "gradient-boosting",
    ),
    "phase4": ("majority-class", "rule:guo_vec", "random-forest", "gradient-boosting"),
}


def build_models(task: str, *, n_jobs: int | None = -1) -> list[object]:
    """Baselines for one task, all scored on the same rows so they compare.

    ``n_jobs`` goes to the random forest only and never changes a
    prediction; the browser engine passes None because it has one thread.
    """
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier

    if task not in BASELINE_NAMES:
        raise ValueError(f"unknown task {task!r}; expected one of {sorted(BASELINE_NAMES)}")
    models: list[object] = [MajorityClass()]
    if task == "single_vs_multi":
        models.append(_rule_single_vs_multi(zhang_delta))
        models.append(_rule_single_vs_multi(yang_omega))
    else:
        models.append(_rule_guo_phase4)
    models.append(
        DescriptorModel(
            RandomForestClassifier(n_estimators=300, random_state=FOREST_SEED, n_jobs=n_jobs),
            "random-forest",
        )
    )
    models.append(
        DescriptorModel(
            GradientBoostingClassifier(random_state=FOREST_SEED),
            "gradient-boosting",
        )
    )
    return models


def baseline_model(task: str, name: str, *, n_jobs: int | None = -1) -> object:
    """One baseline by its table name, for example ``"random-forest"``."""
    if name not in BASELINE_NAMES.get(task, ()):
        raise ValueError(
            f"unknown baseline {name!r} for task {task!r}; expected one of "
            f"{list(BASELINE_NAMES.get(task, ()))}"
        )
    if name == "majority-class":
        return MajorityClass()
    if name == "rule:zhang_delta":
        return _rule_single_vs_multi(zhang_delta)
    if name == "rule:yang_omega":
        return _rule_single_vs_multi(yang_omega)
    if name == "rule:guo_vec":
        return _rule_guo_phase4
    for model in build_models(task, n_jobs=n_jobs):
        if getattr(model, "name", None) == name:
            return model
    raise AssertionError(f"baseline {name!r} listed but not built")  # pragma: no cover


__all__ = [
    "BASELINE_NAMES",
    "FOREST_SEED",
    "DescriptorModel",
    "baseline_model",
    "build_models",
]
