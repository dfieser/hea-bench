# hea-bench

<!-- mcp-name: io.github.dfieser/hea-bench -->

Open, interpretable tools for computing the standard **high-entropy-alloy
(HEA) and high-entropy-oxide (HEO) thermodynamic and geometric
descriptors** and the classic empirical **phase-prediction rules** — from
any composition, with no fitted model and no black box. Every number is a
transparent closed-form expression over a curated element-property table,
validated against the primary literature.

**Try it now:** <https://dfieser.github.io/hea-bench/> — no install, runs
entirely in your browser.

[![Paper](https://img.shields.io/badge/Materials-10.3390%2Fma19143075-2f7d3b)](https://doi.org/10.3390/ma19143075)
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

## Four ways to run it

| Surface | Where | Status |
|---|---|---|
| **Python library + CLI** | `pip install hea-bench` | done, tested |
| **Zero-install browser app** | <https://dfieser.github.io/hea-bench/> · `web/index.html` | done, Python-parity-tested |
| **Native desktop app** | a single portable `.exe`, [download (no install)](https://github.com/dfieser/hea-bench/releases/latest/download/HEA-Bench.exe) (Tauri wrapper of the same page) | done, built from the same parity-tested core |
| **MCP server for AI agents** | `pip install "hea-bench[mcp]"`, then `hea-bench-mcp` | done, seven tools over the same core |

The three surfaces share **one calculation core**. The browser/desktop
core (`web/hea-calculator-core.js`) is a pure-JS port of the Python
library, and `tests/test_web_parity.py` guarantees the two match on all
666 binary pairs and the canonical multi-element fixtures, while
`tests/test_web_oxides_parity.py` does the same for the oxide module,
down to identical warning messages.

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

## Quick start (oxides)

```python
from hea_bench import oxides

# Rost 2015 "J14" entropy-stabilized rock salt
j14 = oxides.describe_rock_salt({"Mg": 1, "Co": 1, "Ni": 1, "Cu": 1, "Zn": 1})
j14["descriptors"]["s_config"]       # 13.382 J/(mol·K) = R·ln 5
j14["oxidation_states"]              # all 2+ by charge balance

# Jiang 2018 single-phase high-entropy perovskite
pvk = oxides.describe_perovskite({"Sr": 1}, {"Zr": 1, "Sn": 1, "Ti": 1, "Hf": 1, "Mn": 1})
pvk["descriptors"]["goldschmidt_t"]  # 0.979, inside the 0.92–1.04 window
pvk["verdicts"]["bartel"]            # 'perovskite' (τ = 3.72 < 4.18)
```

Each `describe_*` report carries the solved oxidation states, the
Shannon radii actually used, every descriptor, the formability
verdicts with their windows, and any warnings. See
[`examples/02_oxides_walkthrough.py`](./examples/02_oxides_walkthrough.py)
for the full tour, including the fluorite and pyrochlore screens and
oxidation-state overrides.

## Quick start (AI agents, MCP)

LLM agents hallucinate descriptor values; this server grounds them.
`hea_bench.mcp_server` exposes the calculator over the
[Model Context Protocol](https://modelcontextprotocol.io/) as seven
deterministic tools (`parse_composition`, batch `alloy_descriptors` and
`alloy_rules`, `omega_sensitivity`, `oxide_report`, `element_coverage`,
`about`). Every response carries units, the citation key of each
parametrization, and the library version, so an agent's reasoning trace
contains auditable receipts rather than bare floats.

```bash
pip install "hea-bench[mcp]"
```

Register it with any MCP client (Claude Desktop, Cursor, ...), for
example in `claude_desktop_config.json`:

```json
{ "mcpServers": { "hea-bench": { "command": "hea-bench-mcp" } } }
```

The `omega_sensitivity` tool is worth singling out: it reports the
per-pair Miedema contributions and how far Ω moves when the dominant
element's pair enthalpies are shifted within the spread of published
compilations, so an agent can ask not just for a number but for how
much to trust it.

## Quick start (browser, no install)

A self-contained HTML calculator computes every descriptor, applies all
six rules, runs the Miedema decompositions, and covers the oxide mode,
entirely client-side. Two equivalent paths:

- Open the hosted site: **<https://dfieser.github.io/hea-bench/>**. The
  page is the calculator.
- Or clone the repo and open `web/index.html` — no install, no
  terminal, no server.

The calculator ships its own documentation: a **Theory** view deriving
every alloy and oxide formula with citations, a grouped, filterable
**Equations** reference, and a grouped **References** bibliography.
Deep links open a view directly (`index.html#theory`,
`#equations`, `#refs`). The parity-critical math lives in
`web/hea-calculator-core.js` and is regression-checked against Python
by the two parity test suites.

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
│   ├── oxides/          HEO module: families, oxidation-state solver,
│   │                    Shannon radii (94 elements, vendored from pymatgen)
│   ├── composition.py   formula parser, normalizer
│   ├── constants.py     R = 8.314
│   └── cli.py           command-line entry point
├── tests/               unit tests + BOTH Python↔JS parity suites
├── web/                 landing page + self-contained calculator (+ MathJax)
├── src-tauri/           native desktop wrapper (Rust/Tauri)
├── examples/            Cantor-alloy and oxides walkthroughs (.py + .ipynb)
└── pyproject.toml
```

## Development

```bash
git clone https://github.com/dfieser/hea-bench
cd hea-bench
pip install -e ".[dev]"
python -m pytest tests/ -q          # includes the Python↔JS parity test (needs Node)
```

The HTML calculator (`web/index.html` over
`web/hea-calculator-core.js`) is an independent JavaScript
implementation of the same descriptors and rules. When you modify the
Python descriptor code, update the JS core to match and re-run
`tests/test_web_parity.py` and `tests/test_web_oxides_parity.py` so the
surfaces don't drift. The element data tables inside the JS core are
generated from the Python library by `tests/data/_sync_js_tables.py`
and `tests/data/_sync_js_oxide_tables.py` — regenerate, never
hand-edit.

## License

[MIT](./LICENSE). The vendored
[matminer Miedema data files](./src/hea_bench/descriptors/data/) remain
under their upstream BSD-3-Clause license, preserved at
[`descriptors/data/LICENSE.matminer.txt`](./src/hea_bench/descriptors/data/LICENSE.matminer.txt).

## Contributing and support

Contributions and bug reports are welcome. See
[CONTRIBUTING.md](./CONTRIBUTING.md) for development setup and the
testing convention. To report a bug or ask a question, open a GitHub
issue; for direct contact, email the maintainer at `davjfies@gmail.com`.
Participation is governed by the [Code of Conduct](./CODE_OF_CONDUCT.md).

## Citation

If you use hea-bench in your work, please cite the paper that
describes it:

> Fieser, D.; Dewanjee, U.; Hu, A. HEA-Bench: An AI-Agent-Optimized
> Calculator of High-Entropy Alloy and Oxide Descriptors and
> Phase-Prediction Rules. *Materials* **2026**, *19*, 3075.
> <https://doi.org/10.3390/ma19143075>

```bibtex
@article{ma19143075,
  author         = {Fieser, David and Dewanjee, Unmanaa and Hu, Anming},
  title          = {{HEA-Bench}: An {AI}-Agent-Optimized Calculator of High-Entropy Alloy and Oxide Descriptors and Phase-Prediction Rules},
  journal        = {Materials},
  volume         = {19},
  year           = {2026},
  number         = {14},
  article-number = {3075},
  issn           = {1996-1944},
  doi            = {10.3390/ma19143075},
  url            = {https://www.mdpi.com/1996-1944/19/14/3075},
}
```

Machine-readable metadata, including this preferred citation, is in
[`CITATION.cff`](./CITATION.cff) (GitHub's "Cite this repository"
button uses it). To reference the exact software version you used,
additionally cite the Zenodo archive: the concept DOI
[10.5281/zenodo.20346287](https://doi.org/10.5281/zenodo.20346287)
always resolves to the latest version.

When citing hea-bench, please also cite the primary sources for the
parametrizations it implements: de Boer et al. 1988 for the Miedema
model, the rule papers (Yeh 2004, Zhang 2008, Guo–Liu 2011, Yang–Zhang
2012, King 2016, Ye 2015), the oxide primaries (Shannon 1976,
Goldschmidt 1926, Bartel 2019, Spiridigliozzi 2021, Subramanian 1983),
matminer for the vendored pair table, and pymatgen for the
Shannon-radius digitization. The full grouped bibliography is in the
calculator's References view.

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
