"""Configurational mixing entropy ΔS_mix for ideal random solutions.

ΔS_mix = -R · Σ_i c_i · ln(c_i)

References
----------
Yeh, J.-W. *et al.* (2004). Nanostructured high-entropy alloys with
multiple principal elements: Novel alloy design concepts and outcomes.
*Adv. Eng. Mater.* **6**, 299–303.
"""

from __future__ import annotations

import math

from ..constants import R


def smix(composition: dict[str, float]) -> float:
    """Configurational mixing entropy in J / (mol · K).

    Parameters
    ----------
    composition
        Mapping of element symbol to mole fraction (or any positive amount —
        values are normalized internally so they only need to be proportional
        to the molar amounts).

    Returns
    -------
    float
        ΔS_mix in J / (mol · K).

    Raises
    ------
    ValueError
        If ``composition`` is empty or its values do not sum to a positive
        number.

    Examples
    --------
    Cantor alloy CoCrFeMnNi — five elements at equal fractions:

    >>> round(smix({'Co': 1, 'Cr': 1, 'Fe': 1, 'Mn': 1, 'Ni': 1}), 3)
    13.382
    """
    total = sum(composition.values())
    if total <= 0:
        raise ValueError("composition must sum to a positive value")
    s = 0.0
    for amount in composition.values():
        ci = amount / total
        if ci > 0:
            s -= ci * math.log(ci)
    return R * s
