"""Loading the consolidated corpus and attaching its frozen splits.

The corpus is not shipped inside the wheel. Its largest source dataset
(Peivaste, the majority of contributed rows) carries no license, and a
derived corpus inherits the restrictions of everything it is built
from, so what this package ships is the recipe rather than the data:
loaders,
consolidation rules, pinned SHA-256 hashes of the exact upstream bytes,
and the split algorithm. Running the build turns those into a corpus
that is byte-identical to the one every reported number was computed
against. ``data/raw/README.md`` records the per-source status and
``benchmark_build`` in ``tools/`` drives the build.

That is a deliberate trade. Shipping the CSV would be more convenient
and would also redistribute data the upstream authors have not licensed
for it.
"""

from __future__ import annotations

import pathlib
from collections.abc import Sequence
from dataclasses import dataclass

from ..composition import Composition
from ..corpus import DEFAULT_CORPUS_VERSION
from ..corpus import load_corpus as _load_corpus
from . import splits as _splits
from .splits import SplitScheme
from .taxonomy import binary_observed

#: Task name to the function projecting a canonical 4-class label onto it.
TASKS = {
    # The full canonical taxonomy: which single-phase structure forms, or
    # none of them.
    "phase4": lambda canonical: canonical,
    # The textbook screening question the empirical rules actually answer:
    # does a single-phase solid solution form at all.
    "single_vs_multi": binary_observed,
}



@dataclass(frozen=True)
class BenchmarkRow:
    """One benchmark alloy.

    Attributes
    ----------
    composition_key
        The corpus join key: elements sorted alphabetically at 4-decimal
        mole-fraction precision. Unique within the corpus.
    composition
        Normalized mole-fraction dict, the form every descriptor takes.
    family
        Alloy-family key, the grouping unit of the grouped split.
    label
        The class for the selected task.
    canonical_phase
        The underlying 4-class corpus label, kept even when the task
        projects it to something coarser.
    sources
        Upstream datasets that contributed this composition.
    n_elements
        Number of elements present.
    descriptor_ready
        True when every element is covered by both the element table and
        the Miedema pair table, so the package's descriptors are all
        computable. Rows are kept either way; this only marks which ones
        a descriptor-based model can score.
    """

    composition_key: str
    composition: Composition
    family: str
    label: str
    canonical_phase: str
    sources: tuple[str, ...]
    n_elements: int
    descriptor_ready: bool


@dataclass(frozen=True)
class Benchmark:
    """The corpus, its labels, and both frozen split schemes.

    ``grouped`` and ``random`` partition exactly these rows with the same
    fold count, so their scores are directly comparable and their
    difference is attributable to grouping alone.
    """

    corpus_version: str
    task: str
    rows: tuple[BenchmarkRow, ...]
    grouped: SplitScheme
    random: SplitScheme
    manifest: dict

    def __len__(self) -> int:
        return len(self.rows)

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(row.label for row in self.rows)

    @property
    def families(self) -> tuple[str, ...]:
        return tuple(row.family for row in self.rows)

    @property
    def compositions(self) -> tuple[Composition, ...]:
        return tuple(row.composition for row in self.rows)

    def subset_indices(self, *, descriptor_ready_only: bool = False) -> tuple[int, ...]:
        """Row positions passing a filter, for models that cannot score everything.

        Filtering here never moves a row between folds. Fold membership
        is decided once, over the whole corpus, so two models evaluated
        on different subsets are still being tested on the same
        partition of chemistry.
        """
        return tuple(
            index
            for index, row in enumerate(self.rows)
            if not descriptor_ready_only or row.descriptor_ready
        )

    def describe(self) -> dict:
        """Composition of the benchmark and the balance of both schemes."""
        labels = self.labels
        return {
            "corpus_version": self.corpus_version,
            "task": self.task,
            "n_rows": len(self.rows),
            "n_descriptor_ready": len(self.subset_indices(descriptor_ready_only=True)),
            "grouped": self.grouped.summary(labels),
            "random": self.random.summary(labels),
            "family_overlap_profile": _splits.family_overlap_profile(
                self.grouped, self.random, self.families
            ),
        }


