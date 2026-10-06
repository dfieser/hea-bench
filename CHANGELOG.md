# Changelog

All notable changes to `hea-bench` are recorded here. Numbering follows
[Semantic Versioning](https://semver.org/). Each release section pairs
the version label with the date and links to the corresponding Zenodo
DOI for the archived snapshot.

The format is loosely based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- **Every feature is now in all four parts**: the Python package, the
  MCP server, the website and the desktop app. A person only needs to
  pick one of them. This is a standing project rule from now on, and CI
  enforces it (see the last item below).
- **The MCP server has every feature of the package: 24 tools, up from
  13.** New tools: `ceramic_report`, `element_data`, `corpus_build`,
  `corpus_export`, `measured_properties`, `predict_phase_set`,
  `benchmark_summary`, `benchmark_run`, `benchmark_folds`,
  `benchmark_score` and `coverage_study`. `alloy_descriptors` now
  returns the Miedema formation enthalpies, and `alloy_descriptors`,
  `alloy_rules` and `omega_sensitivity` accept custom elements and pair
  enthalpies. `campaign_suggest` also accepts a campaign inline. The
  server moves to the official MCP Python SDK 2.x (`mcp>=2.3,<3`), and
  the `mcp` extra now includes scikit-learn, so hardness, phase sets and
  campaigns work from a registry install.
- **The dataset works from a plain pip install.** The wheel ships the
  openly licensed source datasets, and `hea_bench.corpus.build_corpus()`
  downloads the one file that declares no license (Peivaste), checks its
  SHA-256 and builds every corpus version in a per-user folder. The MCP
  `corpus_build` tool does the same.
- **Library functions for what only the apps had:**
  `hea_bench.custom_data()` (your own elements and pair enthalpies, for
  any descriptor or rule), `hea_bench.omega_sensitivity()`,
  `hea_bench.descriptors.miedema_decomposition` and
  `hea_bench.descriptors.elements.element_data()`.
- `pip install "hea-bench[all]"` installs everything. Python 3.13 and
  3.14 are now tested and declared.
- New checks that keep the four parts equal.
  `tests/test_feature_parity.py` (formerly `test_app_parity.py`) fails CI
  unless every feature has its library function, its MCP tool, a working
  app surface and tests. The CI `package` job builds the wheel, installs
  it fresh and calls every MCP tool over stdio
  (`tests/test_installed_package.py`, also run by the pre-push
  preflight). The release `desktop-build` job uses every tab inside the
  built exe before attaching it (`tests/test_desktop_smoke.py`). The
  preflight also checks that the MCP container image receives every file
  the wheel bundles.

### Changed

- **The app is much smoother.** It keeps its fitted models (hardness,
  phase sets, the dataset check) in the browser between visits, so a
  returning visitor gets predictions about a second after the engine
  starts instead of waiting about 18 seconds for refits. The engine
  prepares models in the background while the page is idle, starts by
  itself for returning visitors, and long tables no longer stall tab
  switches.
- **The dataset opens on corpus v0.2.0, the largest (10,290 alloys)**,
  in `load_corpus()`, the app's Dataset tab and the MCP corpus tools.
  The benchmark, the phase predictions and the domain flag stay on the
  reference corpus v0.1.0, so every published number is unchanged.
- The in-app engine runs Pyodide 0.29.5 (was 0.29.3), the desktop app
  uses Tauri 2.12.1 (was 2.11.2) without the unused logging plugin, the
  MCP container image uses Python 3.13, and every GitHub Action is on
  its current major version.

### Fixed

- The data-file fingerprints the app shows now match the ones the
  library reports on every platform. They were computed from a Windows
  checkout's line endings; they now use the bytes git stores. The data
  itself is unchanged.

## [2.6.2] — 2026-10-06

### Added

- A browser test, `tests/test_app_smoke.py`, opens the built site in
  headless Chrome or Edge and uses every tab the way a person does: the
  calculator in its three modes, the predictions panel, the dataset, the
  benchmark (including an uploaded predictions file scored with the gap)
  and the design tab. It runs in the CI `web-engine` job, so a broken tab
  now blocks a release, and `tests/test_app_parity.py` fails when a
  feature that uses the engine has no step in it.

### Fixed

- A returning visitor no longer sees numbers for a different alloy. The
  calculator restored the last inputs but showed leftover example
  results beside them until Calculate was pressed. It now shows the
  welcome screen until then.

### Changed

- The site and the desktop app are lighter. `index.html` drops about
  150 KB of styles left over from a saved copy of the page, none of which
  matched anything on it, and `web/mathjax/` drops 14 MB of bundles the
  page never loads. Equations, the MathJax menu, its SVG renderer and its
  accessibility tools work as before.

## [2.6.1] — 2026-10-06

### Fixed

- The `interop` extra now pins HEACalculator to the 2.0 series
  (`~=2.0.1`), the one the comparison in `docs/backend-agreement.md` was
  made with. Their 2.1.0 and 2.2.0 changed the reference data, and the
  looser pin let them into the release checks, which stopped 2.6.0
  before it reached PyPI, the MCP registry and GitHub Releases. 2.6.1 is
  the first 2.6 release there, and it contains everything listed under
  2.6.0.

## [2.6.0] — 2026-10-06

### Added

- **Every library feature now works in the app**, on the website and in
  the desktop exe, for people who never write code. New tabs:
  **Dataset** (the consolidated corpus with every source's label and
  paper, filters, paging, CSV download, and the measured hardness and
  density records), **Design** (composition search with property
  limits, rule filters and the Pareto front, and experiment planning
  from your own measurements with save and reopen) and **Benchmark**
  (the frozen random and family-grouped splits with their digests,
  live baseline reruns, scoring of uploaded predictions with the gap,
  an example predictions file, and the coverage study). The Calculator
  gains a Properties and predictions panel (density and raw-material
  cost instantly, hardness with its conformal interval, the conformal
  phase prediction sets and the domain flag), a check of how far Ω
  moves under the spread between published pair tables, and a
  Ceramics mode for carbides, nitrides and diborides.
- The app runs the `hea_bench` package itself, unchanged, inside the
  page (Pyodide 0.29.3 in a Web Worker, `web/hea-engine-worker.js`),
  with the built corpus kept in browser storage. The engine bundle is
  assembled at deploy time by `tools/build_web_engine.py` with every
  file SHA-256 pinned, and `tests/test_web_engine.py` runs the shipped
  bundle under Node and checks that it returns what CPython returns.
  The new `hea_bench.webapp` module is the JSON bridge it calls.
- App parity is enforced: `tests/test_app_parity.py` maps every public
  name, MCP tool, phase rule and CLI command to its app surface in
  `tests/data/app_parity.json` and fails CI, with the exact fix, when
  one has none. The HEACalculator bridge is the one owner-deferred
  exception.
- `score_predictions` scores labels predicted outside the package on the
  frozen folds, `predict_property_batch` and `predict_hardness_batch`
  predict many compositions in one call, and the benchmark baselines,
  frozen digest table, coverage study and phase prediction sets moved
  from `tools/` scripts into `hea_bench.benchmark.baselines`,
  `hea_bench.benchmark.frozen`, `hea_bench.uncertainty.coverage` and
  `hea_bench.uncertainty.phase`, so the app, the tests and CI share one
  implementation. The published numbers reproduce exactly.
- CI gains a `web-engine` job that builds the corpus and the engine
  bundle and runs the engine, bridge and parity suites with skips
  turned into failures. The site deploy and the desktop build assemble
  the engine, and the release check now also requires the live engine
  to report the released version.

### Changed

- The calculator stacks its input panel above the results on phones and
  narrow windows instead of squeezing the results into a sliver.
- The landing page lists what each tab does and no longer claims the
  app has no fitted model or that the exe is 14 MB (the exe now carries
  the engine).

### Fixed

- Experiment-planning campaigns ignored `PropertyConstraint` limits.
  They now apply them to the candidate pool exactly as `search()` does.

## [2.5.6] — 2026-08-25

### Changed

- The landing hero now leads with the claim that distinguishes the tool
  rather than an abstract. The headline sets at a scale that lands in two
  lines instead of three, and the 88-word opening paragraph is cut to one
  sentence. Everything the paragraph said about descriptors, phase rules,
  oxide screens and receipts is already stated, in more detail, in the
  sections below it, so nothing was lost by cutting rather than moving it.

## [2.5.5] — 2026-08-24

### Changed

- Document every MCP tool parameter, and add the container and Glama manifests

## [2.5.4] — 2026-08-23

### Fixed

- `hea-bench-mcp` could not start. The `mcp` extra declared an
  unbounded `mcp>=1.2`, so a fresh `uvx --from hea-bench[mcp]
  hea-bench-mcp` resolved the MCP SDK to 2.0.0, which removed the
  `mcp.server.fastmcp` module the server is built on, and the server
  exited claiming the `mcp` package was not installed. The extra now
  requires `mcp>=1.9.4,<2`. The floor also clears CVE-2025-53366 (HIGH)
  in SDKs older than 1.9.4, and the failure path now names the
  installed SDK version and the exact command that fixes it instead of
  telling the reader to install a package they already have.
- Registering the tools raised `TypeError: issubclass() arg 1 must be a
  class` on MCP SDKs that inspect parameter annotations directly, so no
  tool was ever served. `mcp_server.py` no longer uses
  `from __future__ import annotations`, which had stringized every tool
  signature. Two tests now build the real server and assert all
  thirteen tools register.

### Added

- Every MCP tool now carries `ToolAnnotations` (`readOnlyHint`,
  `destructiveHint`, `idempotentHint`, `openWorldHint`, and a title), so
  an agent can see from the manifest that these tools only read curated
  tables and never touch the network.

### Changed

- `verify-release` no longer waits for the desktop exe. It goes green
  once the `pypi`, `mcp` and `release` jobs succeed, so the `Auto
  release` run finishes in minutes rather than after a 15-20 minute
  Rust build. A new `desktop-failed` job in `release.yml` opens an
  issue labelled `desktop-build` that mentions and assigns the owner
  when `desktop-build` or `desktop-attach` fails, which GitHub delivers
  by email, and comments on the open issue instead of opening another.

## [2.5.3] — 2026-08-23

### Added

- README graphics: a banner and a screenshot of the browser calculator
  computing the Cantor alloy, each in a light and a dark cut served
  through `<picture>` so GitHub matches the reader's theme. PyPI strips
  `<source>` but keeps the `<img>`, so the light cut is the fallback
  there. A mermaid diagram of the path from composition to report
  replaces the claim that nothing is fitted with a picture of it.
- `tools/make_screenshots.py` re-captures those screenshots from the
  current `web/` sources with Playwright, so refreshing them is a
  command rather than a manual capture that nobody repeats.
- `tools/preflight.py` checks the README graphics exist and that every
  image URL in the README is absolute. `pyproject` uses this README as
  the PyPI long description, where a relative path renders broken.

### Changed

- The README's `tests: passing` badge was hard-coded and could not go
  red. It now points at the CI workflow. Added PyPI version and
  supported-Python badges.
- Questions and ideas now route to GitHub Discussions instead of the
  issue tracker, via a `.github/ISSUE_TEMPLATE/config.yml` that offers
  the Q&A, Ideas and Show-and-tell categories on the New Issue chooser.
  README and CONTRIBUTING follow the same split: issues for bugs and
  feature requests, Discussions for everything else.
- The maintainer contact in CONTRIBUTING is now the academic address
  already used in the Code of Conduct, so the two public contact points
  agree.
- Landing page design pass. The hero crystallite is drawn in the
  brand's own tones (ink, terracotta, oxblood, warm grey, and a ringed
  fifth species) instead of five categorical primaries, so it reads as
  the mark grown large rather than a chart dropped onto a document. The
  worked example is composed as one band: the composition set as a
  label in display size, Table 1 and Table 2 side by side from 1120px,
  both starting on the same line whatever their captions' length, and
  the Guo-Liu screen set on two lines on purpose. Figures (the
  crystallite and the worked example) may extend up to 120px into the
  right margin on wide screens; text never does.

