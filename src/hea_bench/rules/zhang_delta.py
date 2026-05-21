"""Zhang δ < 6.5% rule (Zhang 2008).

Binary classifier: predicts "single-phase" (BCC or FCC or HCP solid
solution) when the atomic-size mismatch is below the threshold,
"multi-phase" otherwise. The 6.5% threshold is the canonical value
from Zhang 2008; the function exposes ``threshold`` so downstream
ROC analysis can sweep it.

Reference
---------
Zhang, Y., Zuo, T. T., Tang, Z. *et al.* (2008). Solid-solution phase
formation rules for multi-component alloys. *Advanced Engineering
Materials* **10**, 534-538.
"""

from __future__ import annotations

from ..composition import Composition
from ..descriptors.size import delta

DESCRIPTION = "Zhang 2008: δ < 6.5% → single-phase solid solution"

DEFAULT_THRESHOLD = 6.5  # percent


def predict(composition: Composition, threshold: float = DEFAULT_THRESHOLD) -> str:
    """Return ``"single-phase"`` if δ < threshold, else ``"multi-phase"``.

    >>> predict({"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2})
    'single-phase'
    """
    return "single-phase" if delta(composition) < threshold else "multi-phase"
