"""Run the baseline zoo and write the static results table.

Four baselines, each scored under both frozen splits:

``majority-class``
    The floor. Predicts the most common training label.
``rule:*``
    The canonical empirical screens already in this package, used as
    published, with no fitting. Having no fitted parameters, they have
    no training rows to sit close to, so their grouped and random
    columns should agree; see the note in ``hea_bench.benchmark.evaluate``.
``random-forest`` and ``gradient-boosting``
    Fitted on this package's own descriptors, so the comparison is
    against the same physics the rules use rather than against a
    different feature set.

Run from the repository root:

    PYTHONPATH=src python tools/benchmark_baselines.py

Needs scikit-learn, which the library core deliberately does not depend
on; install the pinned version with ``pip install -e .[benchmark]``.
Writes docs/benchmark-baselines.md and prints each report.
"""

from __future__ import annotations

import json
import pathlib
import platform
import sys
from collections import Counter
from collections.abc import Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from hea_bench.benchmark import (  # noqa: E402
    MajorityClass,
    descriptor_matrix,
    evaluate,
    finite_descriptor_indices,
    load_benchmark,
)
from hea_bench.composition import Composition  # noqa: E402
from hea_bench.rules import guo_vec, yang_omega, zhang_delta  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_MD = REPO_ROOT / "docs" / "benchmark-baselines.md"
OUT_JSON = REPO_ROOT / "docs" / "benchmark-baselines.json"

# Fixed so a rerun reproduces the table. Any change here changes every
# number below it.
FOREST_SEED = 0


#: Composition (as a sorted item tuple) -> descriptor row. Every fold of
#: every scheme of every fitted model featurizes the same ~7k corpus
#: compositions; computing each row once cuts minutes from a run without
#: touching a single value.
_MATRIX_CACHE: dict[tuple, list[float]] = {}


def _cached_matrix(compositions: Sequence[Composition]) -> list[list[float]]:
    rows = []
    for comp in compositions:
        key = tuple(sorted(comp.items()))
        row = _MATRIX_CACHE.get(key)
        if row is None:
            row = descriptor_matrix([comp])[0]
            _MATRIX_CACHE[key] = row
        rows.append(row)
    return rows


class DescriptorModel:
    """Adapter fitting any scikit-learn classifier on this package's descriptors."""

    def __init__(self, estimator, name: str) -> None:
        self.estimator = estimator
        self.name = name

    def fit(self, compositions: Sequence[Composition], labels: Sequence[str]) -> DescriptorModel:
        self.estimator.fit(_cached_matrix(compositions), list(labels))
        return self

    def predict(self, compositions: Sequence[Composition]) -> list[str]:
        return list(self.estimator.predict(_cached_matrix(compositions)))


def _rule_single_vs_multi(rule) -> object:
    def predict(composition: Composition) -> str:
        return rule.predict(composition)

    predict.__name__ = f"rule:{rule.__name__.rsplit('.', 1)[-1]}"
    return predict


def _rule_guo_phase4(composition: Composition) -> str:
    # Guo's VEC bounds emit FCC, BCC, or mixed. "mixed" is the rule
    # saying no single phase is expected, which is what multi-phase
    # means in this taxonomy. The rule cannot emit HCP at all, so it
    # scores zero recall on that class by construction.
    verdict = guo_vec.predict(composition)
    return "multi-phase" if verdict == "mixed" else verdict


_rule_guo_phase4.__name__ = "rule:guo_vec"


def build_models(task: str) -> list[object]:
    """Baselines for one task, all scored on the same rows so they compare."""
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier

    models: list[object] = [MajorityClass()]
    if task == "single_vs_multi":
        models.append(_rule_single_vs_multi(zhang_delta))
        models.append(_rule_single_vs_multi(yang_omega))
    else:
        models.append(_rule_guo_phase4)
    models.append(
        DescriptorModel(
            RandomForestClassifier(n_estimators=300, random_state=FOREST_SEED, n_jobs=-1),
            "random-forest",
        )
    )
    models.append(
        DescriptorModel(
            GradientBoostingClassifier(random_state=FOREST_SEED),
            "gradient-boosting",
        )
    )
    return models


def _closure_paragraph(bench) -> str:
    """Why the grouped scheme is the strictest one offered, with numbers."""
    from hea_bench.benchmark.splits import subset_closure_components

    components = subset_closure_components(bench.families)
    n_families, n_rows = components[0]
    return (
        "The grouped score is still an upper bound on out-of-system performance, "
        "because element-set grouping lets a system train while its extensions are "
        "tested. The stricter subset-closure rule was measured and ruled out rather "
        f"than skipped: it collapses {n_families} of the "
        f"{len({*bench.families})} families into one component of {n_rows} rows, "
        f"{n_rows / len(bench):.1%} of the benchmark, and no k-fold partition can "
        "respect an indivisible block that large. The experimentally studied HEA "
        "compositions form a single connected web of shared subsystems."
    )


