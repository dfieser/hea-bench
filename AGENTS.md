# AGENTS.md

Machine-oriented usage guide for `hea-bench`. If you are an AI coding
agent integrating this library into another project, read this first.
It tells you the public API, exact return types and units, the
fastest path to each common task, and the mistakes to avoid. Every
snippet here is copy-pasteable and was checked against the shipped
code.

> **Editing this repo's own docs (or this file)?** Follow the writing
> rule in [CONTRIBUTING.md](./CONTRIBUTING.md): minimize jargon and
> explain any necessary term inline in plain language, and always state
> what a number is and its units. Don't defer to a glossary.

## What this is

`hea-bench` is an open, interpretable **calculator** of the standard
high-entropy-alloy (HEA) thermodynamic and geometric descriptors plus
the canonical empirical **phase-prediction rules**. Every quantity is a
transparent closed-form expression over a curated element-property
table — no fitted model, no black box.

One calculation core, three surfaces:

1. **Python library + CLI** — this package (`pip install hea-bench`).
2. **Zero-install browser app** — `web/calculator.html` (hosted at
   <https://dfieser.github.io/hea-bench/>, where `web/index.html` is the
   landing page).
3. **Native desktop app** — a single offline executable that wraps the
   browser app via Tauri.
4. **MCP server** — `pip install "hea-bench[mcp]"` then run
   `hea-bench-mcp` (stdio). Seven deterministic tools over this same
   library: `parse_composition`, batch `alloy_descriptors` /
   `alloy_rules`, `omega_sensitivity` (pair-table robustness check),
   `oxide_report`, `element_coverage`, `about`. Every response carries
   units, a citation key per value, and the library version. If you are
   an agent with MCP support, prefer those tools over reimplementing
   the formulas below; if not, the Python API is identical.

The browser/desktop core (`web/hea-calculator-core.js`) is a pure-JS
reimplementation of this library and is **parity-tested** against it on
every binary pair and the canonical multi-element fixtures
(`tests/test_web_parity.py`). The library core is composition-only and
**dependency-free**.

## Install and import

```bash
pip install hea-bench
```

```python
import hea_bench as hb
```

Python >= 3.10. No required runtime dependencies for the core. The
`[dev]` extra adds pytest/ruff only.

## The one mental model you need

A **composition is a plain `dict`** mapping element symbol to amount:
`{"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}`. Amounts do
**not** need to sum to 1; they are normalized internally, so
`{"Al": 1, "Co": 1, "Cr": 1}` is equiatomic AlCoCr. Every descriptor
and rule accepts this dict directly. You rarely need anything else.

## Descriptors (pure functions, exact units)

All take a composition dict (or the result of `parse_formula`) and
return a float.

| Call | Returns | Unit | Notes |
|---|---|---|---|
| `hb.smix(comp)` | mixing entropy | J/(mol·K) | `-R Σ cᵢ ln cᵢ` |
| `hb.delta(comp)` | atomic-size mismatch | **percent** (e.g. 3.164, not 0.03) | |
| `hb.vec(comp)` | valence electron concentration | electrons | linear mean |
| `hb.melting_temperature(comp)` | average melting point | K | rule-of-mixtures |
| `hb.mixing_enthalpy(comp)` | Miedema mixing enthalpy | **kJ/mol** | semi-empirical estimate |
| `hb.omega(comp)` | Yang-Zhang Ω | dimensionless | `Tm·ΔS / \|ΔH\|` |
| `hb.s_excess(comp)` | Mansoori excess entropy | J/(mol·K) | Ye 2015 packing/size term |
| `hb.delta_g_ss(comp, temperature=None)` | solid-solution Gibbs proxy | kJ/mol | defaults to `T = Tm` |
| `hb.delta_g_max(comp)` | most-stable binary-subsystem proxy | kJ/mol | min over `4 cᵢ cⱼ ΔHᵢⱼ` |
| `hb.phi_king(comp, temperature=None)` | King capital `Phi` | dimensionless | defaults to `T = Tm` |
| `hb.phi_ye(comp)` | Ye lowercase `phi` | dimensionless | uses `s_excess(comp)` |
| `hb.delta_chi(comp)` | electronegativity mismatch Δχ | Pauling scale | composition-weighted std |
| `hb.mean_electronegativity(comp)` | mean Pauling electronegativity | Pauling scale | linear mean |

```python
cantor = {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}
hb.smix(cantor)              # 13.381  (= R·ln 5)
hb.delta(cantor)             # 3.164   (percent)
hb.vec(cantor)               # 8.0
hb.melting_temperature(cantor)  # 1801.2 (K)
hb.mixing_enthalpy(cantor)   # -4.16   (kJ/mol)
hb.omega(cantor)             # 5.794
hb.s_excess(cantor)          # 0.318   (J/(mol·K))
hb.delta_g_ss(cantor)        # -28.262 (kJ/mol)
hb.delta_g_max(cantor)       # -8.000  (kJ/mol)  most-negative Miedema pair
hb.phi_king(cantor)          # 3.533
hb.phi_ye(cantor)            # 34.822
hb.delta_chi(cantor)         # 0.138   (Pauling scale)
hb.mean_electronegativity(cantor)  # 1.766
```

