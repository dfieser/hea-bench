# descriptors/data — vendored physical-property tables

This folder holds two kinds of reference data that the descriptor
modules consume:

| File | Origin | License | Loader |
|---|---|---|---|
| `elemental.py` | Curated by hand from the legacy `validate_rules.py` (Pauling-style atomic radii, CRC melting points, standard valence-electron counts) | hea-bench's own (MIT) | importable Python dict |
| `pair_enthalpies.tsv` | Vendored from [matminer](https://github.com/hackingmaterials/matminer)'s `MiedemaLiquidDeltaHf.tsv` | BSD-3-Clause | `pair_enthalpies.py` |
| `miedema_parameters.csv` | Vendored from matminer's `Miedema.csv` (per-element Miedema parameters: φ\*, n_ws, V_m, valence, bulk modulus, shear modulus, T_m, structural stability) | BSD-3-Clause | source of the calculator page's Miedema decomposition tables (`MIEDEMA_PARAMS`, `ELEMENT_EXTENDED` in `web/calculator.html`); no Python loader yet |
| `LICENSE.matminer.txt` | matminer's full BSD-3-Clause license | — | — |

## What's in `pair_enthalpies.tsv`

2,628 binary mixing-enthalpy pairs from the Miedema macroscopic-atom
model, covering 75 chemical elements. Format: tab-separated
`elem_A`, `elem_B`, `delta_Hf` (kJ/mol). Self-pairs are not stored —
the loader returns `0.0` by convention.

### Provenance

matminer's data file derives from the Miedema model parameters
originally tabulated in:

> de Boer, F. R., Boom, R., Mattens, W. C. M., Miedema, A. R., &
> Niessen, A. K. (1988). *Cohesion in Metals: Transition Metal Alloys.*
> Cohesion and Structure, Vol. 1. North-Holland, Amsterdam.
> ISBN 978-0-444-87098-8.

This is the same primary source that Takeuchi & Inoue 2005
(*Mater. Trans.* **46**, 2817-2829) tabulated in their Tables 1, 2, 3.

### Cross-verification against Takeuchi-Inoue 2005

Pairs from Takeuchi-Inoue 2005 Table 1 that I read directly from the
PDF during acquisition (2026-05-20) and confirmed match matminer's
vendored values:

| Pair | matminer | Takeuchi-Inoue 2005 Table 1 | Match |
|---|---:|---:|---|
| Al-Ni | -22 kJ/mol | -22 kJ/mol | ✓ |
| Al-Fe | -11 kJ/mol | -11 kJ/mol | ✓ |
| Cu-Ni |  +4 kJ/mol |  +4 kJ/mol | ✓ |
| Ti-Ni | -35 kJ/mol | -35 kJ/mol | ✓ |

Other pair values used in our test suite (Cr-Fe, Co-Fe, Co-Cr,
Mn-Ni, etc.) were *computationally* spot-checked — the per-pair
values are what matminer ships, and our tests assert exactly those
values. We did **not** independently re-verify every test pair
against the PDF, only the four above. Both matminer and Takeuchi-
Inoue derive from the same primary source (de Boer *et al.* 1988),
so wholesale agreement is the expected outcome; the four
hand-confirmed cases are the evidence for that expectation.

If reviewers ask for fuller verification, the matminer maintainers
maintain the source-of-truth file at
[`hackingmaterials/matminer/.../MiedemaLiquidDeltaHf.tsv`](https://github.com/hackingmaterials/matminer/blob/main/src/matminer/utils/data_files/MiedemaLiquidDeltaHf.tsv)
and document its provenance in their package.

### Coverage vs. our 24-element ELEMENTAL_DATA

All 276 unique pairs needed for the 24 elements in
[`elemental.py`](elemental.py) are present in `pair_enthalpies.tsv`.
**100% pair coverage** at the current elemental data scope.

The vendored table also covers V (previously missing from our
Miedema setup) and many elements absent from `elemental.py` (rare
earths, alkali metals) — useful for Phase 2e coverage-gap expansion.

## File integrity (SHA-256, captured 2026-05-20)

```
pair_enthalpies.tsv      5b461ab99d7605fb8b306bda9cfe047b266ffa3e67387cb4b0ffeccaf57a5f48
miedema_parameters.csv   ef6e1dccc347628a52725b13752c9c311c522b463a08e46f87febfbd379202a3
LICENSE.matminer.txt     e4df766c6937dad4a0f0646e2afbbc1689aacb3a0c30db687acbd86f73083cc4
```

## Re-vendoring from upstream

The two data files were copied from matminer's
[`src/matminer/utils/data_files/`](https://github.com/hackingmaterials/matminer/tree/main/src/matminer/utils/data_files)
on 2026-05-20. To refresh:

```bash
curl -L https://raw.githubusercontent.com/hackingmaterials/matminer/main/src/matminer/utils/data_files/MiedemaLiquidDeltaHf.tsv \
  -o src/hea_bench/descriptors/data/pair_enthalpies.tsv
curl -L https://raw.githubusercontent.com/hackingmaterials/matminer/main/src/matminer/utils/data_files/Miedema.csv \
  -o src/hea_bench/descriptors/data/miedema_parameters.csv
```

Spot-check a few values against `pair_enthalpies.py`'s test suite
after any re-vendoring.

## Attribution requirement

matminer is BSD-3-Clause. The license text is preserved at
[LICENSE.matminer.txt](LICENSE.matminer.txt) in this folder.
Per condition (1) of the BSD-3 license, the matminer copyright notice
must be retained alongside any redistribution; this folder's `LICENSE.matminer.txt`
satisfies that. Per condition (3), we do not claim endorsement by the
University of California / Lawrence Berkeley National Laboratory /
the U.S. Department of Energy.

To cite the data, cite the original Miedema model literature (de Boer
*et al.* 1988) and, optionally, matminer for the digitization:

> Ward, L., Dunn, A., Faghaninia, A., *et al.* (2018). Matminer: An open
> source toolkit for materials data mining. *Comput. Mater. Sci.* **152**,
> 60-69. DOI: 10.1016/j.commatsci.2018.05.018.
