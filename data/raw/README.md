# data/raw/ — per-source dataset acquisition

This directory contains one subfolder per upstream dataset. Each subfolder
has:

- `README.md` — citation, license status, schema, acquisition notes,
  decisions made
- `fetch.py` (where applicable) — downloads the dataset from upstream when
  redistribution isn't permitted
- `<dataset>.csv` (where redistribution *is* permitted under the hybrid
  policy summarized below)

## Redistribution policy summary

| Upstream license | Action |
|---|---|
| CC0 / CC-BY / CC-BY-SA / MIT / Apache / BSD / GPL / similar | **Mirror.** Commit the data file directly. Cite source in `README.md`. |
| No declared license / "all rights reserved" | **Pointer.** Commit only the `README.md` + `fetch.py`. User downloads on demand. |
| Non-commercial / restrictive | **Pointer + warning.** Same as above with explicit reuse caveats. |

An article being open access does not by itself license a dataset that
sits in a separate repository. Where a paper is CC-BY but its data lives
in a GitHub repo with no LICENSE file, this project treats the data as
unlicensed and refuses to mirror it. That is the conservative reading
and it is the reason the consolidated corpus is built locally rather
than shipped.

## Index of source datasets

Licenses re-verified 2026-08-10 by reading each upstream repository
directly. The two entries marked "no LICENSE file" were checked on that
date and neither repository declared a license.

| Subfolder | Source | License | Status |
|---|---|---|---|
| [`borg2020/`](borg2020/) | Borg *et al.* 2020 (*Sci. Data* 7, 430) | **CC-BY-4.0** (figshare deposit explicitly licensed) | ✓ **Mirrored 2026-05-20.** 1,545 measurement rows / 740 unique (formula, processing) alloys / 23 columns including phase, processing, mechanical properties, and per-row source DOI. The canonical backbone of the benchmark. |
| [`pei2020/`](pei2020/) | Pei *et al.* 2020 (*npj Comput. Mater.* 6, 50) | **CC-BY-4.0** (Crossref-confirmed, `tdm` and `vor`, zero delay) | ✓ **Mirrored 2026-05-20.** 1,252 rows, 2 columns (Alloy, Phase), four phase labels (bcc/fcc/hcp/multi-phase). 1,208 unique formulas load after deduplicating 43 repeated formulas and rejecting the malformed `Ta_Th` entry at row 1251. |
| [`peivaste/`](peivaste/) | Iman-Peivaste/ML_HEAs_Phase_Dataset (GitHub) + companion Sci. Rep. 13, 22556 (2023) by same authors | **None.** No LICENSE file on the data repository, re-confirmed 2026-08-10. The *Sci. Rep.* article is CC-BY, the GitHub dataset is not covered by it. | **Pointer-only.** `fetch.py` provided, CSV gitignored. Largest single contributor to the corpus, which is why the corpus as a whole cannot be redistributed. |
| [`chizhevskiy2026/`](chizhevskiy2026/) | Chizhevskiy *et al.* 2026 (*Sci. Data* 13, 612), repo Vladimirchizh/hea_database | **CC-BY-4.0**, resolved 2026-08-10: the maintainer merged [hea_database#2](https://github.com/Vladimirchizh/hea_database/pull/2) adding a LICENSE file (GitHub license detection confirms CC-BY-4.0). | ✓ **Mirrored 2026-08-10**, byte-identical to upstream at the pinned SHA-256. 12,427 LLM-extracted records, 2,974 unique parseable alloys. Feeds corpus **v0.2.0 only**; v0.1.0 is frozen without it. Its labels agree with the v0.1.0 consensus on only ~70% of overlapping alloys, so disagreements are quarantined as conflicts and corpus v0.2.0 is opt-in by design; v0.1.0 stays the reference corpus. |
| [`couzinie2018/`](couzinie2018/) | Couzinié *et al.* 2018 (*Data in Brief* 21, 1622) | CC-BY-4.0 | Acquisition stalled. Elsevier CDN supplementary files are mis-attributed, and the content is mostly subsumed by Borg anyway. **Deprioritized.** See README for log. |
| (planned) `miracle_senkov2017/` | Miracle & Senkov 2017 (*Acta Mater.* 122, 448) | Elsevier, to be determined | Not yet attempted |
| (planned) `witman/` | mwitman1/HEAphaseML (GitHub) | To be determined | Not yet attempted |
