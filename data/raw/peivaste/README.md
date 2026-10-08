# peivaste/ — Iman Peivaste's MPEA phase dataset

> **Per-source documentation** for the Peivaste *et al.* HEA phase dataset.
> `dataset11252_79.csv` is mirrored here byte for byte under CC BY 4.0.

## Source

- **Repository:** [Iman-Peivaste/ML_HEAs_Phase_Dataset](https://github.com/Iman-Peivaste/ML_HEAs_Phase_Dataset)
- **Companion paper:** I. Peivaste *et al.*, "Data-driven analysis and prediction of stable phases for high-entropy alloy design", *Scientific Reports* 13, 22556 (2023), doi:[10.1038/s41598-023-50044-0](https://doi.org/10.1038/s41598-023-50044-0). Cite it whenever this dataset is used.
- **Acquired by `hea-bench` on:** 2026-05-20 (top of `main` at the time).
- **Snapshot:** `dataset11252_79.csv` is 6,424,704 bytes, SHA-256 `655a43e521003f5c8973050b5f7c0a5d4b9ab902ca4ecc9c8a7d9813b2b0ba10`, with CRLF line endings. `.gitattributes` keeps git from converting them, and `hea_bench/benchmark/loaders/peivaste.py` refuses any other bytes, because every published number was computed from these.

## License

**CC BY 4.0.** The authors added a LICENSE file on 2026-10-08 by merging
[ML_HEAs_Phase_Dataset#2](https://github.com/Iman-Peivaste/ML_HEAs_Phase_Dataset/pull/2)
(merge commit `e823c17`). The file at that commit is byte-identical to
the 2026-05-20 snapshot (same git blob, `97040283`), so the mirrored
bytes are the licensed bytes. Before that date the repository declared
no license, and `hea-bench` fetched the file from upstream at build time
instead of mirroring it.

## Files (upstream, in `Dataset/` folder)

| Upstream file | Size | What it is |
|---|---|---|
| `Dataset_HEAs.xlsx` | 254 KB | Original Excel compilation |
| `dataset11252_79.csv` | 6.4 MB | **Primary dataset** — 11,252 records, post-CSV conversion |
| `dataset10387_70.csv` | 5.6 MB | First-stage cleaned, 10,387 records |
| `Enthalpy_mix.csv` | 20 KB | Auxiliary: pair mixing enthalpies |
| `elemental_propertieses.csv` | 52 KB | Auxiliary: per-element parameter table |
| `Dataset_preparation.ipynb` | 33 KB | Cleaning pipeline (produces final 5,677-row dataset, which is *not* committed upstream — must be regenerated) |

Only `dataset11252_79.csv`, the primary dataset, is mirrored here. The
other files are in the upstream repository.

## Schema of `dataset11252_79.csv`

**80 fields per row, 11,252 data rows + 1 header.** Verified
2026-05-20: every data row has exactly 80 fields (no embedded commas,
no quoting irregularities).

### Header / data alignment quirk

The upstream header is offset by one position relative to the data — the
first header field is *empty*, and downstream labels are shifted left by
one. Concretely:

| Data column | Header label says | What it actually is |
|---|---|---|
| 1 | `""` (blank) | Row index integer (0-indexed) |
| 2 | `index` | **Alloy formula string** (e.g., `AlAuCoCrCuNi`) |
| 3 | `Num_el` | Number of distinct elements |
| 4–65 | `Li`, `Be`, …, `Au` | Mole fractions of 62 elements (Li…Au, with rare/unstable isotopes omitted) |
| 66 | `VEC` | Precomputed valence-electron concentration |
| 67 | `Pauling_EN` | Mean Pauling electronegativity |
| 68 | `Melting_point_K` | Composition-weighted melting point |
| 69 | `DFT_LDA_Etot` | DFT total energy (LDA functional) |
| 70 | `outer_shell_electrons` | Outer-shell e⁻ count |
| 71 | `no_of_valence_electrons` | Same family — total valence e⁻ |
| 72 | `Atomic_radius_calculated` | Mean atomic radius |
| 73 | `Atomic_weight` | Mean atomic weight |
| 74 | `Pauling_EN_div` | Electronegativity stdev/divergence |
| 75 | `entropy` | ΔS_mix (J·mol⁻¹·K⁻¹) |
| 76 | `Atomic_radius_calculated_dif` | **δ** atomic size mismatch (%) |
| 77 | `Enthalpy` | ΔH_mix (kJ·mol⁻¹) |
| 78 | `Geo` | Geometric stability parameter |
| 79 | `Phase` | **Phase label** ← target for benchmarking |
| 80 | `E_per_el` | Energy per element |

### Phase-label distribution (column 79)

12 unique labels across 11,252 rows:

| Label | Count | Fraction |
|---|---:|---:|
| `BCC` | 3,357 | 29.8% |
| `FCC` | 2,251 | 20.0% |
| `BCC+FCC` | 1,661 | 14.8% |
| `AM` | 1,279 | 11.4% |
| `IM` | 1,186 | 10.5% |
| `FCC+IM` | 500 | 4.4% |
| `BCC+IM` | 432 | 3.8% |
| `BCC+FCC+IM` | 182 | 1.6% |
| `HCP` | 153 | 1.4% |
| `FCC+AM` | 145 | 1.3% |
| `BCC+AM` | 72 | 0.6% |
| `BCC+FCC+AM` | 34 | 0.3% |

Notes:
- `AM` = amorphous, `IM` = intermetallic. Borg 2020 collapses both into
  "other"; Peivaste keeps them separate. This finer-grained labeling is
  one reason to consolidate Peivaste alongside Borg.
- `HCP` is rare (1.4%) but present.

### Notes for downstream consolidation

- **Recompute descriptors from raw composition** rather than trust the
  upstream precomputed values. Different sources use different elemental
  parameter tables; consistency is more important than matching upstream.
- **Treat the precomputed descriptors as benchmark-able predictions** —
  comparing our recomputed values to upstream's is a sanity check.
- **Dedup key:** the formula string (col 2) only. Peivaste doesn't track
  processing route, so all rows are nominally "as-reported."
- **Label-conflict policy:** when Peivaste and Borg (or any other source)
  give different phase labels for the same composition, record both;
  don't silently pick.

## Why this dataset is in the corpus

- **Scale.** 11,252 records — by far the largest open MPEA phase
  database we've identified. Borg 2020 has 740 (formula, processing)
  pairs; Peivaste alone is ~15× larger.
- **Label granularity.** AM, IM, HCP, and multi-phase combinations
  separated rather than collapsed into "other."
- **Composition-only.** No processing metadata, which means it can't
  distinguish phases that depend on processing history — but this also
  makes it the right level for descriptor-rule validation (which is
  composition-only by design).
