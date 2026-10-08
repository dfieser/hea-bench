"""Consolidate the three source datasets into one canonical benchmark.

Walks each source loader, merges records on a *composition-only* join
key (Borg's processing column is preserved as side-channel data but
does **not** participate in the join), and produces:

- ``<corpus dir>/consolidated.csv``  — the benchmark
- ``<corpus dir>/manifest.json``     — provenance, dedup stats, SHA-256s

where the corpus dir is ``hea_bench.corpus.corpus_location(version)``:
``data/consolidated/v<version>`` in a checkout, a per-user folder in an
installed wheel.

Label conflict handling: when two or more sources contribute records for
the same composition but disagree on the canonical phase class, the
output row has ``canonical_phase`` blank and ``has_conflict=1``. The
per-source labels are still recorded so users can resolve the conflict
however they want.

Run as a module to (re)build every version from a checkout:

    python -m hea_bench.benchmark.consolidate

From an installed wheel, ``hea_bench.corpus.build_corpus()`` does the
same. Every source ships with the package, so no build downloads anything.
"""

from __future__ import annotations

import csv
import datetime
import hashlib
import json
import pathlib
import sys
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from .. import _paths
from ..composition import Composition
from .loaders import AlloyRecord, borg2020, chizhevskiy2026, pei2020, peivaste
from .taxonomy import PhaseClass

DEFAULT_VERSION = "0.1.0"

# Which sources feed which corpus version. A version's source list is a
# frozen part of its recipe: v0.1.0 must always rebuild from exactly its
# original three sources so its pinned digests stay reproducible, and a
# corpus that adds a source is a NEW version with new digests, never an
# edit to an old one.
#
# v0.2.0 adds the Chizhevskiy LLM-extracted database (CC-BY-4.0 since
# upstream merged a LICENSE on 2026-08-10). Its labels carry extraction
# noise on top of inter-study noise: on the 384 alloys where it overlaps
# the v0.1.0 consensus it agrees 69.8%, and the disagreements skew
# toward reporting a single phase where the consensus says multi-phase.
# The agreement-or-conflict consolidation rule quarantines every such
# disagreement rather than voting, at the cost of blanking rows that
# were consensus in v0.1.0.
SOURCES_BY_VERSION: dict[str, tuple[str, ...]] = {
    "0.1.0": ("borg2020", "pei2020", "peivaste"),
    "0.2.0": ("borg2020", "pei2020", "peivaste", "chizhevskiy2026"),
}



def canonical_formula_key(composition: Composition, precision: int = 4) -> str:
    """Stable string key for a normalized composition.

    Elements sorted alphabetically; fractions formatted at fixed
    precision. Two compositions differing only by float noise produce
    the same key.

    >>> canonical_formula_key({'Fe': 0.5, 'Co': 0.5})
    'Co0.5000Fe0.5000'
    >>> canonical_formula_key({'Co': 0.500000001, 'Fe': 0.499999999})
    'Co0.5000Fe0.5000'
    """
    parts = []
    for el in sorted(composition):
        frac = round(composition[el], precision)
        if frac > 0:
            parts.append(f"{el}{frac:.{precision}f}")
    return "".join(parts)


@dataclass
class ConsolidatedRow:
    composition_key: str
    composition: Composition
    n_elements: int
    sources: list[str]
    canonical_phase: PhaseClass | None
    has_conflict: bool
    per_source_canonical: dict[str, PhaseClass]
    per_source_raw_labels: dict[str, str]
    borg_processing: str | None = None
    borg_doi: str | None = None
    source_row_ids: dict[str, str] = field(default_factory=dict)


