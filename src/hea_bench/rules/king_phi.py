"""King capital-Φ rule (King et al. 2016).

The paper (Acta Mater. 104, 172, page 174) says "a value of Φ > 1
would suggest a stable solid solution at the system's melting
temperature." This rule uses strict ``>`` to match the paper and the
existing ``yang_omega.predict`` pattern.
"""

from __future__ import annotations

from ..composition import Composition
from ..constants import KING_PHI_THRESHOLD
from ..descriptors.phi import phi_king

DESCRIPTION = "King 2016: Φ > 1.0 → solid_solution"

DEFAULT_THRESHOLD = KING_PHI_THRESHOLD


def predict(
    composition: Composition,
    threshold: float = DEFAULT_THRESHOLD,
    temperature_policy: float | None = None,
) -> str:
    """Return ``solid_solution`` if Φ exceeds the threshold.

    ``temperature_policy`` is an optional numeric override (in K) for
    the temperature used inside the descriptor's Gibbs-energy
    computation. When ``None``, the rule-of-mixtures melting
    temperature is used, matching King 2016 page 174.
    """
    phi = phi_king(composition, temperature=temperature_policy)
    return "solid_solution" if phi > threshold else "intermetallic"