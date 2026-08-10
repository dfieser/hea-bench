"""Loader for the Borg et al. 2020 MPEA dataset.

Source: ``data/raw/borg2020/MPEA_dataset.csv`` (CC-BY-4.0, mirrored
verbatim from figshare 10.6084/m9.figshare.12642953 v9).

Schema, dedup behaviour, and label-normalization decisions are
documented inline below; see ``data/raw/borg2020/README.md`` for the
full source-level context.
"""

from __future__ import annotations

import csv
import pathlib
from collections.abc import Iterator

from ...composition import parse_formula
from ..taxonomy import BORG_SIMPLE_MAP
from . import AlloyRecord

SOURCE_NAME = "borg2020"

# Column names — Borg's upstream headers, verbatim (including raw LaTeX).
_COL_REF_ID         = "IDENTIFIER: Reference ID"
_COL_FORMULA        = "FORMULA"
_COL_MICROSTRUCTURE = "PROPERTY: Microstructure"
_COL_PROCESSING     = "PROPERTY: Processing method"
_COL_SIMPLE_PHASE   = "PROPERTY: BCC/FCC/other"
_COL_DOI            = "REFERENCE: doi"


def load(csv_path: pathlib.Path) -> Iterator[AlloyRecord]:
    """Yield one `AlloyRecord` per unique ``(formula, processing)`` alloy.

    Borg has 1,545 measurement rows for 740 unique ``(formula, processing)``
    alloys — the duplicates come from multiple mechanical tests at
    different temperatures/test types on the same alloy. Phase is a
    property of the alloy and its processing, not the test, so we
    deduplicate here.

    When duplicate ``(formula, processing)`` rows disagree on the phase
    label, the first row encountered wins. (Borg's data is internally
    consistent on this point — duplicate rows from the same source paper
    always carry the same phase label — but the loader is defensive.)

    Rows missing a parseable formula or a simplified phase label are
    skipped silently. Caller can compare yielded count to file row count
    if a count of skipped rows is needed.
    """
    seen: set[tuple[str, str]] = set()

    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        for raw in csv.DictReader(f):
            formula = (raw.get(_COL_FORMULA) or "").strip()
            processing = (raw.get(_COL_PROCESSING) or "").strip()
            source_label = (raw.get(_COL_SIMPLE_PHASE) or "").strip()
            full_microstructure = (raw.get(_COL_MICROSTRUCTURE) or "").strip()

            if not formula or not source_label:
                continue

            key = (formula, processing)
            if key in seen:
                continue

            try:
                composition = parse_formula(formula)
            except ValueError:
                continue

            canonical = BORG_SIMPLE_MAP.get(source_label)
            if canonical is None:
                continue

            seen.add(key)
            yield AlloyRecord(
                source=SOURCE_NAME,
                source_row_id=(raw.get(_COL_REF_ID) or "").strip(),
                formula_raw=formula,
                composition=composition,
                canonical_phase=canonical,
                source_label=full_microstructure or source_label,
                processing=processing or None,
                source_doi=(raw.get(_COL_DOI) or "").strip() or None,
            )
