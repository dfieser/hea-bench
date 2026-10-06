# AGENTS.md

Machine-oriented usage guide for `hea-bench`. If you are an AI coding
agent integrating this library into another project, read this first.
It tells you the public API, exact return types and units, the
fastest path to each common task, and the mistakes to avoid. Every
snippet here is copy-pasteable and was checked against the shipped
code.

> **Editing this repo's own docs (or this file)?** Follow the writing
> rule in [CONTRIBUTING.md](./CONTRIBUTING.md): minimize jargon and
> explain any necessary term inline in plain language, and always state
> what a number is and its units. Don't defer to a glossary.

## What this is

`hea-bench` is an open, interpretable **calculator** of the standard
high-entropy-alloy (HEA) thermodynamic and geometric descriptors plus
the canonical empirical **phase-prediction rules**. Every descriptor is
a transparent closed-form expression over a curated element-property
table. The fitted predictions (hardness, phase prediction sets) carry
calibrated uncertainty and a flag for alloys unlike their training data.

One calculation core, four parts, and every feature is in all four
(owner rule, 2026-10-06), so point each person at whichever part suits
them:

1. **Python library + CLI**: this package (`pip install hea-bench`, or
   `pip install "hea-bench[all]"` for the fitted models and the MCP
   server too).
2. **MCP server**: `pip install "hea-bench[mcp]"`, then run
   `hea-bench-mcp` (stdio), or `uvx --from "hea-bench[mcp]"
   hea-bench-mcp`. Twenty-four tools over this same library: the
   calculator (`parse_composition`, batch `alloy_descriptors` with the
   Miedema enthalpies and `alloy_rules`, both taking custom elements and
   pair values, `omega_sensitivity`, `oxide_report`, `ceramic_report`,
   `element_data`, `element_coverage`), the dataset (`corpus_build`,
   `corpus_query`, `corpus_describe`, `corpus_export`,
   `measured_properties`), predictions (`predict_properties`,
   `predict_phase_set`, `check_applicability`), design
   (`design_search`, `campaign_suggest`), the benchmark
   (`benchmark_summary`, `benchmark_run`, `benchmark_folds`,
   `benchmark_score`, `coverage_study`) and `about`, which reports what
   is available. Every response carries units or uncertainty fields, a
   citation key where a parametrization is involved, and the library
   version. If you are an agent with MCP support, prefer those tools
   over reimplementing the formulas below; if not, the Python API is
   identical.
3. **Web app**: <https://dfieser.github.io/hea-bench/>, built from
   `web/`. The calculator (alloys, oxides, ceramics, property and phase
   predictions), the Dataset, Design and Benchmark tabs. Point a person
   who does not code here.
4. **Desktop app**: one portable offline exe that is the web app in a
   Tauri window.

The browser/desktop calculator core (`web/hea-calculator-core.js`) is a
pure-JS reimplementation of this library and is **parity-tested**
against it on every binary pair and the canonical multi-element fixtures
(`tests/test_web_parity.py`). The library core is composition-only and
**dependency-free**. The app's corpus, benchmark, design and prediction
features run this package itself in the page (Pyodide), checked against
CPython by `tests/test_web_engine.py`. If you add a public name, CI
fails until the feature has its library function, its MCP tool and a
working app surface: `tests/test_feature_parity.py` names the gap and
the exact fix, and `hea-bench/CLAUDE.md` lists the steps.

## Install and import

```bash
pip install hea-bench
```

```python
import hea_bench as hb
```

Python >= 3.10. No required runtime dependencies for the core. The
`[dev]` extra adds pytest/ruff only.

## The one mental model you need

A **composition is a plain `dict`** mapping element symbol to amount:
`{"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}`. Amounts do
**not** need to sum to 1; they are normalized internally, so
`{"Al": 1, "Co": 1, "Cr": 1}` is equiatomic AlCoCr. Every descriptor
and rule accepts this dict directly. You rarely need anything else.

