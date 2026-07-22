"""Wang solid-angle packing parameter γ.

Around a central atom of radius r_c touching neighbors of the mean
radius r̄, the tangent cone satisfies sin θ = r̄/(r_c + r̄), so the
fractional solid angle subtended by one neighbor is

    ω(r_c) = 1 − √( ((r_c + r̄)² − r̄²) / (r_c + r̄)² )

γ compares the packing around the smallest and the largest atom:

    γ = ω_S / ω_L,   ω_S = ω(r_min), ω_L = ω(r_max)

Equal radii give γ = 1 exactly; γ grows with size mismatch. The paper
finds crystalline solid solutions require γ < 1.175 (their dataset's
boundary against intermetallic- and amorphous-forming compositions).

References
----------
Wang, Z., Huang, Y., Yang, Y., Wang, J. & Liu, C. T. (2015).
Atomic-size effect and solid solubility of multicomponent alloys.
*Scripta Materialia* **94**, 28-31. doi:10.1016/j.scriptamat.2014.09.010
"""

from __future__ import annotations

import math

from ..composition import Composition
from .data.elemental import ELEMENTAL_DATA, missing_elements


def _omega(r_center: float, r_bar: float) -> float:
    s = r_center + r_bar
    return 1.0 - math.sqrt((s * s - r_bar * r_bar) / (s * s))


def _gamma_from_radii(fractions: dict[str, float], radii: dict[str, float]) -> float:
    """γ from explicit fraction and radius tables (testable core)."""
    total = sum(fractions.values())
    norm = {k: v / total for k, v in fractions.items() if v > 0}
    r_bar = sum(c * radii[k] for k, c in norm.items())
    r_min = min(radii[k] for k in norm)
    r_max = max(radii[k] for k in norm)
    return _omega(r_min, r_bar) / _omega(r_max, r_bar)


def wang_gamma(composition: Composition) -> float:
    """γ = ω_S/ω_L (dimensionless, ≥ 1)."""
    if not composition:
        raise ValueError("composition must be non-empty")
    missing = missing_elements(set(composition))
    if missing:
        raise ValueError(
            f"composition contains elements not in elemental data table: "
            f"{sorted(missing)}"
        )
    radii = {el: ELEMENTAL_DATA[el].radius_pm for el in composition}
    return _gamma_from_radii(dict(composition), radii)
