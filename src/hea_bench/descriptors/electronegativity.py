"""Pauling electronegativity descriptors for HEA phase prediction.

Δχ = √( Σ_i  c_i · (χ_i − χ̄)² )

where ``χ̄ = Σ_i c_i · χ_i`` is the composition-weighted mean Pauling
electronegativity. Δχ is the composition-weighted standard deviation of
the constituent electronegativities, the standard HEA electronegativity
mismatch term. A large Δχ signals a tendency toward ordered
intermetallic compounds rather than a disordered solid solution.

This descriptor carries information that the atomic-size, melting-point,
and valence-electron descriptors do not: electronegativity is not a
function of those three properties. It is provided as an additional
general-purpose HEA descriptor alongside the canonical six.

References
----------
Pauling, L. (1960). *The Nature of the Chemical Bond*, 3rd ed. Cornell
University Press. (Source of the Pauling-scale values; the WebElements
consistent set used here and reproduced in the CRC Handbook, Haynes 2016.)

Guo, S. & Liu, C. T. (2011). Phase stability in high entropy alloys.
*Progress in Natural Science: Materials International* **21**, 433-446.
"""

from __future__ import annotations

import math

from ..composition import Composition
from .data.elemental import ELEMENTAL_DATA, missing_elements


def _normalized(composition: Composition) -> dict[str, float]:
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
    return {el: amount / total for el, amount in composition.items() if amount > 0}


def mean_electronegativity(composition: Composition) -> float:
    """Composition-weighted mean Pauling electronegativity χ̄.

    Examples
    --------
    >>> round(mean_electronegativity(
    ...     {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}), 4)
    1.766
    """
    norm = _normalized(composition)
    return sum(c * ELEMENTAL_DATA[el].electronegativity for el, c in norm.items())


def delta_chi(composition: Composition) -> float:
    """Electronegativity mismatch Δχ (composition-weighted std, dimensionless).

    Parameters
    ----------
    composition
        Normalized mole-fraction mapping (re-normalized defensively if it
        does not sum to 1).

    Returns
    -------
    float
        Δχ on the Pauling scale.

    Raises
    ------
    ValueError
        If ``composition`` is empty or contains elements not present in
        the elemental data table. The error message lists the missing
        element symbols.

    Examples
    --------
    Cantor alloy CoCrFeMnNi at equimolar composition:

    >>> round(delta_chi(
    ...     {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}), 4)
    0.1384
    """
    norm = _normalized(composition)
    chi_bar = sum(c * ELEMENTAL_DATA[el].electronegativity for el, c in norm.items())
    inner = sum(
        c * (ELEMENTAL_DATA[el].electronegativity - chi_bar) ** 2
        for el, c in norm.items()
    )
    return math.sqrt(max(inner, 0.0))
