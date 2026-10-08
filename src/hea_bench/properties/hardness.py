"""Tier B hardness surrogate over the Borg room-temperature HV records.

The model is deliberately unexciting: the baseline random forest
(300 trees, seed 0) on this package's own 14 descriptors, trained on
every usable alloy, plus a domain model fitted on the same
compositions. The conformal interval's half-width comes from the errors
of five-fold cross-validation that holds out whole alloy systems, so
every alloy calibrates, the interval is not narrowed by stoichiometric
near-duplicates, and it describes the error on systems the model has
not seen. Its job is a screening estimate with an honest interval, not
a hardness theory; the held-out error and the processing-state mix are
in the model card, ``docs/property-hardness.md``, and whether the
interval supports ranking close candidates is stated there rather than
implied.

Everything is fitted on demand per process (seeded, cached), because
shipping a pickled model would freeze a scikit-learn version into the
wheel; the ``properties`` extra pins the series instead.
"""

from __future__ import annotations

import math
from functools import lru_cache

from ..composition import Composition, accepts_formula, family_of, normalize
from ..descriptors.backend import matrix_vector
from ..uncertainty import ConformalRegressor, fit_domain
from ..uncertainty.applicability import DomainRow
from ..uncertainty.conformal import cross_val_scores
from .borg import hardness_records

#: Below this many usable training alloys the model refuses to exist.
N_MIN = 50

_SEED = 0
_TREES = 300
#: Cross-validation folds that set the interval, whole systems per fold.
_FOLDS = 5


class PropertyUnavailableError(RuntimeError):
    """A property, or the capability to compute it, is not available.

    The message names the missing install, the data floor, or the
    omission reason; it never hands back a silent guess.
    """


def _require_random_forest():
    try:
        from sklearn.ensemble import RandomForestRegressor
    except ImportError as exc:
        raise PropertyUnavailableError(
            "the hardness surrogate needs scikit-learn, which is not "
            'installed. Install it with: pip install "hea-bench[properties]"'
        ) from exc
    return RandomForestRegressor


@lru_cache(maxsize=8)
def _fitted(processing: str | None):
    """(model, conformal, domain, n), fitted once per processing filter."""
    from .._model_cache import cached

    random_forest_cls = _require_random_forest()
    return cached(f"hardness-{processing or 'pooled'}", lambda: _fit(processing, random_forest_cls))


def _fit(processing: str | None, random_forest_cls):

    records = [
        record
        for record in hardness_records()
        if processing is None or record.processing == processing
    ]
    usable = []
    features = []
    for record in records:
        vector = matrix_vector(record.composition)
        if vector is not None:
            usable.append(record)
            features.append(vector)

    if len(usable) < N_MIN:
        subset = f"processing={processing!r}" if processing else "the pooled set"
        raise PropertyUnavailableError(
            f"the hardness model needs at least {N_MIN} descriptor-scorable "
            f"training alloys and {subset} has {len(usable)}. Below that floor "
            f"the fit is close to guessing, so it refuses rather than pretends."
        )

    from .._model_cache import FOREST_JOBS
    from ..benchmark.splits import grouped_split

    families = [family_of(record.composition) for record in usable]
    values = [record.value for record in usable]
    if len(set(families)) < _FOLDS:
        subset = f"processing={processing!r}" if processing else "the pooled set"
        raise PropertyUnavailableError(
            f"the hardness interval is calibrated by {_FOLDS}-fold cross-validation over "
            f"whole alloy systems, and {subset} spans only {len(set(families))} systems"
        )
    folds = [
        (list(fold.train), list(fold.test))
        for fold in grouped_split(families, ["x"] * len(usable), k=_FOLDS).folds
    ]

    def make_forest():
        return random_forest_cls(n_estimators=_TREES, random_state=_SEED, n_jobs=FOREST_JOBS)

    scores = cross_val_scores(make_forest, features, values, folds)
    model = make_forest().fit(features, values)
    conformal = ConformalRegressor(model).calibrate_scores(scores)
    domain = fit_domain(
        [DomainRow(record.composition, family) for record, family in zip(usable, families)]
    )
    return model, conformal, domain, len(usable)


@accepts_formula
def predict_hardness(
    composition: Composition, *, alpha: float = 0.1, processing: str | None = None
):
    """(value, interval, novelty, n_training, warnings) for one composition."""
    comp = normalize(composition)
    model, conformal, domain, n_training = _fitted(processing)

    vector = matrix_vector(comp)
    if vector is None:
        raise PropertyUnavailableError(
            f"hardness needs all 14 descriptor features and at least one is "
            f"not computable for {comp!r} (element outside the descriptor "
            f"tables, or a singular descriptor)"
        )

    value = float(model.predict([vector])[0])
    return _assemble(comp, value, conformal, domain, n_training, alpha, processing)


def predict_hardness_batch(
    compositions, *, alpha: float = 0.1, processing: str | None = None
) -> list:
    """:func:`predict_hardness` for many compositions in one forest call.

    Returns one entry per input, in order: the same tuple
    :func:`predict_hardness` returns, or the :class:`PropertyUnavailableError`
    it would have raised. One forest call instead of one per row is what
    makes a lattice search affordable in the browser engine; the numbers
    are identical, because a forest averages its trees per row in the
    same order either way.
    """
    model, conformal, domain, n_training = _fitted(processing)
    comps = [normalize(composition) for composition in compositions]
    vectors = [matrix_vector(comp) for comp in comps]
    scorable = [vector for vector in vectors if vector is not None]
    values = iter(model.predict(scorable)) if scorable else iter(())
    results: list = []
    for comp, vector in zip(comps, vectors):
        if vector is None:
            results.append(
                PropertyUnavailableError(
                    f"hardness needs all 14 descriptor features and at least one is "
                    f"not computable for {comp!r} (element outside the descriptor "
                    f"tables, or a singular descriptor)"
                )
            )
            continue
        results.append(
            _assemble(comp, float(next(values)), conformal, domain, n_training, alpha, processing)
        )
    return results


def _assemble(comp, value, conformal, domain, n_training, alpha, processing):
    """The (value, interval, novelty, n_training, warnings) tuple for one row."""
    # The interval is the calibrated threshold around the prediction just
    # made; rebuilding it via predict_interval would run the forest a
    # second time on the same row for the same numbers.
    threshold = conformal._threshold(alpha)
    interval = (
        (-math.inf, math.inf)
        if threshold is None
        else (value - threshold, value + threshold)
    )
    novelty = domain.novelty(comp)

    warnings: list[str] = []
    if processing is None:
        warnings.append(
            "training data pools multiple processing routes (cast, annealed, "
            "powder and more); pass processing='CAST' style filters to "
            "condition, at the cost of training rows"
        )
    if threshold is None:
        warnings.append(
            f"calibration size cannot support alpha={alpha}; the interval is "
            f"unbounded at this level"
        )
    if not novelty["in_domain"]:
        warnings.append(
            "composition is outside the hardness training domain; the "
            "interval's guarantee is weakest exactly here"
        )
    return value, interval, novelty, n_training, tuple(warnings)


__all__ = ["N_MIN", "PropertyUnavailableError", "predict_hardness", "predict_hardness_batch"]
