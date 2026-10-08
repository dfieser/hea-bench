"""Generate docs/corpus-card.md, the dataset card for the consolidated corpus.

The card is the one document a user reads before trusting a label:
where every row came from, under what license, what harmonization did
to it, and what the corpus cannot support. Statistics are computed from
the built corpus releases; provenance and license text is maintained
here and must stay consistent with data/raw/README.md.

Run from the repository root with both corpus versions built:

    PYTHONPATH=src python tools/corpus_card.py
"""

from __future__ import annotations

import datetime
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from hea_bench import __version__ as _hea_bench_version  # noqa: E402
from hea_bench.corpus import load_corpus  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_MD = REPO_ROOT / "docs" / "corpus-card.md"

# Provenance chain per source: citation, deposit, license status, how
# the repo obtains it, and the decisions a user should know about.
# Facts mirror data/raw/README.md (licenses re-verified 2026-08-10).
SOURCE_SECTIONS = {
    "borg2020": (
        "**Borg et al. 2020** (Sci. Data 7, 430, doi:10.1038/s41597-020-00768-9). "
        "Deposit: figshare 10.6084/m9.figshare.12642953 v9, explicitly licensed "
        "**CC-BY-4.0**, mirrored verbatim in `data/raw/borg2020/` since 2026-05-20. "
        "1,545 measurement rows covering 740 unique (formula, processing) alloys "
        "with phase, processing route, mechanical properties, and a per-row "
        "primary-literature DOI. The canonical backbone of the corpus; it is the "
        "only source contributing the processing and DOI side channels."
    ),
    "pei2020": (
        "**Pei et al. 2020** (npj Comput. Mater. 6, 50, doi:10.1038/s41524-020-0308-7). "
        "License **CC-BY-4.0** (Crossref-confirmed for text and data mining and "
        "the version of record). Mirrored in `data/raw/pei2020/` since 2026-05-20. "
        "1,252 rows of (alloy, phase) pairs with four phase labels; 1,208 unique "
        "formulas load after deduplication and one malformed-entry rejection."
    ),
    "peivaste": (
        "**Peivaste et al.** (GitHub Iman-Peivaste/ML_HEAs_Phase_Dataset, companion "
        "article Sci. Rep. 13, 22556 (2023), doi:10.1038/s41598-023-50044-0). "
        "License **CC-BY-4.0**, added by the authors on 2026-10-08 (merged pull "
        "request #2). Mirrored in `data/raw/peivaste/` since that day, byte-identical "
        "to the snapshot acquired 2026-05-20, which the license merge left unchanged; "
        "the loader refuses any other bytes (pinned SHA-256). The largest contributor "
        "to the corpus."
    ),
    "chizhevskiy2026": (
        "**Chizhevskiy et al. 2026** (Sci. Data 13, 612, "
        "doi:10.1038/s41597-026-06930-z; repo Vladimirchizh/hea_database). "
        "**CC-BY-4.0** since 2026-08-10, when upstream merged a LICENSE file; "
        "mirrored at the pinned SHA-256 the same day. 12,427 LLM-extracted records "
        "yielding 2,974 unique alloys in plain formulas. Rows in group notation, "
        "such as (CrCoNi)97W1Mo2, stay out because v0.2.0 is frozen. Feeds corpus "
        "v0.2.0 only. Its "
        "labels agree with the v0.1.0 consensus on about 70 percent of overlapping "
        "alloys; every disagreement is quarantined as a conflict rather than voted "
        "on, and the named-intermetallic raw labels (B2, L12, Laves, sigma) are "
        "preserved verbatim in the raw-label column."
    ),
}

HARMONIZATION = """\
## Harmonization rules

- **Join key**: composition only, elements alphabetical at 4-decimal
  mole-fraction precision (`canonical_formula_key`). Two upstream rows
  differing only by float noise merge; two processing states of the same
  composition also merge, with Borg's processing string preserved as a
  side channel rather than in the key.
- **Label policy**: sources agree, the label becomes `canonical_phase`;
  sources disagree, the row gets `has_conflict=1` and an empty canonical
  label. Nothing votes. Conflict rows stay in the CSV for anyone who
  wants to study the disagreement itself and are excluded from the
  benchmark projection.
- **Per-source dedup**: each loader drops exact repeats before
  consolidation and keeps the first row (Borg on formula and processing
  together, Pei and Peivaste on the formula string). A source can still
  list one composition more than once, under several Borg processing
  routes or under differently written Peivaste formulas. Its first
  record in file order then sets that source's label, and the label
  policy above compares sources on that label.
- **Raw labels**: every source's reported phase string is preserved
  verbatim in `<source>_raw_label`, so any harmonized label can be
  audited against what the upstream actually said without leaving the
  package (`hea_bench.corpus.CorpusRow.raw_labels`).
"""

