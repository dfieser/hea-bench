"""Tests for hea_bench.corpus, the standalone corpus API.

Unit tests run over a synthetic six-row corpus written to tmp_path, so
they need no built data. Integration tests against the real build skip
when it is absent, exactly like the benchmark tests.
"""

import pathlib

import pytest

from hea_bench.corpus import Corpus, CorpusRow, load_corpus

_DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "data" / "consolidated"

needs_corpus = pytest.mark.skipif(
    not (_DATA_DIR / "v0.1.0" / "consolidated.csv").exists(),
    reason=(
        "benchmark corpus not built; run data/raw/peivaste/fetch.py then "
        "python -m hea_bench.benchmark.consolidate"
    ),
)

_HEADER = (
    "composition_key,n_elements,sources,canonical_phase,has_conflict,"
    "borg_label,pei_label,borg_raw_label,pei_raw_label,"
    "borg_processing,borg_doi,source_row_ids"
)

_ROWS = [
    # Multi-source, agreeing, Borg side-channel data present.
    'Co0.5000Fe0.5000,2,borg2020;pei2020,FCC,0,FCC,FCC,FCC_A1,fcc,CAST,10.1000/abc,'
    '"borg2020:12;pei2020:7"',
    # Multi-source, conflicting: canonical blank, per-source labels kept.
    "Al0.2500Co0.2500Cr0.2500Fe0.2500,4,borg2020;pei2020,,1,BCC,multi-phase,"
    "BCC_B2,bcc+fcc,ANNEAL,10.1000/def,borg2020:44;pei2020:91",
    # Single-source refractory, labelled BCC.
    "Mo0.2500Nb0.2500Ta0.2500W0.2500,4,borg2020,BCC,0,BCC,,BCC_A2,,CAST,,borg2020:71",
    # Single-source Al-containing FCC.
    "Al0.5000Cu0.5000,2,pei2020,FCC,0,,FCC,,fcc,,,pei2020:5",
    # Boron is outside the descriptor tables: descriptor_ready False.
    "B0.5000Co0.5000,2,pei2020,multi-phase,0,,multi-phase,,im,,,pei2020:9",
    # Covered rare-earth pair, labelled HCP.
    "Dy0.5000Y0.5000,2,pei2020,HCP,0,,HCP,,hcp,,,pei2020:13",
]


@pytest.fixture()
def synthetic_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    (tmp_path / "consolidated.csv").write_text(
        "\n".join([_HEADER, *_ROWS]) + "\n", encoding="utf-8"
    )
    return tmp_path


def _load(synthetic_dir: pathlib.Path) -> Corpus:
    return load_corpus(corpus_dir=synthetic_dir)


def test_load_corpus_reads_every_row_including_unlabelled(synthetic_dir) -> None:
    corpus = _load(synthetic_dir)
    assert len(corpus) == 6
    assert all(isinstance(row, CorpusRow) for row in corpus)


def test_missing_corpus_raises_with_the_build_commands(tmp_path) -> None:
    with pytest.raises(FileNotFoundError) as caught:
        load_corpus(corpus_dir=tmp_path / "nope")
    assert "consolidate" in str(caught.value)


def test_rows_carry_full_per_source_provenance(synthetic_dir) -> None:
    row = _load(synthetic_dir).rows[0]
    assert row.composition_key == "Co0.5000Fe0.5000"
    assert row.composition == {"Co": 0.5, "Fe": 0.5}
    assert row.family == "Co-Fe"
    assert row.sources == ("borg2020", "pei2020")
    assert row.canonical_phase == "FCC"
    assert row.has_conflict is False
    assert row.labels == {"borg2020": "FCC", "pei2020": "FCC"}
    assert row.raw_labels == {"borg2020": "FCC_A1", "pei2020": "fcc"}
    assert row.processing == "CAST"
    assert row.doi == "10.1000/abc"
    assert row.source_row_ids == {"borg2020": "12", "pei2020": "7"}
    assert row.descriptor_ready is True


def test_conflict_rows_are_unlabelled_but_keep_source_labels(synthetic_dir) -> None:
    row = next(r for r in _load(synthetic_dir) if r.has_conflict)
    assert row.canonical_phase is None
    assert row.labels == {"borg2020": "BCC", "pei2020": "multi-phase"}


def test_descriptor_ready_flags_uncovered_elements(synthetic_dir) -> None:
    corpus = _load(synthetic_dir)
    boron = next(r for r in corpus if "B" in r.composition)
    assert boron.descriptor_ready is False


def test_query_elements_is_exact_set_match(synthetic_dir) -> None:
    hits = _load(synthetic_dir).query(elements=["Fe", "Co"])
    assert [r.composition_key for r in hits] == ["Co0.5000Fe0.5000"]


