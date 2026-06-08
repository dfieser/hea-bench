"""Phi-family thermodynamic descriptors.

This module adds the v1.1 phi descriptors discussed in the project
plan:

- ``phi_king``: King capital Phi, based on a disordered-solid-solution
  Gibbs energy against the most stable binary-subsystem proxy.
- ``phi_ye``: Ye lowercase phi, based on the entropic stabilization
  ratio with a Mansoori excess-entropy term.

The implementation is intentionally explicit and decomposed into small
helpers so the intermediate quantities can be regression-tested.
"""

from __future__ import annotations

import math
from itertools import combinations

from ..composition import Composition
from ..constants import (
    KING_PHI_THRESHOLD,
    PACKING_FRACTION_BCC,
    PACKING_FRACTION_FCC,
    R,
    YE_PHI_THRESHOLD,
)
from .data.elemental import ELEMENTAL_DATA, missing_elements
from .data.pair_enthalpies import pair_enthalpy
from .entropy import smix
from .melting import melting_temperature
from .miedema import mixing_enthalpy

_DEFAULT_PACKING_FRACTIONS = (PACKING_FRACTION_BCC, PACKING_FRACTION_FCC)


def _normalize(composition: Composition) -> Composition:
    if not composition:
        raise ValueError("composition must be non-empty")
    missing = missing_elements(set(composition))
    if missing:
        raise ValueError(
            f"composition contains elements not in elemental data table: {sorted(missing)}"
        )
    total = sum(composition.values())
    if total <= 0:
        raise ValueError("composition values must sum to a positive number")
    return {el: amount / total for el, amount in composition.items() if amount > 0}


def delta_h_ss(composition: Composition) -> float:
    """Enthalpy of forming the disordered solid solution (kJ/mol)."""
    return mixing_enthalpy(composition)


def delta_g_ss(composition: Composition, temperature: float | None = None) -> float:
    """Gibbs free energy proxy for the disordered solid solution (kJ/mol)."""
    tm = melting_temperature(composition) if temperature is None else temperature
    return delta_h_ss(composition) - tm * smix(composition) / 1000.0


def delta_g_max(composition: Composition) -> float:
    """Most stable binary-subsystem intermetallic Gibbs energy (kJ/mol).

    Approximation of King 2016's ΔG_max. King defines it as the
    formation enthalpy of the most stable binary intermetallic that
    can form from the constituents, computed from his Eq. 5.9 (sourced
    from Bakker 1998). Since hea-bench's data layer is the
    matminer-vendored Miedema pair-enthalpy table rather than Bakker's
    binary-intermetallic enthalpy formula, this function returns the
    most negative *raw* pair enthalpy across all binaries — no
    composition scaling — as the documented approximation. King's
    assumption that ΔS_conf = 0 for ordered intermetallics means
    ΔG_int ≈ ΔH_int, so the pair enthalpy stands in for the binary
    intermetallic Gibbs energy directly.

    The numerical consequence: this approximation underestimates
    King's ΔG_max for n-element alloys with n ≥ 4, because King
    scales for multiple-binary allocation across the alloy's
    stoichiometry. ``phi_king`` values from this implementation are
    therefore systematically larger than King's published Φ values
    by roughly a factor of n/2. The held-out evaluation in v1.1
    re-tunes the Φ threshold against the consolidated benchmark, so
    the absolute scale is recoverable by the tuned threshold even if
    the raw scale differs from the paper's.
    """
    norm = _normalize(composition)
    values = [pair_enthalpy(a, b) for a, b in combinations(sorted(norm), 2)]
    return min(values) if values else 0.0


def _mansoori_excess_entropy(composition: Composition, packing_fraction: float) -> float:
    if not 0.0 < packing_fraction < 1.0:
        raise ValueError("packing_fraction must be between 0 and 1")

    norm = _normalize(composition)
    diameters = {el: 2.0 * ELEMENTAL_DATA[el].radius_pm for el in norm}
    sigma_2 = sum(norm[el] * diameters[el] ** 2 for el in norm)
    sigma_3 = sum(norm[el] * diameters[el] ** 3 for el in norm)

    pair_term_1 = 0.0
    pair_term_2 = 0.0
    for a, b in combinations(sorted(norm), 2):
        da = diameters[a]
        db = diameters[b]
        coeff = norm[a] * norm[b] * (da - db) ** 2
        pair_term_1 += (da + db) * coeff
        pair_term_2 += da * db * coeff

    zeta = 1.0 / (1.0 - packing_fraction)
    y1 = pair_term_1 / sigma_3 if sigma_3 else 0.0
    y2 = (sigma_2 / (sigma_3**2)) * pair_term_2 if sigma_3 else 0.0
    y3 = (sigma_2**3) / (sigma_3**2) if sigma_3 else 1.0

    expression = (
        1.5 * (zeta**2 - 1.0) * y1
        + 1.5 * (zeta - 1.0) ** 2 * y2
        - ((0.5 * (zeta - 1.0) * (zeta - 3.0)) + math.log(zeta)) * (1.0 - y3)
    )
    return R * expression


def s_excess(
    composition: Composition,
    packing_fraction: float | None = None,
) -> float:
    """Mansoori excess entropy term S_E (J / (mol · K)).

    When ``packing_fraction`` is omitted, the Ye convention is used:
    compute both the bcc and fcc packing fractions and average them.
    """
    if packing_fraction is not None:
        return _mansoori_excess_entropy(composition, packing_fraction)
    values = tuple(_mansoori_excess_entropy(composition, xi) for xi in _DEFAULT_PACKING_FRACTIONS)
    return sum(values) / len(values)


def phi_king(composition: Composition, temperature: float | None = None) -> float:
    """King capital Phi (dimensionless)."""
    g_ss = delta_g_ss(composition, temperature=temperature)
    g_max = delta_g_max(composition)
    if g_max == 0.0:
        return math.inf
    return g_ss / (-abs(g_max))


def phi_ye(composition: Composition) -> float:
    """Ye lowercase phi (dimensionless)."""
    tm = melting_temperature(composition)
    numerator = smix(composition) - abs(delta_h_ss(composition)) * 1000.0 / tm
    denominator = abs(s_excess(composition))
    if denominator == 0.0:
        return math.inf
    return numerator / denominator


__all__ = [
    "KING_PHI_THRESHOLD",
    "YE_PHI_THRESHOLD",
    "delta_h_ss",
    "delta_g_ss",
    "delta_g_max",
    "phi_king",
    "phi_ye",
    "s_excess",
]