## Descriptors (pure functions, exact units)

All take a composition dict (or the result of `parse_formula`) and
return a float.

| Call | Returns | Unit | Notes |
|---|---|---|---|
| `hb.smix(comp)` | mixing entropy | J/(mol·K) | `-R Σ cᵢ ln cᵢ` |
| `hb.delta(comp)` | atomic-size mismatch | **percent** (e.g. 3.164, not 0.03) | |
| `hb.vec(comp)` | valence electron concentration | electrons | linear mean |
| `hb.melting_temperature(comp)` | average melting point | K | rule-of-mixtures |
| `hb.mixing_enthalpy(comp)` | Miedema mixing enthalpy | **kJ/mol** | semi-empirical estimate |
| `hb.omega(comp)` | Yang-Zhang Ω | dimensionless | `Tm·ΔS / \|ΔH\|` |
| `hb.s_excess(comp)` | Mansoori excess entropy | J/(mol·K) | Ye 2015 packing/size term |
| `hb.delta_g_ss(comp, temperature=None)` | solid-solution Gibbs proxy | kJ/mol | defaults to `T = Tm` |
| `hb.delta_g_max(comp)` | most-stable binary-subsystem proxy | kJ/mol | min over raw `ΔHᵢⱼ`, no composition scaling |
| `hb.phi_king(comp, temperature=None)` | King capital `Phi` | dimensionless | defaults to `T = Tm` |
| `hb.phi_ye(comp)` | Ye lowercase `phi` | dimensionless | uses `s_excess(comp)` |
| `hb.delta_chi(comp)` | electronegativity mismatch Δχ | Pauling scale | composition-weighted std |
| `hb.mean_electronegativity(comp)` | mean Pauling electronegativity | Pauling scale | linear mean |
| `hb.singh_lambda(comp)` | Singh Λ = ΔS/δ² | J/(mol·K·%²) | `math.inf` when δ = 0 |
| `hb.wang_gamma(comp)` | Wang solid-angle γ | dimensionless | 1.0 for equal radii |
| `hb.h_elastic(comp)` | Andreoli elastic-strain energy | kJ/mol | `None` if B or V missing |

```python
cantor = {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}
hb.smix(cantor)              # 13.381  (= R·ln 5)
hb.delta(cantor)             # 3.164   (percent)
hb.vec(cantor)               # 8.0
hb.melting_temperature(cantor)  # 1801.2 (K)
hb.mixing_enthalpy(cantor)   # -4.16   (kJ/mol)
hb.omega(cantor)             # 5.794
hb.s_excess(cantor)          # 0.318   (J/(mol·K))
hb.delta_g_ss(cantor)        # -28.262 (kJ/mol)
hb.delta_g_max(cantor)       # -8.000  (kJ/mol)  most-negative Miedema pair
hb.phi_king(cantor)          # 3.533
hb.phi_ye(cantor)            # 34.822
hb.delta_chi(cantor)         # 0.138   (Pauling scale)
hb.mean_electronegativity(cantor)  # 1.766
hb.singh_lambda(cantor)      # 1.337
hb.wang_gamma(cantor)        # 1.093
hb.h_elastic(cantor)         # 0.900   (kJ/mol)
```

These values for the Cantor alloy are pinned in the regression
suite; treat them as the canonical sanity check.

## Descriptor backends (optional)

The descriptor layer is backend-pluggable. `get_backend("native")` is
the stdlib default documented above. With the `interop` extra
(`pip install "hea-bench[interop]"`), `get_backend("heacalculator")`
adapts an installed HEACalculator to the same interface:
`compute(comp)` returns every union descriptor name with `None` for
anything the active backend cannot produce, and
`descriptor_matrix(comps, backend=...)` builds that backend's feature
matrix. Same-named values legitimately differ between backends
(different vendored reference data; radius conventions differ most).
The measured comparison is `docs/backend-agreement.md`; a missing
install raises `BackendUnavailableError` naming the exact pip command.
The CLI mirror is `hea-bench describe FORMULA --backend native|heacalculator`.

