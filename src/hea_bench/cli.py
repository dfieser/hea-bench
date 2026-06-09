"""Command-line entry point for hea-bench.

Thin wrapper around the descriptor library. ``--version`` reports the
package version; the descriptor and rule API is the documented surface
(see ``README.md``). A richer ``describe`` subcommand may arrive later.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hea-bench",
        description=(
            "Open calculator of high-entropy-alloy thermodynamic and geometric "
            "descriptors plus the canonical empirical phase-prediction rules."
        ),
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"hea-bench {__version__}",
    )
    args = parser.parse_args(argv)
    del args  # nothing to do yet
    print(f"hea-bench {__version__}")
    print("Use the Python API (import hea_bench), the browser app, or the")
    print("desktop app. See README.md for the descriptor and rule surface.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
