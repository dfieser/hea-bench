"""Composition design: constrained search and, next door, campaigns.

``search`` walks a deterministic composition lattice over a palette,
filters by rule, property, composition, and domain constraints, and
returns a Pareto front where every candidate carries its full receipt
(descriptors, rule verdicts, property predictions with intervals,
novelty components, domain flag). It is a screening and prioritization
aid; the property models under it are honest about their error and so
is the front.
"""

from .constraints import (
    CompositionConstraint,
    DomainConstraint,
    Maximize,
    Minimize,
    PropertyConstraint,
    RuleConstraint,
)
from .search import Candidate, ParetoResult, search

__all__ = [
    "Candidate",
    "CompositionConstraint",
    "DomainConstraint",
    "Maximize",
    "Minimize",
    "ParetoResult",
    "PropertyConstraint",
    "RuleConstraint",
    "search",
]
