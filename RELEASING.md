# Releasing hea-bench

hea-bench has **one** version number and a **single, hands-off release
pipeline**, and since 2.0.6 the pipeline drives itself: **pushing to
`main` is releasing**. This document explains where the version lives,
what a push triggers, the overrides, and the one-time setup.

## The one version number

The single source of truth is `__version__` in
[`src/hea_bench/__init__.py`](src/hea_bench/__init__.py). Everything else
either derives from it automatically or is stamped from it:

| Surface | How it gets the version |
| --- | --- |
| `pyproject.toml` (PyPI) | Derived. `dynamic = ["version"]`; hatchling reads `__version__`. |
| `src-tauri/tauri.conf.json` (desktop) | Derived. No `version` key, so Tauri inherits `src-tauri/Cargo.toml`. |
| CLI, MCP server, tests | Derived. They `from . import __version__`. |
| `src-tauri/Cargo.toml` | Stamped. |
| `server.json` (MCP registry, twice) | Stamped. |
| `CITATION.cff` (`version` + `date-released`) | Stamped. |
| `llms.txt` (prose + BibTeX) | Stamped. |
| `web/index.html` (`VERSION` + `VERSION_DATE`) | Stamped. |

Stamping and verification are handled by one zero-dependency script,
[`tools/version.py`](tools/version.py):

```bash
python tools/version.py --check      # fail if any file disagrees (runs in CI)
python tools/version.py --set 2.1.0  # bump the canonical value + restamp + dates
```

CI runs `--check` on every push and pull request, so the files can never
silently drift apart.

The two append-only histories — the `## [x.y.z]` section in
[`CHANGELOG.md`](CHANGELOG.md) and the top row of the `VERSION_HISTORY` array
in [`web/index.html`](web/index.html) — are written at release time by
[`tools/autorelease.py`](tools/autorelease.py).

## Releases are automatic: push = release

Any push to `main` that changes a shippable surface — `src/**`, `web/**`,
`src-tauri/**`, `server.json`, or `pyproject.toml` — triggers
[`.github/workflows/auto-release.yml`](.github/workflows/auto-release.yml),
which with no further input:

1. runs `tools/autorelease.py --prepare`: bumps the patch version (or honors
   a pre-bumped tree, see below), stamps every surface, promotes the
   `## [Unreleased]` changelog section (or synthesizes notes from the pushed
   commit subjects), and prepends the web `VERSION_HISTORY` entry;
2. commits `Release vX.Y.Z`, pushes it, and pushes an annotated `vX.Y.Z` tag;
3. dispatches `release.yml` on that tag (the full pipeline below) and
   `pages.yml` on `main` (site redeploy), explicitly, because pushes made
   with the workflow token never trigger other workflows on their own;
4. then **verifies**: the run goes red if the release pipeline fails or if
   the live site is not serving the new version within 15 minutes.

So the day-to-day release procedure is, in full:

```bash
git commit -am "Fix the thing"
git push
```

Controls, all optional:

- **Skip a release**: put `[no-release]` anywhere in the head commit message
  of the push. The changes ride along in the next release.
- **Minor or major bump**: run `python tools/version.py --set X.Y.0` and
  include that in your push. The bot detects the pre-bumped tree and releases
  exactly that version instead of a patch bump.
- **Better release notes**: write them under `## [Unreleased]` in
  `CHANGELOG.md` before pushing; the bot promotes them verbatim. Otherwise
  the commit subjects since the last tag become the notes.
- **Docs, CI, tests, tools, manuscript**: pushes touching only those paths
  never release.

## The tag pipeline

Whether cut by the bot or by hand, a `vX.Y.Z` tag drives
[`.github/workflows/release.yml`](.github/workflows/release.yml), which runs
with no further input:

1. **gate** — the full pytest 3.10–3.12 matrix, the JS parity test, and the
   version-consistency check on the tagged commit.
2. **pypi** — build the sdist and wheel and publish to PyPI over OIDC Trusted
   Publishing (no token).
3. **mcp** — wait until PyPI serves the new version, then publish `server.json`
   to the Model Context Protocol registry via GitHub OIDC.
4. **release** — create the GitHub Release with the changelog section as its
   notes and the sdist/wheel attached. Publishing the Release fires the
   GitHub↔Zenodo integration, which archives the tag and mints the new version
   DOI under the concept DOI.
5. **desktop** — build the portable `HEA-Bench.exe` and attach it to the
   release.

## Manual fallback (only if the automation is down)

The bot stands down when the head commit message starts with `Release v`, so
a manual release never collides with an automatic one:

```bash
python tools/autorelease.py --prepare --notes "One-line what's-new text"
git commit -am "Release vX.Y.Z"        # X.Y.Z = the version the script printed
git tag -a vX.Y.Z -m "Release vX.Y.Z"  # ANNOTATED tag (-a), see below
git push origin main vX.Y.Z            # push the tag BY NAME
git ls-remote --tags origin vX.Y.Z     # confirm it is really on the remote
```

Two traps this recipe avoids, learned the hard way:

- **Never rely on `git push --follow-tags`.** It only pushes *annotated*
  tags; a plain `git tag vX.Y.Z` makes a lightweight tag, which
  `--follow-tags` silently skips — the branch pushes, the tag stays local,
  no release fires, and every surface silently stays on the old version.
  Always push the tag by name and confirm with `ls-remote`.
- **A bare commit push is not a release.** Without a tag (or the bot), only
  the Pages site redeploys; PyPI, the MCP registry, the desktop exe, the
  GitHub Release, the Zenodo DOI, and the version badge all stay put.

## One-time setup

These are configured once, in the GitHub and PyPI web consoles. Until they are
done, the first tagged release will fail at the `pypi` job.

1. **PyPI Trusted Publisher.** On the existing
   [hea-bench PyPI project](https://pypi.org/project/hea-bench/) → *Manage* →
   *Publishing*, add a GitHub publisher:
   - Owner: `dfieser`
   - Repository: `hea-bench`
   - Workflow filename: `release.yml`
   - Environment name: `pypi`
2. **GitHub environment.** Repo *Settings* → *Environments* → create one named
   exactly `pypi`. Leave it with no required reviewers so releases stay
   hands-off. (It exists only to scope the OIDC token to release publishing.)
3. **Retire the old token.** After the first successful OIDC publish, delete
   the `PYPI_API_TOKEN` repository secret and revoke that token on PyPI. The
   pipeline no longer uses it.

## Zenodo (do not touch the integration)

The GitHub↔Zenodo integration is already enabled and bound to the concept DOI
[`10.5281/zenodo.20346287`](https://doi.org/10.5281/zenodo.20346287), which
always resolves to the latest release and is the DOI to cite. Publishing a
GitHub Release is the only trigger it needs.

**Never disconnect, re-enable, toggle, rename-and-relink, or drive this
integration through the Zenodo REST API.** Any of those can mint a new concept
DOI and permanently fork the citation lineage. DOIs cannot be merged or
deleted.

[`.zenodo.json`](.zenodo.json) pins the authors, ORCIDs, affiliation, license,
and keywords that each new release records, so the archive does not depend on
whatever Zenodo would otherwise scrape. Keep its author list in step with
`CITATION.cff`. `CITATION.cff` itself intentionally records only the concept
DOI, so it never needs a per-release DOI edit.
