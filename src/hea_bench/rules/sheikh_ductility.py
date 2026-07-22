"""Sheikh intrinsic-ductility screen for refractory bcc HEAs.

Single-phase bcc refractory HEAs are intrinsically ductile when
VEC < 4.5 and brittle when VEC ≥ 4.6; the narrow band between is
reported as ``borderline``. The screen is meaningful for bcc-forming
refractory alloys; callers should present it alongside the Guo VEC
structure bands rather than as a universal verdict.

References
----------
Sheikh, S., Shafeie, S., Hu, Q., Ahlstrom, J., Persson, C.,
Vesely, J., Zyka, J., Klement, U. & Guo, S. (2016). Alloy design for
intrinsically ductile refractory high-entropy alloys.
*J. Appl. Phys.* **120**, 164902. doi:10.1063/1.4966659
"""

from __future__ import annotations

from dataclasses import dataclass

from ..composition import Composition
from ..constants import SHEIKH_BRITTLE_VEC, SHEIKH_DUCTILE_VEC
from ..descriptors.vec import vec

DESCRIPTION = "Sheikh 2016: VEC < 4.5 -> ductile; VEC >= 4.6 -> brittle (bcc RHEAs)"


@dataclass(frozen=True)
class DuctilityPrediction:
    vec: float
    verdict: str


def predict(composition: Composition) -> DuctilityPrediction:
    v = vec(composition)
    if v < SHEIKH_DUCTILE_VEC:
        verdict = "ductile"
    elif v >= SHEIKH_BRITTLE_VEC:
        verdict = "brittle"
    else:
        verdict = "borderline"
    return DuctilityPrediction(vec=v, verdict=verdict)
