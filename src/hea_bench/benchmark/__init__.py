"""Leakage-controlled benchmark splits and evaluation for HEA phase prediction.

The descriptors and rules in the rest of this package answer "what is
this alloy like". This subpackage answers a different and harder
question: how well does any model actually predict phase on alloys it
has not seen.

The usual protocol in the HEA literature is a random train/test split
over a corpus full of stoichiometric series, so a model tested on
``Al0.3CoCrFeNi`` has very often been trained on ``Al0.25CoCrFeNi``.
That measures interpolation along a composition line, not prediction of
a new system, and it is why reported accuracies are high while practical
performance on a new chemistry is not.

This subpackage ships one corpus, two frozen splits over it, and one
call that reports both:

    >>> from hea_bench.benchmark import evaluate, load_benchmark, MajorityClass
    >>> bench = load_benchmark(task="single_vs_multi")     # doctest: +SKIP
    >>> print(evaluate(MajorityClass(), bench).table())    # doctest: +SKIP

The grouped column is the honest number. The random column is what the
same model would have scored under the usual protocol. The gap is the
point.

The corpus is built locally rather than shipped, because most of its
upstream data is not licensed for redistribution. See
:mod:`hea_bench.benchmark.corpus` for the build commands and
``data/raw/README.md`` for the per-source licensing status.
"""

from __future__ import annotations

from .corpus import (
    TASKS,
    Benchmark,
    BenchmarkRow,
    descriptor_matrix,
    descriptor_names,
    finite_descriptor_indices,
    load_benchmark,
)
from .evaluate import EvaluationReport, MajorityClass, evaluate
from .metrics import FoldMetrics, score
from .splits import Fold, SplitScheme, family_of, grouped_split, random_split
from .taxonomy import PhaseClass

__all__ = [
    "TASKS",
    "Benchmark",
    "BenchmarkRow",
    "EvaluationReport",
    "Fold",
    "FoldMetrics",
    "MajorityClass",
    "PhaseClass",
    "SplitScheme",
    "descriptor_matrix",
    "descriptor_names",
    "evaluate",
    "family_of",
    "finite_descriptor_indices",
    "grouped_split",
    "load_benchmark",
    "random_split",
    "score",
]
