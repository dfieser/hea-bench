# hea-bench — rules that override defaults

- **Agents operate this repo** (commits, pushes, releases). Optimize
  every rule, doc, and process for agents by default: enforce
  mechanically (hooks, CI) rather than by convention, write mechanical
  sequences rather than advice, and make error messages name the exact
  fix. A fresh agent session that has read nothing should still be
  forced into the right behavior.

- **FOUR-PART PARITY IS MANDATORY (owner rule, 2026-10-06; it widens
  the 2026-10-05 app-parity rule).** hea-bench ships as four parts, and
  a person should only ever need ONE of them: the Python package
  (PyPI), the MCP server (`hea-bench-mcp`, in the official MCP
  registry), the desktop exe (the `web/` folder in a Tauri shell with no
  Rust commands) and the web site (built from `web/`). From now on every
  user-facing feature must appear AND work in all four. A feature
  missing from any part is a DEFECT, not a finished feature, and a new
  feature is not done until it works in all four. Since v2.7.0 they all
  do, except the HEACalculator bridge, which the owner deferred on
  2026-10-05 (it needs the user's own HEACalculator install).

  ENFORCED, not advised. `tests/test_feature_parity.py` reads
  `tests/data/feature_parity.json`, where every public name, MCP tool,
  phase rule and CLI command is listed once, and fails CI with the
  exact fix when a feature lacks a library name, an MCP tool, app
  evidence (DOM ids, bridge methods the page calls, browser-core
  functions it uses) or tests. `tests/test_app_smoke.py` uses every tab
  of the built site in a headless browser (CI `web-engine` job).
  `tests/test_installed_package.py` builds the wheel, installs it fresh
  and calls every MCP tool over stdio (CI `package` job).
  `tests/test_desktop_smoke.py` uses every tab inside the built exe
  (release `desktop-build` job). Adding a public feature, mechanically:
  (1) the library function, public in some `__all__`; (2) its MCP tool
  in `_TOOLS` in `src/hea_bench/mcp_server.py`, a thin wrapper with a
  `_PARAM_DOCS` entry, and a call to it in `TOOL_CALLS` in
  `tests/package_smoke.py`; (3) its app surface in `web/`
  (`hea-features.js`, plus a `hea_bench.webapp` bridge method if it
  needs Python, added to `tests/data/web_engine_calls.json`); (4) its
  names under one feature in `tests/data/feature_parity.json`; (5) if
  it uses the engine, a step in `STEPS` in `tests/app_smoke.cjs` that
  uses it through its UI; (6) `python tools/build_web_engine.py`, then
  `pytest tests/test_feature_parity.py tests/test_webapp.py
  tests/test_app_smoke.py` and `HEA_BENCH_PACKAGE_SMOKE=1 pytest
  tests/test_installed_package.py`. How the app is built:
  `web/README.md`.

- **Shipping = pushing.** Any push to `main` touching `src/**`, `web/**`,
  `src-tauri/**`, `server.json`, or `pyproject.toml` auto-releases all
  four surfaces (PyPI, MCP registry, desktop exe, web site) via the
  `Auto release` workflow. Do not hand-tag or bump versions for routine
  changes; push, then confirm the run goes green with `gh run list`.
  Opt out with `[no-release]` in the head commit message.
- **The pre-push hook runs the release preflight; do not fight it.**
  Pushing a shippable path triggers `python tools/preflight.py`
  (every locally runnable release gate plus the external-registry
  metadata limits) via `tools/git-hooks/pre-push`, enabled by the same
  one-per-clone `git config core.hooksPath tools/git-hooks` as the
  commit-msg hook. Agent push sequence, mechanically: (1) `git push` —
  the hook runs the preflight and refuses a failing push; (2) fix
  whatever it names and push again, NEVER `--no-verify` and never
  delete a check; (3) `gh run list` and watch the `Auto release` run
  to green. Green means PyPI, the MCP registry, the GitHub Release and
  the live site are verified; it does NOT wait for the desktop exe,
  which is a 15-20 minute Rust build that nobody waits for. Never
  watch or wait for `desktop-build`: if it fails, `release.yml` opens
  an issue labelled `desktop-build` that mentions and assigns the
  owner, so the owner is emailed by GitHub; a later session fixes it.
  A transient failure is re-fired with `gh workflow run release.yml
  --ref vX.Y.Z`, but a re-fire builds the tagged code, so a code fix
  needs a green `gh workflow run desktop-smoke.yml --ref main` and then
  ships with the next releasing push (preflight enforces this). Heed
  preflight's "gate NOT pre-verified" warnings before
  touching benchmark, corpus, split, or web-parity code. If a release
  ever fails for a reason the preflight did not catch, the fix commit
  must also add the check and a RELEASING.md catalog row — checks are
  only added, never removed.
- The one version number lives in `src/hea_bench/__init__.py`; the only
  legal way to change it is `python tools/version.py --set X.Y.Z`.
- NEVER touch the GitHub↔Zenodo integration; it can irreversibly fork
  the concept DOI. See `RELEASING.md` for everything about releases.
- **No AI attribution, anywhere, ever.** Never add a `Co-Authored-By`
  trailer naming an AI or agent, and never list one as an author,
  contributor, creator, or reviewer in commit messages, `CITATION.cff`,
  `.zenodo.json`, `README.md`, `CONTRIBUTING.md`, release notes, or the
  web app. Credit named humans only. A `commit-msg` hook in
  `tools/git-hooks/` rejects such trailers; enable it once per clone
  with `git config core.hooksPath tools/git-hooks`. The 101 historical
  commits that carry the old trailer are deliberately left alone,
  because rewriting them would move every tag and put the Zenodo-linked
  releases at risk.
- Credit external reporters and reviewers in the CHANGELOG entry, the
  README acknowledgements, and the GitHub release notes, in the form
  the person asks for. Ask before publishing a name that arrived by
  private email.
- Library usage (API, units, pinned sanity values): `AGENTS.md`.
