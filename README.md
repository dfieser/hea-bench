# hea-bench

Open, interpretable tools for computing the standard **high-entropy-alloy
(HEA) thermodynamic and geometric descriptors** and the classic empirical
**phase-prediction rules** — from any composition, with no fitted model and
no black box. Every number is a transparent closed-form expression over a
curated element-property table, validated against the primary literature.

[![DOI](https://zenodo.org/badge/1246292321.svg)](https://doi.org/10.5281/zenodo.20346287)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
![tests: passing](https://img.shields.io/badge/tests-passing-success)

> **Using an AI coding agent to integrate this?** See
> [AGENTS.md](./AGENTS.md) for a machine-oriented guide to the API,
> exact return types and units, the fastest path to each task, and the
> mistakes to avoid.

## What it computes

For any composition it reports:

- **Core descriptors** — mixing entropy ΔS<sub>mix</sub>, atomic-size
  mismatch δ, mean melting temperature T<sub>m</sub>, Miedema mixing
  enthalpy ΔH<sub>mix</sub>, valence-electron concentration VEC,
  Yang–Zhang Ω, Pauling electronegativity mismatch Δχ, Mansoori excess
  entropy S<sub>E</sub>, ΔG<sub>ss</sub>, ΔG<sub>max</sub>, King Φ, Ye φ.
- **Phase-prediction rules** — Yeh entropy, Zhang δ, Guo–Liu VEC,
  Yang–Zhang Ω, King Φ, Ye φ.
- **Miedema formation enthalpies** (browser/desktop apps) — compound /
  solid-solution / amorphous, decomposed into chemical, elastic,
  structural, and topological terms.
- **High-entropy oxides** (`hea_bench.oxides` + the apps' Oxides mode) —
  rock-salt, perovskite, fluorite, and pyrochlore formability
  descriptors over Shannon ionic radii with automatic charge-balance
  oxidation-state assignment: per-sublattice configurational entropy,
  cation size disorder, Goldschmidt t / octahedral μ / Bartel τ, the
  fluorite radius-dispersion rule, and the pyrochlore radius-ratio
  window.

Element coverage: 37 elements for alloys (Ag Al Au Be Ca Ce Co Cr Cu Fe
Gd Hf In Ir La Li Mg Mn Mo Nb Ni Os Pd Pt Re Rh Ru Sc Si Sn Ta Ti V W Y
Zn Zr); the Miedema pair table covers 75; the oxide module's Shannon
table covers 94.

## Three ways to run it

| Surface | Where | Status |
|---|---|---|
| **Python library + CLI** | `pip install hea-bench` | done, tested |
| **Zero-install browser app** | `web/index.html` · <https://dfieser.github.io/hea-bench/> | done, Python-parity-tested |
| **Native desktop app** | one offline `.exe` (Tauri wrapper of the browser app) | done, built from the same parity-tested core |

The three surfaces share **one calculation core**. The browser/desktop
core (`web/hea-calculator-core.js`) is a pure-JS port of the Python
library, and `tests/test_web_parity.py` guarantees the two match on all
666 binary pairs and the canonical multi-element fixtures.

## Quick start (Python)

```bash
pip install hea-bench
```

```python
import hea_bench as hb

cantor = {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}

hb.smix(cantor)               # 13.381 J/(mol·K)  = R · ln 5
hb.delta(cantor)              # 3.164 % atomic-size mismatch
hb.vec(cantor)                # 8.0 valence electrons
hb.mixing_enthalpy(cantor)    # -4.16 kJ/mol  (Miedema)
hb.omega(cantor)              # 5.79  (Yang–Zhang)
hb.delta_chi(cantor)          # 0.138 Pauling electronegativity mismatch
hb.s_excess(cantor)           # 0.318 J/(mol·K)  (Mansoori excess entropy)
hb.delta_g_max(cantor)        # -8.00 kJ/mol  (most-negative Miedema pair)
hb.phi_king(cantor)           # 3.533 (King 2016 proxy)
hb.phi_ye(cantor)             # 34.82 (Ye 2015 proxy)

# Apply the canonical rules
from hea_bench.rules import guo_vec, king_phi, yang_omega, ye_phi, zhang_delta
zhang_delta.predict(cantor)          # 'single-phase'
yang_omega.predict(cantor)           # 'single-phase'
guo_vec.predict(cantor)              # 'FCC'
king_phi.predict(cantor)             # 'solid_solution'
ye_phi.predict(cantor)               # 'solid_solution'
```

These Cantor-alloy values are pinned in the test suite as the canonical
sanity check. The rules are simple empirical surrogates — fast screens,
not predictions; treat their output accordingly.

## Quick start (browser, no install)

A self-contained HTML calculator computes every descriptor, applies all
six rules, and runs the Miedema decompositions entirely client-side, on
the full element table. Two equivalent paths:

- Open the hosted page: **<https://dfieser.github.io/hea-bench/>**
- Or clone the repo and open `web/index.html` — no install, no terminal,
  no server.

The parity-critical math lives in `web/hea-calculator-core.js` and is
regression-checked against Python by `tests/test_web_parity.py`.

## A note on Ω near ΔH<sub>mix</sub> ≈ 0

`Ω = Tm·ΔSmix / |ΔHmix|` diverges as ΔH<sub>mix</sub> → 0, so for
near-ideal alloys (|ΔH<sub>mix</sub>| ≲ 1–2 kJ/mol) the Ω *magnitude* is
extremely sensitive to the choice of Miedema pair table (sources
disagree most on Mn). The phase verdict (Ω ≫ 1.1) stays robust even when
the number does not — read Ω qualitatively in that regime.

## Project layout

```
hea-bench/
├── src/hea_bench/
│   ├── descriptors/     ΔS_mix, δ, VEC, T_m, ΔH_mix, Ω, S_E, φ + data tables
│   ├── rules/           the six empirical phase-prediction rules
│   ├── composition.py   formula parser, normalizer
│   ├── constants.py     R = 8.314
│   └── cli.py           command-line entry point
├── tests/               descriptor/rule unit tests + Python↔JS parity test
├── web/                 self-contained HTML/JS calculator (+ vendored MathJax)
├── src-tauri/           native desktop wrapper (Rust/Tauri)
├── examples/            worked Cantor-alloy walkthrough
└── pyproject.toml
```

## Development

```bash
git clone https://github.com/dfieser/hea-bench
cd hea-bench
pip install -e ".[dev]"
python -m pytest tests/ -q          # includes the Python↔JS parity test (needs Node)
```

The HTML calculator (`web/index.html`) is an independent JavaScript
implementation of the same descriptors and rules. When you modify the
Python descriptor code, update `web/hea-calculator-core.js` to match and
re-run `tests/test_web_parity.py` so the two surfaces don't drift.

## License

[MIT](./LICENSE). The vendored
[matminer Miedema data files](./src/hea_bench/descriptors/data/) remain
under their upstream BSD-3-Clause license, preserved at
[`descriptors/data/LICENSE.matminer.txt`](./src/hea_bench/descriptors/data/LICENSE.matminer.txt).

## Contributing and support

Contributions and bug reports are welcome. See
[CONTRIBUTING.md](./CONTRIBUTING.md) for development setup and the
testing convention. To report a bug or ask a question, open a GitHub
issue; for direct contact, email the maintainer at `dfieser9@gmail.com`.
Participation is governed by the [Code of Conduct](./CODE_OF_CONDUCT.md).

## Citation

Citation metadata in [`CITATION.cff`](./CITATION.cff). When citing
hea-bench, please also cite the primary sources for the parametrizations
it implements (de Boer et al. 1988 for the Miedema model; the rule
papers — Yeh 2004, Zhang 2008, Guo–Liu 2011, Yang–Zhang 2012, King 2016,
Ye 2015 — listed in `web/index.html`) and matminer for the vendored pair
table.

hea-bench is archived on Zenodo. The concept DOI
[10.5281/zenodo.20346287](https://doi.org/10.5281/zenodo.20346287)
always resolves to the latest version.

## Disclaimer

Descriptor values and rule predictions reported by hea-bench are
**empirical estimates** for research and informational purposes only.
The rules and descriptors are semi-empirical surrogates with known
limitations. No warranty is made as to accuracy, completeness, fitness
for any particular purpose, or suitability for material qualification.
Do not use these outputs as the sole basis for engineering design or
material qualification without independent verification by validated
thermodynamic methods (e.g. CALPHAD or DFT).

Software is provided **"as is"** under the [MIT License](LICENSE).
Vendored Miedema elemental parameters from
[matminer](https://github.com/hackingmaterials/matminer) remain under
their upstream BSD-3-Clause license; see
[`src/hea_bench/descriptors/data/LICENSE.matminer.txt`](./src/hea_bench/descriptors/data/LICENSE.matminer.txt).
