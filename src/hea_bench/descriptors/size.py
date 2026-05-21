"""Atomic-size mismatch descriptor δ.

δ = 100 · √( Σ_i  c_i · (1 − r_i / r̄)² )

where ``r̄ = Σ_i c_i · r_i`` is the composition-weighted mean atomic
radius. The historical convention reports δ as a percentage (multiply
by 100), which is the convention used in essentially all HEA literature
and is the one used here.

References
----------
Zhang, Y., Zuo, T. T., Tang, Z. *et al.* (2008). Solid-solution phase
formation rules for multi-component alloys.
*Advanced Engineering Materials* **10**, 534-538.

Guo, S. & Liu, C. T. (2011). Phase stability in high entropy alloys.
*Progress in Natural Science: Materials International* **21**, 433-446.
"""

from __future__ import annotations

import math

from ..composition import Composition
from .data.elemental import ELEMENTAL_DATA, missing_elements


def delta(composition: Composition) -> float:
    """Atomic-size mismatch δ (percent).

    Parameters
    ----------
    composition
        Normalized mole-fraction mapping (will be re-normalized
        defensively if it does not sum to 1).

    Returns
    -------
    float
        δ in percent.

    Raises
    ------
    ValueError
        If ``composition`` is empty, or contains elements not present
        in the elemental data table. The error message lists the
        missing element symbols.

    Examples
    --------
    Cantor alloy CoCrFeMnNi at equimolar composition (against the
    Pauling-style atomic radii in :mod:`hea_bench.descriptors.data.elemental`;
    literature values for δ vary 3.0–3.5% depending on radius source):

    >>> round(delta({"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}), 4)
    3.1641
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
    norm = {el: amount / total for el, amount in composition.items() if amount > 0}

    r_bar = sum(c * ELEMENTAL_DATA[el].radius_pm for el, c in norm.items())
    if r_bar <= 0:
        raise ValueError("mean atomic radius is zero or negative")

    inner = sum(
        c * (1.0 - ELEMENTAL_DATA[el].radius_pm / r_bar) ** 2
        for el, c in norm.items()
    )
    return 100.0 * math.sqrt(max(inner, 0.0))
