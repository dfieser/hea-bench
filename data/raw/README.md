# data/raw/ — per-source dataset acquisition

This directory contains one subfolder per upstream dataset. Each subfolder
has:

- `README.md` — citation, license status, schema, acquisition notes,
  decisions made
- `fetch.py` (where applicable) — downloads the dataset from upstream when
  redistribution isn't permitted
- `<dataset>.csv` (where redistribution *is* permitted under the hybrid
  policy in `PROJECT_PLAN.md` §7)

## Redistribution policy summary

| Upstream license | Action |
|---|---|
| CC0 / CC-BY / CC-BY-SA / MIT / Apache / BSD / GPL / similar | **Mirror.** Commit the data file directly. Cite source in `README.md`. |
| No declared license / "all rights reserved" | **Pointer.** Commit only the `README.md` + `fetch.py`. User downloads on demand. |
| Non-commercial / restrictive | **Pointer + warning.** Same as above with explicit reuse caveats. |

## Index of source datasets

| Subfolder | Source | License | Status |
|---|---|---|---|
| [`borg2020/`](borg2020/) | Borg *et al.* 2020 (*Sci. Data* 7, 430) | **CC-BY-4.0** | ✓ **Mirrored 2026-05-20.** 1,545 measurement rows / 740 unique (formula, processing) alloys / 23 columns including phase, processing, mechanical properties, and per-row source DOI. The canonical backbone of the benchmark. |
| [`peivaste/`](peivaste/) | Iman-Peivaste/ML_HEAs_Phase_Dataset (GitHub) + companion Sci. Rep. 13, 22556 (2023) by same authors | **none declared on data** (paper is CC-BY but the data is on GitHub without a license file) | Pointer-only; `fetch.py` provided |
| [`pei2020/`](pei2020/) | Pei *et al.* 2020 (*npj Comput. Mater.* 6, 50) | **CC-BY-4.0** (Crossref-confirmed) | ✓ **Mirrored 2026-05-20.** 1,252 alloys × 4 phase labels (bcc/fcc/hcp/multi-phase). |
| [`couzinie2018/`](couzinie2018/) | Couzinié *et al.* 2018 (*Data in Brief* 21, 1622) | CC-BY-4.0 | Acquisition stalled — Elsevier CDN supplementary files are mis-attributed; mostly subsumed by Borg anyway. **Deprioritized.** See README for log. |
| (planned) `miracle_senkov2017/` | Miracle & Senkov 2017 (*Acta Mater.* 122, 448) | Elsevier — TBD | Not yet attempted |
| (planned) `witman/` | mwitman1/HEAphaseML (GitHub) | TBD | Not yet attempted |