def _row(report) -> str:
    def cell(scheme, name: str) -> str:
        return f"{scheme.summary[f'{name}_mean']:.3f} ± {scheme.summary[f'{name}_se']:.3f}"

    return (
        f"| `{report.model_name}` | {report.n_rows_evaluated} "
        f"| {cell(report.grouped, 'balanced_accuracy')} "
        f"| {cell(report.random, 'balanced_accuracy')} "
        f"| {report.gap['balanced_accuracy']:+.3f} "
        f"| {cell(report.grouped, 'macro_f1')} "
        f"| {cell(report.random, 'macro_f1')} "
        f"| {report.gap['macro_f1']:+.3f} |"
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    import sklearn

    reports: dict[str, list] = {}
    coverage: dict[str, dict] = {}
    benches: dict[str, object] = {}
    for task in ("single_vs_multi", "phase4"):
        bench = load_benchmark(task=task)
        benches[task] = bench
        # One subset for every baseline in the table. Scoring the rules on
        # all covered rows and the fitted models on the finite subset
        # would put the two on different denominators and make the
        # comparison meaningless.
        usable = finite_descriptor_indices(bench)
        usable_set = set(usable)
        dropped = [
            bench.rows[index].label
            for index in bench.subset_indices(descriptor_ready_only=True)
            if index not in usable_set
        ]
        coverage[task] = {
            "n_labelled": len(bench),
            "n_element_covered": len(bench.subset_indices(descriptor_ready_only=True)),
            "n_evaluated": len(usable),
            "dropped_singular_by_class": dict(Counter(dropped)),
        }
        print(f"\n=== task={task}  n={len(usable)} of {len(bench)} ===")
        print(f"    dropped for a singular descriptor: {coverage[task]['dropped_singular_by_class']}")
        task_reports = []
        for model in build_models(task):
            report = evaluate(model, bench, indices=usable)
            print()
            print(report.table())
            task_reports.append(report)
        reports[task] = task_reports

    bench = benches["single_vs_multi"]
    described = bench.describe()

    lines = [
        "# Baseline results",
        "",
        "Generated by `tools/benchmark_baselines.py`. Every number here is",
        "reproducible from the frozen splits recorded below, so a rerun that",
        "disagrees means something moved.",
        "",
        "The two columns answer different questions. The random column uses the",
        "protocol most published evaluations in this area use, a random split over",
        "a corpus dense with stoichiometric series, and largely measures",
        "interpolation within known alloy systems. The grouped column keeps every",
        "alloy family whole across the fold boundary and measures extrapolation to",
        "unseen element systems. Neither is correct on its own; the gap between",
        "them, which this benchmark exists to measure, quantifies how much of a",
        "random-split score comes from testing on close relatives of training",
        "alloys. For the interpolation-versus-extrapolation reading of grouped",
        "evaluation see Li et al., Commun. Mater. 6:9 (2025),",
        "doi:10.1038/s43246-024-00731-w.",
        "",
        "## Provenance",
        "",
        f"- Corpus version: v{bench.corpus_version}",
        f"- Rows with a consensus label: {len(bench)}",
        f"- Alloy families: {described['family_overlap_profile']['n_families']}",
        f"- Grouped split digest: `{bench.grouped.digest}`",
        f"- Random split digest: `{bench.random.digest}` (seed {bench.random.seed})",
        f"- scikit-learn {sklearn.__version__}, Python {platform.python_version()}",
        "",
        "Under the random split, "
        f"{described['family_overlap_profile']['random_straddling_families']} alloy families "
        f"appear on both sides of a fold boundary, covering "
        f"{described['family_overlap_profile']['random_rows_in_straddling_families']} rows, or "
        f"{described['family_overlap_profile']['random_fraction_rows_interpolable']:.1%} of the "
        "benchmark. Under the grouped split that count is zero by construction.",
        "",
        _closure_paragraph(bench),
        "",
    ]

    for task, task_reports in reports.items():
        cover = coverage[task]
        lines += [
            f"## Task: {task}",
            "",
            f"{cover['n_labelled']} rows carry a consensus label. "
            f"{cover['n_element_covered']} of those use only elements the tables cover, "
            f"and {cover['n_evaluated']} of those in turn have every descriptor finite. "
            f"The rest were dropped because Omega or phi is singular where the mixing "
            f"enthalpy approaches zero. By class, dropped: "
            f"{cover['dropped_singular_by_class']}. That exclusion is not random, since "
            f"near-ideal alloys skew single-phase, so the evaluated subset is a little "
            f"harder than the corpus as a whole.",
            "",
            "| model | n | grouped bal. acc. | random bal. acc. | gap | grouped macro F1 "
            "| random macro F1 | gap |",
            "|---|---:|---|---|---:|---|---|---:|",
        ]
        lines += [_row(report) for report in task_reports]
        lines.append("")

    lines += [
        "## Reading the rule rows",
        "",
        "The rule baselines carry no fitted parameters, so they have no training",
        "rows to be close to and their gap is near zero. That is a property of",
        "the protocol, not evidence",
        "that the rules generalize well. Compare rules against the fitted models",
        "on the grouped column only.",
        "",
        "## What the fitted models are, and are not",
        "",
        "The random forest (300 trees) and gradient boosting rows use",
        "scikit-learn defaults apart from the fixed seed, fitted on this",
        "package's own fourteen descriptors. They are deliberately not",
        "reimplementations of any published HEA model, and no hyperparameter",
        "tuning was done, so they measure what a stock ensemble extracts from",
        "these descriptors rather than any specific paper's ceiling. A tuned or",
        "differently featurized model belongs in a new row, fitted only inside",
        "training folds, not in a revision of these.",
        "",
    ]

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    OUT_JSON.write_text(
        json.dumps(
            {
                "corpus": described,
                "coverage": coverage,
                "results": {
                    task: [report.to_dict() for report in task_reports]
                    for task, task_reports in reports.items()
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nwrote {OUT_MD}")
    print(f"wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
