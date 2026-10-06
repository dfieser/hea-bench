"""Custom elements and custom pair enthalpies.

The library side of the calculator's custom-element editor and pair
editor. Inside a ``with custom_data(...)`` block every descriptor, rule
and Miedema term reads the custom values first and the curated tables
second::

    import hea_bench as hb

    with hb.custom_data(
        elements={"X": {"radius_pm": 135.0, "melting_K": 1800.0, "valence": 8,
                        "electronegativity": 1.83}},
        pair_enthalpies={"Fe-X": -5.0, "Co-X": -3.0},
    ):
        hb.omega({"Fe": 0.4, "Co": 0.4, "X": 0.2})

A custom element needs a pair enthalpy with every other element of the
alloy for anything that depends on the mixing enthalpy. Without one the
mixing enthalpy raises an error that names the missing pairs, and the
size, valence and melting descriptors still work. A pair enthalpy given
for two tabulated elements replaces the tabulated value. The overrides
are context-local, so concurrent callers never see each other's values.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager

from . import _overrides
from .descriptors.data.elemental import ELEMENTAL_DATA, ElementProperties

#: Labels the app's custom-element editor accepts, for the same reasons:
#: short, unambiguous, and never a tabulated element's symbol.
_LABEL = re.compile(r"[A-Za-z0-9_-]{1,10}")


def _element(label: str, values: Mapping) -> ElementProperties:
    if not _LABEL.fullmatch(label):
        raise ValueError(
            f"custom element label {label!r} must be 1 to 10 letters, digits, '_' or '-'"
        )
    if label in ELEMENTAL_DATA:
        raise ValueError(
            f"{label!r} is a tabulated element; give a custom element its own label, "
            f"such as {label}2"
        )
    unknown = sorted(set(values) - {"radius_pm", "melting_K", "valence", "electronegativity"})
    if unknown:
        raise ValueError(
            f"custom element {label!r}: unknown fields {unknown}; use radius_pm, "
            f"melting_K, valence and (optionally) electronegativity"
        )

    def number(name: str, *, minimum: float, strict: bool, optional: bool = False):
        value = values.get(name)
        if value is None and optional:
            return None
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"custom element {label!r}: {name} must be a number") from None
        if not math.isfinite(value) or value < minimum or (strict and value == minimum):
            bound = "greater than" if strict else "at least"
            raise ValueError(f"custom element {label!r}: {name} must be {bound} {minimum:g}")
        return value

    return ElementProperties(
        radius_pm=number("radius_pm", minimum=0.0, strict=True),
        melting_K=number("melting_K", minimum=0.0, strict=True),
        valence=number("valence", minimum=0.0, strict=False),
        electronegativity=number("electronegativity", minimum=0.0, strict=True, optional=True),
    )


def _pair(key, value) -> tuple[frozenset[str], float]:
    if isinstance(key, str):
        parts = key.replace("|", "-").split("-")
    else:
        parts = list(key)
    if len(parts) != 2 or not all(isinstance(p, str) and p for p in parts) or parts[0] == parts[1]:
        raise ValueError(
            f"pair enthalpy key {key!r} must name two different elements, as 'Fe-X' or ('Fe', 'X')"
        )
    try:
        enthalpy = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"pair enthalpy for {key!r} must be a number in kJ/mol") from None
    if not math.isfinite(enthalpy):
        raise ValueError(f"pair enthalpy for {key!r} must be finite")
    return frozenset(parts), enthalpy


@contextmanager
def custom_data(
    elements: Mapping[str, Mapping] | None = None,
    pair_enthalpies: Mapping | None = None,
) -> Iterator[None]:
    """Use custom elements and pair enthalpies inside a ``with`` block.

    Parameters
    ----------
    elements
        Label -> ``{"radius_pm", "melting_K", "valence",
        "electronegativity"}``. Radius in pm and melting point in K must
        be positive, the valence electron count non-negative, and the
        Pauling electronegativity is optional (descriptors that need it
        are unavailable without it). Labels are 1 to 10 letters, digits,
        ``_`` or ``-`` and may not be a tabulated element. A label shaped
        like an element symbol (``X``, ``Xa``) can also be written in a
        formula string.
    pair_enthalpies
        ``"A-B"`` or ``("A", "B")`` -> equiatomic pair mixing enthalpy in
        kJ/mol, replacing the tabulated value or supplying a missing one.

    Blocks nest: an inner block extends and overrides the outer one.
    """
    custom = dict(_overrides.ELEMENTS.get() or {})
    for label, values in (elements or {}).items():
        custom[label] = _element(label, values)
    pairs = dict(_overrides.PAIRS.get() or {})
    for key, value in (pair_enthalpies or {}).items():
        pair, enthalpy = _pair(key, value)
        pairs[pair] = enthalpy
    element_token = _overrides.ELEMENTS.set(custom or None)
    pair_token = _overrides.PAIRS.set(pairs or None)
    try:
        yield
    finally:
        _overrides.PAIRS.reset(pair_token)
        _overrides.ELEMENTS.reset(element_token)


__all__ = ["custom_data"]