def load_benchmark(
    *,
    task: str = "phase4",
    k: int = _splits.DEFAULT_K,
    seed: int = _splits.DEFAULT_SEED,
    version: str = DEFAULT_CORPUS_VERSION,
    corpus_dir: pathlib.Path | None = None,
) -> Benchmark:
    """Load the corpus and attach both frozen split schemes.

    Rows excluded, and why:

    - **Cross-source label conflicts.** Where two upstream datasets
      report different phases for the same composition the corpus leaves
      ``canonical_phase`` blank and sets ``has_conflict``. Those rows are
      dropped here rather than resolved by a vote, because a vote would
      manufacture agreement the literature does not have. In corpus
      v0.1.0 this is 100 rows. They stay in the CSV for anyone who wants
      to study the disagreement itself.
    - **Unparseable composition keys.** None are expected; the key is
      generated by the build. The guard exists so a corrupted corpus
      fails loudly at load rather than silently later.

    Parameters
    ----------
    task
        ``"phase4"`` for the 4-class taxonomy or ``"single_vs_multi"``
        for the binary screening question. See :data:`TASKS`.
    k
        Fold count, shared by both schemes.
    seed
        Seed for the random scheme only. The grouped scheme is not
        random and ignores this.
    version
        Corpus version directory to read. ``"0.1.0"`` (the default) is
        the reference corpus: three hand-curated sources, and the
        corpus every published baseline number is measured on.
        ``"0.2.0"`` is the extended corpus, adding the Chizhevskiy
        LLM-extracted database (CC-BY-4.0) for 10,064 labelled rows.
        It is deliberately opt-in rather than the default because its
        labels are measurably noisier: on overlapping alloys it agrees
        with the reference consensus only ~70% of the time, and every
        disagreement is quarantined as a conflict rather than voted
        on. Both versions' splits are frozen and digest-pinned.
    corpus_dir
        Explicit directory, overriding both the environment variable and
        the repository-relative default.

    Raises
    ------
    FileNotFoundError
        If the corpus has not been built. The message gives the commands.
    ValueError
        If ``task`` is unknown.
    """
    if task not in TASKS:
        raise ValueError(f"unknown task {task!r}; expected one of {sorted(TASKS)}")

    # The corpus package owns reading, provenance parsing, and the
    # missing-corpus error; this wrapper only projects labels and
    # attaches the frozen splits. Row order is the corpus CSV order,
    # which is what the split digests are computed over.
    corpus = _load_corpus(version=version, corpus_dir=corpus_dir)
    project = TASKS[task]

    rows: list[BenchmarkRow] = []
    for corpus_row in corpus.rows:
        canonical = corpus_row.canonical_phase
        if canonical is None:
            continue
        label = project(canonical)
        if label is None:
            continue
        rows.append(
            BenchmarkRow(
                composition_key=corpus_row.composition_key,
                composition=corpus_row.composition,
                family=corpus_row.family,
                label=label,
                canonical_phase=canonical,
                sources=corpus_row.sources,
                n_elements=corpus_row.n_elements,
                descriptor_ready=corpus_row.descriptor_ready,
            )
        )

    if not rows:
        raise ValueError(f"corpus v{version} yielded no labelled rows")

    # Row order is the corpus CSV order, which the build writes sorted by
    # composition_key. The split digests are computed over that order, so
    # anything that reorders the CSV changes the digests and is caught.
    labels = [row.label for row in rows]
    families = [row.family for row in rows]

    return Benchmark(
        corpus_version=version,
        task=task,
        rows=tuple(rows),
        grouped=_splits.grouped_split(families, labels, k=k),
        random=_splits.random_split(labels, k=k, seed=seed),
        manifest=corpus.manifest,
    )


