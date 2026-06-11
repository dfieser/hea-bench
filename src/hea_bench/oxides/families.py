"""Structure-family reports for high-entropy oxides.

Each ``describe_*`` function takes cation occupancies (amounts need not
sum to 1; they are normalized per sublattice), solves the
charge-neutrality oxidation-state assignment, looks up the Shannon
radii at the family's coordination numbers, and returns one dict with
the descriptors, the rule verdicts, and every warning produced along
the way. The verdict thresholds and their sources:

- Configurational entropy: >= 1.5 R "high-entropy", 1.36-1.5 R
  "medium-entropy", classified on the most-disordered sublattice (per
  site of that sublattice). This is the HEO literature convention: an
  ABO3 with five equimolar B cations is a high-entropy perovskite
  (1.61 R on the B sublattice) even though the value per total cation
  site is half that. Both normalizations are reported.
- Perovskite Goldschmidt window 0.92 <= t <= 1.04 (Manchón-Gordón et
  al. 2025 compilation; the classic textbook window is 0.9-1.0 and the
  bound is configurable), octahedral factor 0.414 < mu < 0.732, and
  Bartel tau < 4.18 (Bartel et al. 2019, ~91% reported accuracy).
- Fluorite: sample standard deviation of the eight-fold cation radii
  > 0.095 A predicts a single-phase (entropy-stabilized) fluorite;
  below it, bixbyite-type or mixed phases are expected (Spiridigliozzi
  et al. 2021; convention verified against their published SD values).
  Calibrated on equimolar rare-earth-based five-cation oxides — treat
  verdicts outside that domain as extrapolation.
- Pyrochlore: 1.46 < rA/rB < 1.78 (Subramanian et al. 1983); below the
  window a defect fluorite is expected, above it no single cubic phase.

All verdicts are weak empirical screens, exactly like the alloy-side
rules: calibrated on small historical datasets, never ground truth.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from .descriptors import (
    OXYGEN_RADIUS,
    R_GAS,
    bartel_tau,
    combined_size_disorder,
    delta_chi,
    goldschmidt_t,
    mean_chi,
    normalize_site,
    octahedral_factor,
    radius_ratio,
    radius_sample_std,
    size_disorder,
    sublattice_entropy,
)
from .radii import shannon_radius
from .states import assign_oxidation_states

StatesArg = Mapping[str, Sequence[int]] | None


def _radii_for(
    norm: dict[str, float],
    states: dict[str, int],
    coordination: int,
    spin: str,
    warnings: list[str],
) -> dict[str, float]:
    radii = {}
    for el in norm:
        radius, notes = shannon_radius(el, states[el], coordination, spin)
        radii[el] = radius
        warnings.extend(notes)
    return radii


def _entropy_verdict(s_per_cation: float) -> str:
    if s_per_cation >= 1.5 * R_GAS:
        return "high-entropy"
    if s_per_cation >= 1.36 * R_GAS:
        return "medium-entropy"
    return "low-entropy"


def _window_verdict(value: float, low: float, high: float) -> str:
    if value < low:
        return "below-window"
    if value > high:
        return "above-window"
    return "within-window"


def _chi_stats(pooled: dict[str, float], warnings: list[str]) -> tuple[float | None, float | None]:
    try:
        return mean_chi(pooled), delta_chi(pooled)
    except ValueError as exc:
        warnings.append(str(exc))
        return None, None


def describe_rock_salt(
    cations: Mapping[str, float],
    states: StatesArg = None,
    spin: str = "high",
) -> dict:
    """Descriptor report for a rock-salt oxide MO (cations six-fold).

    Examples
    --------
    >>> r = describe_rock_salt({"Mg": 1, "Co": 1, "Ni": 1, "Cu": 1, "Zn": 1})
    >>> r["verdicts"]["entropy"]
    'high-entropy'
    """
    norm = normalize_site(cations)
    warnings: list[str] = []
    ox, w = assign_oxidation_states(norm, target_charge=2.0, allowed=states)
    warnings.extend(w)
    radii = _radii_for(norm, ox, 6, spin, warnings)
    s_formula = sublattice_entropy({"M": norm}, {"M": 1.0})
    chi_bar, d_chi = _chi_stats(dict(norm), warnings)
    return {
        "family": "rock_salt",
        "sites": {"M": norm},
        "oxygen_per_formula_unit": 1.0,
        "oxidation_states": ox,
        "coordination": {"M": 6},
        "shannon_radii": radii,
        "descriptors": {
            "s_config": s_formula,
            "s_config_per_cation": s_formula,
            "s_config_per_site": {"M": s_formula},
            "delta_r": size_disorder(norm, radii),
            "mean_radius": sum(x * radii[el] for el, x in norm.items()),
            "mean_chi": chi_bar,
            "delta_chi": d_chi,
        },
        "verdicts": {"entropy": _entropy_verdict(s_formula)},
        "warnings": warnings,
    }


def describe_fluorite(
    cations: Mapping[str, float],
    oxygen: float = 2.0,
    states: StatesArg = None,
    spin: str = "high",
) -> dict:
    """Descriptor report for a fluorite oxide MO_x (cations eight-fold).

    ``oxygen`` is the O content per cation formula unit; rare-earth
    systems are typically oxygen-deficient (e.g. ``oxygen=1.7`` for an
    equimolar 4+/3+ mix), and the charge balance is solved against
    ``2 * oxygen``.

    Examples
    --------
    The Spiridigliozzi Low_SD sample (Ce,Zr,Nd,Y,Er)O1.7:

    >>> r = describe_fluorite(
    ...     {"Ce": 1, "Zr": 1, "Nd": 1, "Y": 1, "Er": 1}, oxygen=1.7)
    >>> round(r["descriptors"]["radius_sigma"], 4)
    0.0976
    """
    norm = normalize_site(cations)
    warnings: list[str] = []
    ox, w = assign_oxidation_states(norm, target_charge=2.0 * oxygen, allowed=states)
    warnings.extend(w)
    radii = _radii_for(norm, ox, 8, spin, warnings)
    s_formula = sublattice_entropy({"M": norm}, {"M": 1.0})

    sigma = None
    sigma_verdict = None
    if len(norm) >= 2:
        fracs = list(norm.values())
        if max(fracs) - min(fracs) > 1e-9:
            warnings.append(
                "the fluorite radius-dispersion criterion is calibrated on equimolar "
                "compositions; this composition is not equimolar"
            )
        sigma = radius_sample_std(list(radii.values()))
        sigma_verdict = "fluorite" if sigma > 0.095 else "bixbyite-or-multiphase"
    else:
        warnings.append("the fluorite radius-dispersion criterion needs at least two cations")

    chi_bar, d_chi = _chi_stats(dict(norm), warnings)
    return {
        "family": "fluorite",
        "sites": {"M": norm},
        "oxygen_per_formula_unit": oxygen,
        "oxidation_states": ox,
        "coordination": {"M": 8},
        "shannon_radii": radii,
        "descriptors": {
            "s_config": s_formula,
            "s_config_per_cation": s_formula,
            "s_config_per_site": {"M": s_formula},
            "delta_r": size_disorder(norm, radii),
            "mean_radius": sum(x * radii[el] for el, x in norm.items()),
            "radius_sigma": sigma,
            "mean_chi": chi_bar,
            "delta_chi": d_chi,
        },
        "verdicts": {
            "entropy": _entropy_verdict(s_formula),
            "spiridigliozzi": sigma_verdict,
        },
        "warnings": warnings,
    }


def _two_site_report(
    family: str,
    a_site: Mapping[str, float],
    b_site: Mapping[str, float],
    site_multiplicity: float,
    oxygen: float,
    cn_a: int,
    cn_b: int,
    states: StatesArg,
    spin: str,
) -> tuple[dict, dict[str, float], dict[str, float], dict, list[str]]:
    norm_a = normalize_site(a_site)
    norm_b = normalize_site(b_site)
    shared = set(norm_a) & set(norm_b)
    if shared:
        raise ValueError(
            f"{', '.join(sorted(shared))} appears on both sublattices; site-resolved "
            f"oxidation states are not supported — describe the sites separately"
        )
    warnings: list[str] = []
    moles = {el: x * site_multiplicity for el, x in norm_a.items()}
    moles.update({el: x * site_multiplicity for el, x in norm_b.items()})
    groups = {el: "A" for el in norm_a}
    groups.update({el: "B" for el in norm_b})
    ox, w = assign_oxidation_states(
        moles, target_charge=2.0 * oxygen, allowed=states, groups=groups
    )
    warnings.extend(w)
    radii_a = _radii_for(norm_a, ox, cn_a, spin, warnings)
    radii_b = _radii_for(norm_b, ox, cn_b, spin, warnings)

    s_formula = sublattice_entropy(
        {"A": norm_a, "B": norm_b},
        {"A": site_multiplicity, "B": site_multiplicity},
    )
    s_cation = s_formula / (2.0 * site_multiplicity)
    s_site_a = sublattice_entropy({"A": norm_a}, {"A": 1.0})
    s_site_b = sublattice_entropy({"B": norm_b}, {"B": 1.0})
    pooled = dict(moles)
    chi_bar, d_chi = _chi_stats(pooled, warnings)

    delta_a = size_disorder(norm_a, radii_a)
    delta_b = size_disorder(norm_b, radii_b)
    report = {
        "family": family,
        "sites": {"A": norm_a, "B": norm_b},
        "oxygen_per_formula_unit": oxygen,
        "oxidation_states": ox,
        "coordination": {"A": cn_a, "B": cn_b},
        "shannon_radii": {**radii_a, **radii_b},
        "descriptors": {
            "s_config": s_formula,
            "s_config_per_cation": s_cation,
            "s_config_per_site": {"A": s_site_a, "B": s_site_b},
            "delta_r_a": delta_a,
            "delta_r_b": delta_b,
            "delta_r_star": combined_size_disorder(delta_a, delta_b),
            "mean_radius_a": sum(x * radii_a[el] for el, x in norm_a.items()),
            "mean_radius_b": sum(x * radii_b[el] for el, x in norm_b.items()),
            "mean_chi": chi_bar,
            "delta_chi": d_chi,
        },
        "verdicts": {"entropy": _entropy_verdict(max(s_site_a, s_site_b))},
        "warnings": warnings,
    }
    return report, norm_a, norm_b, ox, warnings


def describe_perovskite(
    a_site: Mapping[str, float],
    b_site: Mapping[str, float],
    states: StatesArg = None,
    spin: str = "high",
    t_window: tuple[float, float] = (0.92, 1.04),
) -> dict:
    """Descriptor report for a perovskite ABO3 (A twelve-fold, B six-fold).

    Examples
    --------
    Jiang et al. 2018's Sr(Zr,Sn,Ti,Hf,Mn)O3 (single-phase cubic):

    >>> r = describe_perovskite(
    ...     {"Sr": 1}, {"Zr": 1, "Sn": 1, "Ti": 1, "Hf": 1, "Mn": 1})
    >>> r["verdicts"]["bartel"]
    'perovskite'
    """
    report, norm_a, norm_b, ox, warnings = _two_site_report(
        "perovskite", a_site, b_site, 1.0, 3.0, 12, 6, states, spin
    )
    d = report["descriptors"]
    r_a, r_b = d["mean_radius_a"], d["mean_radius_b"]
    n_a = sum(x * ox[el] for el, x in norm_a.items())
    t = goldschmidt_t(r_a, r_b)
    mu = octahedral_factor(r_b)
    try:
        tau = bartel_tau(r_a, r_b, n_a)
        tau_verdict = "perovskite" if tau < 4.18 else "nonperovskite"
    except ValueError as exc:
        warnings.append(str(exc))
        tau, tau_verdict = None, None
    d.update({"goldschmidt_t": t, "octahedral_mu": mu, "bartel_tau": tau, "mean_n_a": n_a})
    report["verdicts"].update(
        {
            "goldschmidt": _window_verdict(t, *t_window),
            "octahedral": _window_verdict(mu, 0.414, 0.732),
            "bartel": tau_verdict,
        }
    )
    return report


def describe_pyrochlore(
    a_site: Mapping[str, float],
    b_site: Mapping[str, float],
    states: StatesArg = None,
    spin: str = "high",
) -> dict:
    """Descriptor report for a pyrochlore A2B2O7 (A eight-fold, B six-fold).

    Examples
    --------
    >>> r = describe_pyrochlore(
    ...     {"La": 1, "Ce": 1, "Nd": 1, "Sm": 1, "Eu": 1}, {"Zr": 1})
    >>> r["verdicts"]["radius_ratio"]
    'pyrochlore'
    """
    report, _, _, _, _ = _two_site_report(
        "pyrochlore", a_site, b_site, 2.0, 7.0, 8, 6, states, spin
    )
    d = report["descriptors"]
    ratio = radius_ratio(d["mean_radius_a"], d["mean_radius_b"])
    if ratio < 1.46:
        verdict = "defect-fluorite"
    elif ratio > 1.78:
        verdict = "no-single-cubic-phase"
    else:
        verdict = "pyrochlore"
    d["radius_ratio"] = ratio
    report["verdicts"]["radius_ratio"] = verdict
    return report


__all__ = [
    "OXYGEN_RADIUS",
    "describe_fluorite",
    "describe_perovskite",
    "describe_pyrochlore",
    "describe_rock_salt",
]
