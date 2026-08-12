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


__all__ = ["density"]
