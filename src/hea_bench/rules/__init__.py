"""Canonical empirical phase-prediction rules, wrapped as classifiers.

Each rule module exposes a ``predict(composition, ...)`` function and a
module-level ``DESCRIPTION`` string. Rules are deliberately kept simple
and composition-only; the diagnostic-statistics machinery in
:mod:`hea_bench.classifiers.diagnostic_stats` evaluates them against
the consolidated benchmark.

Four rules covered in v0.1.0:

- :mod:`hea_bench.rules.yeh_smix`    — ΔS_mix > 1.5R (Yeh 2004)
- :mod:`hea_bench.rules.zhang_delta` — δ < 6.5% (Zhang 2008)
- :mod:`hea_bench.rules.guo_vec`     — VEC bounds for FCC/BCC (Guo & Liu 2011)
- :mod:`hea_bench.rules.yang_omega`  — Ω > 1.1 (Yang & Zhang 2012)
"""
