"""Model Context Protocol (MCP) surface for hea-bench.

Exposes every feature of the package to LLM agents as deterministic,
batch-oriented tools, the same set the web and desktop app has. The
design follows published experience with MCP servers for science:
explicit typed schemas, bounded execution, structured errors, and
provenance in-band. Every numeric result carries its unit, the citation
key of its parametrization and the library version, so an agent's
reasoning trace holds auditable receipts rather than bare floats.

Each tool below is a thin wrapper over one function in
:mod:`hea_bench.service`, which the app's engine bridge
(:mod:`hea_bench.webapp`) calls too, so the two return the same numbers.
The wrappers keep the signatures and docstrings, because those are the
tool schemas and descriptions. The tool bodies are plain functions with
no MCP dependency, so CI unit-tests them like the rest of the library.
Only :func:`build_server`
and :func:`main` import the ``mcp`` package
(``pip install hea-bench[mcp]``), and they import it lazily.

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

from . import __version__, service
from .service._payload import SOURCES, needs_corpus, stamp


def parse_composition(formula: str) -> dict:
    """Parse a chemical formula into normalized mole fractions.

    Accepts forms like ``CoCrFeMnNi`` (equimolar), ``Al0.3CoCrFeNi``, or
    ``Co20Cu20Fe5Mn35Ni20`` (percent-style amounts). Amounts are
    normalized to fractions that sum to 1.
    """
    return stamp(service.alloys.parse_composition(formula))


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
    return stamp(service.alloys.alloy_descriptors(
        compositions, king_temperature, custom_elements, pair_enthalpies
    ))


def alloy_rules(
    compositions: list[str],
    king_temperature: float | None = None,
    custom_elements: dict[str, dict] | None = None,
    pair_enthalpies: dict[str, float] | None = None,
) -> dict:
    """Apply the nine canonical empirical phase-prediction rules to a batch.

    Each verdict comes with the descriptor value it was judged on and
    the published threshold, so the margin is auditable. These rules are
    weak empirical screens calibrated on small historical datasets.
    Treat verdicts as hints, never ground truth. A rule outside its
    domain says ``not_applicable``: Tsai without Cr or V, and Sheikh
    with any element beyond Ti, Zr, Hf, V, Nb, Ta, Cr, Mo and W.
    ``guo_vec`` carries a ``note`` when VEC sits within 0.2 of a Guo
    cutoff. ``senkov_kappa`` carries one when an element of the pair
    behind Senkov's ΔH_IM (``im_pair``) is under 10 at.%. The ``note``
    is null when there is nothing to say. ``custom_elements`` and
    ``pair_enthalpies`` work as in ``alloy_descriptors``.
    """
    return stamp(service.alloys.alloy_rules(
        compositions, king_temperature, custom_elements, pair_enthalpies
    ))


def omega_sensitivity(
    composition: str,
    perturbation_kj_mol: float = 2.0,
    custom_elements: dict[str, dict] | None = None,
    pair_enthalpies: dict[str, float] | None = None,
) -> dict:
    """Report how sensitive Omega is to the choice of Miedema pair table.

    Omega diverges as the mixing enthalpy approaches zero, so for
    near-ideal alloys its value depends strongly on which published pair
    table supplies the enthalpies. This tool returns the per-pair
    contributions ``4 H_ij c_i c_j`` and identifies the element whose
    pairs dominate the enthalpy. It then recomputes Omega with that
    element's pair enthalpies shifted by +/- ``perturbation_kj_mol``
    (default 2 kJ/mol, the typical spread between published Miedema
    compilations). A wide Omega range means the verdict, not the number,
    is what to trust.
    """
    return stamp(service.alloys.omega_sensitivity(
        composition, perturbation_kj_mol, custom_elements, pair_enthalpies
    ))


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
    criteria calibrated on small datasets, so treat verdicts as hints.
    """
    return stamp(service.alloys.oxide_report(
        family, cations, b_site_cations, oxygen_per_formula_unit, spin
    ))


