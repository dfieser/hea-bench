# HEA-Bench Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the eight-phase expansion spec (descriptor backends, corpus as product,
uncertainty, properties, design search, campaigns, MCP expansion, ceramics) against the
v2.4.0 tree.

**Architecture:** Every new capability is an optional layer over the dependency-free core.
Stdlib-only where possible (corpus, conformal, applicability, design core, ceramics);
scikit-learn-backed pieces live behind pinned optional extras. The frozen benchmark
(digests, baselines) is a hard invariant that every phase must leave untouched.

**Tech Stack:** Python >= 3.10 stdlib core; optional extras: `interop` (HEACalculator,
GPLv3, user-installed), `properties` / existing `benchmark` (scikit-learn ~= 1.7.2), `mcp`.

**Source spec:** `D:\Downloads\EXPANSION-BUILD-SPEC.md` (copied assumptions were verified
against the tree on 2026-08-11; deviations are noted inline as "Adaptation").

## Global Constraints

- `[project] dependencies = []` stays empty. New third-party libraries go in optional
  extras, pinned with a why-comment when they can move published numbers.
- Frozen split digests (tests/test_benchmark_corpus.py FROZEN) and every number in
  docs/benchmark-baselines.md are unchanged. A moved digest or baseline is a STOP
  condition: halt the phase and report, do not re-pin.
- No em dashes anywhere (code, comments, docs, changelog). No AI attribution anywhere.
- Splits are framed as interpolative (random) versus extrapolative (grouped)
  evaluation only; the retired framing from the closed audit must not reappear
  in any new text. Uncertainty output describes this package's confidence,
  never other tools or published accuracies. No criterion ranking headlines.
- Typed failure over silent substitution: raise or flag None, never impute quietly.
  Missing optional extras raise a typed error naming the exact pip install command.
- Every prediction-bearing API added from Phase 3 on returns an uncertainty measure and an
  `in_domain` flag at top level.
- Version stays 2.4.0 in this working session; only `python tools/version.py --set` may
  ever change it, at release time, at the maintainer's direction. No pushes this session;
  one local commit per phase, CHANGELOG entries accumulate under [Unreleased].
- Python 3.10 compatibility (ruff target py310, line length 100); `ruff check src tests`
  and `python -m pytest tests/ -q` green before every commit.
- The Zenodo/GitHub integration is untouchable.

## Verified tree facts the spec did not know

- Tree is at v2.4.0; `gap` / `family_overlap_profile` renames already applied.
- `data/consolidated/v0.1.0` and `v0.2.0` are built locally; digest tests run here.
- consolidated.csv already carries per-source labels, raw labels, borg_processing,
  borg_doi, and source_row_ids; Phase 2 provenance is exposure, not new data.
- data/raw/borg2020/MPEA_dataset.csv (CC-BY-4.0, mirrored) carries HV, YS, UTS,
  elongation, exp/calc density, exp/calc Young modulus, O/N/C content, processing,
  test temperature, per-row DOI. Phase 4 Tier B needs no new fetch.
- The CLI is a version stub whose docstring reserves a future `describe` subcommand;
  that is where Phase 1 threads `--backend`.
- HEACalculator: `pip install HEACalculator`, GPLv3, CLI + GUI + Python API (API shape to
  be discovered at install time and pinned in the adapter).
- `hea_bench.rules.__init__` docstring references `hea_bench.classifiers.diagnostic_stats`
  (does not exist) and lists 4+2 rules where 9 ship. Fix in Phase 1.
- Local toolchain: Python 3.10.1, pytest 9.0.2, ruff 0.15.14, scikit-learn 1.7.2, node
  present in CI for web parity.

---

## Phase 1: Descriptor backend abstraction and HEACalculator interop

### Task 1.1: Housekeeping fix in rules/__init__.py

**Files:** Modify: `src/hea_bench/rules/__init__.py` (docstring only)

- [ ] Rewrite the module docstring: evaluation machinery reference becomes
  `hea_bench.benchmark` (evaluate + load_benchmark), and the rule list becomes the nine
  shipped modules (yeh_smix, zhang_delta, guo_vec, yang_omega, king_phi, ye_phi,
  senkov_kappa, tsai_sigma, sheikh_ductility) with one-line citations matching AGENTS.md.
