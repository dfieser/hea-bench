"""The consolidated corpus and the Borg measurements, as the surfaces serve them.

Two filter shapes reach this module. The app sends one ``filters`` dict
(:func:`filtered`, read through a cache), and the MCP tools send named
arguments (:func:`tool_slice`, read fresh). Both return a
:class:`hea_bench.corpus.Corpus` slice, and :func:`row_payload` is the
one row shape both surfaces return.
"""

from __future__ import annotations

import csv
import io
from functools import lru_cache

from . import benchmark
from ._payload import CORPUS_SAMPLE_CAP, PAGE_CAP, needs_corpus, say


def status() -> dict:
    """Which corpus versions are built where the loaders read."""
    from ..benchmark.consolidate import SOURCES_BY_VERSION
    from ..corpus import corpus_location

    return {
        "built": {
            version: (corpus_location(version) / "consolidated.csv").exists()
            for version in SOURCES_BY_VERSION
        }
    }


def build(version: str = "0.2.0", progress=None) -> dict:
    """Build one corpus version into the directory the loaders read."""
    from ..benchmark.consolidate import build as build_version
    from ..corpus import corpus_location

    say(progress, f"building corpus v{version}", 0.1)
    manifest = build_version(version, out_dir=corpus_location(version))
    clear_caches()
    say(progress, "done", 1.0)
    return manifest


def build_all(versions: list[str] | None = None) -> dict:
    """Build the given corpus versions, every one by default."""
    from ..corpus import build_corpus

    try:
        built = build_corpus(*(versions or ()))
    except OSError as exc:
        raise ValueError(str(exc)) from None
    clear_caches()
    return {
        "built": {
            version: {"location": manifest["location"], "totals": manifest["totals"]}
            for version, manifest in built.items()
        }
    }


def clear_caches() -> None:
    """Forget everything read or fitted from a corpus, after a build replaced it."""
    from ..uncertainty import applicability, phase

    cached_corpus.cache_clear()
    benchmark.load.cache_clear()
    benchmark.finite_indices.cache_clear()
    phase.clear_caches()
    applicability.default_domain.cache_clear()


@lru_cache(maxsize=2)
def cached_corpus(version: str):
    from ..corpus import load_corpus

    return load_corpus(version=version)


def filtered(version: str, filters: dict | None):
    """The app's slice: one filters dict, empty values ignored."""
    filters = dict(filters or {})
    n_min = filters.pop("n_elements_min", None)
    n_max = filters.pop("n_elements_max", None)
    if n_min is not None or n_max is not None:
        filters["n_elements"] = (n_min or 1, n_max or 99)
    allowed = {
        "elements", "contains", "excludes", "n_elements", "phase", "source",
        "family", "labelled", "has_conflict", "descriptor_ready",
    }
    unknown = sorted(set(filters) - allowed)
    if unknown:
        raise ValueError(f"unknown dataset filters {unknown}: expected {sorted(allowed)}")
    return cached_corpus(version).query(**{k: v for k, v in filters.items() if v not in (None, [], "")})


def tool_slice(
    version: str,
    elements: list[str] | None,
    contains: list[str] | None,
    excludes: list[str] | None,
    n_elements_min: int | None,
    n_elements_max: int | None,
    phase: str | None,
    source: str | None,
    labelled: bool | None,
    has_conflict: bool | None,
    descriptor_ready: bool | None,
):
    """The MCP tools' slice: named filters, an unbuilt corpus as a ValueError."""
    from ..corpus import load_corpus

    try:
        corpus = load_corpus(version=version)
    except FileNotFoundError as exc:
        raise needs_corpus(exc) from None
    n_range = None
    if n_elements_min is not None or n_elements_max is not None:
        n_range = (n_elements_min or 1, n_elements_max or 99)
    return corpus.query(
        elements=elements,
        contains=contains,
        excludes=excludes,
        n_elements=n_range,
        phase=phase,
        source=source,
        labelled=labelled,
        has_conflict=has_conflict,
        descriptor_ready=descriptor_ready,
    )


