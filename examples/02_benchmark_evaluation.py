# %% [markdown]
# # Example 2 — Benchmark evaluation
#
# This notebook reproduces the project's **headline benchmark
# numbers**: the four canonical empirical phase-prediction rules
# evaluated as diagnostic classifiers against the consolidated
# v0.1.0 dataset.
#
# Every number below is **pinned in `tests/test_evaluate.py`** as
# ground truth, so any future code or data change that perturbs them
# also breaks the test suite.

# %% [markdown]
# ## Load the rule baselines
#
# `evaluate.build_report` loads the consolidated benchmark, runs each
# rule against the appropriate subset of alloys, and returns a dict
# with all the diagnostic statistics.

# %%
from hea_bench.evaluate import build_report, format_report

report = build_report()
print(f"benchmark CSV:        {report['csv_path']}")
print(f"non-conflict rows:    {report['n_rows_loaded']}")

# %% [markdown]
# ## Headline numbers — formatted summary

# %%
print(format_report(report))

# %% [markdown]
# ## What the numbers mean
#
# Both binary rules — Zhang δ < 6.5% and Yang Ω > 1.1 — have very
# high sensitivity (they almost never miss a true single-phase
# alloy) but very low specificity (they almost never correctly
# identify a multi-phase alloy). Both have Youden's J close to zero,
# meaning that as classifiers they are barely better than
# always-predict-single-phase. **This is the publishable
# observation:** the canonical rules generalize poorly across the
# broader open HEA literature.
#
# The Guo–Liu VEC rule, evaluated stratified to single-phase
# observations (BCC or FCC only — it was never designed to predict
# *whether* a composition forms single-phase, only *which* crystal
# structure if it does), achieves 66.9% accuracy with a strong FCC
# bias: it catches 92.3% of FCC alloys but only 48.3% of BCC alloys.

# %% [markdown]
# ## Looking at individual rule details

# %%
zhang = report["rules"]["zhang_delta_6_5"]
print(f"Zhang δ < 6.5% rule details:")
print(f"  n evaluated      : {zhang['n']}")
print(f"  true positives   : {zhang['true_positive']}  (predicted single, observed single)")
print(f"  false positives  : {zhang['false_positive']}  (predicted single, observed multi)")
print(f"  true negatives   : {zhang['true_negative']}  (predicted multi,  observed multi)")
print(f"  false negatives  : {zhang['false_negative']}  (predicted multi,  observed single)")
print(f"  ----")
print(f"  accuracy   = {zhang['accuracy']:.3f}  [95% CI {zhang['accuracy_ci95'][0]:.3f}, {zhang['accuracy_ci95'][1]:.3f}]")
print(f"  sensitivity = {zhang['sensitivity']:.3f}")
print(f"  specificity = {zhang['specificity']:.3f}")

# %% [markdown]
# The 6,030 false positives are the story. Most multi-phase alloys
# in the benchmark have δ values *below* 6.5%, so the canonical
# threshold predicts them as single-phase. The rule is well-suited
# to confirm a single-phase candidate but poorly suited to *rule
# out* multi-phase formation.
#
# ## A ROC sweep — what threshold would actually work?
#
# `roc_sweep` lets us try every threshold from 1.0% to 12.0% (in
# 0.1% steps) and see what the best classifier-style trade-off would
# be on this dataset.

# %%
import csv
import pathlib

from hea_bench.classifiers.diagnostic_stats import roc_sweep
from hea_bench.composition import parse_formula
from hea_bench.descriptors.size import delta
from hea_bench.descriptors.data.elemental import covered_elements
from hea_bench.evaluate import _binary_observed

V010 = pathlib.Path(report["csv_path"])
elemental = covered_elements()

delta_values, observations = [], []
with V010.open(newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        canonical = row.get("canonical_phase", "").strip()
        if not canonical:
            continue
        comp = parse_formula(row["composition_key"])
        if not set(comp).issubset(elemental):
            continue
        delta_values.append(delta(comp))
        observations.append(_binary_observed(canonical))

thresholds = [t / 10.0 for t in range(10, 121)]
points = roc_sweep(delta_values, observations, thresholds, "single-phase", positive_below_threshold=True)
best_acc = max(points, key=lambda p: p.accuracy)
best_j   = max(points, key=lambda p: p.youden_j)

print(f"ROC sweep over Zhang δ rule, {len(points)} threshold points evaluated.")
print(f"  best accuracy    : {best_acc.accuracy:.3f} at threshold δ < {best_acc.threshold}%")
print(f"    (sens = {best_acc.sensitivity:.3f}, spec = {best_acc.specificity:.3f})")
print(f"  best Youden's J  : J = {best_j.youden_j:.3f} at threshold δ < {best_j.threshold}%")
print(f"    (sens = {best_j.sensitivity:.3f}, spec = {best_j.specificity:.3f})")
print(f"  canonical 6.5% threshold for reference: J = {next(p.youden_j for p in points if p.threshold == 6.5):.3f}")

# %% [markdown]
# The optimal threshold on this dataset is *much tighter* than the
# canonical 6.5%. The accuracy at the optimum is materially higher
# than at the canonical value, but it's still nowhere near a
# strong classifier — the empirical rule has real but limited
# power to separate single-phase from multi-phase compositions
# across the full open literature.
#
# This kind of recalibration finding is exactly the use that
# `hea-bench` is designed to support.
