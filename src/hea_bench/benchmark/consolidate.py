"""Consolidate the three source datasets into one canonical benchmark.

Walks each source loader, merges records on a *composition-only* join
key (Borg's processing column is preserved as side-channel data but
does **not** participate in the join), and produces:

- ``data/consolidated/<version>/consolidated.csv``  — the benchmark
- ``data/consolidated/<version>/manifest.json``     — provenance, dedup
                                                       stats, SHA-256s

Label conflict handling: when two or more sources contribute records for
the same composition but disagree on the canonical phase class, the
output row has ``canonical_phase`` blank and ``has_conflict=1``. The
per-source labels are still recorded so users can resolve the conflict
however they want.

Run as a module to (re)build v0.1.0:

    python -m hea_bench.benchmark.consolidate
"""

from __future__ import annotations

import csv
import datetime
import hashlib
import json
import pathlib
import sys
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from ..composition import Composition
from .loaders import AlloyRecord, borg2020, pei2020, peivaste
from .taxonomy import PhaseClass

DEFAULT_VERSION = "0.1.0"

# Repo-relative paths (repo root is 3 parents up from this file:
# hea-bench/src/hea_bench/benchmark/consolidate.py → hea-bench/).
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_RAW_DIR = _REPO_ROOT / "data" / "raw"
_CONSOLIDATED_DIR = _REPO_ROOT / "data" / "consolidated"


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
            # Within one source, a single (formula, processing) pair has
            # already been deduped by the per-source loader. Multiple rs
            # entries for the same source would only happen if two Borg
            # processings of the same composition exist; keep the first.
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

_CSV_COLUMNS = [
    "composition_key",
    "n_elements",
    "sources",
    "canonical_phase",
    "has_conflict",
    "borg_label",
    "pei_label",
    "peivaste_label",
    "borg_raw_label",
    "pei_raw_label",
    "peivaste_raw_label",
    "borg_processing",
    "borg_doi",
    "source_row_ids",
]


def _row_to_csv(row: ConsolidatedRow) -> list[str]:
    def lbl(src: str) -> str:
        v = row.per_source_canonical.get(src)
        return v.value if v else ""

    return [
        row.composition_key,
        str(row.n_elements),
        ";".join(row.sources),
        row.canonical_phase.value if row.canonical_phase else "",
        "1" if row.has_conflict else "0",
        lbl("borg2020"),
        lbl("pei2020"),
        lbl("peivaste"),
        row.per_source_raw_labels.get("borg2020", ""),
        row.per_source_raw_labels.get("pei2020", ""),
        row.per_source_raw_labels.get("peivaste", ""),
        row.borg_processing or "",
        row.borg_doi or "",
        ";".join(f"{s}:{rid}" for s, rid in sorted(row.source_row_ids.items())),
    ]


def write_consolidated_csv(rows: Iterable[ConsolidatedRow], path: pathlib.Path) -> int:
    """Write rows in alphabetical composition_key order. Returns row count."""
    rows = sorted(rows, key=lambda r: r.composition_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(_CSV_COLUMNS)
        for r in rows:
            w.writerow(_row_to_csv(r))
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

    overlap = {"single_source": 0, "two_sources": 0, "three_sources": 0}
    for r in rows:
        n = len(r.sources)
        if n == 1:
            overlap["single_source"] += 1
        elif n == 2:
            overlap["two_sources"] += 1
        elif n >= 3:
            overlap["three_sources"] += 1

    src_meta_table = {
        "borg2020":  {"license": "CC-BY-4.0",     "doi": "10.1038/s41597-020-00768-9"},
        "pei2020":   {"license": "CC-BY-4.0",     "doi": "10.1038/s41524-020-0308-7"},
        "peivaste":  {"license": "none-declared", "url": "https://github.com/Iman-Peivaste/ML_HEAs_Phase_Dataset"},
    }

    sources_section = []
    for name in ("borg2020", "pei2020", "peivaste"):
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


def build(version: str = DEFAULT_VERSION, out_dir: pathlib.Path | None = None) -> dict:
    """Run all three loaders, consolidate, write the v<version> release.

    Returns the manifest dict (also written to disk).
    """
    out_dir = out_dir or (_CONSOLIDATED_DIR / f"v{version}")
    out_dir.mkdir(parents=True, exist_ok=True)

    source_paths = {
        "borg2020": _RAW_DIR / "borg2020" / "MPEA_dataset.csv",
        "pei2020":  _RAW_DIR / "pei2020"  / "pei2020_alloys_phases.csv",
        "peivaste": _RAW_DIR / "peivaste" / "dataset11252_79.csv",
    }
    borg_rows     = list(borg2020.load(source_paths["borg2020"]))
    pei_rows      = list(pei2020.load(source_paths["pei2020"]))
    peivaste_rows = list(peivaste.load(source_paths["peivaste"]))
    source_counts = {"borg2020": len(borg_rows), "pei2020": len(pei_rows), "peivaste": len(peivaste_rows)}

    consolidated = consolidate([*borg_rows, *pei_rows, *peivaste_rows])
    write_consolidated_csv(consolidated, out_dir / "consolidated.csv")

    manifest = build_manifest(consolidated, source_counts, source_paths, version)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    m = build()
    print(f"=== v{m['version']} built {m['created']} ===")
    print(f"unique compositions: {m['totals']['unique_compositions']}")
    print(f"by_source_overlap:   {m['totals']['by_source_overlap']}")
    print(f"canonical:           {m['totals']['canonical_distribution']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
