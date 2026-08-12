"""Constraint and objective vocabulary for the composition search.

Small frozen dataclasses; the search evaluates them. Constraints AND
together. ``DomainConstraint(in_domain=True)`` is present by default in
every search because optimizers exploit model error hardest exactly
where the data runs out; opting out is explicit
(``DomainConstraint(in_domain=None)``), never a silent default.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Maximize:
    """Maximize a property from :func:`hea_bench.properties.available_properties`."""

    name: str


@dataclass(frozen=True)
class Minimize:
    """Minimize a property from :func:`hea_bench.properties.available_properties`."""

    name: str


@dataclass(frozen=True)
class RuleConstraint:
    """Require a rule verdict.

    ``rule`` is a module name from ``hea_bench.rules`` (for example
    ``"guo_vec"``); ``satisfied`` is the verdict string, or a tuple of
    acceptable verdicts. A rule that cannot compute for a candidate
    (missing pair data) fails the constraint, conservatively.
    """

    rule: str
    satisfied: str | tuple[str, ...]

    def matches(self, verdict: str | None) -> bool:
        if verdict is None:
            return False
        if isinstance(self.satisfied, str):
            return verdict == self.satisfied
        return verdict in self.satisfied


@dataclass(frozen=True)
class PropertyConstraint:
    """Bound a property. ``bound`` picks what is compared for tier B.

    ``"point"`` compares the point prediction; ``"lower"``/``"upper"``
    compare that end of the conformal interval, the conservative choice
    when the constraint protects against over- or under-shooting.
    Tier A properties have no interval; they always compare the value.
    """

    prop: str
    min: float | None = None
    max: float | None = None
    bound: str = "point"


@dataclass(frozen=True)
class CompositionConstraint:
    """Per-element mole-fraction bounds, enforced on the lattice itself."""

    element: str
    min: float = 0.0
    max: float = 1.0


@dataclass(frozen=True)
class DomainConstraint:
    """Require candidates inside (True), outside (False), or ignore (None)."""

    in_domain: bool | None = True


__all__ = [
    "CompositionConstraint",
    "DomainConstraint",
    "Maximize",
    "Minimize",
    "PropertyConstraint",
    "RuleConstraint",
]
