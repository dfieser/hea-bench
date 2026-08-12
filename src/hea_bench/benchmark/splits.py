"""Frozen train/test splits for the HEA phase-prediction benchmark.

Two split schemes are built over the same rows, the same fold count, and
the same class labels. Only the partition rule differs, so the pair
isolates one effect: how much of a reported score comes from testing on
alloys whose close relatives were in the training set.

**Grouped** puts a whole alloy family on one side of every fold
boundary. A family is the *set of elements present*, so every
stoichiometric variant of one system travels together. All of
``Al0.1CoCrFeNi``, ``Al0.3CoCrFeNi`` and ``Al2CoCrFeNi`` are the family
``Al-Co-Cr-Fe-Ni`` and land in the same fold. A model is therefore
scored on chemistries it has never seen.

**Random** ignores families and shuffles rows. Near-duplicate variants
of one system land on both sides, so the model can interpolate along a
composition line it has already been fitted to. This is the protocol
most published HEA phase-prediction numbers use, so it is the half of
the pair that is comparable to the literature, and it answers a real
question: performance on new stoichiometries of known systems.

Neither scheme is "correct" on its own. Reported together they say what
a model does on new stoichiometries of a known system (random, the
interpolative question) versus on an unseen element system (grouped,
the extrapolative question), and the gap between them is the quantity
this benchmark exists to measure. Grouped evaluation of materials
models is established prior art (Meredig et al. 2018 LOCO-CV; Li et
al., Commun. Mater. 2025); what this module adds is a frozen,
digest-pinned instance for this corpus.

Determinism
-----------
The grouped scheme uses no random number generator at all. Families are
ordered by descending row count with ties broken alphabetically, then
each is placed in whichever fold is currently least loaded, measured as
the sum over classes of the squared class count normalized by that
class's corpus total. Ties break to the lowest fold index.

The load comparison is done in exact integer arithmetic, not floats, so
the assignment cannot depend on any float's last bit. Determinism of
the whole chain was earned the expensive way: the first release attempt
was blocked by the CI freeze gate because Python 3.12 computes builtin
``sum`` with compensated (Neumaier) summation while 3.10 does not, and
that last-bit difference in composition normalization totals moved a
few mole fractions across a decimal rounding boundary, changed a
handful of composition keys, and cascaded into different folds. The
corpus build now uses exactly rounded ``math.fsum`` (see
:func:`hea_bench.composition.normalize`), this module keeps every
comparison in integers, and the CI ``benchmark-freeze`` job rebuilds
the corpus and checks the digests on Linux to hold the guarantee
mechanically.

The random scheme is seeded and stratified by class, so it too is
reproducible, and it is fair to the grouped scheme in class balance.

Both schemes carry a SHA-256 digest of their own fold assignment.
:func:`freeze_digest` computes it and the corpus manifest pins it, which
is what makes a split "frozen" in a way a reader can check rather than
trust.

Why families cannot be balanced perfectly
-----------------------------------------
The corpus is dominated by a few heavily studied systems. In corpus
v0.1.0 the largest family holds 767 of 7,683 labelled rows, or one row
in ten, and it has to sit entirely inside one fold. Perfect balance is
therefore unreachable by construction. The greedy rule above gets fold
sizes within about 8 percent of each other and the rarest class, HCP,
within about 4 percent. Those residual imbalances are reported in the
split summary rather than hidden, because per-fold scores should be read
in light of them.

Known limitation, measured
--------------------------
Grouping by element set does not catch every near-duplicate. Dropping an
element changes the set, so ``CoCrFeNi`` is a different family from
``AlCoCrFeNi`` even though the second is the first plus an addition.
Some relatedness therefore survives the grouped split, which means the
grouped score is an upper bound on true out-of-system performance, not a
lower bound.

The obvious stricter rule, closing families under the subset relation so
an alloy system and all its extensions travel together, was measured
rather than guessed at: on corpus v0.1.0 it collapses 956 of the 1,259
families into one connected component holding 7,260 of the 7,683
labelled rows, 94.5 percent (:func:`subset_closure_components`, with the
numbers pinned in the test suite). A five-fold split cannot be built
around one indivisible block that large, so subset closure is not a
usable protocol on this corpus. That is a statement about the
literature, not about this package: the experimentally studied HEA
compositions form a single connected web of shared subsystems, and
element-set grouping is the strictest family-level rule that still
leaves cross-validation possible.
"""

from __future__ import annotations

import hashlib
import random
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

# family_of moved to hea_bench.composition (the corpus package and the
# split machinery both need it); re-exported here so every existing
# import path keeps working.
from ..composition import family_of  # noqa: F401

DEFAULT_K = 5
DEFAULT_SEED = 0


@dataclass(frozen=True)
class Fold:
    """One fold's row indices, as positions into the benchmark row list."""

    index: int
    train: tuple[int, ...]
    test: tuple[int, ...]


