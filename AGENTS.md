# AGENTS.md

Machine-oriented usage guide for `hea-bench`. If you are an AI coding
agent integrating this library into another project, read this first.
It tells you the public API, exact return types and units, the
fastest path to each common task, and the mistakes to avoid. Every
snippet here is copy-pasteable and was checked against the shipped
code.

> **Editing this repo's own docs (or this file)?** Follow the
> documentation rule in [CONTRIBUTING.md](./CONTRIBUTING.md): define
> every term, symbol, and metric at first use, or link
> [GLOSSARY.md](./GLOSSARY.md) — and always state what a metric is
> measured against (no bare "sensitivity" or "n_eval"). Every term used
> below is defined in the glossary.

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
hb.delta_g_max(cantor)       # -8.000  (kJ/mol)  most-negative Miedema pair
hb.phi_king(cantor)          # 3.533
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
always" (Youden's J of 0.094 and 0.036). Do not treat a rule's output
as ground truth. If you need a confidence-aware answer, evaluate
against the benchmark (below) rather than trusting a single predict().

## Scoring against the benchmark

```python
from hea_bench.evaluate import build_report
report = build_report()                       # textbook rules only
report = build_report(include_phi=True)       # add King Phi + Ye phi
```

`report` is a dict with keys `csv_path`, `n_rows_loaded`, and `rules`.
`report["rules"]` has four base entries (`zhang_delta_6_5`,
`yang_omega_1_1`, `guo_vec_stratified`, `yeh_smix_descriptive`) plus
the two phi entries (`king_phi_1_0`, `ye_phi_20_0`) when
`include_phi=True`. Each binary-rule entry is a dict of statistics:

```python
r = report["rules"]["zhang_delta_6_5"]
r["accuracy"]      # 0.5711
r["sensitivity"]   # 0.989
r["specificity"]   # 0.105
r["youden_j"]      # 0.094
r["accuracy_ci95"] # (low, high) Wilson 95% interval
r["confusion"]     # confusion matrix
# also: n, n_positive_observed, n_negative_observed,
#       true_positive, false_positive, true_negative, false_negative,
#       positive_label
```

What the metrics mean (full definitions in [GLOSSARY.md](./GLOSSARY.md)):
`n` is the number of alloys scored; `accuracy` is the fraction labelled
correctly; `sensitivity` is — of the alloys that truly are the positive
class (`positive_label`, here single-phase) — the fraction predicted
positive; `specificity` is the same for the negative class (multi-phase);
`youden_j` = sensitivity + specificity − 1, where 0 means no better than
guessing and 1 is perfect; `accuracy_ci95` is the Wilson 95% confidence
interval for the accuracy.

## Held-out cross-validation (v1.1)

```python
from hea_bench.evaluate import build_evaluation_report
report = build_evaluation_report(include_phi=True)
```

`build_evaluation_report` returns the in-sample dict above plus three
held-out sections, all under stratified 5-fold CV (stratified jointly
by phase and source signature):

- `report["holdout_strict_consensus_fixed"]` — held-out at the
  published threshold (no tuning).
- `report["holdout_strict_consensus_tuned"]` — held-out with a
  per-fold threshold chosen by maximising Youden's J on the
  training folds only.
- `report["holdout_double_scored_fixed"]` — conflict rows scored two
  ways (`any_match` and `all_match`) so cross-source uncertainty is
  visible.

Each held-out rule entry has `accuracy_mean`, `accuracy_se`,
`sensitivity_mean`, `sensitivity_se`, `specificity_mean`,
`specificity_se`, `youden_j_mean`, `youden_j_se`, plus
`threshold_mean` and `threshold_se` for the tuned variants. Youden's
J is the right metric to report for tuned rules; J = 0 is the
random baseline regardless of class balance.

## Intermetallic-aware sub-benchmark (v1.1)

```python
from hea_bench.evaluate import build_intermetallic_subbench_report
sub = build_intermetallic_subbench_report()
```

Scores King Phi and Ye phi against Peivaste's 12-class side-channel
label projected to `solid_solution` (BCC, FCC, HCP, BCC+FCC) versus
`intermetallic` (IM, FCC+IM, BCC+IM, BCC+FCC+IM). Amorphous-
containing labels are excluded. 5,930 compositions have usable
ground truth; 5,685 are scorable. Returns:

