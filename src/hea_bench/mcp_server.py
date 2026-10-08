"""Model Context Protocol (MCP) surface for hea-bench.

Exposes every feature of the package, the same set the web and desktop
app has, to LLM agents as deterministic, batch-oriented tools. Design
follows the published MCP-for-science experience: explicit typed
schemas, bounded execution, structured errors, and provenance in-band:
every numeric result carries its unit, the citation key of its
parametrization, and the library version, so an agent's reasoning trace
contains auditable receipts rather than bare floats.

The tool bodies below are plain functions with no MCP dependency, so
they are unit-tested in CI like the rest of the library. The ``mcp``
package (``pip install hea-bench[mcp]``) is imported lazily only by
:func:`build_server` / :func:`main`.

Run the server over stdio::

    hea-bench-mcp

or register it with an MCP client (Claude Desktop, Cursor, ...)::

    {"command": "hea-bench-mcp"}
"""

# Do NOT add `from __future__ import annotations` here. It stringizes
# every tool signature, and the MCP SDK inspects those signatures with
# `issubclass(param.annotation, Context)`, which raises TypeError on a
# string and kills the whole server before it serves one tool. The
# module targets Python >=3.10, so `list[str]` and `float | None`
# already evaluate natively without it.

import pathlib

import hea_bench as hb
from . import __version__
from ._json import json_safe, strict_json
from .ceramics import describe_diboride, describe_rock_salt_carbide, describe_rock_salt_nitride
from .descriptors.backend import UNITS
from .descriptors.miedema_decomposition import miedema_decomposition
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

_CERAMIC_STRUCTURES = {
    "rock_salt_carbide": describe_rock_salt_carbide,
    "rock_salt_nitride": describe_rock_salt_nitride,
    "diboride": describe_diboride,
}


def _stamp(payload: dict) -> dict:
    """Attach the library version to a tool response, as strict JSON."""
    payload["hea_bench_version"] = __version__
    return strict_json(payload)


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


def alloy_descriptors(
    compositions: list[str],
    king_temperature: float | None = None,
    custom_elements: dict[str, dict] | None = None,
    pair_enthalpies: dict[str, float] | None = None,
) -> dict:
    """Compute every alloy descriptor for a batch of compositions.

    Each value is returned with its unit and the citation key of its
    parametrization (see ``about()`` for the key -> reference map).
    Compositions containing elements outside the curated 55-element
    table return ``null`` for the affected descriptors plus a warning,
    never a silent wrong number. ``miedema_enthalpies`` carries the
    compound, solid-solution and amorphous formation enthalpies of the
    Miedema model (37 elements).

    ``king_temperature`` (kelvin) optionally overrides the
    rule-of-mixtures melting temperature used by the King Phi proxy
    and the Senkov-Miracle kappa criterion. ``custom_elements`` and
    ``pair_enthalpies`` add elements and pair values for this call only,
    like the app's custom-element and pair editors.
    """
    results = []
    with hb.custom_data(elements=custom_elements, pair_enthalpies=pair_enthalpies):
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
    return _stamp({"results": results})


def alloy_rules(
    compositions: list[str],
    king_temperature: float | None = None,
    custom_elements: dict[str, dict] | None = None,
    pair_enthalpies: dict[str, float] | None = None,
) -> dict:
    """Apply the nine canonical empirical phase-prediction rules to a batch.

    Each verdict is returned with the descriptor value it was judged on
    and the published threshold, so the margin is auditable. These rules
    are weak empirical screens calibrated on small historical datasets;
    treat verdicts as hints, never ground truth. A rule outside its
    domain says ``not_applicable`` (Tsai without Cr or V, Sheikh with any
    element beyond Ti, Zr, Hf, V, Nb, Ta, Cr, Mo, W). ``guo_vec`` and
    ``senkov_kappa`` carry a ``note`` (null when there is nothing to
    say) when VEC sits within 0.2 of a Guo cutoff, or when an element of
    the pair behind Senkov's ΔH_IM (``im_pair``) is under 10 at.%.
    ``custom_elements`` and ``pair_enthalpies`` work as in
    ``alloy_descriptors``.
    """
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


def omega_sensitivity(
    composition: str,
    perturbation_kj_mol: float = 2.0,
    custom_elements: dict[str, dict] | None = None,
    pair_enthalpies: dict[str, float] | None = None,
) -> dict:
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
    with hb.custom_data(elements=custom_elements, pair_enthalpies=pair_enthalpies):
        report = hb.omega_sensitivity(_parse(composition), perturbation_kj_mol)
    return _stamp({"input": composition, **report})


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