LIMITATIONS = """\
## Known limitations

- **Composition does not fix phase.** The join key deliberately ignores
  processing, so an as-cast and an annealed report of one composition
  merge, and the first of them in Borg's file sets Borg's label. Users
  studying processing effects should start from the raw Borg data,
  which keeps the states separate.
- **A source's repeated records are not checked against each other.**
  When repeated records of one composition in one source disagree, the
  first record decides, where a disagreement between sources would
  quarantine the row. This decides the label of 59 consensus-labelled
  rows in v0.1.0 and 49 in v0.2.0. Both versions are frozen, so they
  keep the rule and their digests.
- **The conflict quarantine removes contested chemistry.** Excluded
  conflict rows are not random: heavily studied systems are more likely
  to accumulate disagreeing reports.
- **The corpus inherits literature bias.** Element and family counts
  reflect what experimentalists chose to make, not a design of
  experiments; 3d transition-metal systems dominate.
- **Chizhevskiy rows are LLM-extracted** and measurably noisier than the
  hand-curated sources (about 70 percent agreement on overlaps). They
  are confined to v0.2.0, and disagreements with the reference corpus
  are quarantined, not resolved.
- **`descriptor_ready` marks scorability, not quality.** Rows with
  elements outside the descriptor tables are kept; the flag only says
  whether this package's descriptor stack can score them.
"""


def _version_section(version: str) -> list[str]:
    corpus = load_corpus(version=version)
    stats = corpus.describe()
    manifest = corpus.manifest
    lines = [
        f"### Corpus v{version}",
        "",
        f"- Rows (unique compositions): {stats['n_rows']}",
        f"- Consensus-labelled rows: {stats['n_labelled']}",
        f"- Conflict-quarantined rows: {stats['n_conflicts']}",
        f"- Alloy families: {stats['n_families']}",
        f"- Distinct elements: {stats['n_distinct_elements']}",
        f"- Rows this package's descriptors can score: {stats['n_descriptor_ready']}",
        "- Label distribution: "
        + ", ".join(f"{phase} {count}" for phase, count in sorted(stats["by_phase"].items())),
        f"- Multi-source rows: {stats['multi_source_rows']}"
        + (
            f" (agreement rate {stats['multi_source_agreement_rate']:.3f})"
            if stats["multi_source_agreement_rate"] is not None
            else ""
        ),
    ]
    sources = manifest.get("sources", [])
    if sources:
        lines += ["", "| source | rows yielded | license | SHA-256 (upstream bytes) |",
                  "|---|---:|---|---|"]
        for entry in sources:
            digest = entry.get("sha256", "")
            short = f"`{digest[:16]}...`" if digest else "(built locally)"
            lines.append(
                f"| {entry['name']} | {entry.get('rows_yielded', '?')} | "
                f"{entry.get('license', '?')} | {short} |"
            )
    lines.append("")
    return lines


def main() -> int:
    today = datetime.date.today().isoformat()
    lines = [
        "# Corpus card: the consolidated experimental HEA phase corpus",
        "",
        f"Generated by `tools/corpus_card.py` with hea-bench {_hea_bench_version} "
        f"on {today}. Regenerate after any corpus release.",
        "",
        "The corpus consolidates published experimental HEA phase observations "
        "into one provenance-tracked table with a conservative consensus label. "
        "It is the input to the phase-prediction benchmark and a product in its "
        "own right, queryable through `hea_bench.corpus.load_corpus`.",
        "",
        "## Versions and roles",
        "",
        "- **v0.1.0 is the reference corpus**: three hand-curated sources, and "
        "the corpus every published baseline number is measured on. The "
        "benchmark (`load_benchmark`), the phase predictions and the domain "
        "flag always use it, and it is the recommended evaluation target.",
        "- **v0.2.0 is the extended corpus**: the same recipe plus the "
        "Chizhevskiy LLM-extracted database. Larger and noisier. It is what "
        "`load_corpus()` and the apps' Dataset tab open by default, for "
        "browsing and download, and `load_benchmark(version=\"0.2.0\")` "
        "opts the benchmark into it.",
        "- The corpus version counter (v0.x) is independent of the package "
        "version (2.x). A corpus release is frozen forever: its rows, digests, "
        "and statistics never change, and adding data means a new version.",
        "",
        "## How the corpus is built",
        "",
        "Every source dataset ships with the package, so the corpus is built "
        "on the user's machine, once, with no download: loaders, consolidation "
        "rules, a pinned SHA-256 of the largest source, and the split "
        "algorithm turn the shipped files into a corpus byte-identical to the "
        "one every reported number was computed against. The build refuses to "
        "produce a partial corpus when a source is missing. One call builds "
        "every version, from a pip install or a repository checkout:",
        "",
        "```python",
        "from hea_bench.corpus import build_corpus",
        "build_corpus()",
        "```",
        "",
        "The MCP server's `corpus_build` tool and the apps do the same. In a "
        "repository checkout, `python -m hea_bench.benchmark.consolidate` is "
        "equivalent.",
        "",
        "## Sources, licenses, provenance chains",
        "",
    ]
    for name in ("borg2020", "pei2020", "peivaste", "chizhevskiy2026"):
        lines += [SOURCE_SECTIONS[name], ""]
    lines += [HARMONIZATION, "", "## Statistics", ""]
    for version in ("0.1.0", "0.2.0"):
        try:
            lines += _version_section(version)
        except FileNotFoundError:
            lines += [f"### Corpus v{version}", "", "(not built in this checkout)", ""]
    lines += [LIMITATIONS]

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
