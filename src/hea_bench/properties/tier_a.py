"""Tier A properties: closed-form estimates from composition alone.

Tier A quantities are transparent arithmetic over vendored, cited
tables, exactly like the descriptors: no fitted model, so no interval
beyond the input data's own quality. Their honesty obligations are
different from the ML tiers': state the formula, state the tables, and
return None rather than a number when a table has no entry.

``density`` is the rule of mixtures over molar masses and molar
volumes, ``sum(c_i M_i) / sum(c_i V_i)``, with masses from the IUPAC
standard atomic weights and volumes from the vendored matminer Miedema
parameter table. Volume additivity ignores excess mixing volume, which
for solid solutions is typically a few percent; the measured comparison
against the experimental densities in the Borg dataset lives in
``docs/property-tier-a.md``.
"""

from __future__ import annotations

from ..composition import Composition, normalize
from ..descriptors.data.mechanics import mechanics
from .data.atomic_masses import ATOMIC_MASS_G_MOL
from .data.element_prices import PRICES_USD_PER_KG


def cost_per_kg(composition: Composition) -> float | None:
    """Indicative alloy raw-material cost in USD per kg, or None.

    Mass-weighted over the date-stamped element price table:
    ``sum(w_i p_i)`` with ``w_i`` the mass fraction. This prices the
    elements going in, not melting, processing, yield losses, or
    research-quantity purchasing, all of which dominate real cost at lab
    scale; the table's docstring carries the full basis caveats. None
    when any element has no price row.
    """
    comp = normalize(composition)
    weights = _mass_fractions(comp)
    if weights is None:
        return None
    total = 0.0
    for element, weight in weights.items():
        row = PRICES_USD_PER_KG.get(element)
        if row is None:
            return None
        total += weight * row[0]
    return total


def cost_breakdown(composition: Composition) -> dict[str, dict]:
    """Per-element cost contributions with each row's basis and source.

    Raises ValueError when the composition has unpriced or massless
    elements; use :func:`cost_per_kg` for the None-returning form.
    """
    comp = normalize(composition)
    weights = _mass_fractions(comp)
    if weights is None:
        missing = sorted(el for el in comp if el not in ATOMIC_MASS_G_MOL)
        raise ValueError(f"no atomic mass for: {', '.join(missing)}")
    breakdown: dict[str, dict] = {}
    for element, weight in weights.items():
        row = PRICES_USD_PER_KG.get(element)
        if row is None:
            raise ValueError(f"no price row for {element}")
        price, basis, asof, source = row
        breakdown[element] = {
            "mass_fraction": weight,
            "usd_per_kg": price,
            "basis": basis,
            "asof": asof,
            "source": source,
            "contribution_usd_per_kg": weight * price,
        }
    return breakdown


def _mass_fractions(comp: Composition) -> dict[str, float] | None:
    masses = {}
    for element, fraction in comp.items():
        mass = ATOMIC_MASS_G_MOL.get(element)
        if mass is None:
            return None
        masses[element] = fraction * mass
    total = sum(masses.values())
    return {element: value / total for element, value in masses.items()}


def density(composition: Composition) -> float | None:
    """Rule-of-mixtures density in g/cm3, or None where a table has no row.

    None (never a guess) when any element lacks an atomic mass or a
    positive molar volume; upstream stores 0.0 volume for gases and some
    nonmetals, which means "not available", not "zero volume".
    """
    comp = normalize(composition)
    total_mass = 0.0
    total_volume = 0.0
    for element, fraction in comp.items():
        mass = ATOMIC_MASS_G_MOL.get(element)
        bundle = mechanics(element)
        if mass is None or bundle is None or bundle.molar_volume_cm3 <= 0:
            return None
        total_mass += fraction * mass
        total_volume += fraction * bundle.molar_volume_cm3
    return total_mass / total_volume


__all__ = ["cost_breakdown", "cost_per_kg", "density"]
