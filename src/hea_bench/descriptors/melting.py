"""Composition-weighted average melting temperature T_m.

T_m = Σ_i  c_i · T_{m,i}

A simple linear (rule-of-mixtures) estimate; serves as the
characteristic temperature in the Yang-Zhang Ω parameter
(``Ω = T_m · ΔS_mix / |ΔH_mix|``).

References
----------
Yang, X. & Zhang, Y. (2012). Prediction of high-entropy stabilized
solid-solution in multi-component alloys. *Materials Chemistry and
Physics* **132**, 233-238.
"""

from __future__ import annotations

from ..composition import Composition
from .data.elemental import ELEMENTAL_DATA, missing_elements


def melting_temperature(composition: Composition) -> float:
    """Rule-of-mixtures average melting temperature (K).

    Examples
    --------
    >>> round(melting_temperature({"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}), 2)
    1801.2
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
        (amount / total) * ELEMENTAL_DATA[el].melting_K
        for el, amount in composition.items()
        if amount > 0
    )