### Fixed

- On Android Chrome the landing rendered at 733px on a 390px phone,
  with the title running off the right edge and the nav off-screen.
  The calculator underneath the overlay still lays out, its
  saved-results table escapes its scroll wrapper and widens the body,
  and mobile Chrome grows the layout viewport to fit, dragging the
  fixed overlay with it. The hidden app is now clipped while the
  landing shows; the rule stops applying the moment the app opens.
- The rules table on a phone now keeps one line per row and scrolls
  sideways instead of crushing the first column into three lines.
- The crystallite's growth entrance now plays when the figure is first
  scrolled into view, rather than silently at load while off-screen.

## [2.5.2] — 2026-08-18

### Added

- A crawlable favicon set for the web app: `favicon.ico` (16/32/48),
  `favicon.svg`, `apple-touch-icon.png`, PWA icons and a web manifest.
  The site previously declared its icon as a `data:` URI, which browsers
  render but Google cannot crawl, so search results carried no favicon.
  The 16 px frame drops the lattice's ring bonds and fattens the spokes,
  because the full mark averages to a smudge at that size.
- An Open Graph social card (`web/og-image.png`, 1200x630), so a link to
  the site renders with the mark, the tagline and the citation instead of
  bare text. Twitter card upgraded to `summary_large_image`.
