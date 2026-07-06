# Changelog

All notable changes to `hea-bench` are recorded here. Numbering follows
[Semantic Versioning](https://semver.org/). Each release section pairs
the version label with the date and links to the corresponding Zenodo
DOI for the archived snapshot.

The format is loosely based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [2.0.3] — 2026-07-06

### Fixed

- Release tooling. `tools/version.py --set` now refuses a missing version or an
  unknown flag and re-verifies the whole tree after stamping, so a drifted
  pattern fails loudly instead of leaving a silent partial bump. The Rust
  lockfile (`src-tauri/Cargo.lock`) is now version-synced and drift-checked
  like the other surfaces, and the drift-check additionally verifies that the
  two release-date fields agree and that the `.zenodo.json` author list matches
  `CITATION.cff`.
- Release pipeline. The GitHub Release, and therefore the Zenodo DOI, now
  depends only on the PyPI publish, so a transient MCP-registry failure can no
  longer strand a published version without its archival DOI. The desktop
  executable now builds in parallel rather than behind the other jobs, a manual
  run from a branch ref fails fast instead of deriving a bogus version, and an
  empty changelog section can no longer publish a release with empty notes.

No functional or numerical change to any descriptor or rule.

## [2.0.2] — 2026-07-06

### Changed

- Release engineering: the version now lives in a single place
  (`__version__` in `hea_bench/__init__.py`). Every other surface either
  derives from it (`pyproject.toml` via hatchling, the desktop bundle via
  `Cargo.toml`, the CLI/MCP/tests via import) or is stamped from it by the
  new `tools/version.py`, whose `--check` mode runs in CI and fails the
  build on any drift.
- Releases are now a single hands-off, tag-driven pipeline: a `vX.Y.Z` tag
  runs the tests, publishes to PyPI over OIDC trusted publishing (no token),
  publishes to the MCP registry, creates the GitHub Release that archives to
  Zenodo, and builds the desktop executable. See `RELEASING.md`.
- Citation metadata now records only the concept DOI, which always resolves
  to the latest release, and a `.zenodo.json` pins the complete author list
  for every archived version.

## [2.0.1] — 2026-06-14

### Changed

- Web front end consolidated into a single file: the landing page and the
  calculator now live in `web/index.html` and switch by URL hash, so the
  hosted site and the desktop app load the same one file.
- The desktop app ships as a single portable `HEA-Bench.exe` with no
  installer. CI rebuilds it on every page change and attaches it to the
  latest release.

### Added

- Legal and accessibility information on the landing page (disclaimer,
  privacy, a WCAG 2.1 AA accessibility statement, license) and a
  keyboard-accessible home control.
- Model Context Protocol registry metadata: a `server.json` and an
  `mcp-name` marker in the README for listing as
  `io.github.dfieser/hea-bench`.

## [2.0.0] — 2026-06-12 — first full public release

First full public release. Consolidates the alloy and oxide descriptors,
the six empirical rules, the four delivery surfaces (Python library and
command line, zero-install browser app, offline desktop app, and the
`hea-bench-mcp` agent server), the dual-implementation parity lock, and
the literature anchors into one citable version. No API breaks relative
to 1.8.0; the major bump marks the v1-to-v2 line and the first archived
public release of the full feature set.

### Fixed

- **MCP server emitted invalid JSON when King Phi diverges.** For a
  composition with no competing binary intermetallic (every Miedema pair
  enthalpy non-negative, e.g. the refractory HEA HfNbTaTiZr) the King Phi
  proxy is `+inf`, and `alloy_rules` / `alloy_descriptors` serialized it
  as the bare `Infinity` token, which strict MCP clients reject. The
  magnitude is now reported as `null` with a warning, and the verdict
  (which does not depend on the finite magnitude) is unchanged. The
  Python `phi_king` API still returns `math.inf`; only the JSON boundary
  is sanitized (`tests/test_mcp_server.py`).

### Added

- **Yang-Zhang (2012) Table 1 literature anchors** pinned as regression
  tests (`tests/test_yang_zhang_anchors.py`): the Miedema mixing
  enthalpies reproduce the published values to their printed precision.

## [1.8.0] — 2026-06-11 — agent surface (MCP server)

### Added

- **`hea-bench-mcp`, a Model Context Protocol server** (`hea_bench.mcp_server`,
  optional extra `pip install hea-bench[mcp]`), exposing the calculator to
  LLM agents as seven deterministic tools: `parse_composition`,
  `alloy_descriptors` and `alloy_rules` (batch over composition lists),
  `omega_sensitivity` (per-pair Miedema contributions and the Omega range
  under a pair-table perturbation, pinned against the near-ideal alloy
  Co20Cu20Fe5Mn35Ni20), `oxide_report` (all four families),
  `element_coverage`, and `about`. Every response carries units, the
  citation key of each parametrization, and the library version, so agent
  reasoning traces contain auditable receipts rather than bare floats.
  The tool bodies are plain functions tested in CI without the optional
  dependency (`tests/test_mcp_server.py`, 15 tests); the calculator core
  remains dependency-free.

## [1.7.0] — 2026-06-11 — landing page, named pages, redesigned docs

### Added

- **Project landing page.** `web/index.html` is now a real product page —
  hero, the three surfaces, what the tool computes, the reproducibility
  pillars, and a citation block — and is what GitHub Pages serves at the
  site root. It launches the calculator and honors the calculator's saved
  theme.
- **View deep links.** `calculator.html#theory`, `#equations`, `#refs`
  (and any theory section id such as `#sec-perovskite`) open the matching
  view directly, so the landing page and external docs can link straight
  into the app.

### Changed

- **The calculator has a name.** The app moved from `web/index.html` to
  `web/calculator.html`; the desktop app loads it directly via the window
  `url` in `tauri.conf.json`. Proper page titles and a vector favicon on
  both pages, and the stale "saved from" artifact comment is gone.
- **References view redesigned.** The flat footer-styled list is now a
  grouped bibliography (foundations of the field, descriptors and rules,
  the Miedema model, high-entropy oxides, methods and applications) in the
  same documentation shell as the Theory view, with a sticky section nav,
  scroll-spy, hanging-indent entries, and DOI links. The license,
  third-party, and privacy notices became an "About this software"
  section.
- **Equation reference grouped.** The card grid is split into alloy
  descriptors, Miedema formation enthalpies, and oxide descriptors, each
  with a numbered section header; the filter hides empty groups. The view
  header matches the docs shell.
- **Versions.** Library, browser page, desktop bundle, and CITATION.cff
  all move to 1.7.0 together. PyPI metadata updated (oxides in the
  description and keywords, status Production/Stable, homepage now the
  hosted landing page).

## [1.6.1] — 2026-06-10 — usability and onboarding pass

### Added

- **Welcome quick-start.** The calculator's empty state is now a proper
  landing view: a one-line description of the tool and one-click starts
  (load the alloy example, load the (MgCoNiCuZn)O oxide example, open the
  Theory tab), plus a shortcut hint. The Oxides mode empty state gains its
  own one-click literature example.
- **Manual theme toggle** in the title bar cycling auto → light → dark
  (persisted; auto follows the OS preference as before).
- **What's-new panel.** The version badge now opens a popover listing the
  release history.
- **Click-to-copy result cards.** Clicking any numeric descriptor, rule,
  Miedema, or oxide card copies its value, with a brief "copied" mark.
- **Plain-language tooltips** on every descriptor, rule, Miedema, and oxide
  card explaining what the quantity is and the threshold that applies.
- **Ctrl+Enter (Cmd+Enter)** calculates from anywhere in the page, in
  whichever mode is active.
- **Oxide theory, equations, and references.** The Theory tab gains four
  sections covering the oxide module (sublattice configurational entropy,
  oxidation-state assignment and Shannon radii, the Goldschmidt/Bartel
  perovskite factors, and the fluorite/pyrochlore criteria), the Equation
  reference gains the corresponding eight closed-form cards, and the
  References tab gains the nine oxide primary sources.

### Changed

- **One version number across all surfaces.** The desktop bundle
  (`tauri.conf.json`, `src-tauri/Cargo.toml`) and `CITATION.cff` now carry
  the library version instead of an independent 0.1.0, so the Python
  package, the browser page, the desktop executable, and the citation
  metadata all report the same release.
- Examples refreshed: the Cantor walkthrough no longer dates itself by
  internal version numbers and now includes the electronegativity
  descriptors; a new `02_oxides_walkthrough` notebook covers the oxide
  module on its literature anchors (J14, Jiang 2018 perovskites, the
  Spiridigliozzi fluorite samples with their published SDs, the pyrochlore
  window, and oxidation-state overrides).

## [1.6.0] — 2026-06-10 — high-entropy-oxide support on every surface

### Added

- **Oxides mode in the browser/desktop calculator.** A mode switch in the
  input rail toggles between Alloys and Oxides. The Oxides mode covers the
  same four structure families as the Python module via a family selector,
  free-text per-site cation inputs (formula syntax, any amount scale), an
  oxygen-content field for fluorites, a high/low-spin toggle, and five
  literature example presets (Rost J14, Jiang 2018, the two Spiridigliozzi
  F-ESO samples, a rare-earth zirconate pyrochlore). Results show the
  solved oxidation states and Shannon radii per site, the descriptor
  cards, the formability screens with their windows, and a copy-as-JSON
  button. The JS core port (`describeRockSalt`, `describePerovskite`,
  `describeFluorite`, `describePyrochlore` + the oxidation-state solver
  and Shannon lookup) is parity-tested against the Python implementation
  on 16 curated fixtures, including exact warning-string agreement
  (`tests/test_web_oxides_parity.py`); the 94-element oxide table is
  generated into the core by `tests/data/_sync_js_oxide_tables.py`.
- **Enter-to-calculate** in the alloy composition table, the King
  temperature field, and all oxide inputs.
- **High-entropy-oxide descriptor module (`hea_bench.oxides`), Python surface.**
  First increment of the oxide expansion: closed-form HEO descriptors and
  empirical formability screens for four structure families via
  `describe_rock_salt`, `describe_perovskite`, `describe_fluorite`, and
  `describe_pyrochlore` (spinel deferred). Computes per-sublattice
  configurational entropy (formula / per-cation / per-site conventions),
  Shannon-radius size disorder per sublattice, Goldschmidt `t`, octahedral
  factor `mu`, Bartel `tau` (< 4.18 rule), the Spiridigliozzi fluorite
  radius-dispersion criterion (sigma > 0.095 Å, eight-fold radii, sample SD —
  reproduces the published SDs of the F-ESO samples exactly), the
  Subramanian pyrochlore radius-ratio window, and cation electronegativity
  statistics. A deterministic charge-neutrality solver assigns oxidation
  states (common states first, charge-uniform sublattices preferred,
  explicit override supported); Shannon radii resolve by oxidation state,
  coordination number, and spin (high-spin default, low-spin toggle), with
  documented nearest-CN fallback warnings. Data vendored from pymatgen's
  digitization of Shannon 1976 (MIT, 94 elements, provenance + SHA pinned
  in `src/hea_bench/oxides/data/README.md`). 19 new tests pin literature
  anchors (Rost J14, Jiang 2018 perovskites, Spiridigliozzi F-ESO,
  zirconate pyrochlore). The alloy surface and the browser/desktop apps are
  untouched; the JS port and calculator Oxides mode are the next increment.

## [1.5.0] — 2026-06-10 — electronegativity descriptors; full-coverage Miedema panel

### Added

- **Electronegativity descriptors on every surface.** `delta_chi` (Pauling
  electronegativity mismatch) and `mean_electronegativity`, present in the
  Python library since v1.3 but never exported at the top level or ported to
  the calculator, are now top-level Python exports, computed by the JS core
  (`deltaChi`, `meanElectronegativity`), shown as result cards, included in
  the saved-results table and CSV export, documented in the Equations view,
  and covered by the Python↔JS parity test on all 676 fixtures. The synced
  element table now carries the Pauling values; custom elements accept an
  optional electronegativity and degrade with a warning when it is absent.
- **Miedema formation-enthalpy panel extended 24 → 37 elements.** The
  page-side `MIEDEMA_PARAMS` and `ELEMENT_EXTENDED` tables now cover every
  element the calculator supports (adds Au, Be, Ca, Ce, Gd, In, La, Li, Mg,
  Re, Sc, Sn, Zn), sourced from the vendored matminer Miedema parameter
  table (the de Boer 1988 parametrization, BSD-3). The compound,
  solid-solution, and amorphous decompositions now compute for all 666
  binary pairs instead of skipping alloys containing the 13 missing
  elements.

### Changed

- **Per-element hybridization factors aligned with the source table.** The
  R correction in the formation-enthalpy panel previously used factor 1.0
  for every element except Al and Si. It now uses the per-element factors
  from the vendored parameter table (Cu/Ag/Au 0.3, Sc/Y/La/Ce/Gd 0.7,
  Zn 1.4, In 1.9, Sn 2.1, Be/Mg/Ca 0.4, Li 0.0), which slightly changes
  the panel's decomposition values for alloys pairing Cu, Ag, or Y with Al
  or Si. The parity-tested descriptors and rules are unaffected.

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
interpretable **descriptor calculator** (the research-software direction). The
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
