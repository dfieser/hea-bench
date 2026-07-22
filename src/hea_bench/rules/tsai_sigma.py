"""Tsai σ-phase risk window for Cr- and/or V-containing alloys.

The survey behind the rule found that annealed HEAs containing Cr
and/or V form the σ phase when 6.88 ≤ VEC ≤ 7.84 and generally do not
outside that window. The rule is silent about alloys without Cr or V;
``applies`` is False there and the verdict is ``not_applicable``.

References
----------
Tsai, M.-H., Tsai, K.-Y., Tsai, C.-W., Lee, C., Juan, C.-C. &
Yeh, J.-W. (2013). Criterion for sigma phase formation in Cr- and
V-containing high-entropy alloys. *Mater. Res. Lett.* **1**, 207-212.
doi:10.1080/21663831.2013.831382
"""

from __future__ import annotations

from dataclasses import dataclass

from ..composition import Composition
from ..constants import TSAI_SIGMA_VEC_MAX, TSAI_SIGMA_VEC_MIN
from ..descriptors.vec import vec

DESCRIPTION = "Tsai 2013: Cr/V present and 6.88 <= VEC <= 7.84 -> sigma_prone"

_SIGMA_FORMERS = frozenset({"Cr", "V"})


@dataclass(frozen=True)
class SigmaPrediction:
    applies: bool
    in_window: bool
    vec: float
    verdict: str


def predict(composition: Composition) -> SigmaPrediction:
    v = vec(composition)
    applies = any(
        el in _SIGMA_FORMERS and amount > 0 for el, amount in composition.items()
    )
    in_window = TSAI_SIGMA_VEC_MIN <= v <= TSAI_SIGMA_VEC_MAX
    if not applies:
        verdict = "not_applicable"
    elif in_window:
        verdict = "sigma_prone"
    else:
        verdict = "sigma_unlikely"
    return SigmaPrediction(applies=applies, in_window=in_window, vec=v, verdict=verdict)