- `tools/preflight.py` now checks the web assets the `<head>` promises:
  every icon exists at its declared size, the card is exactly 1200x630,
  the manifest and JSON-LD parse, and no icon is a `data:` URI or a
  root-absolute path. These fail silently in production otherwise.

## [2.5.1] — 2026-08-16

### Changed

- Shorten the MCP registry description to the 100-character limit

## [2.5.0] — 2026-08-16

### Added

- `hea_bench.ceramics`: the calculator extends to high-entropy
  rock-salt carbides and nitrides and AlB2-type diborides, following
  the oxides module's API shape. Reports carry the metal-sublattice
  configurational entropy in every published normalization convention
  (per mole cation, per formula unit, per mole atoms), because the
  ceramics literature switches between them without warning, and VEC
  per formula unit for the rock-salt classes with annotated literature
  reference points (the 8.4 hardness maximum, the roughly 9.4 fracture
  resistance and 9.5 plasticity marks) instead of a verdict, because
  no single published window exists. Deliberately absent, with reasons
  in `docs/ceramics.md`: a size-mismatch descriptor (the field derives
  it from DFT binary-cell bond lengths; adopting a cited
  composition-only table is future curation work), entropy-forming
  ability and DEED (DFT-ensemble quantities; no parity claimed
  anywhere), and a ceramics corpus or benchmark task (the available
  outcome data is too small to support one; a license audit of every
  candidate dataset is recorded for the future consolidation).
