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
a rebuild of the in-app engine bundle when its pinned runtime is already
on disk, and the full pytest suite, including the installed-package gate
(the built wheel installed fresh, every MCP tool called over stdio, about
two minutes), then reports which release gates could NOT be verified
locally (a missing corpus skips the benchmark-freeze evidence, a missing
Node skips the JS parity evidence, a missing engine bundle skips the
engine parity evidence, and the desktop exe smoke test needs a built
exe) so the risk is taken knowingly rather than by accident.

The ratchet rule: whenever a release fails for a new reason, the same
change that fixes it must teach this script (or the CI gate) to catch
that reason before the next push. Checks are only added, never removed.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from version import VERSION_TARGETS  # noqa: E402  (the version stamp table)

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


#: README graphics, generated by tools/make_icons.py and
#: tools/make_screenshots.py.
README_ASSETS = {
    "banner-light.png", "banner-dark.png",
    "screenshot-calculator-light.png", "screenshot-calculator-dark.png",
}

RAW_PREFIX = "https://raw.githubusercontent.com/dfieser/hea-bench/main/"


def check_readme_assets() -> list[str]:
    """Keep the README's graphics working on GitHub *and* PyPI.

    pyproject sets ``readme = "README.md"``, so this file is also the
    PyPI long description. PyPI resolves nothing relative to the
    repository, so a relative image path renders on GitHub and shows a
    broken image on the package page, where nobody involved will see it.
    """
    problems: list[str] = []
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for name in sorted(README_ASSETS):
        if not (ROOT / "docs" / "assets" / name).exists():
            problems.append(
                f"docs/assets/{name}: missing; run: python tools/make_icons.py "
                f"and python tools/make_screenshots.py"
            )
        if name not in readme:
            problems.append(f"README.md: no longer references docs/assets/{name}")

    # Every image the README points at must be an absolute https URL, and
    # any that points into this repository must resolve to a real file.
    for url in re.findall(r'<(?:img[^>]+src|source[^>]+srcset)="([^"]+)"', readme):
        if not url.startswith("https://"):
            problems.append(
                f"README.md: image {url!r} is not an absolute https URL, so it "
                f"renders broken on PyPI"
            )
        elif url.startswith(RAW_PREFIX):
            rel = url[len(RAW_PREFIX):]
            if not (ROOT / rel).exists():
                problems.append(f"README.md: image {url!r} points at missing {rel}")
    for alt, path in re.findall(r'!\[([^\]]*)\]\((?!https://)([^)]+)\)', readme):
        problems.append(
            f"README.md: markdown image {alt!r} uses relative path {path!r}; "
            f"PyPI cannot resolve it, use {RAW_PREFIX}..."
        )
    return problems


def _dockerignored(path: str, patterns: list[str]) -> bool:
    """Docker's rule: the last pattern matching the path or a parent wins."""
    parts = path.split("/")
    candidates = ["/".join(parts[: i + 1]) for i in range(len(parts))]
    excluded = False
    for pattern in patterns:
        negated = pattern.startswith("!")
        pattern = pattern.lstrip("!").strip("/")
        if any(fnmatch.fnmatchcase(c, pattern) for c in candidates):
            excluded = not negated
    return excluded


