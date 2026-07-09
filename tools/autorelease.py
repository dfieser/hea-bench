#!/usr/bin/env python3
"""Prepare a release commit in one shot: version, stamps, changelog, history.

This is the file-editing half of the automatic release pipeline
(``.github/workflows/auto-release.yml``); it is equally usable by hand.
It decides the next version, stamps every surface through
``tools/version.py``, promotes the ``## [Unreleased]`` section of
CHANGELOG.md (or synthesizes notes from the commit subjects since the
last tag), prepends the web ``VERSION_HISTORY`` entry, and re-verifies
the whole tree. It does NOT run git commit/tag/push; the workflow (or
you) does that::

    python tools/autorelease.py --prepare              # auto patch bump
    python tools/autorelease.py --prepare --dry-run    # show what would happen
    python tools/autorelease.py --prepare --version 2.1.0 --notes "..."

Version choice: if ``__version__`` in ``src/hea_bench/__init__.py`` is
already ahead of the latest ``v*`` tag (someone ran
``tools/version.py --set X.Y.0`` for a minor/major bump), that version
is released as-is; otherwise the patch number is incremented. If HEAD
*is* the latest tag's commit there is nothing to release and the script
exits cleanly.

The last line of stdout is always ``version=X.Y.Z`` (empty value when
there is nothing to release) so a workflow can capture it directly into
``$GITHUB_OUTPUT``.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import version as version_tool  # tools/version.py, the stamping SSOT

MAX_HISTORY_NOTES = 400  # chars; the web What's-new popover is small


def _git(*args: str) -> str:
    out = subprocess.run(["git", *args], cwd=ROOT, check=True,
                         capture_output=True, text=True)
    return out.stdout.strip()


def latest_tag() -> str | None:
    tags = _git("tag", "--list", "v[0-9]*", "--sort=-v:refname").splitlines()
    return tags[0] if tags else None


def _parse(v: str) -> tuple[int, int, int]:
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", v)
    if not m:
        raise SystemExit(f"not a semver X.Y.Z: {v!r}")
    return tuple(int(x) for x in m.groups())  # type: ignore[return-value]


def compute_target(canon: str, last: str | None) -> str:
    """Patch-bump the canonical version, or honor a hand-made pre-bump."""
    if last is None:
        return canon
    c, tag = _parse(canon), _parse(last.lstrip("v"))
    if c > tag:
        return canon  # someone already ran version.py --set for minor/major
    if c == tag:
        return f"{c[0]}.{c[1]}.{c[2] + 1}"
    raise SystemExit(
        f"canonical __version__ {canon} is BEHIND the latest tag {last}; "
        "the tree is in a broken state, fix it before releasing")


def commit_subjects(last: str | None) -> list[str]:
    rng = f"{last}..HEAD" if last else "HEAD"
    subjects = _git("log", rng, "--no-merges", "--pretty=%s").splitlines()
    keep = []
    for s in subjects:
        if s.startswith("Release v"):
            continue
        keep.append(s.replace("[no-release]", "").strip())
    return [s for s in keep if s]


def promote_changelog(target: str, today: str, bullets: list[str]) -> None:
    """Turn ## [Unreleased] into the new release section (keeping a fresh one).

    If a human/agent already wrote notes under Unreleased they are used
    verbatim; otherwise the pushed commit subjects become the bullets.
    """
    p = ROOT / "CHANGELOG.md"
    text = p.read_text(encoding="utf-8")
    m = re.search(r"^## \[Unreleased\]\s*?\n(.*?)(?=^## \[)", text,
                  re.M | re.S)
    if not m:
        raise SystemExit("CHANGELOG.md: cannot find the '## [Unreleased]' "
                         "section followed by a previous release section")
    body = m.group(1).strip("\n")
    if not body.strip():
        lines = "\n".join(f"- {s}" for s in bullets) or "- Maintenance release."
        body = f"### Changed\n\n{lines}"
    section = f"## [Unreleased]\n\n## [{target}] — {today}\n\n{body}\n\n"
    p.write_text(text[:m.start()] + section + text[m.end():], encoding="utf-8")


def prepend_history(target: str, today: str, notes: str) -> None:
    """Add the release to the top of the web app's VERSION_HISTORY array."""
    p = ROOT / "web" / "index.html"
    text = p.read_text(encoding="utf-8")
    anchor = "const VERSION_HISTORY = [\n"
    i = text.find(anchor)
    if i < 0:
        raise SystemExit("web/index.html: 'const VERSION_HISTORY = [' not found")
    if len(notes) > MAX_HISTORY_NOTES:
        notes = notes[:MAX_HISTORY_NOTES - 1].rstrip() + "…"
    entry = (f'        {{ version: "{target}", date: "{today}", '
             f'notes: {json.dumps(notes)} }},\n')
    j = i + len(anchor)
    p.write_text(text[:j] + entry + text[j:], encoding="utf-8")


def prepare(explicit_version: str | None, explicit_notes: str | None,
            dry_run: bool) -> int:
    canon = version_tool.canonical(ROOT)
    last = latest_tag()
    if last and _git("rev-parse", "HEAD") == _git("rev-parse", f"{last}^{{commit}}"):
        print(f"HEAD is already the released commit for {last}; nothing to do.")
        print("version=")
        return 0
    target = explicit_version or compute_target(canon, last)
    if explicit_version:
        _parse(explicit_version)
        if last and _parse(explicit_version) <= _parse(last.lstrip("v")):
            raise SystemExit(f"--version {explicit_version} is not after {last}")
    subjects = commit_subjects(last)
    notes = explicit_notes or "; ".join(subjects) or "Maintenance release"
    print(f"canonical {canon}, latest tag {last or '(none)'} -> release {target}")
    print(f"notes: {notes}")
    if dry_run:
        print("dry run: no files written.")
        print("version=")
        return 0
    today = datetime.date.today().isoformat()
    version_tool.set_version(target, ROOT)   # stamps + re-checks all surfaces
    promote_changelog(target, today, subjects)
    prepend_history(target, today, notes)
    problems = version_tool.check(ROOT)
    if problems:
        raise SystemExit("post-prepare verification failed:\n  " +
                         "\n  ".join(problems))
    print(f"prepared release {target}: stamped, changelog and history written.")
    print(f"version={target}")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prepare", action="store_true", required=True,
                    help="prepare the release files (the only action)")
    ap.add_argument("--version", help="release exactly this version "
                    "(default: auto patch bump / honor a pre-bumped tree)")
    ap.add_argument("--notes", help="one-line What's-new text for the web "
                    "history (default: the commit subjects since the last tag)")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the decision, write nothing")
    args = ap.parse_args(argv)
    return prepare(args.version, args.notes, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
