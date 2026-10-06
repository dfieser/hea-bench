# Four-surface parity: every feature in every part

Owner rule, 2026-10-06: hea-bench ships as four parts, and from now on
each one must have every feature, so a person only needs to choose one.

| Part | What a person installs or opens |
| --- | --- |
| Python package | `pip install "hea-bench[all]"` from PyPI |
| MCP server | `hea-bench-mcp`, from the MCP registry (`uvx --from "hea-bench[mcp]" hea-bench-mcp`) |
| Desktop app | `HEA-Bench.exe` from the GitHub release (the `web/` folder in a Tauri shell) |
| Website | https://dfieser.github.io/hea-bench/ (the same `web/` folder) |

This extends the app-parity rule of 2026-10-05 (library to app) to all
four directions. The registry is `tests/data/feature_parity.json`; the
checks are `tests/test_feature_parity.py`.

## Gaps found on 2026-10-06

- MCP server lacked ceramics, measured hardness and density, conformal
  phase sets, the benchmark (summary, live baselines, fold export,
  scoring uploaded predictions), the coverage study, element data with
  sources, a dataset export, and a way to build the dataset at all.
- From a pip install, hardness, the dataset, the benchmark, phase sets
  and the domain flag all failed: the wheel shipped no datasets and the
  corpus could only be built from a repository checkout.
- The registry install of the MCP server (`hea-bench[mcp]`) had no
  scikit-learn, so hardness, phase sets and campaigns failed there too.
- Web-only features with no Python or MCP counterpart: the Miedema
  formation-enthalpy decomposition, custom elements, and custom pair
  enthalpies.
- The desktop exe was never tested as an exe: CI tests the `web/` folder
  in Chrome, not the Tauri build.

## Steps

1. Library: ship the openly licensed datasets in the wheel
   (`hea_bench/_paths.py`, pyproject force-include), add
   `hea_bench.corpus.build_corpus()` (downloads the one unshipped file,
   SHA-256 checked), move the Omega pair-table check into the library
   (`hea_bench.omega_sensitivity`), add `hea_bench.element_data`, port the
   Miedema decomposition, and support custom elements and pair
   enthalpies.
2. MCP: one tool per missing feature, each a thin wrapper over the same
   library or `hea_bench.webapp` function the app calls, so the two
   cannot disagree. The `mcp` extra pulls in scikit-learn.
3. Enforcement: every feature in the registry must name its library
   names, its MCP tools and its app evidence; `tests/package_smoke.py`
   installs the built wheel in a clean virtual environment outside the
   repository and uses every feature through the Python API and every
   MCP tool over a real stdio session; the desktop exe is smoke-tested
   with the browser driver over WebView2's DevTools port after it is
   built.
4. App responsiveness: measure main-thread long frames and
   time-to-content per tab, then fix what blocks.
5. Corpus default, owner decision 2026-10-06: browsing and downloading
   the dataset opens on v0.2.0 on every part; the benchmark, phase sets
   and the domain flag stay on v0.1.0, where the published numbers are
   measured.
6. Dependencies and CI brought up to date, docs and the preprint's
   agent-server wording updated, released as 2.7.0.

## Status

Shipped in 2.7.0 (2026-10-06). Every step above is done: 24 MCP tools,
the datasets in the wheel with `build_corpus()`, the `[all]` extra,
custom elements and the Miedema breakdown in the library and over MCP,
and four gates (`tests/test_feature_parity.py`,
`tests/test_installed_package.py` in the CI `package` job,
`tests/test_app_smoke.py` in the CI `web-engine` job, and
`tests/test_desktop_smoke.py` in the release `desktop-build` job). The
app keeps fitted models between visits, prepares them while idle, starts
its engine early for returning visitors and defers long tables' layout.
The one exception is the HEACalculator bridge, deferred by the owner on
2026-10-05 because it needs the user's own HEACalculator install.
