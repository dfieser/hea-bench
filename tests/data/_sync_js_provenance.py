"""Regenerate the provenance tables embedded in ``web/index.html``.

The Python provenance registry (``descriptors/data/provenance.py``) is
the source of truth for the web app's Data view and provenance drawer:
per-element source notes, cross-check values, the keyed bibliography
(with generated BibTeX), and the SHA-256 pins of the data files.

Run from the repo root::

    PYTHONPATH=src python tests/data/_sync_js_provenance.py

Idempotent: same inputs produce byte-identical output.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re

from hea_bench.descriptors.data.provenance import (
    ELEMENT_SOURCES,
    PROPERTY_SOURCES,
    REFERENCES,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
INDEX = ROOT / "web" / "index.html"
DATA_DIR = ROOT / "src" / "hea_bench" / "descriptors" / "data"

_DATA_FILES = (
    "elemental.py",
    "pair_enthalpies.tsv",
    "miedema_parameters.csv",
    "provenance.py",
)


def _bibtex_authors(authors: str) -> str:
    """Turn the display author string into a valid BibTeX author list.

    Display form: "Family, I. I., Family, I. & Family, I." (with "et al."
    and ", Jr." suffixes). BibTeX needs " and " between authors.
    """
    a = authors
    a = a.replace(" et al.", " and others")
    a = a.replace(" & ", " and ")
    # Attach generational suffixes to the name so the splitter below
    # does not mistake them for a new author.
    a = a.replace(", Jr.", " Jr.")
    # An initial's dot followed by ", Name" separates two authors.
    a = re.sub(r"\.\s*,\s+(?=[A-Za-z])", ". and ", a)
    return a


_VENUE_RE = re.compile(r"^(?P<journal>.+?)\s+(?P<volume>\d+),\s*(?P<pages>\S.*)$")


def _bibtex(key: str, ref) -> str:
    """Deterministic BibTeX for one Ref.

    A hand-written ``ref.bibtex`` wins. Otherwise: a real @article with
    journal/volume/pages fields when the venue parses as
    "Journal VOLUME, PAGES" and a DOI exists; @misc with howpublished
    for books, reports, and datasets.
    """
    if ref.bibtex:
        return ref.bibtex
    venue = _VENUE_RE.match(ref.venue)
    kind = "article" if (ref.doi and venue) else "misc"
    lines = [f"@{kind}{{{key},"]
    lines.append(f"  author = {{{_bibtex_authors(ref.authors)}}},")
    lines.append(f"  title = {{{ref.title}}},")
    if kind == "article":
        lines.append(f"  journal = {{{venue.group('journal')}}},")
        lines.append(f"  volume = {{{venue.group('volume')}}},")
        lines.append(f"  pages = {{{venue.group('pages')}}},")
    else:
        lines.append(f"  howpublished = {{{ref.venue}}},")
    lines.append(f"  year = {{{ref.year}}},")
    if ref.doi:
        lines.append(f"  doi = {{{ref.doi}}},")
    if ref.url:
        lines.append(f"  url = {{{ref.url}}},")
    lines.append("}")
    return "\n".join(lines)


def references_js() -> dict:
    out = {}
    for key, ref in sorted(REFERENCES.items()):
        out[key] = {
            "authors": ref.authors,
            "title": ref.title,
            "venue": ref.venue,
            "year": ref.year,
            "doi": ref.doi,
            "url": ref.url or (f"https://doi.org/{ref.doi}" if ref.doi else ""),
            "bibtex": _bibtex(key, ref),
        }
    return out


def element_sources_js() -> dict:
    out = {}
    for sym, src in sorted(ELEMENT_SOURCES.items()):
        out[sym] = {
            "radiusSource": src.radius_source_key,
            "crosscheckRadiusPm": src.crosscheck_radius_pm,
            "crosscheckSource": src.crosscheck_source_key,
            "crosscheckNote": src.crosscheck_note,
            "notes": src.notes,
            "flags": list(src.flags),
        }
    return out


def property_sources_js() -> dict:
    return {
        col: {"statement": ps.statement, "sourceKeys": list(ps.source_keys)}
        for col, ps in PROPERTY_SOURCES.items()
    }


def data_file_shas() -> dict:
    out = {}
    for name in _DATA_FILES:
        digest = hashlib.sha256((DATA_DIR / name).read_bytes()).hexdigest()
        out[name] = digest
    return out


def main() -> None:
    shas = data_file_shas()
    combined = hashlib.sha256("".join(shas[n] for n in _DATA_FILES).encode()).hexdigest()[:8]

    def js_const(name: str, value) -> str:
        return f"      const {name} = " + json.dumps(value, indent=2, ensure_ascii=False).replace("\n", "\n      ") + ";\n"

    block = (
        "      // BEGIN GENERATED: PROVENANCE_TABLES\n"
        "      // Generated from src/hea_bench/descriptors/data/provenance.py by\n"
        "      // tests/data/_sync_js_provenance.py. Do not edit by hand.\n"
        + js_const("REFERENCES_JS", references_js())
        + js_const("ELEMENT_SOURCES_JS", element_sources_js())
        + js_const("PROPERTY_SOURCES_JS", property_sources_js())
        + js_const("DATA_FILE_SHAS", shas)
        + f'      const DATA_TABLES_SHORT_SHA = "{combined}";\n'
        "      // END GENERATED: PROVENANCE_TABLES"
    )

    text = INDEX.read_text(encoding="utf-8")
    text, n = re.subn(
        r"(?s)      // BEGIN GENERATED: PROVENANCE_TABLES\n.*?      // END GENERATED: PROVENANCE_TABLES",
        block.replace("\\", "\\\\"),
        text,
        count=1,
    )
    if n != 1:
        raise SystemExit("PROVENANCE_TABLES block not found")
    INDEX.write_text(text, encoding="utf-8", newline="\n")
    print(
        f"synced provenance tables: {len(REFERENCES)} references, "
        f"{len(ELEMENT_SOURCES)} element source rows, dataset sha {combined}"
    )


if __name__ == "__main__":
    main()
