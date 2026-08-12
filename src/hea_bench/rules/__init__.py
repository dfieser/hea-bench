"""Canonical empirical phase-prediction rules, wrapped as classifiers.

Each rule module exposes a ``predict(composition, ...)`` function, a
module-level ``DESCRIPTION`` string, and, where the threshold is
tunable, a ``DEFAULT_THRESHOLD``. Rules are deliberately kept simple
and composition-only. To measure any of them against the consolidated
experimental corpus, pass the ``predict`` callable to
:func:`hea_bench.benchmark.evaluate`, which scores it under the paired
interpolative (random-split) and extrapolative (family-grouped)
protocols.

Nine rules ship:

- :mod:`hea_bench.rules.yeh_smix`    - entropy classes (Yeh 2004)
- :mod:`hea_bench.rules.zhang_delta` - delta < 6.5% (Zhang 2008)
- :mod:`hea_bench.rules.guo_vec`     - VEC bounds for FCC/BCC (Guo & Liu 2011)
- :mod:`hea_bench.rules.yang_omega`  - Omega > 1.1 (Yang & Zhang 2012)
- :mod:`hea_bench.rules.king_phi`    - King Phi >= 1.0 (King et al. 2016)
- :mod:`hea_bench.rules.ye_phi`      - Ye phi >= 20.0 (Ye et al. 2015)
- :mod:`hea_bench.rules.senkov_kappa`     - k1 versus k1_cr(T) (Senkov & Miracle 2016)
- :mod:`hea_bench.rules.tsai_sigma`       - sigma-phase VEC window (Tsai et al. 2013)
- :mod:`hea_bench.rules.sheikh_ductility` - RHEA ductility VEC screen (Sheikh et al. 2016)
"""
