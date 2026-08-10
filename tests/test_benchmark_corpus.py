"""Tests for hea_bench.benchmark.corpus, including the frozen split digests.

The corpus is built locally rather than shipped, because most of its
upstream data is not licensed for redistribution. Everything here that
needs the built corpus skips when it is absent, so a plain checkout
still runs a clean suite. The tests that pin the frozen splits therefore
only bite where the data exists, which is the environment where a split
could actually drift.
"""

import pathlib

import pytest

from hea_bench.benchmark import corpus as _corpus
from hea_bench.benchmark import load_benchmark
from hea_bench.benchmark.corpus import descriptor_matrix, descriptor_names

# --- the freeze ------------------------------------------------------------
#
# These digests ARE the frozen splits. A change to the corpus, the row
# order, the grouping rule, or the assignment rule moves them. If one of
# these fails, do not update the constant to make it pass: work out what
# moved and whether the benchmark needs a new version. Rewriting a
# published split silently is how a benchmark stops being one.

CORPUS_VERSION = "0.1.0"
EXPECTED_ROWS = 7683
EXPECTED_FAMILIES = 1259
EXPECTED_ELEMENT_COVERED = 7373

# Computed with math.fsum-based normalization (see composition.normalize),
# verified byte-identical across Python 3.10 and 3.13 on Windows and
# Python 3.12 on Linux before pinning.
FROZEN_DIGESTS = {
    "single_vs_multi": {
        "grouped": "a1d87ef65c5a96485edecbb6fea4ec8c10b82ef303de300b43292adb7b485226",
        "random": "33a2cbffce2b7c0657bd1962ba6f73559a54e7247c172f3f49940293cb5e820a",
    },
    "phase4": {
        "grouped": "3996c5a68b58a07c31b2586efdc0c7b1415108391e2a674641b226a8814fda16",
        "random": "171fdb33115efe7701eb96b289ec2db7073a4897e18eead91162b6b934ac0531",
    },
}

_CORPUS_CSV = (
    pathlib.Path(__file__).resolve().parents[1]
    / "data" / "consolidated" / f"v{CORPUS_VERSION}" / "consolidated.csv"
)

needs_corpus = pytest.mark.skipif(
    not _CORPUS_CSV.exists(),
    reason=(
        "benchmark corpus not built; run data/raw/peivaste/fetch.py then "
        "python -m hea_bench.benchmark.consolidate"
    ),
)


# --- behaviour that needs no data ------------------------------------------


def test_missing_corpus_raises_with_the_build_commands() -> None:
    """The error has to tell the user how to fix it, since the data is not shipped."""
    with pytest.raises(FileNotFoundError) as caught:
        load_benchmark(corpus_dir=pathlib.Path("no-such-directory"))
    message = str(caught.value)
    assert "consolidate" in message
    assert "fetch.py" in message


def test_unknown_task_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown task"):
        load_benchmark(task="not-a-task")


def test_descriptor_names_match_the_matrix_width() -> None:
    cantor = {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}
    matrix = descriptor_matrix([cantor])
    assert len(matrix) == 1
    assert len(matrix[0]) == len(descriptor_names())


def test_descriptor_matrix_matches_the_pinned_cantor_values() -> None:
    """Ties the feature matrix to the package's canonical sanity values."""
    cantor = {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}
    values = dict(zip(descriptor_names(), descriptor_matrix([cantor])[0]))
    assert values["smix"] == pytest.approx(13.381, abs=5e-4)
    assert values["delta"] == pytest.approx(3.164, abs=5e-4)
    assert values["vec"] == pytest.approx(8.0, abs=5e-4)
    assert values["omega"] == pytest.approx(5.794, abs=5e-4)


# --- the built corpus ------------------------------------------------------


@needs_corpus
def test_corpus_size_and_family_count() -> None:
    bench = load_benchmark(task="single_vs_multi")
    assert len(bench) == EXPECTED_ROWS
    assert len({*bench.families}) == EXPECTED_FAMILIES
    assert len(bench.subset_indices(descriptor_ready_only=True)) == EXPECTED_ELEMENT_COVERED


