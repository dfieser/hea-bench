"""Binary mixing-enthalpy lookups (Miedema model).

Wraps the Miedema-derived pair-enthalpy table vendored from
matminer (BSD-3-Clause; LICENSE.matminer.txt in this folder).
The table itself derives from de Boer, Boom, Mattens, Miedema &
Niessen (1988) *Cohesion in Metals* and is equivalent to (and
spot-check-verified against) the open Takeuchi & Inoue 2005
*Mater. Trans.* **46**, 2817 tabulation.

Usage
-----
>>> from hea_bench.descriptors.data.pair_enthalpies import pair_enthalpy
>>> pair_enthalpy("Al", "Ni")
-22.0
>>> pair_enthalpy("Ni", "Al")     # symmetric
-22.0
>>> pair_enthalpy("Fe", "Fe")     # self-pair
0.0

Values are ΔH^mix for the equiatomic A-B liquid alloy in kJ/mol.
"""

from __future__ import annotations

import functools
import importlib.resources

_TSV_FILENAME = "pair_enthalpies.tsv"


@functools.lru_cache(maxsize=1)
def _load_table() -> dict[frozenset[str], float]:
    """Read the vendored TSV once; build a symmetric lookup dict.

    Keys are frozen-set element pairs so lookup is order-independent.
    Self-pairs are not stored — `pair_enthalpy(X, X)` returns 0.0 by
    convention (a pure element mixed with itself has zero enthalpy of
    mixing).
    """
    table: dict[frozenset[str], float] = {}
    text = importlib.resources.files(__package__).joinpath(_TSV_FILENAME).read_text(
        encoding="utf-8"
    )
    for i, line in enumerate(text.splitlines()):
        if i == 0:
            continue  # header
        parts = line.split()
        if len(parts) != 3:
            continue
        a, b, h = parts
        table[frozenset((a, b))] = float(h)
    return table


def pair_enthalpy(elem_a: str, elem_b: str) -> float:
    """Equiatomic binary mixing enthalpy ΔH^mix_{A,B} (kJ/mol).

    Symmetric in its arguments. Self-pairs return 0.0.

    Raises
    ------
    KeyError
        If the pair is not in the table (one or both elements outside
        the 75 covered by matminer's vendored data).
    """
    if elem_a == elem_b:
        return 0.0
    table = _load_table()
    key = frozenset((elem_a, elem_b))
    if key not in table:
        raise KeyError(
            f"pair {elem_a}-{elem_b} not in Miedema pair-enthalpy table "
            f"(matminer-vendored, 75 elements covered)"
        )
    return table[key]


def covered_elements() -> set[str]:
    """Set of element symbols appearing in the pair-enthalpy table."""
    elems: set[str] = set()
    for key in _load_table():
        elems.update(key)
    return elems


def missing_pairs(composition_elements: set[str]) -> set[frozenset[str]]:
    """Return the set of pairs (frozenset[str, str]) needed to compute
    a multi-component Miedema mixing enthalpy for ``composition_elements``
    that are absent from the table."""
    covered = set()
    for key in _load_table():
        covered.add(key)
    needed = {
        frozenset((a, b))
        for a in composition_elements
        for b in composition_elements
        if a < b
    }
    return needed - covered