@dataclass(frozen=True)
class SplitScheme:
    """A complete k-fold partition of the benchmark rows.

    Attributes
    ----------
    name
        ``"grouped"`` or ``"random"``.
    k
        Number of folds.
    seed
        Seed used by the random scheme; ``None`` for the grouped scheme,
        which uses no randomness.
    folds
        One :class:`Fold` per fold, in fold-index order.
    fold_of
        Per-row fold index, aligned with the benchmark row list. This is
        the primitive the folds are derived from and the thing the
        digest is computed over.
    digest
        SHA-256 of the canonical serialization of ``fold_of``. Two runs
        that agree here produced identical splits.
    """

    name: str
    k: int
    seed: int | None
    folds: tuple[Fold, ...]
    fold_of: tuple[int, ...]
    digest: str

    def summary(self, labels: Sequence[str]) -> dict:
        """Per-fold row and class counts, for reporting fold balance."""
        per_fold: list[Counter] = [Counter() for _ in range(self.k)]
        for fold_index, label in zip(self.fold_of, labels):
            per_fold[fold_index][label] += 1
        classes = sorted({label for label in labels})
        return {
            "name": self.name,
            "k": self.k,
            "seed": self.seed,
            "digest": self.digest,
            "rows_per_fold": [sum(counter.values()) for counter in per_fold],
            "class_counts_per_fold": {
                cls: [per_fold[i][cls] for i in range(self.k)] for cls in classes
            },
        }


def freeze_digest(fold_of: Sequence[int]) -> str:
    """SHA-256 over the canonical fold assignment.

    The assignment is serialized as the fold indices in row order joined
    by commas, so the digest changes if any row moves folds or if the
    row order itself changes.
    """
    payload = ",".join(str(index) for index in fold_of)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _folds_from_assignment(fold_of: Sequence[int], k: int) -> tuple[Fold, ...]:
    test_buckets: list[list[int]] = [[] for _ in range(k)]
    for row_index, fold_index in enumerate(fold_of):
        test_buckets[fold_index].append(row_index)
    universe = set(range(len(fold_of)))
    return tuple(
        Fold(
            index=fold_index,
            train=tuple(sorted(universe.difference(bucket))),
            test=tuple(bucket),
        )
        for fold_index, bucket in enumerate(test_buckets)
    )