def test_query_contains_excludes_and_chaining(synthetic_dir) -> None:
    corpus = _load(synthetic_dir)
    assert len(corpus.query(contains=["Al"])) == 2
    assert len(corpus.query(excludes=["Al", "B"])) == 3
    chained = corpus.query(contains=["Co"]).query(descriptor_ready=True)
    assert {r.composition_key for r in chained} == {
        "Co0.5000Fe0.5000",
        "Al0.2500Co0.2500Cr0.2500Fe0.2500",
    }


def test_query_n_elements_int_and_range(synthetic_dir) -> None:
    corpus = _load(synthetic_dir)
    assert len(corpus.query(n_elements=4)) == 2
    assert len(corpus.query(n_elements=(2, 2))) == 4


def test_query_phase_source_labelled_conflict_flags(synthetic_dir) -> None:
    corpus = _load(synthetic_dir)
    assert len(corpus.query(phase="FCC")) == 2
    assert len(corpus.query(phase={"BCC", "HCP"})) == 2
    assert len(corpus.query(source="pei2020")) == 5
    assert len(corpus.query(labelled=True)) == 5
    assert len(corpus.query(has_conflict=True)) == 1
    assert len(corpus.query(family="Co-Fe")) == 1


def test_describe_reports_counts_and_agreement(synthetic_dir) -> None:
    stats = _load(synthetic_dir).describe()
    assert stats["n_rows"] == 6
    assert stats["n_labelled"] == 5
    assert stats["n_conflicts"] == 1
    assert stats["by_phase"] == {"FCC": 2, "BCC": 1, "HCP": 1, "multi-phase": 1}
    assert stats["by_source"] == {"borg2020": 3, "pei2020": 5}
    assert stats["n_families"] == 6
    assert stats["multi_source_rows"] == 2
    assert stats["multi_source_agreement_rate"] == pytest.approx(0.5)
    assert stats["n_descriptor_ready"] == 5


def test_to_records_and_csv_round_trip(synthetic_dir, tmp_path) -> None:
    corpus = _load(synthetic_dir)
    records = corpus.to_records()
    assert records[0]["composition_key"] == "Co0.5000Fe0.5000"
    assert records[0]["borg_raw_label"] == "FCC_A1"

    out_dir = tmp_path / "roundtrip"
    out_dir.mkdir()
    subset = corpus.query(labelled=True)
    assert subset.to_csv(out_dir / "consolidated.csv") == 5
    again = load_corpus(corpus_dir=out_dir)
    assert [r.composition_key for r in again] == [r.composition_key for r in subset]
    assert again.rows[0].raw_labels == subset.rows[0].raw_labels


# --- the built corpus ------------------------------------------------------


@needs_corpus
def test_real_corpus_row_and_label_counts() -> None:
    corpus = load_corpus(version="0.1.0")
    assert len(corpus) == 7783
    assert len(corpus.query(labelled=True)) == 7683
    assert len(corpus.query(has_conflict=True)) == 100


@needs_corpus
def test_real_corpus_describe_and_chaining() -> None:
    corpus = load_corpus(version="0.1.0")
    stats = corpus.describe()
    assert stats["n_rows"] == 7783
    assert stats["n_conflicts"] == 100
    assert 0.0 < stats["multi_source_agreement_rate"] < 1.0
    aluminium_bcc = corpus.query(contains=["Al"], phase="BCC", descriptor_ready=True)
    assert 0 < len(aluminium_bcc) < len(corpus)
    assert all("Al" in row.composition for row in aluminium_bcc)


@needs_corpus
def test_real_corpus_v020_loads_with_chizhevskiy_columns() -> None:
    corpus = load_corpus(version="0.2.0")
    assert len(corpus) == 10290
    chiz = corpus.query(source="chizhevskiy2026")
    assert len(chiz) > 2000
    sampled = chiz.rows[0]
    assert "chizhevskiy2026" in sampled.labels or "chizhevskiy2026" in sampled.raw_labels


def test_corpus_defaults_to_the_largest_version_and_the_benchmark_to_the_reference() -> None:
    # Owner decision 2026-10-06: browsing opens on v0.2.0, while the
    # benchmark, the predictions and the domain check stay on v0.1.0,
    # where every published number is measured.
    import inspect

    from hea_bench.benchmark import load_benchmark
    from hea_bench.corpus import DEFAULT_CORPUS_VERSION, build_corpus
    from hea_bench.webapp import dataset_query

    assert DEFAULT_CORPUS_VERSION == "0.2.0"
    assert inspect.signature(load_corpus).parameters["version"].default == "0.2.0"
    assert inspect.signature(dataset_query).parameters["version"].default == "0.2.0"
    assert inspect.signature(load_benchmark).parameters["version"].default == "0.1.0"
    with pytest.raises(ValueError, match="9.9.9"):
        build_corpus("9.9.9")
