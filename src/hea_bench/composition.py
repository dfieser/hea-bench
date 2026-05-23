"""Composition parsing and normalization.

The three v0.1.0 source datasets use slightly different formula
conventions:

  Borg 2020:    'Al0.25 Co1 Fe1 Ni1'         (space-separated tokens,
                                              proportional atomic amounts)
  Pei 2020:     'Al0.15Cr0.85'                (no spaces, already normalized
                                              or proportional)
  Peivaste:     stored as one column per element, plus a formula string
                like 'AlAuCoCrCuNi' or 'AlCoCrCu0.5Fe'

A single regex `_ELEMENT_TOKEN` parses any of these formula strings into
a list of (element-symbol, coefficient) pairs; missing coefficients
default to 1. `normalize` then converts proportional amounts to mole
fractions summing to 1.

For Peivaste, the per-element-column representation is parsed by
`from_element_columns` instead.

This module lives at package root (not under ``benchmark/``) because
both the benchmark loaders *and* the descriptor functions consume the
``Composition`` type — descriptors should not depend on benchmark.
"""

from __future__ import annotations

import re

Composition = dict[str, float]
"""Mapping of element symbol to mole fraction. Must sum to ~1.0 after
normalization. Element symbols are canonical (first letter upper, second
lower)."""

# One token = element symbol (1–2 letters) + optional numeric coefficient.
# Coefficient may be integer or decimal; if absent, default to 1.
_ELEMENT_TOKEN = re.compile(r"([A-Z][a-z]?)([0-9]*\.?[0-9]*)")

# The 118 IUPAC-recognised element symbols. parse_formula validates each
# matched token against this set so that an input like "Al0.5Xy0.5" is
# rejected with a clear error rather than silently treated as containing
# a phantom element.
_VALID_ELEMENTS = frozenset({
    "H",  "He",
    "Li", "Be", "B",  "C",  "N",  "O",  "F",  "Ne",
    "Na", "Mg", "Al", "Si", "P",  "S",  "Cl", "Ar",
    "K",  "Ca",
    "Sc", "Ti", "V",  "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr",
    "Rb", "Sr",
    "Y",  "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
    "In", "Sn", "Sb", "Te", "I",  "Xe",
    "Cs", "Ba",
    "La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd",
    "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
    "Hf", "Ta", "W",  "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl", "Pb", "Bi", "Po", "At", "Rn",
    "Fr", "Ra",
    "Ac", "Th", "Pa", "U",  "Np", "Pu", "Am", "Cm",
    "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr",
    "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds", "Rg", "Cn",
    "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
})


def parse_formula(formula: str) -> Composition:
    """Parse an HEA composition formula into a normalized mole-fraction dict.

    Handles all three v0.1.0 source conventions: space-separated
    proportional amounts (Borg), packed proportional amounts (Pei),
    and bare formulas with implicit unit amounts (Peivaste's `FORMULA`
    column).

    Parameters
    ----------
    formula
        Composition string. Whitespace is ignored.

    Returns
    -------
    Composition
        Mapping from element symbol to mole fraction, normalized to
        sum to 1.0 (within float epsilon).

    Raises
    ------
    ValueError
        If no element tokens are found, or the parsed coefficients sum
        to zero.

    Examples
    --------
    >>> parse_formula("CoCrFeMnNi")
    {'Co': 0.2, 'Cr': 0.2, 'Fe': 0.2, 'Mn': 0.2, 'Ni': 0.2}

    >>> parse_formula("Al0.25 Co1 Fe1 Ni1")
    {'Al': 0.07692307692307693, 'Co': 0.3076923076923077, 'Fe': 0.3076923076923077, 'Ni': 0.3076923076923077}

    >>> parse_formula("Al0.15Cr0.85")
    {'Al': 0.15, 'Cr': 0.85}
    """
    raw: dict[str, float] = {}
    bad: list[str] = []
    for el, coef in _ELEMENT_TOKEN.findall(formula):
        if not el:
            continue
        if el not in _VALID_ELEMENTS:
            bad.append(el)
            continue
        amount = float(coef) if coef else 1.0
        raw[el] = raw.get(el, 0.0) + amount

    if bad:
        raise ValueError(
            f"unrecognised element symbol(s) {sorted(set(bad))!r} "
            f"in formula {formula!r}"
        )
    if not raw:
        raise ValueError(f"no elements parsed from formula {formula!r}")

    return normalize(raw)


def normalize(amounts: dict[str, float]) -> Composition:
    """Normalize proportional amounts to mole fractions summing to 1.0.

    Skips elements with zero amount.

    Raises
    ------
    ValueError
        If the input is empty or its values sum to zero.
    """
    total = sum(v for v in amounts.values() if v > 0)
    if total <= 0:
        raise ValueError("composition amounts must sum to a positive value")
    return {el: amount / total for el, amount in amounts.items() if amount > 0}


def from_element_columns(
    row: dict[str, float | str], element_symbols: list[str]
) -> Composition:
    """Build a composition from a row that has one column per element.

    Used by the Peivaste loader, where the upstream CSV has 62 columns
    (one per element from Li to Au) holding mole fractions directly.

    Parameters
    ----------
    row
        Mapping from column name to value. Values may be float or string;
        strings are converted via `float`.
    element_symbols
        The element symbols to look up in `row`. Symbols absent from `row`
        or holding non-numeric values are silently skipped.

    Returns
    -------
    Composition
        Normalized composition. If all values are zero or missing, raises
        ``ValueError``.
    """
    amounts: dict[str, float] = {}
    for el in element_symbols:
        if el not in row:
            continue
        try:
            v = float(row[el])
        except (TypeError, ValueError):
            continue
        if v > 0:
            amounts[el] = v
    return normalize(amounts)