- `sub["in_sample"]` — King and Ye at their published cutoffs on
  the full sub-benchmark.
- `sub["holdout_fixed"]` — same cutoffs under 5-fold CV.
- `sub["holdout_tuned"]` — per-fold cutoff selected by argmax J on
  training folds.

Headline result: Ye phi has J ≈ +0.19 on the sub-benchmark versus
J ≈ -0.01 on the main benchmark. The fine label restores a real
signal that the coarse multi-phase class hides. King Phi remains
weak on both (J ≈ -0.01 at the published cutoff, J ≈ +0.02 tuned).

## Learned reference baseline (v1.3, optional `[ml]` extra)

`hea_bench.baselines` ships a learned classifier as the quantitative
floor a new method should beat. It needs numpy, so install the extra:
`pip install "hea-bench[ml]"`. Importing the package without numpy is
fine; only fitting requires it.

```python
from hea_bench.baselines import LogisticBaseline, descriptor_vector, evaluate

csv = "data/consolidated/v0.1.0/consolidated.csv"
evaluate(csv, interactions=False)["youden_j"]["mean"]  # ~0.092 (ties best rule)
evaluate(csv, interactions=True)["youden_j"]["mean"]   # ~0.313 (triples it)
```

`evaluate(csv, interactions=False|True, k=5, seed=0)` runs held-out
k-fold scoring under the same stratified split as the rules, returning
`{accuracy, sensitivity, specificity, youden_j}` each as
`{"mean", "se"}`, plus `n_rows`, `n_descriptors`, `interactions`.
`LogisticBaseline(interactions=...)` is the model (`fit` / `predict` /
`predict_proba`); `descriptor_vector(comp)` is the six-feature vector
(size mismatch, VEC, mixing entropy, mixing enthalpy, melting T, Omega
capped at 50). The finding: a linear model ties the best rule
(J ≈ 0.09), but squared + interaction terms triple it (J ≈ 0.31) on
single-vs-multi — the descriptors carry joint signal the single-
threshold rules cannot reach. The core stays dependency-free; only this
module imports numpy.

## Threshold sweeps / ROC

```python
from hea_bench.classifiers.diagnostic_stats import roc_sweep
```

Use this to find the accuracy-optimal or Youden-J-optimal threshold
for a tunable rule. The shipped recalibration finding for the Zhang
rule is J-optimal at δ < 2.6% (vs the canonical 6.5%); reproduce it
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
- `src/hea_bench/descriptors/data/` — vendored elemental table (30
  elements) and the matminer Miedema pair table (75 elements).

## Coverage limit (read before scaling up)

The elemental data table covers **30 elements**, so 90.2% of the
benchmark is scorable by every descriptor. Compositions containing
elements outside the table (C, B, Be, Ca, Sc, and others) will
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
(`smix=13.381`, `delta=3.164`, `vec=8.0`, `omega=5.794`,
`s_excess=0.318`, `delta_g_max=-8.000`, `phi_king=3.533`,
`phi_ye=34.822`) and run the test suite (`python -m pytest -q`, 241
tests). If those match, your environment is using the canonical
implementation correctly.

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

Expected output (truncated):

```json
{
  "version": "1.3.0",
  "cantor_descriptors": {
    "smix": 13.3815...,
    "delta": 3.1643...,
    "vec": 8.0,
    "melting_temperature": 1801.2,
    "mixing_enthalpy": -4.16,
    "omega": 5.7937...,
    "s_excess": 0.3179...,
    "delta_g_ss": -28.2616...,
    "delta_g_max": -8.0,
    "phi_king": 3.5327...,
    "phi_ye": 34.8218...
  },
  "cantor_rules": {
    "yeh_smix": "HEA",
    "zhang_delta": "single-phase",
    "guo_vec": "FCC",
    "yang_omega": "single-phase",
    "king_phi": "solid_solution",
    "ye_phi": "solid_solution"
  }
}
```

If your numbers match to four decimal places and your rule outputs
are identical strings, your environment is correctly using the
canonical implementation. If not, check (in this order): Python
version >= 3.10, whether you accidentally installed a fork or an
older PyPI snapshot, whether your composition dict uses integer
proportional amounts vs already-normalised mole fractions (both
work, the descriptors normalise internally).
