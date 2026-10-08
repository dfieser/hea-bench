"""Phase prediction with a conformal prediction set, for one composition.

The model is the baseline random forest (300 trees, seed 0) on this
package's fourteen descriptors, fitted on every descriptor-finite row of
the benchmark corpus and wrapped in a
:class:`~hea_bench.uncertainty.ConformalClassifier`. Its calibration
scores come from five-fold cross-validation over the frozen system
split: every alloy is scored by a forest that never saw its alloy
system, so the sets are calibrated for systems the model has not seen.
Alloys with fewer than four elements are calibrated apart from the
multi-principal alloys (:func:`calibration_group`), because the two
populations err differently and one pooled threshold over-covers the
first and under-covers the second. That is the procedure whose coverage
on unseen alloy systems :func:`hea_bench.uncertainty.coverage.coverage_study`
measures, so the measured numbers describe how far these sets can be
trusted.

A prediction set lists every phase label the model cannot rule out at
the chosen confidence. One label is a confident answer, several labels
mean the data cannot separate them, and an empty set means no label
reaches the calibrated bar. The corpus domain flag rides along, because
the coverage guarantee assumes the query resembles the calibration
alloys and an unusual alloy breaks that assumption, and so does what
the coverage study measured (``measured_coverage``).

Needs the built corpus (see :mod:`hea_bench.corpus`) and scikit-learn
(``pip install "hea-bench[benchmark]"``).
"""

from __future__ import annotations

from functools import lru_cache

from ..composition import Composition, accepts_formula, family_of, normalize

_SEED = 0
_TREES = 300

#: What each task's labels mean, in plain words, for display surfaces.
TASK_DESCRIPTIONS = {
    "single_vs_multi": "whether the alloy forms a single-phase solid solution",
    "phase4": "which structure forms: BCC, FCC or HCP solid solution, or multi-phase",
}


def calibration_group(composition) -> str:
    """The calibration group of a composition, by its number of elements."""
    return "fewer_than_four" if len(composition) < 4 else "four_or_more"


def system_fold_positions(bench, rows) -> list[tuple[list[int], list[int]]]:
    """The frozen system-split folds as positions into ``rows``.

    ``rows`` is a list of benchmark row indices (the descriptor-finite
    ones); rows outside it are dropped from every fold.
    """
    position = {row: p for p, row in enumerate(rows)}
    return [
        (
            [position[i] for i in fold.train if i in position],
            [position[i] for i in fold.test if i in position],
        )
        for fold in bench.grouped.folds
    ]


@lru_cache(maxsize=4)
def _fitted(task: str, version: str):
    """(model, conformal, n_training, n_calibration), fitted once per task and version."""
    from .._model_cache import cached

    return cached(f"phase-{task}-v{version}", lambda: _fit(task, version))


def _fit(task: str, version: str):
    from sklearn.ensemble import RandomForestClassifier

    from .._model_cache import FOREST_JOBS
    from ..benchmark import load_benchmark
    from ..benchmark.corpus import descriptor_matrix, finite_descriptor_indices
    from .conformal import ConformalClassifier, cross_val_scores

    bench = load_benchmark(task=task, version=version)
    finite = list(finite_descriptor_indices(bench))
    features = descriptor_matrix([bench.rows[i].composition for i in finite])
    labels = [bench.rows[i].label for i in finite]
    groups = [calibration_group(bench.rows[i].composition) for i in finite]

    def make_forest():
        return RandomForestClassifier(n_estimators=_TREES, random_state=_SEED, n_jobs=FOREST_JOBS)

    scores = cross_val_scores(make_forest, features, labels, system_fold_positions(bench, finite))
    model = make_forest().fit(features, labels)
    conformal = ConformalClassifier(model).calibrate_scores(scores, groups)
    return model, conformal, len(finite), len(scores)


