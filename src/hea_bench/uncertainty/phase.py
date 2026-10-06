"""Phase prediction with a conformal prediction set, for one composition.

The model is the baseline random forest (300 trees, seed 0) on this
package's fourteen descriptors, fitted on the descriptor-finite rows of
the benchmark corpus with a family-grouped 20 percent calibration
hold-out, wrapped in a :class:`~hea_bench.uncertainty.ConformalClassifier`.
That is the configuration whose coverage on unseen alloy systems is
measured by :func:`hea_bench.uncertainty.coverage.coverage_study`, so the
measured numbers describe how far these sets can be trusted.

A prediction set lists every phase label the model cannot rule out at
the chosen confidence. One label is a confident answer, several labels
mean the data cannot separate them, and an empty set means no label
reaches the calibrated bar. The corpus domain flag rides along, because
the coverage guarantee assumes the query resembles the calibration
alloys and an unusual alloy breaks that assumption.

Needs the built corpus (see :mod:`hea_bench.corpus`) and scikit-learn
(``pip install "hea-bench[benchmark]"``).
"""

from __future__ import annotations

from functools import lru_cache

from ..composition import Composition, family_of, normalize

_SEED = 0
_TREES = 300
_CALIBRATION_FRACTION = 0.2

#: What each task's labels mean, in plain words, for display surfaces.
TASK_DESCRIPTIONS = {
    "single_vs_multi": "whether the alloy forms a single-phase solid solution",
    "phase4": "which structure forms: BCC, FCC or HCP solid solution, or multi-phase",
}


@lru_cache(maxsize=4)
def _fitted(task: str, version: str):
    """Fit (model, conformal, n_proper, n_calibration) once per task and version."""
    from sklearn.ensemble import RandomForestClassifier

    from ..benchmark import load_benchmark
    from ..benchmark.corpus import descriptor_matrix, finite_descriptor_indices
    from .conformal import ConformalClassifier
    from .splitting import grouped_calibration_split

    bench = load_benchmark(task=task, version=version)
    finite = list(finite_descriptor_indices(bench))
    features = descriptor_matrix([bench.rows[i].composition for i in finite])
    labels = [bench.rows[i].label for i in finite]
    families = [bench.rows[i].family for i in finite]
    proper, calibration = grouped_calibration_split(
        families, fraction=_CALIBRATION_FRACTION, seed=_SEED
    )
    model = RandomForestClassifier(n_estimators=_TREES, random_state=_SEED)
    model.fit([features[i] for i in proper], [labels[i] for i in proper])
    conformal = ConformalClassifier(model).fit_calibrate(
        [features[i] for i in calibration], [labels[i] for i in calibration]
    )
    return model, conformal, len(proper), len(calibration)


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
        measures, training sizes, and plain-language ``warnings``.

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
    model, conformal, n_proper, n_calibration = _fitted(task, version)
    probabilities = {
        str(label): float(p) for label, p in zip(model.classes_, model.predict_proba([vector])[0])
    }
    prediction_set = sorted(conformal.predict_set([vector], alpha=alpha)[0])
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
            "this alloy is unlike the dataset, so the coverage guarantee is weakest here"
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
        "n_training": n_proper,
        "n_calibration": n_calibration,
        "corpus_version": version,
        "model": (
            f"random forest, {_TREES} trees, seed {_SEED}, family-grouped "
            f"{_CALIBRATION_FRACTION:.0%} calibration hold-out"
        ),
        "warnings": warnings,
    }


@lru_cache(maxsize=4)
def _domain_for(version: str):
    from ..corpus import load_corpus
    from .applicability import fit_domain

    return fit_domain(load_corpus(version=version))


def _corpus_domain(version: str):
    """The corpus domain model; the shared default for the reference corpus."""
    if version == "0.1.0":
        from .applicability import default_domain

        domain = default_domain()
        if domain is not None:
            return domain
    return _domain_for(version)


__all__ = ["TASK_DESCRIPTIONS", "predict_phase_set"]