- The MCP surface grows from seven to thirteen tools, covering the
  whole workflow: `corpus_query` and `corpus_describe` (filtered slices
  of the provenance-tracked corpus, sample hard-capped at 50 rows),
  `predict_properties` (every property entry carries interval, tier,
  domain flag, novelty, and warnings at the top level of its payload),
  `check_applicability` (the novelty components), `design_search`
  (hard caps: 10 palette elements, step at least 0.05, 20 candidates,
  a fixed 50,000-point budget; oversized requests are refused with the
  cap named), and `campaign_suggest` (batch capped at 10, operating on
  a campaign file the user supplies and never writing it). Missing
  optional extras or missing local corpus data surface as a clear
  message naming the exact fix rather than a traceback, and `about()`
  now reports per-capability availability for the running environment.
- `hea_bench.design.campaign`: the active-learning loop. A `Campaign`
  holds an objective, palette, and constraints, accepts the user's own
  measurements (`observe`), and ranks the unexplored lattice by
  expected improvement or UCB over a seeded random-forest ensemble
  whose uncertainty is tree disagreement (documented as a
  model-disagreement band, not a coverage guarantee). Batches use the
  believer heuristic; hardness campaigns warm start from the Borg
  records matching the palette; state round-trips through versioned
  plain JSON on the user's disk with no accounts and no telemetry;
  and below 10 informative rows `suggest` raises `ColdStartError`
  because a near-random loop should refuse rather than pretend. A
  publication-year replay on the Al-Co-Cr-Fe-Ni hardness record is
  reported in `docs/campaign-replay.md`, honest outcome included.
- `hea_bench.design`: constrained composition search. `search()` walks
  a deterministic simplex lattice over a palette (element subsets times
  fixed-step compositions), filters by rule verdicts, property bounds
  (point or conservative interval end), per-element composition bounds,
  and a domain-of-applicability constraint that is ON by default, then
  returns a Pareto front where every candidate carries its complete
  receipt: descriptors, all nine rule verdicts, property predictions
  with intervals, novelty components, and the domain flag.
  `optimize_bound="lower"` ranks fitted objectives by the conservative
  interval end, the standard mitigation for optimizers exploiting model
  error. The lattice is exhaustive within a hard `max_evaluations`
  budget and refuses loudly rather than sampling silently; results
  record seed and settings and serialize to JSON. A retrospective
  recovery study over the Al-Co-Cr-Fe-Ni and Mo-Nb-Ta-V-W palettes
  (`docs/design-recovery.md`) reports where measured alloys sit
  relative to recovered fronts, including the misses. Limitation,
  framed throughout: this is a screening and prioritization aid whose
  fronts are only as good as the tier B surrogates under them.
