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

PYODIDE_VERSION = "0.29.3"
CDN = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/"

#: Every runtime file the browser loads, pinned. A Pyodide upgrade means
#: new pins here and a green tests/test_web_engine.py, nothing else.
PYODIDE_FILES = {
    "pyodide.js": "718d40f1c015dd25ec724cc8fc4e2325d6a45a92ae225121ff6953f224a16f72",
    "pyodide.asm.js": "1263f02b5b26099b96112378156f242dd98b39a8201ba7765e5fe3d455c5ce91",
    "pyodide.asm.wasm": "e2f4ee75b325e35eb31bfb8c613d4dd5098f5502c156a97847686875b5025480",
    "python_stdlib.zip": "4298b6ee445cb724c3973437da47789752b9e6ff4e26619026b283ec801fc46b",
    "pyodide-lock.json": "3256ffc76388de0e37f4b34d42ab484268d1afc675179ff97b2a5bb14f84ccac",
    "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl":
        "6eaab6a7bb658d71ebe702911a3deab715323642462eb41b65565ca6a7cc23f1",
    "scipy-1.14.1-cp313-cp313-pyodide_2025_0_wasm32.whl":
        "96fbc718e81cf54ac7df7d8a2c24e370fa3c45086e917c3d58752207d85d21af",
    "scikit_learn-1.7.0-cp313-cp313-pyodide_2025_0_wasm32.whl":
        "267a184f7d3c2cd236a17d729b0f62993c581337b40ee7f99f00e0598dfdb5c2",
    "joblib-1.4.2-py3-none-any.whl":
        "f6cd3ff44cc58faa3216f8778048b37792822183fd5ece300bd9a5d7f1be72ba",
    "threadpoolctl-3.5.0-py3-none-any.whl":
        "a6c097ecbc46c97610e6fdf44e270d6cdc07fa5291b24db0e3d2427ee15c3478",
    "libopenblas-0.3.26.zip": "f8f5db65c9367ed7f057d0ee853d94ddb3c007968aa8138253461dad42537fa2",
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
