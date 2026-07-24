# HEA-Bench v2.1.0 — provenance UI, element expansion, descriptor expansion

Date: 2026-07-22. Status: approved scope (user set descriptor scope to
Tiers 0–2 and cross-referencing to all three senses; element scope
Tier 1+2 decided autonomously per the research report while the user
was away).

## Goal

Make the browser and desktop apps trustworthy and citable at the point
of use, and expand scientific coverage: 37 → 55 elements, six new
descriptors/criteria, and three literature maps. The desktop app is the
same `web/` bundle inside Tauri, so every UI change lands on both
surfaces automatically.

## Non-goals

- No backend, no per-result DOI minting, no accounts. Everything stays
  fully client-side.
- No Tier 3/4 descriptors (Allen-χ screens, PSFE, ε_RMS,
  Toda-Caraballo, Troparevsky, e/a maps) — later version.
- No oxide-side element changes (94-cation table is already broader).
- No change to the Zenodo integration or release automation.

## Workstream A — provenance and citability UI

Research anchors: NIST WebBook per-value source links; Materials
Project version-pinned citations; QIIME 2 provenance receipts; AFLOW
content-hash IDs; FORCE11 verifiability principle.

### A1. Provenance drawer ("click a result, see its evidence")

Every result card (alloy descriptors, Miedema panel, rule verdicts,
oxide descriptors, formability screens) gets a small ⓘ affordance.
Clicking it opens a right-side drawer (bottom sheet on narrow screens)
with five blocks:

1. **Value** — name, symbol, value, units (restating the card).
2. **Equation** — the defining formula, MathJax-typeset (MathJax is
   already vendored and loaded on the page).
3. **Inputs used** — the exact per-element numbers this descriptor
   consumed for the current composition (radii for δ, Tm for Ω, pair
   enthalpies for ΔH_mix, moduli/volumes for ΔH_el, …), each with its
   source tag (LA-4003, CRC, Pauling/WebElements set, Guo convention,
   de Boer/matminer). User-edited pair enthalpies are flagged
   "edited by you". Each element links to its row in the Data view.
4. **Interpretation** — the threshold/window with its primary citation
   (linked DOI), including the honest-limits caveats already used in
   the app (e.g. Ω instability near ΔH_mix ≈ 0).
5. **Cross-links + cite** — links to the Theory section, the Equations
   entry, and the References entries for this descriptor, plus a
   "Copy BibTeX" button for the primary source(s).

Existing behavior preserved: clicking the card value still copies the
number; the ⓘ is a separate click target.

Implementation: one static `DESCRIPTOR_PROVENANCE` registry in
`web/index.html` (id → symbol, units, LaTeX equation, input kinds,
thresholds, ref keys, theory/eq anchors). Cards carry
`data-descriptor="<id>"`. One drawer component, filled at open time
from the registry + the last computation payload.

### A2. "Cite this result" panel

A panel under the results with:

- **Result ID**: `hea-<12 hex>` = SHA-256 prefix of the canonical JSON
  of {app version, mode, normalized inputs, pair-enthalpy overrides}.
  AFLOW-style reproducible identifier, computed with WebCrypto.
- **Permalink**: existing `?comp=` URL (extended to carry kingT; oxide
  mode gets its own params if cheap, else alloy-only this version).
- **Copy citation**: formatted text citation of the paper
  (10.3390/ma19143075) + Zenodo concept DOI + version + result ID +
  "retrieved <date>"; and **Copy BibTeX** (paper + Zenodo entries,
  hand-built strings, no external library).
- **Download provenance receipt (JSON)**: QIIME-style record —
  schema id `hea-bench-receipt/1`, version, DOIs, permalink, result
  ID, inputs (composition, T, overrides), full descriptor outputs,
  rule verdicts, per-descriptor reference DOIs, data-table SHA-256s
  (build-time constants), generated date. Also "Copy JSON".

The existing oxide "Copy report (JSON)" button is upgraded to emit the
same receipt envelope.

### A3. Version + data pinning in the chrome

