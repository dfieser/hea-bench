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
4. then **verifies**: the run goes red if PyPI, the MCP registry or the
   GitHub Release fail, or if the live site, and its in-app engine
   (`engine/manifest.json`), are not serving the new version within 15
   minutes. It does not wait for the desktop exe (see below).

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

1. **gate** — the full pytest 3.10–3.14 matrix, the JS parity test, the
   version-consistency check, the `package` job (the built wheel installed
   fresh, every MCP tool called over stdio, `tests/test_installed_package.py`)
   and the `web-engine` job (the in-app engine bundle assembled and checked
   against CPython, the four-part feature registry, and every tab of the
   built site used in headless Chrome) on the tagged commit.
2. **pypi** — build the sdist and wheel and publish to PyPI over OIDC Trusted
   Publishing (no token).
3. **mcp** — wait until PyPI serves the new version, then publish `server.json`
   to the Model Context Protocol registry via GitHub OIDC.
4. **release** — create the GitHub Release with the changelog section as its
   notes and the sdist/wheel attached. Publishing the Release fires the
   GitHub↔Zenodo integration, which archives the tag and mints the new version
   DOI under the concept DOI.
5. **desktop** — assemble the in-app engine (`tools/build_web_engine.py`,
   gitignored `web/engine/`), build the portable `HEA-Bench.exe` around
   `web/`, use every tab inside it (`tests/test_desktop_smoke.py`), and
   attach it to the release.

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

## The desktop exe is not waited for

The Windows executable is a 15-20 minute Rust build on a Windows runner,
and it is the only surface that takes longer than a coffee. So, as of
2026-08-18, `verify-release` in `auto-release.yml` goes green as soon as
the `pypi`, `mcp` and `release` jobs succeed, and the `Auto release` run
is green while the exe is still compiling. Agents and humans stop
watching at that point.

A failure in `desktop-build` or `desktop-attach` would otherwise be
silent, so `release.yml` has a `desktop-failed` job that runs only when
one of those two actually failed (not when they were skipped because
an upstream surface failed first, which the watch already reports). It
opens an issue titled "Desktop exe failed to ship for vX.Y.Z", labelled
`desktop-build`, that mentions and assigns the owner; GitHub delivers
both as email. If an open `desktop-build` issue already exists it
comments there instead, so a flaky runner cannot fan out into a pile of
issues. The site's download link shows its update-in-progress notice
until an exe is attached.

To recover from a transient failure (a runner, the network, an outage),
re-fire only the release pipeline for that tag and close the issue once
the exe is attached:

```bash
gh workflow run release.yml --ref vX.Y.Z
```

A re-fire builds the code the tag points at, so it cannot pick up a
fix. When the cause was in the code, the tests or the workflow, fix it
on `main` with `[no-release]`, confirm it with a green
`gh workflow run desktop-smoke.yml --ref main`, and the next releasing
push ships the exe. Close the issue once an exe is attached.

## Recovering an interrupted release

If a release run dies after the tag exists (runner eviction, a cancelled
run, an outage), nothing is lost and nothing needs reverting: the tag and
the stamped release commit are already on `main`, and every pipeline step
is idempotent (PyPI publishing skips already-uploaded files). Re-fire it:

```bash
gh workflow run release.yml --ref vX.Y.Z   # the four surfaces + Release + Zenodo
gh workflow run pages.yml --ref main       # the site, if it is stale too
```

The `verify-release` and `verify-live` jobs already do this once
automatically when they see a *cancelled* (as opposed to failed) run.

If the run died after it pushed the `Release vX.Y.Z` commit but before
the tag reached the remote (the v2.7.0 shape: `main` carries the release
commit, `git ls-remote --tags origin vX.Y.Z` prints nothing), do NOT
re-run the `Auto release` run: it would promote the changelog and the
version history a second time. Tag the release commit by name instead.
The tag push fires `release.yml` by itself; then redeploy the site so it
carries the version-history entry:

```bash
git pull --ff-only origin main
git tag -a vX.Y.Z -m "Release vX.Y.Z" <sha of the Release vX.Y.Z commit>
git push origin vX.Y.Z
git ls-remote --tags origin vX.Y.Z
gh workflow run pages.yml --ref main
```

