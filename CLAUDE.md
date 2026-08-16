# hea-bench — rules that override defaults

- **Shipping = pushing.** Any push to `main` touching `src/**`, `web/**`,
  `src-tauri/**`, `server.json`, or `pyproject.toml` auto-releases all
  four surfaces (PyPI, MCP registry, desktop exe, web site) via the
  `Auto release` workflow. Do not hand-tag or bump versions for routine
  changes; push, then confirm the run goes green with `gh run list`.
  Opt out with `[no-release]` in the head commit message.
- **Run `python tools/preflight.py` before ANY push that touches a
  shippable path, and only push when it passes.** It runs every release
  gate that can run locally plus the external-registry metadata limits;
  the failure catalog behind it is in RELEASING.md. If a release ever
  fails for a new reason, the fix commit must also teach preflight (or
  CI) to catch that reason, and add the catalog row — checks are only
  added, never removed.
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
