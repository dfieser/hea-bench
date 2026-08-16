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

from itertools import combinations

import hea_bench as hb
from . import __version__
from ._json import json_safe
from .descriptors.backend import UNITS
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
        "delta = 0 and Lambda is unbounded (trivially in the "
        "single-solid-solution band)"
    ),
    "omega": (
        "the mixing enthalpy is zero, so Omega diverges (near-ideal "
        "mixing; see omega_sensitivity for how robust that is)"
    ),
}
_DEFAULT_DIVERGENCE = "no competing intermetallic; the verdict is unaffected"

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


def _parse(formula: str) -> dict[str, float]:
    """Parse a composition string (already normalized), with a structured error."""
    try:
        return dict(hb.parse_formula(formula))
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
    def fixed(module, value_func, **predict_kw):
        """Rule whose verdict comes with a descriptor value and static threshold."""
        def evaluate(comp):
            return module.predict(comp, **predict_kw), value_func(comp), {}
        return evaluate

    def senkov_evaluate(comp):
        kp = senkov_kappa.predict(comp, temperature=king_temperature)
        return kp.verdict, kp.k1, {
            "threshold": json_safe(kp.k1_cr),
            "temperature_K": kp.temperature_K,
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
         fixed(guo_vec, hb.vec), None),
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
         "VEC < 4.5 ductile, >= 4.6 brittle (bcc RHEAs)",
         sheikh_evaluate, None),
    )

    results = []
    for formula in compositions:
        comp = _parse(formula)
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
                    f"({reason}); the verdict is unaffected"
                )
        results.append(
            {"input": formula, "composition": comp, "rules": rules, "warnings": warnings}
        )
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


# -- corpus, properties, applicability, design, campaigns -------------------
#
# The tools below expose the post-v2.4 capability layers. Design rules,
# shared with the original seven tools: plain functions with no MCP
# dependency; every uncertainty and domain field at the top level of its
# payload entry, never nested where a client might drop it; missing
# optional extras or missing local data surface as ValueError with the
# exact fix in the message, not a traceback; and the expensive calls
# carry hard caps because agents call tools carelessly.

_CORPUS_SAMPLE_CAP = 50
_DESIGN_MAX_PALETTE = 10
_DESIGN_MAX_CANDIDATES = 20
_DESIGN_MIN_STEP = 0.05
_DESIGN_BUDGET = 50_000
_CAMPAIGN_MAX_BATCH = 10


def _corpus_slice(
    version: str,
    elements: list[str] | None,
    contains: list[str] | None,
    excludes: list[str] | None,
    n_elements_min: int | None,
    n_elements_max: int | None,
    phase: str | None,
    source: str | None,
    labelled: bool | None,
    has_conflict: bool | None,
    descriptor_ready: bool | None,
):
    from .corpus import load_corpus

    try:
        corpus = load_corpus(version=version)
    except FileNotFoundError as exc:
        raise ValueError(str(exc)) from None
    n_range = None
    if n_elements_min is not None or n_elements_max is not None:
        n_range = (n_elements_min or 1, n_elements_max or 99)
    return corpus.query(
        elements=elements,
        contains=contains,
        excludes=excludes,
        n_elements=n_range,
        phase=phase,
        source=source,
        labelled=labelled,
        has_conflict=has_conflict,
        descriptor_ready=descriptor_ready,
    )