def ceramic_report(structure: str, metals: str) -> dict:
    """Composition-only descriptors for a high-entropy carbide, nitride or diboride.

    ``structure`` is ``rock_salt_carbide``, ``rock_salt_nitride`` or
    ``diboride``; ``metals`` is the metal-sublattice formula. The report
    gives the configurational entropy in every normalization papers use,
    and for the rock-salt structures the VEC per formula unit against
    the literature's reference points. It deliberately gives no
    formability verdict, because no single published window exists.
    """
    if structure not in _CERAMIC_STRUCTURES:
        raise ValueError(
            f"unknown structure {structure!r}; expected one of {sorted(_CERAMIC_STRUCTURES)}"
        )
    return _stamp(dict(_CERAMIC_STRUCTURES[structure](_parse(metals))))


def element_data(elements: list[str] | None = None) -> dict:
    """The tabulated values behind every number, per element, with sources.

    Radius, melting point, valence, electronegativity, molar volume and
    moduli, each with its unit; the radius source and where good sources
    disagree; which features each element supports; the cited
    references; and the SHA-256 of every data file. All 55 elements
    when ``elements`` is omitted.
    """
    from .descriptors.elements import element_data as tabulated

    return _stamp(tabulated(elements))


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


def _needs_corpus(exc: FileNotFoundError) -> ValueError:
    return ValueError(f"{exc}\nFrom an MCP client, call the corpus_build tool once instead.")


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
        raise _needs_corpus(exc) from None
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
    version: str = "0.2.0",
    limit: int = 25,
) -> dict:
    """Filter the consolidated experimental corpus and sample matching rows.

    Filters AND together: ``elements`` is an exact element-set match,
    ``contains``/``excludes`` are memberships, ``phase`` matches the
    consensus label, ``source`` the contributing dataset. Returns the
    match count plus a sample capped at 50 rows, each carrying full
    provenance (per-source canonical and verbatim labels, processing,
    DOI, upstream row ids). ``corpus_export`` writes the whole slice to
    a CSV file. The corpus is built on this machine rather than shipped,
    for the licensing reasons in the corpus card; ``corpus_build`` builds
    it once.
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
    version: str = "0.2.0",
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


def corpus_export(
    path: str,
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
    version: str = "0.2.0",
) -> dict:
    """Write a filtered corpus slice to a new CSV file, every column kept.

    Same filters as ``corpus_query``, in the consolidated-CSV schema the
    app's Download button produces. Refuses to overwrite an existing
    file.
    """
    target = _new_file(path)
    subset = _corpus_slice(
        version, elements, contains, excludes, n_elements_min, n_elements_max,
        phase, source, labelled, has_conflict, descriptor_ready,
    )
    n_rows = subset.to_csv(target)
    return _stamp({"path": str(target.resolve()), "n_rows": n_rows, "corpus_version": subset.version})


def corpus_build(versions: list[str] | None = None) -> dict:
    """Build the corpus on this machine, once. Every corpus tool needs it.

    Every source dataset ships with the package, so the build needs no
    network. Builds every version by default. Rebuilding reproduces the
    same corpus, so calling it again is harmless.
    """
    from .corpus import build_corpus
    from .webapp import _clear_caches

    try:
        built = build_corpus(*(versions or ()))
    except OSError as exc:
        raise ValueError(str(exc)) from None
    _clear_caches()
    return _stamp(
        {
            "built": {
                version: {"location": manifest["location"], "totals": manifest["totals"]}
                for version, manifest in built.items()
            }
        }
    )


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


def measured_properties(
    prop: str = "hardness", contains: list[str] | None = None, limit: int = 25
) -> dict:
    """Measured hardness or density from Borg et al. (2020), with DOIs.

    The measurements the hardness model trains on, or the densities the
    rule-of-mixtures estimate is checked against, optionally only alloys
    containing every element in ``contains``. Returns the exact match
    count and a sample capped at 50 rows.
    """
    from .webapp import measured_properties as records

    payload = records(prop, contains)
    payload["rows"] = payload["rows"][: min(max(0, limit), _CORPUS_SAMPLE_CAP)]
    payload["sample_capped_at"] = _CORPUS_SAMPLE_CAP
    return _stamp(payload)


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
            "the corpus is not built on this machine, so applicability cannot be "
            "assessed. Call the corpus_build tool once, then try again."
        )
    payload = domain.novelty(comp)
    payload["input"] = composition
    payload["corpus_version"] = domain.corpus_version
    return _stamp(payload)


def predict_phase_set(
    compositions: list[str],
    task: str = "single_vs_multi",
    alpha: float = 0.1,
    version: str = "0.1.0",
) -> dict:
    """Phase prediction with a conformal prediction set, per composition.

    A random forest on the 14 descriptors, trained on the corpus, with
    split-conformal calibration: the set contains the true label about
    ``1 - alpha`` of the time on alloys like the calibration set. A set
    with more than one label means the model cannot decide. Each entry
    carries class probabilities, the corpus ``in_domain`` flag and
    novelty measures, and plain-language warnings. The first call per
    task fits the model (several seconds).
    """
    from .benchmark.corpus import TASKS
    from .uncertainty.phase import predict_phase_set as predict

    if task not in TASKS:
        raise ValueError(f"unknown task {task!r}; expected one of {sorted(TASKS)}")
    results = []
    for formula in compositions:
        comp = _parse(formula)
        try:
            entry = predict(comp, task=task, alpha=alpha, version=version)
        except FileNotFoundError as exc:
            raise _needs_corpus(exc) from None
        except ImportError:
            raise ValueError('phase prediction needs scikit-learn: pip install "hea-bench[mcp]"') from None
        except ValueError as exc:
            entry = {"error": str(exc)}
        results.append({"input": formula, "composition": comp, **entry})
    return _stamp({"task": task, "alpha": alpha, "corpus_version": version, "results": results})


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
    property predictions with intervals, novelty, the domain flag, and
    ``phase``: its four-class phase prediction set (null without a built
    corpus). An element cap such as ``{"element": "Al", "max": 0.2}``
    keeps hardness searches from drifting to aluminides.
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


def campaign_suggest(
    campaign_path: str | None = None,
    n: int = 5,
    strategy: str = "ei",
    campaign: dict | None = None,
) -> dict:
    """Next-batch suggestions for a campaign, from a file or inline.

    The campaign is plain JSON, as the app's Campaign panel and
    ``hea_bench.design.campaign.Campaign.save`` write it: give its path
    as ``campaign_path`` or its contents as ``campaign``. This tool
    never writes the file; inline calls get the canonical campaign back
    to save. Batch size is capped at 10. Suggestions carry the ensemble
    mean, a 90 percent conformal interval set from the forest's
    out-of-bag errors (coverage measured in docs/campaign-replay.md),
    and the domain flag. Below the 10-observation floor the loop refuses rather than
    guessing.
    """
    from .design.campaign import Campaign, ColdStartError

    if (campaign_path is None) == (campaign is None):
        raise ValueError(
            "give exactly one of campaign_path (a campaign JSON file) or campaign "
            "(the file's contents)"
        )
    if campaign is not None:
        from .webapp import campaign_suggest as suggest_inline

        return _stamp(suggest_inline(campaign, n=n, strategy=strategy))
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


# -- benchmark ----------------------------------------------------------------
#
# Thin wrappers over the app's own bridge methods (hea_bench.webapp), so
# the Benchmark tab and these tools return the same numbers.


def _bench(method, *args, **kwargs) -> dict:
    try:
        return method(*args, **kwargs)
    except FileNotFoundError as exc:
        raise _needs_corpus(exc) from None
    except ImportError:
        raise ValueError(
            'the fitted baselines need scikit-learn: pip install "hea-bench[mcp]"'
        ) from None


def _new_file(path: str) -> pathlib.Path:
    target = pathlib.Path(path).expanduser()
    if target.exists():
        raise ValueError(f"{str(target)!r} already exists; choose a new file name")
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def benchmark_summary(task: str = "single_vs_multi", version: str = "0.1.0") -> dict:
    """The paired benchmark at a glance: splits, digests and the published table.

    Two frozen 5-fold schemes over the same rows: random folds measure
    interpolation within known alloy families, family-grouped folds
    measure extrapolation to unseen element systems. Returns the class
    balance and family overlap of each scheme, whether both match their
    frozen SHA-256 digests, the baselines you can score live with
    ``benchmark_run``, and the published results table for v0.1.0.
    """
    from .webapp import benchmark_summary as summary

    return _stamp(_bench(summary, task, version))


def benchmark_run(model: str, task: str = "single_vs_multi", version: str = "0.1.0") -> dict:
    """Score one published baseline live under both split schemes.

    Fits and scores ``model`` on every fold of the random and the
    family-grouped scheme, on the same rows as the published table, and
    reports per-scheme metrics plus the ``gap`` (random minus grouped),
    which measures how much harder extrapolation is than interpolation.
    The fitted baselines take tens of seconds.
    """
    from .webapp import benchmark_run as run

    return _stamp(_bench(run, model, task, version))


def benchmark_folds(path: str, task: str = "single_vs_multi", version: str = "0.1.0") -> dict:
    """Write every benchmark row with its fold under both schemes to a new CSV.

    The file for training your own model offline: ``composition_key``,
    ``family``, ``label``, ``grouped_fold``, ``random_fold``,
    ``n_elements`` and ``descriptors_finite``. Score the predictions
    with ``benchmark_score``. Refuses to overwrite an existing file.
    """
    from .webapp import benchmark_folds_csv

    target = _new_file(path)
    folds = _bench(benchmark_folds_csv, task, version)
    target.write_text(folds["text"], encoding="utf-8", newline="")
    return _stamp({"path": str(target.resolve()), "n_rows": folds["n_rows"], "task": task})


def benchmark_score(
    predictions_path: str,
    task: str = "single_vs_multi",
    version: str = "0.1.0",
    model_name: str = "",
) -> dict:
    """Score your own model's predictions under both split schemes.

    ``predictions_path`` is a CSV with the columns ``composition_key``,
    ``grouped`` and ``random``: for each row, the label your model
    predicted when that row was in the test fold of each scheme (the
    folds come from ``benchmark_folds``). Returns the same report as
    ``benchmark_run``, including the ``gap``.
    """
    from .webapp import benchmark_score as score

    source = pathlib.Path(predictions_path).expanduser()
    if not source.exists():
        raise ValueError(f"no predictions file at {predictions_path!r}")
    text = source.read_text(encoding="utf-8-sig")
    return _stamp(_bench(score, text, task, version, model_name))


def coverage_study(task: str = "single_vs_multi", version: str = "0.1.0") -> dict:
    """Check the phase prediction sets' coverage on held-out alloy families.

    Reruns the conformal coverage study: under the family-grouped
    scheme, how often the prediction set contains the true label, at
    several miscoverage levels, for all test alloys and for the in- and
    out-of-domain groups separately. Takes a minute or more.
    """
    from .webapp import coverage

    return _stamp(_bench(coverage, task, version))


def about() -> dict:
    """Version, provenance, license, capability availability, citations."""
    import importlib.util

    from .benchmark.consolidate import SOURCES_BY_VERSION
    from .corpus import corpus_location

    built = {
        version: (corpus_location(version) / "consolidated.csv").exists()
        for version in SOURCES_BY_VERSION
    }
    sklearn_present = importlib.util.find_spec("sklearn") is not None
    heacalculator_present = importlib.util.find_spec("HEACalculator") is not None
    capabilities = {
        "corpus": any(built.values()),
        "properties_tier_a": True,
        "properties_tier_b": sklearn_present,
        "phase_prediction": sklearn_present,
        "benchmark_baselines": sklearn_present,
        "design_search": True,
        "campaigns": sklearn_present,
        "interop": heacalculator_present,
    }
    return _stamp({
        "capabilities": capabilities,
        "corpus_versions_built": built,
        "capability_notes": {
            "corpus": (
                "the dataset tools, check_applicability, predict_phase_set and the "
                "benchmark tools need the corpus, which is built on this machine "
                "from the source datasets that ship with the package. Call "
                "corpus_build once (no download)."
            ),
            "properties_tier_b": 'pip install "hea-bench[mcp]" (includes scikit-learn)',
            "phase_prediction": 'pip install "hea-bench[mcp]" (includes scikit-learn)',
            "benchmark_baselines": 'pip install "hea-bench[mcp]" (includes scikit-learn)',
            "campaigns": 'pip install "hea-bench[mcp]" (includes scikit-learn)',
            "interop": 'pip install "hea-bench[interop]"',
        },
        "name": "hea-bench",
        "description": (
            "Open, parity-tested calculator of high-entropy alloy, oxide and "
            "ceramic descriptors and empirical phase-prediction rules, with an "
            "experimental phase dataset, a paired interpolative and extrapolative "
            "benchmark, property and phase predictions with uncertainty, and an "
            "alloy search. Every descriptor is a closed-form expression over "
            "curated, cited element-property tables. The Python package, this MCP "
            "server, the web app and the desktop app have the same features."
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
    ceramic_report,
    element_data,
    element_coverage,
    corpus_build,
    corpus_query,
    corpus_describe,
    corpus_export,
    measured_properties,
    predict_properties,
    predict_phase_set,
    check_applicability,
    design_search,
    campaign_suggest,
    benchmark_summary,
    benchmark_run,
    benchmark_folds,
    benchmark_score,
    coverage_study,
    about,
)

#: The tools that are not pure local reads, and the hints that differ.
#: Every other tool reads curated tables or the built corpus and returns
#: numbers: nothing writes and nothing reaches the network.
_TOOL_HINTS = {
    "corpus_build": {"readOnlyHint": False, "openWorldHint": True},
    "corpus_export": {"readOnlyHint": False},
    "benchmark_folds": {"readOnlyHint": False},
}


# Prose for every tool parameter, keyed by tool then parameter name.
# The MCP SDK derives each input schema from the function signature, which
# carries types and defaults but no meaning, so without this table an
# agent sees `phase: string` with no hint that the corpus holds only
# four labels. The descriptions live here rather than in
# ``Annotated[..., Field(description=...)]`` metadata because that
# would pull pydantic into module scope and make importing
# hea_bench.mcp_server fail without the optional ``mcp`` extra, which
# is the same reason build_server imports lazily. Say what the schema
# cannot: units, allowed values, caps, and whether a default is a real
# choice or a placeholder.
_CORPUS_FILTER_DOCS = {
    "elements": (
        "Exact element-set match: keep only rows whose element set is exactly "
        "this list, e.g. ['Co', 'Cr', 'Fe', 'Mn', 'Ni']."
    ),
    "contains": "Keep only rows containing every one of these elements, in any larger alloy.",
    "excludes": "Keep only rows containing none of these elements.",
    "n_elements_min": "Fewest distinct elements a row may have.",
    "n_elements_max": "Most distinct elements a row may have.",
    "phase": "Consensus phase label to match, one of 'FCC', 'BCC', 'HCP', or 'multi-phase'.",
    "source": (
        "Contributing dataset to match, one of 'borg2020', 'pei2020', 'peivaste', or "
        "(version '0.2.0' only) 'chizhevskiy2026'."
    ),
    "labelled": (
        "True keeps only rows carrying a consensus phase label, false only "
        "unlabelled rows; omit for both."
    ),
    "has_conflict": (
        "True keeps only rows quarantined because their sources disagree on the "
        "phase, false excludes them; omit for both."
    ),
    "descriptor_ready": (
        "True keeps only rows whose every element is present in the descriptor "
        "tables, so descriptors can actually be computed for them."
    ),
    "version": (
        "Corpus version. '0.2.0' (default) is the largest: it adds an LLM-extracted "
        "database whose labels agree with the reference on roughly 70% of "
        "overlapping rows, every disagreement quarantined as a conflict. '0.1.0' is "
        "the hand-curated reference corpus every published hea-bench number is "
        "measured on. This counter is independent of the package version."
    ),
}

_BATCH_DOC = (
    "Formulas to evaluate in a single call, e.g. ['CoCrFeMnNi', 'Al0.3CoCrFeNi']. "
    "Element counts need not sum to 1; they are normalized to mole fractions. "
    "Batch here rather than issuing one call per alloy."
)
_KING_TEMPERATURE_DOC = (
    "Temperature in kelvin at which King's Phi is evaluated. Defaults to the "
    "melting-point estimate derived from the composition; set it only to "
    "reproduce a published value quoted at a stated temperature."
)
_CUSTOM_ELEMENTS_DOC = (
    "Elements outside the 55-element table, for this call only, keyed by a label "
    "shaped like an element symbol that is not a real one (a capital letter, "
    "optionally one lowercase letter), so formulas can use it, e.g. "
    "{'Xx': {'radius_pm': 140, 'melting_K': 1800, 'valence': 6, "
    "'electronegativity': 1.7}} with the formula 'CoCrFeNiXx'. radius_pm, melting_K "
    "and valence are required; electronegativity is optional."
)
_PAIR_ENTHALPIES_DOC = (
    "Mixing enthalpies in kJ/mol that replace or add Miedema pair values for this "
    "call only, keyed 'A-B', e.g. {'Co-Xx': -5.0, 'Cr-Fe': -2.0}. A custom element "
    "needs a value for every pair it forms before the mixing enthalpy and Omega can "
    "be computed."
)
_TASK_DOC = (
    "Benchmark task: 'single_vs_multi' (single-phase solid solution or not, the "
    "default) or 'phase4' (multi-phase, BCC, FCC or HCP)."
)
_BENCH_VERSION_DOC = (
    "Corpus version the benchmark runs on. '0.1.0' (default) is the reference "
    "every published number is measured on; '0.2.0' is larger but its added labels "
    "are noisier."
)
_ALPHA_DOC = (
    "Miscoverage rate for the conformal interval on fitted (tier B) properties: "
    "0.1, the default, gives a 90% interval. Tier A properties are closed-form and "
    "ignore it."
)

_PARAM_DOCS: dict[str, dict[str, str]] = {
    "parse_composition": {
        "formula": (
            "Chemical formula in element-count notation, e.g. 'CoCrFeMnNi' for an "
            "equiatomic alloy or 'Al0.3CoCrFeNi' for a scaled one. Counts need not "
            "sum to 1; they are normalized to mole fractions."
        ),
    },
    "alloy_descriptors": {
        "compositions": _BATCH_DOC,
        "king_temperature": _KING_TEMPERATURE_DOC,
        "custom_elements": _CUSTOM_ELEMENTS_DOC,
        "pair_enthalpies": _PAIR_ENTHALPIES_DOC,
    },
    "alloy_rules": {
        "compositions": _BATCH_DOC,
        "king_temperature": _KING_TEMPERATURE_DOC,
        "custom_elements": _CUSTOM_ELEMENTS_DOC,
        "pair_enthalpies": _PAIR_ENTHALPIES_DOC,
    },
    "omega_sensitivity": {
        "composition": (
            "Single formula to stress-test. Worth running whenever a mixing "
            "enthalpy near zero makes Omega blow up, which is exactly when its "
            "magnitude should not be trusted."
        ),
        "perturbation_kj_mol": (
            "Symmetric shift applied to the mixing enthalpy, in kJ/mol. Default "
            "2.0, the typical spread between Miedema-model implementations."
        ),
        "custom_elements": _CUSTOM_ELEMENTS_DOC,
        "pair_enthalpies": _PAIR_ENTHALPIES_DOC,
    },
    "oxide_report": {
        "family": (
            "Oxide structure family, one of 'rock_salt', 'perovskite', 'fluorite', "
            "or 'pyrochlore'. It selects which formability screens apply."
        ),
        "cations": (
            "Formula-style string for the cation sublattice, e.g. 'MgCoNiCuZn'. For "
            "'perovskite' and 'pyrochlore' this is the A site and b_site_cations is "
            "also required."
        ),
        "b_site_cations": (
            "Formula-style string for the B-site cations. Required for 'perovskite' "
            "and 'pyrochlore', ignored for the single-sublattice families."
        ),
        "oxygen_per_formula_unit": (
            "Oxygen atoms per formula unit, used to close the charge balance. "
            "Applies to 'fluorite' only, where it defaults to 2.0."
        ),
        "spin": (
            "Spin state used to pick Shannon radii for the 3d cations whose tables "
            "distinguish them: 'high' (default) or 'low'."
        ),
    },
    "ceramic_report": {
        "structure": (
            "Ceramic structure: 'rock_salt_carbide', 'rock_salt_nitride', or "
            "'diboride'."
        ),
        "metals": (
            "Formula of the metal sublattice only, e.g. 'HfNbTaTiZr'. The anion "
            "sublattice follows from the structure."
        ),
    },
    "element_data": {
        "elements": (
            "Element symbols to report, e.g. ['Co', 'Cr']. Omit for all 55. Unknown "
            "symbols are refused with their names."
        ),
    },
    "element_coverage": {},
    "corpus_build": {
        "versions": (
            "Corpus versions to build, e.g. ['0.2.0']. Omit to build every version, "
            "which is what the other tools expect."
        ),
    },
    "corpus_query": {
        **_CORPUS_FILTER_DOCS,
        "limit": (
            "Rows to return in the sample, capped at 50. The reported match count "
            "is always exact and unaffected by this cap."
        ),
    },
    "corpus_describe": dict(_CORPUS_FILTER_DOCS),
    "corpus_export": {
        **_CORPUS_FILTER_DOCS,
        "path": (
            "Path of the new CSV file to write. An existing file is never "
            "overwritten."
        ),
    },
    "measured_properties": {
        "prop": "Which measurement: 'hardness' (Vickers, HV, the default) or 'density' (g/cm^3).",
        "contains": "Keep only alloys containing every one of these elements, e.g. ['Al', 'Ti'].",
        "limit": (
            "Rows to return in the sample, capped at 50. The reported match count "
            "is always exact."
        ),
    },
    "predict_properties": {
        "compositions": _BATCH_DOC,
        "properties": (
            "Which properties to predict, any of 'density', 'melting_temperature', "
            "'cost_per_kg' (closed-form, tier A) and 'hardness' (fitted surrogate, "
            "tier B). Defaults to all four."
        ),
        "alpha": _ALPHA_DOC,
        "processing": (
            "Processing route to condition fitted models on, e.g. 'as-cast' or "
            "'annealed'. Omit when the route is unknown."
        ),
    },
    "predict_phase_set": {
        "compositions": _BATCH_DOC,
        "task": _TASK_DOC,
        "alpha": (
            "Miscoverage rate: 0.1, the default, asks for a set that contains the "
            "true label about 90% of the time on alloys like the calibration set."
        ),
        "version": (
            "Corpus version the model trains on. '0.1.0' (default) is the reference "
            "corpus every published number is measured on."
        ),
    },
    "check_applicability": {
        "composition": (
            "Single formula to test against the corpus's coverage. Run it before "
            "trusting any prediction for an unusual chemistry."
        ),
    },
    "design_search": {
        "elements": (
            "Element palette to screen over, at most 10 elements. An oversized "
            "palette is refused outright rather than truncated."
        ),
        "n_elements_min": "Fewest distinct elements a candidate may contain. Default 3.",
        "n_elements_max": "Most distinct elements a candidate may contain. Default 5.",
        "step": (
            "Mole-fraction spacing of the search lattice. Floor 0.05; finer "
            "lattices belong in the Python API with an explicit evaluation budget."
        ),
        "objectives": (
            "[direction, property] pairs, e.g. "
            "[['maximize', 'hardness'], ['minimize', 'cost_per_kg']]. Direction is "
            "'maximize' or 'minimize'. Omit to rank by constraint satisfaction alone."
        ),
        "composition_constraints": (
            "Per-element mole-fraction bounds, each "
            "{'element': 'Al', 'min': 0.0, 'max': 0.2}. Bounds default to 0.0 and 1.0."
        ),
        "rule_constraints": (
            "Required phase-rule verdicts, each "
            "{'rule': 'yang_omega', 'satisfied': true}; 'satisfied' also accepts a "
            "list of acceptable verdicts. Rule names: guo_vec, king_phi, "
            "senkov_kappa, sheikh_ductility, tsai_sigma, yang_omega, ye_phi, "
            "yeh_entropy, zhang_delta."
        ),
        "property_constraints": (
            "Bounds on predicted properties, each "
            "{'prop': 'density', 'max': 8.0, 'bound': 'point'}. 'bound' selects what "
            "is compared for fitted properties: 'point' (default), or 'lower'/"
            "'upper' to compare that end of the interval when the constraint guards "
            "against under- or overshooting."
        ),
        "include_out_of_domain": (
            "True keeps candidates that fall outside the fitted models' training "
            "domain, flagged rather than dropped. Default false."
        ),
        "optimize_bound": (
            "Which end of the interval ranks fitted objectives: 'lower' (default, "
            "the conservative choice) or 'point'."
        ),
        "max_candidates": "Candidates to return, capped at 20. Default 10.",
        "alpha": _ALPHA_DOC,
    },
    "campaign_suggest": {
        "campaign_path": (
            "Filesystem path to a campaign JSON file, as the app's Campaign panel "
            "or hea_bench.design.campaign.Campaign.save writes it. Read only; this "
            "tool never writes the file back. Give this or campaign, not both."
        ),
        "campaign": (
            "The campaign file's contents as an object, instead of campaign_path, in "
            "the schema the app saves: {'schema': 1, 'objective': 'hardness', "
            "'direction': 'maximize', 'palette': ['Co', 'Cr', 'Fe', 'Ni', 'Al'], "
            "'constraints': [], 'seed': 0, 'step': 0.1, 'n_elements': [3, 5], "
            "'warm_start': true, 'observations': [{'composition': 'CoCrFeNi', "
            "'value': 160}]}. Observation compositions may be formulas. The response "
            "carries the canonical campaign back."
        ),
        "n": "Suggestions to return in this batch, capped at 10. Default 5.",
        "strategy": (
            "Acquisition strategy: 'ei' (expected improvement, the default) or "
            "'ucb' (upper confidence bound, which explores more)."
        ),
    },
    "benchmark_summary": {"task": _TASK_DOC, "version": _BENCH_VERSION_DOC},
    "benchmark_run": {
        "model": (
            "Published baseline to score. For 'single_vs_multi': 'majority-class', "
            "'rule:zhang_delta', 'rule:yang_omega', 'random-forest', "
            "'gradient-boosting'. For 'phase4': 'majority-class', 'rule:guo_vec', "
            "'random-forest', 'gradient-boosting'."
        ),
        "task": _TASK_DOC,
        "version": _BENCH_VERSION_DOC,
    },
    "benchmark_folds": {
        "path": "Path of the new CSV file to write. An existing file is never overwritten.",
        "task": _TASK_DOC,
        "version": _BENCH_VERSION_DOC,
    },
    "benchmark_score": {
        "predictions_path": (
            "Path to your predictions CSV with the columns composition_key, grouped "
            "and random."
        ),
        "task": _TASK_DOC,
        "version": _BENCH_VERSION_DOC,
        "model_name": "Name to print on the report. Optional.",
    },
    "coverage_study": {"task": _TASK_DOC, "version": _BENCH_VERSION_DOC},
    "about": {},
}


def build_server():
    """Create the MCP server with all tools registered.

    Requires the optional ``mcp`` dependency
    (``pip install hea-bench[mcp]``).
    """
    try:
        from mcp.server.mcpserver import MCPServer
        from mcp.types import ToolAnnotations
    except ImportError as exc:
        try:
            from importlib.metadata import version

            installed = version("mcp")
        except Exception:
            installed = None
        if installed is None:
            raise SystemExit(
                "The MCP surface needs the optional 'mcp' package. "
                "Install it with: pip install 'hea-bench[mcp]'"
            ) from exc
        raise SystemExit(
            f"The installed MCP SDK (mcp {installed}) is too old for "
            "hea-bench-mcp, which is built on mcp 2 (mcp.server.mcpserver). "
            "Upgrade it with: pip install 'hea-bench[mcp]'"
        ) from exc

    server = MCPServer(
        "hea-bench",
        version=__version__,
        instructions=(
            "High-entropy alloy, oxide and ceramic calculator with an "
            "experimental phase dataset, a paired benchmark, predictions with "
            "uncertainty and an alloy search: the same features as the hea-bench "
            "web and desktop app. Deterministic closed-form values carry units "
            "and citation keys; every prediction carries an interval (where a "
            "model is fitted) and an in_domain flag at the top level of its "
            "payload. Batch compositions into one alloy_descriptors / "
            "alloy_rules / predict_properties / predict_phase_set call. Check "
            "element_coverage before large sweeps, omega_sensitivity before "
            "trusting any Omega magnitude for a near-ideal alloy, and "
            "check_applicability before trusting any prediction for an unusual "
            "chemistry. The dataset, phase-set, applicability and benchmark "
            "tools need the corpus: call corpus_build once. design_search is "
            "the expensive call and enforces hard caps; about() reports which "
            "capabilities are available in this environment."
        ),
    )
    # Every tool but those in _TOOL_HINTS is a pure local computation, so
    # an agent can tell from the manifest alone which calls are safe.
    # Titles are derived from the function name so a tool cannot be added
    # without one.
    for tool in _TOOLS:
        hints = {
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
            **_TOOL_HINTS.get(tool.__name__, {}),
        }
        server.tool(
            annotations=ToolAnnotations(
                title=tool.__name__.replace("_", " ").capitalize(), **hints
            )
        )(tool)
    _document_parameters(server)
    return server


def _document_parameters(server) -> None:
    """Copy _PARAM_DOCS onto the registered tools' input schemas.

    Raises rather than warns when a parameter has no entry: an
    undocumented parameter should break the test suite the moment it is
    added, not ship as a blank field in the manifest.
    """
    for tool in server._tool_manager.list_tools():
        docs = _PARAM_DOCS.get(tool.name)
        if docs is None:
            raise RuntimeError(
                f"tool {tool.name!r} has no _PARAM_DOCS entry; add one, even if "
                f"the tool takes no parameters"
            )
        properties = tool.parameters.get("properties", {})
        undocumented = sorted(set(properties) - set(docs))
        if undocumented:
            raise RuntimeError(
                f"tool {tool.name!r} has undocumented parameters: "
                f"{', '.join(undocumented)}; add them to _PARAM_DOCS"
            )
        for name, schema in properties.items():
            schema["description"] = docs[name]


def main() -> None:
    """Run the hea-bench MCP server over stdio."""
    build_server().run()


if __name__ == "__main__":
    main()
