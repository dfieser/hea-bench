"""Property estimates in explicit tiers, by data quality.

Tier A properties (``density``, ``melting_temperature``) are closed-form
arithmetic over cited tables, exactly like the descriptors: no fitted
model, so no interval; their measured accuracy against experiment is
documented in ``docs/property-tier-a.md``. Tier B (``hardness``) is a
fitted surrogate and always returns a conformal interval plus a
domain-of-applicability flag; its model card is
``docs/property-hardness.md``.

The domain flag means slightly different things per tier, and the
docstrings say so: for tier B it reflects the property's own training
data; for tier A it reflects the experimental phase corpus (available
from a repository checkout), answering "is this a chemistry anyone has
studied", and is None with a warning when no corpus is built.

Properties whose public data cannot support a decision a user would
actually make (yield strength across uncontrolled test temperatures,
ductility, corrosion measures) are deliberately not shipped; the model
card documents the omissions. Tier A is standard-library only; tier B
needs ``pip install "hea-bench[properties]"``.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass

from .._json import json_safe
from ..composition import Composition, accepts_formula, normalize
from .data.element_prices import PRICE_ASOF
from .hardness import PropertyUnavailableError
from .tier_a import cost_breakdown, cost_per_kg, density

_TIER_A_NOTES = {
    "density": (
        "closed form over cited tables (IUPAC masses, vendored molar "
        "volumes); volume additivity ignores excess mixing volume. Measured "
        "error versus experiment: docs/property-tier-a.md"
    ),
    "melting_temperature": (
        "closed form: rule of mixtures over CRC elemental melting points; "
        "solidus/liquidus spread and intermetallic melting sit outside the "
        "model"
    ),
    "cost_per_kg": (
        "indicative raw-material screening number, mass-weighted over a "
        "date-stamped element price table with per-element basis caveats "
        "(two-tier markets, oxide and contained-element rows); processing, "
        "yield, and research-quantity purchasing dominate real cost and are "
        "not included. Never read this as precise."
    ),
}


@dataclass(frozen=True)
class PropertyPrediction:
    """One property estimate with its uncertainty and domain context."""

    prop: str
    value: float
    unit: str
    interval: tuple[float, float] | None
    alpha: float | None
    tier: str
    in_domain: bool | None
    novelty: dict | None
    n_training: int | None
    model_card: str | None
    asof: str | None
    warnings: tuple[str, ...]

    def to_dict(self) -> dict:
        """Strict-JSON payload of this prediction (non-finite floats null).

        The one serialization every surface derives from: the MCP
        ``predict_properties`` payload is exactly this dict; design
        receipts carry a documented subset of its keys.
        """
        return {
            "value": json_safe(self.value),
            "unit": self.unit,
            "interval": (
                [json_safe(self.interval[0]), json_safe(self.interval[1])]
                if self.interval is not None
                else None
            ),
            "alpha": self.alpha,
            "tier": self.tier,
            "in_domain": self.in_domain,
            "novelty": self.novelty,
            "n_training": self.n_training,
            "model_card": self.model_card,
            "asof": self.asof,
            "warnings": list(self.warnings),
        }


def _tier_a_prediction(prop: str, comp: Composition, value: float, unit: str) -> PropertyPrediction:
    from ..uncertainty import default_domain

    warnings = [_TIER_A_NOTES[prop]]
    domain = default_domain()
    if domain is None:
        novelty = None
        in_domain = None
        warnings.append(
            "corpus not built in this environment, so the domain flag is "
            "unavailable (it reports coverage of the experimental phase corpus)"
        )
    else:
        novelty = domain.novelty(comp)
        in_domain = novelty["in_domain"]
    return PropertyPrediction(
        prop=prop,
        value=value,
        unit=unit,
        interval=None,
        alpha=None,
        tier="A",
        in_domain=in_domain,
        novelty=novelty,
        n_training=None,
        model_card="docs/property-tier-a.md",
        asof=None,
        warnings=tuple(warnings),
    )


def available_properties() -> dict[str, dict]:
    """What can be predicted, in which tier, and what each needs."""
    sklearn_present = importlib.util.find_spec("sklearn") is not None
    return {
        "density": {"tier": "A", "unit": "g/cm^3", "needs": None, "available": True},
        "melting_temperature": {"tier": "A", "unit": "K", "needs": None, "available": True},
        "cost_per_kg": {"tier": "A", "unit": "USD/kg", "needs": None, "available": True},
        "hardness": {
            "tier": "B",
            "unit": "HV",
            "needs": 'pip install "hea-bench[properties]" (scikit-learn)',
            "available": sklearn_present,
        },
    }


@accepts_formula
def predict_property(
    composition: Composition,
    prop: str,
    *,
    alpha: float = 0.1,
    processing: str | None = None,
) -> PropertyPrediction:
    """Predict one property with its uncertainty and domain flag.

    Parameters
    ----------
    composition
        Mole-fraction dict (amounts normalize internally, like every
        other surface).
    prop
        One of :func:`available_properties`.
    alpha
        Miscoverage level for tier B intervals (0.1 = a nominal 90
        percent interval). Ignored by tier A, which has no fitted model.
    processing
        Tier B only: restrict training to one processing route (Borg's
        vocabulary, e.g. ``"CAST"``, ``"ANNEAL"``). Fewer rows, more
        homogeneous population; below the floor the model refuses.

    Raises
    ------
    PropertyUnavailableError
        Unknown property, missing optional install, missing table rows,
        or a training population below the floor. The message names the
        fix; nothing is imputed.
    """
    comp = normalize(composition)

    if prop == "hardness":
        entry = predict_property_batch([comp], "hardness", alpha=alpha, processing=processing)[0]
        if isinstance(entry, PropertyUnavailableError):
            raise entry
        return entry

    if prop in _TIER_A_NOTES and processing is not None:
        raise PropertyUnavailableError(
            "processing conditioning applies to fitted (tier B) properties only"
        )

    if prop == "density":
        value = density(comp)
        if value is None:
            missing = sorted(
                element
                for element in comp
                if _density_gap(element)
            )
            raise PropertyUnavailableError(
                f"density is not computable: no mass or molar-volume table row "
                f"for {', '.join(missing)}"
            )
        return _tier_a_prediction("density", comp, value, "g/cm^3")

    if prop == "cost_per_kg":
        value = cost_per_kg(comp)
        if value is None:
            from .data.atomic_masses import ATOMIC_MASS_G_MOL
            from .data.element_prices import PRICES_USD_PER_KG

            missing = sorted(
                element
                for element in comp
                if element not in PRICES_USD_PER_KG or element not in ATOMIC_MASS_G_MOL
            )
            raise PropertyUnavailableError(
                f"cost_per_kg is not computable: no price or mass row for "
                f"{', '.join(missing)}"
            )
        import dataclasses

        prediction = _tier_a_prediction("cost_per_kg", comp, value, "USD/kg")
        return dataclasses.replace(prediction, asof=PRICE_ASOF)

    if prop == "melting_temperature":
        from ..descriptors.melting import melting_temperature

        try:
            value = float(melting_temperature(comp))
        except Exception as error:
            raise PropertyUnavailableError(
                f"melting_temperature is not computable for {comp!r}: {error}"
            ) from None
        return _tier_a_prediction("melting_temperature", comp, value, "K")

    raise PropertyUnavailableError(
        f"unknown property {prop!r}; available: {sorted(available_properties())}"
    )


def predict_property_batch(
    compositions,
    prop: str,
    *,
    alpha: float = 0.1,
    processing: str | None = None,
) -> list:
    """:func:`predict_property` over many compositions, same numbers.

    Returns one entry per input, in order: a :class:`PropertyPrediction`,
    or the :class:`PropertyUnavailableError` :func:`predict_property`
    would have raised for that row. Tier B runs its forest once for the
    whole batch instead of once per row, which is what the composition
    search needs; tier A is closed form and simply loops.
    """
    if prop != "hardness":
        results: list = []
        for composition in compositions:
            try:
                results.append(
                    predict_property(composition, prop, alpha=alpha, processing=processing)
                )
            except PropertyUnavailableError as error:
                results.append(error)
        return results

    from .hardness import predict_hardness_batch

    results = []
    for entry in predict_hardness_batch(compositions, alpha=alpha, processing=processing):
        if isinstance(entry, PropertyUnavailableError):
            results.append(entry)
            continue
        value, interval, novelty, n_training, warnings = entry
        results.append(
            PropertyPrediction(
                prop="hardness",
                value=value,
                unit="HV",
                interval=interval,
                alpha=alpha,
                tier="B",
                in_domain=novelty["in_domain"],
                novelty=novelty,
                n_training=n_training,
                model_card="docs/property-hardness.md",
                asof=None,
                warnings=warnings,
            )
        )
    return results


def _density_gap(element: str) -> bool:
    from ..descriptors.data.mechanics import mechanics
    from .data.atomic_masses import ATOMIC_MASS_G_MOL

    bundle = mechanics(element)
    return (
        ATOMIC_MASS_G_MOL.get(element) is None
        or bundle is None
        or bundle.molar_volume_cm3 <= 0
    )


__all__ = [
    "PropertyPrediction",
    "PropertyUnavailableError",
    "available_properties",
    "cost_breakdown",
    "cost_per_kg",
    "density",
    "predict_property",
    "predict_property_batch",
]