- [ ] `ruff check src tests` and `python -m pytest tests/ -q` pass.

### Task 1.2: backend.py with NativeBackend

**Files:**
- Create: `src/hea_bench/descriptors/backend.py`
- Test: `tests/test_descriptor_backend.py`

**Produces (later tasks rely on these exact names):**

```python
class BackendUnavailableError(RuntimeError): ...   # message names the pip install
class DescriptorBackend(Protocol):
    name: str
    def descriptor_names(self) -> tuple[str, ...]: ...   # union, this backend's Nones included
    def matrix_names(self) -> tuple[str, ...]: ...       # the all-float subset for matrices
    def compute(self, composition: Composition) -> dict[str, float | None]: ...

UNION_DESCRIPTOR_NAMES: tuple[str, ...]   # native 16 + heacalculator-only names
class NativeBackend:          # name = "native"
class HEACalculatorBackend:   # name = "heacalculator", lazy import
def get_backend(backend: str | DescriptorBackend | None = None) -> DescriptorBackend
```

- `compute` returns the union name set: native fills its 16 (`smix, delta, vec,
  melting_temperature, mixing_enthalpy, omega, s_excess, delta_g_ss, delta_g_max,
  phi_king, phi_ye, delta_chi, mean_electronegativity, singh_lambda, wang_gamma,
  h_elastic`), `None` for names only the other backend defines, `None` when a value is
  not computable (missing element data), and the raw float otherwise (inf allowed,
  callers decide; matches current library behavior).
- `NativeBackend.matrix_names()` is exactly today's `descriptor_names()` 14-tuple from
  `benchmark/corpus.py` (excludes singh_lambda, h_elastic, same reasons).
- Explicit `_HEACALCULATOR_MAP` table: our name -> their accessor; unmapped stays None.
  Never map a near-equivalent silently (their Takeuchi-Inoue h_mix is NOT our Miedema
  h_mix: both are exposed under distinct names, `mixing_enthalpy` native versus
  `mixing_enthalpy` theirs, and the agreement doc quantifies the difference).

- [ ] Write failing tests: native compute matches direct functions on Cantor
  (pinned: smix 13.381, delta 3.164, vec 8.0, omega 5.794, abs 5e-4); uncovered-element
  composition ({"Co": 1, "Fr": 1} - Fr parses but has no table row) yields None values,
  no raise; `get_backend()` defaults to NativeBackend; `get_backend("nope")` raises
  ValueError listing known names; `get_backend(instance)` passes through.
- [ ] Implement `backend.py` (NativeBackend + registry + error type; HEACalculator
  adapter stub raising BackendUnavailableError when import fails).
- [ ] Test: with `monkeypatch.setitem(sys.modules, "HEACalculator", None)`-style forced
  import failure, `get_backend("heacalculator")` raises BackendUnavailableError whose
  message contains `pip install "hea-bench[interop]"`.
- [ ] Run suite, lint.

### Task 1.3: HEACalculatorBackend adapter (real API)

**Files:** Modify: `src/hea_bench/descriptors/backend.py`, `pyproject.toml`

- [ ] `pip install HEACalculator` into the local env; introspect the Python API; record
  exact import path, call shape, and version in the module comment.
- [ ] Fill `_HEACALCULATOR_MAP` with verified accessors; unmappable names stay None.
- [ ] pyproject: `interop = ["HEACalculator>=<found major>,<next-major bound>"]` with a
  comment on the pin and on GPLv3 (their license; installing the extra is the user's
  choice; hea-bench ships none of their code and stays MIT).
- [ ] Integration tests marked `pytest.importorskip("HEACalculator")`: Cantor VEC agrees
  to 1e-6 (same definition), smix agrees (same formula), delta reported with tolerance or
  documented convention delta, h_mix NOT asserted equal (different reference data).
- [ ] Run suite, lint.

### Task 1.4: backend= through descriptor_matrix and CLI describe

**Files:**
- Modify: `src/hea_bench/benchmark/corpus.py` (descriptor_matrix, descriptor_names)
- Modify: `src/hea_bench/cli.py`
- Test: `tests/test_descriptor_backend.py`, `tests/test_cli.py` (new)