## Parsing formula strings

Every function that takes a composition also takes a formula string,
so `hb.smix("CoCrFeMnNi")` works. The parser accepts compact formulas
(`"CoCrFeMnNi"`), subscripted formulas (`"CuCoMn1.75NiFe0.25"`),
space-separated amounts, repeated elements, which add up
(`"CoCrFeNiNi"` is Ni at 40 at.%), and group notation, where a
bracketed group keeps its own ratio and takes the amount after it
(`"(CoCrFeNi)95Al5"` is 23.75 at.% each of Co, Cr, Fe and Ni plus 5
at.% Al). Groups nest. The browser core parses identically, which a
CI parity test enforces.

```python
comp = hb.parse_formula("CoCrFeMnNi")   # dict-like Composition
hb.normalize(comp)                      # explicit mole-fraction dict
hb.smix(comp)                           # descriptors accept it directly
hb.smix("CoCrFeMnNi")                   # or the formula string
```

## Custom elements and pair values

`hb.custom_data(elements=..., pair_enthalpies=...)` is a context
manager: inside the `with` block every descriptor, rule and formula
parse also knows your elements and your pair enthalpies. An element is
`{"radius_pm", "melting_K", "valence", "electronegativity"}`
(electronegativity optional). A label shaped like an element symbol
(`Xx`) can be written in formulas; `X1` cannot, because it reads as X
with amount 1. A pair value (`"Co-Xx"`, kJ/mol) adds a missing pair or
overrides a tabulated one. Blocks nest, and nothing leaks outside them.

```python
xx = {"Xx": {"radius_pm": 140.0, "melting_K": 1500.0, "valence": 5, "electronegativity": 1.6}}
pairs = {"Co-Xx": -10.0, "Cr-Xx": -8.0, "Fe-Xx": -9.0, "Ni-Xx": -12.0}
with hb.custom_data(elements=xx, pair_enthalpies=pairs):
    hb.mixing_enthalpy(hb.parse_formula("CoCrFeNiXx"))   # -8.64 (kJ/mol)
```

A custom element with no pair values raises a `ValueError` naming the
missing pairs from any enthalpy-based descriptor. The MCP tools
`alloy_descriptors`, `alloy_rules` and `omega_sensitivity` take the same
two inputs as `custom_elements` and `pair_enthalpies`.

## Rules (classifiers)

```python
from hea_bench.rules import (
    guo_vec, king_phi, senkov_kappa, sheikh_ductility, tsai_sigma,
    yang_omega, ye_phi, yeh_smix, zhang_delta,
)
```

Each module exposes `predict(composition, ...)`, a `DESCRIPTION`
string, and (for the tunable ones) a `DEFAULT_THRESHOLD`. Return
values are strings:

| Rule | Call | Returns one of | Threshold arg |
|---|---|---|---|
| Yeh ΔS_mix | `yeh_smix.predict(comp)` | `"HEA"` / `"MEA"` / `"dilute"` | fixed (descriptive) |
| Zhang δ | `zhang_delta.predict(comp, threshold=6.5)` | `"single-phase"` / `"multi-phase"` | percent, default 6.5 |
| Yang Ω | `yang_omega.predict(comp, threshold=1.1)` | `"single-phase"` / `"multi-phase"` | default 1.1 |
| Guo-Liu VEC | `guo_vec.predict(comp)`; `guo_vec.boundary_note(comp)` | `"FCC"` / `"BCC"` / `"mixed"`; note is a string when VEC is within 0.2 of a cutoff, else `None` | fixed bounds 8.0 / 6.87 |
| King `Phi` | `king_phi.predict(comp, temperature_policy=None, threshold=1.0)` | `"solid_solution"` / `"intermetallic"` | defaults to `T = Tm` |
| Ye `phi` | `ye_phi.predict(comp, threshold=20.0)` | `"solid_solution"` / `"intermetallic"` | default 20.0 |
| Senkov-Miracle κ | `senkov_kappa.predict(comp, temperature=None)` | dataclass: `.verdict`, `.k1`, `.k1_cr`, `.g_ss_kj`, `.g_im_kj`, `.im_pair`, `.note` (set when that pair has an element under 10 at.%) | defaults to `T = Tm`; k₂ = 0.6 |
| Tsai σ window | `tsai_sigma.predict(comp)` | dataclass: `.verdict` in `sigma_prone` / `sigma_unlikely` / `not_applicable` | fixed 6.88-7.84, needs Cr/V |
| Sheikh ductility | `sheikh_ductility.predict(comp)` | dataclass: `.verdict` in `ductile` / `brittle` / `borderline` / `not_applicable`, `.applies` | fixed 4.5 / 4.6; only alloys of Ti, Zr, Hf, V, Nb, Ta, Cr, Mo, W |