@needs_corpus
@pytest.mark.parametrize("task", sorted(FROZEN_DIGESTS))
def test_frozen_split_digests(task: str) -> None:
    """The splits are frozen. These digests are the freeze."""
    bench = load_benchmark(task=task)
    assert bench.grouped.digest == FROZEN_DIGESTS[task]["grouped"]
    assert bench.random.digest == FROZEN_DIGESTS[task]["random"]


@needs_corpus
def test_conflict_rows_are_excluded_not_voted_on() -> None:
    """Rows where sources disagree must not be resolved by a majority vote."""
    import csv

    with _CORPUS_CSV.open(newline="", encoding="utf-8") as handle:
        total = sum(1 for _ in csv.DictReader(handle))
    with _CORPUS_CSV.open(newline="", encoding="utf-8") as handle:
        conflicts = sum(
            1 for row in csv.DictReader(handle) if row["has_conflict"] == "1"
        )
    assert conflicts == 100
    assert len(load_benchmark(task="single_vs_multi")) == total - conflicts


@needs_corpus
def test_no_family_straddles_a_grouped_fold() -> None:
    """The central guarantee, checked on the real corpus rather than a toy."""
    from hea_bench.benchmark.splits import straddling_families

    bench = load_benchmark(task="single_vs_multi")
    assert straddling_families(bench.grouped, bench.families) == {}


@needs_corpus
def test_the_random_split_leaks_most_of_the_corpus() -> None:
    """Quantifies why the contrast matters on this particular corpus."""
    bench = load_benchmark(task="single_vs_multi")
    profile = bench.describe()["leakage_profile"]
    assert profile["grouped_straddling_families"] == 0
    assert profile["random_fraction_rows_interpolable"] > 0.85


@needs_corpus
def test_grouped_folds_stay_within_ten_percent_on_size() -> None:
    """Whole families move as blocks, so balance is approximate by construction."""
    bench = load_benchmark(task="single_vs_multi")
    sizes = bench.grouped.summary(bench.labels)["rows_per_fold"]
    assert max(sizes) / min(sizes) < 1.10


@needs_corpus
def test_both_tasks_project_the_same_rows() -> None:
    binary = load_benchmark(task="single_vs_multi")
    four = load_benchmark(task="phase4")
    assert [row.composition_key for row in binary.rows] == [
        row.composition_key for row in four.rows
    ]
    assert set(four.labels) == {"BCC", "FCC", "HCP", "multi-phase"}
    assert set(binary.labels) == {"single-phase", "multi-phase"}


@needs_corpus
def test_subset_closure_is_infeasible_on_this_corpus() -> None:
    """Pins the measurement that rules out strict subset-closure grouping.

    One component holds 94.5% of labelled rows, so no k-fold partition
    can respect the closure. This is why element-set grouping is the
    strictest scheme the benchmark offers; see the splits module
    docstring. If these numbers move, the corpus changed.
    """
    from hea_bench.benchmark.splits import subset_closure_components

    bench = load_benchmark(task="single_vs_multi")
    components = subset_closure_components(bench.families)
    assert len(components) == 302
    n_families, n_rows = components[0]
    assert (n_families, n_rows) == (956, 7260)
    assert n_rows / len(bench) == pytest.approx(0.945, abs=0.001)


@needs_corpus
def test_singular_descriptor_rows_are_dropped_by_the_finite_filter() -> None:
    """Near-ideal alloys such as Ag-Au have a divergent Omega and must be excluded."""
    bench = load_benchmark(task="single_vs_multi")
    covered = set(bench.subset_indices(descriptor_ready_only=True))
    finite = set(_corpus.finite_descriptor_indices(bench))
    assert finite < covered
    dropped_keys = {bench.rows[index].composition_key for index in covered - finite}
    assert "Ag0.5000Au0.5000" in dropped_keys
