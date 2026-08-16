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

from __future__ import annotations

from . import (
    guo_vec,
    king_phi,
    senkov_kappa,
    sheikh_ductility,
    tsai_sigma,
    yang_omega,
    ye_phi,
    yeh_smix,
    zhang_delta,
)

#: Canonical rule name -> verdict function (composition -> verdict
#: string). The three rules whose ``predict`` returns a result object
#: are adapted here so every entry answers with the verdict string,
#: which is what constraint filtering consumes. This is the one place
#: the nine-rule vocabulary lives; the design search, campaigns, and
#: the MCP surface all draw from it.
VERDICT_FUNCTIONS = {
    "yeh_smix": yeh_smix.predict,
    "zhang_delta": zhang_delta.predict,
    "guo_vec": guo_vec.predict,
    "yang_omega": yang_omega.predict,
    "king_phi": king_phi.predict,
    "ye_phi": ye_phi.predict,
    "senkov_kappa": lambda comp: senkov_kappa.predict(comp).verdict,
    "tsai_sigma": lambda comp: tsai_sigma.predict(comp).verdict,
    "sheikh_ductility": lambda comp: sheikh_ductility.predict(comp).verdict,
}

#: Accepted alternative spellings -> canonical rule name. The MCP
#: surface labels the entropy rule ``yeh_entropy`` in its payloads, so
#: anywhere a rule is named by string (design-search rule constraints,
#: campaign constraints) both spellings must resolve to the same rule.
RULE_ALIASES = {"yeh_entropy": "yeh_smix"}


def canonical_rule_name(name: str) -> str:
    """Resolve a rule name or accepted alias to its canonical name."""
    return RULE_ALIASES.get(name, name)
