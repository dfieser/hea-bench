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

## [Unreleased] — v1.1

`v1.1-phi` branch, scheduled to merge into `main` and tag as `v1.1.0`.

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
