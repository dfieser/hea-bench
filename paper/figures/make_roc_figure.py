"""Generate the ROC-curve figure for the JOSS paper.

Reproducible figure generation, same philosophy as the example
notebooks: every point comes from running the library against the
committed v0.1.0 benchmark, so the figure cannot drift from the
numbers pinned in the test suite.

Run from the repository root:

    PYTHONPATH=src python paper/figures/make_roc_figure.py

Writes paper/figures/roc_zhang_delta.png.
"""

from __future__ import annotations

import csv
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from hea_bench.classifiers.diagnostic_stats import roc_sweep  # noqa: E402
from hea_bench.composition import parse_formula  # noqa: E402
from hea_bench.descriptors.data.elemental import covered_elements  # noqa: E402
from hea_bench.descriptors.size import delta  # noqa: E402
from hea_bench.evaluate import _binary_observed  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CSV_PATH = REPO_ROOT / "data" / "consolidated" / "v0.1.0" / "consolidated.csv"
OUT_PATH = pathlib.Path(__file__).resolve().parent / "roc_zhang_delta.png"


def collect() -> tuple[list[float], list[str]]:
    """Return (delta values, binary observations) for benchmark
    compositions fully covered by the elemental data table."""
    elemental = covered_elements()
    deltas: list[float] = []
    obs: list[str] = []
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            canonical = (row.get("canonical_phase") or "").strip()
            if not canonical:
                continue
            comp = parse_formula(row["composition_key"])
            if not set(comp).issubset(elemental):
                continue
            deltas.append(delta(comp))
            obs.append(_binary_observed(canonical))
    return deltas, obs


def main() -> int:
    deltas, obs = collect()
    thresholds = [t / 10.0 for t in range(10, 121)]  # 1.0% to 12.0%
    points = roc_sweep(deltas, obs, thresholds, "single-phase",
                       positive_below_threshold=True)

    fpr = [1.0 - p.specificity for p in points]
    tpr = [p.sensitivity for p in points]

    canonical = min(points, key=lambda p: abs(p.threshold - 6.5))
    best_j = max(points, key=lambda p: p.youden_j)

    fig, ax = plt.subplots(figsize=(5.0, 4.4))
    ax.plot(fpr, tpr, color="#1f4e79", lw=1.8, zorder=2,
            label="threshold sweep (1.0 to 12.0 %)")
    ax.plot([0, 1], [0, 1], color="0.6", lw=1.0, ls="--", zorder=1,
            label="no-skill reference")

    ax.scatter([1.0 - canonical.specificity], [canonical.sensitivity],
               s=70, color="#962d24", zorder=3, edgecolor="white",
               label=f"canonical $\\delta<6.5\\%$ ($J={canonical.youden_j:.3f}$)")
    ax.scatter([1.0 - best_j.specificity], [best_j.sensitivity],
               s=70, color="#2e7d32", marker="D", zorder=3, edgecolor="white",
               label=f"optimal $\\delta<{best_j.threshold:.1f}\\%$ ($J={best_j.youden_j:.3f}$)")

    ax.set_xlabel("False positive rate (1 - specificity)")
    ax.set_ylabel("True positive rate (sensitivity)")
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_aspect("equal")
    ax.legend(loc="lower right", fontsize=8, framealpha=0.95)
    ax.grid(True, color="0.92", lw=0.6)
    fig.tight_layout()
    fig.savefig(OUT_PATH, dpi=200)
    print(f"wrote {OUT_PATH}")
    print(f"  n points: {len(points)}")
    print(f"  canonical 6.5%: sens={canonical.sensitivity:.3f} "
          f"spec={canonical.specificity:.3f} J={canonical.youden_j:.3f}")
    print(f"  optimal {best_j.threshold:.1f}%: sens={best_j.sensitivity:.3f} "
          f"spec={best_j.specificity:.3f} J={best_j.youden_j:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
