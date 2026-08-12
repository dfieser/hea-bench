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
the canonical empirical **phase-prediction rules**. Every quantity is a
transparent closed-form expression over a curated element-property
table — no fitted model, no black box.

One calculation core, three surfaces:

1. **Python library + CLI** — this package (`pip install hea-bench`).
2. **Zero-install browser app** — `web/index.html` (hosted at
   <https://dfieser.github.io/hea-bench/>; the page is the calculator).
3. **Native desktop app** — a single offline executable that wraps the
   browser app via Tauri.
4. **MCP server** — `pip install "hea-bench[mcp]"` then run
   `hea-bench-mcp` (stdio). Seven deterministic tools over this same
   library: `parse_composition`, batch `alloy_descriptors` /
   `alloy_rules`, `omega_sensitivity` (pair-table robustness check),
   `oxide_report`, `element_coverage`, `about`. Every response carries
   units, a citation key per value, and the library version. If you are
   an agent with MCP support, prefer those tools over reimplementing
   the formulas below; if not, the Python API is identical.

The browser/desktop core (`web/hea-calculator-core.js`) is a pure-JS
reimplementation of this library and is **parity-tested** against it on
every binary pair and the canonical multi-element fixtures
(`tests/test_web_parity.py`). The library core is composition-only and
**dependency-free**.

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

If you have a string rather than a dict, parse it first. The parser
accepts compact formulas (`"CoCrFeMnNi"`), subscripted formulas
(`"CuCoMn1.75NiFe0.25"`), and space-separated amounts.

```python
comp = hb.parse_formula("CoCrFeMnNi")   # dict-like Composition
hb.normalize(comp)                      # explicit mole-fraction dict
hb.smix(comp)                           # descriptors accept it directly
```

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
| Guo-Liu VEC | `guo_vec.predict(comp)` | `"FCC"` / `"BCC"` / `"mixed"` | fixed bounds 8.0 / 6.87 |
| King `Phi` | `king_phi.predict(comp, temperature_policy=None, threshold=1.0)` | `"solid_solution"` / `"intermetallic"` | defaults to `T = Tm` |
| Ye `phi` | `ye_phi.predict(comp, threshold=20.0)` | `"solid_solution"` / `"intermetallic"` | default 20.0 |
| Senkov-Miracle κ | `senkov_kappa.predict(comp, temperature=None)` | dataclass: `.verdict`, `.k1`, `.k1_cr`, `.g_ss_kj`, `.g_im_kj` | defaults to `T = Tm`; k₂ = 0.6 |
| Tsai σ window | `tsai_sigma.predict(comp)` | dataclass: `.verdict` in `sigma_prone` / `sigma_unlikely` / `not_applicable` | fixed 6.88-7.84, needs Cr/V |
| Sheikh ductility | `sheikh_ductility.predict(comp)` | dataclass: `.verdict` in `ductile` / `brittle` / `borderline` | fixed 4.5 / 4.6 |

The three v2.1 rules return small frozen dataclasses (not bare
strings) because their verdicts carry context (temperature, window
membership); use `.verdict` for the string.

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

## Command line

```bash
hea-bench --version
```

The CLI is a thin version/help wrapper; the Python API above is the
documented surface.

## Data layout

- `src/hea_bench/descriptors/data/` — the vendored element table (55
  elements: radius, melting point, VEC, Pauling electronegativity), the
  matminer-derived Miedema pair-enthalpy table (`pair_enthalpies.tsv`,
  75 elements), and the Miedema elemental-parameter table
  (`miedema_parameters.csv`). These are shipped inside the wheel; no
  fetch step is needed.
- `web/hea-calculator-core.js` — the JS port of the same math + tables,
  used by the browser and desktop apps.

The browser/desktop apps additionally compute the **Miedema
formation-enthalpy decompositions** (compound / solid-solution /
amorphous, split into chemical / elastic / structural / topological
terms) in page-side code; the Python library currently exposes the
descriptor + rule surface above.

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

## Phase-prediction benchmark (repo-only, experimental)

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

**The corpus is not shipped and this surface only works from a repo
checkout** (or with `HEA_BENCH_BENCHMARK_DIR` pointing at a built
corpus). The largest source dataset (Peivaste) declares no license, so
the repo carries a loader, a pinned SHA-256, and a fetch script instead
of that data, and the derived corpus inherits the restriction. Build
once:

```bash
python data/raw/peivaste/fetch.py
python -m hea_bench.benchmark.consolidate
```

The split fold assignments are frozen: each carries a SHA-256 digest
pinned in `tests/test_benchmark_corpus.py`. **Do not update those
digests to make a test pass** — a moved digest means the benchmark
changed and needs a new corpus version, not a silenced test. Licensing
per source: `data/raw/README.md`.

## Corpus API (repo-only, like the benchmark)

`hea_bench.corpus.load_corpus(version="0.1.0")` returns the full
consolidated corpus (7,783 rows in v0.1.0, including the 100
conflict-quarantined ones) with per-source provenance on every row:
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
