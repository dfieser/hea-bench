"""Per-element mechanics data from the vendored matminer Miedema table.

Exposes molar volume and elastic moduli for the elements covered by
``miedema_parameters.csv`` (73 elements, vendored 2026-05-20, SHA
recorded in this folder's README). These feed the Andreoli
elastic-strain energy criterion and the Miedema decomposition tables.

Column-name caveat, verified against physical values on 2026-07-22:
matminer's ``Miedema.csv`` header calls the ninth column
``compressibility``, but the numbers are bulk moduli in GPa
(Fe 168.3, Al 72.18, W 314.4 all match standard bulk-modulus tables,
not compressibilities in any unit). This loader therefore publishes
the column as ``bulk_modulus_gpa``. ``molar_volume`` is cm3/mol and
``shear_modulus`` is GPa.

Rows whose modulus or volume is exactly 0.0 upstream (gases, some
nonmetals) are loaded as stored; consumers must treat a zero as "not
available" — ``h_elastic`` returns None rather than dividing by it.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_CSV_PATH = Path(__file__).with_name("miedema_parameters.csv")


@dataclass(frozen=True)
class Mechanics:
    """Frozen per-element mechanics bundle."""

    molar_volume_cm3: float
    bulk_modulus_gpa: float
    shear_modulus_gpa: float


@lru_cache(maxsize=1)
def _table() -> dict[str, Mechanics]:
    table: dict[str, Mechanics] = {}
    with _CSV_PATH.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            table[row["element"]] = Mechanics(
                molar_volume_cm3=float(row["molar_volume"]),
                bulk_modulus_gpa=float(row["compressibility"]),
                shear_modulus_gpa=float(row["shear_modulus"]),
            )
    return table


def mechanics(symbol: str) -> Mechanics | None:
    """Return the mechanics bundle for ``symbol``, or None if uncovered."""
    return _table().get(symbol)


def covered_mechanics() -> set[str]:
    """Return the set of element symbols with mechanics rows."""
    return set(_table())