## Why releases have failed, and the preflight that prevents it

Every failed release cycle to date, with its root cause and the guard
that now exists against it. This table is maintained deliberately: a
release process that fails a quarter of the time is a process problem,
not bad luck, and each row below was a check that either could have run
before the push and did not, or lived only inside an external publisher.

| Date | Release | What failed | Root cause | Guard now in place |
| --- | --- | --- | --- | --- |
| 2026-07-06 | v2.0.3, v2.0.4 | manual tag flow | lightweight tag + `--follow-tags` silently pushed no tag; bare commit push released nothing | manual flow retired; push = release automation, and the manual recipe above pushes tags by name and verifies with `ls-remote` |
| 2026-07-09 | landing-page push | every gate job cancelled | runner eviction, not a code fault | verify jobs distinguish cancelled from failed and re-dispatch once |
| 2026-07-23 | v2.1.0 | release-gate ruff | new descriptors missing from `__all__`; lint never ran locally before the push | `tools/preflight.py` runs the exact gate lint pre-push |
| 2026-07-24 | app-icon push | release-gate ruff | unpinned ruff minor release changed the rules mid-week | ruff pinned to the 0.15 series in `pyproject.toml` |
| 2026-08-10 | v2.2.0 | benchmark-freeze gate | benchmark code changed without regenerating the frozen digests; the local suite silently skipped those tests because no corpus was built | `tools/preflight.py` reports every locally skipped test and names the benchmark-freeze gate as unverified when the corpus is absent |
| 2026-08-11 | v2.4.0 watch | verify-release went red on a green release | one transient GitHub API timeout failed the whole watch | watcher treats unreadable status as "still running" and polls again |
| 2026-08-16 | v2.5.0 | `mcp` publish, HTTP 422 | `server.json` description was 199 characters; the MCP registry caps it at 100, and nothing anywhere validated registry constraints | `tools/preflight.py --metadata` encodes the registry limits and runs in four places: the pre-push hook, by hand locally, in CI on every push, and in the release bot before it stamps or tags |
| 2026-08-17 | no red run; found by inspection | the live site never showed a favicon in Google results | the icon was a `data:` URI, which Google cannot crawl, and no gate has ever opened a file under `web/` that is not code | `tools/preflight.py --metadata` checks the icon set, the 1200x630 social card, the manifest and the JSON-LD, and rejects a `data:` URI or a root-absolute icon path |
| 2026-10-05 | v2.6.0 | `gate / interop`, two HEACalculator backend tests | HEACalculator released 2.1.0 and 2.2.0 with changed reference data; the `[interop]` pin `~=2.0` admitted any 2.x, so CI installed 2.2.0 while every local run still had the verified 2.0.1, and no commit here changed anything | the pin is `~=2.0.1`, and `tests/test_descriptor_backend.py` (run by the preflight and in CI) fails whenever the pin admits a minor series other than the one `docs/backend-agreement.md` was generated with |
| 2026-10-05 | no red run; found by inspection | most library features (dataset, benchmark, phase sets, domain flag, properties, search, campaigns, ceramics) were unreachable in the app, where about 99% of users are | features were only ever finished in the library, and nothing compared the two surfaces | `tests/test_app_parity.py` (since 2.7.0 `tests/test_feature_parity.py`) maps every public name to working app evidence and fails CI otherwise; the CI `web-engine` job checks the in-app engine against CPython; `verify-live` requires the live engine to report the released version; `tests/test_app_smoke.py` uses every tab of the built site in headless Chrome in the same job |
| 2026-10-06 | no red run; found by inspection | the MCP server lacked eleven of the package's features (dataset build and export, measured properties, phase sets, the benchmark, the coverage study, ceramics, element data), custom elements and the Miedema breakdown; nothing ever ran the published wheel or the built exe | parity was checked only between the library and the web app, always from a repository checkout | owner rule: every feature in all four parts. `tests/test_feature_parity.py` requires a library name, an MCP tool, app evidence and tests for every feature; the CI `package` job installs the built wheel fresh and calls every MCP tool over stdio (`tests/test_installed_package.py`, also run by the preflight); the release `desktop-build` job uses every tab inside the built exe before attaching it (`tests/test_desktop_smoke.py`) |
| 2026-10-06 | no red run; caught before release | the MCP container image (`Dockerfile`, which directory listings such as Glama build) would have stopped building | the wheel started bundling files from `data/` and `docs/`, which the Dockerfile never copied and `.dockerignore` excluded | `tools/preflight.py`, in every mode (so also CI and the release bot), checks that every file the wheel force-includes reaches the image build stage (the Peivaste file was kept out of the image while it had no license; since its CC BY 4.0 license on 2026-10-08 the same check requires it) |
| 2026-10-06 | v2.7.0 | `Auto release` cut job, tag push | GitHub refused the tag push with a bare `remote rejected (failed)` after the release commit was already on `main`, and the tag push had no retry, so the release stopped with no tag | the tag push retries three times with a growing pause, and the recovery section above covers a stranded release commit (tag it by name, never re-run the cut) |
| 2026-10-06 | v2.7.1, v2.7.2 | `desktop-build`, the exe smoke test, so neither release got an exe | the new test passed on a desktop but timed out on GitHub's runners waiting for WebView2's DevTools port. The runners run elevated, and WebView2 ignores `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS` and per-user policies for an elevated app. The test's first run on a runner was inside the release | the test also sets the machine-wide `AdditionalBrowserArguments` policy, which WebView2 honors, when it runs elevated. `tools/preflight.py` refuses a releasing push whose desktop inputs (`src-tauri/`, the test, `desktop-smoke.yml`) changed since the last release until a green `Desktop smoke` run covers them |
| 2026-10-08 | no red run; caught before release | the pre-push preflight refused the 2.8.0 push twice with `FAIL pytest (full suite)` and no test output | `tools/preflight.py` kept the output of a failing check but printed only its label, so the failure could not be read from the hook. The failure was real: the new parallel forests also predicted on several threads, which add the trees' answers in the order the threads finish, so under load a hardness prediction changed in its last digit between calls | the preflight prints the last 2,000 characters of every failing check's output under its label. Forests fit on every core and predict on one (`hea_bench._model_cache.serial`), and `tests/test_properties_hardness.py` checks it |
| 2026-10-08 | no red run; caught before release | the desktop-inputs check refused the 2.8.0 minor bump | `python tools/version.py --set X.Y.0`, the documented way to bump, rewrites the version line in `src-tauri/Cargo.toml` and `Cargo.lock`, and the check counted that as a new exe input although every patch release makes the same change in CI | the check blanks the version stamps that `tools/version.py` writes before comparing, and still refuses any other change under `src-tauri/`; `tests/test_version_sync.py` tests it |