- `hea_bench.properties`: property predictions in explicit tiers.
  Tier A closed forms (stdlib): `density` by rule of mixtures over a
  new cited IUPAC standard-atomic-weight table and the vendored molar
  volumes, validated against the 49 experimentally measured densities
  in the Borg deposit (mean absolute error 0.20 g/cm3, documented in
  `docs/property-tier-a.md`); `melting_temperature` re-exposed; and
  `cost_per_kg`, an explicitly indicative raw-material screening number
  mass-weighted over a date-stamped element price table whose every row
  carries its own basis, as-of date, and source (USGS MCS 2026, LME,
  bullion spot, named minor-metal relays), with `cost_breakdown()`
  exposing per-element contributions so the bases are never hidden.
  Tier B (`hardness`, new `properties` extra pinning scikit-learn
  1.7.2): a seeded random forest over the package's own descriptors on
  the 417 near-room-temperature Borg HV alloys, always returned with a
  family-grouped split conformal interval and a domain-of-applicability
  flag fitted on its own training data; `processing=` conditions on one
  processing route and refuses below a 50-alloy floor. The model card
  (`docs/property-hardness.md`) records the family-grouped CV error
  (mean absolute error 115 HV, empirical interval coverage 0.909 at
  nominal 90 percent, mean width 658 HV) and states plainly that this
  supports coarse screening, not ranking close candidates. Yield
  strength, moduli, ductility, and corrosion are deliberately not
  shipped; the card documents why (test-temperature and processing
  confounds, thin licensed data), because a confidently wrong number
  would be worse than an absent one.
- `hea_bench.uncertainty`: the trust layer. Standard-library split
  conformal prediction (`ConformalClassifier`, `ConformalRegressor`)
  wraps any fitted sklearn-style model with prediction sets or
  intervals carrying the distribution-free finite-sample coverage
  guarantee, including honest edge behavior: sets may be empty, and
  both wrappers go maximal (full class set, unbounded interval) when
  the calibration size cannot support the requested level. A
  domain-of-applicability model (`fit_domain`, `DomainModel.novelty`)
  reports orthogonal novelty signals (family seen, nearest-family
  Jaccard distance, descriptor-cloud distance, element coverage) plus a
  conservative combined `in_domain` flag, JSON round-trippable for
  caching. Empirical coverage at nominal 80/90/95 on the frozen grouped
  folds, split by domain flag, is measured in
  `docs/uncertainty-coverage.md`. Limitation, stated where it matters:
  the conformal guarantee assumes calibration/test exchangeability,
  which novel chemistries violate; that is what the domain flag is for.
  These tools describe this package's confidence only.
- The consolidated experimental corpus is now a first-class, standalone
  product: `hea_bench.corpus.load_corpus()` returns every corpus row
  (including conflict-quarantined ones) with full per-source provenance
  already recorded by the build (per-source canonical and verbatim
  phase labels, Borg processing and primary-literature DOI, upstream
  row identifiers), chainable `query()` filters, `describe()`
  statistics with a multi-source agreement rate, and `to_csv()` export
  of any slice. A generated dataset card (`docs/corpus-card.md`)
  documents provenance chains, per-source license status, harmonization
  rules, and known limitations. `load_benchmark()` is now a thin
  wrapper over this API with byte-identical output: all frozen split
  digests, row counts, and baseline numbers are unchanged, and the
  corpus build now refuses loudly (naming the missing source and its
  fetch command) rather than ever building a partial corpus. The corpus
  API is standard-library only and, like the benchmark, works from a
  repository checkout or `HEA_BENCH_BENCHMARK_DIR`.
- Descriptor computation is now backend-pluggable. The default
  (`native`) backend is the package's own stdlib implementation and is
  unchanged; `pip install "hea-bench[interop]"` adds an adapter over an
  installed HEACalculator (Sariturk et al., GPLv3) exposing the same
  interface, `descriptor_matrix(..., backend=...)` accepts either, and
  a new CLI subcommand `hea-bench describe FORMULA [--backend ...]`
  prints a strict-JSON descriptor report. Same-named values can differ
  between backends because each vendors its own reference data (radius
  conventions differ most); the measured comparison is committed as
  `docs/backend-agreement.md`, structurally different quantities are
  deliberately left unmapped, and every published baseline number still
  comes from the native backend. Limitations: the adapter targets
  HEACalculator's 2.0 `get_dict` schema, and compositions outside its
  element database come back as typed None values rather than numbers.

### Changed

- The web app's Miedema solid-solution / amorphous / compound
  decomposition moved from hand-maintained page script into the
  parity-tested core. Its per-element parameter table is now generated
  from the vendored matminer `Miedema.csv` (the same file the Python
  mechanics table reads) by `tests/data/_sync_js_tables.py`, and a
  Node regression suite pins the decomposition's values. Reconciling
  the old hand table against the CSV corrects several displayed
  numbers, most visibly: the Ti and Ru surface areas V^(2/3) (the hand
  table carried 4.12 and 4.60 where the CSV volumes give 4.82 and
  4.07, shifting Ti- and Ru-pair chemical terms by roughly ten
  percent), silicon's metallic molar volume (12.06 -> 8.6 cm3/mol,
  which shrinks Ni-Si elastic mismatch terms severalfold and makes the
  volume consistent with the V^(2/3) the page already used), manganese
  and chromium bulk moduli (120 -> 59.67 and 160 -> 190.3 GPa), and
  yttrium's volume-correction constant (0.04 -> 0.07). Bulk and shear
  moduli and molar volumes for all 37 covered elements now match the
  vendored table exactly (Fe 170 -> 168.3 GPa and similar
  rounding-level shifts elsewhere).
