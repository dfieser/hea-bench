"""Property measurements from the mirrored Borg 2020 dataset.

Source: ``data/raw/borg2020/MPEA_dataset.csv`` (CC-BY-4.0, figshare
10.6084/m9.figshare.12642953 v9, mirrored verbatim). The phase loader
in ``hea_bench.benchmark.loaders.borg2020`` reads the same file for
labels; this module reads the mechanical-property columns the property
tier trains on.

Loader rules, stated because they define the training population:

- Hardness rows must be near room temperature (blank test temperature,
  which the deposit uses for ambient tests, or at most 35 C). Elevated
  temperature hardness is a different quantity and is excluded rather
  than mixed in.
- Duplicate measurements of one (formula, processing) pair collapse to
  their median, keeping repeated studies from over-weighting an alloy.
- Processing states stay distinct: an as-cast and an annealed
  measurement of one composition are two records, and the model layer
  decides whether to pool or condition.
"""

from __future__ import annotations

import csv
import pathlib
import statistics
from dataclasses import dataclass
from functools import lru_cache

from ..benchmark.loaders.borg2020 import (
    _COL_DOI,
    _COL_FORMULA,
    _COL_PROCESSING,
    _COL_REF_ID,
)
from ..composition import Composition, parse_formula

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_DEFAULT_CSV = _REPO_ROOT / "data" / "raw" / "borg2020" / "MPEA_dataset.csv"

# Property-tier columns this module adds to the phase loader's shared
# Borg header constants imported above (verbatim upstream headers,
# including the raw LaTeX).
_COL_HV = "PROPERTY: HV"
_COL_TEST_TEMPERATURE = "PROPERTY: Test temperature ($^\\circ$C)"
_COL_EXP_DENSITY = "PROPERTY: Exp. Density (g/cm$^3$)"
_COL_YEAR = "REFERENCE: year"

_ROOM_TEMPERATURE_MAX_C = 35.0


@dataclass(frozen=True)
class PropertyRecord:
    """One deduplicated property measurement for one alloy state."""

    composition: Composition
    formula_raw: str
    value: float
    processing: str | None
    doi: str | None
    reference_id: str
    year: int | None


def _near_room_temperature(record: dict) -> bool:
    text = (record.get(_COL_TEST_TEMPERATURE) or "").strip()
    if not text:
        return True
    try:
        return float(text) <= _ROOM_TEMPERATURE_MAX_C
    except ValueError:
        return False


def _load_column(
    csv_path: pathlib.Path,
    column: str,
    *,
    room_temperature_only: bool,
) -> tuple[PropertyRecord, ...]:
    grouped: dict[tuple[str, str | None], list[float]] = {}
    meta: dict[tuple[str, str | None], dict] = {}
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        for record in csv.DictReader(handle):
            text = (record.get(column) or "").strip()
            if not text:
                continue
            if room_temperature_only and not _near_room_temperature(record):
                continue
            formula = (record.get(_COL_FORMULA) or "").strip()
            try:
                composition = parse_formula(formula)
                value = float(text)
            except ValueError:
                continue
            processing = (record.get(_COL_PROCESSING) or "").strip() or None
            key = (formula, processing)
            grouped.setdefault(key, []).append(value)
            if key not in meta:
                year_text = (record.get(_COL_YEAR) or "").strip()
                meta[key] = {
                    "composition": composition,
                    "doi": (record.get(_COL_DOI) or "").strip() or None,
                    "reference_id": (record.get(_COL_REF_ID) or "").strip(),
                    "year": int(float(year_text)) if year_text else None,
                }
    records = []
    for (formula, processing), values in grouped.items():
        info = meta[(formula, processing)]
        records.append(
            PropertyRecord(
                composition=info["composition"],
                formula_raw=formula,
                value=statistics.median(values),
                processing=processing,
                doi=info["doi"],
                reference_id=info["reference_id"],
                year=info["year"],
            )
        )
    records.sort(key=lambda record: (record.formula_raw, record.processing or ""))
    return tuple(records)


@lru_cache(maxsize=4)
def _cached(csv_path: str, column: str, room_temperature_only: bool):
    return _load_column(
        pathlib.Path(csv_path), column, room_temperature_only=room_temperature_only
    )


def hardness_records(csv_path: pathlib.Path | None = None) -> tuple[PropertyRecord, ...]:
    """Vickers hardness (HV) per (formula, processing), near room temperature."""
    path = csv_path or _DEFAULT_CSV
    return _cached(str(path), _COL_HV, True)


def experimental_density_records(
    csv_path: pathlib.Path | None = None,
) -> tuple[PropertyRecord, ...]:
    """Experimentally measured densities (g/cm3), for validating tier A."""
    path = csv_path or _DEFAULT_CSV
    return _cached(str(path), _COL_EXP_DENSITY, False)


__all__ = ["PropertyRecord", "experimental_density_records", "hardness_records"]