The three v2.1 rules return small frozen dataclasses (not bare
strings) because their verdicts carry context (temperature, window
membership); use `.verdict` for the string. Sheikh returns
`not_applicable` for any alloy with an element outside the nine
refractory metals its screen was built on.

```python
zhang_delta.predict(cantor)   # 'single-phase'
guo_vec.predict(cantor)       # 'FCC'
yeh_smix.predict(cantor)      # 'HEA'
king_phi.predict(cantor)      # 'solid_solution'
ye_phi.predict(cantor)        # 'solid_solution'
```

**Important:** these rules are weak, semi-empirical screens, not
predictions. They were calibrated on small historical datasets and
generalize poorly; do not treat a rule's output as ground truth.

## The Ω singularity (read this)

`omega = Tm·ΔSmix / |ΔHmix|` diverges as `ΔHmix → 0`. For near-ideal
alloys (`|ΔHmix| ≲ 1–2 kJ/mol`) Ω is extremely sensitive — a few-kJ
change in one pair value, or a different Miedema parametrization, can
move Ω by an order of magnitude. Read Ω **qualitatively** in that
regime; the phase verdict (Ω ≫ 1.1) is robust even when the magnitude
is not. Absolute `ΔHmix` values depend on which Miedema pair table is
used; published compilations disagree most on **Mn**.

`hb.omega_sensitivity(comp, perturbation_kj_mol=2.0)` measures this for
one alloy. It returns each pair's contribution to ΔHmix, the element
whose pairs dominate it, and Ω recomputed with that element's pair
enthalpies shifted by ±2 kJ/mol, the typical spread between published
tables. `diverges_within_range` is True when ΔHmix can cross zero
inside that shift, so only the verdict is worth reading.

## Command line

```bash
hea-bench --version
hea-bench describe Al0.3CoCrFeNi   # every descriptor for one composition, as JSON
```

The CLI covers the version and that one report; the Python API above
is the documented surface.

## Data layout

- `src/hea_bench/descriptors/data/` — the vendored element table (55
  elements: radius, melting point, VEC, Pauling electronegativity), the
  matminer-derived Miedema pair-enthalpy table (`pair_enthalpies.tsv`,
  75 elements), and the Miedema elemental-parameter table
  (`miedema_parameters.csv`). These are shipped inside the wheel; no
  fetch step is needed.
- `web/hea-calculator-core.js` — the JS port of the same math + tables,
  used by the browser and desktop apps.

The **Miedema formation-enthalpy decomposition** is in the library
too, the same numbers the apps show: compound formation enthalpy,
solid-solution enthalpy split into chemical, elastic and structural
terms, and amorphous enthalpy split into chemical and topological
terms, all in kJ/mol.

```python
from hea_bench.descriptors.miedema_decomposition import miedema_decomposition
d = miedema_decomposition({"Cu": 0.5, "Zr": 0.5})
d["compound"]["H_form"], d["amorphous"]["H_total"]   # -30.78, -16.19
```