def descriptor_names(backend: object = None) -> tuple[str, ...]:
    """Names of the descriptors :func:`descriptor_matrix` returns, in order.

    ``backend`` selects whose feature space is being described: None or
    ``"native"`` for this package's own descriptors (the frozen 14-name
    order every baseline was computed with), ``"heacalculator"`` or a
    backend instance for that backend's all-float subset.
    """
    from ..descriptors.backend import get_backend

    # get_backend(None) is the native backend, whose matrix_names() IS
    # the frozen 14-name order; one tuple, defined once.
    return get_backend(backend).matrix_names()


def finite_descriptor_indices(benchmark: Benchmark) -> tuple[int, ...]:
    """Rows a descriptor-based model can actually be fitted on.

    Stricter than ``descriptor_ready``, which only checks that the
    element tables cover every element. Some covered alloys still have a
    singular descriptor: Omega is ``Tm * dSmix / |dHmix|`` and diverges
    as the mixing enthalpy approaches zero, which is exactly what
    happens for near-ideal systems such as Ag-Au. The two phi descriptors
    diverge for the same reason. In corpus v0.1.0 this removes 156 of the
    7,373 element-covered rows, about 2 percent.

    Those rows are dropped rather than clipped because a clipped
    infinity is a number the model will happily fit and no one can
    interpret. Be aware that the exclusion is not random: near-ideal
    alloys skew toward single-phase solid solutions, so the surviving
    subset is slightly harder than the full corpus. The count and class
    balance of what was dropped belong in any writeup that uses this
    filter.

    This computes every descriptor for every row and takes several
    seconds. Call it once and pass the result to
    :func:`hea_bench.benchmark.evaluate` as ``indices``.
    """
    import math

    covered = benchmark.subset_indices(descriptor_ready_only=True)
    matrix = descriptor_matrix([benchmark.rows[index].composition for index in covered])
    return tuple(
        index
        for index, values in zip(covered, matrix)
        if all(math.isfinite(value) for value in values)
    )


def descriptor_matrix(
    compositions: Sequence[Composition], *, backend: object = None
) -> list[list[float]]:
    """Compute a descriptor feature matrix for each composition.

    With ``backend=None`` (the default) this computes the package's own
    descriptors, so a baseline model can be fitted on exactly the
    quantities this package documents, with no third-party featurizer in
    the way. ``singh_lambda`` is excluded because it is infinite when
    delta is zero, and ``h_elastic`` because it is ``None`` for elements
    missing bulk modulus or volume. This default path is frozen: it is
    the feature space every published baseline number was computed with.

    ``backend`` (a name or a ``DescriptorBackend`` instance) computes
    that backend's own all-float subset instead; the column names are
    ``descriptor_names(backend=...)``. Matrices from different backends
    are different feature spaces built from different reference data,
    not interchangeable drop-ins; see docs/backend-agreement.md.

    Raises
    ------
    ValueError
        If any composition contains an element the active backend's
        tables do not cover (the message names the composition and the
        descriptor; nothing is imputed). For the native backend, filter
        with ``Benchmark.subset_indices(descriptor_ready_only=True)``
        first.
    """
    if backend is None:
        from ..descriptors.backend import _NATIVE, NativeBackend

        # The same function objects the backend registry holds, in the
        # frozen matrix order; exceptions propagate exactly as the
        # direct calls did.
        functions = tuple(
            _NATIVE[name][0] for name in NativeBackend().matrix_names()
        )
        return [[float(function(comp)) for function in functions] for comp in compositions]

    from ..descriptors.backend import get_backend

    resolved = get_backend(backend)
    names = resolved.matrix_names()
    matrix: list[list[float]] = []
    for comp in compositions:
        values = resolved.compute(comp)
        row: list[float] = []
        for name in names:
            value = values.get(name)
            if value is None:
                raise ValueError(
                    f"backend {resolved.name!r} cannot compute {name!r} for "
                    f"composition {comp!r}; drop such rows or use a backend that "
                    f"covers them"
                )
            row.append(float(value))
        matrix.append(row)
    return matrix


__all__ = [
    "DEFAULT_CORPUS_VERSION",
    "TASKS",
    "Benchmark",
    "BenchmarkRow",
    "descriptor_matrix",
    "descriptor_names",
    "finite_descriptor_indices",
    "load_benchmark",
]