def ceramic_report(structure: str, metals: str) -> dict:
    """Composition-only descriptors for a high-entropy carbide, nitride or diboride.

    ``structure`` is ``rock_salt_carbide``, ``rock_salt_nitride`` or
    ``diboride``, and ``metals`` is the metal-sublattice formula. The
    report gives the configurational entropy in every normalization that
    papers use. For the rock-salt structures it also gives the VEC per
    formula unit against the literature's reference points. It
    deliberately gives no formability verdict, because no single
    published window exists.
    """
    return stamp(service.alloys.ceramic_report(structure, metals))


def element_data(elements: list[str] | None = None) -> dict:
    """The tabulated values behind every number, per element, with sources.

    Returns radius, melting point, valence, electronegativity, molar
    volume and moduli, each with its unit. The payload also names the
    radius source and where good sources disagree, which features each
    element supports, the cited references and the SHA-256 of every
    data file. Omitting ``elements`` returns all 55 elements.
    """
    return stamp(service.alloys.element_data(elements))


def element_coverage() -> dict:
    """List which elements each data table covers.

    Use this before batch calls: compositions outside the alloy table
    produce warnings rather than numbers, and oxide cations outside the
    Shannon table raise structured errors.
    """
    return stamp(service.alloys.element_coverage())


# -- corpus, properties, applicability, design, campaigns -------------------
#
# The tools below expose the post-v2.4 capability layers. Design rules,
# shared with the original seven tools: plain functions with no MCP
# dependency; every uncertainty and domain field at the top level of its
# payload entry, never nested where a client might drop it; missing
# optional extras or missing local data surface as ValueError with the
# exact fix in the message, not a traceback; and the expensive calls
# carry hard caps because agents call tools carelessly.

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
    for the licensing reasons in the corpus card. ``corpus_build`` builds
    it once.
    """
    subset = service.dataset.tool_slice(
        version, elements, contains, excludes, n_elements_min, n_elements_max,
        phase, source, labelled, has_conflict, descriptor_ready,
    )
    return stamp(service.dataset.sample(subset, limit))


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
    subset = service.dataset.tool_slice(
        version, elements, contains, excludes, n_elements_min, n_elements_max,
        phase, source, labelled, has_conflict, descriptor_ready,
    )
    return stamp(subset.describe())


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
    subset = service.dataset.tool_slice(
        version, elements, contains, excludes, n_elements_min, n_elements_max,
        phase, source, labelled, has_conflict, descriptor_ready,
    )
    n_rows = subset.to_csv(target)
    return stamp({"path": str(target.resolve()), "n_rows": n_rows, "corpus_version": subset.version})


def corpus_build(versions: list[str] | None = None) -> dict:
    """Build the corpus on this machine, once. Every corpus tool needs it.

    Every source dataset ships with the package, so the build needs no
    network. Builds every version by default. Rebuilding reproduces the
    same corpus, so calling it again is harmless.
    """
    return stamp(service.dataset.build_all(versions))


def predict_properties(
    compositions: list[str],
    properties: list[str] | None = None,
    alpha: float = 0.1,
    processing: str | None = None,
) -> dict:
    """Predict properties with uncertainty and domain flags, per composition.

    Tier A (density, melting_temperature, cost_per_kg) is closed-form
    over cited tables. Tier B (hardness) is a fitted surrogate and
    always carries a conformal interval, its training-domain flag, and
    its model card reference. Every entry's ``interval``, ``in_domain``,
    ``tier``, and ``warnings`` sit at the top level of that property's
    payload. Missing optional installs come back as a clear error
    naming the pip command.
    """
    return stamp(service.predictions.predict_properties(compositions, properties, alpha, processing))


def measured_properties(
    prop: str = "hardness", contains: list[str] | None = None, limit: int = 25
) -> dict:
    """Measured hardness or density from Borg et al. (2020), with DOIs.

    Returns the measurements the hardness model trains on, or the
    densities the rule-of-mixtures estimate is checked against.
    ``contains`` keeps only alloys containing every one of its elements.
    The result gives the exact match count and a sample capped at 50
    rows.
    """
    return stamp(service.dataset.measured_sample(prop, contains, limit))


def check_applicability(composition: str) -> dict:
    """Report whether a composition sits inside what the corpus covers.

    Returns the orthogonal novelty components (exact family seen and
    how often, nearest-family Jaccard distance, descriptor-cloud
    distance, element coverage) plus the conservative combined
    ``in_domain`` flag. Needs a built corpus. The components describe
    how well this package's corpus covers your query, nothing else.
    """
    return stamp(service.predictions.check_applicability(composition))


def predict_phase_set(
    compositions: list[str],
    task: str = "single_vs_multi",
    alpha: float = 0.1,
    version: str = "0.1.0",
) -> dict:
    """Phase prediction with a conformal prediction set, per composition.

    The model is a random forest on the 14 descriptors, trained on the
    corpus, with split-conformal calibration. The set contains the true
    label about ``1 - alpha`` of the time on alloys like the calibration
    set. A set
    with more than one label means the model cannot decide. Each entry
    carries class probabilities, the corpus ``in_domain`` flag and
    novelty measures, and plain-language warnings. The first call per
    task fits the model (several seconds).
    """
    return stamp(service.predictions.predict_phase_set(compositions, task, alpha, version))


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
    50,000-point lattice budget. An oversized request is refused with
    the cap named, never silently truncated. Objectives are
    ``[direction, property]`` pairs, e.g.
    ``[["maximize", "hardness"], ["minimize", "cost_per_kg"]]``.
    Fitted objectives rank by the conservative interval end by default.
    Every candidate carries descriptors, all nine rule verdicts,
    property predictions with intervals, novelty, the domain flag, and
    ``phase``: its four-class phase prediction set (null without a built
    corpus). An element cap such as ``{"element": "Al", "max": 0.2}``
    keeps hardness searches from drifting to aluminides.
    Results are a screening aid, not answers. See
    docs/design-recovery.md.
    """
    return stamp(
        service.design.design_search(
            elements,
            n_elements_min=n_elements_min,
            n_elements_max=n_elements_max,
            step=step,
            objectives=objectives,
            composition_constraints=composition_constraints,
            rule_constraints=rule_constraints,
            property_constraints=property_constraints,
            include_out_of_domain=include_out_of_domain,
            optimize_bound=optimize_bound,
            max_candidates=max_candidates,
            alpha=alpha,
        )
    )


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
    never writes the file. An inline call gets the canonical campaign
    back to save. Batch size is capped at 10. Suggestions carry the
    ensemble mean, a 90 percent conformal interval set from the forest's
    out-of-bag errors (coverage measured in docs/campaign-replay.md),
    and the domain flag. Below the 10-observation floor the loop refuses
    rather than guessing.
    """
    from .design.campaign import Campaign

    if (campaign_path is None) == (campaign is None):
        raise ValueError(
            "give exactly one of campaign_path (a campaign JSON file) or campaign "
            "(the file's contents)"
        )
    if campaign is not None:
        return stamp(service.design.suggest_inline(campaign, n=n, strategy=strategy))
    service.design.check_batch(n)
    path = pathlib.Path(campaign_path)
    if not path.exists():
        raise ValueError(f"no campaign file at {campaign_path!r}")
    try:
        loaded = Campaign.load(path)
    except (RuntimeError, ValueError) as exc:
        raise ValueError(str(exc)) from None
    return stamp({"campaign_path": str(path), **service.design.suggestions(loaded, n, strategy)})


# -- benchmark ----------------------------------------------------------------
#
# Thin wrappers over hea_bench.service.benchmark, which the app's Benchmark
# tab also calls, so the two return the same numbers.


def _bench(method, *args, **kwargs) -> dict:
    try:
        return method(*args, **kwargs)
    except FileNotFoundError as exc:
        raise needs_corpus(exc) from None
    except ImportError:
        raise ValueError(
            'the fitted baselines need scikit-learn: pip install "hea-bench[mcp]"'
        ) from None


def _new_file(path: str) -> pathlib.Path:
    target = pathlib.Path(path).expanduser()
    if target.exists():
        raise ValueError(f"{str(target)!r} already exists. Choose a new file name.")
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def benchmark_summary(task: str = "single_vs_multi", version: str = "0.1.0") -> dict:
    """The paired benchmark at a glance: splits, digests and the published table.

    Two frozen 5-fold schemes cover the same rows. Random folds measure
    interpolation within known alloy families, and family-grouped folds
    measure extrapolation to unseen element systems. Returns the class
    balance and family overlap of each scheme, whether both match their
    frozen SHA-256 digests, the baselines you can score live with
    ``benchmark_run``, and the published results table for v0.1.0.
    """
    return stamp(_bench(service.benchmark.summary, task, version))


def benchmark_run(model: str, task: str = "single_vs_multi", version: str = "0.1.0") -> dict:
    """Score one published baseline live under both split schemes.

    Fits and scores ``model`` on every fold of the random and the
    family-grouped scheme, on the same rows as the published table. It
    reports per-scheme metrics plus the ``gap`` (random minus grouped),
    which measures how much harder extrapolation is than interpolation.
    The fitted baselines take tens of seconds.
    """
    return stamp(_bench(service.benchmark.run, model, task, version))


def benchmark_folds(path: str, task: str = "single_vs_multi", version: str = "0.1.0") -> dict:
    """Write every benchmark row with its fold under both schemes to a new CSV.

    The file for training your own model offline: ``composition_key``,
    ``family``, ``label``, ``grouped_fold``, ``random_fold``,
    ``n_elements`` and ``descriptors_finite``. Score the predictions
    with ``benchmark_score``. Refuses to overwrite an existing file.
    """
    target = _new_file(path)
    folds = _bench(service.benchmark.folds_csv, task, version)
    target.write_text(folds["text"], encoding="utf-8", newline="")
    return stamp({"path": str(target.resolve()), "n_rows": folds["n_rows"], "task": task})


def benchmark_score(
    predictions_path: str,
    task: str = "single_vs_multi",
    version: str = "0.1.0",
    model_name: str = "",
) -> dict:
    """Score your own model's predictions under both split schemes.

    ``predictions_path`` is a CSV with the columns ``composition_key``,
    ``grouped`` and ``random``. The ``grouped`` and ``random`` columns
    hold the label your model predicted for the row while it sat in that
    scheme's test fold. The folds come from ``benchmark_folds``. Returns
    the same report as ``benchmark_run``, including the ``gap``.
    """
    source = pathlib.Path(predictions_path).expanduser()
    if not source.exists():
        raise ValueError(f"no predictions file at {predictions_path!r}")
    text = source.read_text(encoding="utf-8-sig")
    return stamp(_bench(service.benchmark.score_csv, text, task, version, model_name))


def coverage_study(task: str = "single_vs_multi", version: str = "0.1.0") -> dict:
    """Check the phase prediction sets' coverage on held-out alloy families.

    Reruns the conformal coverage study under the family-grouped scheme.
    It reports how often the prediction set contains the true label at
    several miscoverage levels, for all test alloys and separately for
    the in-domain and out-of-domain groups. Takes a minute or more.
    """
    return stamp(_bench(service.benchmark.coverage, task, version))


def about() -> dict:
    """Version, provenance, license, capability availability, citations."""
    import importlib.util

    built = service.dataset.status()["built"]
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
    return stamp({
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
        "True keeps only rows carrying a consensus phase label, and false keeps "
        "only unlabelled rows. Omit it for both."
    ),
    "has_conflict": (
        "True keeps only rows quarantined because their sources disagree on the "
        "phase, and false excludes them. Omit it for both."
    ),
    "descriptor_ready": (
        "True keeps only rows whose every element is present in the descriptor "
        "tables, so descriptors can actually be computed for them."
    ),
    "version": (
        "Corpus version. '0.2.0' (default) is the largest. It adds an LLM-extracted "
        "database whose labels agree with the reference on roughly 70% of "
        "overlapping rows, with every disagreement quarantined as a conflict. '0.1.0' is "
        "the hand-curated reference corpus every published hea-bench number is "
        "measured on. This counter is independent of the package version."
    ),
}

_BATCH_DOC = (
    "Formulas to evaluate in a single call, e.g. ['CoCrFeMnNi', 'Al0.3CoCrFeNi']. "
    "The tool normalizes element counts to mole fractions, so they need not sum "
    "to 1. Batch here rather than issuing one call per alloy."
)
_KING_TEMPERATURE_DOC = (
    "Temperature in kelvin at which King's Phi is evaluated. Defaults to the "
    "melting-point estimate derived from the composition. Set it only to "
    "reproduce a published value quoted at a stated temperature."
)
_CUSTOM_ELEMENTS_DOC = (
    "Elements outside the 55-element table, for this call only. Key each one by "
    "a label shaped like an element symbol that is not a real one (a capital "
    "letter, optionally followed by one lowercase letter), so formulas can use "
    "it. Example: {'Xx': {'radius_pm': 140, 'melting_K': 1800, 'valence': 6, "
    "'electronegativity': 1.7}} with the formula 'CoCrFeNiXx'. radius_pm, melting_K "
    "and valence are required, and electronegativity is optional."
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
    "every published number is measured on. '0.2.0' is larger, but its added "
    "labels are noisier."
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
            "equiatomic alloy or 'Al0.3CoCrFeNi' for a scaled one. The tool "
            "normalizes counts to mole fractions, so they need not sum to 1."
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
            "Mole-fraction spacing of the search lattice. Floor 0.05. Finer "
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
            "{'rule': 'yang_omega', 'satisfied': true}. The 'satisfied' field also "
            "accepts a list of acceptable verdicts. Rule names: guo_vec, king_phi, "
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
            "or hea_bench.design.campaign.Campaign.save writes it. Read only: this "
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
            "and citation keys. Every prediction carries an interval (where a "
            "model is fitted) and an in_domain flag at the top level of its "
            "payload. Batch compositions into one call of alloy_descriptors, "
            "alloy_rules, predict_properties or predict_phase_set. Check "
            "element_coverage before large sweeps, omega_sensitivity before "
            "trusting any Omega magnitude for a near-ideal alloy, and "
            "check_applicability before trusting any prediction for an unusual "
            "chemistry. The dataset, phase-set, applicability and benchmark "
            "tools need the corpus: call corpus_build once. design_search is "
            "the expensive call and enforces hard caps. The about tool reports "
            "which capabilities are available in this environment."
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

    Raises rather than warns when a parameter has no entry. An
    undocumented parameter should break the test suite the moment it is
    added, not ship as a blank field in the manifest.
    """
    for tool in server._tool_manager.list_tools():
        docs = _PARAM_DOCS.get(tool.name)
        if docs is None:
            raise RuntimeError(
                f"tool {tool.name!r} has no _PARAM_DOCS entry. Add one, even if "
                f"the tool takes no parameters."
            )
        properties = tool.parameters.get("properties", {})
        undocumented = sorted(set(properties) - set(docs))
        if undocumented:
            raise RuntimeError(
                f"tool {tool.name!r} has undocumented parameters "
                f"({', '.join(undocumented)}). Add them to _PARAM_DOCS."
            )
        for name, schema in properties.items():
            schema["description"] = docs[name]


def main() -> None:
    """Run the hea-bench MCP server over stdio."""
    build_server().run()


if __name__ == "__main__":
    main()
