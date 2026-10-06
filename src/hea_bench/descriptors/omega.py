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
from itertools import combinations

from ..composition import Composition, accepts_formula, normalize
from .entropy import smix
from .melting import melting_temperature
from .miedema import mixing_enthalpy, pair_enthalpy


@accepts_formula
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


@accepts_formula
def omega_sensitivity(composition: Composition, perturbation_kj_mol: float = 2.0) -> dict:
    """How robust Omega is to the choice of Miedema pair table.

    Omega diverges as the mixing enthalpy approaches zero, so its value
    for near-ideal alloys depends strongly on which published pair table
    is used. This returns the per-pair contributions ``4 H_ij c_i c_j``,
    the element whose pairs dominate the enthalpy, and Omega recomputed
    with that element's pair enthalpies shifted by +/-
    ``perturbation_kj_mol`` (default 2 kJ/mol, the typical spread between
    published Miedema compilations). A wide Omega range means the
    verdict, not the number, is what to trust.

    Parameters
    ----------
    composition
        Mapping of element symbol to amount (normalized here), with at
        least two elements.
    perturbation_kj_mol
        Non-negative shift applied to the dominant element's pairs.

    Returns
    -------
    dict
        ``composition``, ``h_mix_kj_mol``, ``omega`` (None when the
        mixing enthalpy is exactly zero), ``pair_contributions``,
        ``dominant_element``, ``perturbation_kj_mol``,
        ``h_mix_range_kj_mol``, ``omega_at_range_endpoints``,
        ``diverges_within_range``, ``advice`` and ``source``.
    """
    if perturbation_kj_mol < 0:
        raise ValueError("perturbation_kj_mol must be non-negative")
    comp = dict(normalize(composition))
    if len(comp) < 2:
        raise ValueError("need at least two elements for pair contributions")

    contributions = []
    per_element: dict[str, float] = {el: 0.0 for el in comp}
    for a, b in combinations(sorted(comp), 2):
        h = pair_enthalpy(a, b)
        weight = 4.0 * comp[a] * comp[b]
        contrib = weight * h
        contributions.append(
            {"pair": f"{a}-{b}", "pair_enthalpy_kj_mol": h, "weight": weight,
             "contribution_kj_mol": contrib}
        )
        per_element[a] += abs(contrib)
        per_element[b] += abs(contrib)
    contributions.sort(key=lambda c: c["contribution_kj_mol"])

    dominant = max(per_element, key=lambda el: per_element[el])
    shift = perturbation_kj_mol * sum(
        c["weight"] for c in contributions if dominant in c["pair"].split("-")
    )

    h_mix = mixing_enthalpy(comp)
    t_m = melting_temperature(comp)
    s_mix = smix(comp)

    def omega_at(h: float) -> float | None:
        if h == 0:
            return None
        return t_m * s_mix / (abs(h) * 1000.0)

    h_low, h_high = h_mix - shift, h_mix + shift
    crosses_zero = h_low < 0 < h_high
    endpoint_omegas = [o for o in (omega_at(h_low), omega_at(h_high)) if o is not None]

    return {
        "composition": comp,
        "h_mix_kj_mol": h_mix,
        "omega": omega_at(h_mix),
        "pair_contributions": contributions,
        "dominant_element": dominant,
        "perturbation_kj_mol": perturbation_kj_mol,
        "h_mix_range_kj_mol": [h_low, h_high],
        "omega_at_range_endpoints": endpoint_omegas,
        "diverges_within_range": crosses_zero,
        "advice": (
            "The perturbation interval crosses h_mix = 0, so Omega is unbounded "
            "within the spread of published pair tables. Use the phase verdict, "
            "not the Omega magnitude." if crosses_zero else
            "Omega varies between the endpoint values across the typical spread "
            "of published Miedema pair tables."
        ),
        "source": "deBoer1988 / Takeuchi2005 pair table; Yang2012 Omega",
    }
