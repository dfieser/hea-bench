"""Run the empirical phase-prediction rules against the consolidated
benchmark and report diagnostic statistics.

This module is the **scientific output** of the project: it produces
the headline numbers the paper will cite. Each rule from
:mod:`hea_bench.rules` is evaluated as a classifier against the
consolidated v<version> benchmark's `canonical_phase` ground truth,
with appropriate label mappings:

- **Zhang δ rule** (binary: single-phase / multi-phase)
  ground truth: single-phase = {BCC, FCC, HCP}, multi = multi-phase
- **Yang Ω rule** (binary: single-phase / multi-phase) — same mapping
- **Guo–Liu VEC rule** (3-class: FCC / BCC / mixed) — stratified
  evaluation restricting observations to {BCC, FCC} for the
  meaningful single-phase-conditional accuracy
- **Yeh ΔS_mix rule** (descriptive) — reports fraction in
  HEA / MEA / dilute bins

Run as a module:

    python -m hea_bench.evaluate                 # default: v0.1.0

Writes ``rule_baselines.json`` alongside the consolidated CSV.
"""

from __future__ import annotations

import csv
import json
import pathlib
import sys
from collections import Counter
from collections.abc import Iterable

from .classifiers.diagnostic_stats import BinaryStats, evaluate_binary
from .composition import parse_formula
from .descriptors.data.elemental import covered_elements as _elemental_covered
from .descriptors.data.pair_enthalpies import covered_elements as _pair_covered
from .rules import guo_vec, yang_omega, yeh_smix, zhang_delta

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_DEFAULT_CSV = _REPO_ROOT / "data" / "consolidated" / "v0.1.0" / "consolidated.csv"

# Ground-truth mapping from canonical 4-class taxonomy to binary
# {single-phase, multi-phase} for the δ and Ω rules.
_SINGLE_PHASE_CLASSES = frozenset({"BCC", "FCC", "HCP"})


def _binary_observed(canonical_phase: str) -> str | None:
    """Map canonical 4-class label to binary single/multi. Returns
    ``None`` for conflict rows (canonical_phase blank)."""
    if not canonical_phase:
        return None
    return "single-phase" if canonical_phase in _SINGLE_PHASE_CLASSES else "multi-phase"


def _load_benchmark(csv_path: pathlib.Path) -> list[dict]:
    """Load each consolidated row and parse its composition. Drops
    conflict rows (no canonical_phase) since they aren't ground truth."""
    out: list[dict] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            canonical = row.get("canonical_phase", "").strip()
            if not canonical:
                continue
            try:
                comp = parse_formula(row["composition_key"])
            except (KeyError, ValueError):
                continue
            row["_composition"] = comp
            row["_binary_observed"] = _binary_observed(canonical)
            out.append(row)
    return out


def evaluate_zhang_delta(rows: list[dict], threshold: float = zhang_delta.DEFAULT_THRESHOLD) -> BinaryStats:
    elemental = _elemental_covered()
    preds: list[str] = []
    obs: list[str] = []
    for r in rows:
        comp = r["_composition"]
        if not set(comp).issubset(elemental):
            continue
        preds.append(zhang_delta.predict(comp, threshold=threshold))
        obs.append(r["_binary_observed"])
    return evaluate_binary(preds, obs, positive_label="single-phase")


def evaluate_yang_omega(rows: list[dict], threshold: float = yang_omega.DEFAULT_THRESHOLD) -> BinaryStats:
    needed = _elemental_covered() & _pair_covered()  # Ω needs both
    preds: list[str] = []
    obs: list[str] = []
    for r in rows:
        comp = r["_composition"]
        if not set(comp).issubset(needed):
            continue
        preds.append(yang_omega.predict(comp, threshold=threshold))
        obs.append(r["_binary_observed"])
    return evaluate_binary(preds, obs, positive_label="single-phase")


def evaluate_guo_vec_stratified(rows: list[dict]) -> dict:
    """VEC rule restricted to single-phase observed alloys. Returns
    a dict of:
        accuracy (FCC|BCC predicted matches FCC|BCC observed)
        FCC sensitivity, BCC sensitivity
        n_eval (single-phase rows scorable by VEC)
        confusion {(pred, obs): count}
    """
    elemental = _elemental_covered()
    confusion: Counter[tuple[str, str]] = Counter()
    correct = 0
    n_eval = 0
    n_fcc_obs = n_bcc_obs = 0
    tp_fcc = tp_bcc = 0

    for r in rows:
        canonical = r["canonical_phase"]
        if canonical not in ("FCC", "BCC"):
            continue
        comp = r["_composition"]
        if not set(comp).issubset(elemental):
            continue
        pred = guo_vec.predict(comp)
        confusion[(pred, canonical)] += 1
        n_eval += 1
        if pred == canonical:
            correct += 1
        if canonical == "FCC":
            n_fcc_obs += 1
            if pred == "FCC":
                tp_fcc += 1
        else:
            n_bcc_obs += 1
            if pred == "BCC":
                tp_bcc += 1

    return {
        "n_eval": n_eval,
        "accuracy": correct / n_eval if n_eval else 0.0,
        "fcc_sensitivity": tp_fcc / n_fcc_obs if n_fcc_obs else 0.0,
        "bcc_sensitivity": tp_bcc / n_bcc_obs if n_bcc_obs else 0.0,
        "n_fcc_observed": n_fcc_obs,
        "n_bcc_observed": n_bcc_obs,
        "confusion": {f"{p}->{o}": c for (p, o), c in confusion.items()},
    }


