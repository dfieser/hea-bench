# Architecture

Read this before adding code. It says where each kind of code lives and
which way imports may point. `tests/test_architecture.py` enforces the
import rules, and its failures name the fix.

## Python layers

Each layer may import only from the layers above it in this table. Lazy
imports inside a function count the same as imports at the top.

| Layer | Modules | Belongs here | Does not belong here |
|---|---|---|---|
| 0. Foundation | `constants`, `_overrides`, `_paths`, `_json`, `descriptors/data/*`, `oxides/_data`, `properties/data/*` | Vendored tables and their provenance, physical constants and rule thresholds, data-file locations, strict-JSON cleaning | Any calculation |
| 1. Core | `composition`, `custom`, `descriptors/*`, `rules/*`, `oxides/*`, `ceramics`, `properties/tier_a` | Closed-form science over the tables. Standard library only | Corpus access, scikit-learn, file writes, response shapes for a surface |
| 2. Analysis | `benchmark/*`, `corpus`, `uncertainty/*`, `properties` (tier B), `design/*`, `_model_cache` | Everything that needs the corpus or a fitted model. scikit-learn imports go inside functions, never at the top | Tool caps, parameter parsing for a surface, response shapes |
| 3. Service | `service/*` | One function per user-facing operation, shared by every surface: plain values in (formula strings, dicts), a strict-JSON dict out, the shared caps, the warning wording, the citation keys | The MCP SDK, Pyodide, argparse, and writing to a path the caller names |
| 4. Interfaces | `mcp_server`, `webapp`, `cli` | Registration, parameter docs, transport envelope, progress reporting, file paths | Science, payload shapes, caps |

The web app is a fifth surface over the same layers. Its calculator tab
uses `hea-calculator-core.js`, a JavaScript port of layer 1. The
`tests/data/_sync_js_*.py` scripts generate its tables from layer 0.
Everything else goes through `hea-engine.js`, its worker and
`hea_bench.webapp`.

## Import rules

1. A module imports only from its own layer or the layers above it in
   the table.
2. Layers 0 and 1 import only the standard library. The one exception
   is the optional HEACalculator adapter in `descriptors/backend`, which
   imports HEACalculator inside a function.
3. `mcp_server`, `webapp` and `cli` never import each other.
4. No module imports a function, class or constant whose name starts
   with `_` from a module in another package. Make it public in its own
   module first. The shared underscore modules (`_paths`, `_json`,
   `_overrides`, `_model_cache`, `descriptors/_tables`,
   `service/_payload`) are exempt.
5. The corpus builder (`benchmark/consolidate`, `benchmark/loaders`)
   never imports the corpus reader (`hea_bench.corpus`).
6. No import cycle between modules, lazy imports included, except inside
   one package.

## Web app rules

1. Page code never computes a number itself. It calls
   `hea-calculator-core.js` or the engine.
2. `index.html` holds the markup, the `<head>`, and the constant blocks
   that tools rewrite (`VERSION`, `VERSION_DATE`, `VERSION_HISTORY`, the
   generated `PROVENANCE_TABLES`). Calculator-tab logic lives in
   `hea-calculator-ui.js`, its styles in `hea-app.css`. The other tabs
   live in `hea-features.js` and `hea-features.css`.
3. The text-style and parity tests find every script in `web/` by glob,
   never through a hand-kept file list.

## Where new code goes

| New thing | Where |
|---|---|
| A descriptor | `descriptors/<name>.py`, registered in `descriptors/backend.NATIVE_DESCRIPTORS`, exported from `hea_bench/__init__.py` |
| A phase rule | `rules/<name>.py` with `predict`, registered in `rules/__init__.py`, its threshold in `constants.py`, one row in the rule table in `service/alloys.py` |
| A source dataset | `benchmark/loaders/<source>.py`, then `SOURCES_BY_VERSION` in `benchmark/consolidate.py` |
| A fitted property | `properties/<name>.py`, dispatched from `properties.predict_property` |
| Any user-facing feature | The library function, then one `service` function, then a thin MCP tool and a `webapp.METHODS` entry that both call that function, then the web UI, then `tests/data/feature_parity.json`. The mechanical steps are in `CLAUDE.md` |
| A data-file path | `_paths.py` |
| A tool cap or limit | `service/_payload.py`, so the MCP server and the app share it |

## One source of truth

| Fact | Home |
|---|---|
| Package version | `hea_bench/__init__.py`, changed only by `tools/version.py --set` |
| Constants and rule thresholds | `constants.py` and each rule's `DEFAULT_THRESHOLD` |
| Element and pair data | `descriptors/data/*`, copied into `hea-calculator-core.js` only by `tests/data/_sync_js_*.py` |
| Descriptor names and units | `descriptors/backend.NATIVE_DESCRIPTORS` and `UNITS` |
| Data-file locations | `_paths.py` |
| Citation keys in responses | `service/_payload.SOURCES`, re-exported as `mcp_server.SOURCES` |
| Strict JSON | `_json.strict_json` |

## How errors flow

Layers 1 and 2 raise typed errors whose message names the fix:
`ValueError` for bad input, `PropertyUnavailableError`,
`BackendUnavailableError`, `FileNotFoundError` for a corpus that is not
built, and `ImportError` for a missing extra. They never hide an error,
with one documented exception: a value that cannot be computed for one
composition becomes `None`, so one bad value does not sink a batch.

The service layer rewrites those errors as the message a user sees, such
as telling them to build the corpus first or to install
`hea-bench[mcp]`, and raises it as `ValueError`. A `None` value becomes
a null plus a warning in the response.

Only the interfaces catch `Exception` broadly. MCP reports the message
as a tool error. `webapp.call` returns `{"ok": false, "error", "type"}`.
The CLI prints to stderr and exits with code 2.

## Module map

Where code moved in the November 2026 restructure. Modules not listed
kept their place and their job.

| Before | Now |
|---|---|
| `mcp_server.py`, alloy, oxide, ceramic and element reports | `service/alloys.py`, with the MCP tools as thin wrappers keeping their names, signatures and docstrings |
| `mcp_server.py`, corpus tools, `webapp.py` dataset methods | `service/dataset.py` |
| `mcp_server.py` and `webapp.py`, properties, applicability, phase sets | `service/predictions.py` |
| `mcp_server.py`, design search parsing, caps, campaign payload | `service/design.py` |
| `webapp.py`, benchmark summary, run, folds CSV, score CSV, coverage | `service/benchmark.py` |
| `mcp_server._stamp`, `SOURCES`, the caps | `service/_payload.py` |
| `corpus.corpus_location`, `corpus.SOURCE_COLUMN_PREFIX` | `_paths.py`, re-exported from `hea_bench.corpus`. Not under `benchmark/`, whose package import loads the corpus reader |
| `design.search.search` | the same function, its screening, feasibility and Pareto phases split into named helpers |
| `uncertainty.phase._fitted`, `_corpus_domain`, `properties.hardness._fitted`, `descriptors.backend._NATIVE`, the Borg `_COL_*` names | the same objects under public names (`fitted_model`, `corpus_domain`, `NATIVE_DESCRIPTORS`, `COL_*`), since other packages read them. `hardness._fitted` stays as an alias |
| `web/index.html`, inline calculator script and styles | `web/hea-calculator-ui.js` and `web/hea-app.css` |
