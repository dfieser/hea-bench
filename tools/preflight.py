#!/usr/bin/env python3
"""Pre-push release preflight: run every gate that can run locally.

Every hea-bench release failure to date (the catalog lives in
RELEASING.md) happened at a check that either could have run before the
push and did not, or existed only inside an external publisher. This
script is the single command that closes that gap::

    python tools/preflight.py             # full preflight, run before any push
    python tools/preflight.py --metadata  # publish-metadata checks only (stdlib,
                                          # seconds; CI and the release bot run this)

Full mode runs, in order: the publish-metadata checks, the version
consistency check, ruff over src and tests (the exact release-gate lint),
and the full pytest suite, then reports which release gates could NOT be
verified locally (a missing corpus skips the benchmark-freeze evidence, a
missing Node skips the JS parity evidence) so the risk is taken knowingly
rather than by accident.

The ratchet rule: whenever a release fails for a new reason, the same
change that fixes it must teach this script (or the CI gate) to catch
that reason before the next push. Checks are only added, never removed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: The MCP registry rejects a server.json whose description exceeds this
#: (HTTP 422, learned from the v2.5.0 release failure on 2026-08-16).
MCP_DESCRIPTION_MAX = 100

#: Registry server-name shape: namespace/name, lowercase.
MCP_NAME_RE = re.compile(r"^[a-z0-9.-]+/[a-z0-9._-]+$")


def _canonical_version() -> str:
    sys.path.insert(0, str(ROOT / "tools"))
    import version as version_tool  # tools/version.py, the stamping SSOT

    return version_tool.canonical(ROOT)


def check_metadata() -> list[str]:
    """Validate everything external publishers will validate later.

    These constraints are enforced by services outside this repository
    (the MCP registry today; extend this list the moment any publisher
    rejects a field), so nothing else in CI would catch them.
    """
    problems: list[str] = []
    path = ROOT / "server.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"server.json: unreadable or invalid JSON ({exc})"]

    for field in ("$schema", "name", "description", "version", "packages"):
        if field not in data:
            problems.append(f"server.json: missing required field {field!r}")
    description = data.get("description", "")
    if len(description) > MCP_DESCRIPTION_MAX:
        problems.append(
            f"server.json: description is {len(description)} characters; the "
            f"MCP registry rejects anything over {MCP_DESCRIPTION_MAX} "
            f"(HTTP 422, the v2.5.0 failure)"
        )
    name = data.get("name", "")
    if name and not MCP_NAME_RE.fullmatch(name):
        problems.append(
            f"server.json: name {name!r} does not match the registry's "
            f"namespace/name shape"
        )

    canonical = _canonical_version()
    if data.get("version") != canonical:
        problems.append(
            f"server.json: version {data.get('version')!r} != canonical {canonical!r}"
        )
    for package in data.get("packages", []):
        if package.get("version") != canonical:
            problems.append(
                f"server.json: packages[] version {package.get('version')!r} "
                f"!= canonical {canonical!r}"
            )
    return problems


#: Web assets the live site's <head> promises. Each maps to the exact
#: square size it must be, or None when only existence matters.
WEB_ASSETS: dict[str, tuple[int, int] | None] = {
    "favicon.ico": None,          # frames checked separately
    "favicon.svg": None,
    "apple-touch-icon.png": (180, 180),
    "icon-192.png": (192, 192),
    "icon-512.png": (512, 512),
    "og-image.png": (1200, 630),  # the Open Graph standard; scrapers crop off-size cards
    "site.webmanifest": None,
}


def _png_size(data: bytes) -> tuple[int, int] | None:
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", data[16:24])


def _ico_sizes(data: bytes) -> set[int]:
    """Widths present in an ICO directory (0 in the header means 256)."""
    if len(data) < 6 or data[2:4] != b"\x01\x00":
        return set()
    count = struct.unpack("<H", data[4:6])[0]
    widths = set()
    for i in range(count):
        entry = 6 + i * 16
        if entry + 16 > len(data):
            break
        widths.add(data[entry] or 256)
    return widths


def check_web_assets() -> list[str]:
    """Guard the SEO assets the <head> promises but no test would open.

    Everything here fails silently and invisibly in production: a missing
    file just means no favicon in Google's results or a blank social
    card, with no error anywhere. Added 2026-08-17 with the crawlable
    favicon set, per the ratchet rule.
    """
    problems: list[str] = []
    web = ROOT / "web"
    head = (web / "index.html").read_text(encoding="utf-8", errors="replace")[:12000]

    for name, expected in WEB_ASSETS.items():
        path = web / name
        if not path.exists():
            problems.append(f"web/{name}: missing; run: python tools/make_icons.py")
            continue
        if expected and name.endswith(".png"):
            actual = _png_size(path.read_bytes())
            if actual != expected:
                problems.append(
                    f"web/{name}: is {actual[0]}x{actual[1]} but must be "
                    f"{expected[0]}x{expected[1]}; run: python tools/make_icons.py"
                )

    ico = web / "favicon.ico"
    if ico.exists() and 48 not in _ico_sizes(ico.read_bytes()):
        problems.append(
            "web/favicon.ico: no 48x48 frame, which is the size Google's "
            "result-favicon crawler requests; run: python tools/make_icons.py"
        )

    # A data: URI or a missing tag means no favicon in search results.
    for name in ("favicon.ico", "favicon.svg", "apple-touch-icon.png", "site.webmanifest"):
        if f'href="{name}"' not in head:
            problems.append(
                f'web/index.html: <head> does not reference {name} with a relative '
                f'href="{name}"'
            )
    if 'href="data:image' in head:
        problems.append(
            "web/index.html: a data: URI icon is back in <head>; Google cannot "
            "crawl it, so search results lose the favicon"
        )
    # Project page: a root-absolute icon path resolves against the user
    # site (dfieser.github.io), which this repository does not own.
    if re.search(r'<link[^>]+rel="(?:icon|apple-touch-icon|manifest)"[^>]+href="/', head):
        problems.append(
            'web/index.html: root-absolute icon href; this is a project page '
            'served from /hea-bench/, so icon paths must be relative'
        )
    # Scrapers do not resolve relative og:image URLs.
    match = re.search(r'<meta property="og:image" content="([^"]+)"', head)
    if not match:
        problems.append('web/index.html: no og:image, so shared links render a blank card')
    elif not match.group(1).startswith("https://"):
        problems.append(
            f'web/index.html: og:image {match.group(1)!r} is not absolute; '
            f"scrapers do not resolve relative Open Graph URLs"
        )

    # A malformed manifest or JSON-LD block fails silently: the browser
    # drops the manifest, and Google drops the rich result, with no error.
    try:
        json.loads((web / "site.webmanifest").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        problems.append(f"web/site.webmanifest: invalid JSON ({exc})")
    full = (web / "index.html").read_text(encoding="utf-8", errors="replace")
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', full, re.S)
    if not blocks:
        problems.append("web/index.html: the JSON-LD structured-data block is gone")
    for i, block in enumerate(blocks):
        try:
            json.loads(block)
        except ValueError as exc:
            problems.append(f"web/index.html: JSON-LD block {i} is invalid JSON ({exc})")
    return problems


def _run(label: str, command: list[str]) -> tuple[str, int, str]:
    completed = subprocess.run(
        command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
    )
    output = (completed.stdout or "") + (completed.stderr or "")
    return label, completed.returncode, output


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--metadata",
        action="store_true",
        help="run only the publish-metadata checks (stdlib, no dev extras)",
    )
    args = parser.parse_args(argv)

    failures: list[str] = []
    warnings: list[str] = []

    problems = check_metadata()
    if problems:
        failures.extend(problems)
    print(("FAIL" if problems else "ok  ") + "  publish metadata (server.json)")
    for problem in problems:
        print(f"      {problem}")

    problems = check_web_assets()
    if problems:
        failures.extend(problems)
    print(("FAIL" if problems else "ok  ") + "  web assets (icons, social card)")
    for problem in problems:
        print(f"      {problem}")

    if not args.metadata:
        checks = [
            ("version consistency", [sys.executable, "tools/version.py", "--check"]),
            ("ruff (release-gate lint)", [sys.executable, "-m", "ruff", "check", "src", "tests"]),
            ("pytest (full suite)", [sys.executable, "-m", "pytest", "tests/", "-q", "-rs"]),
        ]
        env_src = os.environ.get("PYTHONPATH", "")
        if "src" not in env_src.split(os.pathsep):
            os.environ["PYTHONPATH"] = os.pathsep.join(p for p in ("src", env_src) if p)
        for label, command in checks:
            _, code, output = _run(label, command)
            print(("ok  " if code == 0 else "FAIL") + f"  {label}")
            if code != 0:
                failures.append(f"{label} failed:\n{output[-2000:]}")
            elif label.startswith("pytest") and " skipped" in output:
                summary = output.strip().splitlines()[-1]
                warnings.append(f"pytest skipped tests locally: {summary}")

        # Gates that cannot run without local assets: name them so the
        # risk of pushing anyway is taken knowingly.
        corpus = ROOT / "data" / "consolidated" / "v0.1.0" / "consolidated.csv"
        if not corpus.exists() and not os.environ.get("HEA_BENCH_BENCHMARK_DIR"):
            warnings.append(
                "benchmark-freeze gate NOT pre-verified: no local corpus. If this "
                "push touches benchmark, corpus, split, or loader code, build the "
                "corpus first (python data/raw/peivaste/fetch.py && python -m "
                "hea_bench.benchmark.consolidate) or expect the release gate to "
                "be the first real run of those digests."
            )
        if shutil.which("node") is None:
            warnings.append(
                "JS parity gate NOT pre-verified: no Node.js on PATH, the web "
                "parity suites were skipped."
            )

    for warning in warnings:
        print(f"warn  {warning}")

    if failures:
        print(f"\npreflight: {len(failures)} blocking problem(s); do not push.")
        return 1
    print("\npreflight: all locally verifiable release gates pass.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
