# peivaste/ — Iman Peivaste's MPEA phase dataset

> **Per-source documentation** for the Peivaste *et al.* HEA phase dataset.
> Data **not** redistributed in this repo: license status requires
> fetch-on-demand. Run `fetch.py` after cloning to materialize the CSV.

## Source

- **Repository:** [Iman-Peivaste/ML_HEAs_Phase_Dataset](https://github.com/Iman-Peivaste/ML_HEAs_Phase_Dataset)
- **Default branch:** `main`
- **Companion paper:** Peivaste, I. *et al.* — "Machine learning-based prediction of phases in high-entropy alloys: A data article." See the upstream repo README for the published article DOI.
- **Acquired by `hea-bench` on:** 2026-05-20 (rev: top of `main` at time of acquisition).

## License status

**No LICENSE file declared in the upstream repository.** Per the
`hea-bench` hybrid redistribution policy (PROJECT_PLAN.md §7), this means
we **do not redistribute** the CSV inside this repo. Users must download
it directly from upstream via `fetch.py`. The repository owner retains
all rights; users are responsible for confirming their own permitted use.

If upstream adds a permissive license in the future (CC-BY, MIT, Apache,
GPL, etc.), this restriction can be lifted and the CSV mirrored in
`hea-bench/data/raw/peivaste/` alongside this README.

## Files (upstream, in `Dataset/` folder)

| Upstream file | Size | What it is |
|---|---|---|
| `Dataset_HEAs.xlsx` | 254 KB | Original Excel compilation |
| `dataset11252_79.csv` | 6.4 MB | **Primary dataset** — 11,252 records, post-CSV conversion |
| `dataset10387_70.csv` | 5.6 MB | First-stage cleaned, 10,387 records |
| `Enthalpy_mix.csv` | 20 KB | Auxiliary: pair mixing enthalpies |
| `elemental_propertieses.csv` | 52 KB | Auxiliary: per-element parameter table |
| `Dataset_preparation.ipynb` | 33 KB | Cleaning pipeline (produces final 5,677-row dataset, which is *not* committed upstream — must be regenerated) |

`fetch.py` here pulls `dataset11252_79.csv` only (the primary dataset).
Other files can be obtained from the upstream repo directly.

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

## Fetching

```bash
cd hea-bench/data/raw/peivaste
python fetch.py              # downloads dataset11252_79.csv to this dir
```

The download URL and expected SHA-256 are pinned inside `fetch.py`.

## Why this dataset is worth pulling

- **Scale.** 11,252 records — by far the largest open MPEA phase
  database we've identified. Borg 2020 has 740 (formula, processing)
  pairs; Peivaste alone is ~15× larger.
- **Label granularity.** AM, IM, HCP, and multi-phase combinations
  separated rather than collapsed into "other."
- **Composition-only.** No processing metadata, which means it can't
  distinguish phases that depend on processing history — but this also
  makes it the right level for descriptor-rule validation (which is
  composition-only by design).