It covers the 37 elements of the Miedema parameter table; any pair
outside it makes the three totals `None` with a warning, and the core
descriptors are unaffected. The MCP tool `alloy_descriptors` returns it
as `miedema_enthalpies`.

`hea_bench.descriptors.elements.element_data(["Fe", "Ni"])` returns the
tabulated values for those elements (all 55 with no argument), their
units, which features each element supports, and the sources and
SHA-256 fingerprints of the data files. The MCP tool is `element_data`.

## Oxides module (experimental)

`hea_bench.oxides` extends the calculator to **high-entropy oxides**:
closed-form descriptors and weak empirical formability screens for four
structure families (rock salt, perovskite, fluorite, pyrochlore),
computed over vendored Shannon (1976) ionic radii with an explicit
charge-neutrality oxidation-state solver.

```python
from hea_bench import oxides
j14 = oxides.describe_rock_salt({"Mg": 1, "Co": 1, "Ni": 1, "Cu": 1, "Zn": 1})
j14["verdicts"]["entropy"]            # 'high-entropy'
pvk = oxides.describe_perovskite({"Sr": 1}, {"Zr": 1, "Sn": 1, "Ti": 1, "Hf": 1, "Mn": 1})
round(pvk["descriptors"]["goldschmidt_t"], 3)   # 0.979
pvk["verdicts"]["bartel"]             # 'perovskite'  (tau = 3.723 < 4.18)
flu = oxides.describe_fluorite({"Ce": 1, "Zr": 1, "Nd": 1, "Y": 1, "Er": 1}, oxygen=1.7)
round(flu["descriptors"]["radius_sigma"], 4)    # 0.0976  (published value)
```

Each `describe_*` returns one dict: normalized sites, solved oxidation
states, Shannon radii used, descriptors, verdicts, warnings. Entropy
verdicts classify on the most-disordered sublattice (the HEO
convention). The oxide verdicts are screens, not predictions, exactly
like the alloy rules. The JS core ports the same functions
(`describeRockSalt`, `describePerovskite`, `describeFluorite`,
`describePyrochlore`), parity-locked by
`tests/test_web_oxides_parity.py`, and the calculator page exposes them
as an **Oxides mode** (mode switch at the top of the input rail). The
module is deliberately not exported at the `hea_bench` top level;
import it as `from hea_bench import oxides`.

## Ceramics module (experimental)

`from hea_bench import ceramics`:
`describe_rock_salt_carbide(metals)`, `describe_rock_salt_nitride(metals)`,
`describe_diboride(metals)` take the metal-sublattice composition dict
and return one report: normalized metals, configurational entropy in
every published normalization convention (per mole cation, per formula
unit, per mole atoms; papers disagree silently, so all are labelled),
`vec_per_formula_unit` for the rock-salt classes (weighted metal group
count plus 4 for C or 5 for N) with annotated literature reference
points (8.4 hardness maximum, about 9.4 fracture resistance, about 9.5
plasticity), warnings, and citations. No verdicts are emitted, no size
mismatch yet (deferred with reasons), and no entropy-forming-ability
or DEED (DFT-only; no parity claimed). See `docs/ceramics.md`.

## Phase-prediction benchmark (experimental)

`hea_bench.benchmark` evaluates phase-prediction models under two
frozen five-fold splits of a consolidated experimental corpus (default
corpus v0.1.0, ~7,700 alloys from Borg 2020, Pei 2020, and Peivaste;
`load_benchmark(version="0.2.0")` opts into the 10,064-alloy corpus
that adds the Chizhevskiy LLM-extracted database, whose noisier labels
are quarantined-on-disagreement — see `data/raw/README.md`): a
**grouped** split
where a whole alloy family — the set of elements present, so every
stoichiometric variant of one system — stays on one side of each
train/test boundary, and a **random** split, the usual literature
protocol. Neither split is correct on its own: they answer different
questions (new stoichiometries of known systems versus unseen element
systems), and the gap between them quantifies how much of a
random-split score comes from testing on close relatives of training
alloys. For a stock random forest on this package's descriptors that
gap is about 0.21 balanced accuracy (0.941 random vs 0.734 grouped);
see `docs/benchmark-baselines.md`. The report field carrying the
per-metric difference is named `gap`.

