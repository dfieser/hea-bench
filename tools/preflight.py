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
