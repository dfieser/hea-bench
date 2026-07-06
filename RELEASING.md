# Releasing hea-bench

hea-bench has **one** version number and a **single, hands-off release
pipeline**. This document explains where the version lives, how to cut a
release, and the one-time setup that makes it fully automatic.

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

The append-only histories are **not** auto-synced; they get a new entry each
release, by hand: the `## [x.y.z]` section in
[`CHANGELOG.md`](CHANGELOG.md) and the top row of the `VERSION_HISTORY` array
in [`web/index.html`](web/index.html).

## Cutting a release

1. Bump and restamp:
   ```bash
   python tools/version.py --set X.Y.Z
   ```
2. In `CHANGELOG.md`, rename `## [Unreleased]` to `## [X.Y.Z] — <today>` and
   add a fresh empty `## [Unreleased]` above it. The release notes on GitHub
   are taken verbatim from this section.
3. In `web/index.html`, prepend one entry to `VERSION_HISTORY`:
   `{ version: "X.Y.Z", date: "<today>", notes: "..." }`.
4. Confirm consistency and commit:
   ```bash
   python tools/version.py --check
   git commit -am "Release vX.Y.Z"
   ```
5. Tag and push:
   ```bash
   git tag vX.Y.Z
   git push --follow-tags
   ```

That is the whole job. The tag triggers
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
