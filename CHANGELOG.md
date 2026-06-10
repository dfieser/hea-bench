# Changelog

All notable changes to `hea-bench` are recorded here. Numbering follows
[Semantic Versioning](https://semver.org/). Each release section pairs
the version label with the date and links to the corresponding Zenodo
DOI for the archived snapshot.

The format is loosely based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.4.0] — 2026-06-10 — 37-element coverage on every surface

### Added

- **Calculator coverage 30 → 37 elements everywhere.** The JS core's element
  and pair tables are now generated from the Python library by
  `tests/data/_sync_js_tables.py` (Be, Ca, Ce, Gd, In, La, Sc join the
  browser/desktop surfaces; the pair table grows 435 → 666 entries). The
  parity fixture regenerated to 676 cases (666 exhaustive binaries + 10
  curated multis); the Python↔JS parity test passes.
- **Ω near-zero-enthalpy warning** in the calculator page: when
  |ΔH_mix| < 2 kJ/mol the result panel warns that Ω diverges and its
  magnitude is pair-table-sensitive (the Ω > 1.1 verdict remains robust).

### Fixed

- **Stale 24-element page table.** `web/index.html` carried its own
  pre-v1.2 24-element copy of `ELEMENT_DATA` and passed it into the core,
  silently limiting the live calculator to 24 elements (Au, Li, Mg, Re,
  Sn, Zn never reached the UI). The page now derives its table from the
  parity-tested core export, so the dropdowns, formula parser, and
  calculations always match the core. Elements without page-side Miedema
  decomposition parameters degrade gracefully (warning + panel skip), as
  before.

## [Unreleased] — V2: descriptor-calculator repackaging

Refocused the project from a phase-prediction *benchmark* to an open,
interpretable **descriptor calculator** (the SoftwareX direction). The
calculation core is unchanged; the Python↔JS parity test still passes.

### Added

- **Native desktop app** (`src-tauri/`): a Tauri wrapper that bundles the
  browser calculator into a single offline executable.
- **Redesigned calculator UI** (`web/index.html`): a desktop app shell —
  title bar with Calculator / Theory / Equations / References tabs, a
  two-pane workspace (input rail + results), a draggable rail divider, a
  results empty state, a documentation-style Theory view with a sticky
  section nav, and a filterable equation reference.

### Changed

- Corrected the stale "Implementation note" in the theory section that
  claimed a non-existent factor-of-4 bug in ΔH_mix. The multi-component
  sum applies the factor of 4 exactly once over equiatomic pair values;
  replaced with an accurate provenance + Ω-singularity note (Ω is
  parametrization-sensitive as ΔH_mix → 0; sources disagree most on Mn).
- Package description, README, AGENTS.md, llms.txt, and CITATION refocused
  on the descriptor-calculator tool and its three surfaces.

### Removed

- **Phase-prediction benchmark subsystem moved out of the public repo**
  (recoverable; archived for later reintegration): the `benchmark/`,
  `classifiers/`, and `evaluation/` packages, `evaluate.py`, the
  consolidated/raw datasets under `data/`, the benchmark loader/evaluation
  tests, the benchmark example notebook, and `docs/v1.1-phi-spec.md`. The
  descriptor + rule library and the parity-tested calculator are unchanged.
- Dropped the now-unused `[data]` (pandas) and `[plot]` (matplotlib)
  optional-dependency extras; the calculator core remains dependency-free.

## [1.3.0] — browser parity at 30 elements (prior benchmark line)

`v1.3-baseline` branch, stacked on `v1.2-coverage`. Targets tag `v1.3.0`.

### Added

- **Browser calculator extended to 30 elements** to match the v1.2
  Python table (`ELEMENTAL_DATA`). The JS core (`web/hea-calculator-
  core.js`) and Python source-of-truth (`hea_bench.descriptors.
  browser_compat`) now both carry Au, Li, Mg, Re, Sn, and Zn in the
  Miedema parameter set, the volume-mismatch coefficient table, and
  the vendored binary pair-enthalpy table (159 new pairs). The parity
  fixture expanded from 286 to 445 cases (every C(30, 2) binary plus
  the 10 curated multi-element compositions); the byte-for-byte
  Python/JS parity test continues to pass at `rtol=5e-4`.
- **Pauling electronegativity** added to `ElementProperties`
  (`electronegativity` field) for all 37 covered elements, sourced from
  the WebElements consistent set (Pauling 1960; reproduced in the CRC
  Handbook, Haynes 2016). New `hea_bench.descriptors.electronegativity`
  module exports `delta_chi` (electronegativity mismatch, the
  composition-weighted standard deviation) and `mean_electronegativity`,
  available as general HEA descriptors.

### Changed

- **Unified the calculator's `Hmix` / `Omega` on the vendored
  pair-enthalpy table.** The browser calculator and `tests/
  test_web_parity.py` previously displayed a separate live-Miedema
  estimate for `Hmix` / `Omega` while the phi-family rules used the
  vendored pair table. Both now derive from the single pair-table
  path (`hea_bench.mixing_enthalpy` / `hea_bench.omega`), so every
  descriptor on the page is internally consistent and matches the
  Python library.

### Removed

- **Legacy live-Miedema descriptor path.** Removed the
  `hea_bench.descriptors.browser_compat` module (and its
  `browser_mixing_enthalpy` / `browser_omega` exports), the
  `browser*` helpers and `BROWSER_MIEDEMA_*` tables in
  `web/hea-calculator-core.js`, and the corresponding dead code in
  `web/index.html`. The extended Miedema formation-enthalpy panel
  (compound / solid-solution / amorphous decompositions) is unchanged.

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