**Produces:** `descriptor_matrix(compositions, *, backend=None)`,
`descriptor_names(backend=None)`, CLI `hea-bench describe FORMULA [--backend NAME]
[--json]`.

- [ ] backend=None keeps the current code path byte-for-byte (existing pinned tests are
  the guard). backend given: resolve via get_backend, columns = backend.matrix_names(),
  any None value raises ValueError naming composition and descriptor (typed, no
  imputation).
- [ ] Failing tests first: `descriptor_matrix([cantor], backend="native") ==
  descriptor_matrix([cantor])`; unknown backend name raises; None-value case raises with
  the composition in the message.
- [ ] CLI: argparse subparser `describe`; prints JSON {input, composition, descriptors
  {name: {value, unit}}, backend, warnings}; `--backend heacalculator` without the extra
  exits 2 with the BackendUnavailableError message on stderr. Unit strings reuse the
  mcp_server._DESCRIPTORS units (import from one shared table; move the name->unit map
  into backend.py and have mcp_server consume it so there is one source of truth).
- [ ] tests/test_cli.py: describe Cantor exercises stdout JSON (json.loads, spot-check
  smix approx 13.381); `--version` behavior unchanged.
- [ ] Run suite, lint.

### Task 1.5: agreement harness + doc + CI

**Files:**
- Create: `tools/backend_agreement.py`, `docs/backend-agreement.md` (generated + committed)
- Modify: `.github/workflows/ci.yml` (new `interop` job), `README.md`, `AGENTS.md`,
  `CHANGELOG.md` ([Unreleased])

- [ ] tools/backend_agreement.py: FIXED literal list of 50 formulas spanning corpus
  chemistry (Cantor family, Al-x, refractory, precious, rare-earth, solder); computes
  shared descriptors under both backends; writes per-descriptor delta table (mean, max,
  sign structure) plus a provenance paragraph: differences are reference-data choices
  (their tabulated Takeuchi-Inoue binaries versus our Miedema computation; radius
  conventions), not bugs, and neither side is declared right.
- [ ] Generate the doc with the real installed HEACalculator; record its exact version in
  the doc header. Commit the doc.
- [ ] CI job `interop` (3.12): `pip install -e ".[dev,interop]"`, run
  tests/test_descriptor_backend.py tests/test_cli.py.
- [ ] README: short "Descriptor backends" section (native default, interop optional,
  agreement doc link). AGENTS.md: one paragraph + describe example. CHANGELOG entry
  under [Unreleased] (capability + the different-reference-data caveat).
- [ ] Full suite + lint. Acceptance: default path outputs unchanged (existing pinned
  tests), bare core imports clean with the extra absent.
- [ ] Commit: `Add descriptor backend abstraction with optional HEACalculator interop`.

---

## Phase 2: The corpus as a first-class product

### Task 2.1: protective pins before refactor

**Files:** Test: `tests/test_benchmark_corpus.py` (additions only)

- [ ] Add `test_load_benchmark_first_and_last_rows_pinned` (needs_corpus): row 0 and
  row -1 composition_key, sources, n_elements, family, canonical_phase for v0.1.0
  single_vs_multi, values read from the current build and pinned as literals.
- [ ] Run to green BEFORE any refactor; these plus the digest pins are the stop-condition
  guard for 2.3.

### Task 2.2: family_of moves to composition.py

**Files:** Modify: `src/hea_bench/composition.py`, `src/hea_bench/benchmark/splits.py`

Import-cycle rationale: `hea_bench.corpus` (new, top-level) must not import
`hea_bench.benchmark` (whose `__init__` imports corpus machinery back). `family_of` is a
composition-level concept; move the function body to composition.py verbatim,
splits.py does `from ..composition import family_of` and keeps re-exporting it
(`__all__` unchanged) so every existing import path still works.

- [ ] Move + re-export; no test changes needed (existing splits doctests/tests cover);
  run suite to confirm zero drift.

### Task 2.3: hea_bench.corpus package

**Files:**
- Create: `src/hea_bench/corpus/__init__.py`
- Test: `tests/test_corpus.py`

