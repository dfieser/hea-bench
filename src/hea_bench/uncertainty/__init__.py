"""Uncertainty and domain of applicability: the package's trust layer.

Two ingredients, designed to be read together:

- :mod:`~hea_bench.uncertainty.conformal` wraps any fitted model with
  split conformal prediction sets or intervals carrying a
  distribution-free finite-sample coverage guarantee.
- :mod:`~hea_bench.uncertainty.applicability` reports whether a query
  composition sits inside the region the corpus actually covers, as
  several orthogonal novelty signals plus one conservative ``in_domain``
  flag, because the conformal guarantee assumes exchangeability and a
  novel chemistry violates it.

Everything here describes this package's own confidence about a query
against this corpus. It does not characterize published models,
published accuracies, or other tools.
"""

from .applicability import DomainModel, default_domain, fit_domain, novelty_score
from .conformal import ConformalClassifier, ConformalRegressor

__all__ = [
    "ConformalClassifier",
    "ConformalRegressor",
    "DomainModel",
    "default_domain",
    "fit_domain",
    "novelty_score",
]
