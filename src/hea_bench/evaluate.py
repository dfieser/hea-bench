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

    python -m hea_bench.evaluate                                # in-sample + held-out summary
    python -m hea_bench.evaluate --include-phi                  # include v1.1 phi rules
    python -m hea_bench.evaluate --single-split                 # quick 70/30 reproduction mode
    python -m hea_bench.evaluate --in-sample-only --include-phi # legacy v1.1 artifact

Writes ``evaluation_report.json`` by default, or
``evaluation_report_v1.1.json`` when ``--include-phi`` is used.
Use ``--in-sample-only`` to write the legacy ``rule_baselines*.json``
artifacts instead.
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import sys
from collections import Counter
from collections.abc import Iterable

from .benchmark.taxonomy import binary_observed as _binary_observed
from .benchmark.taxonomy import phi_observed as _phi_observed
from .classifiers.diagnostic_stats import BinaryStats, evaluate_binary
from .composition import parse_formula
from .descriptors.data.elemental import covered_elements as _elemental_covered
from .descriptors.data.pair_enthalpies import covered_elements as _pair_covered
from .evaluation import (
    build_binary_holdout_report,
    build_binary_single_split_report,
    build_double_scored_binary_holdout_report,
    build_double_scored_binary_single_split_report,
    build_tuned_binary_holdout_report,
    build_tuned_binary_single_split_report,
)
from .rules import guo_vec, king_phi, yang_omega, ye_phi, yeh_smix, zhang_delta

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_DEFAULT_CSV = _REPO_ROOT / "data" / "consolidated" / "v0.1.0" / "consolidated.csv"
_DEFAULT_JSON = _DEFAULT_CSV.parent / "rule_baselines.json"
_DEFAULT_V11_JSON = _DEFAULT_CSV.parent / "rule_baselines_v1.1.json"
_DEFAULT_EVALUATION_JSON = _DEFAULT_CSV.parent / "evaluation_report.json"
_DEFAULT_EVALUATION_V11_JSON = _DEFAULT_CSV.parent / "evaluation_report_v1.1.json"
_DEFAULT_HOLDOUT_MODE = "kfold"
_DEFAULT_HOLDOUT_SEED = 0
_DEFAULT_SINGLE_SPLIT_TEST_FRACTION = 0.3

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


def evaluate_king_phi(
    rows: list[dict],
    threshold: float = king_phi.DEFAULT_THRESHOLD,
    temperature_policy: float | None = None,
) -> BinaryStats:
    needed = _elemental_covered() & _pair_covered()
    preds: list[str] = []
    obs: list[str] = []
    for r in rows:
        comp = r["_composition"]
        if not set(comp).issubset(needed):
            continue
        preds.append(
            king_phi.predict(
                comp,
                threshold=threshold,
                temperature_policy=temperature_policy,
            )
        )
        obs.append(_phi_observed(r["canonical_phase"]))
    return evaluate_binary(preds, obs, positive_label="solid_solution")


def evaluate_ye_phi(
    rows: list[dict],
    threshold: float = ye_phi.DEFAULT_THRESHOLD,
) -> BinaryStats:
    needed = _elemental_covered() & _pair_covered()
    preds: list[str] = []
    obs: list[str] = []
    for r in rows:
        comp = r["_composition"]
        if not set(comp).issubset(needed):
            continue
        preds.append(ye_phi.predict(comp, threshold=threshold))
        obs.append(_phi_observed(r["canonical_phase"]))
    return evaluate_binary(preds, obs, positive_label="solid_solution")


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


def build_report(csv_path: pathlib.Path = _DEFAULT_CSV, *, include_phi: bool = False) -> dict:
    rows = _load_benchmark(csv_path)
    zhang = evaluate_zhang_delta(rows)
    yang = evaluate_yang_omega(rows)
    guo = evaluate_guo_vec_stratified(rows)
    yeh = evaluate_yeh_smix(rows)
    rules = {
        "zhang_delta_6_5":   _binary_stats_to_dict(zhang),
        "yang_omega_1_1":    _binary_stats_to_dict(yang),
        "guo_vec_stratified": guo,
        "yeh_smix_descriptive": yeh,
    }
    if include_phi:
        rules["king_phi_1_0"] = _binary_stats_to_dict(evaluate_king_phi(rows))
        rules["ye_phi_20_0"] = _binary_stats_to_dict(evaluate_ye_phi(rows))
    return {
        "csv_path": str(csv_path),
        "n_rows_loaded": len(rows),
        "rules": rules,
    }