- Internal consolidation across surfaces with no API change: one JSON
  non-finite sanitizer, one 14-descriptor feature-row builder, one
  scorable-element set, and one rules registry shared by the design
  search, campaigns, and the MCP surface, which also makes
  `yeh_entropy` accepted as an alias of `yeh_smix` in rule
  constraints. Caching the pair-table coverage set makes a full native
  descriptor profile about eight times faster.

## [2.4.0] — 2026-08-11

### Changed

- The benchmark's framing is revised. The random-versus-grouped gap is
  now described as the difference between interpolative (random-split)
  and extrapolative (family-grouped) evaluation, rather than as leakage
  or inflation, following the established reading of grouped evaluation
  in the literature (Li et al., Commun. Mater. 6:9, 2025,
  doi:10.1038/s43246-024-00731-w; Meredig et al. 2018 LOCO-CV). The
  `EvaluationReport.inflation` field is renamed `gap`, and
  `leakage_profile` is renamed `family_overlap_profile`. All split
  digests, fold assignments, corpus builds, and baseline numbers are
  unchanged; only wording and the two names moved.

## [2.3.2] — 2026-08-10

### Changed

- Settle the corpus roles: v0.1.0 is the reference, v0.2.0 the extended option
- Style the download-window notice as a proper callout

## [2.3.1] — 2026-08-10

### Changed

- Handle the release window on the Windows-app download link

## [2.3.0] — 2026-08-10

### Added

- Benchmark corpus v0.2.0, adding the Chizhevskiy et al. LLM-extracted
  HEA database (Sci. Data 13, 612), which became usable when its
  repository gained a CC-BY-4.0 license on 2026-08-10. The labelled
  corpus grows from 7,683 to 10,064 alloys with its own frozen,
  digest-pinned splits. `load_benchmark(version="0.2.0")` opts in; the
  default stays v0.1.0 because the new source's LLM-extracted labels
  agree with the established consensus on only about 70% of overlapping
  alloys, and every such disagreement is quarantined as a conflict
  rather than resolved by voting. The named-intermetallic raw labels
  (B2, L12, Laves, sigma) are preserved verbatim as side-channel
  columns.

## [2.2.1] — 2026-08-10

### Added

- `hea_bench.benchmark`: frozen, leakage-controlled train/test splits for
  HEA phase prediction plus a paired evaluation API. `load_benchmark()`
  returns the consolidated corpus with two frozen five-fold splits over
  the same rows: one grouped by alloy family (the set of elements
  present, so no alloy system straddles a train/test boundary) and one
  random. `evaluate(model)` scores a model under both and reports the
  gap, which measures how much of a random-split score is interpolation
  between stoichiometric variants rather than prediction. Each split
  carries a SHA-256 digest of its fold assignment, pinned in the test
  suite, and the grouped split uses no random number generator and no
  float arithmetic in fold assignment, so the same corpus produces
  byte-identical folds on every platform (a CI job rebuilds the corpus
  and verifies the digests on each push).
  On corpus v0.1.0 a stock random forest over this package's descriptors
  scores 0.941 balanced accuracy under the random split and 0.734 under
  the grouped one; baseline results and provenance live in
  `docs/benchmark-baselines.md`.
- The benchmark corpus is built locally, not shipped: its largest source
  dataset (Peivaste) declares no license, so the repo carries loaders,
  pinned SHA-256 hashes, and a fetch script instead of that data, and
  the derived corpus inherits the restriction. The two CC-BY sources
  (Borg 2020, Pei 2020) are mirrored. See `data/raw/README.md` for the
  per-source licensing audit.
- New optional extra `benchmark` pinning the scikit-learn version used
  by the baseline table. The benchmark subpackage itself, like the core,
  needs only the standard library.

(These notes were first staged for a v2.2.0 that was tagged but never
published: its release run was correctly blocked by the new benchmark
CI gate itself, which caught the corpus build producing different
composition keys on Python 3.12 than on 3.10. Builtin `sum` switched
to compensated summation in 3.12, and that last-bit difference in
normalization totals moved a few mole fractions across the 4-decimal
rounding boundary. Composition normalization now uses exactly rounded
`math.fsum`, fold assignment uses exact integer arithmetic, and the
frozen digests were re-pinned after verifying byte-identical corpus
builds on Python 3.10, 3.12, and 3.13 across Windows and Linux. No
published result was affected, because nothing had been published.)

