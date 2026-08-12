"""The consolidated experimental corpus as a standalone, queryable product.

:func:`load_corpus` reads a built corpus release (every row, including
the conflict-quarantined and otherwise unlabelled ones) into a
:class:`Corpus` of :class:`CorpusRow` records carrying the full
per-source provenance the build already writes: which sources
contributed, each source's canonical and verbatim reported phase label,
Borg's processing route and primary-literature DOI where present, and
the upstream row identifiers. That is enough to audit any label without
leaving the package.

This module is deliberately independent of the benchmark machinery: no
task projection, no splits. :func:`hea_bench.benchmark.load_benchmark`
is a thin wrapper that filters to consensus-labelled rows, projects a
task, and attaches the frozen splits; its outputs and digests are
unchanged by this module's existence.

The corpus itself is built locally rather than shipped, because its
largest source dataset declares no license and a derived corpus
inherits the restrictions of everything it is built from. Build it
once from a repository checkout::

    python data/raw/peivaste/fetch.py
    python -m hea_bench.benchmark.consolidate

``HEA_BENCH_BENCHMARK_DIR`` points loads at a corpus directory
elsewhere, exactly as it does for ``load_benchmark``.
"""

from __future__ import annotations

import csv
import json
import os
import pathlib
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field, replace

from ..composition import Composition, family_of, parse_formula

DEFAULT_CORPUS_VERSION = "0.1.0"

#: Source name -> short CSV column prefix. The consolidated CSV schema
#: derives its per-source label columns from this table (the build in
#: hea_bench.benchmark.consolidate imports it from here).
SOURCE_COLUMN_PREFIX = {
    "borg2020": "borg",
    "pei2020": "pei",
    "peivaste": "peivaste",
    "chizhevskiy2026": "chizhevskiy",
}

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_ENV_VAR = "HEA_BENCH_BENCHMARK_DIR"


def corpus_location(version: str, corpus_dir: pathlib.Path | None = None) -> pathlib.Path:
    """Resolve the directory a corpus version is read from.

    Explicit ``corpus_dir`` wins, then the ``HEA_BENCH_BENCHMARK_DIR``
    environment variable (with ``v<version>`` appended), then the
    repository-relative default ``data/consolidated/v<version>``.
    """
    if corpus_dir is not None:
        return pathlib.Path(corpus_dir)
    override = os.environ.get(_ENV_VAR)
    if override:
        return pathlib.Path(override) / f"v{version}"
    return _REPO_ROOT / "data" / "consolidated" / f"v{version}"


def missing_corpus_error(path: pathlib.Path) -> FileNotFoundError:
    """The corpus is not shipped; the error must say how to build it."""
    return FileNotFoundError(
        f"benchmark corpus not found at {path}.\n"
        f"The corpus is built locally rather than shipped, because its largest "
        f"source dataset is not licensed for redistribution. Build it with:\n"
        f"    python data/raw/peivaste/fetch.py\n"
        f"    python -m hea_bench.benchmark.consolidate\n"
        f"Set {_ENV_VAR} to point at a corpus directory elsewhere."
    )


@dataclass(frozen=True)
class CorpusRow:
    """One corpus composition with its labels and provenance.

    Attributes
    ----------
    composition_key
        The corpus join key: elements sorted alphabetically at 4-decimal
        mole-fraction precision. Unique within the corpus.
    composition
        Normalized mole-fraction dict, the form every descriptor takes.
    n_elements
        Number of elements present.
    family
        Alloy-family key (the element set, sorted and hyphen-joined).
    sources
        Upstream datasets that contributed this composition.
    canonical_phase
        The consensus 4-class label, or None when the sources disagree
        (``has_conflict``) and the corpus refuses to vote.
    has_conflict
        True when contributing sources gave different canonical labels.
    labels
        Per-source canonical label, for auditing consensus and conflict.
    raw_labels
        Per-source reported phase string, verbatim from upstream, before
        any harmonization. The audit trail for every label decision.
    processing
        Processing route where the upstream source records it (Borg
        only); None elsewhere. Not part of the join key.
    doi
        DOI of the primary-literature paper the alloy was reported in,
        where the upstream source records it (Borg only).
    source_row_ids
        Per-source upstream record identifier, pointing back into the
        raw datasets.
    descriptor_ready
        True when every element is covered by both the element table and
        the Miedema pair table, so this package's descriptors are all
        computable for the row.
    """

    composition_key: str
    composition: Composition
    n_elements: int
    family: str
    sources: tuple[str, ...]
    canonical_phase: str | None
    has_conflict: bool
    labels: dict[str, str]
    raw_labels: dict[str, str]
    processing: str | None
    doi: str | None
    source_row_ids: dict[str, str]
    descriptor_ready: bool


