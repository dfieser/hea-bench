# borg2020/ — Borg et al. 2020 expanded MPEA dataset

> **Mirrored under CC-BY-4.0.** Verbatim copy of `MPEA_dataset.csv` from
> the figshare deposit attached to Borg *et al.* (2020) *Scientific Data*
> **7**, 430. This is the canonical reference dataset for our work — it
> drove the validation in the legacy `thermo-descriptor-calculator/`
> repo whose findings motivated the pivot to a benchmark suite.

## Source

- **Citation:** Borg, C., Frey, C., Moy, J., Moh, J., Miracle, D. B.,
  Saal, J. E., Meredig, B., Pollock, T. M., & Gorsse, S. (2020).
  Expanded dataset of mechanical properties and observed phases of
  multi-principal element alloys. *Scientific Data* **7**, 430.
- **DOI (paper):** [10.1038/s41597-020-00768-9](https://doi.org/10.1038/s41597-020-00768-9)
- **DOI (data, figshare):** [10.6084/m9.figshare.12642953](https://doi.org/10.6084/m9.figshare.12642953)
  (v9 used here)
- **Direct file URL:** `https://ndownloader.figshare.com/files/25797305`
- **Acquired by hea-bench on:** 2026-05-20 (mirrored from the legacy
  `thermo-descriptor-calculator/validation/data/MPEA_dataset.csv`, which
  was originally downloaded from figshare on the same date)
- **Bytes:** 332,126
- **SHA-256:** `c5504d93fd324d1be26cf814d0694ee9ee95578d68a0b38aba6813b939fa2c5d`

## License

[Creative Commons Attribution 4.0 International (CC-BY-4.0)](https://creativecommons.org/licenses/by/4.0).
*Scientific Data* requires open licensing for all article-associated
datasets; the figshare deposit is explicitly CC-BY-4.0. Cite the
original Borg *et al.* (2020) paper when using this data.

## File

`MPEA_dataset.csv` — 332 KB, 1,546 lines (1 header + 1,545 data rows).

## Schema

23 columns. Notation `$\mu$m` and `$^\circ$C` in column names is raw
LaTeX from the original upstream file (no preprocessing); consumers
should expect those exact header strings.

| Column | Meaning |
|---|---|
| 1. `IDENTIFIER: Reference ID` | Integer ID linking related rows from the same source paper (multiple alloys per paper share an ID) |
| 2. `FORMULA` | Composition as space-separated `Element<atomic-amount>` tokens (e.g., `Al0.25 Co1 Fe1 Ni1`). Atomic amounts are proportional, not normalized. |
| 3. `PROPERTY: Microstructure` | **Full phase-content label** — `FCC`, `BCC`, `FCC+BCC`, `BCC+B2`, `BCC+Laves`, `FCC+Sec.`, etc. 30+ unique labels. |
| 4. `PROPERTY: Processing method` | `CAST`, `WROUGHT`, `ANNEAL`, etc. |
| 5. `PROPERTY: BCC/FCC/other` | **Simplified 3-class phase label** — `FCC`, `BCC`, or `other`. Used in our existing validator. |
| 6–17 | Mechanical / physical properties: grain size, density (exp + calculated), Vickers hardness, tension/compression type, test temperature, yield strength, UTS, elongation, Young's modulus |
| 18–20 | Interstitial content: `O content (wppm)`, `N content (wppm)`, `C content (wppm)` |
| 21–23 | Provenance: `REFERENCE: doi`, `REFERENCE: year`, `REFERENCE: title` |

### Row counts after deduplication

(From the analysis already done in `thermo-descriptor-calculator/validation/validate_rules.py`.)

- **Raw rows:** 1,545 (multiple measurements per alloy at different
  test temperatures and test types)
- **Unique `(FORMULA, Processing method)`:** 740 (the natural dedup key
  for phase-prediction work — phase is a property of the alloy and its
  processing, not the mechanical test)
- **Covered by `ELEMENT_DATA` in our legacy validator (24 elements):**
  670 alloys (90.5%) — the remaining 70 contain rare additions
  (C, Sn, Mg, Zn, Li, B, Re, Ca, Sc, Nd, Ga)

### Simplified phase label distribution (column 5, per-alloy view)

| Label | Count |
|---|---:|
| `other` | 812 |
| `BCC` | 468 |
| `FCC` | 265 |

The full `PROPERTY: Microstructure` column (3) preserves the underlying
phases — e.g., `FCC+BCC`, `BCC+B2`, `BCC+Laves` — for downstream
analyses that need finer granularity than 3-class.

## Notes for downstream consolidation

- **Dedup key:** `(normalized FORMULA, Processing method)`. Within Borg
  alone, dedup goes 1545 → 740.
- **Inter-source dedup:** when consolidating across Borg + Peivaste +
  Pei 2020, Borg's `(formula, processing)` key is the strictest; the
  other two are composition-only. Default join: composition only, with
  Borg's processing column preserved as a side-channel for users who
  want it.
- **Label-normalization decisions** (for the canonical taxonomy):
  - Borg `BCC` ↔ Peivaste `BCC` ↔ Pei `bcc`  (trivial case-fold)
  - Borg `other` is a heterogeneous bucket — has to split into
    {dual-phase SS, intermetallic, mixed} using the full
    `PROPERTY: Microstructure` column to make it comparable with
    Peivaste's finer labels.
  - Borg has no `AM` (amorphous) class; Peivaste/Pei do. Borg's
    amorphous-forming alloys are buried in `other`.

## Why this dataset is worth being the backbone

- **Provenance-complete.** Every row links back to its source paper via
  `REFERENCE: doi`. None of the other compilations do this.
- **Phase + mechanical properties in one file.** Useful for downstream
  multi-property work even though our Phase 1 focus is phase prediction
  only.
- **Processing column.** Only Borg distinguishes (formula, processing)
  pairs. Captures the fact that the same composition can form
  different phases depending on whether it's as-cast vs. annealed.
- **Already battle-tested in our pipeline.** Used in
  `thermo-descriptor-calculator/validation/validate_rules.py` for the
  78.5%-on-single-phase-VEC and δ-threshold-sweep results that informed
  the project pivot.

## Cross-link to legacy validator

The legacy validator at
`../../../thermo-descriptor-calculator/validation/validate_rules.py`
loads this file from `validation/data/MPEA_dataset.csv` (its own local
copy). Both copies are byte-identical (same SHA-256). When the legacy
repo is finally retired, the validator code itself will be
ported into `hea_bench` as Phase 2 — the data already lives here.
