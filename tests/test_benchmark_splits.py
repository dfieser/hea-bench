"""Tests for hea_bench.benchmark.splits (grouping, determinism, freezing)."""

import pytest

from hea_bench.benchmark.splits import (
    family_of,
    freeze_digest,
    grouped_split,
    family_overlap_profile,
    random_split,
    straddling_families,
)


def _toy_corpus(n_families: int = 12, per_family: int = 4):
    """Families of equal size with alternating labels."""
    families, labels = [], []
    for family_index in range(n_families):
        for row in range(per_family):
            families.append(f"F{family_index:02d}")
            labels.append("single-phase" if (family_index + row) % 2 else "multi-phase")
    return families, labels


# --- family_of -------------------------------------------------------------


def test_family_ignores_amounts() -> None:
    """Every stoichiometric variant of one system shares a family."""
    lean = {"Al": 0.02, "Co": 0.245, "Cr": 0.245, "Fe": 0.245, "Ni": 0.245}
    rich = {"Al": 0.40, "Co": 0.150, "Cr": 0.150, "Fe": 0.150, "Ni": 0.150}
    assert family_of(lean) == family_of(rich) == "Al-Co-Cr-Fe-Ni"


def test_family_is_alphabetical_regardless_of_dict_order() -> None:
    assert family_of({"Ni": 0.5, "Co": 0.3, "Al": 0.2}) == "Al-Co-Ni"


def test_family_drops_zero_amount_elements() -> None:
    """A zero-amount element is not present, so it is not part of the system."""
    assert family_of({"Al": 0.0, "Co": 0.5, "Ni": 0.5}) == "Co-Ni"


def test_family_differs_when_an_element_is_dropped() -> None:
    """The documented limitation: an addition makes a different family."""
    assert family_of({"Co": 0.25, "Cr": 0.25, "Fe": 0.25, "Ni": 0.25}) != family_of(
        {"Al": 0.2, "Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Ni": 0.2}
    )


# --- grouped split ---------------------------------------------------------


def test_grouped_split_keeps_families_whole() -> None:
    """The core guarantee: no alloy system straddles a fold boundary."""
    families, labels = _toy_corpus()
    scheme = grouped_split(families, labels, k=4)
    assert straddling_families(scheme, families) == {}


def test_grouped_split_partitions_every_row_exactly_once() -> None:
    families, labels = _toy_corpus()
    scheme = grouped_split(families, labels, k=4)
    test_rows = [row for fold in scheme.folds for row in fold.test]
    assert sorted(test_rows) == list(range(len(families)))
    for fold in scheme.folds:
        assert set(fold.train).isdisjoint(fold.test)
        assert len(fold.train) + len(fold.test) == len(families)


def test_grouped_split_is_deterministic() -> None:
    """No RNG at all, so repeated calls agree byte for byte."""
    families, labels = _toy_corpus()
    first = grouped_split(families, labels, k=4)
    second = grouped_split(families, labels, k=4)
    assert first.fold_of == second.fold_of
    assert first.digest == second.digest
    assert first.seed is None


def test_grouped_split_balances_equal_families_exactly() -> None:
    """With 12 equal families over 4 folds each fold takes 3 of them."""
    families, labels = _toy_corpus(n_families=12, per_family=4)
    scheme = grouped_split(families, labels, k=4)
    assert scheme.summary(labels)["rows_per_fold"] == [12, 12, 12, 12]


def test_grouped_split_rejects_fewer_families_than_folds() -> None:
    families, labels = _toy_corpus(n_families=3, per_family=5)
    with pytest.raises(ValueError, match="cannot fill"):
        grouped_split(families, labels, k=5)


def test_grouped_split_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError, match="same length"):
        grouped_split(["A", "B"], ["x"], k=2)


def test_grouped_split_rejects_empty_and_small_k() -> None:
    with pytest.raises(ValueError, match="empty"):
        grouped_split([], [], k=2)
    families, labels = _toy_corpus()
    with pytest.raises(ValueError, match="at least 2"):
        grouped_split(families, labels, k=1)


def test_grouped_split_places_the_largest_family_first() -> None:
    """One dominant family must sit whole in a single fold."""
    families = ["big"] * 50 + [f"small{i}" for i in range(10)]
    labels = ["multi-phase"] * 60
    scheme = grouped_split(families, labels, k=5)
    big_folds = {fold for fold, family in zip(scheme.fold_of, families) if family == "big"}
    assert len(big_folds) == 1


