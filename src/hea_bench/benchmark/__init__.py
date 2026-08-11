"""Paired benchmark splits and evaluation for HEA phase prediction.

The descriptors and rules in the rest of this package answer "what is
this alloy like". This subpackage measures how well a model predicts
phase, under two evaluation protocols that answer different questions.

A random train/test split over a corpus full of stoichiometric series
tests a model on close variants of alloys it trained on: a model tested
on ``Al0.3CoCrFeNi`` has very often been trained on ``Al0.25CoCrFeNi``.
That largely measures interpolation within known alloy systems. A
family-grouped split keeps every stoichiometric variant of a system on
one side of the boundary, so it measures extrapolation to unseen
element systems. Neither protocol is correct on its own; they answer
different questions, and most published evaluations in this area use
random splits, so grouped results are rarely reported. This subpackage
ships one corpus, both splits frozen over it, and one call that reports
them side by side:

    >>> from hea_bench.benchmark import evaluate, load_benchmark, MajorityClass
    >>> bench = load_benchmark(task="single_vs_multi")     # doctest: +SKIP
    >>> print(evaluate(MajorityClass(), bench).table())    # doctest: +SKIP

The gap between the two columns quantifies how much of a random-split
score comes from testing on close relatives of training alloys. That
interpolation-versus-extrapolation reading of grouped evaluation is
established prior art, not this package's discovery: see Li et al.,
Commun. Mater. 6:9 (2025), doi:10.1038/s43246-024-00731-w; Meredig et
al., Mol. Syst. Des. Eng. 3, 819 (2018), doi:10.1039/C8ME00012C
(LOCO-CV); Zhao, del Cueto and Troisi, Digital Discovery 1, 266 (2022),
doi:10.1039/D1DD00050K; and Witman and Schindler, Digital Discovery
(2025), doi:10.1039/D4DD00250D (MatFold). What this package adds is the
frozen, digest-pinned, paired protocol for this corpus.

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
