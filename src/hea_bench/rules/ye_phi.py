"""Ye lowercase-φ rule (Ye et al. 2015)."""

from __future__ import annotations

from ..composition import Composition
from ..constants import YE_PHI_THRESHOLD
from ..descriptors.phi import phi_ye

DESCRIPTION = "Ye 2015: φ > 20.0 → solid_solution"

DEFAULT_THRESHOLD = YE_PHI_THRESHOLD


def predict(composition: Composition, threshold: float = DEFAULT_THRESHOLD) -> str:
    """Return ``solid_solution`` if φ exceeds the threshold.

    Strict ``>`` is used to match the existing rule-comparator pattern
    in :mod:`hea_bench.rules.yang_omega` and the boundary condition
    convention in Ye 2015 page 54.
    """
    return "solid_solution" if phi_ye(composition) > threshold else "intermetallic"