def _as_set(value) -> set[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        return {value}
    return {str(item) for item in value}


@dataclass(frozen=True)
class Corpus:
    """An immutable set of corpus rows with chainable filters.

    Every filter returns a new :class:`Corpus` sharing the row objects,
    so queries compose without copying data. ``records`` retains the raw
    CSV cells for lossless :meth:`to_csv` round-trips of any subset.
    """

    rows: tuple[CorpusRow, ...]
    version: str
    manifest: dict = field(repr=False)
    records: tuple[dict, ...] = field(repr=False)
    columns: tuple[str, ...] = field(repr=False)

    def __len__(self) -> int:
        return len(self.rows)

    def __iter__(self) -> Iterator[CorpusRow]:
        return iter(self.rows)

    def query(
        self,
        *,
        elements: Iterable[str] | None = None,
        contains: Iterable[str] | None = None,
        excludes: Iterable[str] | None = None,
        n_elements: int | tuple[int, int] | None = None,
        phase: str | Iterable[str] | None = None,
        source: str | Iterable[str] | None = None,
        family: str | Iterable[str] | None = None,
        labelled: bool | None = None,
        has_conflict: bool | None = None,
        descriptor_ready: bool | None = None,
    ) -> "Corpus":
        """Filter rows; every given condition must hold (they AND together).

        Parameters
        ----------
        elements
            Exact element-set match: the row contains these elements and
            no others (amounts ignored, like families).
        contains
            All listed elements are present.
        excludes
            None of the listed elements are present.
        n_elements
            Exact count, or an inclusive ``(minimum, maximum)`` range.
        phase
            Canonical consensus label equals this value (or is in this
            set). Conflict rows have no canonical label and never match.
        source
            At least one of these sources contributed the row.
        family
            Alloy-family key match (str or set).
        labelled
            True keeps only rows with a consensus label; False only rows
            without one.
        has_conflict / descriptor_ready
            Match the corresponding flag.
        """
        wanted_elements = frozenset(_as_set(elements)) if elements is not None else None
        contains_set = _as_set(contains)
        excludes_set = _as_set(excludes)
        phase_set = _as_set(phase)
        source_set = _as_set(source)
        family_set = _as_set(family)
        if isinstance(n_elements, int):
            n_range = (n_elements, n_elements)
        else:
            n_range = n_elements

        def keep(row: CorpusRow) -> bool:
            present = set(row.composition)
            if wanted_elements is not None and present != wanted_elements:
                return False
            if contains_set is not None and not contains_set <= present:
                return False
            if excludes_set is not None and excludes_set & present:
                return False
            if n_range is not None and not n_range[0] <= row.n_elements <= n_range[1]:
                return False
            if phase_set is not None and row.canonical_phase not in phase_set:
                return False
            if source_set is not None and not source_set & set(row.sources):
                return False
            if family_set is not None and row.family not in family_set:
                return False
            if labelled is not None and (row.canonical_phase is not None) != labelled:
                return False
            if has_conflict is not None and row.has_conflict != has_conflict:
                return False
            if descriptor_ready is not None and row.descriptor_ready != descriptor_ready:
                return False
            return True

        kept = [index for index, row in enumerate(self.rows) if keep(row)]
        return replace(
            self,
            rows=tuple(self.rows[index] for index in kept),
            records=tuple(self.records[index] for index in kept),
        )

    def describe(self) -> dict:
        """Composition of this (possibly filtered) corpus slice.

        ``multi_source_agreement_rate`` is the fraction of rows carrying
        two or more sources whose sources agree on the canonical label;
        its complement is exactly the conflict quarantine.
        """
        multi_source = [row for row in self.rows if len(row.sources) >= 2]
        conflicts = sum(1 for row in self.rows if row.has_conflict)
        by_source: Counter = Counter()
        for row in self.rows:
            by_source.update(row.sources)
        by_element: Counter = Counter()
        for row in self.rows:
            by_element.update(row.composition)
        families = Counter(row.family for row in self.rows)
        return {
            "corpus_version": self.version,
            "n_rows": len(self.rows),
            "n_labelled": sum(1 for row in self.rows if row.canonical_phase is not None),
            "n_conflicts": conflicts,
            "n_descriptor_ready": sum(1 for row in self.rows if row.descriptor_ready),
            "by_phase": dict(
                Counter(
                    row.canonical_phase for row in self.rows if row.canonical_phase is not None
                )
            ),
            "by_n_elements": dict(Counter(row.n_elements for row in self.rows)),
            "by_source": dict(by_source),
            "n_families": len(families),
            "top_families": families.most_common(10),
            "n_distinct_elements": len(by_element),
            "top_elements": by_element.most_common(10),
            "multi_source_rows": len(multi_source),
            "multi_source_agreement_rate": (
                1.0 - conflicts / len(multi_source) if multi_source else None
            ),
        }

    def to_records(self) -> list[dict]:
        """The raw CSV cells of this slice, one dict per row."""
        return [dict(record) for record in self.records]

    def to_csv(self, path: pathlib.Path | str) -> int:
        """Write this slice in the consolidated-CSV schema. Returns row count."""
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(self.columns)
            for record in self.records:
                writer.writerow([record.get(column, "") for column in self.columns])
        return len(self.records)


def _row_from_record(
    record: dict, prefix_to_source: dict[str, str], scorable: frozenset[str]
) -> CorpusRow:
    key = record["composition_key"]
    try:
        composition = parse_formula(key)
    except ValueError as error:
        raise ValueError(
            f"corpus row has an unparseable composition_key {key!r}: {error}"
        ) from error

    labels: dict[str, str] = {}
    raw_labels: dict[str, str] = {}
    for prefix, source in prefix_to_source.items():
        label = (record.get(f"{prefix}_label") or "").strip()
        if label:
            labels[source] = label
        raw = (record.get(f"{prefix}_raw_label") or "").strip()
        if raw:
            raw_labels[source] = raw

    row_ids: dict[str, str] = {}
    for chunk in (record.get("source_row_ids") or "").split(";"):
        if ":" in chunk:
            source, identifier = chunk.split(":", 1)
            row_ids[source] = identifier

    canonical = (record.get("canonical_phase") or "").strip() or None
    return CorpusRow(
        composition_key=key,
        composition=composition,
        n_elements=int(record["n_elements"]),
        family=family_of(composition),
        sources=tuple((record.get("sources") or "").split(";")) if record.get("sources") else (),
        canonical_phase=canonical,
        has_conflict=(record.get("has_conflict") or "0").strip() == "1",
        labels=labels,
        raw_labels=raw_labels,
        processing=(record.get("borg_processing") or "").strip() or None,
        doi=(record.get("borg_doi") or "").strip() or None,
        source_row_ids=row_ids,
        descriptor_ready=set(composition).issubset(scorable),
    )


def load_corpus(
    version: str = DEFAULT_CORPUS_VERSION,
    *,
    corpus_dir: pathlib.Path | None = None,
) -> Corpus:
    """Load a built corpus release, every row, no task machinery.

    Parameters
    ----------
    version
        Corpus version directory to read. ``"0.1.0"`` (default) is the
        reference corpus every published number is measured on;
        ``"0.2.0"`` adds the Chizhevskiy LLM-extracted database and is
        opt-in because its labels are measurably noisier (about 70
        percent agreement with the reference consensus on overlaps,
        every disagreement quarantined as a conflict).
    corpus_dir
        Directory holding ``consolidated.csv``, overriding both the
        environment variable and the repository-relative default.

    Raises
    ------
    FileNotFoundError
        If the corpus has not been built; the message gives the build
        commands.
    """
    directory = corpus_location(version, corpus_dir)
    csv_path = directory / "consolidated.csv"
    if not csv_path.exists():
        raise missing_corpus_error(csv_path)

    manifest_path = directory / "manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    )

    from ..descriptors.data.elemental import covered_elements as _elemental_covered
    from ..descriptors.data.pair_enthalpies import covered_elements as _pair_covered

    scorable = frozenset(_elemental_covered() & _pair_covered())

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = tuple(reader.fieldnames or ())
        records = tuple({key: value for key, value in record.items()} for record in reader)

    prefix_to_source = {
        prefix: source
        for source, prefix in SOURCE_COLUMN_PREFIX.items()
        if f"{prefix}_label" in columns
    }

    rows = tuple(_row_from_record(record, prefix_to_source, scorable) for record in records)
    return Corpus(rows=rows, version=version, manifest=manifest, records=records, columns=columns)


__all__ = [
    "DEFAULT_CORPUS_VERSION",
    "SOURCE_COLUMN_PREFIX",
    "Corpus",
    "CorpusRow",
    "corpus_location",
    "load_corpus",
    "missing_corpus_error",
]