These values for the Cantor alloy are pinned in the regression
suite; treat them as the canonical sanity check.

## Parsing formula strings

If you have a string rather than a dict, parse it first. The parser
accepts compact formulas (`"CoCrFeMnNi"`), subscripted formulas
(`"CuCoMn1.75NiFe0.25"`), and space-separated amounts.

```python
comp = hb.parse_formula("CoCrFeMnNi")   # dict-like Composition
hb.normalize(comp)                      # explicit mole-fraction dict
hb.smix(comp)                           # descriptors accept it directly
```

## Rules (classifiers)

```python
from hea_bench.rules import guo_vec, king_phi, yang_omega, ye_phi, yeh_smix, zhang_delta
```

Each module exposes `predict(composition, ...)`, a `DESCRIPTION`
string, and (for the tunable ones) a `DEFAULT_THRESHOLD`. Return
values are strings:

| Rule | Call | Returns one of | Threshold arg |
|---|---|---|---|
| Yeh ΔS_mix | `yeh_smix.predict(comp)` | `"HEA"` / `"MEA"` / `"dilute"` | fixed (descriptive) |
| Zhang δ | `zhang_delta.predict(comp, threshold=6.5)` | `"single-phase"` / `"multi-phase"` | percent, default 6.5 |
| Yang Ω | `yang_omega.predict(comp, threshold=1.1)` | `"single-phase"` / `"multi-phase"` | default 1.1 |
| Guo-Liu VEC | `guo_vec.predict(comp)` | `"FCC"` / `"BCC"` / `"mixed"` | fixed bounds 8.0 / 6.87 |
| King `Phi` | `king_phi.predict(comp, temperature_policy=None, threshold=1.0)` | `"solid_solution"` / `"intermetallic"` | defaults to `T = Tm` |
| Ye `phi` | `ye_phi.predict(comp, threshold=20.0)` | `"solid_solution"` / `"intermetallic"` | default 20.0 |

```python
zhang_delta.predict(cantor)   # 'single-phase'
guo_vec.predict(cantor)       # 'FCC'
yeh_smix.predict(cantor)      # 'HEA'
king_phi.predict(cantor)      # 'solid_solution'
ye_phi.predict(cantor)        # 'solid_solution'
```

**Important:** these rules are weak, semi-empirical screens, not
predictions. They were calibrated on small historical datasets and
generalize poorly; do not treat a rule's output as ground truth.

## The Ω singularity (read this)

`omega = Tm·ΔSmix / |ΔHmix|` diverges as `ΔHmix → 0`. For near-ideal
alloys (`|ΔHmix| ≲ 1–2 kJ/mol`) Ω is extremely sensitive — a few-kJ
change in one pair value, or a different Miedema parametrization, can
move Ω by an order of magnitude. Read Ω **qualitatively** in that
regime; the phase verdict (Ω ≫ 1.1) is robust even when the magnitude
is not. Absolute `ΔHmix` values depend on which Miedema pair table is
used; published compilations disagree most on **Mn**.

## Command line

```bash
hea-bench --version
```

The CLI is a thin version/help wrapper; the Python API above is the
documented surface.

## Data layout

- `src/hea_bench/descriptors/data/` — the vendored element table (37
  elements: radius, melting point, VEC, Pauling electronegativity), the
  matminer-derived Miedema pair-enthalpy table (`pair_enthalpies.tsv`,
  75 elements), and the Miedema elemental-parameter table
  (`miedema_parameters.csv`). These are shipped inside the wheel; no
  fetch step is needed.
- `web/hea-calculator-core.js` — the JS port of the same math + tables,
  used by the browser and desktop apps.

The browser/desktop apps additionally compute the **Miedema
formation-enthalpy decompositions** (compound / solid-solution /
amorphous, split into chemical / elastic / structural / topological
terms) in page-side code; the Python library currently exposes the
descriptor + rule surface above.

## Oxides module (experimental)

`hea_bench.oxides` extends the calculator to **high-entropy oxides**:
closed-form descriptors and weak empirical formability screens for four
structure families (rock salt, perovskite, fluorite, pyrochlore),
computed over vendored Shannon (1976) ionic radii with an explicit
charge-neutrality oxidation-state solver.