```python
from hea_bench.benchmark import evaluate, load_benchmark, MajorityClass
bench = load_benchmark(task="single_vs_multi")   # or "phase4"
report = evaluate(MajorityClass(), bench)
print(report.table())                            # grouped vs random, side by side
```

The grouped score is an **upper bound** on true out-of-system
performance: element-set grouping still lets `CoCrFeNi` train while
`AlCoCrFeNi` is tested. The stricter subset-closure rule was measured
and ruled out, not skipped — on this corpus it collapses 94.5% of rows
into one indivisible component, so no k-fold split can respect it
(`subset_closure_components`, numbers pinned in the tests).

`evaluate` accepts either a trainable model (`fit(compositions, labels)`
+ `predict(compositions)`, refitted per fold) or a plain callable
mapping one composition dict to a label string (how the empirical rules
are scored). `hea_bench.benchmark.descriptor_matrix` builds a feature
matrix from this package's own descriptors for fitted models, and
`finite_descriptor_indices` drops the ~2% of rows where Ω or Φ is
singular (near-ideal alloys, ΔH_mix → 0).

**The corpus is built on your machine, once.** The largest source
dataset (Peivaste) declares no license, so neither the package nor the
repo ships it or anything derived from it. They ship a loader, a pinned
SHA-256 and a download step instead, plus every other source. One call
downloads the Peivaste file (6.4 MB), accepts it only if the hash
matches, and builds every corpus version:

```python
from hea_bench.corpus import build_corpus
build_corpus()                              # or build_corpus(peivaste_csv="peivaste.csv") offline
```

From an installed package the corpus lands in the per-user hea-bench
folder (`%LOCALAPPDATA%\hea-bench` on Windows, `~/.local/share/hea-bench`
on Linux, `~/Library/Application Support/hea-bench` on macOS); in a repo
checkout it lands in `data/consolidated/`. `HEA_BENCH_BENCHMARK_DIR`
points every load at a corpus built elsewhere. From an MCP client, call
the `corpus_build` tool once. The apps build it in the page, once per
release, after their in-page engine starts.

The split fold assignments are frozen: each carries a SHA-256 digest
pinned in `tests/test_benchmark_corpus.py`. **Do not update those
digests to make a test pass** — a moved digest means the benchmark
changed and needs a new corpus version, not a silenced test. Licensing
per source: `data/raw/README.md`.

## Corpus API

`hea_bench.corpus.load_corpus()` returns the full consolidated corpus,
by default the largest version, v0.2.0 (10,290 rows, including the 226
conflict-quarantined ones). `load_corpus(version="0.1.0")` returns the
hand-curated reference (7,783 rows, 100 quarantined) that
`load_benchmark`, the phase predictions and the applicability domain
always use, so every published number stays put. Every row carries
per-source provenance:
`labels` (per-source canonical), `raw_labels` (verbatim upstream phase
strings), `processing` and `doi` (Borg only), `source_row_ids`, and
`descriptor_ready`. Filters chain and AND together:

```python
from hea_bench.corpus import load_corpus
corpus = load_corpus()
corpus.query(contains=["Al", "Cr"], n_elements=(4, 6), labelled=True).describe()
```

`query` accepts `elements` (exact set), `contains`, `excludes`,
`n_elements` (int or inclusive range), `phase`, `source`, `family`,
`labelled`, `has_conflict`, `descriptor_ready`. `describe()` reports
counts and the multi-source agreement rate; `to_csv()` writes any slice
in the consolidated schema. Dataset card: `docs/corpus-card.md`.
`load_benchmark` is now a thin wrapper over this API; its outputs and
frozen digests are unchanged.

## Uncertainty API

