"""The alloy, oxide, ceramic and element reports behind the MCP calculator tools.

Every numeric value carries its unit and the citation key of its
parametrization (``SOURCES`` in :mod:`hea_bench.service._payload`). A
value that cannot be computed for one composition becomes a null plus a
warning, so one bad value does not sink a batch.
"""

import hea_bench as hb

from .._json import json_safe
from ..ceramics import describe_diboride, describe_rock_salt_carbide, describe_rock_salt_nitride
from ..descriptors.backend import UNITS
from ..descriptors.miedema_decomposition import miedema_decomposition
from ..oxides import (
    describe_fluorite,
    describe_perovskite,
    describe_pyrochlore,
    describe_rock_salt,
)
from ..rules import (
    guo_vec,
    king_phi,
    senkov_kappa,
    sheikh_ductility,
    tsai_sigma,
    yang_omega,
    ye_phi,
    yeh_smix,
    zhang_delta,
)
from ._payload import parse


#: MCP descriptor name -> (native descriptor name, citation key). Only
#: the MCP-facing aliases and citation keys live here; the callable and
#: unit string are pulled from the descriptor backend registry below, so
#: the two surfaces cannot drift apart.
_DESCRIPTOR_TABLE = {
    "s_mix": ("smix", "Boltzmann"),
    "delta": ("delta", "Zhang2008"),
    "vec": ("vec", "Guo2011"),
    "t_melt_mean": ("melting_temperature", "CRC"),
    "h_mix": ("mixing_enthalpy", "Takeuchi2005"),
    "omega": ("omega", "Yang2012"),
    "delta_chi": ("delta_chi", "Pauling"),
    "chi_mean": ("mean_electronegativity", "Pauling"),
    "s_excess": ("s_excess", "Mansoori1971"),
    "delta_g_ss": ("delta_g_ss", "King2016"),
    "delta_g_max": ("delta_g_max", "King2016"),
    "phi_king": ("phi_king", "King2016"),
    "phi_ye": ("phi_ye", "Ye2015"),
    "lambda_singh": ("singh_lambda", "Singh2014"),
    "gamma_wang": ("wang_gamma", "Wang2015"),
    "h_elastic": ("h_elastic", "Andreoli2019"),
}

#: descriptor name -> (callable, unit, source key). The callables all take
#: a normalized composition mapping.
_DESCRIPTORS = {
    name: (getattr(hb, native), UNITS[native], source)
    for name, (native, source) in _DESCRIPTOR_TABLE.items()
}

#: Why a value can be legitimately non-finite, keyed by MCP descriptor
#: name; used to explain nulled values in warnings. Names absent here
#: get the King-family reason: their divergence comes from the same
#: no-competing-intermetallic denominator.
_DIVERGENCE_REASONS = {
    "lambda_singh": (
        "all constituents share the same tabulated radius, so "
        "delta = 0 and Lambda is unbounded, trivially inside the "
        "single-solid-solution band"
    ),
    "omega": (
        "the mixing enthalpy is zero, so Omega diverges for this "
        "near-ideal mixture, and omega_sensitivity tests how stable that is"
    ),
}
_DEFAULT_DIVERGENCE = "no competing intermetallic, which leaves the verdict unaffected"

_OXIDE_FAMILIES = {
    "rock_salt": (describe_rock_salt, ["Rost2015", "Shannon1976", "ManchonGordon2025"]),
    "perovskite": (describe_perovskite, ["Goldschmidt1926", "Bartel2019", "Shannon1976", "ManchonGordon2025"]),
    "fluorite": (describe_fluorite, ["Spiridigliozzi2021", "Shannon1976"]),
    "pyrochlore": (describe_pyrochlore, ["Subramanian1983", "Shannon1976"]),
}

_CERAMIC_STRUCTURES = {
    "rock_salt_carbide": describe_rock_salt_carbide,
    "rock_salt_nitride": describe_rock_salt_nitride,
    "diboride": describe_diboride,
}


def parse_composition(formula: str) -> dict:
    """A formula as normalized mole fractions."""
    comp = parse(formula)
    return {"input": formula, "composition": comp}


