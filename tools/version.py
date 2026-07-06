#!/usr/bin/env python3
"""Single source of truth for the hea-bench version.

The canonical version is ``__version__`` in ``src/hea_bench/__init__.py``.
Files a toolchain already reads dynamically are intentionally NOT listed here:

* ``pyproject.toml``     -> hatchling ``dynamic = ["version"]`` reads __init__.py
* ``src-tauri/tauri.conf.json`` -> inherits ``src-tauri/Cargo.toml`` (no version key)
* CLI / MCP server / tests -> ``from . import __version__``

This script stamps and verifies only the files no toolchain reads::

    python tools/version.py --check       # CI gate: nonzero exit on any drift
    python tools/version.py --set 2.1.0   # bump the canonical value + restamp

``--set`` also moves the two release-date fields to today so the number and
its date never diverge. The append-only histories (CHANGELOG.md and the
web/index.html VERSION_HISTORY list) are left to a human, like a changelog.
"""
from __future__ import annotations

import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANON_FILE = "src/hea_bench/__init__.py"
CANON_RE = re.compile(r'__version__ = "([^"]+)"')

# file -> [(regex with ONE capturing group, label)]. --check asserts every
# captured value equals the canonical version; --set rewrites each to `new`.
VERSION_TARGETS = {
    "src/hea_bench/__init__.py": [(re.compile(r'__version__ = "([^"]+)"'), "__version__")],
    "src-tauri/Cargo.toml": [(re.compile(r'(?ms)^\[package\].*?^version = "([^"]+)"'), "[package] version")],
    "server.json": [(re.compile(r'"version"\s*:\s*"([^"]+)"'), "version (x2)")],
    "CITATION.cff": [(re.compile(r'(?m)^version: (\S+)'), "version")],
    "llms.txt": [(re.compile(r'version (\S+) under MIT'), "prose"),
                 (re.compile(r'version = \{([^}]+)\}'), "bibtex")],
    "web/index.html": [(re.compile(r'const VERSION = "([^"]+)"'), "const VERSION")],
}

# date fields that move to today on every bump: (prefix)(date)(suffix).
DATE_TARGETS = {
    "CITATION.cff": re.compile(r"(date-released: ')(\d{4}-\d{2}-\d{2})(')"),
    "web/index.html": re.compile(r'(const VERSION_DATE = ")(\d{4}-\d{2}-\d{2})(")'),
}


def canonical(root: Path = ROOT) -> str:
    text = (root / CANON_FILE).read_text(encoding="utf-8")
    m = CANON_RE.search(text)
    if not m:
        raise SystemExit(f"cannot find __version__ in {CANON_FILE}")
    return m.group(1)


def check(root: Path = ROOT) -> list[str]:
    """Return a list of drift problems; empty list means everything agrees."""
    canon = canonical(root)
    problems: list[str] = []
    for rel, rules in VERSION_TARGETS.items():
        text = (root / rel).read_text(encoding="utf-8")
        for rx, label in rules:
            hits = rx.findall(text)
            if not hits:
                problems.append(f"{rel}: {label} matched nothing")
            problems += [f"{rel}: {label} = {v!r} != {canon!r}" for v in hits if v != canon]
    tauri = json.loads((root / "src-tauri/tauri.conf.json").read_text(encoding="utf-8"))
    if "version" in tauri:
        problems.append(
            "src-tauri/tauri.conf.json still pins 'version'; delete the key so it "
            "inherits src-tauri/Cargo.toml"
        )
    return problems


def set_version(new: str, root: Path = ROOT) -> None:
    if not re.fullmatch(r"\d+\.\d+\.\d+", new):
        raise SystemExit(f"not a semver X.Y.Z: {new!r}")
    today = datetime.date.today().isoformat()
    for rel, rules in VERSION_TARGETS.items():
        p = root / rel
        text = p.read_text(encoding="utf-8")
        for rx, _ in rules:
            text = rx.sub(lambda m: m.group(0).replace(m.group(1), new), text)
        p.write_text(text, encoding="utf-8")
    for rel, rx in DATE_TARGETS.items():
        p = root / rel
        text = p.read_text(encoding="utf-8")
        text = rx.sub(lambda m: m.group(1) + today + m.group(3), text)
        p.write_text(text, encoding="utf-8")
    print(
        f"stamped {new} (date {today}). Now add a CHANGELOG.md section and a "
        f"web/index.html VERSION_HISTORY entry, then commit and tag v{new}."
    )


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "--set":
        set_version(argv[1])
        return 0
    problems = check()
    if problems:
        print("VERSION DRIFT:\n  " + "\n  ".join(problems))
        return 1
    print(f"OK: all files agree at {canonical()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
