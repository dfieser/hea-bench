"""Canonical empirical phase-prediction rules, wrapped as classifiers.

Each rule module exposes a ``predict(composition, ...)`` function and a
module-level ``DESCRIPTION`` string. Rules are deliberately kept simple
and composition-only; the diagnostic-statistics machinery in
:mod:`hea_bench.classifiers.diagnostic_stats` evaluates them against
the consolidated benchmark.

Four rules shipped in v0.1.0:

- :mod:`hea_bench.rules.yeh_smix`    — ΔS_mix > 1.5R (Yeh 2004)
- :mod:`hea_bench.rules.zhang_delta` — δ < 6.5% (Zhang 2008)
- :mod:`hea_bench.rules.guo_vec`     — VEC bounds for FCC/BCC (Guo & Liu 2011)
- :mod:`hea_bench.rules.yang_omega`  — Ω > 1.1 (Yang & Zhang 2012)

Two additional rules are under v1.1 development on the phi branch:

- :mod:`hea_bench.rules.king_phi`    — King Φ ≥ 1.0 (King et al. 2016)
- :mod:`hea_bench.rules.ye_phi`      — Ye φ ≥ 20.0 (Ye et al. 2015)
"""