def consolidate(records: Iterable[AlloyRecord], precision: int = 4) -> list[ConsolidatedRow]:
    """Merge records from any number of sources by composition-only key."""
    by_key: dict[str, list[AlloyRecord]] = defaultdict(list)
    for r in records:
        by_key[canonical_formula_key(r.composition, precision)].append(r)

    out: list[ConsolidatedRow] = []
    for key, rs in by_key.items():
        per_source_canonical: dict[str, PhaseClass] = {}
        per_source_raw: dict[str, str] = {}
        row_ids: dict[str, str] = {}
        for r in rs:
            # The loaders drop exact repeats, but one source can still
            # list a composition more than once: several Borg processing
            # routes, or differently written Peivaste formulas. The first
            # record in file order sets that source's label. Frozen corpus
            # versions depend on this rule (docs/corpus-card.md).
            per_source_canonical.setdefault(r.source, r.canonical_phase)
            per_source_raw.setdefault(r.source, r.source_label)
            row_ids.setdefault(r.source, r.source_row_id)

        canonical_set = set(per_source_canonical.values())
        has_conflict = len(canonical_set) > 1
        canonical = next(iter(canonical_set)) if not has_conflict else None

        borg_rec = next((r for r in rs if r.source == "borg2020"), None)

        out.append(
            ConsolidatedRow(
                composition_key=key,
                composition=rs[0].composition,
                n_elements=sum(1 for v in rs[0].composition.values() if v > 0),
                sources=sorted(per_source_canonical),
                canonical_phase=canonical,
                has_conflict=has_conflict,
                per_source_canonical=per_source_canonical,
                per_source_raw_labels=per_source_raw,
                borg_processing=borg_rec.processing if borg_rec else None,
                borg_doi=borg_rec.source_doi if borg_rec else None,
                source_row_ids=row_ids,
            )
        )
    return out


# ---- Output writers -------------------------------------------------------

# Short column-name prefix per source. The CSV schema is derived from the
# version's source list, so v0.1.0 keeps its exact original 14 columns and
# a version that adds a source grows label columns for it without touching
# the older recipe's output. The table itself lives in hea_bench.corpus,
# the reader of this schema, so build and read cannot drift apart.
from ..corpus import SOURCE_COLUMN_PREFIX as _SOURCE_COLUMN_PREFIX  # noqa: E402


def _csv_columns(source_names: Sequence[str]) -> list[str]:
    prefixes = [_SOURCE_COLUMN_PREFIX[name] for name in source_names]
    return [
        "composition_key",
        "n_elements",
        "sources",
        "canonical_phase",
        "has_conflict",
        *[f"{prefix}_label" for prefix in prefixes],
        *[f"{prefix}_raw_label" for prefix in prefixes],
        "borg_processing",
        "borg_doi",
        "source_row_ids",
    ]


def _row_to_csv(row: ConsolidatedRow, source_names: Sequence[str]) -> list[str]:
    def lbl(src: str) -> str:
        v = row.per_source_canonical.get(src)
        return v.value if v else ""

    return [
        row.composition_key,
        str(row.n_elements),
        ";".join(row.sources),
        row.canonical_phase.value if row.canonical_phase else "",
        "1" if row.has_conflict else "0",
        *[lbl(name) for name in source_names],
        *[row.per_source_raw_labels.get(name, "") for name in source_names],
        row.borg_processing or "",
        row.borg_doi or "",
        ";".join(f"{s}:{rid}" for s, rid in sorted(row.source_row_ids.items())),
    ]


