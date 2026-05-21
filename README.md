# hea-bench

An open, reproducible benchmark suite and reference baselines for
**high-entropy alloy (HEA) phase prediction**.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
![tests: 151](https://img.shields.io/badge/tests-151%20passing-success)
![coverage: 86.7%](https://img.shields.io/badge/v0.1.0%20coverage-86.7%25-success)

## TL;DR

- A **consolidated, deduplicated open dataset** of 7,784 experimentally
  characterized multi-principal element alloys, merged from three
  primary sources (Borg 2020, Pei 2020, Peivaste 2023) with
  per-row source provenance.
- **Reference baseline implementations** of the four canonical
  empirical phase-prediction rules (Yeh ΔS<sub>mix</sub>, Zhang δ,
  Guo-Liu VEC, Yang-Zhang Ω), wrapped as proper diagnostic
  classifiers with sensitivity / specificity / Wilson 95% CIs.
- **A clean, dependency-free Python API** (`pip install hea-bench`)
  *and* an in-browser frontend that runs the same library via
  Pyodide/WebAssembly — no install, no server, no JavaScript
  re-implementation.

## Headline benchmark numbers (v0.1.0)

Running the four canonical rules against the consolidated benchmark
produces the reference baselines below. **These are pinned in tests so
any drift in dataset, descriptor code, or rule thresholds surfaces as
a test failure.**

| Rule | n_eval | Accuracy | Sens (single-phase) | Spec (multi-phase) | Youden's J |
|---|---:|---:|---:|---:|---:|
| **Zhang δ < 6.5%** | 6,651 | 56.7% | **99.0%** | **8.5%** | 0.075 |
| **Yang Ω > 1.1**   | 6,651 | 54.4% | 95.8% | 7.4% | 0.032 |

The Guo–Liu VEC rule predicts crystal structure rather than
single-vs-multi, so it's evaluated stratified to single-phase
observations (BCC|FCC only):

| Rule | n_eval | Accuracy | FCC sensitivity | BCC sensitivity |
|---|---:|---:|---:|---:|
| **Guo–Liu VEC** (FCC if VEC ≥ 8.0, BCC if VEC < 6.87) | 3,463 | 66.9% | 92.3% | **48.3%** |

Yeh ΔS<sub>mix</sub> is descriptive (no phase-prediction claim
attached) — 47% of the consolidated benchmark passes the 1.5R
HEA-class threshold, 37% sits in the MEA bin, 16% is dilute.

**The publishable observation:** on a consolidated benchmark drawn
from three independent open sources, both binary rules collapse to
"predict single-phase almost always" (Youden's J ~ 0.03–0.08), and
the VEC rule misses about half of observed BCC alloys despite
catching 92% of FCC alloys. The canonical rules generalize poorly.

## Quick start (Python)

```bash
pip install hea-bench
```

```python
import hea_bench

cantor = {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}

hea_bench.smix(cantor)               # 13.381 J/(mol·K)  = R · ln 5
hea_bench.delta(cantor)              # 3.164 % atomic-size mismatch
hea_bench.vec(cantor)                # 8.0 valence electrons
hea_bench.mixing_enthalpy(cantor)    # -4.16 kJ/mol  (Miedema)
hea_bench.omega(cantor)              # 5.79  (Yang-Zhang)

# Apply the canonical rules
from hea_bench.rules import zhang_delta, yang_omega, guo_vec
zhang_delta.predict(cantor)          # 'single-phase'
yang_omega.predict(cantor)           # 'single-phase'
guo_vec.predict(cantor)              # 'FCC'

# Run the full rule benchmark against the consolidated v0.1.0 dataset
from hea_bench.evaluate import build_report
report = build_report()
print(report["rules"]["zhang_delta_6_5"]["accuracy"])  # 0.5670
```

## Quick start (CLI)

```bash
hea-bench --version
python -m hea_bench.evaluate           # run all 4 rules on v0.1.0
python -m hea_bench.benchmark.coverage # coverage analysis on v0.1.0
```

## Quick start (browser, no install)

The same Python library runs in a browser tab via Pyodide. After
cloning:

```bash
python -m http.server 8000 --directory web
# open http://localhost:8000
```

First load downloads the Pyodide runtime (~10 MB, cached after) and
the `hea_bench` wheel. Then the in-page UI computes descriptors
locally — same code, same numerics, no server.

## Architecture

```
                                ┌────────────────────────────┐
                                │  data/consolidated/v0.1.0/ │
                                │  - consolidated.csv        │
                                │  - rule_baselines.json     │
                                │  - coverage_report.json    │
                                │  - manifest.json           │
                                └─────────────▲──────────────┘
                                              │
                                              │ produced by
                                              │
   ┌─────────────────────┐    ┌───────────────┴───────────────┐
   │  data/raw/          │    │  src/hea_bench/               │
   │  - borg2020/        │───►│  - benchmark/                 │
   │  - pei2020/         │    │      consolidate.py           │
   │  - peivaste/        │    │      coverage.py              │
   │  (per-source READMEs│    │      loaders/{borg,pei,...}.py│
   │   + provenance)     │    │  - descriptors/{size, vec,    │
   └─────────────────────┘    │      melting, miedema, omega} │
                              │  - rules/{yeh, zhang,         │
                              │      guo, yang}               │
                              │  - classifiers/               │
                              │      diagnostic_stats.py      │
                              │  - evaluate.py                │
                              └──────────────┬────────────────┘
                                             │
                                             │ also runs in
                                             ▼
                              ┌──────────────────────────────┐
                              │  web/   (Pyodide front-end)  │
                              │  - index.html                │
                              │  - dist/hea_bench-*.whl      │
                              └──────────────────────────────┘
```

## What's in the benchmark

`data/consolidated/v0.1.0/consolidated.csv` — **7,784 unique
compositions × 14 columns**:

- `composition_key` — alphabetically sorted element symbols + 4-decimal
  mole fractions, the canonical join key
- `n_elements`, `sources` (semicolon-separated)
- `canonical_phase` — one of `BCC` / `FCC` / `HCP` / `multi-phase`
  (blank when the contributing sources disagree)
- `has_conflict` — 1 when the canonical_phase is blank because of a
  source-label disagreement
- Per-source canonical and raw labels preserved verbatim
- `borg_processing`, `borg_doi`, `source_row_ids` for provenance

100 of the 7,784 compositions are *cross-source label conflicts* —
flagged for downstream resolution rather than silently picked. The
sources are: Borg 2020 (740 alloys), Pei 2020 (1,209 alloys),
Peivaste 2023 (7,747 alloys).

See [`data/consolidated/v0.1.0/README.md`](./data/consolidated/v0.1.0/README.md)
for the full schema, per-source attribution, and a complete
description of the consolidation rules. See
[`data/raw/`](./data/raw/) for per-source provenance, licenses, and
SHA-256s.

## What's covered

- **86.7%** of the 7,784 compositions are scorable by every descriptor
  (δ, VEC, T_m, ΔS_mix, ΔH_mix, Ω) with the current 24-element
  `ELEMENTAL_DATA` table
- **99.6%** are scorable for Miedema-based descriptors only
  (the vendored matminer pair table covers 75 elements)
- Top elements whose addition would lift coverage to ~95%: Mg, C, Zn,
  B, Sn, Re (all already in the matminer pair table — pending v0.2.0
  data release)

Re-run the coverage analysis on your own version of the dataset with:

```bash
python -m hea_bench.benchmark.coverage
```

## Sources and attribution

Every primary source is cited per-row in the consolidated CSV. The
data files in [`data/raw/`](./data/raw/) carry per-source READMEs with
DOIs, licenses, and acquisition SHA-256s.

| Source | Citation | License | Status |
|---|---|---|---|
| Borg 2020 | *Sci. Data* **7**, 430 ([doi:10.1038/s41597-020-00768-9](https://doi.org/10.1038/s41597-020-00768-9)) | CC-BY-4.0 | Mirrored |
| Pei 2020 | *npj Comput. Mater.* **6**, 50 ([doi:10.1038/s41524-020-0308-7](https://doi.org/10.1038/s41524-020-0308-7)) | CC-BY-4.0 | Mirrored |
| Peivaste 2023 | *Sci. Rep.* **13**, 22556 + [GitHub](https://github.com/Iman-Peivaste/ML_HEAs_Phase_Dataset) | none on data | Pointer-only (`fetch.py`) |
| Miedema pair enthalpies | [matminer](https://github.com/hackingmaterials/matminer) `MiedemaLiquidDeltaHf.tsv` | BSD-3-Clause | Vendored (see [`descriptors/data/`](./src/hea_bench/descriptors/data/)) |

## Project layout

```
hea-bench/
├── data/
│   ├── raw/             per-source data with READMEs, licenses, SHAs
│   └── consolidated/    versioned benchmark releases (v0.1.0 here)
├── src/hea_bench/
│   ├── benchmark/       loaders, consolidator, coverage analysis
│   ├── descriptors/     ΔS_mix, δ, VEC, T_m, ΔH_mix, Ω + data tables
│   ├── rules/           four canonical empirical rules as classifiers
│   ├── classifiers/     diagnostic-stats machinery
│   ├── composition.py   formula parser, normalizer
│   ├── constants.py     R = 8.314
│   ├── evaluate.py      orchestrator: rules vs benchmark → headline stats
│   └── cli.py           command-line entry point
├── tests/               151 tests, all passing
├── web/                 Pyodide browser frontend
└── pyproject.toml
```

## Development

```bash
git clone <repo>
cd hea-bench
pip install -e ".[dev,data]"
python -m pytest tests/ -q
```

After modifying any descriptor code or vendored data, rebuild the
Pyodide wheel:

```bash
python -m pip wheel . --no-deps -w web/dist
```

## License

[MIT](./LICENSE). The vendored
[matminer Miedema data files](./src/hea_bench/descriptors/data/) remain
under their upstream BSD-3-Clause license, preserved at
[`descriptors/data/LICENSE.matminer.txt`](./src/hea_bench/descriptors/data/LICENSE.matminer.txt).

## Citation

Citation metadata in [`CITATION.cff`](./CITATION.cff). When citing
hea-bench, please also cite the original source datasets (Borg, Pei,
Peivaste) and matminer — see `data/raw/<source>/README.md` for each
source's preferred citation.

A DOI for hea-bench itself will be minted via Zenodo on the first
tagged release.

## Acknowledgements

Development was assisted by large language models (Claude) for code
scaffolding and documentation. All numerical parameters, formulas,
threshold values, and benchmark numbers are derived from cited
primary sources or computed in this codebase from documented inputs;
the author verified outputs against the cited literature.
