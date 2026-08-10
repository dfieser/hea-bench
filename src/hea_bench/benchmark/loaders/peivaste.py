"""Loader for the Peivaste MPEA phase dataset.

Source: ``data/raw/peivaste/dataset11252_79.csv``. Pointer-only because
the upstream GitHub repo declares no license — see
``data/raw/peivaste/README.md`` for the full provenance and the
mandatory fetch step.

Two upstream quirks the loader handles transparently:

1. **Header/data column offset.** The upstream CSV's first header
   field is empty; the second header field is misleadingly named
   ``index`` but actually holds the alloy *formula string*. Python's
   ``csv.DictReader`` will key the formula under the literal column
   name ``"index"``. We accept that naming and document it here
   rather than fight upstream.

2. **Per-element-column composition.** Mole fractions live in 62
   separate columns (Li through Au) rather than in a parseable
   formula string. We use ``from_element_columns`` to assemble the
   composition rather than ``parse_formula``.
"""

from __future__ import annotations

import csv
import pathlib
from collections.abc import Iterator

from ...composition import from_element_columns
from ..taxonomy import PEIVASTE_MAP
from . import AlloyRecord

SOURCE_NAME = "peivaste"
DEFAULT_CSV_NAME = "dataset11252_79.csv"

# Element columns in upstream order, used as the alphabet for
# ``from_element_columns``. The order doesn't affect parsing
# correctness but matches the upstream header for traceability.
ELEMENT_COLUMNS = [
    "Li", "Be", "B",  "C",  "N",  "Na", "Mg", "Al", "Si", "P",
    "Ca", "Sc", "Ti", "V",  "Cr", "Mn", "Fe", "Co", "Ni", "Cu",
    "Zn", "Ga", "Ge", "Rb", "Sr", "Y",  "Zr", "Nb", "Mo", "Tc",
    "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn", "Sb", "Cs", "Ba",
    "La", "Ce", "Pr", "Nd", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho",
    "Er", "Tm", "Yb", "Lu", "Hf", "Ta", "W",  "Re", "Os", "Ir",
    "Pt", "Au",
]

# See module docstring quirk #1: the formula sits under DictReader key "index".
_COL_FORMULA = "index"
_COL_PHASE = "Phase"


def load(csv_path: pathlib.Path) -> Iterator[AlloyRecord]:
    """Yield one `AlloyRecord` per unique formula.

    Raises
    ------
    FileNotFoundError
        If ``csv_path`` doesn't exist. Peivaste is pointer-only; the
        user must fetch the upstream CSV before loading. Error message
        includes the exact command to run.
    """
    if not csv_path.exists():
        fetch_script = csv_path.parent / "fetch.py"
        raise FileNotFoundError(
            f"Peivaste CSV not found at {csv_path}.\n"
            f"Peivaste is pointer-only because the upstream repo declares "
            f"no license. Fetch it with:\n"
            f"    python {fetch_script}"
        )

    seen: set[str] = set()
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row_idx, raw in enumerate(reader):
            formula = (raw.get(_COL_FORMULA) or "").strip()
            phase_label = (raw.get(_COL_PHASE) or "").strip()

            if not formula or not phase_label:
                continue
            if formula in seen:
                continue

            try:
                composition = from_element_columns(raw, ELEMENT_COLUMNS)
            except ValueError:
                continue

            canonical = PEIVASTE_MAP.get(phase_label)
            if canonical is None:
                continue

            seen.add(formula)
            yield AlloyRecord(
                source=SOURCE_NAME,
                source_row_id=str(row_idx),
                formula_raw=formula,
                composition=composition,
                canonical_phase=canonical,
                source_label=phase_label,
                processing=None,
                source_doi=None,
            )
