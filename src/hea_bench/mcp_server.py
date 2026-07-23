"""Model Context Protocol (MCP) surface for hea-bench.

Exposes the parity-tested calculator to LLM agents as a small set of
deterministic, batch-oriented tools. Design follows the published
MCP-for-science experience: few tools, explicit typed schemas, bounded
execution, structured errors, and provenance in-band — every numeric
result carries its unit, the citation key of its parametrization, and
the library version, so an agent's reasoning trace contains auditable
receipts rather than bare floats.

The tool bodies below are plain functions with no MCP dependency, so
they are unit-tested in CI like the rest of the library. The ``mcp``
package (``pip install hea-bench[mcp]``) is imported lazily only by
:func:`build_server` / :func:`main`.

Run the server over stdio::

    hea-bench-mcp

or register it with an MCP client (Claude Desktop, Cursor, ...)::

    {"command": "hea-bench-mcp"}
"""

from __future__ import annotations

import math
from itertools import combinations

import hea_bench as hb
from . import __version__
from .descriptors.miedema import pair_enthalpy
from .oxides import (
    describe_fluorite,
    describe_perovskite,
    describe_pyrochlore,
    describe_rock_salt,
)
from .rules import (
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

#: Citation keys -> short reference strings, returned by ``about()`` and
#: referenced by the per-value ``source`` fields.
SOURCES = {
    "Boltzmann": "Classical ideal configurational entropy, -R sum(c ln c).",
    "Zhang2008": "Zhang et al. (2008). Adv. Eng. Mater. 10, 534. delta rule.",
    "Guo2011": "Guo & Liu (2011). Prog. Nat. Sci. 21, 433. VEC rule.",
    "Yang2012": "Yang & Zhang (2012). Mater. Chem. Phys. 132, 233. Omega rule.",
    "Yeh2004": "Yeh et al. (2004). Adv. Eng. Mater. 6, 299. Entropy classes.",
    "King2016": "King et al. (2016). Acta Mater. 104, 172. Phi criterion.",
    "Ye2015": "Ye et al. (2015). Scripta Mater. 104, 53. phi criterion.",
    "Mansoori1971": "Mansoori et al. (1971). J. Chem. Phys. 54, 1523. Hard-sphere excess entropy.",
    "deBoer1988": "de Boer et al. (1988). Cohesion in Metals. Miedema parametrization.",
    "Takeuchi2005": "Takeuchi & Inoue (2005). Mater. Trans. 46, 2817. Pair-enthalpy table.",
    "Pauling": "Pauling electronegativities from the vendored element table.",
    "CRC": "Melting points (CRC Handbook) from the curated 55-element table.",
    "LA4003": "Teatum, Gschneidner & Waber (1968). LA-4003. CN12 metallic radii.",
    "MS2017": "Miracle & Senkov (2017). Acta Mater. 122, 448. Review; Table 3 cross-checks.",
    "Singh2014": "Singh et al. (2014). Intermetallics 53, 112. Lambda = S_mix/delta^2.",
    "Wang2015": "Wang et al. (2015). Scripta Mater. 94, 28. Solid-angle gamma.",
    "SenkovMiracle2016": "Senkov & Miracle (2016). J. Alloys Compd. 658, 603. k1 vs k1_cr(T).",
    "Andreoli2019": "Andreoli et al. (2019). Materialia 5, 100222. Elastic-strain energy.",
    "Tsai2013": "Tsai et al. (2013). Mater. Res. Lett. 1, 207. Sigma-phase VEC window.",
    "Sheikh2016": "Sheikh et al. (2016). J. Appl. Phys. 120, 164902. RHEA ductility VEC.",
    "Shannon1976": "Shannon (1976). Acta Cryst. A32, 751. Effective ionic radii.",
    "Goldschmidt1926": "Goldschmidt (1926). Naturwissenschaften 14, 477. Tolerance factor.",
    "Bartel2019": "Bartel et al. (2019). Sci. Adv. 5, eaav0693. tau factor.",
    "Spiridigliozzi2021": "Spiridigliozzi et al. (2021). Acta Mater. 202, 181. Fluorite sigma rule.",
    "Subramanian1983": "Subramanian et al. (1983). Prog. Solid State Chem. 15, 55. Pyrochlore window.",
    "ManchonGordon2025": "Manchon-Gordon et al. (2025). Materials 18, 3862. HEO descriptor windows.",
    "Rost2015": "Rost et al. (2015). Nat. Commun. 6, 8485. Entropy-stabilized oxides.",
}

#: descriptor name -> (callable, unit, source key). The callables all take
#: a normalized composition mapping.
_DESCRIPTORS = {
    "s_mix": (hb.smix, "J/(mol K)", "Boltzmann"),
    "delta": (hb.delta, "%", "Zhang2008"),
    "vec": (hb.vec, "electrons/atom", "Guo2011"),
    "t_melt_mean": (hb.melting_temperature, "K", "CRC"),
    "h_mix": (hb.mixing_enthalpy, "kJ/mol", "Takeuchi2005"),
    "omega": (hb.omega, "dimensionless", "Yang2012"),
    "delta_chi": (hb.delta_chi, "Pauling scale", "Pauling"),
    "chi_mean": (hb.mean_electronegativity, "Pauling scale", "Pauling"),
    "s_excess": (hb.s_excess, "J/(mol K)", "Mansoori1971"),
    "delta_g_ss": (hb.delta_g_ss, "kJ/mol", "King2016"),
    "delta_g_max": (hb.delta_g_max, "kJ/mol", "King2016"),
    "phi_king": (hb.phi_king, "dimensionless", "King2016"),
    "phi_ye": (hb.phi_ye, "dimensionless", "Ye2015"),
    "lambda_singh": (hb.singh_lambda, "J/(mol K %^2)", "Singh2014"),
    "gamma_wang": (hb.wang_gamma, "dimensionless", "Wang2015"),
    "h_elastic": (hb.h_elastic, "kJ/mol", "Andreoli2019"),
}

_OXIDE_FAMILIES = {
    "rock_salt": (describe_rock_salt, ["Rost2015", "Shannon1976", "ManchonGordon2025"]),
    "perovskite": (describe_perovskite, ["Goldschmidt1926", "Bartel2019", "Shannon1976", "ManchonGordon2025"]),
    "fluorite": (describe_fluorite, ["Spiridigliozzi2021", "Shannon1976"]),
    "pyrochlore": (describe_pyrochlore, ["Subramanian1983", "Shannon1976"]),
}


def _stamp(payload: dict) -> dict:
    """Attach the library version to a tool response."""
    payload["hea_bench_version"] = __version__
    return payload


def _finite(value):
    """Return ``value`` unless it is a non-finite float, then ``None``.

    JSON has no representation for infinity or NaN, and emitting a bare
    ``Infinity`` token (which ``json.dumps`` does by default) produces
    output that strict MCP clients reject. The King Phi proxy is the one
    descriptor that legitimately diverges: when no binary intermetallic
    competes with the solid solution (every pair enthalpy is
    non-negative, e.g. HfNbTaTiZr) its denominator is zero and the value
    is ``+inf``. The verdict is unaffected, so we null the magnitude and
    flag it rather than break the response.
    """
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _parse(formula: str) -> dict[str, float]:
    """Parse and normalize a composition string, with a structured error."""
    try:
        return dict(hb.normalize(hb.parse_formula(formula)))
    except Exception as exc:
        raise ValueError(
            f"could not parse composition {formula!r}: {exc}. Use element "
            f"symbols with optional amounts, e.g. 'CoCrFeMnNi' or "
            f"'Co20Cu20Fe5Mn35Ni20' or 'Al0.3CoCrFeNi'."
        ) from None


def parse_composition(formula: str) -> dict:
    """Parse a chemical formula into normalized mole fractions.

    Accepts forms like ``CoCrFeMnNi`` (equimolar), ``Al0.3CoCrFeNi``, or
    ``Co20Cu20Fe5Mn35Ni20`` (percent-style amounts). Amounts are
    normalized to fractions that sum to 1.
    """
    comp = _parse(formula)
    return _stamp({"input": formula, "composition": comp})


def alloy_descriptors(compositions: list[str], king_temperature: float | None = None) -> dict:
    """Compute every alloy descriptor for a batch of compositions.

    Each value is returned with its unit and the citation key of its
    parametrization (see ``about()`` for the key -> reference map).
    Compositions containing elements outside the curated 55-element
    table return ``null`` for the affected descriptors plus a warning,
    never a silent wrong number.

    ``king_temperature`` (kelvin) optionally overrides the
    rule-of-mixtures melting temperature used by the King Phi proxy
    and the Senkov-Miracle kappa criterion.
    """
    results = []
    for formula in compositions:
        comp = _parse(formula)
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
            safe = _finite(value)
            descriptors[name] = {"value": safe, "unit": unit, "source": source}
            if safe is None and value is not None:
                if name == "lambda_singh":
                    reason = (
                        "all constituents share the same tabulated radius, so "
                        "delta = 0 and Lambda is unbounded (trivially in the "
                        "single-solid-solution band)"
                    )
                else:
                    reason = "no competing intermetallic; the verdict is unaffected"
                warnings.append(f"{name}: value is unbounded for {formula!r} ({reason})")
            elif value is None:
                warnings.append(
                    f"{name}: not computable for {formula!r} "
                    f"(an element lacks the required per-element data)"
                )
        results.append(
            {"input": formula, "composition": comp, "descriptors": descriptors, "warnings": warnings}
        )
    return _stamp({"results": results})


def alloy_rules(compositions: list[str], king_temperature: float | None = None) -> dict:
    """Apply the nine canonical empirical phase-prediction rules to a batch.

    Each verdict is returned with the descriptor value it was judged on
    and the published threshold, so the margin is auditable. These rules
    are weak empirical screens calibrated on small historical datasets;
    treat verdicts as hints, never ground truth.
    """
    results = []
    for formula in compositions:
        comp = _parse(formula)
        rules: dict[str, dict] = {}
        warnings: list[str] = []

        def apply(name, module, value_func, threshold, source, **kw):
            try:
                raw = value_func(comp) if value_func else None
                value = _finite(raw)
                rules[name] = {
                    "verdict": module.predict(comp, **kw),
                    "value": value,
                    "threshold": threshold,
                    "source": source,
                }
                if value is None and raw is not None:
                    warnings.append(
                        f"{name}: value is unbounded for {formula!r} "
                        f"(no competing intermetallic); the verdict is unaffected"
                    )
            except Exception as exc:
                rules[name] = {"verdict": None, "value": None, "threshold": threshold, "source": source}
                warnings.append(f"{name}: not computable for {formula!r} ({exc})")

        apply("yeh_entropy", yeh_smix, hb.smix, "1.0R / 1.5R class bounds", "Yeh2004")
        apply("zhang_delta", zhang_delta, hb.delta, zhang_delta.DEFAULT_THRESHOLD, "Zhang2008")
        apply("guo_vec", guo_vec, hb.vec, "FCC >= 8.0, BCC < 6.87", "Guo2011")
        apply("yang_omega", yang_omega, hb.omega, yang_omega.DEFAULT_THRESHOLD, "Yang2012")
        if king_temperature is not None:
            apply(
                "king_phi", king_phi, lambda c: hb.phi_king(c, temperature=king_temperature),
                king_phi.DEFAULT_THRESHOLD, "King2016", temperature_policy=king_temperature,
            )
        else:
            apply("king_phi", king_phi, hb.phi_king, king_phi.DEFAULT_THRESHOLD, "King2016")
        apply("ye_phi", ye_phi, hb.phi_ye, ye_phi.DEFAULT_THRESHOLD, "Ye2015")

        try:
            kp = senkov_kappa.predict(comp, temperature=king_temperature)
            rules["senkov_kappa"] = {
                "verdict": kp.verdict,
                "value": _finite(kp.k1),
                "threshold": _finite(kp.k1_cr),
                "temperature_K": kp.temperature_K,
                "source": "SenkovMiracle2016",
            }
        except Exception as exc:
            rules["senkov_kappa"] = {"verdict": None, "value": None, "threshold": None, "source": "SenkovMiracle2016"}
            warnings.append(f"senkov_kappa: not computable for {formula!r} ({exc})")

        try:
            sp = tsai_sigma.predict(comp)
            rules["tsai_sigma"] = {
                "verdict": sp.verdict,
                "value": sp.vec,
                "threshold": "Cr/V present and 6.88 <= VEC <= 7.84",
                "source": "Tsai2013",
            }
        except Exception as exc:
            rules["tsai_sigma"] = {"verdict": None, "value": None, "threshold": None, "source": "Tsai2013"}
            warnings.append(f"tsai_sigma: not computable for {formula!r} ({exc})")

        try:
            dp = sheikh_ductility.predict(comp)
            rules["sheikh_ductility"] = {
                "verdict": dp.verdict,
                "value": dp.vec,
                "threshold": "VEC < 4.5 ductile, >= 4.6 brittle (bcc RHEAs)",
                "source": "Sheikh2016",
            }
        except Exception as exc:
            rules["sheikh_ductility"] = {"verdict": None, "value": None, "threshold": None, "source": "Sheikh2016"}
            warnings.append(f"sheikh_ductility: not computable for {formula!r} ({exc})")

        results.append({"input": formula, "composition": comp, "rules": rules, "warnings": warnings})
    return _stamp({"results": results})


def omega_sensitivity(composition: str, perturbation_kj_mol: float = 2.0) -> dict:
    """Report how robust Omega is to the Miedema pair-table choice.

    Omega diverges as the mixing enthalpy approaches zero, so its value
    for near-ideal alloys depends strongly on which published pair
    table is used. This tool returns the per-pair contributions
    ``4 H_ij c_i c_j``, identifies the element whose pairs dominate the
    enthalpy, and recomputes Omega with that element's pair enthalpies
    shifted by +/- ``perturbation_kj_mol`` (default 2 kJ/mol, the
    typical spread between published Miedema compilations). A wide
    Omega range means the verdict, not the number, is what to trust.
    """
    if perturbation_kj_mol < 0:
        raise ValueError("perturbation_kj_mol must be non-negative")
    comp = _parse(composition)
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

    h_mix = hb.mixing_enthalpy(comp)
    t_m = hb.melting_temperature(comp)
    s_mix = hb.smix(comp)

    def omega_at(h: float) -> float | None:
        if h == 0:
            return None
        return t_m * s_mix / (abs(h) * 1000.0)

    h_low, h_high = h_mix - shift, h_mix + shift
    crosses_zero = h_low < 0 < h_high
    endpoint_omegas = [o for o in (omega_at(h_low), omega_at(h_high)) if o is not None]

    return _stamp({
        "input": composition,
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
    })


def oxide_report(
    family: str,
    cations: str,
    b_site_cations: str | None = None,
    oxygen_per_formula_unit: float | None = None,
    spin: str = "high",
) -> dict:
    """Full formability report for a high-entropy oxide composition.

    ``family`` is one of ``rock_salt``, ``perovskite``, ``fluorite``, or
    ``pyrochlore``. ``cations`` is a formula-style string for the cation
    sublattice (the A site for perovskite/pyrochlore, which also require
    ``b_site_cations``). ``oxygen_per_formula_unit`` applies to fluorite
    only (default 2.0). ``spin`` selects high- or low-spin Shannon radii
    for the 3d cations where the tables distinguish them.

    The report contains the charge-balance oxidation states, the Shannon
    radii used, the sublattice entropy and size-disorder descriptors,
    the family's formability screens with their published windows, and
    every warning raised along the way. The screens are weak empirical
    criteria calibrated on small datasets; treat verdicts as hints.
    """
    if family not in _OXIDE_FAMILIES:
        raise ValueError(
            f"unknown family {family!r}; expected one of {sorted(_OXIDE_FAMILIES)}"
        )
    describe, sources = _OXIDE_FAMILIES[family]
    site_a = _parse(cations)

    if family in ("perovskite", "pyrochlore"):
        if not b_site_cations:
            raise ValueError(f"{family} requires b_site_cations (the B sublattice)")
        report = describe(site_a, _parse(b_site_cations), spin=spin)
    elif family == "fluorite":
        if oxygen_per_formula_unit is not None:
            report = describe(site_a, oxygen=oxygen_per_formula_unit, spin=spin)
        else:
            report = describe(site_a, spin=spin)
    else:
        report = describe(site_a, spin=spin)

    report = dict(report)
    report["sources"] = sources
    return _stamp(report)


def element_coverage() -> dict:
    """List which elements each data table covers.

    Use this before batch calls: compositions outside the alloy table
    produce warnings rather than numbers, and oxide cations outside the
    Shannon table raise structured errors.
    """
    from .descriptors.data.elemental import ELEMENTAL_DATA
    from .oxides._data import OXIDE_ELEMENTS

    return _stamp({
        "alloy_descriptors_and_rules": sorted(ELEMENTAL_DATA),
        "alloy_count": len(ELEMENTAL_DATA),
        "miedema_pair_table_note": (
            "The vendored Miedema pair-enthalpy table extends mixing-enthalpy "
            "estimates to 75 elements in total."
        ),
        "oxide_shannon_table": sorted(OXIDE_ELEMENTS),
        "oxide_count": len(OXIDE_ELEMENTS),
    })


def about() -> dict:
    """Version, provenance, license, and citation information."""
    return _stamp({
        "name": "hea-bench",
        "description": (
            "Open, parity-tested calculator of high-entropy alloy and oxide "
            "thermodynamic descriptors and empirical phase-prediction rules. "
            "Every value is a closed-form expression over curated, cited "
            "element-property tables; the Python core and the browser/desktop "
            "JavaScript port are kept identical by automated parity tests."
        ),
        "license": "MIT",
        "repository": "https://github.com/dfieser/hea-bench",
        "paper_doi": "10.3390/ma19143075",
        "cite_as": (
            "Fieser, D.; Dewanjee, U.; Hu, A. HEA-Bench: An AI-Agent-Optimized "
            "Calculator of High-Entropy Alloy and Oxide Descriptors and "
            "Phase-Prediction Rules. Materials 2026, 19, 3075. "
            "doi:10.3390/ma19143075"
        ),
        "archive_doi": "10.5281/zenodo.20346287",
        "homepage": "https://dfieser.github.io/hea-bench/",
        "sources": SOURCES,
        "disclaimer": (
            "Descriptor values and rule verdicts are empirical estimates for "
            "research screening, not engineering qualification."
        ),
    })


_TOOLS = (
    parse_composition,
    alloy_descriptors,
    alloy_rules,
    omega_sensitivity,
    oxide_report,
    element_coverage,
    about,
)


def build_server():
    """Create the FastMCP server with all tools registered.

    Requires the optional ``mcp`` dependency
    (``pip install hea-bench[mcp]``).
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise SystemExit(
            "The MCP surface needs the optional 'mcp' package. "
            "Install it with: pip install hea-bench[mcp]"
        ) from exc

    server = FastMCP(
        "hea-bench",
        instructions=(
            "Verified high-entropy alloy and oxide descriptor calculator. "
            "Deterministic closed-form values with units and citation keys "
            "in every response. Batch the compositions you want to screen "
            "into one alloy_descriptors / alloy_rules call. Check "
            "element_coverage before large sweeps, and use omega_sensitivity "
            "before trusting any Omega magnitude for a near-ideal alloy."
        ),
    )
    for tool in _TOOLS:
        server.tool()(tool)
    return server


def main() -> None:
    """Run the hea-bench MCP server over stdio."""
    build_server().run()


if __name__ == "__main__":
    main()
