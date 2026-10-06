"""Tests for hea_bench.benchmark.corpus, including the frozen split digests.

The corpus is built locally rather than shipped, because most of its
upstream data is not licensed for redistribution. Everything here that
needs the built corpus skips when it is absent, so a plain checkout
still runs a clean suite. The tests that pin the frozen splits therefore
only bite where the data exists, which is the environment where a split
could actually drift.
"""

import hashlib
import json
import pathlib

import pytest

from hea_bench.benchmark import corpus as _corpus
from hea_bench.benchmark import load_benchmark
from hea_bench.benchmark.corpus import descriptor_matrix, descriptor_names
from hea_bench.benchmark.frozen import FROZEN

# --- the freeze ------------------------------------------------------------
#
# The frozen facts live in hea_bench.benchmark.frozen, so the test suite,
# the CI benchmark-freeze job and the web app all check one table. If one
# of these fails, do not update the constant to make it pass: work out
# what moved and whether the benchmark needs a new version.

CORPUS_VERSION = "0.1.0"

# SHA-256 of the whole FROZEN table, so the table cannot change without
# this test noticing, even though the test now reads the table from the
# library. Adding a new corpus version block legitimately changes it:
# update the hash in the same commit. Changing a published version's
# numbers never is legitimate.
FROZEN_TABLE_SHA256 = "1134fd2788a6876787df324367b875c4560828e5ecc7af5105e9972cd5b85a37"


def test_frozen_table_matches_its_pinned_hash() -> None:
    digest = hashlib.sha256(json.dumps(FROZEN, sort_keys=True).encode("utf-8")).hexdigest()
    assert digest == FROZEN_TABLE_SHA256, (
        "hea_bench.benchmark.frozen.FROZEN changed. If you ADDED a new corpus version block, "
        f"set FROZEN_TABLE_SHA256 in this file to {digest}. If a published version's numbers "
        "changed, revert that edit: published splits never change."
    )

# Kept for the older single-version tests below.
EXPECTED_ROWS = FROZEN["0.1.0"]["rows"]
EXPECTED_FAMILIES = FROZEN["0.1.0"]["families"]
EXPECTED_ELEMENT_COVERED = FROZEN["0.1.0"]["element_covered"]
FROZEN_DIGESTS = FROZEN["0.1.0"]["digests"]

_DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "data" / "consolidated"
_CORPUS_CSV = _DATA_DIR / f"v{CORPUS_VERSION}" / "consolidated.csv"


def _corpus_csv(version: str) -> pathlib.Path:
    return _DATA_DIR / f"v{version}" / "consolidated.csv"


needs_corpus = pytest.mark.skipif(
    not _CORPUS_CSV.exists(),
    reason=(
        "benchmark corpus not built; run data/raw/peivaste/fetch.py then "
        "python -m hea_bench.benchmark.consolidate"
    ),
)


def _needs_version(version: str):
    return pytest.mark.skipif(
        not _corpus_csv(version).exists(),
        reason=f"corpus v{version} not built; run python -m hea_bench.benchmark.consolidate",
    )


# --- behaviour that needs no data ------------------------------------------


def test_missing_corpus_raises_with_the_build_commands() -> None:
    """The error has to tell the user how to fix it, since the data is not shipped."""
    with pytest.raises(FileNotFoundError) as caught:
        load_benchmark(corpus_dir=pathlib.Path("no-such-directory"))
    message = str(caught.value)
    assert "build_corpus()" in message


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
def test_load_benchmark_first_and_last_rows_pinned() -> None:
    """Characterization guard for the corpus-package refactor.

    load_benchmark must keep producing byte-identical rows when its body
    becomes a thin wrapper over hea_bench.corpus. These literals were
    read from the v0.1.0 build before that refactor; if one moves, the
    wrapper changed behavior, not just structure.
    """
    bench = load_benchmark(task="single_vs_multi")
    first, last = bench.rows[0], bench.rows[-1]
    assert first.composition_key == "Ag0.0166Al0.1400Co0.0500Cu0.0833La0.6601Ni0.0500"
    assert first.n_elements == 6
    assert first.family == "Ag-Al-Co-Cu-La-Ni"
    assert first.canonical_phase == "multi-phase"
    assert first.label == "multi-phase"
    assert first.sources == ("peivaste",)
    assert first.descriptor_ready is True
    assert last.composition_key == "Zr1.0000"
    assert last.n_elements == 1
    assert last.canonical_phase == "BCC"
    assert last.label == "single-phase"


@needs_corpus
def test_corpus_size_and_family_count() -> None:
    bench = load_benchmark(task="single_vs_multi")
    assert len(bench) == EXPECTED_ROWS
    assert len({*bench.families}) == EXPECTED_FAMILIES
    assert len(bench.subset_indices(descriptor_ready_only=True)) == EXPECTED_ELEMENT_COVERED


@pytest.mark.parametrize("version", sorted(FROZEN))
@pytest.mark.parametrize("task", ("single_vs_multi", "phase4"))
def test_frozen_split_digests(version: str, task: str) -> None:
    """The splits are frozen. These digests are the freeze, per corpus version."""
    if not _corpus_csv(version).exists():
        pytest.skip(f"corpus v{version} not built")
    bench = load_benchmark(task=task, version=version)
    pinned = FROZEN[version]["digests"][task]
    assert bench.grouped.digest == pinned["grouped"]
    assert bench.random.digest == pinned["random"]


@pytest.mark.parametrize("version", sorted(FROZEN))
def test_frozen_corpus_statistics(version: str) -> None:
    """Row, family, coverage, and conflict counts per corpus version."""
    import csv

    if not _corpus_csv(version).exists():
        pytest.skip(f"corpus v{version} not built")
    bench = load_benchmark(task="single_vs_multi", version=version)
    pinned = FROZEN[version]
    assert len(bench) == pinned["rows"]
    assert len({*bench.families}) == pinned["families"]
    assert len(bench.subset_indices(descriptor_ready_only=True)) == pinned["element_covered"]
    with _corpus_csv(version).open(newline="", encoding="utf-8") as handle:
        conflicts = sum(1 for row in csv.DictReader(handle) if row["has_conflict"] == "1")
    assert conflicts == pinned["conflicts"]


@needs_corpus
def test_v020_grouped_split_also_keeps_families_whole() -> None:
    """The central guarantee must hold on every published corpus version."""
    from hea_bench.benchmark.splits import straddling_families

    if not _corpus_csv("0.2.0").exists():
        pytest.skip("corpus v0.2.0 not built")
    bench = load_benchmark(task="single_vs_multi", version="0.2.0")
    assert straddling_families(bench.grouped, bench.families) == {}


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
def test_most_rows_straddle_under_the_random_split() -> None:
    """Quantifies why the contrast matters on this particular corpus."""
    bench = load_benchmark(task="single_vs_multi")
    profile = bench.describe()["family_overlap_profile"]
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
