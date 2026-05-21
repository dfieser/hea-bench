"""Yeh ΔS_mix > 1.5R rule (Yeh 2004).

Predicts "HEA-class" composition when configurational mixing entropy
exceeds 1.5R ≈ 12.47 J/(mol·K). The rule classifies *compositions* into
HEA / MEA / dilute bins; it does NOT predict phase formation on its own.

Reference
---------
Yeh, J.-W. *et al.* (2004). Nanostructured high-entropy alloys with
multiple principal elements: Novel alloy design concepts and outcomes.
*Adv. Eng. Mater.* **6**, 299-303.
"""

from __future__ import annotations

from ..composition import Composition
from ..constants import R
from ..descriptors.entropy import smix

DESCRIPTION = "Yeh 2004: ΔS_mix > 1.5R → HEA-class composition"

HEA_THRESHOLD = 1.5 * R      # ≈ 12.471 J/(mol·K)
MEA_THRESHOLD = 1.0 * R      # ≈ 8.314  J/(mol·K)


def predict(composition: Composition) -> str:
    """Return one of ``"HEA"``, ``"MEA"``, ``"dilute"``.

    >>> predict({"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2})
    'HEA'
    """
    s = smix(composition)
    if s > HEA_THRESHOLD:
        return "HEA"
    if s >= MEA_THRESHOLD:
        return "MEA"
    return "dilute"