The defense has four layers, in firing order:

1. **The pre-push hook** (`tools/git-hooks/pre-push`, enabled by the
   same one-per-clone `git config core.hooksPath tools/git-hooks` as
   the commit-msg hook) detects shippable paths (`src/**`, `web/**`,
   `src-tauri/**`, `server.json`, `pyproject.toml`) in the pushed range
   and refuses the push until the preflight passes. Nobody — human or
   agent — has to remember anything; forgetting is not possible, and
   `--no-verify` is never an acceptable answer to a red preflight.
   Non-shippable pushes (docs, tools, tests, CI) pass through silently.
2. **`python tools/preflight.py` by hand**, while iterating on a
   shippable change. It runs the publish-metadata checks,
   `version.py --check`, the exact release-gate ruff invocation, a
   rebuild of the in-app engine bundle when its runtime is cached, and
   the full pytest suite, then names any release gate it could NOT
   verify locally (missing corpus, missing Node, missing engine bundle)
   so pushing anyway is a knowing choice rather than an accident.
3. **CI on every push and pull request** runs
   `tools/preflight.py --metadata`, so externally enforced constraints
   are checked long before a release exists.
4. **The release bot** runs the same metadata check before it stamps,
   commits, or tags, so invalid metadata fails the run cleanly instead
   of half-releasing (tag cut, PyPI published, registry rejected — the
   v2.5.0 shape).

**The ratchet rule.** When a release fails for a reason this table does
not list, the fix is not complete until the same change teaches
`tools/preflight.py` (or the CI gate) to catch that reason before the
next push, and adds the row here. Checks are only added, never removed.

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
