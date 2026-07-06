#!/usr/bin/env python3
"""Single source of truth for the hea-bench version.

The canonical version is ``__version__`` in ``src/hea_bench/__init__.py``.
Files a toolchain already reads dynamically are intentionally NOT handled here:

* ``pyproject.toml``            -> hatchling ``dynamic`` reads __init__.py
* ``src-tauri/tauri.conf.json`` -> inherits ``src-tauri/Cargo.toml`` (no version key)
* CLI / MCP server / tests      -> ``from . import __version__``

This script stamps and verifies everything else::

    python tools/version.py --check       # CI gate: nonzero exit on any drift
    python tools/version.py --set 2.1.0   # bump the canonical value + restamp

``--set`` also moves the two release-date fields to today and re-verifies the
whole tree before reporting success, so a pattern that has drifted fails loudly
instead of leaving a silent partial bump. The append-only histories
(CHANGELOG.md and the web VERSION_HISTORY list) are left to a human.
"""
from __future__ import annotations

import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANON_FILE = "src/hea_bench/__init__.py"

# file -> [(regex with ONE capturing group, label)]. --check asserts every
# captured value equals the canonical version; --set rewrites each to `new`.
VERSION_TARGETS = {
    CANON_FILE: [(re.compile(r'__version__ = "([^"]+)"'), "__version__")],
    "src-tauri/Cargo.toml": [(re.compile(r'(?ms)^\[package\].*?^version = "([^"]+)"'), "[package] version")],
    # scoped to the workspace crate so dependency versions are never touched
    "src-tauri/Cargo.lock": [(re.compile(r'(?m)^name = "hea-bench"\nversion = "([^"]+)"'), "[[package]] hea-bench")],
    "server.json": [(re.compile(r'"version"\s*:\s*"([^"]+)"'), "version")],
    "CITATION.cff": [(re.compile(r'(?m)^version: (\S+)'), "version")],
    "llms.txt": [(re.compile(r'shipping\s+version (\d+\.\d+\.\d+)'), "prose"),
                 (re.compile(r'version = \{([^}]+)\}'), "bibtex")],
    "web/index.html": [(re.compile(r'const VERSION = "([^"]+)"'), "const VERSION")],
}

# (file, label) -> exact number of matches expected, so a structural change
# (e.g. a new server.json packages[] entry) fails loudly rather than being
# silently over-stamped or under-checked.
EXPECTED_HITS = {
    ("server.json", "version"): 2,
}

# release-date fields moved to today on every --set: (prefix)(date)(suffix).
DATE_TARGETS = {
    "CITATION.cff": re.compile(r"(date-released: ')(\d{4}-\d{2}-\d{2})(')"),
    "web/index.html": re.compile(r'(const VERSION_DATE = ")(\d{4}-\d{2}-\d{2})(")'),
}

ORCID_RE = re.compile(r"\d{4}-\d{4}-\d{4}-[\dxX]{4}")


def _read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def canonical(root: Path = ROOT) -> str:
    rx = VERSION_TARGETS[CANON_FILE][0][0]
    m = rx.search(_read(root, CANON_FILE))
    if not m:
        raise SystemExit(f"cannot find __version__ in {CANON_FILE}")
    return m.group(1)


def check(root: Path = ROOT) -> list[str]:
    """Return a list of drift problems; empty list means everything agrees."""
    canon = canonical(root)
    problems: list[str] = []
    for rel, rules in VERSION_TARGETS.items():
        text = _read(root, rel)
        for rx, label in rules:
            hits = rx.findall(text)
            if not hits:
                problems.append(f"{rel}: {label} matched nothing")
            expected = EXPECTED_HITS.get((rel, label))
            if expected is not None and len(hits) != expected:
                problems.append(f"{rel}: {label} expected {expected} matches, found {len(hits)} (update tools/version.py)")
            problems += [f"{rel}: {label} = {v!r} != {canon!r}" for v in hits if v != canon]
    # tauri.conf.json must NOT pin a version (it inherits Cargo.toml)
    if "version" in json.loads(_read(root, "src-tauri/tauri.conf.json")):
        problems.append("src-tauri/tauri.conf.json still pins 'version'; delete the key so it inherits src-tauri/Cargo.toml")
    # the two release-date fields must agree with each other
    dates = []
    for rel, rx in DATE_TARGETS.items():
        m = rx.search(_read(root, rel))
        if not m:
            problems.append(f"{rel}: release-date field matched nothing")
        else:
            dates.append(m.group(2))
    if len(set(dates)) > 1:
        problems.append(f"release dates disagree across files: {sorted(set(dates))}")
    # .zenodo.json authors must match CITATION.cff (Zenodo prefers .zenodo.json)
    zenodo_orcids = {c["orcid"] for c in json.loads(_read(root, ".zenodo.json")).get("creators", []) if c.get("orcid")}
    cff_orcids = set(ORCID_RE.findall(_read(root, "CITATION.cff")))
    if zenodo_orcids != cff_orcids:
        problems.append(f".zenodo.json ORCIDs {sorted(zenodo_orcids)} != CITATION.cff ORCIDs {sorted(cff_orcids)}")
    return problems


def set_version(new: str, root: Path = ROOT) -> None:
    if not re.fullmatch(r"\d+\.\d+\.\d+", new):
        raise SystemExit(f"not a semver X.Y.Z: {new!r}")
    today = datetime.date.today().isoformat()
    failures: list[str] = []
    for rel, rules in VERSION_TARGETS.items():
        p = root / rel
        text = p.read_text(encoding="utf-8")
        for rx, label in rules:
            text, n = rx.subn(lambda m: m.group(0).replace(m.group(1), new), text)
            if n == 0:
                failures.append(f"{rel}: {label} matched nothing to stamp")
        p.write_text(text, encoding="utf-8")
    for rel, rx in DATE_TARGETS.items():
        p = root / rel
        text = p.read_text(encoding="utf-8")
        text, n = rx.subn(lambda m: m.group(1) + today + m.group(3), text)
        if n == 0:
            failures.append(f"{rel}: release-date field matched nothing to stamp")
        p.write_text(text, encoding="utf-8")
    if failures:
        raise SystemExit("stamp failed (patterns drifted):\n  " + "\n  ".join(failures))
    problems = check(root)
    if problems:
        raise SystemExit("post-stamp verification failed:\n  " + "\n  ".join(problems))
    print(f"stamped {new} (date {today}). Add a CHANGELOG.md section and a "
          f"web/index.html VERSION_HISTORY entry, then commit and tag v{new}.")


def main(argv: list[str]) -> int:
    if argv[:1] == ["--set"]:
        if len(argv) != 2:
            raise SystemExit("usage: python tools/version.py --set X.Y.Z")
        set_version(argv[1])
        return 0
    if argv not in ([], ["--check"]):
        raise SystemExit(f"usage: python tools/version.py [--check | --set X.Y.Z]; got {argv}")
    problems = check()
    if problems:
        print("VERSION DRIFT:\n  " + "\n  ".join(problems))
        return 1
    print(f"OK: all files agree at {canonical()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
