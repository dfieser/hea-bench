# hea-bench — rules that override defaults

- **Agents operate this repo** (commits, pushes, releases). Optimize
  every rule, doc, and process for agents by default: enforce
  mechanically (hooks, CI) rather than by convention, write mechanical
  sequences rather than advice, and make error messages name the exact
  fix. A fresh agent session that has read nothing should still be
  forced into the right behavior.

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
  to green. Heed preflight's "gate NOT pre-verified" warnings before
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
