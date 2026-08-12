"""Tier B hardness surrogate over the Borg room-temperature HV records.

The model is deliberately unexciting: the baseline random forest
(300 trees, seed 0) on this package's own 14 descriptors, wrapped in a
split conformal regressor calibrated on a family-grouped hold-out so
the interval is not narrowed by stoichiometric near-duplicates, plus a
domain model fitted on the same training compositions. Its job is a
screening estimate with an honest interval, not a hardness theory; the
held-out error and the processing-state mix are in the model card,
``docs/property-hardness.md``, and whether the interval supports
ranking close candidates is stated there rather than implied.

Everything is fitted on demand per process (seeded, cached), because
shipping a pickled model would freeze a scikit-learn version into the
wheel; the ``properties`` extra pins the series instead.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from ..composition import Composition, family_of, normalize
from ..descriptors.backend import NativeBackend
from ..uncertainty import ConformalRegressor, fit_domain
from ..uncertainty.splitting import grouped_calibration_split
from .borg import hardness_records

#: Below this many usable training alloys the model refuses to exist.
N_MIN = 50

_SEED = 0
_TREES = 300
_CALIBRATION_FRACTION = 0.2


class PropertyUnavailableError(RuntimeError):
    """A property, or the capability to compute it, is not available.

    The message names the missing install, the data floor, or the
    omission reason; it never hands back a silent guess.
    """


@dataclass(frozen=True)
class _DomainRow:
    """Adapter giving fit_domain what it needs from a property record."""

    composition: Composition
    family: str
    descriptor_ready: bool = True


def _require_random_forest():
    try:
        from sklearn.ensemble import RandomForestRegressor
    except ImportError as exc:
        raise PropertyUnavailableError(
            "the hardness surrogate needs scikit-learn, which is not "
            'installed. Install it with: pip install "hea-bench[properties]"'
        ) from exc
    return RandomForestRegressor


def _feature_vector(composition: Composition) -> list[float] | None:
    backend = NativeBackend()
    values = backend.compute(composition)
    vector = [values.get(name) for name in backend.matrix_names()]
    if all(value is not None and math.isfinite(value) for value in vector):
        return [float(value) for value in vector]
    return None


@lru_cache(maxsize=8)
def _fitted(processing: str | None):
    """Fit (model, conformal, domain, n) for one processing filter."""
    random_forest_cls = _require_random_forest()

    records = [
        record
        for record in hardness_records()
        if processing is None or record.processing == processing
    ]
    usable = []
    features = []
    for record in records:
        vector = _feature_vector(record.composition)
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

    families = [family_of(record.composition) for record in usable]
    proper, calibration = grouped_calibration_split(
        families, fraction=_CALIBRATION_FRACTION, seed=_SEED
    )
    model = random_forest_cls(n_estimators=_TREES, random_state=_SEED)
    model.fit([features[i] for i in proper], [usable[i].value for i in proper])
    conformal = ConformalRegressor(model).fit_calibrate(
        [features[i] for i in calibration], [usable[i].value for i in calibration]
    )
    domain = fit_domain(
        [_DomainRow(record.composition, family) for record, family in zip(usable, families)]
    )
    return model, conformal, domain, len(usable)


def predict_hardness(
    composition: Composition, *, alpha: float = 0.1, processing: str | None = None
):
    """(value, interval, novelty, n_training, warnings) for one composition."""
    comp = normalize(composition)
    model, conformal, domain, n_training = _fitted(processing)

    vector = _feature_vector(comp)
    if vector is None:
        raise PropertyUnavailableError(
            f"hardness needs all 14 descriptor features and at least one is "
            f"not computable for {comp!r} (element outside the descriptor "
            f"tables, or a singular descriptor)"
        )

    value = float(model.predict([vector])[0])
    interval = conformal.predict_interval([vector], alpha=alpha)[0]
    novelty = domain.novelty(comp)

    warnings: list[str] = []
    if processing is None:
        warnings.append(
            "training data pools multiple processing routes (cast, annealed, "
            "powder and more); pass processing='CAST' style filters to "
            "condition, at the cost of training rows"
        )
    if conformal.degenerate(alpha):
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


__all__ = ["N_MIN", "PropertyUnavailableError", "predict_hardness"]
