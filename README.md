# hea-bench

An open, reproducible benchmark suite and reference baselines for
**high-entropy alloy (HEA) phase prediction**.

[![DOI](https://zenodo.org/badge/1246292321.svg)](https://doi.org/10.5281/zenodo.20346287)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
![tests: 241](https://img.shields.io/badge/tests-241%20passing-success)
![coverage: 90.2%](https://img.shields.io/badge/v0.1.0%20coverage-90.2%25-success)

## TL;DR

- A **consolidated, deduplicated open dataset** of 7,784 experimentally
  characterized multi-principal element alloys, merged from three
  primary sources (Borg 2020, Pei 2020, Peivaste 2023) with
  per-row source provenance.
- **Reference baseline implementations** of the four canonical
  v0.1.0 empirical rules plus the v1.1 phi-family thermodynamic
  extension (`S_E`, `DeltaG_ss`, `DeltaG_max`, King `Phi`, Ye `phi`),
  all exposed as test-guarded descriptor and rule APIs.
- **A learned reference baseline** (v1.3, `hea_bench.baselines`): a
  logistic regression on the six descriptors that sets the quantitative
  floor a new method should beat. A linear fit only ties the best rule,
  but adding interaction terms triples its discrimination — the
  descriptors hold joint signal the single-threshold rules miss.
- **A clean, dependency-free Python API** (`pip install hea-bench`)
  *and* a self-contained HTML calculator that runs entirely
  client-side, computes the full v1.1 browser descriptor set plus the
  Miedema decompositions, and applies all six shipped rule outputs to
  the entered composition. The browser core is parity-tested against
  Python on canonical alloys.

> **Using an AI coding agent to integrate this?** See
> [AGENTS.md](./AGENTS.md) for a machine-oriented guide to the API,
> exact return types and units, the fastest path to each task, and
> the mistakes to avoid.

## Headline benchmark numbers (v0.1.0)

Running the four canonical rules against the consolidated benchmark
produces the reference baselines below. **These are pinned in tests so
any drift in dataset, descriptor code, or rule thresholds surfaces as
a test failure.**

| Rule | n_eval | Accuracy | Sens (single-phase) | Spec (multi-phase) | Youden's J |
|---|---:|---:|---:|---:|---:|
| **Zhang δ < 6.5%** | 6,922 | 57.1% | **98.9%** | **10.5%** | 0.094 |
| **Yang Ω > 1.1**   | 6,922 | 54.2% | 95.0% | 8.6% | 0.036 |

The Guo–Liu VEC rule predicts crystal structure rather than
single-vs-multi, so it's evaluated stratified to single-phase
observations (BCC|FCC only):

| Rule | n_eval | Accuracy | FCC sensitivity | BCC sensitivity |
|---|---:|---:|---:|---:|
| **Guo–Liu VEC** (FCC if VEC ≥ 8.0, BCC if VEC < 6.87) | 3,556 | 67.4% | 91.9% | **49.1%** |

Yeh ΔS<sub>mix</sub> is descriptive (no phase-prediction claim
attached) — 47% of the consolidated benchmark passes the 1.5R
HEA-class threshold, 37% sits in the MEA bin, 16% is dilute.

**The publishable observation:** on a consolidated benchmark drawn
from three independent open sources, both binary rules collapse to
"predict single-phase almost always" (Youden's J ~ 0.04–0.09), and
the VEC rule misses about half of observed BCC alloys despite
catching 92% of FCC alloys. The canonical rules generalize poorly.

### Learned reference baseline (v1.3)

The benchmark also ships a learned floor to beat. A logistic regression
on the same six descriptors, scored under the same held-out protocol,
ties the best rule (Youden's J ≈ 0.09) when linear but reaches J ≈ 0.31
once squared and interaction terms are added — evidence the descriptors
carry joint signal the single-threshold rules cannot reach. Needs the
`[ml]` extra (`pip install "hea-bench[ml]"`); see `hea_bench.baselines`.

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
hea_bench.s_excess(cantor)           # 0.318 J/(mol·K)  (Mansoori excess entropy)
hea_bench.delta_g_max(cantor)        # -8.00 kJ/mol  (most-negative Miedema pair)
hea_bench.phi_king(cantor)           # 3.533 (King 2016 proxy)
hea_bench.phi_ye(cantor)             # 34.82 (Ye 2015 proxy)

# Apply the canonical rules
from hea_bench.rules import guo_vec, king_phi, yang_omega, ye_phi, zhang_delta
zhang_delta.predict(cantor)          # 'single-phase'
yang_omega.predict(cantor)           # 'single-phase'
guo_vec.predict(cantor)              # 'FCC'
king_phi.predict(cantor)             # 'solid_solution'
ye_phi.predict(cantor)               # 'solid_solution'

# Run the full rule benchmark against the consolidated v0.1.0 dataset
from hea_bench.evaluate import build_report, build_evaluation_report
report = build_report()
print(report["rules"]["zhang_delta_6_5"]["accuracy"])  # 0.5711

# Held-out 5-fold cross-validation (v1.1) — every rule under
# stratified phase x source folds with optional per-fold threshold
# tuning, so the optimism gap is visible separately from the
# in-sample sweep.
heldout = build_evaluation_report(include_phi=True)
heldout["holdout_strict_consensus_tuned"]["rules"]["zhang_delta_tuned"]["youden_j_mean"]

# Intermetallic-aware sub-benchmark (v1.1) — King Phi and Ye phi
# scored against Peivaste's 12-class side-channel labels projected
# to solid_solution vs intermetallic, the distinction the phi rules
# were actually designed to make.
from hea_bench.evaluate import build_intermetallic_subbench_report
sub = build_intermetallic_subbench_report()
sub["in_sample"]["ye_phi_20_0"]["youden_j"]  # 0.191 (vs -0.012 on the coarse main benchmark)
```

Need the exact HTML calculator `Hmix` / `Omega` path from Python?
Use `hea_bench.browser_mixing_enthalpy(...)` and
`hea_bench.browser_omega(...)`. The benchmark-default
`mixing_enthalpy(...)` / `omega(...)` APIs remain the pair-table
definitions used by the pinned evaluation artifacts.

## Quick start (CLI)

```bash
hea-bench --version
python -m hea_bench.evaluate           # in-sample + held-out summary on v0.1.0
python -m hea_bench.evaluate --include-phi  # add King/Ye phi rules to the report
python -m hea_bench.evaluate --single-split  # quick 70/30 held-out reproduction (seed 0)
python -m hea_bench.evaluate --in-sample-only --include-phi  # legacy v1.1 in-sample artifact
python -m hea_bench.benchmark.coverage # coverage analysis on v0.1.0
```

## Quick start (browser, no install)

A self-contained HTML calculator computes the v1.1 browser descriptors,
applies all six shipped rules, and runs the Miedema decompositions
entirely client-side. Two equivalent paths:

- Open the hosted page: **https://dfieser.github.io/hea-bench/**
- Or download / clone the repo and double-click `web/index.html`. No
  install, no terminal, no server.

The page reports each rule's verdict (Yeh HEA/MEA/dilute, Zhang
single/multi, Guo–Liu FCC/BCC/mixed, Yang–Zhang single/multi,
King `Phi` solid-solution/intermetallic, Ye `phi`
solid-solution/intermetallic) alongside the computed descriptor values.
The parity-critical math lives in `web/hea-calculator-core.js` and is
regression-checked against Python by `tests/test_web_parity.py`.
The calculator's displayed `Hmix` / `Omega` path is also exposed from
Python as `hea_bench.browser_mixing_enthalpy(...)` and
`hea_bench.browser_omega(...)`.

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
                                             │ parity-tested
                                             │ shared formulas
                                             ▼
                              ┌──────────────────────────────┐
                              │  web/   (standalone HTML +   │
                              │          shared JS core)     │
                              │  - index.html                │
                              │  - hea-calculator-core.js    │
                              │  - mathjax/   (vendored)     │
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

- **90.2%** of the 7,784 compositions are scorable by every descriptor
  (δ, VEC, T_m, ΔS_mix, ΔH_mix, Ω) with the current 30-element
  `ELEMENTAL_DATA` table
- **99.6%** are scorable for Miedema-based descriptors only
  (the vendored matminer pair table covers 75 elements)
- Remaining uncovered alloys are dominated by C, B, Be, Ca, Sc, La;
  carbon and boron are deliberately held out (no metallic radius, and
  no 1-atm melting point for carbon), so further coverage gains come
  from the metals among the rest

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
│   ├── rules/           canonical rules + v1.1 King/Ye phi rules
│   ├── classifiers/     diagnostic-stats machinery
│   ├── composition.py   formula parser, normalizer
│   ├── constants.py     R = 8.314
│   ├── evaluate.py      orchestrator: rules vs benchmark → headline stats
│   └── cli.py           command-line entry point
├── tests/               241 tests, all passing
├── web/                 self-contained HTML calculator (pure JS, no server)
└── pyproject.toml
```

## Development

```bash
git clone <repo>
cd hea-bench
pip install -e ".[dev,data]"
python -m pytest tests/ -q
```

The HTML calculator (`web/index.html`) is an independent
JavaScript implementation of the same descriptors and rules. When you
modify Python descriptor code, sanity-check the calculator against
the same composition (e.g. the Cantor alloy values) so the two
surfaces don't drift.

## Contributing and support

Contributions, bug reports, and dataset additions are welcome. See
[CONTRIBUTING.md](./CONTRIBUTING.md) for development setup, the
testing convention, and the data-provenance policy. To report a bug
or ask a question, open a GitHub issue; for direct contact, email
the maintainer at `davjfies@gmail.com`. Participation is governed by
the [Code of Conduct](./CODE_OF_CONDUCT.md).

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

hea-bench is archived on Zenodo. The concept DOI
[10.5281/zenodo.20346287](https://doi.org/10.5281/zenodo.20346287)
always resolves to the latest version; v0.1.0 specifically is
[10.5281/zenodo.20346288](https://doi.org/10.5281/zenodo.20346288).

## Acknowledgements

All numerical parameters, formulas,
threshold values, and benchmark numbers are derived from cited
primary sources or computed in this codebase from documented inputs;
the author verified outputs against the cited literature.
