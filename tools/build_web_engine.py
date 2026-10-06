"""Assemble the app's in-browser engine under web/engine/ (never committed).

The web app and the desktop shell run the real hea_bench package inside
Pyodide, so every engine-backed number in the app is the library's own.
This script puts two things in place:

1. ``web/engine/pyodide/``: the pinned Pyodide runtime and the wheels the
   library needs (numpy, scipy, scikit-learn and their dependencies),
   downloaded from the official Pyodide CDN and refused unless every
   SHA-256 matches the pin below.
2. ``web/engine/hea-bench.zip``: the package source, the redistributable
   raw datasets (everything tracked under data/raw, which never includes
   the unlicensed Peivaste CSV that the app fetches from its authors at
   run time) and the published baseline table, zipped deterministically,
   plus ``web/engine/manifest.json`` naming its hash.

Run from the repository root:

    python tools/build_web_engine.py           # build (cached downloads are reused)
    python tools/build_web_engine.py --check   # verify an existing build, exit 1 if stale

pages.yml and the desktop build run it before publishing.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import pathlib
import subprocess
import sys
import time
import urllib.request
import zipfile

REPO = pathlib.Path(__file__).resolve().parents[1]
ENGINE = REPO / "web" / "engine"
PYODIDE_DIR = ENGINE / "pyodide"
ZIP_PATH = ENGINE / "hea-bench.zip"
MANIFEST_PATH = ENGINE / "manifest.json"

PYODIDE_VERSION = "0.29.5"
CDN = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/"

#: Every runtime file the browser loads, pinned. A Pyodide upgrade means
#: new pins here and a green tests/test_web_engine.py, nothing else.
PYODIDE_FILES = {
    "pyodide.js": "7f832a350240263d9946a9c3c877f7bcdab6c37d6dc65f72cd3be5905dca62dd",
    "pyodide.asm.js": "356c42f69e1695397e9d8670bd3c2e678248cde76e18bdae1731e848537b47d7",
    "pyodide.asm.wasm": "54309a5a2cfd757b1f0fdbc9093c92503f7b341500110329d932487183912718",
    "python_stdlib.zip": "831fd1e535084b972f87c6a35275de3d236efd5166f5e77ce89497710635e73c",
    "pyodide-lock.json": "14d2c2dba101277999e17135e653d8f15389ad1437f53eae213bf0c3cdff723d",
    "numpy-2.2.5-cp313-cp313-pyemscripten_2025_0_wasm32.whl":
        "800c98edc0c864dfa49f07005680c699b4b42b84eae1f8cb19d35b3634e7f05c",
    "scipy-1.14.1-cp313-cp313-pyemscripten_2025_0_wasm32.whl":
        "7a60ad5e52acd8d8059f4acc0932d701c3e07723d82e567523dd1a6e0e85ec3e",
    "scikit_learn-1.7.0-cp313-cp313-pyemscripten_2025_0_wasm32.whl":
        "5dd1611a1ee57147a4387e56499bb1def407919ef452efb50beb5229dbe4a3db",
    "joblib-1.4.2-py3-none-any.whl":
        "f07902625672ca0d92e979870ff501e4138589ff3b2b734680d07863676f9996",
    "threadpoolctl-3.5.0-py3-none-any.whl":
        "0d768335eaa50416503e8e5c2c8a51eb96fc9b1c051f02be30bf694707d9a981",
    "libopenblas-0.3.26.zip": "e958192aa6fe14de37ecfb58740a4ee04a6ff68d971d2a0841280594723037e4",
}

#: Repository paths shipped inside hea-bench.zip (tracked or new files only,
#: so local scratch, caches and the gitignored Peivaste CSV never ship).
ZIP_ROOTS = ("src/hea_bench", "data/raw", "docs/benchmark-baselines.json")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _download(name: str) -> bytes:
    url = CDN + name
    for attempt in range(1, 5):
        try:
            with urllib.request.urlopen(url, timeout=120) as response:
                return response.read()
        except Exception as error:  # noqa: BLE001 - retried, then reported
            if attempt == 4:
                raise SystemExit(f"download failed after 4 attempts: {url}: {error}") from None
            time.sleep(5 * attempt)
    raise AssertionError("unreachable")


def fetch_pyodide() -> None:
    PYODIDE_DIR.mkdir(parents=True, exist_ok=True)
    # Files an older pin left behind would ship inside the site and the exe.
    for leftover in PYODIDE_DIR.iterdir():
        if leftover.name not in PYODIDE_FILES:
            leftover.unlink()
            print(f"removed {leftover.name} (not pinned)")
    for name, expected in PYODIDE_FILES.items():
        target = PYODIDE_DIR / name
        if target.exists() and _sha256(target.read_bytes()) == expected:
            continue
        data = _download(name)
        actual = _sha256(data)
        if actual != expected:
            raise SystemExit(
                f"{name}: SHA-256 {actual} does not match the pin {expected}. The CDN served "
                f"different bytes; do not re-pin without re-running tests/test_web_engine.py."
            )
        target.write_bytes(data)
        print(f"fetched {name} ({len(data):,} bytes)")


def _zip_members() -> list[str]:
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", *ZIP_ROOTS],
        cwd=REPO, check=True, capture_output=True, text=True,
    ).stdout.split("\n")
    return sorted(
        path for path in listed
        if path and (REPO / path).is_file() and "__pycache__" not in path
    )


def build_zip() -> bytes:
    """The package archive, byte-identical for identical inputs."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in _zip_members():
            info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, (REPO / path).read_bytes())
    return buffer.getvalue()


def _manifest(zip_bytes: bytes) -> dict:
    sys.path.insert(0, str(REPO / "src"))
    from hea_bench import __version__

    return {
        "hea_bench_version": __version__,
        "pyodide_version": PYODIDE_VERSION,
        "zip_sha256": _sha256(zip_bytes),
        "zip_bytes": len(zip_bytes),
        "pyodide_files": PYODIDE_FILES,
    }


def check() -> list[str]:
    """Problems with the current build; empty means current and complete."""
    problems = []
    for name, expected in PYODIDE_FILES.items():
        target = PYODIDE_DIR / name
        if not target.exists():
            problems.append(f"missing web/engine/pyodide/{name}")
        elif _sha256(target.read_bytes()) != expected:
            problems.append(f"web/engine/pyodide/{name} does not match its pin")
    if PYODIDE_DIR.exists():
        problems += [
            f"web/engine/pyodide/{leftover.name} is not pinned (left over from an older runtime)"
            for leftover in sorted(PYODIDE_DIR.iterdir())
            if leftover.name not in PYODIDE_FILES
        ]
    zip_bytes = build_zip()
    if not ZIP_PATH.exists() or ZIP_PATH.read_bytes() != zip_bytes:
        problems.append("web/engine/hea-bench.zip is missing or stale")
    if not MANIFEST_PATH.exists() or json.loads(MANIFEST_PATH.read_text()) != _manifest(zip_bytes):
        problems.append("web/engine/manifest.json is missing or stale")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true", help="verify only, never download")
    args = parser.parse_args()
    if args.check:
        problems = check()
        for problem in problems:
            print(f"STALE: {problem}")
        if problems:
            print("fix: python tools/build_web_engine.py")
        return 1 if problems else 0
    fetch_pyodide()
    zip_bytes = build_zip()
    ZIP_PATH.write_bytes(zip_bytes)
    MANIFEST_PATH.write_text(json.dumps(_manifest(zip_bytes), indent=2) + "\n", encoding="utf-8")
    print(f"wrote web/engine/hea-bench.zip ({len(zip_bytes):,} bytes) and manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
