"""Loader for the Pei et al. 2020 HEA dataset (npj Comput. Mater. 6, 50).

Source: ``data/raw/pei2020/pei2020_alloys_phases.csv`` (CC-BY-4.0,
mirrored verbatim from Springer's CDN — see
``data/raw/pei2020/README.md``).

Upstream schema is minimal: two columns (``Alloy``, ``Phase``), 1,252
rows, four lower-case phase labels (``bcc``, ``fcc``, ``hcp``,
``multi-phase``). 43 of those rows repeat a formula already seen; per
the design decision in this loader those are deduplicated on first
occurrence to match the Borg loader's behaviour, leaving 1,209 unique
formulas. No row is dropped for an unparseable formula or an
unrecognised label; the only attrition is duplicate formulas.

Pei has no processing column and no per-row DOI; both AlloyRecord
fields are left ``None``. The whole dataset shares one DOI
(10.1038/s41524-020-0308-7), recorded once at the source level.
"""

from __future__ import annotations

import csv
import pathlib
from collections.abc import Iterator

from ..composition import parse_formula
from ..taxonomy import PEI_MAP
from . import AlloyRecord

SOURCE_NAME = "pei2020"

# Upstream column names (case-sensitive).
_COL_ALLOY = "Alloy"
_COL_PHASE = "Phase"


def load(csv_path: pathlib.Path) -> Iterator[AlloyRecord]:
    """Yield one `AlloyRecord` per unique formula.

    Behaviour:

    - Deduplicates by raw formula string (Pei has no processing
      column). First occurrence wins on phase-label conflicts.
    - Rows with an unparseable formula, an empty phase label, or a
      phase label not in :data:`hea_bench.benchmark.taxonomy.PEI_MAP`
      are skipped silently.
    - ``source_row_id`` is the 0-indexed CSV data row number (matches
      Pei's internal ordering; not a stable upstream ID).
    """
    seen: set[str] = set()

    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row_idx, raw in enumerate(reader):
            formula = (raw.get(_COL_ALLOY) or "").strip()
            phase_label = (raw.get(_COL_PHASE) or "").strip()

            if not formula or not phase_label:
                continue
            if formula in seen:
                continue

            try:
                composition = parse_formula(formula)
            except ValueError:
                continue

            canonical = PEI_MAP.get(phase_label.lower())
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