`hea_bench.uncertainty` (stdlib, no extra needed for the wrappers
themselves): `ConformalClassifier(model).fit_calibrate(X_cal,
y_cal).predict_set(X, alpha=0.1)` returns one label set per row;
`ConformalRegressor(...).predict_interval(X, alpha=0.1)` returns
`(low, high)` tuples. Calibration rows must be disjoint from training
rows. Sets can be empty (no label credible at that level) and both
wrappers go maximal when `degenerate(alpha)` is True (calibration too
small for the requested level). `fit_domain(corpus)` returns a
JSON-serializable `DomainModel`; `domain.novelty(comp)` returns the
applicability components (`element_set_seen`, `family_count`,
`nearest_family_distance`, `descriptor_distance`, `element_coverage`)
plus the conservative `in_domain` flag. Read the components, not just
the flag. Empirical coverage: `docs/uncertainty-coverage.md`.

## Property API

`hea_bench.properties.predict_property(comp, prop, alpha=0.1,
processing=None)` returns a frozen `PropertyPrediction` with `value`,
`unit`, `interval` (tier B only), `alpha`, `tier`, `in_domain`,
`novelty`, `n_training`, `model_card`, and `warnings`.
`available_properties()` lists what exists: tier A `density` (g/cm3)
and `melting_temperature` (K) are stdlib closed forms; tier B
`hardness` (HV) needs `pip install "hea-bench[properties]"` and always
carries a conformal interval plus a domain flag fitted on its own
training data (Borg room-temperature HV, 417 alloys). Missing installs,
unknown properties, uncovered elements, and sub-floor training
populations raise `PropertyUnavailableError` naming the fix. Model
cards: `docs/property-hardness.md`, `docs/property-tier-a.md`. Read the
interval width before ranking close candidates; the cards state what
the error supports.

## Design search API

`hea_bench.design.search(elements, n_elements=(3,5), constraints=(),
objectives=(), step=0.05, n_candidates=50, seed=0,
max_evaluations=200_000, optimize_bound="point", alpha=0.1)` returns a
`ParetoResult` (candidates, seed, settings, n_evaluated, n_feasible,
n_front, `to_json()`). Constraints: `RuleConstraint(rule, satisfied)`,
`PropertyConstraint(prop, min=, max=, bound="point"|"lower"|"upper")`,
`CompositionConstraint(element, min=, max=)`,
`DomainConstraint(in_domain=True|False|None)`; a domain constraint is
injected ON by default, opt out with `DomainConstraint(in_domain=None)`.
Objectives: `Maximize(prop)` / `Minimize(prop)` over
`available_properties()` names. Every candidate carries descriptors,
all nine rule verdicts, property predictions with intervals, novelty
components, and the domain flag. The lattice is exhaustive within
`max_evaluations` and raises rather than sampling silently; truncation
to `n_candidates` is visible via `n_front`. Treat fronts as screening
output; see `docs/design-recovery.md`.

## Campaign API

`hea_bench.design.campaign.Campaign(objective, palette, constraints=(),
direction="maximize", seed=0, step=0.1, n_elements=(3,5),
warm_start=True)`; `observe(comp, value, processing=None,
uncertainty=None)`; `suggest(n=5, strategy="ei"|"ucb")` returns
`Suggestion` objects whose repr carries the interval and domain flag;
`save(path)`/`Campaign.load(path)` round-trip versioned plain JSON
(schema 1). Warm start pools Borg hardness rows matching the palette
when objective is "hardness"; any other objective starts cold. Below 10
informative rows `suggest` raises `ColdStartError`. Suggestion
intervals are ensemble spread (tree disagreement), not
coverage-calibrated; the module docstring states this. Replay study:
`docs/campaign-replay.md`.

## Coverage limit