```python
from hea_bench import oxides
j14 = oxides.describe_rock_salt({"Mg": 1, "Co": 1, "Ni": 1, "Cu": 1, "Zn": 1})
j14["verdicts"]["entropy"]            # 'high-entropy'
pvk = oxides.describe_perovskite({"Sr": 1}, {"Zr": 1, "Sn": 1, "Ti": 1, "Hf": 1, "Mn": 1})
round(pvk["descriptors"]["goldschmidt_t"], 3)   # 0.979
pvk["verdicts"]["bartel"]             # 'perovskite'  (tau = 3.723 < 4.18)
flu = oxides.describe_fluorite({"Ce": 1, "Zr": 1, "Nd": 1, "Y": 1, "Er": 1}, oxygen=1.7)
round(flu["descriptors"]["radius_sigma"], 4)    # 0.0976  (published value)
```

Each `describe_*` returns one dict: normalized sites, solved oxidation
states, Shannon radii used, descriptors, verdicts, warnings. Entropy
verdicts classify on the most-disordered sublattice (the HEO
convention). The oxide verdicts are screens, not predictions, exactly
like the alloy rules. The JS core ports the same functions
(`describeRockSalt`, `describePerovskite`, `describeFluorite`,
`describePyrochlore`), parity-locked by
`tests/test_web_oxides_parity.py`, and the calculator page exposes them
as an **Oxides mode** (mode switch at the top of the input rail). The
module is deliberately not exported at the `hea_bench` top level;
import it as `from hea_bench import oxides`.

## Coverage limit

The element table covers **37 elements** (alloy surface; the oxides
module has its own 94-element Shannon table). Compositions containing
elements outside it (C, B, the refractory-gas formers, and most
lanthanides) are not fully scorable: `delta`, `smix`-class
geometric/melting descriptors need the element table, while
Miedema-based descriptors fall back to the wider 75-element pair table.
Carbon and boron are deliberately held out (no metallic radius; no
1-atm melting point for carbon).

## Things not to do

- **Do not edit the pinned numbers** in `tests/` to make a test pass.
  Those values are derived from the data and code; a changed number
  means real drift you should explain, not silence.
- **Do not edit `web/hea-calculator-core.js` to diverge from the Python
  library.** The two are parity-locked by `tests/test_web_parity.py`;
  change both together and re-run that test.
- **Do not add elements to the element table** without a citable source
  for the atomic radius, VEC, and melting point. Unsourced values
  corrupt every descriptor that uses them.
- **Do not treat `mixing_enthalpy` as a measured quantity.** It is a
  semi-empirical Miedema estimate with known systematic error for some
  pairs (Mn especially).
- **Do not assume composition fixes phase.** The same composition can
  form different phases depending on processing history; the descriptors
  describe equilibrium driving forces only.

## Verifying your integration

After wiring this in, confirm the Cantor sanity values
(`smix=13.381`, `delta=3.164`, `vec=8.0`, `omega=5.794`,
`s_excess=0.318`, `delta_g_max=-8.000`, `phi_king=3.533`,
`phi_ye=34.822`, `delta_chi=0.1384`) and run the test suite (`python -m pytest -q`). If
those match, your environment is using the canonical implementation
correctly.

## One-shot AI jumpstart (copy-pasteable)

This snippet exercises every public surface and prints a single
machine-readable JSON manifest of the library's state. Run it after
install to verify everything works and to see the surface in one
place.

```python
import json
import hea_bench as hb
from hea_bench.rules import (
    guo_vec, king_phi, yang_omega, ye_phi, yeh_smix, zhang_delta,
)

cantor = {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}
print(json.dumps({
    "version": hb.__version__,
    "cantor_descriptors": {
        "smix":                hb.smix(cantor),
        "delta":               hb.delta(cantor),
        "vec":                 hb.vec(cantor),
        "melting_temperature": hb.melting_temperature(cantor),
        "mixing_enthalpy":     hb.mixing_enthalpy(cantor),
        "omega":               hb.omega(cantor),
        "s_excess":            hb.s_excess(cantor),
        "delta_g_ss":          hb.delta_g_ss(cantor),
        "delta_g_max":         hb.delta_g_max(cantor),
        "phi_king":            hb.phi_king(cantor),
        "phi_ye":              hb.phi_ye(cantor),
        "delta_chi":           hb.delta_chi(cantor),
        "mean_electronegativity": hb.mean_electronegativity(cantor),
    },
    "cantor_rules": {
        "yeh_smix":    yeh_smix.predict(cantor),
        "zhang_delta": zhang_delta.predict(cantor),
        "guo_vec":     guo_vec.predict(cantor),
        "yang_omega":  yang_omega.predict(cantor),
        "king_phi":    king_phi.predict(cantor),
        "ye_phi":      ye_phi.predict(cantor),
    },
}, indent=2))
```

If your numbers match to four decimal places and your rule outputs
are identical strings, your environment is correctly using the
canonical implementation. If not, check (in this order): Python
version >= 3.10, whether you accidentally installed a fork or an
older PyPI snapshot, whether your composition dict uses integer
proportional amounts vs already-normalised mole fractions (both
work, the descriptors normalise internally).