def corpus_query(
    elements: list[str] | None = None,
    contains: list[str] | None = None,
    excludes: list[str] | None = None,
    n_elements_min: int | None = None,
    n_elements_max: int | None = None,
    phase: str | None = None,
    source: str | None = None,
    labelled: bool | None = None,
    has_conflict: bool | None = None,
    descriptor_ready: bool | None = None,
    version: str = "0.1.0",
    limit: int = 25,
) -> dict:
    """Filter the consolidated experimental corpus and sample matching rows.

    Filters AND together: ``elements`` is an exact element-set match,
    ``contains``/``excludes`` are memberships, ``phase`` matches the
    consensus label, ``source`` the contributing dataset. Returns the
    match count plus a sample capped at 50 rows, each carrying full
    provenance (per-source canonical and verbatim labels, processing,
    DOI, upstream row ids). Works from a repository checkout or
    ``HEA_BENCH_BENCHMARK_DIR``; the corpus is not shipped, for the
    licensing reasons in the corpus card.
    """
    subset = _corpus_slice(
        version, elements, contains, excludes, n_elements_min, n_elements_max,
        phase, source, labelled, has_conflict, descriptor_ready,
    )
    capped = min(max(0, limit), _CORPUS_SAMPLE_CAP)
    sample = [
        {
            "composition_key": row.composition_key,
            "composition": dict(row.composition),
            "n_elements": row.n_elements,
            "family": row.family,
            "canonical_phase": row.canonical_phase,
            "has_conflict": row.has_conflict,
            "sources": list(row.sources),
            "labels": dict(row.labels),
            "raw_labels": dict(row.raw_labels),
            "processing": row.processing,
            "doi": row.doi,
            "source_row_ids": dict(row.source_row_ids),
            "descriptor_ready": row.descriptor_ready,
        }
        for row in subset.rows[:capped]
    ]
    return _stamp(
        {
            "corpus_version": subset.version,
            "n_matching": len(subset),
            "sample": sample,
            "sample_capped_at": _CORPUS_SAMPLE_CAP,
        }
    )


def corpus_describe(
    elements: list[str] | None = None,
    contains: list[str] | None = None,
    excludes: list[str] | None = None,
    n_elements_min: int | None = None,
    n_elements_max: int | None = None,
    phase: str | None = None,
    source: str | None = None,
    labelled: bool | None = None,
    has_conflict: bool | None = None,
    descriptor_ready: bool | None = None,
    version: str = "0.1.0",
) -> dict:
    """Summary statistics for a filtered corpus slice.

    Counts by phase, element count, source, and family, plus the
    multi-source agreement rate (its complement is the conflict
    quarantine). Same filters as ``corpus_query``.
    """
    subset = _corpus_slice(
        version, elements, contains, excludes, n_elements_min, n_elements_max,
        phase, source, labelled, has_conflict, descriptor_ready,
    )
    return _stamp(subset.describe())


def predict_properties(
    compositions: list[str],
    properties: list[str] | None = None,
    alpha: float = 0.1,
    processing: str | None = None,
) -> dict:
    """Predict properties with uncertainty and domain flags, per composition.

    Tier A (density, melting_temperature, cost_per_kg) is closed-form
    over cited tables; tier B (hardness) is a fitted surrogate and
    always carries a conformal interval, its training-domain flag, and
    its model card reference. Every entry's ``interval``, ``in_domain``,
    ``tier``, and ``warnings`` sit at the top level of that property's
    payload. Missing optional installs come back as a clear error
    naming the pip command.
    """
    from .properties import (
        PropertyUnavailableError,
        available_properties,
        predict_property,
    )

    known = available_properties()
    wanted = properties or sorted(known)
    for name in wanted:
        if name not in known:
            raise ValueError(
                f"unknown property {name!r}; available: {sorted(known)}"
            )

    results = []
    for formula in compositions:
        comp = _parse(formula)
        entry: dict = {"input": formula, "composition": comp, "properties": {}}
        for name in wanted:
            try:
                prediction = predict_property(comp, name, alpha=alpha, processing=processing)
            except PropertyUnavailableError as exc:
                raise ValueError(str(exc)) from None
            entry["properties"][name] = prediction.to_dict()
        results.append(entry)
    return _stamp({"results": results})