## [2.1.7] — 2026-08-09

### Changed

- Writing pass over the web app's prose: em dashes removed from page
  text, footer labels, drawer notes, and the title tag (value
  placeholders, cited paper titles, and TeX are untouched), several
  passive constructions made active on the landing page and Data view,
  and the version badge now uses consistent separators. No functional
  or numerical change.

## [2.1.6] — 2026-08-09

### Fixed

- Composition parsing now rejects non-whitespace input that is not consumed by the
  documented element-and-amount grammar, instead of silently calculating a composition
  from only the matched tokens. Existing compact, percent-style proportional, and
  space-separated forms are unchanged. Reported by Yen-Ming Horng in
  [#1](https://github.com/dfieser/hea-bench/issues/1).
- The browser and desktop apps apply the same full-consumption contract
  in their own formula parser, so a malformed `?comp=` permalink now
  shows a parse error instead of silently computing a composition built
  from only the recognizable tokens, and a rejected permalink no longer
  renders results or a citable record at all. Same report, [#1].

## [2.1.5] — 2026-08-08

### Added

- Acknowledgements section in the README crediting Yen-Ming Horng for
  the external reproducibility and documentation review behind the
  v2.1.4 fix, at his request and in the form he asked for.
- Attribution policy: the project credits named humans only. A
  `commit-msg` hook in `tools/git-hooks/` rejects AI and agent
  attribution trailers, enabled per clone with
  `git config core.hooksPath tools/git-hooks`.
- Yen-Ming Horng recorded in `.zenodo.json` as a contributor, so the
  acknowledgement carries into the archived DOI metadata of the next
  release. The `creators` list is unchanged.

## [2.1.4] — 2026-07-29

### Fixed

- Documentation of `delta_g_max` corrected in the two places that still
  described a composition-weighted form. The AGENTS.md API table and the
  result-card tooltip in the web app now state the raw definition that
  the runtime, the docstring, the README, llms.txt, the provenance
  drawer, the paper, and the pinned regression test all already use:
  the most negative raw Miedema pair enthalpy, with no 4*c_i*c_j
  scaling. Both stale strings were leftovers from the composition
  weighted draft removed during the 1.1.0 phi-family work. Reported by
  Yen-Ming Horng (external reproducibility and documentation review).
  No calculated value changes on any surface.
- `tests/test_phi.py` named the wrong pair in a docstring. The Cantor
  argmin is Mn-Ni at -8.0 kJ/mol, not Cr-Ni, which is -7.0. The
  asserted value was already correct.

### Changed

- README prose no longer uses em dashes.

## [2.1.3] — 2026-07-24

### Changed

- The desktop app gets its own icon: the HEA-Bench hexagon mark with a
  cream crystal lattice on brand terracotta, replacing the default
  Tauri icon across every size (generated reproducibly by
  tools/make_icons.py). The browser favicon now matches.

## [2.1.2] — 2026-07-23

### Fixed

- The "copied" badge moved to the bottom-left of the card as a small
  chip; at the top right it collided with long card titles.

## [2.1.1] — 2026-07-23

### Fixed

- The "copied" badge no longer overlaps the provenance info button on
  result cards.
- Links in the provenance drawer and Data view now use the accent color
  instead of low-contrast default blue on dark surfaces.
- The cite panel's citation and BibTeX list all three authors, and the
  article BibTeX is a real entry with journal, volume, number, and pages
  fields (the Zenodo software entry likewise); the bibliography
  generator now emits field-level BibTeX for every reference.
- The pair-enthalpy source tag now names the actual source, Miedema /
  de Boer et al. (1988), instead of "hea-bench".
- Drawer equations containing "<" (like the ΔH mix sum over i<j) render
  as math instead of being eaten by the HTML parser.

## [2.1.0] — 2026-07-23

### Fixed

- Composition permalinks (`?comp=...`) now open the calculator directly;
  previously the landing overlay stayed on top of the computed result,
  which made shared and cited links look broken.
- Alloys outside the Miedema decomposition's parameter set now get one
  summary warning instead of a warning per element pair.

### Added

- Element coverage 37 → 55 across all surfaces: the full experimentally
  active rare-earth HEA palette (Pr, Nd, Sm, Tb, Dy, Ho, Er, Tm, Yb, Lu),
  Ga, Ge, U, Th, Sr, Sb, Bi, Pb. Radius authority: Teatum, Gschneidner &
  Waber LA-4003 (1968), every value read from the Table I scan; CRC
  melting points; Guo-convention VEC (lanthanides 3, divalent Yb 2,
  Zachariasen U 6); Pauling electronegativities. 1484 of 1485 Miedema
  pairs covered (the lone Th–U gap is reported, never zeroed).
- Six new criteria on all surfaces, parity-tested: Singh Λ, Wang
  solid-angle γ, Andreoli elastic-strain energy ΔH_el (with a new
  per-element mechanics loader), the temperature-explicit Senkov–Miracle
  κ criterion, the Tsai σ-phase VEC window, and the Sheikh refractory
  ductility screen.
- Phase-selection maps in the calculator: the Zhang δ–ΔH_mix map, the
  Yang–Zhang Ω–δ map, and a VEC band strip (Guo bands + σ window +
  ductility line) with the current alloy plotted and cited captions.
- Provenance drawer: an info button on every result card opens the
  defining equation, the exact per-element inputs the number consumed
  (with source links and user-edit flags), the interpretation window
  with primary citations, per-descriptor BibTeX, and cross-links into
  Theory, Equations, References, and the new Data view.
- Cite-this-result panel: content-derived result IDs
  (`hea-<sha256/12>` over version + canonical inputs), permalinks,
  formatted citation and BibTeX, and a downloadable JSON receipt with
  inputs, outputs, data-file SHA-256 pins, and the full reference list.
  The oxide copy-JSON button emits the same envelope.
- Data view (fifth tab): the 55-element table with per-value sources,
  Miracle & Senkov 2017 Table 3 cross-checks (including their Pr/Nd/Tm
  misprints, flagged), per-element convention flags, a pair-enthalpy
  lookup, data-file integrity pins, and a per-element feature-coverage
  matrix.
- Theory sections for Λ/γ (tangent-cone derivation), κ (Gibbs
  derivation), and ΔH_el; four new equation cards; anchors on every
  bibliography entry; a new "Element data sources" reference group; the
  previously uncited King 2016 and Ye 2015 rules now carry full entries.

### Changed

- MCP: `alloy_descriptors` gains `lambda_singh`, `gamma_wang`,
  `h_elastic`; `alloy_rules` gains `senkov_kappa` (shares
  `king_temperature`), `tsai_sigma`, `sheikh_ductility`; source keys for
  the new criteria and the element-data authorities.
- The LA-4003 attribution replaces the imprecise "Teatum & Waber 1967"
  in the data-layer documentation.
- Landing page, JSON-LD (`variableMeasured`), status bar, and READMEs
  reflect the 55-element / 1484-pair coverage; the version badge now
  carries the data-table fingerprint.
- The auxiliary Miedema decomposition panel deliberately stays on its
  original 37-element parameter set (no invented f-block Miedema
  classes); the coverage matrix in the Data view makes that explicit.

## [2.0.10] — 2026-07-19

### Changed

- SEO: sitemap discovery hint in the page head
- Zenodo metadata: link the live web app as a related identifier

## [2.0.9] — 2026-07-19

### Changed

- Add the Google Search Console ownership verification tag
- SEO: canonical, Open Graph, and JSON-LD software metadata on the web app, plus a deploy-time sitemap.xml

## [2.0.8] — 2026-07-17

### Changed

- Cite the published Materials article everywhere

## [2.0.7] — 2026-07-09

### Changed

- Landing page: the top bar, stats strip, and footer now respect the page side padding
- Auto-release: re-dispatch a cancelled downstream run once instead of only going red

## [2.0.6] — 2026-07-09

### Changed

- Landing page: side padding now scales with the window so the top bar has real breathing room
- Make releases autonomous: any shippable push to main cuts a full patch release
- Add tools/autorelease.py: one-shot release preparation (version, stamps, changelog, history)

## [2.0.5] — 2026-07-08

### Changed

- Landing page. Widened the shared side padding on the landing page so the top
  navigation bar and page sections are no longer crowded against the edges, with
  a narrower fallback on small phones. Presentation only; no functional or
  numerical change to any descriptor, rule, or API.

## [2.0.4] — 2026-07-06

### Changed

- Build tooling. Bumped the pinned GitHub Actions (checkout, setup-python,
  setup-node, upload/download-artifact, the Pages actions, and the GitHub
  Release action) to their current majors, so CI and the release pipeline no
  longer run on the deprecated Node 20 runtime. No functional or numerical
  change to any descriptor or rule.

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
