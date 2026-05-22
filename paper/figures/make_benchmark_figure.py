"""Generate the benchmark-overview figure for the hea-bench manuscript.

Two panels, both computed live from the committed v0.1.0
consolidated CSV so the figure cannot drift from the data:
  (a) canonical phase-class distribution of the 7,784 compositions
  (b) cross-source overlap (how many sources back each composition)

Run from the repository root:

    PYTHONPATH=src python paper/figures/make_benchmark_figure.py

Writes paper/figures/benchmark_overview.png.
"""

from __future__ import annotations

import collections
import csv
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
CSV_PATH = REPO_ROOT / "data" / "consolidated" / "v0.1.0" / "consolidated.csv"
OUT_PATH = pathlib.Path(__file__).resolve().parent / "benchmark_overview.png"


def main() -> int:
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    phase = collections.Counter((r["canonical_phase"] or "conflict") for r in rows)
    overlap = collections.Counter(len(r["sources"].split(";")) for r in rows)
    total = len(rows)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.4, 3.6))

    # Panel (a): phase-class distribution.
    phase_order = ["BCC", "FCC", "HCP", "multi-phase", "conflict"]
    phase_vals = [phase.get(k, 0) for k in phase_order]
    colors = ["#1f4e79", "#2e7d32", "#8a6d00", "#7a7a7a", "#962d24"]
    bars1 = ax1.bar(range(len(phase_order)), phase_vals, color=colors, width=0.7)
    ax1.set_xticks(range(len(phase_order)))
    ax1.set_xticklabels(phase_order, rotation=30, ha="right", fontsize=9)
    ax1.set_ylabel("compositions")
    ax1.set_title("(a) Canonical phase class", fontsize=10)
    ax1.bar_label(bars1, fontsize=8, padding=2)
    ax1.set_ylim(0, max(phase_vals) * 1.15)
    ax1.spines[["top", "right"]].set_visible(False)

    # Panel (b): cross-source overlap.
    overlap_keys = [1, 2, 3]
    overlap_labels = ["one\nsource", "two\nsources", "three\nsources"]
    overlap_vals = [overlap.get(k, 0) for k in overlap_keys]
    bars2 = ax2.bar(range(len(overlap_keys)), overlap_vals,
                    color="#1f4e79", width=0.6)
    ax2.set_xticks(range(len(overlap_keys)))
    ax2.set_xticklabels(overlap_labels, fontsize=9)
    ax2.set_ylabel("compositions")
    ax2.set_title("(b) Cross-source overlap", fontsize=10)
    ax2.bar_label(bars2, fontsize=8, padding=2)
    ax2.set_ylim(0, max(overlap_vals) * 1.15)
    ax2.spines[["top", "right"]].set_visible(False)

    fig.suptitle(f"hea-bench v0.1.0 consolidated benchmark "
                 f"({total} unique compositions)", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT_PATH, dpi=200)
    print(f"wrote {OUT_PATH}")
    print(f"  total compositions: {total}")
    print(f"  phase classes: {dict(phase)}")
    print(f"  source overlap: {dict(sorted(overlap.items()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
