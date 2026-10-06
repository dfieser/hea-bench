# web/: the HEA-Bench app

The app most people use. It runs entirely client-side: compositions never
leave the user's machine. This folder is the site root of
<https://dfieser.github.io/hea-bench/> (GitHub Pages deploys it) and the
frontend the desktop `.exe` embeds (`src-tauri/`), so the website and the
desktop app are the same app.

**Every user-facing feature must appear and work here, and in the
library, the MCP server and the desktop exe too** (owner rule, see
`../CLAUDE.md`), so a person only ever needs one of the four.
`tests/test_feature_parity.py` enforces it: every public library name,
MCP tool, phase rule and CLI command is mapped in
`tests/data/feature_parity.json` to its feature, and CI fails on any
feature without a library name, an MCP tool, app evidence (elements,
engine calls) and tests. Then `tests/test_app_smoke.py` opens the built
site in headless Chrome or Edge and uses every tab the way a person
does, and `tests/test_desktop_smoke.py` runs the same steps inside the
built exe before it is attached to a release.

## How to open it

- **Online:** <https://dfieser.github.io/hea-bench/>. The landing page
  lists what each tab does. Everything works there.
- **Desktop:** the portable `HEA-Bench.exe` on the GitHub release page.
  The engine is inside the exe and starts by itself, so everything works
  offline. The one exception is the dataset's 6.4 MB Peivaste source
  file, which its authors have not licensed for redistribution: the app
  fetches it from their repository by itself the first time it is
  online, checks its SHA-256 and keeps it in IndexedDB.
- **From a clone:** run `python tools/build_web_engine.py` once (it
  assembles `web/engine/`, see below), then `python -m http.server -d web`
  and open <http://localhost:8000>. Double-clicking `index.html` also
  works, but only for the instant calculator: browsers block the engine
  (a Web Worker) on `file://` pages, and the page says so.

## The tabs

- **Calculator.** Alloy descriptors, the nine phase rules, the Miedema
  decompositions and the Ω pair-table check, computed instantly by the
  JavaScript core. The Properties and predictions panel adds density and
  raw-material cost (instant) and, from the engine, hardness with its
  conformal interval, the conformal phase prediction sets and the domain
  flag. **Oxides** and **Ceramics** (carbides, nitrides, diborides) are
  modes of the same tab, also instant.
- **Dataset.** The consolidated experimental corpus (v0.1.0 by default,
  v0.2.0 opt-in) with every source's label and paper, filters, paging and
  CSV download, plus the measured hardness and density records.
- **Design.** Composition search (grid, property limits, rule filters,
  Pareto front) and experiment planning (record measurements, get the
  next alloys to make, save and reopen the campaign file).
- **Benchmark.** The frozen random and family-grouped splits with their
  digests, live baseline reruns, scoring of uploaded predictions with the
  gap, and the conformal coverage study.
- **Element data, Theory, Equations, References.** The data behind every
  number and the documentation, all offline.

## Two engines, one set of numbers

- `hea-calculator-core.js` is a pure-JavaScript port of the descriptor,
  rule, oxide, ceramics, tier A property and Ω-sensitivity code. It is
  instant and works even from `file://`. Its data tables are GENERATED
  from the Python library by `tests/data/_sync_js_tables.py` and
  `tests/data/_sync_js_oxide_tables.py`; never hand-edit those blocks.
  Parity: `tests/test_web_parity.py`, `tests/test_web_oxides_parity.py`,
  `tests/test_web_properties_parity.py`, `tests/test_web_miedema.py`.
- `hea-engine-worker.js` runs the **real `hea_bench` Python package**,
  unchanged, in a Web Worker through Pyodide, for everything that needs
  the corpus or scikit-learn. `hea-engine.js` is the page's handle on it
  (lazy start, progress, restart, a watchdog for stalled starts), and
  `hea_bench.webapp` is the JSON bridge it calls. The built corpus and
  the Peivaste download persist in IndexedDB, keyed by version. Parity:
  `tests/test_web_engine.py` runs the shipped bundle under Node and
  compares every call in `tests/data/web_engine_calls.json` with CPython.
- `hea-features.js` and `hea-features.css` hold the Dataset, Design and
  Benchmark tabs, the predictions panel, the Ω check and Ceramics mode.

## web/engine/ (gitignored, built at deploy time)

`python tools/build_web_engine.py` writes `web/engine/`: the pinned
Pyodide 0.29.5 runtime with the numpy, scipy and scikit-learn wheels
(every file SHA-256 pinned in the script), `hea-bench.zip` (the package
source, the shipped raw data and the published baselines, built
deterministically from tracked files) and `manifest.json`. It is never
committed. `pages.yml` and the desktop build in `release.yml` run it
before shipping, the CI `web-engine` job tests the result, and the
`verify-live` job in `auto-release.yml` checks that the live engine
reports the released version. `python tools/build_web_engine.py --check`
reports a stale or missing bundle and the exact fix.

## Asset URLs

The four scripts and the stylesheet load as `name?v=<version>`, stamped
by `tools/version.py`, so a release never mixes a new page with cached
old scripts. Do not edit those query strings by hand.

## Changing the app

1. Library change that users should see: build its surface here, add the
   bridge method to `hea_bench.webapp` if it needs Python, add the call to
   `tests/data/web_engine_calls.json`, add its MCP tool (the steps are in
   `../CLAUDE.md`), map the public names in
   `tests/data/feature_parity.json`, and, if it uses the engine, add a
   step to `STEPS` in `tests/app_smoke.cjs` that uses it through its UI.
   `pytest tests/test_feature_parity.py tests/test_app_smoke.py` names
   anything missing and the exact fix.
2. Descriptor, rule, oxide, ceramics or tier A change: update
   `hea-calculator-core.js` and run the parity suites listed above.
3. Page-only UI work: edit `index.html` or
   `hea-features.js` / `hea-features.css`.