def check_applicability(composition: str) -> dict:
    """Report whether a composition sits inside what the corpus covers.

    Returns the orthogonal novelty components (exact family seen and
    how often, nearest-family Jaccard distance, descriptor-cloud
    distance, element coverage) plus the conservative combined
    ``in_domain`` flag. Needs a built corpus; the components describe
    this package's corpus coverage for your query, nothing else.
    """
    from .uncertainty import default_domain

    comp = _parse(composition)
    domain = default_domain()
    if domain is None:
        raise ValueError(
            "no corpus is built in this environment, so applicability cannot "
            "be assessed. Build it (see the corpus card) or set "
            "HEA_BENCH_BENCHMARK_DIR."
        )
    payload = domain.novelty(comp)
    payload["input"] = composition
    payload["corpus_version"] = domain.corpus_version
    return _stamp(payload)


def design_search(
    elements: list[str],
    n_elements_min: int = 3,
    n_elements_max: int = 5,
    step: float = 0.1,
    objectives: list[list[str]] | None = None,
    composition_constraints: list[dict] | None = None,
    rule_constraints: list[dict] | None = None,
    property_constraints: list[dict] | None = None,
    include_out_of_domain: bool = False,
    optimize_bound: str = "lower",
    max_candidates: int = 10,
    alpha: float = 0.1,
) -> dict:
    """Constrained Pareto screening over a palette. The expensive call.

    Hard caps, enforced before any work: at most 10 palette elements,
    step at least 0.05, at most 20 returned candidates, and a fixed
    50,000-point lattice budget; oversized requests are refused with
    the cap named, never silently truncated. Objectives are
    ``[direction, property]`` pairs, e.g.
    ``[["maximize", "hardness"], ["minimize", "cost_per_kg"]]``.
    Fitted objectives rank by the conservative interval end by default.
    Every candidate carries descriptors, all nine rule verdicts,
    property predictions with intervals, novelty, and the domain flag.
    Results are a screening aid, not answers; see
    docs/design-recovery.md.
    """
    from .design import (
        CompositionConstraint,
        DomainConstraint,
        Maximize,
        Minimize,
        PropertyConstraint,
        RuleConstraint,
        search,
    )

    if len(elements) > _DESIGN_MAX_PALETTE:
        raise ValueError(
            f"palette of {len(elements)} exceeds the tool cap of "
            f"{_DESIGN_MAX_PALETTE} elements; screen a narrower palette"
        )
    if max_candidates > _DESIGN_MAX_CANDIDATES:
        raise ValueError(
            f"max_candidates {max_candidates} exceeds the tool cap of "
            f"{_DESIGN_MAX_CANDIDATES}"
        )
    if step < _DESIGN_MIN_STEP:
        raise ValueError(
            f"step {step} is below the tool floor of {_DESIGN_MIN_STEP}; "
            f"finer lattices belong in the Python API with an explicit budget"
        )

    objective_objects = []
    for pair in objectives or []:
        direction, name = pair
        if direction == "maximize":
            objective_objects.append(Maximize(name))
        elif direction == "minimize":
            objective_objects.append(Minimize(name))
        else:
            raise ValueError(f"objective direction must be maximize or minimize, got {direction!r}")

    constraints: list = []
    for entry in composition_constraints or []:
        constraints.append(
            CompositionConstraint(
                entry["element"], min=entry.get("min", 0.0), max=entry.get("max", 1.0)
            )
        )
    for entry in rule_constraints or []:
        satisfied = entry["satisfied"]
        constraints.append(
            RuleConstraint(
                entry["rule"],
                tuple(satisfied) if isinstance(satisfied, list) else satisfied,
            )
        )
    for entry in property_constraints or []:
        constraints.append(
            PropertyConstraint(
                entry["prop"],
                min=entry.get("min"),
                max=entry.get("max"),
                bound=entry.get("bound", "point"),
            )
        )
    if include_out_of_domain:
        constraints.append(DomainConstraint(in_domain=None))

    try:
        result = search(
            elements,
            n_elements=(n_elements_min, n_elements_max),
            constraints=tuple(constraints),
            objectives=tuple(objective_objects),
            n_candidates=max_candidates,
            step=step,
            max_evaluations=_DESIGN_BUDGET,
            optimize_bound=optimize_bound,
            alpha=alpha,
        )
    except (RuntimeError, ValueError) as exc:
        raise ValueError(str(exc)) from None

    return _stamp(result.to_dict())


