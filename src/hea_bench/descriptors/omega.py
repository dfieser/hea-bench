"""Yang–Zhang Ω parameter.

Ω = (T_m · ΔS_mix) / |ΔH_mix|

A scaled ratio that compares the entropic stabilization of a
disordered solid solution against the enthalpic driving force toward
ordered (intermetallic) or segregated phases. Yang & Zhang (2012)
empirically observed that:

- **Ω ≥ 1.1**  → single-phase disordered solid solution is favored
- **Ω < 1.1**  → intermetallics or multi-phase mixtures are likely

The threshold rule is implemented in
:mod:`hea_bench.rules.yang_omega` (Phase 2d).

Units
-----
T_m is in K and ΔS_mix is in J/(mol·K), so ``T_m · ΔS_mix`` has units
of J/mol. ΔH_mix from :mod:`hea_bench.descriptors.miedema` is in
kJ/mol; we multiply by 1000 in the denominator so Ω is dimensionless.

References
----------
Yang, X. & Zhang, Y. (2012). Prediction of high-entropy stabilized
solid-solution in multi-component alloys. *Materials Chemistry and
Physics* **132**, 233-238.
"""

from __future__ import annotations

import math

from ..composition import Composition
from .entropy import smix
from .melting import melting_temperature
from .miedema import mixing_enthalpy


def omega(composition: Composition) -> float:
    """Yang–Zhang Ω parameter (dimensionless).

    Parameters
    ----------
    composition
        Mapping of element symbol to mole fraction. All elements must
        be in both :data:`hea_bench.descriptors.data.elemental.ELEMENTAL_DATA`
        (for T_m) and the Miedema pair table (for ΔH_mix).

    Returns
    -------
    float
        Ω = (T_m · ΔS_mix) / |ΔH_mix|. Returns ``+inf`` when ΔH_mix is
        identically zero (ideal mixing — entropy wins unconditionally).

    Raises
    ------
    ValueError
        Propagated from the underlying descriptors if elements are
        missing from the data tables.

    Examples
    --------
    Cantor alloy CoCrFeMnNi at equimolar:

    >>> round(omega({"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}), 2)
    5.79
    """
    s = smix(composition)               # J/(mol·K)
    tm = melting_temperature(composition)  # K
    h = mixing_enthalpy(composition)    # kJ/mol

    if h == 0.0:
        return math.inf

    # T_m [K] · ΔS_mix [J/(mol·K)] = J/mol
    # |ΔH_mix| converted from kJ/mol to J/mol via factor 1000.
    return (tm * s) / (abs(h) * 1000.0)
