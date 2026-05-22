"""Guo–Liu VEC rule (Guo & Liu 2011).

Three-class crystal-structure predictor for single-phase HEA solid
solutions. Note: this rule predicts the *crystal structure given that
the alloy forms single-phase*; it is NOT a single-vs-multi-phase
predictor on its own. Stratified evaluation against the canonical
benchmark should restrict the observed set to single-phase entries
(BCC or FCC).

- VEC ≥ 8.0   → FCC
- VEC < 6.87  → BCC
- otherwise    → mixed (FCC+BCC dual-phase or transitional)

Reference
---------
Guo, S. & Liu, C. T. (2011). Phase stability in high entropy alloys.
*Progress in Natural Science: Materials International* **21**, 433-446.
"""

from __future__ import annotations

from ..composition import Composition
from ..descriptors.vec import vec

DESCRIPTION = "Guo & Liu 2011: VEC≥8.0 → FCC, VEC<6.87 → BCC, else mixed"

FCC_THRESHOLD = 8.0
BCC_THRESHOLD = 6.87


def predict(composition: Composition) -> str:
    """Return one of ``"FCC"``, ``"BCC"``, ``"mixed"``.

    >>> predict({"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2})
    'FCC'
    """
    # Round to 6 decimals before the boundary test. Many benchmark
    # compositions have an exact-integer VEC (e.g. equiatomic CrFeNi is
    # (6+8+10)/3 = 8.0), but float summation yields 7.999999999999999 on
    # some CPython versions and exactly 8.0 on others. Rounding well below
    # any meaningful VEC precision makes the FCC/BCC/mixed call
    # deterministic across platforms and Python versions.
    v = round(vec(composition), 6)
    if v >= FCC_THRESHOLD:
        return "FCC"
    if v < BCC_THRESHOLD:
        return "BCC"
    return "mixed"