def build_evaluation_report(
    csv_path: pathlib.Path = _DEFAULT_CSV,
    *,
    include_phi: bool = False,
    holdout_mode: str = _DEFAULT_HOLDOUT_MODE,
    seed: int = _DEFAULT_HOLDOUT_SEED,
    test_fraction: float = _DEFAULT_SINGLE_SPLIT_TEST_FRACTION,
) -> dict:
    """Build the CLI-facing evaluation report with in-sample and held-out views."""
    if holdout_mode not in {"kfold", "single_split"}:
        raise ValueError("holdout_mode must be 'kfold' or 'single_split'")

    in_sample = build_report(csv_path, include_phi=include_phi)

    if holdout_mode == "kfold":
        holdout_fixed = build_binary_holdout_report(csv_path, include_phi=include_phi, seed=seed)
        holdout_double_scored = build_double_scored_binary_holdout_report(
            csv_path,
            include_phi=include_phi,
            seed=seed,
        )
        holdout_tuned = build_tuned_binary_holdout_report(csv_path, include_phi=include_phi, seed=seed)
    else:
        holdout_fixed = build_binary_single_split_report(
            csv_path,
            include_phi=include_phi,
            test_fraction=test_fraction,
            seed=seed,
        )
        holdout_double_scored = build_double_scored_binary_single_split_report(
            csv_path,
            include_phi=include_phi,
            test_fraction=test_fraction,
            seed=seed,
        )
        holdout_tuned = build_tuned_binary_single_split_report(
            csv_path,
            include_phi=include_phi,
            test_fraction=test_fraction,
            seed=seed,
        )

    return {
        "csv_path": str(csv_path),
        "holdout_mode": holdout_mode,
        "seed": seed,
        "test_fraction": test_fraction if holdout_mode == "single_split" else None,
        "in_sample": in_sample,
        "holdout_strict_consensus_fixed": holdout_fixed,
        "holdout_double_scored_fixed": holdout_double_scored,
        "holdout_strict_consensus_tuned": holdout_tuned,
    }


def _rule_title(rule_key: str) -> str:
    titles = {
        "zhang_delta_6_5": "Zhang δ < 6.5%",
        "yang_omega_1_1": "Yang Ω > 1.1",
        "king_phi_1_0": "King Φ > 1.0",
        "ye_phi_20_0": "Ye φ > 20.0",
        "zhang_delta_tuned": "Zhang δ tuned",
        "yang_omega_tuned": "Yang Ω tuned",
        "king_phi_tuned": "King Φ tuned",
        "ye_phi_tuned": "Ye φ tuned",
    }
    return titles.get(rule_key, rule_key)


def _append_holdout_binary_section(out: list[str], title: str, report: dict, *, tuned: bool = False) -> None:
    if report["protocol"].endswith("kfold") or report["protocol"].endswith("kfold_tuned"):
        context = f"protocol={report['protocol']}  k={report['k']}  seed={report['seed']}"
    else:
        context = (
            f"protocol={report['protocol']}  test_fraction={report['test_fraction']:.0%}"
            f"  seed={report['seed']}"
        )
    out.append(f"=== {title} ({context}) ===")
    for rule_key, summary in report["rules"].items():
        out.append(
            f"  {_rule_title(rule_key)}: accuracy = {summary['accuracy_mean']:.1%}"
            f"  sensitivity = {summary['sensitivity_mean']:.1%}"
            f"  specificity = {summary['specificity_mean']:.1%}"
            f"  Youden's J = {summary['youden_j_mean']:.3f}"
        )
        if tuned:
            out.append(
                f"    threshold mean = {summary['threshold_mean']:.3f}"
                f"  default = {summary['default_threshold']:.3f}"
            )
    out.append("")