def campaign_suggest(campaign_path: str, n: int = 5, strategy: str = "ei") -> dict:
    """Next-batch suggestions from a campaign file the user supplies.

    The campaign is plain JSON created by
    ``hea_bench.design.campaign.Campaign.save``; this tool never writes
    it. Batch size is capped at 10. Suggestions carry the ensemble mean,
    the ensemble-spread interval (model disagreement, not a coverage
    guarantee; the module docstring explains), and the domain flag.
    Below the 10-observation floor the loop refuses rather than
    guessing.
    """
    import pathlib

    from .design.campaign import Campaign, ColdStartError

    if n > _CAMPAIGN_MAX_BATCH:
        raise ValueError(
            f"batch of {n} exceeds the tool cap of {_CAMPAIGN_MAX_BATCH}"
        )
    path = pathlib.Path(campaign_path)
    if not path.exists():
        raise ValueError(f"no campaign file at {campaign_path!r}")
    try:
        campaign = Campaign.load(path)
        suggestions = campaign.suggest(n=n, strategy=strategy)
    except (ColdStartError, RuntimeError, ValueError) as exc:
        raise ValueError(str(exc)) from None
    return _stamp(
        {
            "campaign_path": str(path),
            "objective": campaign.objective,
            "direction": campaign.direction,
            "n_observations": len(campaign.observations),
            "n_informative": campaign.n_informative(),
            "strategy": strategy,
            "suggestions": [
                {
                    "composition": dict(s.composition),
                    "mean": json_safe(float(s.mean)),
                    "interval": [
                        json_safe(float(s.interval[0])),
                        json_safe(float(s.interval[1])),
                    ],
                    "in_domain": s.in_domain,
                    "acquisition": json_safe(float(s.acquisition)),
                }
                for s in suggestions
            ],
        }
    )


def about() -> dict:
    """Version, provenance, license, capability availability, citations."""
    import importlib.util
    import os

    from .corpus import corpus_location

    corpus_built = (corpus_location("0.1.0") / "consolidated.csv").exists() or bool(
        os.environ.get("HEA_BENCH_BENCHMARK_DIR")
    )
    sklearn_present = importlib.util.find_spec("sklearn") is not None
    heacalculator_present = importlib.util.find_spec("HEACalculator") is not None
    capabilities = {
        "corpus": corpus_built,
        "properties_tier_a": True,
        "properties_tier_b": sklearn_present,
        "design_search": True,
        "campaigns": sklearn_present,
        "interop": heacalculator_present,
    }
    return _stamp({
        "capabilities": capabilities,
        "capability_notes": {
            "corpus": (
                "corpus_query / corpus_describe / check_applicability need the "
                "locally built corpus (repo checkout or HEA_BENCH_BENCHMARK_DIR); "
                "the data is not shipped, see docs/corpus-card.md"
            ),
            "properties_tier_b": 'pip install "hea-bench[properties]"',
            "campaigns": 'pip install "hea-bench[properties]"',
            "interop": 'pip install "hea-bench[interop]"',
        },
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
    corpus_query,
    corpus_describe,
    predict_properties,
    check_applicability,
    design_search,
    campaign_suggest,
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
            "Verified high-entropy alloy and oxide descriptor calculator plus "
            "a corpus, property, applicability, and design layer. "
            "Deterministic closed-form values carry units and citation keys; "
            "every prediction carries an interval (where a model is fitted) "
            "and an in_domain flag at the top level of its payload. Batch "
            "compositions into one alloy_descriptors / alloy_rules / "
            "predict_properties call. Check element_coverage before large "
            "sweeps, omega_sensitivity before trusting any Omega magnitude "
            "for a near-ideal alloy, and check_applicability before trusting "
            "any prediction for an unusual chemistry. corpus_query needs the "
            "locally built corpus; design_search is the expensive call and "
            "enforces hard caps; about() reports which capabilities are "
            "available in this environment."
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
