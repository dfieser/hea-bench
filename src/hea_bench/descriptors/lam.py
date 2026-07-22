"""Singh geometric parameter Λ (Lambda).

Λ = ΔS_mix / δ²

with ΔS_mix in J/(mol·K) and δ in percent, following the units used
in the defining paper's Fig. 2. Interpretation bands from the paper:
Λ > 0.96 single disordered solid solution; 0.24 ≤ Λ ≤ 0.96 solid
solution plus compounds; Λ < 0.24 compound-dominated.

Two elements with identical tabulated radii give δ = 0; Λ is then
unbounded and this module returns ``math.inf`` (trivially inside the
single-solid-solution band), which callers may render as "δ = 0".

References
----------
Singh, A. K., Kumar, N., Dwivedi, A. & Subramaniam, A. (2014). A
geometrical parameter for the formation of disordered solid solutions
in multi-component alloys. *Intermetallics* **53**, 112-119.
doi:10.1016/j.intermet.2014.04.019
"""

from __future__ import annotations

import math

from ..composition import Composition
from .entropy import smix
from .size import delta


def singh_lambda(composition: Composition) -> float:
    """Λ = ΔS_mix / δ² (J·mol⁻¹·K⁻¹·%⁻²); ``math.inf`` when δ = 0."""
    d = delta(composition)
    if d == 0.0:
        return math.inf
    return smix(composition) / (d * d)
