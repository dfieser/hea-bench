# pei2020/ — Pei et al. 2020 HEA dataset (npj CM)

> **Mirrored under CC-BY-4.0.** The CSV in this folder is a verbatim copy
> of the supplementary data file attached to Pei *et al.* (2020). It is
> redistributed here under the Creative Commons Attribution 4.0
> International License — see "License" below for the formal statement.

## Source

- **Citation:** Pei, Z., Yin, J., Hawk, J. A., Alman, D. E., & Gao, M. C.
  (2020). Machine-learning informed prediction of high-entropy solid
  solution formation: Beyond the Hume-Rothery rules.
  *npj Computational Materials* **6**, 50.
- **DOI:** [10.1038/s41524-020-0308-7](https://doi.org/10.1038/s41524-020-0308-7)
- **Supplementary file URL (Springer Nature):**
  `https://static-content.springer.com/esm/art%3A10.1038%2Fs41524-020-0308-7/MediaObjects/41524_2020_308_MOESM2_ESM.csv`
- **Acquired by hea-bench on:** 2026-05-20
- **Bytes:** 24,094
- **SHA-256:** `cd69e0eabb20c0d0ad08d16d7481094a327471cb5624fae6dd8ede65839c0cd2`

## License

[Creative Commons Attribution 4.0 International (CC-BY-4.0)](https://creativecommons.org/licenses/by/4.0).
Confirmed via Crossref license metadata for DOI
`10.1038/s41524-020-0308-7` — both `tdm` (text-and-data-mining) and `vor`
(version-of-record) license entries point to CC-BY-4.0 with zero delay.
*npj Computational Materials* is a fully open-access journal; the
supplementary data inherits the article's license.

**You may use this data freely with attribution to the original authors.**
When citing, cite the original Pei *et al.* (2020) paper, not this
mirror. The original Springer Nature URL is preserved above so users can
verify provenance.

## File

`pei2020_alloys_phases.csv` (renamed from upstream `MOESM2_ESM.csv` for
clarity; contents byte-identical, verified by SHA-256).

## Schema

Two columns, 1,252 data rows + 1 header.

| Column | Type | Description |
|---|---|---|
| `Alloy` | string | Composition as a formula string (e.g., `Al0.15Cr0.85`, `CoCrFeNi`, `Mo0.5Nb0.5TaTi`) |
| `Phase` | string | One of: `bcc`, `fcc`, `hcp`, `multi-phase` |

### Phase-label distribution

| Label | Count | Fraction |
|---|---:|---:|
| `multi-phase` | 627 | 50.1% |
| `bcc` | 261 | 20.9% |
| `fcc` | 218 | 17.4% |
| `hcp` | 146 | 11.7% |

### Notes for downstream consolidation

- **Coarse label set.** Pei collapses everything non-single-phase into
  `multi-phase` — no distinction between dual-phase solid solutions
  (FCC+BCC), intermetallics, or amorphous. This is *coarser* than
  Borg 2020's labels (which expose IM, AM, etc. via the full
  Microstructure column) and *much* coarser than Peivaste's 12-category
  set. When consolidating, Pei's `multi-phase` maps cleanly to "other"
  in Borg's simplified column or to the union of {IM, AM, BCC+FCC, …}
  in Peivaste.
- **Lower-case labels.** Pei uses `bcc`/`fcc`/`hcp` (lower-case). Other
  sources use `BCC`/`FCC`/`HCP`. Normalize to upper-case on load.
- **Formula duplicates.** 43 rows repeat a formula already seen earlier
  in the file. The loader dedups by raw formula string (first occurrence
  wins), leaving 1,209 unique formulas; consolidation then re-dedups by
  normalized composition across sources and flags label conflicts.
- **No processing metadata.** Like Peivaste, this is composition-only.
  All entries are nominally "as-reported."

## Why this dataset is worth pulling

- **Pedigree.** Pei *et al.* is one of the most-cited HEA ML papers
  (~600 citations as of 2026). Reviewers will look for it in any
  consolidated benchmark.
- **Author curation.** 1,252 alloys hand-curated by the ORNL group from
  primary literature; quality is high.
- **Cross-verification.** Where Borg, Peivaste, and Pei agree on the
  phase of a composition, confidence is high; where they disagree, that
  composition is flagged for review during consolidation.