The element table covers **55 elements** (alloy surface; the oxides
module has its own 94-element Shannon table). v2.1 added the full
experimentally active rare-earth palette (Pr Nd Sm Tb Dy Ho Er Tm Yb
Lu), Ga, Ge, the nuclear pair U/Th, Sr, and the solder metals Sb Bi
Pb. Compositions containing elements outside it (C, B, N, the alkali
metals) are not fully scorable: `delta`, `smix`-class
geometric/melting descriptors need the element table, while
Miedema-based descriptors fall back to the wider 75-element pair
table (which lacks exactly one of our pairs, Th-U; that pair raises
rather than returning a silent zero).
Carbon and boron are deliberately held out (no metallic radius; no
1-atm melting point for carbon).

## Things not to do

- **Do not edit the pinned numbers** in `tests/` to make a test pass.
  Those values are derived from the data and code; a changed number
  means real drift you should explain, not silence.
- **Do not edit `web/hea-calculator-core.js` to diverge from the Python
  library.** The two are parity-locked by `tests/test_web_parity.py`;
  change both together and re-run that test.
- **Do not add elements to the element table** without a citable source
  for the atomic radius, VEC, and melting point. Unsourced values
  corrupt every descriptor that uses them.
- **Do not treat `mixing_enthalpy` as a measured quantity.** It is a
  semi-empirical Miedema estimate with known systematic error for some
  pairs (Mn especially).
- **Do not assume composition fixes phase.** The same composition can
  form different phases depending on processing history; the descriptors
  describe equilibrium driving forces only.
- **Do not tag, version-bump, or publish by hand.** Pushing to `main`
  auto-releases every surface from the one version counter (see
  [RELEASING.md](./RELEASING.md)); hand-made tags and partial publishes
  are how the surfaces skew apart.

## Verifying your integration

After wiring this in, confirm the Cantor sanity values
(`smix=13.381`, `delta=3.164`, `vec=8.0`, `omega=5.794`,
`s_excess=0.318`, `delta_g_max=-8.000`, `phi_king=3.533`,
`phi_ye=34.822`, `delta_chi=0.1384`) and run the test suite (`python -m pytest -q`). If
those match, your environment is using the canonical implementation
correctly.

## One-shot AI jumpstart (copy-pasteable)

This snippet exercises every public surface and prints a single
machine-readable JSON manifest of the library's state. Run it after
install to verify everything works and to see the surface in one
place.

```python
import json
import hea_bench as hb
from hea_bench.rules import (
    guo_vec, king_phi, yang_omega, ye_phi, yeh_smix, zhang_delta,
)

cantor = {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}
print(json.dumps({
    "version": hb.__version__,
    "cantor_descriptors": {
        "smix":                hb.smix(cantor),
        "delta":               hb.delta(cantor),
        "vec":                 hb.vec(cantor),
        "melting_temperature": hb.melting_temperature(cantor),
        "mixing_enthalpy":     hb.mixing_enthalpy(cantor),
        "omega":               hb.omega(cantor),
        "s_excess":            hb.s_excess(cantor),
        "delta_g_ss":          hb.delta_g_ss(cantor),
        "delta_g_max":         hb.delta_g_max(cantor),
        "phi_king":            hb.phi_king(cantor),
        "phi_ye":              hb.phi_ye(cantor),
        "delta_chi":           hb.delta_chi(cantor),
        "mean_electronegativity": hb.mean_electronegativity(cantor),
    },
    "cantor_rules": {
        "yeh_smix":    yeh_smix.predict(cantor),
        "zhang_delta": zhang_delta.predict(cantor),
        "guo_vec":     guo_vec.predict(cantor),
        "yang_omega":  yang_omega.predict(cantor),
        "king_phi":    king_phi.predict(cantor),
        "ye_phi":      ye_phi.predict(cantor),
    },
}, indent=2))
```

If your numbers match to four decimal places and your rule outputs
are identical strings, your environment is correctly using the
canonical implementation. If not, check (in this order): Python
version >= 3.10, whether you accidentally installed a fork or an
older PyPI snapshot, whether your composition dict uses integer
proportional amounts vs already-normalised mole fractions (both
work, the descriptors normalise internally).