**Produces (later phases consume these exact shapes):**

```python
@dataclass(frozen=True)
class CorpusRow:
    composition_key: str
    composition: Composition
    n_elements: int
    family: str
    sources: tuple[str, ...]
    canonical_phase: str | None          # None = unlabelled (conflict or blank)
    has_conflict: bool
    labels: dict[str, str]               # per-source canonical label
    raw_labels: dict[str, str]           # per-source reported phase string, verbatim
    processing: str | None               # Borg only, upstream truth
    doi: str | None                      # Borg only
    source_row_ids: dict[str, str]
    descriptor_ready: bool

class Corpus:   # frozen container, chainable
    rows: tuple[CorpusRow, ...]; version: str; manifest: dict
    def query(self, *, elements=None, contains=None, excludes=None, n_elements=None,
              phase=None, source=None, family=None, labelled=None,
              has_conflict=None, descriptor_ready=None) -> "Corpus"
    def describe(self) -> dict
    def to_records(self) -> list[dict]
    def to_csv(self, path) -> int
    def __len__(self); def __iter__(self)

def load_corpus(version="0.1.0", *, corpus_dir=None) -> Corpus
def corpus_location(version, corpus_dir=None) -> pathlib.Path   # env var logic lives here
```

Query semantics (document in docstrings): `elements` = exact element-set match;
`contains` = all listed present; `excludes` = none present; `n_elements` = int or
(min, max) inclusive; `phase` = canonical_phase equality (str or set);
`source` = that source contributed (str or set, any-of); `labelled` = canonical_phase
is not None; filters AND together; each call returns a new Corpus sharing row objects.

`describe()` returns: n_rows, n_labelled, n_conflicts, by_phase, by_n_elements,
by_source (contribution counts), n_families, top_families, element counts,
multi_source_rows, multi_source_agreement_rate (rows with >= 2 sources that agree:
1 - conflicts/multi_source_rows), descriptor_ready count.

- [ ] Failing unit tests over a synthetic 6-row CSV written to tmp_path (2 sources, one
  conflict row, one unlabelled, one multi-source agreeing row): load, all filters, len,
  describe values exact, to_csv round-trip, to_records.
- [ ] Integration tests (needs_corpus): v0.1.0 len == 7784 - 1 header == 7783 total rows
  (labelled 7683 + conflicts 100), describe()["multi_source_agreement_rate"] matches
  1 - 100/multi_source_rows, query(contains=["Al"]).query(excludes=["Pb"]) chains,
  query(labelled=True) count == 7683.
