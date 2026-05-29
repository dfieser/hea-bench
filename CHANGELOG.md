# Changelog

All notable changes to `hea-bench` are recorded here. Numbering follows
[Semantic Versioning](https://semver.org/). Each release section pairs
the version label with the date and links to the corresponding Zenodo
DOI for the archived snapshot. The benchmark CSV ships under its own
data-versioning track (`data/consolidated/<version>/`); a benchmark
data version may move independently of the library version when the
library gains features that do not change the underlying dataset.

The format is loosely based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased] — v1.3.0

`v1.3-baseline` branch, stacked on `v1.2-coverage`. Targets tag `v1.3.0`.

### Added

- **Learned reference baseline** (`hea_bench.baselines`):
  `LogisticBaseline`, a logistic regression on the six descriptors with
  an optional squared + pairwise-interaction expansion
  (`interactions=True`), plus `descriptor_vector`, `load_features`, and
  `evaluate` for held-out k-fold scoring under the same stratified
  protocol used for the rules. This is the quantitative floor a new
  phase-prediction method should beat.
  - Headline result on single-vs-multi: a linear model ties the best
    textbook rule (held-out Youden's J 0.092), but adding interactions
    roughly triples it (J 0.313, accuracy 66%) — the descriptors carry
    joint signal the single-threshold rules cannot reach.
  - numpy is the only new dependency: lazily imported and gated behind a
    new optional `[ml]` extra, so the core stays dependency-free
    (`import hea_bench` needs no numpy).
- 5 regression tests (`tests/test_learned_baseline.py`) pinning the
  held-out numbers; skipped when numpy or the v0.1.0 CSV is absent.

## [1.2.0] — elemental coverage 24 → 30 (complete; release on hold)

`v1.2-coverage` branch, stacked on `v1.1-phi`.

### Changed

- **Elemental coverage expanded 24 → 30 elements.** Added Mg, Zn, Sn,
  Re, Au, Li to `ELEMENTAL_DATA` with cross-verified Goldschmidt
  12-coordinate metallic radii, CRC melting points, and s+d /
  group-number valences. Scorable coverage of the consolidated
  benchmark rose from 86.7% (6,750 alloys) to 90.2% (7,021 alloys);
  the binary scored set grew 6,651 → 6,922. The consolidated CSV is
  unchanged — only `coverage_report.json`, `rule_baselines.json`, and
  `rule_baselines_v1.1.json` were regenerated.
- **Boron and carbon deliberately excluded.** Boron is a metalloid
  with no metallic radius; carbon has no 1-atm melting point (it
  sublimes) and no metallic radius. Adding either would mix radius
  conventions in the δ calculation and, for carbon, require inventing
  a rule-of-mixtures melting temperature. Even adding both would only
  reach ~91.5% coverage.
- **All headline numbers re-pinned** to the 30-element table: Zhang δ
  accuracy 57.1% (Youden's J 0.094), Yang Ω 54.2% (J 0.036), Guo–Liu
  VEC 67.4% on 3,556 single-phase alloys, King Φ 48.9%, Ye φ 49.1%.
  Held-out CV and sub-benchmark numbers re-pinned to match. The
  qualitative findings are unchanged.
- **Intermetallic sub-benchmark strengthened**: Ye φ Youden's J rose
  to +0.19 (from +0.17) on the wider scorable set (5,685 scorable, up
  from 5,481).
- Package `__version__` → `1.2.0`.

### Added

- Per-element pinned-value tests for the six v1.2 additions
  (`test_table_has_30_elements`, `test_v12_additions_present_bc_absent`,
  `test_v12_added_element_values_pinned`). Test count 234 → 236, ruff
  clean.

## [1.1.0] — phi family (unreleased)

`v1.1-phi` branch, the phi-family + held-out increment that v1.2.0
builds on.

### Added

- **Phi-family descriptors**: `s_excess` (Mansoori hard-sphere excess
  entropy), `delta_g_ss` (Gibbs energy of the disordered solid
  solution at a chosen temperature), `delta_g_max` (most-negative
  Miedema pair enthalpy across binaries), `phi_king` (King 2016
  capital Φ), and `phi_ye` (Ye 2015 lowercase φ).
- **Phi-family rules**: `rules.king_phi` (Φ > 1.0 → solid_solution)
  and `rules.ye_phi` (φ > 20.0 → solid_solution). Both return native
  `solid_solution` / `intermetallic` strings; the evaluator collapses
  `intermetallic` to `multi-phase` when scoring against the main
  benchmark's coarse four-class taxonomy.
- **Held-out cross-validation protocol** in `hea_bench.evaluation`:
  stratified 5-fold CV by phase × source, with per-fold thresholds
  tuned by argmax Youden's J on the training portion of each fold and
  scored on the held-out portion. Includes a documented 70/30 single-
  split mode for quick reproduction.
- **Conflict-row double scoring** (`any-match` and `all-match`) on the
  ~100 cross-source disagreement rows, so the gap between the most-
  optimistic and most-pessimistic conflict-handling interpretations
  is reportable.
- **Intermetallic-aware sub-benchmark** that projects Peivaste's
  12-class side-channel label to `solid_solution` /
  `intermetallic`, excluding amorphous-containing labels. 5,930
  compositions with usable ground truth, 5,481 scorable.
- **JS calculator parity** infrastructure: `web/hea-calculator-core.js`
  extracted as a UMD module, regression-checked against Python by
  `tests/test_web_parity.py` over 286 fixture compositions covering
  every binary pair in the 24-element table.
- **AI-agent jumpstart** in `AGENTS.md` and a top-level `llms.txt`
  for AI discoverability.
- New tests: 234 total (up from 157 at v0.1.0), ruff clean.

### Changed

- `delta_g_max` now uses the raw most-negative Miedema pair enthalpy,
  documented as an approximation of King 2016's per-binary
  intermetallic Gibbs energy. The earlier draft used a composition-
  weighted contribution and produced Φ values an order of magnitude
  too large.
- King Φ default temperature is the rule-of-mixtures melting
  temperature, matching King 2016 page 174. A `temperature_policy=`
  keyword exposes the override.
- King and Ye rule comparators are strict `>` to match the published
  inequalities and the existing `yang_omega.predict` style.
- The Cantor sanity values that ship with the regression suite were
  updated to reflect the corrections above. The 4-decimal canonical
  values are now `delta_g_max = -8.000`, `phi_king = 3.533`,
  `phi_ye = 34.822`.

### Fixed

- Stale "future descriptor" framing in the supplementary information.
  Section S10 (King Φ) is now a shipped-descriptor specification
  rather than a planned-feature placeholder.

## [0.1.0] — 2026-05-22

Initial release.
[Zenodo](https://doi.org/10.5281/zenodo.20346288).

### Added

- **Six descriptors** for the four textbook screening rules:
  `smix`, `delta`, `vec`, `melting_temperature`, `mixing_enthalpy`,
  `omega`. All composition-only, dependency-free.
- **Four textbook rules** wrapped as binary or multiclass classifiers:
  Yeh ΔS_mix (HEA / MEA / dilute), Zhang δ < 6.5%, Guo–Liu VEC, and
  Yang–Zhang Ω > 1.1.
- **Consolidated benchmark** v0.1.0 with 7,784 unique compositions,
  merged from Borg 2020, Pei 2020, and Peivaste, with per-row source
  provenance and an explicit cross-source-conflict flag for 100
  disagreement rows.
- **Diagnostic-statistics framework** (accuracy, sensitivity,
  specificity, Wilson 95% CI, Youden's J, confusion matrix) and a
  threshold-sweep ROC routine.
- **Self-contained HTML calculator** at
  <https://dfieser.github.io/hea-bench/> implementing the same
  descriptors and rules in client-side JavaScript.
- **CLI** (`python -m hea_bench.evaluate`, `python -m
  hea_bench.benchmark.coverage`) and PyPI distribution.
- 157 tests, all passing on Python 3.10–3.12.