def evaluate_yeh_smix(rows: list[dict]) -> dict:
    """Descriptive: fraction in each HEA/MEA/dilute bin."""
    bins: Counter[str] = Counter()
    n = 0
    for r in rows:
        comp = r["_composition"]
        bins[yeh_smix.predict(comp)] += 1
        n += 1
    return {
        "n": n,
        "fraction_HEA":    bins["HEA"] / n if n else 0.0,
        "fraction_MEA":    bins["MEA"] / n if n else 0.0,
        "fraction_dilute": bins["dilute"] / n if n else 0.0,
        "bins": dict(bins),
    }


def _binary_stats_to_dict(s: BinaryStats) -> dict:
    """Serialize BinaryStats for the JSON report."""
    return {
        "n": s.n,
        "n_positive_observed": s.n_positive_observed,
        "n_negative_observed": s.n_negative_observed,
        "true_positive":  s.true_positive,
        "false_positive": s.false_positive,
        "true_negative":  s.true_negative,
        "false_negative": s.false_negative,
        "accuracy":     s.accuracy,
        "sensitivity":  s.sensitivity,
        "specificity":  s.specificity,
        "youden_j":     s.youden_j,
        "accuracy_ci95": list(s.accuracy_ci95),
        "positive_label": s.positive_label,
        "confusion": {f"{p}->{o}": c for (p, o), c in s.confusion.items()},
    }


def build_report(csv_path: pathlib.Path = _DEFAULT_CSV) -> dict:
    rows = _load_benchmark(csv_path)
    zhang = evaluate_zhang_delta(rows)
    yang = evaluate_yang_omega(rows)
    guo = evaluate_guo_vec_stratified(rows)
    yeh = evaluate_yeh_smix(rows)
    return {
        "csv_path": str(csv_path),
        "n_rows_loaded": len(rows),
        "rules": {
            "zhang_delta_6_5":   _binary_stats_to_dict(zhang),
            "yang_omega_1_1":    _binary_stats_to_dict(yang),
            "guo_vec_stratified": guo,
            "yeh_smix_descriptive": yeh,
        },
    }


def format_report(report: dict) -> str:
    out: list[str] = []
    n = report["n_rows_loaded"]
    out.append(f"=== Rule baselines on {report['csv_path']} ===")
    out.append(f"compositions with canonical_phase (non-conflict): {n}")
    out.append("")

    z = report["rules"]["zhang_delta_6_5"]
    out.append("--- Zhang δ < 6.5% (binary single vs multi) ---")
    out.append(f"  n_evaluated = {z['n']}   accuracy = {z['accuracy']:.1%}  "
               f"[95% CI {z['accuracy_ci95'][0]:.1%}, {z['accuracy_ci95'][1]:.1%}]")
    out.append(f"  sensitivity (single-phase) = {z['sensitivity']:.1%}")
    out.append(f"  specificity (multi-phase)  = {z['specificity']:.1%}")
    out.append(f"  Youden's J = {z['youden_j']:.3f}")
    out.append("")

    y = report["rules"]["yang_omega_1_1"]
    out.append("--- Yang Ω > 1.1 (binary single vs multi) ---")
    out.append(f"  n_evaluated = {y['n']}   accuracy = {y['accuracy']:.1%}  "
               f"[95% CI {y['accuracy_ci95'][0]:.1%}, {y['accuracy_ci95'][1]:.1%}]")
    out.append(f"  sensitivity (single-phase) = {y['sensitivity']:.1%}")
    out.append(f"  specificity (multi-phase)  = {y['specificity']:.1%}")
    out.append(f"  Youden's J = {y['youden_j']:.3f}")
    out.append("")

    g = report["rules"]["guo_vec_stratified"]
    out.append("--- Guo–Liu VEC (stratified to FCC|BCC observed) ---")
    out.append(f"  n_evaluated = {g['n_eval']}   accuracy = {g['accuracy']:.1%}")
    out.append(f"  FCC sensitivity (n={g['n_fcc_observed']}): {g['fcc_sensitivity']:.1%}")
    out.append(f"  BCC sensitivity (n={g['n_bcc_observed']}): {g['bcc_sensitivity']:.1%}")
    out.append("")

    s = report["rules"]["yeh_smix_descriptive"]
    out.append(f"--- Yeh ΔS_mix bins (descriptive, n={s['n']}) ---")
    out.append(f"  HEA    (>1.5R): {s['fraction_HEA']:.1%}")
    out.append(f"  MEA    (R-1.5R): {s['fraction_MEA']:.1%}")
    out.append(f"  dilute (<R):    {s['fraction_dilute']:.1%}")
    return "\n".join(out)


def main(argv: Iterable[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    report = build_report()
    print(format_report(report))
    out_json = pathlib.Path(report["csv_path"]).parent / "rule_baselines.json"
    out_json.write_text(json.dumps(report, indent=2))
    print(f"\nwrote {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