def row_payload(row) -> dict:
    return {
        "composition_key": row.composition_key,
        "composition": dict(row.composition),
        "n_elements": row.n_elements,
        "family": row.family,
        "canonical_phase": row.canonical_phase,
        "has_conflict": row.has_conflict,
        "sources": list(row.sources),
        "labels": dict(row.labels),
        "raw_labels": dict(row.raw_labels),
        "processing": row.processing,
        "doi": row.doi,
        "source_row_ids": dict(row.source_row_ids),
        "descriptor_ready": row.descriptor_ready,
    }


def sample(subset, limit: int) -> dict:
    """The match count and the first rows of a slice, capped for an agent."""
    capped = min(max(0, limit), CORPUS_SAMPLE_CAP)
    rows = [row_payload(row) for row in subset.rows[:capped]]
    return {
        "corpus_version": subset.version,
        "n_matching": len(subset),
        "sample": rows,
        "sample_capped_at": CORPUS_SAMPLE_CAP,
    }


def page(
    filters: dict | None = None, version: str = "0.2.0", offset: int = 0, limit: int = 100
) -> dict:
    """One page of a filtered corpus slice, every row with full provenance."""
    subset = filtered(version, filters)
    limit = max(0, min(int(limit), PAGE_CAP))
    offset = max(0, int(offset))
    return {
        "corpus_version": version,
        "n_matching": len(subset),
        "offset": offset,
        "rows": [row_payload(row) for row in subset.rows[offset : offset + limit]],
    }


def describe(filters: dict | None = None, version: str = "0.2.0") -> dict:
    """Counts by phase, element count, source and family for a slice."""
    return filtered(version, filters).describe()


def csv_text(filters: dict | None = None, version: str = "0.2.0") -> dict:
    """The slice in the consolidated-CSV schema, as text for a download."""
    subset = filtered(version, filters)
    handle = io.StringIO(newline="")
    writer = csv.writer(handle)
    writer.writerow(subset.columns)
    for record in subset.records:
        writer.writerow([record.get(column, "") for column in subset.columns])
    return {
        "filename": f"hea-bench-corpus-v{version}.csv",
        "n_rows": len(subset),
        "text": handle.getvalue(),
    }


# -- measured properties (Borg 2020) -------------------------------------------


def measured(prop: str = "hardness", contains: list | None = None) -> dict:
    """The Borg 2020 measurements the hardness model trains on, or the
    measured densities the rule-of-mixtures estimate is checked against,
    optionally only alloys that contain every element in ``contains``."""
    from ..properties.borg import experimental_density_records, hardness_records

    loaders = {
        "hardness": (hardness_records, "HV"),
        "density": (experimental_density_records, "g/cm^3"),
    }
    if prop not in loaders:
        raise ValueError(f"unknown property {prop!r}: use 'hardness' or 'density'")
    load, unit = loaders[prop]
    records = load()
    wanted = {str(symbol) for symbol in (contains or [])}
    rows = [
        {
            "composition": dict(record.composition),
            "formula_raw": record.formula_raw,
            "value": record.value,
            "processing": record.processing,
            "doi": record.doi,
            "reference_id": record.reference_id,
            "year": record.year,
        }
        for record in records
        if wanted <= set(record.composition)
    ]
    return {
        "property": prop,
        "unit": unit,
        "n_total": len(records),
        "n_matching": len(rows),
        "rows": rows[:PAGE_CAP],
        "source": "Borg et al. (2020), Sci. Data 7, 430, doi:10.1038/s41597-020-00768-9, CC BY 4.0",
    }


def measured_sample(prop: str = "hardness", contains: list | None = None, limit: int = 25) -> dict:
    """:func:`measured`, its rows capped for an agent."""
    payload = measured(prop, contains)
    payload["rows"] = payload["rows"][: min(max(0, limit), CORPUS_SAMPLE_CAP)]
    payload["sample_capped_at"] = CORPUS_SAMPLE_CAP
    return payload