Calculator footer/titlebar shows `v2.1.0 · data tables <shortsha>` —
the Materials Project pattern (any screenshot self-dates). Version
string continues to come from the single source (`__init__.py`) via
the existing sync (`VERSION_HISTORY` top row / release tooling).

### A4. Data view (fifth tab): the source-data browser

New top-level view "Data" next to Calculator/Theory/Equations/Refs:

- **Element table**: all 55 elements × (radius, Tm, VEC, χ), each
  column with its convention header and source; per-element flag notes
  (e.g. Yb divalent, U valence choice, Ge covalent-scale radius);
  a cross-check column showing the second-source value where one
  exists (Miracle & Senkov 2017 Table 3, CRC), with disagreements
  shown honestly (including the three M&S lanthanide misprints).
  Searchable/sortable. Rows addressable by anchor (#data-El).
- **Pair-enthalpy lookup**: two element pickers → ΔH_AB with the de
  Boer 1988 / Takeuchi-Inoue / matminer provenance line.
- **Data files**: names, SHA-256, vendoring date, upstream links
  (OSTI LA-4003, matminer files), licenses.
- **Coverage matrix**: which features each element supports (core
  descriptors vs Miedema decomposition vs ΔH_el) so partial coverage
  is explicit instead of silent.

Sources for the per-element table live in Python
(`descriptors/data/provenance.py`, new) and are synced to JS by the
existing generator pattern, so Python stays the single source of truth.

### A5. Machine-readable citability

- JSON-LD on the page gains `variableMeasured` (descriptor list) and
  updated counts; GSC tag untouched.
- CITATION.cff already present; no change needed beyond version (the
  release bot handles version fields).

## Workstream B — element expansion (37 → 55)

Radius authority: Teatum, Gschneidner & Waber, **LA-4003 (1968)**
(supersedes LA-2345; existing comments citing "Teatum & Waber 1967"
get corrected). Melting: CRC Handbook. VEC: Guo s+d convention,
lanthanides = 3. χ: Pauling (WebElements/CRC consistent set).

Tier 1 (research demand: rare-earth HEAs + Ga-HEAs): Tb Dy Ho Er Tm
Lu Nd Pr Ga. Tier 2 (flagged conventions, documented demand): Sm U Th
Yb Sr Ge Sb Bi Pb.

Values (radius pm / melting K / VEC / χ) as researched, to be
re-verified against the saved LA-4003 scan + M&S Table 3 during
implementation:

| El | r | Tm | VEC | χ | flags |
|---|---|---|---|---|---|
| Tb | 178.3 | 1629 | 3 | 1.10 | χ non-monotonic vs Gd/Dy, as printed |
| Dy | 177.5 | 1685 | 3 | 1.22 | |
| Ho | 176.7 | 1747 | 3 | 1.23 | |
| Er | 175.8 | 1802 | 3 | 1.24 | |
| Tm | 174.7 | 1818 | 3 | 1.25 | M&S prints 156 (misprint), note |
| Lu | 173.5 | 1936 | 3 | 1.27 | |
| Nd | 182.2 | 1289 | 3 | 1.14 | M&S prints 164 (misprint), note |
| Pr | 182.8 | 1204 | 3 | 1.13 | M&S prints 165 (misprint), note |
| Ga | 135.3 | 302.91 | 3 | 1.81 | radius spread 135.3/139.2/141 → LA-4003, note alternatives |
| Sm | 180.2 | 1345 | 3 | 1.17 | |
| U | 154.3 | 1408 | 6 | 1.38 | VEC 6 = Zachariasen metallic valence; strict s+d alternative 3 documented |
| Th | 179.8 | 2023 | 4 | 1.30 | |
| Yb | 193.9 | 1097 | 2 | 1.10 | divalent metal: radius AND VEC divalent for internal consistency; M&S VEC 3 alternative documented; χ approximate |
| Sr | 215.1 | 1050 | 2 | 0.95 | HE-BMG (SrCaYbMgZn) demand |
| Ge | 124 | 1211.40 | 4 | 2.01 | covalent-scale radius to match Si=111 convention; LA-4003 CN12 equiv 137.8 noted |
| Sb | 157.1 | 903.78 | 5 | 2.05 | LA-4003 bond-number conversion; covalent 145 noted |
| Bi | 168.9 | 544.55 | 5 | 2.02 | LA-4003; T-I-style ~170, M&S 160 noted |
| Pb | 175.0 | 600.61 | 4 | 2.33 | χ is the revised Pauling value (older 1.87 noted) |

Melting-point values in the table are provisional to ±few K; the
implementation step re-verifies each against the CRC-consistent set
and the final number wins over this table.

Excluded (with reasons recorded in `elemental.py`'s docstring): Tc
(modeling-only demand), alkalis/Ba (no HEA literature, radius
convention clash), Eu/Pm (data gaps), Cd/Tl/Hg/As/P (no metallic-HEA
usage or pathological mp), B/C/H/N (existing policy), Po/Pa/At.

Knock-ons: `_sync_js_tables.py` regenerates DEFAULT_ELEMENT_DATA (55)
and PAIR_ENTHALPIES (C(55,2) = 1485, all present in the vendored
75-element table); MIEDEMA_PARAMS + ELEMENT_EXTENDED tables extended
from `miedema_parameters.csv` (all 18 covered — CSV's
`compressibility` column actually holds bulk modulus in GPa, verified
Fe = 168.3); parity fixtures regenerated; every hard-coded "37" /
"666" in copy, docs, JSON-LD, llms.txt updated to 55 / 1485.

## Workstream C — descriptors, criteria, maps (Tiers 0–2)

New descriptors (Python module + JS core + cards + provenance entries
+ theory/equations/refs sections + tests, each):

1. **Λ (Singh 2014)** = ΔS_mix/δ² (δ in %). Bands: >0.96 single SS,
   0.24–0.96 SS+compounds, <0.24 compounds.
   DOI 10.1016/j.intermet.2014.04.019.
2. **γ (Wang 2015)** solid-angle packing ratio; SS when γ < 1.175.
   DOI 10.1016/j.scriptamat.2014.09.010. Equation re-derived from the
   paper at implementation time.
3. **κ (Senkov-Miracle 2016)** temperature-explicit SS-vs-IM
   criterion: k₁ = ΔH_IM/ΔH_mix vs k₁^cr(T); ΔH_IM = most negative
   Miedema compound enthalpy over the alloy's binaries (computed with
   machinery we already have). Uses the existing annealing-temperature
   input (shared with King Φ). DOI 10.1016/j.jallcom.2015.10.279.
   Exact equations verified from the saved Andreoli PDF (which
   restates them) + abstract cross-check.
4. **ΔH_el (Andreoli 2019)** elastic-strain energy criterion,
   Eqs. 9–10 of DOI 10.1016/j.mtla.2019.100222 (PDF saved locally):
   ΔH_el = Σ cᵢBᵢ(Vᵢ−V̄)²/(2Vᵢ), V̄ = ΣcᵢBᵢVᵢ/ΣcᵢBᵢ. B in GPa, V in
   cm³/mol → kJ/mol directly. Windows: fcc ≤ 6.05, bcc 6.05–22,
   >22 BMG/IM. New Python loader for `miedema_parameters.csv`.
5. **σ-phase window (Tsai 2013)**: flag when (Cr or V present) and
   6.88 ≤ VEC ≤ 7.84. DOI 10.1080/21663831.2013.831382.
6. **RHEA ductility (Sheikh 2016)**: for BCC-band alloys, VEC < 4.5
   intrinsically ductile / ≥ 4.6 brittle.
   DOI 10.1063/1.4966659.

Rules panel: κ, σ-window, ductility join the existing verdict cards
with window + margin, same style. Λ, γ, ΔH_el get descriptor cards
with band interpretation in the drawer.

**Maps (Tier 0)** — a "Maps" panel in results, three inline SVGs,
no charting library, alloy point plotted, regions labeled, each map
captioned with its citation and clickable into the drawer:

- δ–ΔH_mix (Zhang 2008 SS window; Guo-Liu 2011 SS/BMG regions).
- Ω–δ (Yang-Zhang 2012 quadrant, Ω ≥ 1.1 & δ ≤ 6.6 %).
- VEC strip (Guo 2011 FCC/duplex/BCC bands + Tsai σ window overlay +
  Sheikh 4.5 ductility line).

The dataviz skill is consulted before the SVG work; visual language
must match the existing app (CSS variables, light/dark).

**Cross-checks**: the rules panel gains a one-line reminder that the
canonical practice is to read δ + ΔH_mix + Ω jointly and VEC only
after an SS verdict (Pickering & Jones 2016), with links.

## Workstream D — cross-referencing infrastructure

- References view: every bibliography entry gets a stable
  `id="ref-<key>"`; new entries added (Singh 2014, Wang 2015,
  Senkov-Miracle 2016, Andreoli 2019, Tsai 2013, Sheikh 2016, Zhang
  2008, Guo-Liu 2011 PNSMI, Pickering-Jones 2016, Teatum-Gschneidner-
  Waber LA-4003 1968, Miracle-Senkov 2017, Gschneidner 1966). All
  entries show DOIs/links.
- Theory view: new sections (Λ/γ; κ; ΔH_el; phase-selection additions
  fold into §12's family) numbered continuously; Equations view gains
  the new formulas.
- Drawer links wire card → theory → equations → refs; Data view rows
  anchor per element; theory sections link back to the calculator.

## Python / CLI / MCP surfaces

- `descriptors/`: new modules `singh_lambda.py`, `wang_gamma.py`,
  `elastic.py` (ΔH_el + CSV loader in `data/`), κ lives with the
  Miedema/rules machinery; `rules/`: `tsai_sigma.py`,
  `sheikh_ductility.py`, `senkov_kappa.py`. Exports, CLI table
  columns, and the MCP descriptor/rule outputs pick the new values up
  through the same library calls; the MCP provenance/info tool's
  reference list gains the new DOIs.
- Constants: new thresholds in `constants.py` mirrored to JS.

## Testing

- Unit tests per new descriptor with literature-pinned values
  (Andreoli's tabulated ΔH_el examples from the saved PDF; Singh's Λ
  for canonical alloys; Wang's γ threshold cases; Tsai window
  positive/negative alloys; κ worked example from the paper).
- Element-data tests: all 18 new entries spot-checked against LA-4003
  (values re-read from the saved scan during implementation);
  count/pair-coverage assertions move 37→55, 666→1485.
- Parity: `_sync_js_tables.py` + `_build_parity_cases.py` regenerated;
  `test_web_parity.py` green (node runner).
- UI: receipt JSON schema check + result-ID determinism test in the
  parity harness if cheap; otherwise manual smoke via the run skill.
- Full pytest suite green before push; code review pass
  (user-requested) before push.

## Release

One push to main containing everything, with
`python tools/version.py --set 2.1.0` inside it and an
`## [Unreleased]` changelog section for the bot to promote. Then
`gh run list` until Auto release is green; trust verify-live for the
site (CDN cache ~10 min). No Zenodo-side actions ever.

## Risks / mitigations

- **Data-entry errors in 18 × 4 values** — every value re-verified
  against the saved primary PDFs at implementation, spot tests, and
  the Data view's cross-check column makes residual disagreement
  visible rather than hidden.
- **κ/γ equation transcription** — equations verified against the
  papers (saved PDFs where available) before coding; literature-pinned
  tests.
- **ELEMENT_EXTENDED/MIEDEMA_PARAMS divergence from CSV** — the JS
  tables become generated-from-CSV (same pattern as element tables) so
  hand-curated drift can't recur; where the existing hand values
  disagree with the CSV beyond rounding, the CSV wins and the change
  is noted in the changelog.
- **index.html keeps growing (9.4k lines)** — new UI code is added as
  clearly-delimited sections (registry, drawer, data view) with
  generated blocks marked BEGIN/END GENERATED like existing ones;
  splitting files is out of scope this version.
