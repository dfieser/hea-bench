"""Loader for the Chizhevskiy et al. 2026 LLM-extracted HEA database.

Source: ``data/raw/chizhevskiy2026/database_of_HEAs.csv`` — 12,427 records
mined from 4,625 papers by an LLM pipeline (Sci. Data 13:612,
DOI 10.1038/s41597-026-06930-z). See that directory's README.md for full
provenance, the schema, and the (important) quality caveats.

Two things distinguish this source from the others:

1. **Free-text phase labels.** The `Phase` column is messy LLM output
   ("BCC B2 + FCC L12", "C14 Laves phase + FCC", "cubic", "not specified", …)
   rather than a small fixed label set, so canonical mapping goes through the
   ``chizhevskiy_canonical_phase`` parser in ``taxonomy`` rather than a dict.
   The raw string is preserved verbatim as ``source_label`` — the finer
   SS/ORD/LAV intermetallic-typing analysis (the reason this dataset was
   acquired) reads that side-channel, since canonical mapping collapses all
   intermetallics to ``multi-phase``.

2. **Composition-level dedup.** Records are deduplicated on the *parsed,
   normalized composition* (not the raw `Alloy` string), so "AlCoCrFeNi" and
   "Al1Co1Cr1Fe1Ni1" collapse to one alloy. First valid row for a composition
   wins. (Cross-paper duplicate *reports* of the same alloy — useful for label-
   noise analysis — are intentionally NOT preserved here; the quality-vetting
   script reads the raw CSV directly for that.)

There is no processing-route column (it is buried in free-text
`Experimental details`) and no per-row DOI in the main file, so ``processing``
and ``source_doi`` are always ``None``.
"""

from __future__ import annotations

import csv
import pathlib
from collections.abc import Iterator

from ...composition import Composition, parse_formula
from ..taxonomy import chizhevskiy_canonical_phase
from . import AlloyRecord

SOURCE_NAME = "chizhevskiy2026"
DEFAULT_CSV_NAME = "database_of_HEAs.csv"

_COL_ID = "id"
_COL_ALLOY = "Alloy"
_COL_PHASE = "Phase"


def _composition_key(composition: Composition) -> tuple[tuple[str, float], ...]:
    """Order-independent, rounding-stable key for composition-level dedup."""
    return tuple(sorted((el, round(frac, 6)) for el, frac in composition.items()))


def load(csv_path: pathlib.Path) -> Iterator[AlloyRecord]:
    """Yield one `AlloyRecord` per unique composition.

    Rows missing a formula or phase string, rows whose phase string carries no
    usable canonical class (``chizhevskiy_canonical_phase`` returns ``None`` —
    e.g. "not specified", "cubic", "hcp martensite"), and rows whose `Alloy`
    string does not parse to a valid composition are skipped silently. When two
    rows share a composition, the first encountered wins.
    """
    seen: set[tuple[tuple[str, float], ...]] = set()

    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        for raw in csv.DictReader(f):
            formula = (raw.get(_COL_ALLOY) or "").strip()
            phase = (raw.get(_COL_PHASE) or "").strip()
            if not formula or not phase:
                continue

            canonical = chizhevskiy_canonical_phase(phase)
            if canonical is None:
                continue

            try:
                composition = parse_formula(formula)
            except ValueError:
                continue

            key = _composition_key(composition)
            if key in seen:
                continue
            seen.add(key)

            yield AlloyRecord(
                source=SOURCE_NAME,
                source_row_id=(raw.get(_COL_ID) or "").strip(),
                formula_raw=formula,
                composition=composition,
                canonical_phase=canonical,
                source_label=phase,
                processing=None,
                source_doi=None,
            )
