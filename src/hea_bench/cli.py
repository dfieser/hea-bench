"""Command-line entry point for hea-bench.

Phase 0: stub only. Real subcommands (`describe`, `classify`, `evaluate`,
`leaderboard`) arrive in later phases.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hea-bench",
        description=(
            "Open benchmark suite for high-entropy alloy phase prediction. "
            "Phase 0 skeleton — full subcommands not yet implemented."
        ),
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"hea-bench {__version__}",
    )
    args = parser.parse_args(argv)
    del args  # nothing to do yet
    print("hea-bench Phase 0 skeleton. No commands implemented yet.")
    print("See PROJECT_PLAN.md for the roadmap.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