def check_docker_context() -> list[str]:
    """The MCP container builds: every file the wheel bundles reaches it.

    Directory listings (Glama) build the Dockerfile to check the server.
    The wheel force-includes files from outside src/ (pyproject.toml), so
    each must sit under a path the Dockerfile copies and must survive
    .dockerignore, or hatchling stops the image build.
    """
    problems: list[str] = []
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    section = pyproject.split("[tool.hatch.build.targets.wheel.force-include]", 1)[1]
    section = section.split("\n[", 1)[0]
    bundled = re.findall(r'^"([^"]+)"\s*=', section, flags=re.MULTILINE)
    copied = [
        source
        for line in (ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines()
        if line.startswith("COPY ") and "--from=" not in line
        for source in line.split()[1:-1]
    ]
    ignore = [
        line.strip()
        for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

    def reaches_image(path: str) -> bool:
        under_copy = any(path == c or path.startswith(c.rstrip("/") + "/") for c in copied)
        return under_copy and not _dockerignored(path, ignore)

    for path in bundled:
        if not reaches_image(path):
            problems.append(
                f"Dockerfile: the wheel bundles {path} but the image build never sees it; "
                f"COPY it in the build stage and let it through .dockerignore"
            )
    return problems


#: What the desktop exe smoke test runs besides web/. A releasing push
#: that changes any of these since the last release needs a green
#: Desktop smoke run on the same files first: v2.7.1 and v2.7.2 shipped
#: no exe because the test passed on a desktop, and its first run on
#: GitHub's elevated Windows runners was inside the release.
DESKTOP_SMOKE_INPUTS = ("src-tauri", "tests/test_desktop_smoke.py", ".github/workflows/desktop-smoke.yml")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")


def without_version_stamps(rel: str, text: str) -> str:
    """``text`` with every version that tools/version.py stamps into ``rel`` blanked."""

    def blank(m: re.Match) -> str:
        start, end = m.start(1) - m.start(), m.end(1) - m.start()
        return m.group(0)[:start] + "X" + m.group(0)[end:]

    for pattern, _ in VERSION_TARGETS.get(rel, []):
        text = pattern.sub(blank, text)
    return text


def _desktop_inputs_changed(base: str) -> list[str]:
    """Desktop inputs that differ between ``base`` and HEAD beyond the version stamps.

    Every bump rewrites the version in src-tauri/Cargo.toml and Cargo.lock,
    the release bot's patch bumps included, so a bump alone is no new input.
    """
    diff = _git("diff", "--name-only", base, "HEAD", "--", *DESKTOP_SMOKE_INPUTS)
    if diff.returncode:
        return list(DESKTOP_SMOKE_INPUTS)  # base is not in this clone: assume everything changed
    return [
        rel for rel in diff.stdout.split()
        if without_version_stamps(rel, _git("show", f"{base}:{rel}").stdout)
        != without_version_stamps(rel, _git("show", f"HEAD:{rel}").stdout)
    ]


def check_desktop_smoke() -> list[str]:
    if "[no-release]" in _git("log", "-1", "--format=%B").stdout:
        return []
    _git("fetch", "--tags", "--quiet")  # the release bot makes the tags, so a clone can lag
    tag = _git("describe", "--tags", "--abbrev=0", "--match", "v*").stdout.strip()
    if not tag:
        return ["no release tag in this clone to compare against: run git fetch --tags, then preflight again"]
    changed = _desktop_inputs_changed(tag)
    if not changed:
        return []
    try:
        listed = subprocess.run(
            ["gh", "run", "list", "--workflow", "desktop-smoke.yml", "--status", "success",
             "--limit", "50", "--json", "headSha"],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        )
    except OSError:
        return ["the GitHub CLI (gh) is needed to find a green Desktop smoke run: install it, gh auth login"]
    shas = [run["headSha"] for run in json.loads(listed.stdout or "[]")] if listed.returncode == 0 else []
    if any(not _desktop_inputs_changed(sha) for sha in shas):
        return []
    return [
        f"the desktop exe's inputs changed since {tag} ({', '.join(changed)}) and no green "
        "Desktop smoke run covers them, so the release's desktop-build job would be their "
        "first run on GitHub's runners. Commit them with [no-release] in the message, push, "
        "run gh workflow run desktop-smoke.yml --ref main, wait for it to pass (gh run "
        "watch), then push the release."
    ]


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

    problems = check_readme_assets()
    if problems:
        failures.extend(problems)
    print(("FAIL" if problems else "ok  ") + "  README graphics (GitHub + PyPI)")
    for problem in problems:
        print(f"      {problem}")

    problems = check_docker_context()
    if problems:
        failures.extend(problems)
    print(("FAIL" if problems else "ok  ") + "  MCP container build context (Dockerfile)")
    for problem in problems:
        print(f"      {problem}")

    if not args.metadata:
        problems = check_desktop_smoke()
        if problems:
            failures.extend(problems)
        print(("FAIL" if problems else "ok  ") + "  desktop exe inputs smoke-tested on GitHub's runners")
        for problem in problems:
            print(f"      {problem}")

        checks = [
            ("version consistency", [sys.executable, "tools/version.py", "--check"]),
            ("ruff (release-gate lint)", [sys.executable, "-m", "ruff", "check", "src", "tests"]),
            ("pytest (full suite)", [sys.executable, "-m", "pytest", "tests/", "-q", "-rs"]),
        ]
        # The in-app engine bundle (web/engine/) is gitignored. When the
        # pinned Pyodide runtime is already on disk, rebuild the package zip
        # from this tree first (a second, no download), so the engine parity
        # test checks the code being pushed and not an older build.
        engine_runtime = ROOT / "web" / "engine" / "pyodide"
        if engine_runtime.exists():
            checks.insert(
                2,
                ("web engine bundle (rebuilt from this tree)", [sys.executable, "tools/build_web_engine.py"]),
            )
        env_src = os.environ.get("PYTHONPATH", "")
        if "src" not in env_src.split(os.pathsep):
            os.environ["PYTHONPATH"] = os.pathsep.join(p for p in ("src", env_src) if p)
        # The CI package job's gate (tests/test_installed_package.py) is
        # opt-in for plain pytest runs because it builds and installs the
        # wheel; the preflight always runs it.
        os.environ.setdefault("HEA_BENCH_PACKAGE_SMOKE", "1")
        for label, command in checks:
            _, code, output = _run(label, command)
            print(("ok  " if code == 0 else "FAIL") + f"  {label}")
            if code != 0:
                # Print the tail, or an agent cannot see what failed.
                failures.append(f"{label} failed:\n{output[-2000:]}")
                for line in output[-2000:].splitlines():
                    print(f"      {line}")
            elif label.startswith("pytest") and " skipped" in output:
                summary = output.strip().splitlines()[-1]
                warnings.append(f"pytest skipped tests locally: {summary}")
                package = [line.strip() for line in output.splitlines() if "test_installed_package.py" in line]
                if package:
                    warnings.append(
                        f"installed-package gate NOT pre-verified ({package[0]}). Fix what it "
                        "names, or expect the CI package job to be the first real run."
                    )
                smoke = [line.strip() for line in output.splitlines() if "test_app_smoke.py" in line]
                if smoke:
                    warnings.append(
                        f"browser smoke gate NOT pre-verified ({smoke[0]}). If this push "
                        "touches web/ or src/hea_bench, build the engine (python "
                        "tools/build_web_engine.py) and install Chrome or Edge (or set "
                        "HEA_BENCH_BROWSER), then preflight again, or expect the CI "
                        "web-engine job to be the first real run."
                    )

        # Gates that cannot run without local assets: name them so the
        # risk of pushing anyway is taken knowingly.
        corpus = ROOT / "data" / "consolidated" / "v0.1.0" / "consolidated.csv"
        if not corpus.exists() and not os.environ.get("HEA_BENCH_BENCHMARK_DIR"):
            warnings.append(
                "benchmark-freeze gate NOT pre-verified: no local corpus. If this "
                "push touches benchmark, corpus, split, or loader code, build the "
                "corpus first (python -m "
                "hea_bench.benchmark.consolidate) or expect the release gate to "
                "be the first real run of those digests."
            )
        if shutil.which("node") is None:
            warnings.append(
                "JS parity gate NOT pre-verified: no Node.js on PATH, the web "
                "parity suites were skipped."
            )
        if not os.environ.get("HEA_BENCH_DESKTOP_EXE"):
            warnings.append(
                "desktop smoke gate NOT pre-verified (it needs a built exe). If this "
                "push touches web/ or src-tauri/, on Windows run python "
                "tools/build_web_engine.py, cargo tauri build --no-bundle, then "
                "HEA_BENCH_DESKTOP_EXE=src-tauri/target/release/hea-bench.exe python "
                "-m pytest tests/test_desktop_smoke.py, or expect the release "
                "desktop-build job to be the first real run."
            )
        if not engine_runtime.exists():
            warnings.append(
                "web-engine gate NOT pre-verified: no local engine bundle, so "
                "tests/test_web_engine.py was skipped. If this push touches "
                "src/hea_bench or web/, run python tools/build_web_engine.py once "
                "(downloads the pinned ~30 MB Pyodide runtime) and preflight again, "
                "or expect the CI web-engine job to be the first real run."
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