def _append_holdout_double_scored_section(out: list[str], report: dict) -> None:
    if report["protocol"].endswith("kfold"):
        context = f"protocol={report['protocol']}  k={report['k']}  seed={report['seed']}"
    else:
        context = (
            f"protocol={report['protocol']}  test_fraction={report['test_fraction']:.0%}"
            f"  seed={report['seed']}"
        )
    out.append(f"=== Held-out double-scored fixed thresholds ({context}) ===")
    for rule_key, summary in report["rules"].items():
        any_match = summary["any_match"]
        all_match = summary["all_match"]
        out.append(
            f"  {_rule_title(rule_key)}: any-match accuracy = {any_match['accuracy_mean']:.1%}"
            f"  Youden's J = {any_match['youden_j_mean']:.3f}"
        )
        out.append(
            f"    all-match accuracy = {all_match['accuracy_mean']:.1%}"
            f"  Youden's J = {all_match['youden_j_mean']:.3f}"
        )
    out.append("")


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

    if "king_phi_1_0" in report["rules"]:
        k = report["rules"]["king_phi_1_0"]
        out.append("--- King Φ > 1.0 (binary solid_solution vs intermetallic; default T=T_m) ---")
        out.append(f"  n_evaluated = {k['n']}   accuracy = {k['accuracy']:.1%}  "
                   f"[95% CI {k['accuracy_ci95'][0]:.1%}, {k['accuracy_ci95'][1]:.1%}]")
        out.append(f"  sensitivity (solid_solution) = {k['sensitivity']:.1%}")
        out.append(f"  specificity (intermetallic)  = {k['specificity']:.1%}")
        out.append(f"  Youden's J = {k['youden_j']:.3f}")
        out.append("")

    if "ye_phi_20_0" in report["rules"]:
        p = report["rules"]["ye_phi_20_0"]
        out.append("--- Ye φ > 20.0 (binary solid_solution vs intermetallic) ---")
        out.append(f"  n_evaluated = {p['n']}   accuracy = {p['accuracy']:.1%}  "
                   f"[95% CI {p['accuracy_ci95'][0]:.1%}, {p['accuracy_ci95'][1]:.1%}]")
        out.append(f"  sensitivity (solid_solution) = {p['sensitivity']:.1%}")
        out.append(f"  specificity (intermetallic)  = {p['specificity']:.1%}")
        out.append(f"  Youden's J = {p['youden_j']:.3f}")
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


def format_evaluation_report(report: dict) -> str:
    out = [format_report(report["in_sample"]), ""]
    _append_holdout_binary_section(
        out,
        "Held-out strict-consensus fixed thresholds",
        report["holdout_strict_consensus_fixed"],
    )
    _append_holdout_double_scored_section(out, report["holdout_double_scored_fixed"])
    _append_holdout_binary_section(
        out,
        "Held-out strict-consensus tuned thresholds",
        report["holdout_strict_consensus_tuned"],
        tuned=True,
    )
    return "\n".join(out).rstrip()


def _write_report(report: dict, output_path: pathlib.Path) -> None:
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def main(argv: Iterable[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-phi",
        action="store_true",
        help="include the v1.1 phi-family rules in the report",
    )
    parser.add_argument(
        "--in-sample-only",
        action="store_true",
        help="write only the legacy in-sample rule_baselines artifact",
    )
    parser.add_argument(
        "--single-split",
        action="store_true",
        help="use the documented 70/30 stratified single split instead of 5-fold CV",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=_DEFAULT_HOLDOUT_SEED,
        help="random seed for held-out split assignment (default: 0)",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        help="write the JSON report to this path instead of the default location",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.in_sample_only:
        report = build_report(include_phi=args.include_phi)
        print(format_report(report))
        out_json = args.output or (_DEFAULT_V11_JSON if args.include_phi else _DEFAULT_JSON)
    else:
        holdout_mode = "single_split" if args.single_split else "kfold"
        report = build_evaluation_report(
            include_phi=args.include_phi,
            holdout_mode=holdout_mode,
            seed=args.seed,
        )
        print(format_evaluation_report(report))
        out_json = args.output or (
            _DEFAULT_EVALUATION_V11_JSON if args.include_phi else _DEFAULT_EVALUATION_JSON
        )
    _write_report(report, out_json)
    print(f"\nwrote {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
