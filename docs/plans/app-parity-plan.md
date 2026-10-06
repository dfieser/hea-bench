# App feature parity plan

Status: BUILT, 2026-10-05, shipped as v2.6.0. David approved building it
and told the agent to take the recommended option on every open question
and record it here (see "Decisions" below). Rule: `hea-bench/CLAUDE.md`,
"APP PARITY IS MANDATORY". How the result works: `web/README.md`.

## Decisions (2026-10-05, recommended options)

1. Hybrid design: yes. Instant JavaScript ports for closed-form results
   (descriptors, rules, oxides, ceramics, tier A properties, the Ω
   pair-table check) and the real library in the page (Pyodide) for every
   feature that needs the corpus or scikit-learn.
2. Engine bundled, not loaded from a CDN: the site serves the pinned files
   itself and the desktop exe embeds them, so everything except the first
   dataset build works offline. The exe grew from about 14 MB to 44.8 MB.
3. In-browser download of the Peivaste file from its authors: yes, refused
   unless its SHA-256 matches the pinned file, and kept in browser storage.
4. Navigation: new Dataset, Design and Benchmark tabs, and the old Data tab
   renamed Element data.
5. One minor release, 2.6.0, rather than a patch per step.
6. MCP gaps (benchmark, phase sets, ceramics): not closed in this effort,
   which is app parity. They remain open for a follow-up and matter for
   the preprint's wording about the agent server.
7. Borg CSV inside the PyPI wheel: not in this effort (packaging, not app
   parity). Still open, see finding 2 below.

## Status by item (2026-10-05)

Done: the enforcement registry and its CI test
(`tests/test_app_parity.py`, `tests/data/app_parity.json`), the engine
and its pinned build (`tools/build_web_engine.py`), the CI `web-engine`
job, the engine build in `pages.yml` and the desktop build, the
`verify-live` engine check, the Dataset view plus the measured hardness
and density records, the predictions panel (tier A, hardness with its
interval, phase prediction sets, domain flag), the Ω pair-table check,
the Ceramics mode, the Design view (search, campaigns), the Benchmark
view (splits, digests, live baselines, upload scoring, example file,
coverage study), the phone layout of the calculator, and the library
fixes (finding 1 as `hea_bench.uncertainty.phase.predict_phase_set`,
finding 3 as batched predictions, finding 4 as a fix, finding 5 as
`hea_bench.benchmark.frozen`). Every engine feature was exercised in a
browser and inside the built Windows exe. Also done, in the release
after 2.6.1: the headless-browser test (`tests/test_app_smoke.py`, every
tab used through its UI in the CI `web-engine` job, with a parity check
that every engine feature has a step in it) and Order of work step 2
(the saved-page styles and demo cards removed from `index.html`, and the
unused MathJax bundles removed after a network check of everything the
page and the MathJax menu load).

Not done: the HEACalculator bridge (deferred by David) and the preprint
wording (step 11).

## Goal

Every user-facing library feature appears and functions in the app (the
web site built from `web/` and the desktop exe, which is the same folder in
a Tauri shell), and returns the same numbers as the library. About 99% of
users only ever open the app.

## Key finding: the app can run the real library

Spike on 2026-10-05 in the session scratchpad (Node 24, Pyodide 0.29.3,
scikit-learn 1.7.0 in the browser engine vs 1.7.2 in CPython):

| Check | Result |
|---|---|
| Unmodified `hea_bench` package imports and runs in Pyodide | yes |
| Hardness value, 90% conformal interval, domain flag for AlCoCrFeNi, CoCrFeMnNi, Al0.5CoCrCuFeNi, MoNbTaW | identical to the last bit |
| Random-forest benchmark, single-phase task, both splits | fold digests and every per-fold metric identical. Balanced accuracy 0.9405 and 0.7343 identical. Macro-F1 and MCC gaps differ by 1e-16 |
| Engine start from cache | 3.7 to 4.2 s |
| Compute speed | hardness fit 1.8 s vs 0.9 s. Full forest benchmark 57 s (one thread) vs 8.9 s (CPython, all cores) |
| Engine size (Pyodide core, numpy, scipy, scikit-learn, OpenBLAS) | 37 MB on disk, about 28 MB over the wire |

So the model-driven features do not need a JavaScript re-implementation.
The app can run the same Python code in a Web Worker, and parity holds by
construction rather than by porting.

