"""Download the Peivaste MPEA phase dataset from upstream.

The upstream repo has no LICENSE, so we do not redistribute the CSV inside
hea-bench. This script fetches the file at the user's request, into this
directory, on demand.

Usage:
    python fetch.py
"""

from __future__ import annotations

import hashlib
import pathlib
import sys
import urllib.request

UPSTREAM_URL = (
    "https://raw.githubusercontent.com/Iman-Peivaste/ML_HEAs_Phase_Dataset/"
    "main/Dataset/dataset11252_79.csv"
)
TARGET = pathlib.Path(__file__).resolve().parent / "dataset11252_79.csv"

# Hash of the file used to produce every benchmark statistic reported by
# this package. Pinning it here is how the reproducibility chain is
# closed without redistributing the file: anyone fetching the data can
# verify they have the exact same bytes by comparing the SHA-256.
EXPECTED_BYTES = 6_424_704
EXPECTED_SHA256 = "655a43e521003f5c8973050b5f7c0a5d4b9ab902ca4ecc9c8a7d9813b2b0ba10"


def _hash(path: pathlib.Path) -> tuple[int, str]:
    return path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if TARGET.exists():
        size, sha = _hash(TARGET)
        print(f"already present: {TARGET} ({size} bytes, sha256={sha[:12]}...)")
        if sha != EXPECTED_SHA256:
            print(
                f"  WARNING: SHA-256 differs from the pinned reproducibility "
                f"hash ({EXPECTED_SHA256[:12]}...). The benchmark statistics "
                f"shipped with this package were computed against the pinned "
                f"version. Re-download or report the discrepancy.",
                file=sys.stderr,
            )
            return 2
        return 0

    print(f"downloading {UPSTREAM_URL}")
    print(f"          -> {TARGET}")
    try:
        urllib.request.urlretrieve(UPSTREAM_URL, TARGET)
    except Exception as e:
        print(f"download failed: {e}", file=sys.stderr)
        return 1

    size, sha = _hash(TARGET)
    print(f"size:   {size} bytes")
    print(f"sha256: {sha}")
    if sha != EXPECTED_SHA256:
        print(
            f"  WARNING: SHA-256 does not match the pinned reproducibility "
            f"hash ({EXPECTED_SHA256[:12]}...). The upstream file may have "
            f"changed since this script was pinned. The benchmark statistics "
            f"shipped with this package were computed against the pinned "
            f"version; re-running them against the new bytes may produce "
            f"different numbers.",
            file=sys.stderr,
        )
        return 2
    if size != EXPECTED_BYTES:
        print(f"  note: size {size} differs from expected {EXPECTED_BYTES}.")
    print("verified against pinned SHA-256.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