# --- random split ----------------------------------------------------------


def test_random_split_is_reproducible_for_a_seed() -> None:
    _, labels = _toy_corpus()
    assert random_split(labels, k=4, seed=7).fold_of == random_split(labels, k=4, seed=7).fold_of


def test_random_split_changes_with_the_seed() -> None:
    _, labels = _toy_corpus(n_families=40, per_family=4)
    assert random_split(labels, k=4, seed=0).fold_of != random_split(labels, k=4, seed=1).fold_of


def test_random_split_stratifies_classes_within_one_row() -> None:
    """Round-robin dealing keeps each class's per-fold counts within one."""
    _, labels = _toy_corpus(n_families=25, per_family=4)
    scheme = random_split(labels, k=5, seed=0)
    for counts in scheme.summary(labels)["class_counts_per_fold"].values():
        assert max(counts) - min(counts) <= 1


def test_random_split_lets_families_straddle() -> None:
    """The whole point of the contrast: families straddle under the random scheme."""
    families, labels = _toy_corpus(n_families=25, per_family=8)
    scheme = random_split(labels, k=5, seed=0)
    assert straddling_families(scheme, families)


def test_random_split_partitions_every_row_exactly_once() -> None:
    _, labels = _toy_corpus()
    scheme = random_split(labels, k=4, seed=0)
    test_rows = [row for fold in scheme.folds for row in fold.test]
    assert sorted(test_rows) == list(range(len(labels)))


# --- freezing --------------------------------------------------------------


def test_freeze_digest_is_pinned() -> None:
    """A literal digest, so a change to the serialization cannot pass silently."""
    assert freeze_digest([0, 1, 2, 0, 1, 2]) == (
        "d9a9a21c9e47d1bce127fe2403b9a9e626a4b34073d9b4b8f46ef6abbad1391a"
    )


def test_freeze_digest_detects_a_single_moved_row() -> None:
    assert freeze_digest([0, 1, 2, 3]) != freeze_digest([0, 1, 3, 2])


def test_scheme_digest_matches_its_assignment() -> None:
    families, labels = _toy_corpus()
    scheme = grouped_split(families, labels, k=4)
    assert scheme.digest == freeze_digest(scheme.fold_of)


# --- subset closure --------------------------------------------------------


def test_subset_closure_links_a_system_to_its_extensions() -> None:
    """CoCrFeNi and AlCoCrFeNi merge; an unrelated binary stays alone."""
    from hea_bench.benchmark.splits import subset_closure_components

    families = ["Co-Cr-Fe-Ni", "Al-Co-Cr-Fe-Ni", "Al-Co-Cr-Fe-Ni", "Mo-Nb"]
    components = subset_closure_components(families)
    assert components == [(2, 3), (1, 1)]


def test_subset_closure_is_transitive() -> None:
    """A shared subsystem chains otherwise-unrelated families together."""
    from hea_bench.benchmark.splits import subset_closure_components

    # Co-Cr links to both extensions, which never compare to each other
    # directly, so all three must land in one component.
    families = ["Co-Cr", "Al-Co-Cr", "Co-Cr-Ni"]
    components = subset_closure_components(families)
    assert components == [(3, 3)]


def test_subset_closure_ignores_mere_overlap() -> None:
    """Sharing elements without containment is not a link."""
    from hea_bench.benchmark.splits import subset_closure_components

    families = ["Al-Co-Cr", "Co-Cr-Ni"]  # overlap {Co, Cr}, neither contains the other
    assert subset_closure_components(families) == [(1, 1), (1, 1)]


# --- family overlap profile -------------------------------------------------------


def test_family_overlap_profile_contrasts_the_two_schemes() -> None:
    families, labels = _toy_corpus(n_families=25, per_family=8)
    profile = family_overlap_profile(
        grouped_split(families, labels, k=5),
        random_split(labels, k=5, seed=0),
        families,
    )
    assert profile["grouped_straddling_families"] == 0
    assert profile["random_straddling_families"] > 0
    assert 0.0 < profile["random_fraction_rows_interpolable"] <= 1.0
    assert profile["n_families"] == 25
