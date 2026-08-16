"""Command-line entry point for hea-bench.

``hea-bench`` alone reports the package version and points at the API
surface. ``hea-bench describe FORMULA`` computes every descriptor the
selected backend offers for one composition and prints a strict-JSON
report with units; ``--backend`` selects the computation backend
(``native`` by default, ``heacalculator`` once the interop extra is
installed).
"""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from ._json import json_safe


def _describe(formula: str, backend_name: str) -> int:
    from .composition import parse_formula
    from .descriptors.backend import UNITS, BackendUnavailableError, get_backend

    try:
        composition = parse_formula(formula)
    except ValueError as error:
        print(f"could not parse composition {formula!r}: {error}", file=sys.stderr)
        return 2
    try:
        resolved = get_backend(backend_name)
    except BackendUnavailableError as error:
        print(str(error), file=sys.stderr)
        return 2

    values = resolved.compute(composition)
    descriptors: dict[str, dict] = {}
    warnings: list[str] = []
    for name in resolved.descriptor_names():
        value = values.get(name)
        # Strict JSON has no Infinity/NaN token, so unbounded values are
        # nulled and flagged instead of breaking downstream parsers.
        safe = json_safe(value)
        if safe is None and value is not None:
            warnings.append(f"{name}: value is unbounded for {formula!r}; reported as null")
        elif value is None:
            warnings.append(
                f"{name}: not computable for {formula!r} "
                f"(an element lacks the required per-element data)"
            )
        descriptors[name] = {"value": safe, "unit": UNITS.get(name)}

    print(
        json.dumps(
            {
                "input": formula,
                "backend": resolved.name,
                "composition": composition,
                "descriptors": descriptors,
                "warnings": warnings,
                "hea_bench_version": __version__,
            },
            indent=2,
        )
    )
    return 0


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
    subparsers = parser.add_subparsers(dest="command")

    describe = subparsers.add_parser(
        "describe",
        help="compute every descriptor for one composition, as JSON",
        description=(
            "Compute every descriptor the selected backend offers for one "
            "composition and print a JSON report with units and warnings."
        ),
    )
    describe.add_argument("formula", help="composition, e.g. CoCrFeMnNi or Al0.3CoCrFeNi")
    describe.add_argument(
        "--backend",
        choices=("native", "heacalculator"),
        default="native",
        help=(
            "descriptor backend: this package's own stdlib implementations "
            "(default) or an installed HEACalculator "
            '(pip install "hea-bench[interop]")'
        ),
    )

    args = parser.parse_args(argv)
    if args.command == "describe":
        return _describe(args.formula, args.backend)

    print(f"hea-bench {__version__}")
    print("Use the Python API (import hea_bench), the browser app, or the")
    print("desktop app. See README.md for the descriptor and rule surface.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
