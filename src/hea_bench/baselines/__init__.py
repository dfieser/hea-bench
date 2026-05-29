"""Learned reference baselines for the benchmark.

The single :class:`LogisticBaseline` is a logistic regression on the six
descriptors (optionally with squared and interaction terms). It is the
quantitative floor a new phase-prediction method should beat. Importing
this package is dependency-free; fitting needs the optional ``[ml]``
extra (numpy).
"""

from .learned import (
    FEATURE_NAMES,
    LogisticBaseline,
    descriptor_vector,
    evaluate,
    load_features,
)

__all__ = [
    "FEATURE_NAMES",
    "LogisticBaseline",
    "descriptor_vector",
    "evaluate",
    "load_features",
]