def grouped_split(
    families: Sequence[str],
    labels: Sequence[str],
    *,
    k: int = DEFAULT_K,
) -> SplitScheme:
    """Build the composition-family-grouped split.

    Every row of one family lands in one fold, so no alloy system
    straddles a train/test boundary.

    Parameters
    ----------
    families
        Per-row family key, as produced by :func:`family_of`.
    labels
        Per-row class label, used only to balance classes across folds.
    k
        Number of folds.

    Raises
    ------
    ValueError
        If ``families`` and ``labels`` differ in length, if they are
        empty, if ``k`` is below 2, or if there are fewer families than
        folds (which would leave a fold empty).
    """
    if len(families) != len(labels):
        raise ValueError("families and labels must have the same length")
    if not families:
        raise ValueError("cannot split an empty benchmark")
    if k < 2:
        raise ValueError("k must be at least 2")

    rows_by_family: dict[str, list[int]] = defaultdict(list)
    for row_index, family in enumerate(families):
        rows_by_family[family].append(row_index)
    if len(rows_by_family) < k:
        raise ValueError(
            f"{len(rows_by_family)} families cannot fill {k} folds; "
            f"use a smaller k or a finer grouping"
        )

    corpus_totals = Counter(labels)
    # Largest families first: placing the big, inflexible blocks while
    # every fold is still nearly empty is what keeps the final spread
    # small. Alphabetical tie-break keeps the order deterministic.
    ordered = sorted(rows_by_family, key=lambda family: (-len(rows_by_family[family]), family))

    # The cost being minimized is sum over classes of (load/total)^2, the
    # squared load normalized per class so a rare class such as HCP pulls
    # as hard as a common one. It is compared in exact integer arithmetic:
    # multiplying through by the product of all squared totals turns
    # sum(load_c^2 / total_c^2) into sum(load_c^2 * weight_c) with integer
    # weights, which preserves the argmin exactly. Floats are banned from
    # this comparison deliberately: a greedy argmin amplifies any last-bit
    # float discrepancy into a completely different assignment, so the
    # assignment must not be able to see one. Python integers are exact
    # on every platform and version.
    classes = sorted(corpus_totals)
    denominator_product = 1
    for cls in classes:
        denominator_product *= corpus_totals[cls] ** 2
    weight = {cls: denominator_product // corpus_totals[cls] ** 2 for cls in classes}

    fold_loads: list[Counter] = [Counter() for _ in range(k)]
    fold_of = [0] * len(families)

    for family in ordered:
        family_rows = rows_by_family[family]
        family_labels = Counter(labels[row_index] for row_index in family_rows)

        def load_after(fold_index: int, family_labels: Counter = family_labels) -> int:
            return sum(
                (fold_loads[fold_index][cls] + family_labels[cls]) ** 2 * weight[cls]
                for cls in classes
            )

        chosen = min(range(k), key=lambda fold_index: (load_after(fold_index), fold_index))
        fold_loads[chosen] += family_labels
        for row_index in family_rows:
            fold_of[row_index] = chosen

    frozen = tuple(fold_of)
    return SplitScheme(
        name="grouped",
        k=k,
        seed=None,
        folds=_folds_from_assignment(frozen, k),
        fold_of=frozen,
        digest=freeze_digest(frozen),
    )


def random_split(
    labels: Sequence[str],
    *,
    k: int = DEFAULT_K,
    seed: int = DEFAULT_SEED,
) -> SplitScheme:
    """Build the class-stratified random split, ignoring alloy families.

    This is the leaky counterpart to :func:`grouped_split`. It exists to
    be compared against, not to be reported alone.

    Rows are shuffled within their class and dealt round-robin into
    folds, which keeps each class's per-fold counts within one of each
    other and makes the comparison against the grouped scheme a
    comparison of grouping alone rather than of class balance.
    """
    if not labels:
        raise ValueError("cannot split an empty benchmark")
    if k < 2:
        raise ValueError("k must be at least 2")

    rng = random.Random(seed)
    rows_by_class: dict[str, list[int]] = defaultdict(list)
    for row_index, label in enumerate(labels):
        rows_by_class[label].append(row_index)

    fold_of = [0] * len(labels)
    next_fold = 0
    for cls in sorted(rows_by_class):
        indices = list(rows_by_class[cls])
        rng.shuffle(indices)
        # Carry the starting fold across classes so that a run of small
        # classes does not pile every one of them onto fold 0.
        for offset, row_index in enumerate(indices):
            fold_of[row_index] = (next_fold + offset) % k
        next_fold = (next_fold + len(indices)) % k

    frozen = tuple(fold_of)
    return SplitScheme(
        name="random",
        k=k,
        seed=seed,
        folds=_folds_from_assignment(frozen, k),
        fold_of=frozen,
        digest=freeze_digest(frozen),
    )


def subset_closure_components(families: Sequence[str]) -> list[tuple[int, int]]:
    """Connected components of families under the subset/superset relation.

    Two families are linked when one's element set contains the other's,
    the relation a stricter grouping rule would have to respect (so that
    ``Co-Cr-Fe-Ni`` and ``Al-Co-Cr-Fe-Ni`` cannot end up on opposite
    sides of a fold boundary). Returns one ``(n_families, n_rows)`` pair
    per component, sorted by row count descending.

    This exists to document why that stricter rule is *not* offered as a
    scheme: on corpus v0.1.0 the largest component holds 94.5 percent of
    the labelled rows, so no k-fold partition can respect the closure.
    See the module docstring.
    """
    row_counts: dict[frozenset[str], int] = defaultdict(int)
    for family in families:
        row_counts[frozenset(family.split("-"))] += 1

    keys = sorted(row_counts, key=len)
    parent: dict[frozenset[str], frozenset[str]] = {key: key for key in keys}

    def find(key: frozenset[str]) -> frozenset[str]:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    # Sorted by size, so only the strict-subset direction needs testing.
    for index, small in enumerate(keys):
        for large in keys[index + 1 :]:
            if len(large) > len(small) and small <= large:
                root_small, root_large = find(small), find(large)
                if root_small != root_large:
                    parent[root_small] = root_large

    components: dict[frozenset[str], list[int]] = defaultdict(lambda: [0, 0])
    for key in keys:
        component = components[find(key)]
        component[0] += 1
        component[1] += row_counts[key]
    return sorted(
        ((n_families, n_rows) for n_families, n_rows in components.values()),
        key=lambda pair: -pair[1],
    )


def straddling_families(scheme: SplitScheme, families: Sequence[str]) -> dict[str, int]:
    """Families that appear in more than one fold, and how many folds each spans.

    Zero for a grouped scheme, by construction. Large for a random
    scheme, which is the point of the contrast: it counts the systems
    whose variants sit on both sides of the train/test boundary, where
    a model can interpolate between close relatives.
    """
    folds_per_family: dict[str, set[int]] = defaultdict(set)
    for fold_index, family in zip(scheme.fold_of, families):
        folds_per_family[family].add(fold_index)
    return {
        family: len(folds)
        for family, folds in sorted(folds_per_family.items())
        if len(folds) > 1
    }


def family_overlap_profile(
    grouped: SplitScheme,
    randomized: SplitScheme,
    families: Sequence[str],
) -> Mapping[str, object]:
    """Summarize how much family overlap each scheme allows.

    This is descriptive only. It quantifies the opportunity for
    interpolation that each split leaves open, before any model is run.
    """
    straddling = straddling_families(randomized, families)
    rows_in_straddling = sum(1 for family in families if family in straddling)
    return {
        "n_rows": len(families),
        "n_families": len({*families}),
        "grouped_straddling_families": len(straddling_families(grouped, families)),
        "random_straddling_families": len(straddling),
        "random_rows_in_straddling_families": rows_in_straddling,
        "random_fraction_rows_interpolable": (
            rows_in_straddling / len(families) if families else 0.0
        ),
    }


__all__ = [
    "DEFAULT_K",
    "DEFAULT_SEED",
    "Fold",
    "SplitScheme",
    "family_of",
    "freeze_digest",
    "grouped_split",
    "family_overlap_profile",
    "random_split",
    "straddling_families",
    "subset_closure_components",
]
