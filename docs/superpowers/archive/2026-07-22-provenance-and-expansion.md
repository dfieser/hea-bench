# HEA-Bench v2.1.0 Implementation Plan — provenance UI, 55 elements, Tier 0-2 descriptors

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship v2.1.0: point-of-use provenance/citability in the web+desktop app, element table 37→55, six new descriptors/criteria, three literature maps, full cross-referencing.

**Architecture:** Python stays the single source of truth for all data and physics; generator scripts in `tests/data/` rewrite generated blocks in the JS core; parity fixtures lock the two implementations together. UI work happens once in `web/index.html` and reaches the desktop via the Tauri wrapper unchanged.

**Tech stack:** Python 3.10+ (no new deps), vanilla JS (ES5-style core, no libraries), MathJax (already vendored), inline SVG for maps, WebCrypto for result IDs.

## Global constraints

- Spec: `docs/superpowers/specs/2026-07-22-provenance-and-expansion-design.md` — values and conventions there are final (radius authority LA-4003 1968; CRC melting; Guo VEC, lanthanides 3, Yb 2, U 6; Pauling χ; Ge 124 covalent-scale).
- Data corrections locked during verification: Tb melting 1632 K, Ho 1745 K (CRC), Th 2023 K (CRC; note 2115 K spread in cross-check notes).
- κ: k₂ = 0.6 (Senkov-Miracle's ΔS_IM = 0.6·ΔS_mix); k₁^cr = 1 + (1−k₂)·T·ΔS_mix/(1000·|ΔH_mix|) with ΔH in kJ/mol, S in J/(mol·K); ΔH_IM := `delta_g_max` (documented approximation, same as King Φ). Verdict from direct Gibbs comparison, valid for all signs of ΔH.
- γ: ω(r_c) = 1 − √(((r_c+r̄)² − r̄²)/(r_c+r̄)²); γ = ω_S/ω_L; SS when γ < 1.175. Equal radii ⇒ γ = 1 exactly.
- Λ = ΔS_mix / δ² with δ in percent; bands 0.96 / 0.24.
- ΔH_el = Σ cᵢBᵢ(Vᵢ−V̄)²/(2Vᵢ), V̄ = ΣcᵢBᵢVᵢ/ΣcᵢBᵢ; B in GPa, V in cm³/mol ⇒ kJ/mol. Windows 6.05 / 22 kJ/mol (fcc / bcc / glassy-IM). B comes from `miedema_parameters.csv` column `compressibility` (it holds bulk modulus in GPa — verified Fe 168.3, Al 72.18).
- σ window (Tsai 2013): flag iff (Cr or V present) and 6.88 ≤ VEC ≤ 7.84. Ductility (Sheikh 2016): BCC-band alloys, VEC < 4.5 ductile, ≥ 4.6 brittle, 4.5–4.6 borderline.
- No Claude co-author / contributor credit in any commit or file.
- Never touch Zenodo integration. One release push at the end with `python tools/version.py --set 2.1.0`.
- All shell test commands run from repo root with `PYTHONPATH=src` (or `python -m pytest`, which uses `pyproject.toml` config).
- Existing card click = copy-to-clipboard must keep working; ⓘ is a separate target that must `stopPropagation()`.
- All new UI copy: no em dashes, plain scientific prose, honest-limits tone matching existing app copy.

## Phase 1 — Python data

### Task 1: 18 new elements in `elemental.py`

**Files:** Modify `src/hea_bench/descriptors/data/elemental.py`; Test `tests/test_element_expansion.py` (new)

- [ ] Write failing tests: count == 55; exact (radius_pm, melting_K, valence, electronegativity) for all 18 new rows per the table below; `covered_elements()` includes them; existing 37 unchanged (spot Al/Fe/Y).

| El | radius_pm | melting_K | valence | chi |
|---|---|---|---|---|
| Bi | 168.9 | 544.55 | 5 | 2.02 |
| Dy | 177.5 | 1685.0 | 3 | 1.22 |
| Er | 175.8 | 1802.0 | 3 | 1.24 |
| Ga | 135.3 | 302.91 | 3 | 1.81 |
| Ge | 124.0 | 1211.40 | 4 | 2.01 |
| Ho | 176.7 | 1745.0 | 3 | 1.23 |
| Lu | 173.5 | 1936.0 | 3 | 1.27 |
| Nd | 182.2 | 1289.0 | 3 | 1.14 |
| Pb | 175.0 | 600.61 | 4 | 2.33 |
| Pr | 182.8 | 1204.0 | 3 | 1.13 |
| Sb | 157.1 | 903.78 | 5 | 2.05 |
| Sm | 180.2 | 1345.0 | 3 | 1.17 |
| Sr | 215.1 | 1050.0 | 2 | 0.95 |
| Tb | 178.3 | 1632.0 | 3 | 1.10 |
| Th | 179.8 | 2023.0 | 4 | 1.30 |
| Tm | 174.7 | 1818.0 | 3 | 1.25 |
| U  | 154.3 | 1408.0 | 6 | 1.38 |
| Yb | 193.9 | 1097.0 | 2 | 1.10 |

- [ ] Add the 18 rows alphabetically with per-element source comments (radius LA-4003 Table I read 2026-07-22; melting CRC; VEC convention note; χ Pauling set; flags: Yb divalent, U Zachariasen 6 vs s+d 3, Ge covalent-scale vs LA-4003 137.8, Ga/Sb/Bi radius spreads, Th melting spread, M&S misprints for Pr/Nd/Tm radii).
- [ ] Update module docstring: v2.1 expansion paragraph; correct "Teatum & Waber 1967" to "Teatum, Gschneidner & Waber, LA-4003 (1968), supersedes LA-2345"; note B/C/As/P/alkali/Hg/Cd/Tl/Eu/Pm/Po/Pa/At/Tc exclusions with one-line reasons.
- [ ] Run new tests + `python -m pytest tests/ -k "element or elemental" -q`; fix count assertions elsewhere that pin 37 (grep `37` in tests/). Commit.

### Task 2: mechanics loader (`miedema_parameters.csv` → Python)

**Files:** Create `src/hea_bench/descriptors/data/mechanics.py`; Test `tests/test_mechanics_data.py`
**Produces:** `mechanics(symbol) -> Mechanics(molar_volume_cm3, bulk_modulus_gpa, shear_modulus_gpa) | None`, `covered: frozenset[str]`

- [ ] Failing tests: Fe → (7.09, 168.3, 81.52); Al → (10.0, 72.18, 26.59); Sr → (33.93, 11.62, 5.229); returns None for 'Xx'; all 55 ELEMENTAL_DATA elements covered (loop assertion).
- [ ] Implement csv loader (stdlib csv, cached module-level dict), documenting that the upstream column named `compressibility` holds the bulk modulus in GPa (matminer Miedema.csv convention) and `molar_volume` is cm³/mol. Skip rows with 0.0 moduli by storing them as-is; ΔH_el treats missing/zero B or V as "not computable".
- [ ] Tests pass. Commit.

### Task 3: provenance registry (Python SSOT)

**Files:** Create `src/hea_bench/descriptors/data/provenance.py`; Test `tests/test_provenance_data.py`
**Produces:** `ELEMENT_SOURCES: dict[str, ElementSources]` (per-element: radius_note, crosscheck_radius_pm (M&S Table 3 or None), crosscheck_note, flags list); `PROPERTY_SOURCES` (column-level source statements); `REFERENCES: dict[str, Ref]` (key → authors, title, journal, year, doi/url) covering: yeh2004? (keep existing refs untouched) new keys `singh2014, wang2015, senkov2016, andreoli2019, tsai2013, sheikh2016, zhang2008, guo2011pnsmi, pickering2016, la4003, ms2017, gschneidner1966, deboer1988, takeuchi2005, matminer2018, crc, pauling1960, guo2011vec, yang2012, king2016, ye2015, zhang2012delta?` — include every DOI shown in the Data view and drawer.
- [ ] Failing tests: every element in ELEMENTAL_DATA has an ELEMENT_SOURCES entry; every crosscheck value that exists differs or agrees within stated tolerance fields; every Ref has doi or url; specific spot checks (Tm crosscheck note mentions M&S misprint 156; Th note mentions 2115 K spread; U flags mention valence alternative 3).
- [ ] Implement with the researched content. M&S Table 3 crosscheck radii (pm): Ga 139.2, Ge 124, Sr 215.2, Pr 165 (misprint), Nd 164 (misprint), Sm 181, Tb 178.14, Dy 177.4, Ho 176.61, Er 175.58, Tm 156 (misprint), Yb 170, Lu 173.49, Sb 145, Bi 160, Pb 174.97; U/Th absent from M&S (crosscheck None, note LA-4003-only).
- [ ] Tests pass. Commit.

## Phase 2 — Python descriptors and rules (TDD each)

### Task 4: Λ (Singh 2014)

**Files:** Create `src/hea_bench/descriptors/lam.py`; Modify `src/hea_bench/descriptors/__init__.py`, `src/hea_bench/constants.py`; Test `tests/test_lambda.py`
**Produces:** `singh_lambda(composition) -> float` (J·mol⁻¹·K⁻¹·%⁻²); constants `SINGH_LAMBDA_SS = 0.96`, `SINGH_LAMBDA_IM = 0.24`.

- [ ] Failing test: for equiatomic CoCrFeMnNi, `singh_lambda == smix/delta**2` computed from the library's own smix and delta (structural identity test), and a pinned value asserted to 6 decimals after first computation run (fill in during implementation, expected ≈ 13.3806/δ² with our δ). Also: binary equal-radius alloy (CuNi? radii differ; use synthetic via monkeypatched table — simpler: assert ValueError when delta == 0 is impossible with real elements; use Ag-Au, both 144.0 pm → δ=0 → function returns math.inf and a test asserts that documented behavior).
- [ ] Implement: `return smix(c) / d**2` with `d = delta(c)` (percent); if `d == 0` return `math.inf` (documented: zero mismatch means unbounded Λ, trivially SS).
- [ ] Tests pass. Commit.

### Task 5: γ (Wang 2015)

**Files:** Create `src/hea_bench/descriptors/gamma.py`; Modify exports+constants (`WANG_GAMMA_THRESHOLD = 1.175`); Test `tests/test_gamma.py`
**Produces:** `wang_gamma(composition) -> float`

- [ ] Failing tests: Ag-Au (both r=144) → exactly 1.0; hand case: two elements r=100, r=200 pm, equiatomic → r̄=150; ω_S = 1−√(((100+150)²−150²)/(100+150)²) = 1−√(40000/62500) = 1−0.8 = 0.2; ω_L = 1−√(((200+150)²−150²)/(200+150)²) = 1−√(100000/122500) = 1−0.903508... = 0.0964915...; γ = 2.072719... (assert approx, rel 1e-9, via monkeypatched ELEMENTAL_DATA or a private `_gamma_from_radii(radii, fractions)` helper — expose that helper for testability); Cantor CoCrFeMnNi pinned regression (fill exact after first run; must be < 1.175).
- [ ] Implement with `_omega(r_c, r_bar)` helper; r̄ = Σcᵢrᵢ.
- [ ] Tests pass. Commit.

### Task 6: ΔH_el (Andreoli 2019)

**Files:** Create `src/hea_bench/descriptors/elastic.py`; exports+constants (`ANDREOLI_FCC_MAX = 6.05`, `ANDREOLI_BCC_MAX = 22.0`); Test `tests/test_elastic.py`
**Produces:** `h_elastic(composition) -> float | None` (kJ/mol; None when any element lacks B or V)

- [ ] Failing tests: synthetic two-element hand case B=(100,200) GPa, V=(10,8) cm³/mol equiatomic → V̄ = (0.5·100·10+0.5·200·8)/(0.5·100+0.5·200) = 26/3 ≈ 8.666667; ΔH_el = 0.5·100·(10−8.6667)²/(2·10) + 0.5·200·(8−8.6667)²/(2·8) = 4.444444 + 2.777778 = 7.222222 kJ/mol (helper `_h_elastic_from_tables(fractions, B, V)` exposed for this); Cantor regression pinned after first run and asserted < 6.05 with a comment citing Andreoli's own 2.98 kJ/mol (different B/V table, same fcc window expected); returns None for a composition including an element with missing mechanics data (use monkeypatch).
- [ ] Implement using `mechanics()` from Task 2.
- [ ] Tests pass. Commit.

### Task 7: κ (Senkov-Miracle 2016)

**Files:** Create `src/hea_bench/rules/senkov_kappa.py`; Modify `src/hea_bench/rules/__init__.py`, constants (`SENKOV_K2 = 0.6`); Test `tests/test_kappa.py`
**Produces:** `predict(composition, temperature) -> KappaPrediction` dataclass with fields `k1: float | None`, `k1_cr: float | None`, `g_ss_kj: float`, `g_im_kj: float`, `ss_favored: bool`, `temperature_K: float`, plus `.verdict` property ("SS" / "IM").

- [ ] Failing tests: hand case with monkeypatched enthalpies: ΔH_ss = −10 kJ/mol, ΔH_IM = −20, S = 13.38 J/mol·K, T = 1000 K → k1 = 2.0; k1_cr = 1 + 0.4·1000·13.38/(1000·10) = 1.5352; k1 > k1_cr ⇒ IM favored; direct-G check: G_ss = −10−13.38 = −23.38; G_im = −20−0.6·13.38 = −28.028 ⇒ IM ✓ consistent. Second case T = 3000 K → k1_cr = 2.6056 ⇒ SS; G check consistent. Edge: ΔH_ss = +2 (positive) → k1/k1_cr None, verdict from G only. Real-alloy regression: CoCrFeMnNi at 1000 K pinned after first run.
- [ ] Implement using `mixing_enthalpy`, `smix`, `delta_g_max` (the ΔH_IM approximation — copy the approximation-note docstring style from `delta_g_max`).
- [ ] Tests pass. Commit.

### Task 8: σ window + ductility rules

**Files:** Create `src/hea_bench/rules/tsai_sigma.py`, `src/hea_bench/rules/sheikh_ductility.py`; constants (`TSAI_SIGMA_VEC_MIN = 6.88`, `TSAI_SIGMA_VEC_MAX = 7.84`, `SHEIKH_DUCTILE_VEC = 4.5`, `SHEIKH_BRITTLE_VEC = 4.6`); Test `tests/test_sigma_ductility.py`
**Produces:** `tsai_sigma.predict(composition) -> SigmaPrediction(applies: bool, in_window: bool, vec: float, verdict: str)`; `sheikh_ductility.predict(composition) -> DuctilityPrediction(vec, verdict)` with verdict in {"ductile","brittle","borderline"} (borderline for 4.5 ≤ VEC < 4.6).

- [ ] Failing tests: AlCoCrFeNi (VEC = (3+9+6+8+10)/5 = 7.2, has Cr) → applies, in_window, verdict "sigma-prone"; CoCrFeMnNi (VEC 8.0, has Cr) → applies, not in window; CuNi (no Cr/V) → not applies; HfNbTaTiZr (VEC (4+5+5+4+4)/5 = 4.4) → "ductile"; MoNbTaW (VEC (6+5+5+6)/4 = 5.5) → "brittle"; synthetic VEC 4.55 → "borderline".
- [ ] Implement (VEC via existing `vec()`).
- [ ] Tests pass. Commit.

### Task 9: surface wiring (package exports, CLI, MCP)

**Files:** Modify `src/hea_bench/__init__.py`, `src/hea_bench/cli.py`, `src/hea_bench/mcp_server.py`; Tests: extend `tests/test_cli.py`-equivalent (locate existing CLI tests) + MCP tests

- [ ] Inspect how cli.py builds its descriptor table and mcp_server.py builds descriptor/rule outputs; add Λ, γ, ΔH_el to descriptor outputs (ΔH_el nullable) and κ/σ/ductility to rule outputs (κ takes the same temperature argument King Φ uses; document default = Tm).
- [ ] MCP info/provenance tool: add the six new primary references with DOIs.
- [ ] Update failing/extended tests; run full `python -m pytest -q`. Commit.

## Phase 3 — JS core + parity

### Task 10: regenerate + extend generated tables

**Files:** Modify `tests/data/_sync_js_tables.py`, `web/hea-calculator-core.js`

- [ ] Extend the sync script with a third generated block `ELEMENT_MECHANICS` (from `mechanics()`, all covered elements, `{ B: <GPa>, Vm: <cm3/mol> }`; shear not needed by core) with BEGIN/END GENERATED markers, and update the two existing block comments' counts automatically (they already are).
- [ ] Run `PYTHONPATH=src python tests/data/_sync_js_tables.py` → DEFAULT_ELEMENT_DATA 55 rows, PAIR_ENTHALPIES 1485 rows, ELEMENT_MECHANICS new. Commit the regenerated core + script.

### Task 11: new physics in the JS core + parity fixtures

**Files:** Modify `web/hea-calculator-core.js`, `tests/data/_build_parity_cases.py`, `tests/data/web_parity_cases.json`, `tests/test_web_parity.py`

- [ ] Port Λ, γ, ΔH_el, κ, σ, ductility into the core with identical math and threshold constants; expose in `computeDescriptors` result (keys: `Lambda_singh`, `gamma_wang`, `H_elastic`, nullable) and `rulePredictionsFromDescriptors`/new `kappaPrediction(descriptors, T)` mirroring Python signatures; export constants.
- [ ] Extend `_build_parity_cases.py` compositions to include new-element alloys (add: YGdTbDyHo, GdTbDyHoEr, UNbZrTiMo equiatomic, SnPbInBiSb, SrCaYbMgZn, CoCrFeNiGa, CoCrFeNiGe) and the new descriptor/rule outputs; regenerate `web_parity_cases.json`.
- [ ] `python -m pytest tests/test_web_parity.py -q` green (node available — verify with `node --version`; if absent, install note: parity test skips? check its skip logic — must NOT skip silently; run it and confirm it executed).
- [ ] Full suite green. Commit.

## Phase 4 — UI (web/index.html; desktop inherits)

### Task 12: maps panel (consult dataviz skill first)

**Files:** Modify `web/index.html` (new panel after `#miedema-panel`), `web/hea-calculator-core.js` only if region constants are needed (keep regions in index.html; they are presentation)

- [ ] New `<section class="panel mode-alloy" id="maps-panel">` with three inline SVGs built by JS functions `renderZhangMap(d)`, `renderOmegaDeltaMap(d)`, `renderVecStrip(d)`: axes with ticks and unit labels, literature region rectangles/bands (Zhang 2008 SS: ΔH −15..5 kJ/mol × δ 1..6 %; Guo-Liu 2011 SS: −22..7 × ≤8.5, BMG region −49..−5.5 × ≥9 per Guo-Liu Fig; Ω–δ: Ω ≥ 1.1 & δ ≤ 6.6 quadrant, log-y for Ω 0.01..100; VEC strip 0..12 with BCC <6.87, duplex 6.87..8, FCC ≥8 bands + σ window 6.88..7.84 overlay + 4.5 ductility tick), the current alloy plotted as a labeled point, caption line with citation links into refs view. Colors via existing CSS variables (light/dark safe), region fills at low opacity, all text ≥ 11px, `role="img"` + `aria-label`.
- [ ] Wire into `renderResults` (alloy mode only; hidden when no payload). Off-scale points clamp to the plot edge with an open marker + "off scale" note in the caption.
- [ ] Smoke-test in browser via the run skill; screenshot check both themes. Commit.

### Task 13: provenance drawer + ⓘ affordances

**Files:** Modify `web/index.html`

- [ ] Add `DESCRIPTOR_PROVENANCE` registry object: one entry per card id (`smix, delta, tm, hmix, vec, omega, delta_chi, mean_chi, s_excess, dg_ss, dg_max, phi_king, phi_ye, lambda_singh, gamma_wang, h_elastic, kappa, h_compound, h_ss, h_am, h_elastic_ss_term..., sigma_window, ductility, guo_vec, zhang_delta, yeh_smix, yang_omega, king_phi_rule, ye_phi_rule` + oxide ids `s_config, charge_balance, delta_r, tolerance_t, radius_ratio...` matching existing oxide cards) with: `symbolHtml`, `units`, `eqTex` (display-mode LaTeX), `inputs` (list of {kind: 'element-prop'|'pairs'|'mechanics'|'constant'|'derived', prop, sourceKey}), `interpretation` (threshold text), `refKeys` [], `theoryAnchor`, `eqAnchor`.
- [ ] Drawer markup: `<aside id="prov-drawer" aria-modal="false" role="dialog">` fixed right, translating in; close button, Esc handler, focus management; sections Value / Equation / Inputs used / Interpretation / Cite & links. Inputs table built from the LAST payload (store `lastAlloyPayload` / `lastOxideReport` refs) + `DEFAULT_ELEMENT_DATA` + `ELEMENT_SOURCES_JS` (Task 15 generated) + pair overrides map (flag "edited by you" rows). MathJax: `MathJax.typesetPromise([drawerBody])` on open, guarded if MathJax absent.
- [ ] Cards: add `<button class="prov-btn" data-prov="<id>" aria-label="Provenance for …">ⓘ</button>` into the card header in `renderResults`, miedema cards, rule cards, oxide render paths; click → `openProvenance(id)`; `stopPropagation` so copy still works; also make rule verdict cards carry data-prov.
- [ ] "Copy BibTeX" in drawer: builds BibTeX from REFERENCES_JS for the entry's refKeys.
- [ ] Browser smoke: open drawer for every card id in both modes (temporary dev loop in console), no console errors. Commit.

### Task 14: cite-this-result panel + receipt

**Files:** Modify `web/index.html`

- [ ] Panel under results (alloy) and under oxide results: shows version (from existing VERSION_HISTORY source — locate; else inject constant synced by release tooling — MUST reuse whatever mechanism keeps version current today; investigate `tools/autorelease.py` + grep index.html for the current version string pattern before coding), result ID `hea-xxxxxxxxxxxx` computed by `resultId(payloadCanonicalJson)` via `crypto.subtle.digest('SHA-256', …)` of `JSON.stringify({v: appVersion, mode, inputs, overrides})` with sorted keys; permalink (extend `shareUrl()` — check existing fn near line 8340 — to include kingT; add oxide `?oxide=` params only if the existing oxide state serializes in <30 lines, else skip with code comment); buttons: Copy citation (text), Copy BibTeX, Copy receipt JSON, Download receipt.
- [ ] Receipt builder `buildReceipt()` → `{schema:"hea-bench-receipt/1", app:{name, version, paperDoi:"10.3390/ma19143075", conceptDoi:"10.5281/zenodo.20346287"}, resultId, permalink, generated: ISO date, inputs:{...}, outputs:{descriptors, rules}, references:[{key, doi}...], data:{elementTable:"LA-4003/CRC/Pauling/Guo, see Data view", pairTable:"de Boer 1988 via matminer", shas:{...}}}` — shas from generated constants (Task 15).
- [ ] Wire oxide "Copy report (JSON)" to emit the same envelope (keep old top-level keys under `outputs` for backward compat).
- [ ] Update the citation copy in the landing "Cite HEA-Bench" section to mention result IDs/receipts one line. Browser smoke: WebCrypto path needs https or localhost — guard with fallback (simple FNV-1a hex, labeled "id (fallback)") for file:// use in the desktop webview IF `crypto.subtle` undefined there; verify in Tauri build that subtle exists (tauri serves via custom protocol — test; keep fallback regardless).
- [ ] Commit.

### Task 15: Data view (fifth tab) + generated provenance tables

**Files:** Create `tests/data/_sync_js_provenance.py`; Modify `web/index.html`

- [ ] Sync script emits into index.html a `BEGIN GENERATED: ELEMENT_SOURCES_JS / REFERENCES_JS / DATA_FILE_SHAS` block from Python provenance.py + hashlib SHA-256 of the three data files (pair_enthalpies.tsv, miedema_parameters.csv, elemental table module — hash the .py file) + counts. Idempotent regeneration like _sync_js_tables.py.
- [ ] New tab button `data-view="data"` labeled "Data" in `.titlebar__tabs` + `<div class="view" data-view-panel="data">`: (a) element table (sortable by symbol/property; simple text filter) with columns El, r(pm), Tm(K), VEC, χ, source note icon → expands row with full notes/flags + M&S crosscheck value where present marked agree/differ; row anchors `id="data-<El>"`; (b) pair lookup: two `<select>`s + output line with provenance sentence; (c) data files card: names, SHAs, vendor date, upstream links, licenses; (d) coverage matrix: for each element, ✓ for core descriptors (always), Miedema decomposition (MIEDEMA_PARAMS covers it?), mechanics/ΔH_el (ELEMENT_MECHANICS) — computed from the tables at render time, honest ✗ elsewhere.
- [ ] Hash routing: `#data` and `#data-<El>` open the view (mirror existing theory hash handling near line 9278).
- [ ] Regenerate, browser smoke, commit.

### Task 16: version badge + JSON-LD counts

**Files:** Modify `web/index.html`

- [ ] Footer/titlebar badge `vX.Y.Z · data <shortsha of concatenated table SHAs>` visible in calculator view; version sourced the same way the page displays its current version today (investigate first; reuse).
- [ ] JSON-LD: update description counts 37→55, 666→1485, add `variableMeasured` array of descriptor names; do not touch GSC tag. Landing stats strip + "What it computes" copy updated (grep `37` and `666` through index.html, README.md, web/README.md, llms.txt).
- [ ] Commit.

## Phase 5 — theory, equations, references, cross-links

### Task 17: content sections + anchors

**Files:** Modify `web/index.html`

- [ ] References view: wrap each existing bibliography entry with `id="ref-<key>"` matching REFERENCES_JS keys; add new entries (Singh 2014, Wang 2015, Senkov & Miracle 2016, Andreoli 2019, Tsai 2013, Sheikh 2016, Zhang 2008, Guo & Liu 2011 PNSMI, Pickering & Jones 2016, Teatum-Gschneidner-Waber LA-4003 (OSTI link), Miracle & Senkov 2017, Gschneidner 1966) in the fitting groups with DOIs/URLs.
- [ ] Theory view: new sections after §12 (renumber or use 12a-style suffixes — decide by existing numbering pattern; keep hash ids stable for old sections): "Geometric packing parameters Λ and γ" (with the tangent-cone derivation of ω), "The Senkov-Miracle κ criterion" (derivation from ΔG inequality incl. the (1−k₂) numerator form), "Elastic-strain energy ΔH_el" (Eqs 9-10, window statistics, note our B/V table differs from Andreoli's sources), "Phase-selection maps" paragraph in the prediction section + σ/ductility windows paragraphs. Equation reference view: matching entries in group 01 (Λ, γ) and a new group for κ/ΔH_el.
- [ ] Docs-nav lists in both views updated. MathJax renders (smoke). Cross-link hrefs used by the drawer verified to resolve (`#sec-…`, `#eq-…`, `#ref-…`) — add a tiny dev-mode console check `validateProvenanceAnchors()` run under `?dev=1`.
- [ ] Commit.

### Task 18: CHANGELOG + docs

**Files:** Modify `CHANGELOG.md`, `README.md`, `AGENTS.md` (library usage: new functions), `llms.txt`, `web/README.md`, `src/hea_bench/descriptors/data/README.md` (LA-4003 correction + new-element coverage note)

- [ ] `## [Unreleased]` section: Added (six criteria, maps, provenance drawer, cite/receipt, Data view, 18 elements), Changed (counts, LA-4003 attribution fix, ELEMENT_EXTENDED→generated), Fixed (none unless found). Follow existing changelog entry style.
- [ ] Commit.

## Phase 6 — verification, review, release

### Task 19: full verification (verification-before-completion skill)

- [ ] `python -m pytest -q` — full suite green, paste summary into commit message body of a no-op? No: record in final report only.
- [ ] Parity test explicitly ran (not skipped): `python -m pytest tests/test_web_parity.py -v`.
- [ ] Literature sanity: script `PYTHONPATH=src python - <<…>>` computing for CoCrFeMnNi: δ≈3.27, ΔS 13.38, VEC 8.0, Λ>0.96, γ<1.175, ΔH_el in fcc window, σ not flagged; for AlCoCrFeNi: VEC 7.2 σ-flagged; HfNbTaTiZr ductile + ΔH_el in bcc window (Andreoli prints 11.13 with their tables; ours must land 6.05–22). Any miss → investigate before proceeding (systematic-debugging skill).
- [ ] Browser smoke via run skill: calculator (alloy+oxide), all five views, drawer on ≥6 card types, maps render both themes, receipt download, permalink round-trip, no console errors.

### Task 20: code review + fixes (user-required gate)

- [ ] Dispatch code-reviewer subagent(s) over the full diff (`git diff <base>..HEAD`), instruct: correctness of physics constants vs plan Global Constraints, unit errors, JS/Python parity risks, XSS in new innerHTML paths (element names are attacker-free but pair-editor values/user inputs flow into drawer — verify escaping), a11y of drawer/tabs, perf of maps re-render. Fix CONFIRMED findings; re-run suite.

### Task 21: release

- [ ] `python tools/version.py --set 2.1.0` (check RELEASING.md whether it also stamps changelog/tauri); commit "v2.1.0: trustworthy-and-citable release".
- [ ] Push to main. `gh run list` → watch `Auto release` green including verify-live. Do NOT hand-tag. If red: read logs, fix forward, push again (patch bump auto).
- [ ] Post-release: update memory files (project status, new conventions: LA-4003 authority, Yb VEC 2, U VEC 6, receipt schema v1).

## Self-review notes

- Spec coverage: A1→T13, A2→T14, A3→T16, A4→T15, A5→T16, B→T1-3+T10, C→T4-8+T11+T12, D→T15+T17; testing section→T19; release→T21. Gaps: none found.
- Interfaces consistent: `mechanics()` consumed by T6/T10; `delta_g_max` by T7; provenance.py consumed by T15 generator; card ids shared T13/T17 registry↔anchors with dev-mode validator.
- Deviation from skill defaults, recorded: executed inline (executing-plans) rather than subagent-per-task; rationale: single-file UI coupling + generated-block regeneration make fresh-context handoffs error-prone, and the user is away so between-task human review is unavailable either way. Code review still happens (Task 20).
