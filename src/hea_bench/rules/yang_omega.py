"""Yang–Zhang Ω > 1.1 rule (Yang & Zhang 2012).

Binary classifier: predicts "single-phase" solid solution when the
Ω parameter exceeds 1.1, "multi-phase" otherwise. The threshold is
the value Yang & Zhang 2012 used in their original delineation; the
function exposes ``threshold`` so downstream ROC analysis can sweep it.

Reference
---------
Yang, X. & Zhang, Y. (2012). Prediction of high-entropy stabilized
solid-solution in multi-component alloys. *Materials Chemistry and
Physics* **132**, 233-238.
"""

from __future__ import annotations

import math

from ..composition import Composition
from ..descriptors.omega import omega

DESCRIPTION = "Yang & Zhang 2012: Ω > 1.1 → single-phase solid solution"

DEFAULT_THRESHOLD = 1.1


def predict(composition: Composition, threshold: float = DEFAULT_THRESHOLD) -> str:
    """Return ``"single-phase"`` if Ω > threshold, else ``"multi-phase"``.

    ``+inf`` (the pure-element edge case) is treated as single-phase.

    >>> predict({"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2})
    'single-phase'
    """
    om = omega(composition)
    if math.isinf(om):
        return "single-phase"
    return "single-phase" if om > threshold else "multi-phase"