def write_consolidated_csv(
    rows: Iterable[ConsolidatedRow],
    path: pathlib.Path,
    source_names: Sequence[str] = SOURCES_BY_VERSION[DEFAULT_VERSION],
) -> int:
    """Write rows in alphabetical composition_key order. Returns row count."""
    rows = sorted(rows, key=lambda r: r.composition_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(_csv_columns(source_names))
        for r in rows:
            w.writerow(_row_to_csv(r, source_names))
    return len(rows)


def _sha256(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""


def build_manifest(
    rows: list[ConsolidatedRow],
    source_counts: dict[str, int],
    source_paths: dict[str, pathlib.Path],
    version: str,
) -> dict:
    canonical_dist = {p.value: 0 for p in PhaseClass}
    canonical_dist["conflict"] = 0
    for r in rows:
        if r.has_conflict:
            canonical_dist["conflict"] += 1
        elif r.canonical_phase:
            canonical_dist[r.canonical_phase.value] += 1

    overlap_names = {1: "single_source", 2: "two_sources", 3: "three_sources", 4: "four_sources"}
    overlap = {overlap_names[n]: 0 for n in range(1, len(SOURCES_BY_VERSION[version]) + 1)}
    for r in rows:
        overlap[overlap_names[len(r.sources)]] += 1

    src_meta_table = {
        "borg2020":  {"license": "CC-BY-4.0",     "doi": "10.1038/s41597-020-00768-9"},
        "pei2020":   {"license": "CC-BY-4.0",     "doi": "10.1038/s41524-020-0308-7"},
        # LICENSE added upstream 2026-10-08 via merged PR
        # github.com/Iman-Peivaste/ML_HEAs_Phase_Dataset/pull/2.
        "peivaste":  {"license": "CC-BY-4.0",     "url": "https://github.com/Iman-Peivaste/ML_HEAs_Phase_Dataset"},
        # LICENSE added upstream 2026-08-10 via merged PR
        # github.com/Vladimirchizh/hea_database/pull/2.
        "chizhevskiy2026": {"license": "CC-BY-4.0", "doi": "10.1038/s41597-026-06930-z"},
    }

    sources_section = []
    for name in SOURCES_BY_VERSION[version]:
        meta = src_meta_table[name]
        sources_section.append(
            {
                "name": name,
                **meta,
                "rows_yielded": source_counts.get(name, 0),
                "sha256": _sha256(source_paths.get(name, pathlib.Path())),
            }
        )

    return {
        "version": version,
        "created": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "schema": {
            "composition_key": (
                "Stable hash of normalized composition: alphabetically sorted "
                "elements at 4-decimal mole-fraction precision."
            ),
            "canonical_phase": (
                "One of BCC, FCC, HCP, multi-phase. Empty when sources disagree."
            ),
            "has_conflict": (
                "1 if any pair of contributing sources gave different canonical labels."
            ),
            "borg_processing": "Preserved side-channel from Borg only. Not part of join key.",
        },
        "sources": sources_section,
        "totals": {
            "unique_compositions": len(rows),
            "by_source_overlap": overlap,
            "canonical_distribution": canonical_dist,
        },
        "consolidation_rules": {
            "join_key": "composition_only, 4-decimal mole-fraction precision",
            "label_policy": "agreement → canonical; disagreement → has_conflict=1, canonical_phase blank",
            "borg_processing": "Preserved as side-channel; not part of join key",
            "per_source_dedup": "Each loader deduplicates internally before consolidation",
        },
    }


# Source files, from hea_bench._paths: data/raw in a checkout, inside the
# package in a wheel.
_SOURCE_PATHS = {
    "borg2020": _paths.raw_dir() / "borg2020" / "MPEA_dataset.csv",
    "pei2020": _paths.raw_dir() / "pei2020" / "pei2020_alloys_phases.csv",
    "peivaste": _paths.raw_dir() / "peivaste" / "dataset11252_79.csv",
    "chizhevskiy2026": _paths.raw_dir() / "chizhevskiy2026" / "database_of_HEAs.csv",
}

_LOADERS = {
    "borg2020": borg2020.load,
    "pei2020": pei2020.load,
    "peivaste": peivaste.load,
    "chizhevskiy2026": chizhevskiy2026.load,
}


def build(version: str = DEFAULT_VERSION, out_dir: pathlib.Path | None = None) -> dict:
    """Run the version's loaders, consolidate, write the v<version> release.

    Returns the manifest dict (also written to disk).
    """
    from ..corpus import corpus_location

    source_names = SOURCES_BY_VERSION[version]
    out_dir = out_dir or corpus_location(version)

    source_paths = {name: _SOURCE_PATHS[name] for name in source_names}
    missing = [name for name in source_names if not source_paths[name].exists()]
    if missing:
        instructions = [
            f"  {name}: expected {source_paths[name]}\n    fix: reinstall hea-bench, or "
            f"restore the file from the repository (see data/raw/{name}/README.md)"
            for name in missing
        ]
        raise FileNotFoundError(
            f"cannot build corpus v{version}: source data missing.\n"
            + "\n".join(instructions)
            + "\nA partial corpus is never built: every source in the version's "
            "recipe is required, because a corpus missing a source would carry "
            "the wrong rows under the right filename."
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    rows_by_source = {
        name: list(_LOADERS[name](source_paths[name])) for name in source_names
    }
    source_counts = {name: len(rows) for name, rows in rows_by_source.items()}

    consolidated = consolidate(
        [record for name in source_names for record in rows_by_source[name]]
    )
    write_consolidated_csv(consolidated, out_dir / "consolidated.csv", source_names)

    manifest = build_manifest(consolidated, source_counts, source_paths, version)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for version in SOURCES_BY_VERSION:
        m = build(version)
        print(f"=== v{m['version']} built {m['created']} ===")
        print(f"unique compositions: {m['totals']['unique_compositions']}")
        print(f"by_source_overlap:   {m['totals']['by_source_overlap']}")
        print(f"canonical:           {m['totals']['canonical_distribution']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
