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
| (not integrated) `chizhevskiy2026/` | Chizhevskiy *et al.* 2026 (*Sci. Data* 13, 612), repo Vladimirchizh/hea_database | **Unknown.** No LICENSE file on the data repository, re-confirmed 2026-08-10. *Scientific Data* policy would imply CC-BY but that was **not** verified against the article, whose page is behind an access redirect. Treat as unlicensed until confirmed. | Not part of corpus v0.1.0. 12,427 LLM-extracted records with named intermetallics. Deferred: needs the license resolved and its free-text `Phase` column spot-checked against source papers before it can carry benchmark labels. |
| [`couzinie2018/`](couzinie2018/) | Couzinié *et al.* 2018 (*Data in Brief* 21, 1622) | CC-BY-4.0 | Acquisition stalled. Elsevier CDN supplementary files are mis-attributed, and the content is mostly subsumed by Borg anyway. **Deprioritized.** See README for log. |
| (planned) `miracle_senkov2017/` | Miracle & Senkov 2017 (*Acta Mater.* 122, 448) | Elsevier, to be determined | Not yet attempted |
| (planned) `witman/` | mwitman1/HEAphaseML (GitHub) | To be determined | Not yet attempted |