def alloy_descriptors(
    compositions: list[str],
    king_temperature: float | None = None,
    custom_elements: dict[str, dict] | None = None,
    pair_enthalpies: dict[str, float] | None = None,
) -> dict:
    """Every alloy descriptor, with unit and citation key, for a batch."""
    results = []
    with hb.custom_data(elements=custom_elements, pair_enthalpies=pair_enthalpies):
        for formula in compositions:
            comp = parse(formula)
            descriptors: dict[str, dict] = {}
            warnings: list[str] = []
            for name, (func, unit, source) in _DESCRIPTORS.items():
                try:
                    if name == "phi_king" and king_temperature is not None:
                        value = func(comp, temperature=king_temperature)
                    else:
                        value = func(comp)
                except Exception as exc:
                    descriptors[name] = {"value": None, "unit": unit, "source": source}
                    warnings.append(f"{name}: not computable for {formula!r} ({exc})")
                    continue
                safe = json_safe(value)
                descriptors[name] = {"value": safe, "unit": unit, "source": source}
                if safe is None and value is not None:
                    reason = _DIVERGENCE_REASONS.get(name, _DEFAULT_DIVERGENCE)
                    warnings.append(f"{name}: value is unbounded for {formula!r} ({reason})")
                elif value is None:
                    warnings.append(
                        f"{name}: not computable for {formula!r} "
                        f"(an element lacks the required per-element data)"
                    )
            miedema = miedema_decomposition(comp)
            warnings.extend(miedema.pop("warnings"))
            results.append(
                {
                    "input": formula,
                    "composition": comp,
                    "descriptors": descriptors,
                    "miedema_enthalpies": {**miedema, "unit": "kJ/mol", "source": "deBoer1988"},
                    "warnings": warnings,
                }
            )
    return {"results": results}


def alloy_rules(
    compositions: list[str],
    king_temperature: float | None = None,
    custom_elements: dict[str, dict] | None = None,
    pair_enthalpies: dict[str, float] | None = None,
) -> dict:
    """The nine phase rules, with value, threshold and citation key, for a batch."""
    with hb.custom_data(elements=custom_elements, pair_enthalpies=pair_enthalpies):
        return _alloy_rules(compositions, king_temperature)


def _alloy_rules(compositions: list[str], king_temperature: float | None) -> dict:
    def fixed(module, value_func, **predict_kw):
        """Rule whose verdict comes with a descriptor value and static threshold."""
        def evaluate(comp):
            return module.predict(comp, **predict_kw), value_func(comp), {}
        return evaluate

    def guo_evaluate(comp):
        return guo_vec.predict(comp), hb.vec(comp), {"note": guo_vec.boundary_note(comp)}

    def senkov_evaluate(comp):
        kp = senkov_kappa.predict(comp, temperature=king_temperature)
        return kp.verdict, kp.k1, {
            "threshold": json_safe(kp.k1_cr),
            "temperature_K": kp.temperature_K,
            "im_pair": list(kp.im_pair) if kp.im_pair else None,
            "note": kp.note,
        }

    def tsai_evaluate(comp):
        sp = tsai_sigma.predict(comp)
        return sp.verdict, sp.vec, {}

    def sheikh_evaluate(comp):
        dp = sheikh_ductility.predict(comp)
        return dp.verdict, dp.vec, {}

    if king_temperature is not None:
        king_evaluate = fixed(
            king_phi,
            lambda c: hb.phi_king(c, temperature=king_temperature),
            temperature_policy=king_temperature,
        )
    else:
        king_evaluate = fixed(king_phi, hb.phi_king)

    # (payload name, citation key, static threshold, evaluate, divergence
    # reason). evaluate(comp) -> (verdict, raw value, payload overrides);
    # the overrides carry dynamic thresholds and rule-specific extras.
    # The payload name for the entropy rule is "yeh_entropy"; the library
    # registry accepts it as an alias of yeh_smix wherever rules are
    # named (see hea_bench.rules.RULE_ALIASES).
    rule_specs = (
        ("yeh_entropy", "Yeh2004", "1.0R / 1.5R class bounds",
         fixed(yeh_smix, hb.smix), None),
        ("zhang_delta", "Zhang2008", zhang_delta.DEFAULT_THRESHOLD,
         fixed(zhang_delta, hb.delta), None),
        ("guo_vec", "Guo2011", "FCC >= 8.0, BCC < 6.87",
         guo_evaluate, None),
        ("yang_omega", "Yang2012", yang_omega.DEFAULT_THRESHOLD,
         fixed(yang_omega, hb.omega), _DIVERGENCE_REASONS["omega"]),
        ("king_phi", "King2016", king_phi.DEFAULT_THRESHOLD,
         king_evaluate, None),
        ("ye_phi", "Ye2015", ye_phi.DEFAULT_THRESHOLD,
         fixed(ye_phi, hb.phi_ye), None),
        ("senkov_kappa", "SenkovMiracle2016", None, senkov_evaluate, None),
        ("tsai_sigma", "Tsai2013", "Cr/V present and 6.88 <= VEC <= 7.84",
         tsai_evaluate, None),
        ("sheikh_ductility", "Sheikh2016",
         "VEC < 4.5 ductile, >= 4.6 brittle (bcc RHEAs of Ti, Zr, Hf, V, Nb, Ta, Cr, Mo, W only)",
         sheikh_evaluate, None),
    )

    results = []
    for formula in compositions:
        comp = parse(formula)
        rules: dict[str, dict] = {}
        warnings: list[str] = []
        for name, source, threshold, evaluate, divergence in rule_specs:
            try:
                verdict, raw, overrides = evaluate(comp)
            except Exception as exc:
                rules[name] = {
                    "verdict": None,
                    "value": None,
                    "threshold": threshold,
                    "source": source,
                }
                warnings.append(f"{name}: not computable for {formula!r} ({exc})")
                continue
            value = json_safe(raw)
            entry = {
                "verdict": verdict,
                "value": value,
                "threshold": threshold,
                "source": source,
            }
            entry.update(overrides)
            rules[name] = entry
            if value is None and raw is not None:
                reason = divergence or "no competing intermetallic"
                warnings.append(
                    f"{name}: value is unbounded for {formula!r} "
                    f"({reason}), which leaves the verdict unaffected"
                )
        results.append(
            {"input": formula, "composition": comp, "rules": rules, "warnings": warnings}
        )
    return {"results": results}