- [ ] Implement; reader parses the consolidated.csv columns including the per-source
  label/raw-label columns discovered from the header (schema is derived from the
  version's source list, exactly like consolidate._csv_columns).
- [ ] Run suite, lint.

### Task 2.4: load_benchmark becomes a thin wrapper

**Files:** Modify: `src/hea_bench/benchmark/corpus.py`

- [ ] Replace the CSV-reading body of load_benchmark with: `corpus =
  hea_bench.corpus.load_corpus(version=..., corpus_dir=...)`; then project
  `corpus.rows` in order: skip canonical_phase None, project task label, skip None
  label, build BenchmarkRow from CorpusRow fields (composition object reused; family
  reused; descriptor_ready reused; sources tuple reused). Splits code unchanged.
  Error behavior preserved: missing corpus dir raises the same FileNotFoundError with
  build commands (raise from corpus_location check in load_corpus with that exact
  message); unknown task ValueError unchanged.
- [ ] STOP CONDITION CHECK: run tests/test_benchmark_corpus.py tests/test_benchmark_splits.py
  in full; every digest, count, and newly pinned row test must pass untouched.
- [ ] Run suite, lint.

### Task 2.5: loud build failures

**Files:** Modify: `src/hea_bench/benchmark/consolidate.py`
Test: `tests/test_consolidate_errors.py` (new)

- [ ] In build(): before running loaders, check each source path exists; missing ->
  raise FileNotFoundError listing the missing file, its fetch command
  (peivaste: `python data/raw/peivaste/fetch.py`; mirrored sources: restore the file
  from the repository checkout), and the statement that a partial corpus is never built.
- [ ] Unit test with out_dir=tmp and a bogus _SOURCE_PATHS monkeypatch asserting the
  message names the missing source and no output files were written.
- [ ] Run suite, lint.

### Task 2.6: corpus card

**Files:**
- Create: `tools/corpus_card.py`, `docs/corpus-card.md` (generated + committed)
- Modify: `README.md`, `AGENTS.md`, `CHANGELOG.md`

- [ ] tools/corpus_card.py builds both versions' cards from load_corpus + manifest +
  static per-source sections: provenance chain (paper, deposit, fetch/mirror path,
  SHA-256 from manifest), license status per source (from data/raw/README.md facts),
  harmonization rules (from consolidate docstrings), known limitations (composition-only
  join, processing not in key, conflict quarantine, chizhevskiy ~70 percent agreement and
  quarantine-not-vote, class skew), v0.1.0 versus v0.2.0 roles with the standing
  recommendation (v0.1.0 = evaluation reference). Absolutely no rule-versus-rule ranking
  content.
- [ ] Generate, commit doc. README + AGENTS get a "Corpus API" snippet
  (load_corpus/query/describe). CHANGELOG entry.
- [ ] Full suite + lint + commit: `Promote the corpus to a first-class queryable product`.

---

## Phase 3: Uncertainty and domain of applicability

### Task 3.1: split conformal, stdlib

**Files:**
- Create: `src/hea_bench/uncertainty/__init__.py`, `src/hea_bench/uncertainty/conformal.py`
- Test: `tests/test_conformal.py`

**Produces:**

```python
class ConformalClassifier:
    def __init__(self, model): ...            # needs predict_proba + classes_
    def fit_calibrate(self, X_cal, y_cal): ...  # returns self; stores sorted scores
    def predict_set(self, X, alpha=0.1) -> list[set[str]]
class ConformalRegressor:
    def __init__(self, model): ...            # needs predict
    def fit_calibrate(self, X_cal, y_cal): ...
    def predict_interval(self, X, alpha=0.1) -> list[tuple[float, float]]
```

Math (split conformal, distribution-free finite-sample):
score_i = 1 - p_model(y_i | x_i) (classifier) or |y_i - yhat_i| (regressor);
qhat = the k-th smallest calibration score with k = ceil((n+1) * (1 - alpha));
if k > n the guarantee cannot be met at this alpha: classifier returns the full class
set, regressor returns (-inf, inf), and both attach that fact via a documented
`.degenerate(alpha)` predicate (typed honesty, not an exception).
Prediction set = {c : 1 - p(c|x) <= qhat}; interval = yhat +- qhat.

- [ ] Failing tests with hand-rolled fake models (no sklearn): 3-class fake with fixed
  probabilities and a hand-computed qhat -> exact expected sets at alpha 0.2; regressor
  fake predicting 0 with calibration residuals [1,2,3,4] -> qhat at alpha 0.5 is 3
  (k = ceil(5*0.5) = 3), intervals (-3, 3); alpha <= 0 or >= 1 raises ValueError; empty
  calibration raises; k > n degenerate behavior.
- [ ] Implement (~80 lines); docstring states the exchangeability assumption and its
  violation by novel-chemistry queries, pointing to applicability.
- [ ] sklearn integration test under `pytest.importorskip("sklearn")`: RF on a toy
  two-moons-like descriptor set, empirical coverage at alpha 0.1 in [0.85, 1.0] with a
  fixed seed.
- [ ] Run suite, lint.

### Task 3.2: applicability

**Files:**
- Create: `src/hea_bench/uncertainty/applicability.py`
- Test: `tests/test_applicability.py`

**Produces:**

```python
@dataclass(frozen=True)
class DomainModel:
    corpus_version: str
    families: dict[str, int]
    descriptor_names: tuple[str, ...]
    descriptor_mean: tuple[float, ...]
    descriptor_scale: tuple[float, ...]
    distance_threshold: float           # 99th percentile of in-corpus self-distances
    covered: frozenset[str]
    def novelty(self, composition) -> dict
    def to_json(self) -> str
    @classmethod def from_json(cls, text) -> "DomainModel"
def fit_domain(corpus) -> DomainModel        # Corpus or iterable of CorpusRow
def novelty_score(composition, corpus) -> dict   # convenience, documented slow path
```

novelty() dict keys, all always present: `element_set_seen` (bool), `family_count`
(int), `nearest_family_distance` (min Jaccard distance over corpus families, 0..1),
`descriptor_distance` (RMS z-score over the 14 matrix descriptors; scaled Euclidean,
deliberately not Mahalanobis: a 14x14 stdlib inversion is fragile and the docstring says
so), `element_coverage` (bool), `in_domain` (bool). Conservative documented rule:
`in_domain = element_coverage and descriptor_distance <= distance_threshold and
nearest_family_distance <= 0.5`. Components ship because they fail differently; the
scalar rule is a convenience, not the signal.

- [ ] Failing tests: synthetic corpus of 3 families -> exact Jaccard distances; exact
  z-scores on a 2-descriptor synthetic (monkeypatched names); Cantor on real corpus
  (needs_corpus) is in_domain with element_set_seen True; {"Fr":1,"Ra":1} has
  element_coverage False and in_domain False without raising; JSON round-trip equality.
- [ ] Implement. fit_domain uses descriptor-ready rows with all-finite descriptors only,
  and records that count.
- [ ] Run suite, lint.

### Task 3.3: coverage study doc + CI extras job

**Files:**
- Create: `tools/uncertainty_coverage.py`, `docs/uncertainty-coverage.md` (generated)
- Modify: `.github/workflows/ci.yml` (job `test-extras`: `pip install -e
  ".[dev,benchmark]"`, full pytest), `README.md`, `AGENTS.md`, `CHANGELOG.md`

- [ ] Study design (documented in the doc header): corpus v0.1.0, both tasks; for each
  grouped fold: proper-train / calibration split of the training rows (seeded, family
  grouped so calibration families never appear in proper-train), RF(300, seed 0) on the
  14 descriptors; empirical coverage of conformal sets at nominal 80/90/95 on the
  held-out fold, overall and split by the DomainModel in_domain flag fitted on
  proper-train rows only. Report set sizes too (a full-set prediction is honest but
  useless, and the table should show how often that happens).
- [ ] Expected honest outcome stated in the doc: coverage near nominal in-domain,
  degraded out-of-domain; that degradation is the reason the flag ships. No statement
  about any published model or tool.
- [ ] Generate, commit. README "Uncertainty" section + AGENTS snippet + CHANGELOG.
- [ ] Full suite + lint + commit: `Add split conformal prediction and a domain-of-applicability layer`.

---

## Phase 4: Multi-property surrogates (interfaces locked; elaborate before execution)

**Files:** Create `src/hea_bench/properties/{__init__,tier_a,hardness}.py`,
`src/hea_bench/properties/data/{atomic_masses,element_prices}.py`,
`tools/property_cards.py`, `docs/property-hardness.md`, `docs/property-tier-a.md`;
Modify `pyproject.toml` (`properties = ["scikit-learn~=1.7.2"]` pinned, why-comment),
README, AGENTS, CHANGELOG. Tests: `tests/test_properties_tier_a.py`,
`tests/test_properties_hardness.py`.

**Produces:**

```python
@dataclass(frozen=True)
class PropertyPrediction:
    prop: str; value: float; unit: str
    interval: tuple[float, float] | None   # None only for tier A closed forms
    alpha: float | None
    tier: str                              # "A" | "B"
    in_domain: bool | None; novelty: dict | None
    n_training: int | None; model_card: str | None
    asof: str | None                       # date stamp, cost only
    warnings: tuple[str, ...]
def predict_property(composition, prop, *, alpha=0.1, processing=None) -> PropertyPrediction
def available_properties() -> dict[str, dict]
class PropertyUnavailableError(RuntimeError)   # names the missing extra or the omission reason
```

Committed decisions:
- Tier A: `density` g/cm3 = sum(c_i M_i) / sum(c_i V_i) over new IUPAC/CIAAW abridged
  standard atomic weights table (stdlib data module, cited) and mechanics molar volumes;
  None propagates when either table lacks an element (h_elastic pattern). Validated
  against Borg experimental densities; MAE goes in docs/property-tier-a.md.
  `cost_per_kg` USD/kg from a date-stamped indicative price table (sources per element
  recorded in the data module; gathered by a research pass at execution; if a source
  cannot be verified for an element it gets None, never a guess). `melting_temperature`
  re-exposed as tier A.
- Tier B: `hardness` (HV) from vendored Borg rows with HV present; RF regressor +
  Phase 3 ConformalRegressor + DomainModel; per-(formula, processing) deduplication with
  median HV; fitted per process lru_cache with fixed seed; model card carries n, source
  DOI, family-grouped CV MAE, interval width, processing mix, and the stated conclusion
  about whether the error supports ranking close candidates.
- `processing=` filters training rows; below 50 rows PropertyUnavailableError explains
  the floor (documented as the honest small-N outcome).
- Omitted on purpose, with reasons in the model-card doc: yield strength and elastic
  moduli (test-temperature and processing confounds in the only licensed source),
  ductility, corrosion, oxidation (no adequately licensed public data). Tier C ships
  nothing.

Acceptance: every Tier B prediction carries interval + in_domain; tier A stays stdlib;
bare install unaffected; model cards committed.
Commit: `Add tiered property predictions with intervals and domain flags`.

---

## Phase 5: Constrained composition search (interfaces locked; elaborate before execution)

**Files:** Create `src/hea_bench/design/{__init__,constraints,pareto,search}.py`,
`tools/design_recovery.py`, `docs/design-recovery.md`; tests
`tests/test_design_search.py`. README/AGENTS/CHANGELOG.

**Produces:**

```python
Maximize(name) / Minimize(name)            # name in properties or tier A callables
RuleConstraint(rule, satisfied)            # rule = module name string, satisfied = verdict str or set
PropertyConstraint(prop, min=None, max=None, bound="point")   # bound in point|lower|upper
CompositionConstraint(element, min=0.0, max=1.0)
DomainConstraint(in_domain=True)           # present by default; removable explicitly
search(elements, n_elements=(3,5), constraints=(), objectives=(),
       n_candidates=50, seed=0, step=0.05, max_evaluations=200_000,
       optimize_bound="point") -> ParetoResult
ParetoResult: candidates tuple[Candidate,...], seed, settings dict, n_evaluated,
              n_feasible, to_json()
Candidate: composition, descriptors dict, rules dict, properties dict[str,
           PropertyPrediction], novelty dict, in_domain bool, objective_values dict
```

Committed decisions: enumerate element subsets (combinations within n_elements range),
deterministic simplex lattice at `step` within per-element bounds plus seeded Dirichlet
fill to the evaluation budget; constraint filter; exact O(n^2) non-dominated filter;
optimize_bound="lower" ranks surrogate objectives by their conservative interval end
(the optimizer-exploits-model-error mitigation); DomainConstraint(in_domain=True) is ON
unless explicitly removed; framing throughout: screening and prioritization aid.
Validation: recovery study against measured Borg alloys in two palettes (Al-Co-Cr-Fe-Ni
hardness/density; refractory Mo-Nb-Ta-Ti-V-W), honest misses included.
Acceptance: same seed -> byte-identical ParetoResult.to_json(); caps enforced; every
candidate carries intervals + flags. Commit:
`Add constrained composition search returning receipted Pareto fronts`.

---

## Phase 6: Active-learning campaign loop (interfaces locked; elaborate before execution)

**Files:** Create `src/hea_bench/design/campaign.py`, `tools/campaign_replay.py`,
`docs/campaign-replay.md`; tests `tests/test_campaign.py`. README/AGENTS/CHANGELOG.

**Produces:**

```python
Campaign(objective, palette, constraints=(), seed=0, warm_start=True)
campaign.observe(composition, value, processing=None, uncertainty=None) -> None
campaign.suggest(n=5, strategy="ei") -> list[Suggestion]     # "ei" | "ucb"
campaign.save(path) / Campaign.load(path)                    # versioned JSON, schema: 1
Suggestion: composition, mean, interval, in_domain, acquisition, strategy
  (__repr__ includes interval and in_domain, per spec)
class ColdStartError(RuntimeError)
```

Committed decisions: ensemble surrogate = RF per-tree spread (variance from
disagreement; a GP over variable-length composition vectors was considered and rejected
per spec guidance, stated in the docstring); EI and UCB closed forms; batch suggestions
via the constant-liar refit between picks (documented); warm start pools Borg rows for
the matching objective where chemistry overlaps the palette, user rows are appended and
progressively dominate by count (the weighting choice is documented, not hidden); floor:
fewer than 10 informative observations (user + in-palette warm start) raises
ColdStartError telling the user the loop is near-random below that. Campaign state is
plain human-readable JSON on disk, no accounts, no telemetry.
Validation: year-ordered replay on Borg (observe pre-2016 alloys in publication order,
measure when the loop would have surfaced the later top-HV alloys versus corpus order),
honest outcome reported. Acceptance: save/load round-trip identical state; floor
enforced; replay doc committed. Commit:
`Add a JSON-state active-learning campaign loop with EI and UCB`.

---

## Phase 7: Agent surface expansion (interfaces locked; elaborate before execution)

**Files:** Modify `src/hea_bench/mcp_server.py`, `tests/test_mcp_server.py`, README,
AGENTS, CHANGELOG; check `server.json` for a tool list to update.

New tools (plain functions, testable without mcp, every payload through `_stamp`):
- `corpus_query(filters..., limit=25)`: counts + capped sample rows with provenance.
- `corpus_describe(filters...)`: Corpus.describe() of the slice.
- `predict_properties(compositions, props=None, alpha=0.1)`: interval, tier, in_domain
  at TOP LEVEL of each entry, never nested.
- `check_applicability(composition)`: the novelty components + in_domain.
- `design_search(...)`: hard caps (n_candidates <= 20, max_evaluations <= 50_000,
  palette <= 10 elements), refuses beyond caps with a typed message.
- `campaign_suggest(campaign_path, n<=10, strategy)`: operates on a user-supplied file.
Typed errors: each tool names the exact extra when its capability is missing
(`pip install "hea-bench[properties]"` etc). `about()` gains the new capability list
with availability booleans. Acceptance: tools import and error cleanly with no extras;
full function-level tests. Commit: `Extend the MCP surface to corpus, properties,
applicability, design, and campaigns`.

---

## Phase 8: Ceramics breadth (interfaces locked; elaborate after a research pass)

**Files:** Create `src/hea_bench/ceramics/{__init__,carbides,nitrides,borides,_data}.py`,
`docs/ceramics-corpus-card.md` (per-class sections), tests `tests/test_ceramics.py`.
README/AGENTS/CHANGELOG.

Committed decisions: follow the oxides API shape (`describe_rock_salt_carbide(metals)`,
`describe_rock_salt_nitride(metals)`, `describe_diboride(metals)` returning one dict:
normalized metal sublattice, radii used, descriptors, verdicts, warnings); descriptors
are composition-only (metal-sublattice configurational entropy, size disorder with a
cited radius set appropriate to the class, VEC with cited windows where the literature
gives one); the doc and docstrings state plainly that DFT-backed metrics (entropy
forming ability, disordered enthalpy-entropy descriptors) cannot be reproduced
composition-only and no parity is claimed; any dataset consolidation happens only for a
source with a verified license, with its own corpus card section, and no benchmark task
is built on a dataset too small to support one. Research pass at execution confirms:
radius sets, VEC windows with citations, candidate licensed datasets.
Commit: `Extend the calculator to high-entropy carbides, nitrides, and borides`.

---

## Cross-cutting acceptance checklist (run before every phase commit)

1. `python -m pytest tests/ -q` green; `ruff check src tests` clean.
2. Digest tests and docs/benchmark-baselines.md untouched (git diff confirms).
3. New third-party libraries only in extras, pinned with why-comments.
4. New prediction paths return uncertainty + in_domain.
5. New datasets or tables carry provenance and license status in a card or data-module
   docstring.
6. Text sweep: no em dashes, no AI attribution, and none of the retired
   benchmark framing (`grep -rnE "leak|inflat" <changed files>` plus an
   em-dash grep; price-basis strings about tariffs are the known benign hit).
7. CHANGELOG [Unreleased] entry states capability and limitations.
8. Missing-extra paths raise the typed error naming the install.
