"""Sheikh intrinsic-ductility screen for refractory bcc HEAs.

Single-phase bcc refractory HEAs are intrinsically ductile when
VEC < 4.5 and brittle when VEC ≥ 4.6; the narrow band between is
reported as ``borderline``. Sheikh et al. built the screen on
refractory HEAs made of group IV (Ti, Zr, Hf), V (V, Nb, Ta) and VI
(Cr, Mo, W) elements, so it says nothing about an alloy with any other
element: ``applies`` is False there and the verdict is
``not_applicable``. Present it alongside the Guo VEC structure bands
rather than as a universal verdict.

References
----------
Sheikh, S., Shafeie, S., Hu, Q., Ahlstrom, J., Persson, C.,
Vesely, J., Zyka, J., Klement, U. & Guo, S. (2016). Alloy design for
intrinsically ductile refractory high-entropy alloys.
*J. Appl. Phys.* **120**, 164902. doi:10.1063/1.4966659
"""

from __future__ import annotations

from dataclasses import dataclass

from ..composition import Composition, accepts_formula
from ..constants import SHEIKH_BRITTLE_VEC, SHEIKH_DUCTILE_VEC
from ..descriptors.vec import vec

DESCRIPTION = (
    "Sheikh 2016: VEC < 4.5 -> ductile; VEC >= 4.6 -> brittle "
    "(bcc RHEAs of Ti, Zr, Hf, V, Nb, Ta, Cr, Mo, W only)"
)

#: The group IV, V and VI refractory elements the screen was built on.
REFRACTORY_ELEMENTS = frozenset({"Ti", "Zr", "Hf", "V", "Nb", "Ta", "Cr", "Mo", "W"})


@dataclass(frozen=True)
class DuctilityPrediction:
    vec: float
    verdict: str
    applies: bool = True


@accepts_formula
def predict(composition: Composition) -> DuctilityPrediction:
    v = vec(composition)
    applies = all(
        el in REFRACTORY_ELEMENTS for el, amount in composition.items() if amount > 0
    )
    if not applies:
        verdict = "not_applicable"
    elif v < SHEIKH_DUCTILE_VEC:
        verdict = "ductile"
    elif v >= SHEIKH_BRITTLE_VEC:
        verdict = "brittle"
    else:
        verdict = "borderline"
    return DuctilityPrediction(vec=v, verdict=verdict, applies=applies)
