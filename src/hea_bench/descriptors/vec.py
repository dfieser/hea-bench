"""Valence Electron Concentration (VEC) descriptor.

VEC = Σ_i  c_i · V_i

where ``V_i`` is the valence-electron count of element ``i`` and
``c_i`` is its mole fraction. The Guo & Liu (2011) phase rule maps
VEC bounds to predicted crystal structure:

- VEC ≥ 8.0   → single-phase FCC likely
- VEC < 6.87  → single-phase BCC likely
- otherwise    → mixed FCC+BCC region

This module computes only the value; the rule is implemented in
``hea_bench.rules.guo_vec`` (Phase 2 sub-step 2d).

References
----------
Guo, S. & Liu, C. T. (2011). Phase stability in high entropy alloys:
Formation of solid-solution phase or amorphous phase.
*Progress in Natural Science: Materials International* **21**, 433-446.
"""

from __future__ import annotations

from ..composition import Composition
from .data.elemental import ELEMENTAL_DATA, missing_elements


def vec(composition: Composition) -> float:
    """Valence Electron Concentration (dimensionless).

    Examples
    --------
    Cantor alloy CoCrFeMnNi at equimolar composition:

    >>> vec({"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2})
    8.0
    """
    if not composition:
        raise ValueError("composition must be non-empty")
    missing = missing_elements(set(composition))
    if missing:
        raise ValueError(
            f"composition contains elements not in elemental data table: "
            f"{sorted(missing)}"
        )

    total = sum(composition.values())
    if total <= 0:
        raise ValueError("composition values must sum to a positive number")

    return sum(
        (amount / total) * ELEMENTAL_DATA[el].valence
        for el, amount in composition.items()
        if amount > 0
    )
