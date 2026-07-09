# hea-bench — rules that override defaults

- **Shipping = pushing.** Any push to `main` touching `src/**`, `web/**`,
  `src-tauri/**`, `server.json`, or `pyproject.toml` auto-releases all
  four surfaces (PyPI, MCP registry, desktop exe, web site) via the
  `Auto release` workflow. Do not hand-tag or bump versions for routine
  changes; push, then confirm the run goes green with `gh run list`.
  Opt out with `[no-release]` in the head commit message.
- The one version number lives in `src/hea_bench/__init__.py`; the only
  legal way to change it is `python tools/version.py --set X.Y.Z`.
- NEVER touch the GitHub↔Zenodo integration; it can irreversibly fork
  the concept DOI. See `RELEASING.md` for everything about releases.
- Library usage (API, units, pinned sanity values): `AGENTS.md`.
