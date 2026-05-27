# AGENTS.md

Machine-oriented usage guide for `hea-bench`. If you are an AI coding
agent integrating this library into another project, read this first.
It tells you the public API, exact return types and units, the
fastest path to each common task, and the mistakes to avoid. Every
snippet here is copy-pasteable and was checked against the shipped
code.

## What this library is

`hea-bench` does two separate things:

1. **Descriptors + rules** — pure functions that compute the six
  v0.1.0 canonical high-entropy-alloy (HEA) phase descriptors plus
  the v1.1 thermodynamic extension (`S_E`, `DeltaG_ss`, `DeltaG_max`,
  King `Phi`, Ye `phi`) for a composition, and the corresponding
  empirical phase-prediction rules wrapped as classifiers.
2. **A benchmark** — a versioned, deduplicated dataset of 7,784
   experimentally characterized compositions with per-row provenance,
   plus the machinery to score any rule or model against it with
   diagnostic statistics.

It is composition-only and dependency-free in its core. Use it to
screen candidate alloys, to compute descriptors as features, or as a
fixed reference benchmark to evaluate a new phase-prediction method.

## Install and import

```bash
pip install hea-bench
```

```python
import hea_bench as hb
```

Python >= 3.10. No required runtime dependencies for the core. The
`[data]` and `[dev]` extras add pandas/matplotlib/pytest only.

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
| `hb.omega(comp)` | Yang-Zhang Ω | dimensionless | `Tm·ΔS / |ΔH|` |
| `hb.s_excess(comp)` | Mansoori excess entropy | J/(mol·K) | Ye 2015 packing/size term |
| `hb.delta_g_ss(comp, temperature=None)` | solid-solution Gibbs proxy | kJ/mol | defaults to `T = Tm` |
| `hb.delta_g_max(comp)` | most-stable binary-subsystem proxy | kJ/mol | min over `4 cᵢ cⱼ ΔHᵢⱼ` |
| `hb.phi_king(comp, temperature=None)` | King capital `Phi` | dimensionless | defaults to `T = Tm` |
| `hb.phi_ye(comp)` | Ye lowercase `phi` | dimensionless | uses `s_excess(comp)` |

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
hb.delta_g_max(cantor)       # -1.280  (kJ/mol)
hb.phi_king(cantor)          # 22.079
hb.phi_ye(cantor)            # 34.822
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

**Important:** these rules are weak classifiers. On the consolidated
benchmark both binary rules collapse to "predict single-phase almost
always" (Youden's J of 0.075 and 0.032). Do not treat a rule's output
as ground truth. If you need a confidence-aware answer, evaluate
against the benchmark (below) rather than trusting a single predict().

## Scoring against the benchmark

```python
from hea_bench.evaluate import build_report
report = build_report()
```

`report` is a dict with keys `csv_path`, `n_rows_loaded`, and `rules`.
`report["rules"]` has four entries: `zhang_delta_6_5`,
`yang_omega_1_1`, `guo_vec_stratified`, `yeh_smix_descriptive`. Each
entry is a dict of statistics:

```python
r = report["rules"]["zhang_delta_6_5"]
r["accuracy"]      # 0.5670
r["sensitivity"]   # 0.990
r["specificity"]   # 0.085
r["youden_j"]      # 0.075
r["accuracy_ci95"] # (low, high) Wilson 95% interval
r["confusion"]     # confusion matrix
# also: n, n_positive_observed, n_negative_observed,
#       true_positive, false_positive, true_negative, false_negative,
#       positive_label
```

## Threshold sweeps / ROC

```python
from hea_bench.classifiers.diagnostic_stats import roc_sweep
```

Use this to find the accuracy-optimal or Youden-J-optimal threshold
for a tunable rule. The shipped recalibration finding for the Zhang
rule is J-optimal at δ < 2.5% (vs the canonical 6.5%); reproduce it
rather than hard-coding it.

## Command line

```bash
hea-bench --version
python -m hea_bench.evaluate            # fixed-threshold + held-out reports on v0.1.0 rules
python -m hea_bench.evaluate --include-phi  # add the v1.1 phi rules to those reports
python -m hea_bench.benchmark.coverage  # element-coverage analysis
```

On Windows set `PYTHONIOENCODING=utf-8` before these if the output
contains Greek/math symbols, to avoid a cp1252 encode error.

## Data layout

- `data/consolidated/v0.1.0/consolidated.csv` — the benchmark, 7,784
  rows. Join key is `composition_key`; `canonical_phase` is one of
  BCC/FCC/HCP/multi-phase (blank when sources conflict); `sources` is
  semicolon-separated provenance; `has_conflict` flags the 100
  cross-source disagreements.
- `data/consolidated/v0.1.0/{rule_baselines,coverage_report,manifest}.json`
  — committed outputs, regenerated by the evaluate/coverage modules.
- `data/raw/<source>/` — per-source provenance, licenses, SHA-256s.
- `src/hea_bench/descriptors/data/` — vendored elemental table (24
  elements) and the matminer Miedema pair table (75 elements).

## Coverage limit (read before scaling up)

The elemental data table covers **24 elements**, so 86.7% of the
benchmark is scorable by every descriptor. Compositions containing
elements outside the table (Mg, C, Zn, B, Sn, Re, and others) will
not be fully scorable. Check coverage with
`python -m hea_bench.benchmark.coverage` before assuming a dataset is
fully evaluable.

## Things not to do

- **Do not edit the pinned numbers** in `tests/` to make a test pass.
  Those values are derived from the data and code; a changed number
  means real drift you should explain, not silence.
- **Do not add elements to the elemental table** without a citable
  source for the atomic radius, VEC, and melting point. Unsourced
  values corrupt every descriptor that uses them.
- **Do not treat `mixing_enthalpy` as a measured quantity.** It is a
  semi-empirical Miedema estimate with known systematic error for
  some pairs.
- **Do not assume composition fixes phase.** The benchmark is
  composition-only; the same composition can form different phases
  depending on processing history.

## Verifying your integration

After wiring this in, confirm the Cantor sanity values
(`smix=13.381`, `delta=3.164`, `vec=8.0`, `omega=5.794`, `phi_king=22.079`, `phi_ye=34.822`) and run the
test suite (`python -m pytest -q`, 216 tests). If those match, your
environment is using the canonical implementation correctly.