@accepts_formula
def predict_phase_set(
    composition: Composition,
    *,
    task: str = "single_vs_multi",
    alpha: float = 0.1,
    version: str = "0.1.0",
) -> dict:
    """Predict the phase of one composition with a conformal prediction set.

    Parameters
    ----------
    composition
        Mole-fraction dict (amounts normalize internally).
    task
        ``"single_vs_multi"`` (single-phase solid solution or not) or
        ``"phase4"`` (multi-phase, BCC, FCC or HCP).
    alpha
        Miscoverage level; 0.1 asks for a set that contains the true
        label about 90 percent of the time on alloys like the
        calibration set.
    version
        Corpus version to train on. The published numbers use ``"0.1.0"``.

    Returns
    -------
    dict
        ``prediction_set`` (sorted labels), ``probabilities`` per label,
        ``most_likely``, the corpus ``in_domain`` flag and ``novelty``
        measures, training sizes, plain-language ``warnings``, and
        ``measured_coverage``: how often sets at this confidence held the
        true label on unseen alloy systems inside and outside the
        dataset's range in the coverage study (None for a version or a
        confidence the study did not measure).

    Raises
    ------
    ValueError
        Unknown task, or a composition whose descriptors are not all
        computable (an element outside the tables, or a singular value).
    FileNotFoundError
        The corpus is not built; the message gives the build commands.
    """
    from ..benchmark.corpus import TASKS
    from ..descriptors.backend import matrix_vector

    if task not in TASKS:
        raise ValueError(f"unknown task {task!r}; expected one of {sorted(TASKS)}")
    comp = normalize(composition)
    vector = matrix_vector(comp)
    if vector is None:
        raise ValueError(
            f"phase prediction needs all 14 descriptor features and at least one is not "
            f"computable for {family_of(comp)} (an element outside the descriptor tables, "
            f"or a singular descriptor such as Omega at zero mixing enthalpy)"
        )
    model, conformal, n_training, n_calibration = _fitted(task, version)
    probabilities = {
        str(label): float(p) for label, p in zip(model.classes_, model.predict_proba([vector])[0])
    }
    group = calibration_group(comp)
    prediction_set = sorted(conformal.predict_set([vector], alpha=alpha, groups=[group])[0])
    most_likely = max(sorted(probabilities), key=lambda label: probabilities[label])

    domain = _corpus_domain(version)
    novelty = domain.novelty(comp)

    warnings: list[str] = []
    if not prediction_set:
        warnings.append(
            "the set is empty: no phase reaches the calibrated probability bar at this "
            "confidence, which is the model saying none of its labels is credible here"
        )
    elif len(prediction_set) == len(probabilities):
        warnings.append(
            "the set holds every phase: at this confidence the model cannot rule any out"
        )
    if not novelty["in_domain"]:
        warnings.append(
            "this alloy is outside the dataset's range, so the coverage guarantee is weakest here"
        )
    from .coverage import MEASURED_COVERAGE

    measured = (
        MEASURED_COVERAGE[task].get(round(1.0 - alpha, 4)) if version == "0.1.0" else None
    )
    return {
        "task": task,
        "task_description": TASK_DESCRIPTIONS[task],
        "alpha": alpha,
        "target_coverage": 1.0 - alpha,
        "prediction_set": prediction_set,
        "probabilities": probabilities,
        "most_likely": most_likely,
        "in_domain": novelty["in_domain"],
        "novelty": novelty,
        "n_training": n_training,
        "n_calibration": conformal.n_calibration(group),
        "corpus_version": version,
        "measured_coverage": None if measured is None else {
            "in_domain": measured[0],
            "out_of_domain": measured[1],
            "source": "docs/uncertainty-coverage.md",
        },
        "model": (
            f"random forest, {_TREES} trees, seed {_SEED}, trained on every alloy and "
            f"calibrated by five-fold cross-validation over whole alloy systems, "
            f"alloys with {'fewer than four' if group == 'fewer_than_four' else 'four or more'} "
            f"elements on their own ({n_calibration} cross-validation scores in all)"
        ),
        "warnings": warnings,
    }


@lru_cache(maxsize=4)
def _domain_for(version: str):
    from .._model_cache import cached
    from ..corpus import load_corpus
    from .applicability import fit_domain

    return cached(f"domain-v{version}", lambda: fit_domain(load_corpus(version=version)))


def _corpus_domain(version: str):
    """The corpus domain model; the shared default for the reference corpus."""
    if version == "0.1.0":
        from .applicability import default_domain

        domain = default_domain()
        if domain is not None:
            return domain
    return _domain_for(version)


__all__ = ["TASK_DESCRIPTIONS", "predict_phase_set"]
