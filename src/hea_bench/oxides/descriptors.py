"""Closed-form HEO descriptors.

Every function here is a transparent algebraic expression over the
vendored Shannon-radius and electronegativity tables; nothing is
fitted. The structure-family wrappers in :mod:`hea_bench.oxides.families`
assemble these into complete reports with verdicts.

References
----------
Manchón-Gordón, A. F., et al. (2025). Descriptors for predicting
single- and multi-phase formation in high-entropy oxides: a unified
framework approach. *Materials* **18**, 3862.

Goldschmidt, V. M. (1926). Die Gesetze der Krystallochemie.
*Naturwissenschaften* **14**, 477-485.

Bartel, C. J., et al. (2019). New tolerance factor to predict the
stability of perovskite oxides and halides. *Science Advances* **5**,
eaav0693.

Spiridigliozzi, L., Ferone, C., Cioffi, R., & Dell'Agli, G. (2021).
A simple and effective predictor to design novel fluorite-structured
high entropy oxides (HEOs). *Acta Materialia* **202**, 181-189.

Subramanian, M. A., Aravamudan, G., & Subba Rao, G. V. (1983). Oxide
pyrochlores - a review. *Progress in Solid State Chemistry* **15**, 55-143.
"""

from __future__ import annotations

import math
from typing import Mapping

from ._data import OXIDE_ELEMENTS

#: Gas constant, J/(mol K).
R_GAS = 8.314462618

#: Shannon effective radius of O2- at six-fold coordination, angstroms.
#: The reference anion radius for the Goldschmidt and Bartel factors.
OXYGEN_RADIUS = 1.40


def normalize_site(fractions: Mapping[str, float]) -> dict[str, float]:
    """Normalize a sublattice occupancy mapping to mole fractions."""
    if not fractions:
        raise ValueError("sublattice composition must be non-empty")
    if any(v < 0 for v in fractions.values()):
        raise ValueError("occupancies must be non-negative")
    total = sum(fractions.values())
    if total <= 0:
        raise ValueError("occupancies must sum to a positive number")
    return {el: v / total for el, v in fractions.items() if v > 0}


def sublattice_entropy(
    sublattices: Mapping[str, Mapping[str, float]],
    multiplicities: Mapping[str, float],
    per: str = "formula",
) -> float:
    """Ideal configurational entropy of a multi-sublattice crystal.

    ``dS = -R * sum_k a_k * sum_i x_ik ln x_ik`` where ``a_k`` is the
    number of sites of sublattice ``k`` per formula unit and ``x_ik``
    the mole fraction of species ``i`` on it. Sublattices with a single
    species contribute zero, so a fully ordered oxygen sublattice can
    simply be omitted (anion disorder and oxygen vacancies are not
    modeled).

    Parameters
    ----------
    sublattices
        Sublattice label -> occupancy mapping (each normalized internally).
    multiplicities
        Sublattice label -> sites per formula unit (e.g. A=1, B=1 for
        ABO3; A=2, B=2 for A2B2O7).
    per
        ``"formula"`` (default) returns J/(mol K) per mole of formula
        units; ``"cation"`` divides by the total number of cation sites
        passed, which reduces to the alloy ``smix`` convention (1.61 R
        for five equimolar cations on one site) and is the value the
        1.5 R high-entropy threshold applies to.
    """
    if per not in ("formula", "cation"):
        raise ValueError(f'per must be "formula" or "cation", got {per!r}')
    total = 0.0
    sites = 0.0
    for label, comp in sublattices.items():
        a = multiplicities[label]
        norm = normalize_site(comp)
        total += a * sum(-x * math.log(x) for x in norm.values())
        sites += a
    entropy = R_GAS * total
    return entropy if per == "formula" else entropy / sites