def omega_sensitivity(
    composition: str,
    perturbation_kj_mol: float = 2.0,
    custom_elements: dict[str, dict] | None = None,
    pair_enthalpies: dict[str, float] | None = None,
) -> dict:
    """Omega with the dominant element's pair enthalpies perturbed."""
    with hb.custom_data(elements=custom_elements, pair_enthalpies=pair_enthalpies):
        report = hb.omega_sensitivity(parse(composition), perturbation_kj_mol)
    return {"input": composition, **report}


def oxide_report(
    family: str,
    cations: str,
    b_site_cations: str | None = None,
    oxygen_per_formula_unit: float | None = None,
    spin: str = "high",
) -> dict:
    """The formability report for one high-entropy oxide composition."""
    if family not in _OXIDE_FAMILIES:
        raise ValueError(
            f"unknown family {family!r}: expected one of {sorted(_OXIDE_FAMILIES)}"
        )
    describe, sources = _OXIDE_FAMILIES[family]
    site_a = parse(cations)

    if family in ("perovskite", "pyrochlore"):
        if not b_site_cations:
            raise ValueError(f"{family} requires b_site_cations (the B sublattice)")
        report = describe(site_a, parse(b_site_cations), spin=spin)
    elif family == "fluorite":
        if oxygen_per_formula_unit is not None:
            report = describe(site_a, oxygen=oxygen_per_formula_unit, spin=spin)
        else:
            report = describe(site_a, spin=spin)
    else:
        report = describe(site_a, spin=spin)

    report = dict(report)
    report["sources"] = sources
    return report


def ceramic_report(structure: str, metals: str) -> dict:
    """Composition-only descriptors for a carbide, nitride or diboride."""
    if structure not in _CERAMIC_STRUCTURES:
        raise ValueError(
            f"unknown structure {structure!r}: expected one of {sorted(_CERAMIC_STRUCTURES)}"
        )
    return dict(_CERAMIC_STRUCTURES[structure](parse(metals)))


def element_data(elements: list[str] | None = None) -> dict:
    """The tabulated values behind every number, per element."""
    from ..descriptors.elements import element_data as tabulated

    return tabulated(elements)


def element_coverage() -> dict:
    """Which elements each data table covers."""
    from ..descriptors.data.elemental import ELEMENTAL_DATA
    from ..oxides._data import OXIDE_ELEMENTS

    return {
        "alloy_descriptors_and_rules": sorted(ELEMENTAL_DATA),
        "alloy_count": len(ELEMENTAL_DATA),
        "miedema_pair_table_note": (
            "The vendored Miedema pair-enthalpy table extends mixing-enthalpy "
            "estimates to 75 elements in total."
        ),
        "oxide_shannon_table": sorted(OXIDE_ELEMENTS),
        "oxide_count": len(OXIDE_ELEMENTS),
    }
