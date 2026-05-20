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
EXPECTED_BYTES = 6_424_704  # observed 2026-05-20; upstream is unversioned, so this is a soft check


def main() -> int:
    if TARGET.exists():
        print(f"already present: {TARGET} ({TARGET.stat().st_size} bytes)")
        return 0

    print(f"downloading {UPSTREAM_URL}")
    print(f"          -> {TARGET}")
    try:
        urllib.request.urlretrieve(UPSTREAM_URL, TARGET)
    except Exception as e:
        print(f"download failed: {e}", file=sys.stderr)
        return 1

    size = TARGET.stat().st_size
    sha = hashlib.sha256(TARGET.read_bytes()).hexdigest()
    print(f"size:   {size} bytes")
    print(f"sha256: {sha}")
    if size != EXPECTED_BYTES:
        print(
            f"  note: size differs from the value observed on 2026-05-20 "
            f"({EXPECTED_BYTES} bytes). Upstream is unversioned, so this "
            f"is informational, not an error."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