def size_disorder(fractions: Mapping[str, float], radii: Mapping[str, float]) -> float:
    """Cation size-disorder parameter for one sublattice, in percent.

    ``delta = 100 * sqrt( sum_i x_i (1 - r_i / r_mean)^2 )``, the ionic
    analog of the alloy delta parameter, with Shannon radii in place of
    metallic radii (Manchón-Gordón et al. 2025).
    """
    norm = normalize_site(fractions)
    r_mean = sum(x * radii[el] for el, x in norm.items())
    inner = sum(x * (1.0 - radii[el] / r_mean) ** 2 for el, x in norm.items())
    return 100.0 * math.sqrt(max(inner, 0.0))


def combined_size_disorder(*deltas: float) -> float:
    """Two-sublattice combination ``delta_r* = sqrt(delta_A^2 + delta_B^2)``."""
    return math.sqrt(sum(d * d for d in deltas))


def radius_sample_std(radii: list[float]) -> float:
    """Sample standard deviation (ddof=1) of cation radii, in angstroms.

    This is the exact convention of the Spiridigliozzi fluorite
    predictor: the plain, unweighted standard deviation of the
    constituent cation radii (eight-fold Shannon values, equimolar
    compositions), with the n-1 denominator. Verified against the
    published value for (Ce,Zr,Nd,Y,Er)O1.7 (SD = 0.0976 A).
    """
    if len(radii) < 2:
        raise ValueError("need at least two cations for a standard deviation")
    mean = sum(radii) / len(radii)
    return math.sqrt(sum((r - mean) ** 2 for r in radii) / (len(radii) - 1))


def goldschmidt_t(r_a: float, r_b: float, r_o: float = OXYGEN_RADIUS) -> float:
    """Goldschmidt tolerance factor ``t = (rA + rO) / (sqrt(2) (rB + rO))``."""
    return (r_a + r_o) / (math.sqrt(2.0) * (r_b + r_o))


def octahedral_factor(r_b: float, r_o: float = OXYGEN_RADIUS) -> float:
    """Octahedral factor ``mu = rB / rO``; a stable BO6 needs 0.414 < mu < 0.732."""
    return r_b / r_o


def bartel_tau(r_a: float, r_b: float, n_a: float, r_x: float = OXYGEN_RADIUS) -> float:
    """Bartel tolerance factor tau; tau < 4.18 predicts a perovskite.

    ``tau = rX/rB - nA (nA - (rA/rB) / ln(rA/rB))`` with ``nA`` the
    (composition-weighted mean) oxidation state of the A site. Defined
    for ``rA > rB``; raises otherwise, since ln(rA/rB) changes sign.
    """
    if r_a <= r_b:
        raise ValueError(
            f"bartel_tau requires rA > rB (got rA={r_a:.3f}, rB={r_b:.3f}); "
            f"the larger cation belongs on the A site"
        )
    ratio = r_a / r_b
    return r_x / r_b - n_a * (n_a - ratio / math.log(ratio))


def radius_ratio(r_a: float, r_b: float) -> float:
    """Plain A/B radius ratio (pyrochlore window: 1.46 < rA/rB < 1.78)."""
    return r_a / r_b


def mean_chi(fractions: Mapping[str, float]) -> float:
    """Composition-weighted mean Pauling electronegativity of the cations."""
    norm = normalize_site(fractions)
    chis = {el: OXIDE_ELEMENTS[el]["chi"] for el in norm}
    missing = sorted(el for el, chi in chis.items() if chi is None)
    if missing:
        raise ValueError(f"no Pauling electronegativity for: {', '.join(missing)}")
    return sum(x * chis[el] for el, x in norm.items())


def delta_chi(fractions: Mapping[str, float]) -> float:
    """Composition-weighted std of cation electronegativities (Pauling scale).

    Same convention as the alloy-side ``hea_bench.delta_chi``.
    """
    norm = normalize_site(fractions)
    chi_bar = mean_chi(norm)
    inner = sum(x * (OXIDE_ELEMENTS[el]["chi"] - chi_bar) ** 2 for el, x in norm.items())
    return math.sqrt(max(inner, 0.0))
