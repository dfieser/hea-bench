# hea-bench consolidated benchmark — v0.1.0

> Built 2026-05-20 from Borg 2020 + Pei 2020 + Peivaste (snapshot of
> `main` 2026-05-20). Rebuild with:
>
> ```bash
> python -m hea_bench.benchmark.consolidate
> ```

## Headline numbers

| | count |
|---|---:|
| **Unique compositions** | **7,784** |
| BCC (single-phase) | 2,118 |
| FCC (single-phase) | 1,556 |
| HCP (single-phase) | 123 |
| multi-phase | 3,887 |
| **conflicts** (sources disagree on canonical phase) | **100** |

### Source overlap (how many sources contribute to each composition)

| Overlap | count | fraction |
|---|---:|---:|
| single-source | 6,783 | 87.1% |
| two-source | 890 | 11.4% |
| three-source | 111 | 1.4% |

The 100 cross-source label conflicts are themselves a publishable
finding: those are compositions where the open HEA literature itself
disagrees on the observed phase. They're flagged in the CSV with
``has_conflict=1`` and ``canonical_phase`` blank; the per-source labels
are preserved so downstream consumers can resolve however they want.

## Files

- ``consolidated.csv`` — the benchmark. One row per unique composition,
  14 columns. See "CSV schema" below.
- ``manifest.json`` — machine-readable provenance: source row counts,
  upstream SHA-256s, consolidation rules, totals.
- ``rule_baselines.json`` — the frozen v0.1.0 four-rule in-sample
  baseline artifact.
- ``rule_baselines_v1.1.json`` — the extended in-sample baseline on the
  same v0.1.0 benchmark, adding King Φ and Ye φ. Regenerate with
  ``python -m hea_bench.evaluate --in-sample-only --include-phi``.

## CSV schema

| Column | Type | Meaning |
|---|---|---|
| `composition_key` | string | Stable hash of normalized composition: alphabetically sorted element symbols at 4-decimal mole-fraction precision (e.g. `Co0.2000Cr0.2000Fe0.2000Mn0.2000Ni0.2000`). **The join key.** |
| `n_elements` | int | Number of distinct elements with non-zero fraction |
| `sources` | semicolon-separated | Sources contributing to this row, e.g. `borg2020;pei2020;peivaste` |
| `canonical_phase` | string | One of `BCC`, `FCC`, `HCP`, `multi-phase`. **Blank if `has_conflict=1`.** |
| `has_conflict` | 0 / 1 | 1 if any two contributing sources gave different canonical labels |
| `borg_label` | string | This row's canonical label per Borg 2020 (empty if Borg doesn't have this composition) |
| `pei_label` | string | Same, per Pei 2020 |
| `peivaste_label` | string | Same, per Peivaste |
| `borg_raw_label` | string | The verbatim upstream microstructure label from Borg (e.g. `BCC+Laves`, `FCC+B2`). Empty if Borg doesn't have this composition. |
| `pei_raw_label` | string | The verbatim upstream label from Pei (e.g. `bcc`, `multi-phase`) |
| `peivaste_raw_label` | string | The verbatim upstream label from Peivaste (e.g. `BCC+FCC+IM`, `AM`) |
| `borg_processing` | string | Processing route from Borg's `PROPERTY: Processing method` (e.g. `CAST`, `WROUGHT`). Empty if not from Borg. **Not part of the join key.** |
| `borg_doi` | string | DOI of the primary-literature paper Borg cited |
| `source_row_ids` | semicolon-separated `source:id` | Back-pointer for traceability, e.g. `borg2020:27;pei2020:142` |

## Consolidation rules

- **Join key:** composition only, 4-decimal mole-fraction precision.
  Borg's `processing` column is *not* part of the key — the same
  composition with different processing routes collapses to one row.
- **Per-source dedup:** each loader deduplicates internally before
  consolidation (Borg by `(formula, processing)`, Pei and Peivaste
  by formula).
- **Label agreement → canonical_phase set.** If two or more sources
  agree on the canonical class, that class is recorded.
- **Label disagreement → conflict.** If sources disagree,
  `canonical_phase` is blank, `has_conflict=1`, and per-source
  canonical and raw labels are preserved verbatim. *No silent voting.*

## What the canonical 4-class taxonomy collapses

The taxonomy used here is deliberately coarse to maximize cross-source
coverage at the v0.1.0 release. The richer source labels are preserved
verbatim in the `*_raw_label` columns so downstream consumers needing
finer granularity (amorphous vs. intermetallic vs. dual solid
solution) can reconstruct it.

| Canonical class | What's bundled in |
|---|---|
| `BCC` | single-phase BCC solid solution (incl. ordered B2 only when the source labeled it as plain BCC) |
| `FCC` | single-phase FCC solid solution |
| `HCP` | single-phase HCP solid solution (Borg's simplified column doesn't expose HCP; HCP entries come from Pei and Peivaste only) |
| `multi-phase` | everything else — dual-phase solid solution (FCC+BCC, …), intermetallic (IM; e.g. Laves, B2 ordered compounds), amorphous (AM, glassy), three-phase combos. **Includes amorphous, which is technically not multi-phase in the crystallographic sense.** Caveat documented in `taxonomy.py`. |

A finer 7+ class taxonomy is a candidate for v0.2.0. Reach for the
`*_raw_label` columns in this release if you need it now.

## Provenance and citing

See `manifest.json` for the SHA-256 of each upstream source CSV at the
time this release was built. To cite the benchmark itself, use the
top-level `CITATION.cff` in the repo root. To cite the underlying data,
cite each source individually:

- **Borg 2020:** Borg, C. *et al.* (2020). *Sci. Data* **7**, 430.
  [doi:10.1038/s41597-020-00768-9](https://doi.org/10.1038/s41597-020-00768-9). CC-BY-4.0.
- **Pei 2020:** Pei, Z. *et al.* (2020). *npj Comput. Mater.* **6**, 50.
  [doi:10.1038/s41524-020-0308-7](https://doi.org/10.1038/s41524-020-0308-7). CC-BY-4.0.
- **Peivaste:** Peivaste, I., Jossou, E., & Tiamiyu, A. A. (2023).
  *Sci. Rep.* **13**, 22556 (the data is the companion repository
  [Iman-Peivaste/ML_HEAs_Phase_Dataset](https://github.com/Iman-Peivaste/ML_HEAs_Phase_Dataset);
  the *Sci. Rep.* paper is CC-BY-4.0 but the dataset itself has no
  declared license — pointer-only).