## Recommended architecture (hybrid)

1. Keep the instant JavaScript calculator exactly as it is.
2. Port to JavaScript only the small per-composition arithmetic that must
   be instant: tier A properties (density, melting point, cost) and the
   ceramics module. This follows the existing JS-core-plus-parity-test
   pattern.
3. Run everything dataset- or model-driven on an "analysis engine": the
   real `hea_bench` package in Pyodide inside a Web Worker, loaded on first
   use with a progress bar ("Loading the analysis engine, about 28 MB, once").
4. Vendor the pinned engine (version plus SHA-256 of every file) into the
   site and the desktop bundle at build time, so the desktop works offline
   and the site does not depend on a CDN. No binaries are committed to git.

## Dataset in the app, license-compliant

The library builds the dataset on the user's machine because the Peivaste
source declares no license. The app does the same thing in the browser:

1. Borg and Pei (CC BY 4.0) ship with the site, as they ship with the
   package. Chizhevskiy (CC BY 4.0) ships for opt-in v0.2.0.
2. The browser downloads the Peivaste file from the authors' GitHub
   repository. Verified 2026-10-05: raw.githubusercontent.com answers with
   `Access-Control-Allow-Origin: *`, and the live file still matches the
   pinned SHA-256 `655a43e5...` (6,424,704 bytes).
3. The engine verifies the hash, then builds the consolidated dataset with
   the library's own code. The result must match the digest in
   `data/consolidated/v0.1.0/manifest.json`. It is cached in IndexedDB.

The site never redistributes the unlicensed file.

## Features: placement, engine, parity test

| Feature | Where in the app | Runs on | Parity pinned by |
|---|---|---|---|
| Density, melting point, cost | Calculator, new Properties card | JS | fixtures vs library |
| Carbides, nitrides, diborides | Calculator, new Ceramics tab beside Alloys and Oxides | JS | fixtures vs library |
| Alloy dataset with provenance | New Dataset view: search, filters, per-alloy provenance drawer, data sheet, CSV of the user's own build | engine | build digest equals manifest |
| Hardness with 90% range and domain flag | Properties card | engine | bit-identical fixtures |
| Domain flag and novelty measures | Calculator, "How familiar is this alloy?" card | engine | fixtures |
| Phase prediction sets | Calculator, "Phase prediction with uncertainty" card with a confidence slider | engine, forest trained once on the built dataset and cached | fixtures |
| Alloy search | New Design view, Alloy search tab: elements, step, filters, objectives, results table, Pareto plot, CSV | engine | small-grid fixture |
| Experiment planning | Design view, Experiment planning tab: create or open a campaign file, add measurements, get suggestions | engine | sample-campaign fixture |
| Random and system splits, the gap | New Benchmark view: plain explanation, baseline table with the gap, "re-run in your browser", overlap network, "score your own predictions" from an uploaded CSV | engine | fold digests and baseline numbers |
| HEACalculator bridge | later, only if HEACalculator runs in Pyodide | engine | n/a |

## Web app findings that shape the build

From a read of `web/`, the tests and the workflows on 2026-10-05.

1. `web/index.html` is one hand-edited 11,834-line file with no JS
   toolchain. Tools rewrite it by exact text anchors (the `VERSION` regex,
   `VERSION_HISTORY`, the provenance markers, the 12,000-character head
   window). New features therefore go in separate files beside it, like
   `hea-calculator-core.js`: an engine client script, a Web Worker script,
   and one script per new view. The monolith only gains the view shells.
2. A Pyodide frontend existed once and was removed in commit `6ec98de`,
   because browsers block `fetch()` and Workers on `file://`. That reason
   still holds for someone opening `index.html` from disk, which
   `web/README.md` documents. It does not hold for the two surfaces users
   actually have. The web site is served over https, and the Tauri desktop
   app serves `web/` from its own origin. Plan: the engine features run on
   the site and in the desktop app, and on `file://` the calculator keeps
   working while the engine panels show a one-line notice.
3. No surface sets a CSP (no meta tag, `tauri.conf.json` has `csp: null`,
   Pages cannot send headers), so nothing blocks WASM today.
4. `pages.yml` uploads all of `web/`, and the exe embeds it. The 24 MB
   `mathjax/` folder ships whole although the page loads one entry file.
   Lines 1814 to 5127 of `index.html` are leftovers from a saved browser
   page (about 116 KB of unused third-party CSS with 168 font URLs) plus
   stale pre-rendered cards. Removing both before adding the engine
   offsets much of the engine's size.
5. Parity tests already run the JS core under Node from pytest
   (`tests/conftest.py` `node_snapshot`). The engine parity tests use the
   same route with the `pyodide` npm package, exactly as in the spike. A
   small headless-browser smoke test (Playwright) then proves each view
   renders and runs on the built site.
6. Build: the release workflow builds the `hea_bench` wheel from `src/`
   and a pinned fetch script places the engine files (version plus SHA-256
   each) in `web/engine/` before Pages upload and before the desktop
   build. `web/engine/` stays gitignored, and preflight checks it.

## Library findings that change the plan

From a read of the package on 2026-10-05 (file:line refs in the session
report).

1. Phase prediction sets are not an end-user library feature yet. The
   library has the `ConformalClassifier` building block, and only
   `tools/uncertainty_coverage.py` uses it. No library or MCP call returns a
   phase set for a composition. Plan: add one function (forest plus
   conformal set plus domain flag) to the library and MCP first, then put
   the same function in the app, so all three stay in step.
2. The PyPI wheel ships neither the Borg CSV nor the dataset. So hardness,
   the domain flag and dataset queries work only in a repo checkout, not
   after `pip install`. The app avoids this because it ships Borg (CC BY
   4.0) and builds the dataset in the browser. Shipping the Borg CSV in the
   wheel would fix pip users too (open question).
3. Alloy search predicts hardness one point at a time. A 906-point search
   took 15.2 s in CPython, which would take minutes in the browser.
   Batching the predictions gives identical numbers and must land before
   the app uses the search.
4. Campaigns silently ignore property constraints (`campaign.py:239-283`).
   This is a bug to fix or a limit to state, in the library and the app.
5. Fold digests are pinned only in `tests/test_benchmark_corpus.py`,
   although `splits.py:56-58` says the manifest pins them. A docstring fix.
6. Random folds use CPython's Mersenne Twister and the grouped folds need
   integers above 2^53. A JavaScript port would have to replicate both. The
   engine runs the real code, so it does not.

## Enforcement (agent-first)

1. A feature registry, one file, lists every user-facing feature with its
   library entry point, MCP tool, app surface (a DOM id in `web/`) and
   parity fixture.
2. A preflight and CI check fails when an MCP tool or public subpackage is
   missing from the registry, when an entry names an app surface that does
   not exist, or when it has no fixture. The error names the fix. Today's
   gaps start on an allowlist that may only shrink.
3. A functional check runs headless Chromium on the built site, runs every
   feature on its fixture, and compares the result with CPython.

## Order of work

1. Enforcement first (registry, ratchet allowlist), so no new gap can land.
2. Cleanup: remove the saved-page leftovers from `index.html` and the
   unused parts of `mathjax/`, verified in a browser.
3. JS quick wins: Properties card (tier A), Ceramics tab.
4. Engine: worker, loader and progress UI, wheel and pinned engine files
   at build time, `file://` notice, Node and headless-browser test harness.
5. Library fixes the app depends on: batched search predictions, the
   phase-set function, the campaign property-constraint bug.
6. Dataset view.
7. Hardness with interval, domain flag, phase prediction sets.
8. Design view: alloy search, experiment planning.
9. Benchmark view.
10. HEACalculator bridge, if feasible.
11. Docs, README and preprint wording (Fig 1 Interfaces box, abstract
    "whole workflow", Conclusions "same interfaces").

## Open questions for David (answered, see Decisions above)

1. Approve the hybrid design, with the real library in the browser for
   every model feature?
2. Bundle the engine (offline desktop, installer about 37 MB larger) or
   load it from a CDN (needs internet for those features)?
3. Approve the in-browser download of the Peivaste file from its authors?
4. Navigation names: new Dataset, Design and Benchmark views, and rename
   the existing Data view to Element data?
5. Release cadence: each step as its own patch release, or one 2.6.0?
6. Close the MCP gaps (benchmark, phase sets, ceramics) in the same effort?
7. Ship the Borg CSV inside the PyPI wheel, so hardness works after
   `pip install` too?
