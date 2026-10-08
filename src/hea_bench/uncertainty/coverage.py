"""The conformal coverage study: do the prediction sets keep their promise?

Design, stated up front because the numbers only mean something under
it. The study is a nested cross-validation over the frozen system split,
so it tests exactly the procedure the released predictor uses
(:mod:`hea_bench.uncertainty.phase`). For each fold, the other four folds
play the part of the whole corpus: their calibration scores come from
cross-validation among those four folds (every alloy scored by a forest
that never saw its system, and never saw the held-out fold either), a
random forest (300 trees, seed 0, the baseline configuration) refit on
all four folds predicts the held-out fold, and sets at nominal 80, 90
and 95 percent are calibrated separately for alloys with fewer than four
and with four or more elements. A domain model fitted on the same four
folds flags every test row as in or out of domain. Each cross-validation
forest leaves out two folds, so it serves both of them and the study
fits ten such forests plus five refits.

The system split makes test systems unseen by construction, so this
study measures the coverage guarantee under deliberate strain. Results
are grouped the ways that matter for reading them: overall, by the
domain flag, by element count (fewer than four, four or more), and,
within four or more elements, by whether the alloy's element set is one
added or removed element away from a system the fold's model trained
on. ``tools/uncertainty_coverage.py`` writes ``docs/uncertainty-coverage.md``
from this function, and the web app runs the same function in the
browser. Needs scikit-learn (``pip install "hea-bench[benchmark]"``).
Nothing here characterizes any published model or any other tool.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from collections.abc import Callable

#: Nominal miscoverage levels studied (80, 90 and 95 percent sets).
ALPHAS = (0.2, 0.1, 0.05)
SEED = 0
FOREST_TREES = 300

#: What this study measured on corpus v0.1.0, as tools/uncertainty_coverage.py
#: wrote it to docs/uncertainty-coverage.md: task -> nominal coverage ->
#: (empirical coverage inside the dataset's range, outside it). A test
#: (tests/test_conformal.py) fails when the two disagree, so regenerating
#: the doc means copying its new numbers here.
MEASURED_COVERAGE = {
    "single_vs_multi": {0.8: (0.801, 0.845), 0.9: (0.899, 0.910), 0.95: (0.947, 0.957)},
    "phase4": {0.8: (0.804, 0.830), 0.9: (0.882, 0.903), 0.95: (0.943, 0.951)},
}

#: Result groups, in display order.
GROUPS = (
    "all",
    "in_domain",
    "out_of_domain",
    "fewer_than_four",
    "four_or_more",
    "four_or_more_one_element_from_training",
    "four_or_more_farther",
)


def coverage_study(
    task: str = "single_vs_multi",
    *,
    alphas: tuple[float, ...] = ALPHAS,
    version: str = "0.1.0",
    progress: Callable[[str, float], None] | None = None,
) -> dict:
    """Run the study for one task and return every number it reports.

    Parameters
    ----------
    task
        ``"single_vs_multi"`` or ``"phase4"``.
    alphas
        Miscoverage levels; 0.1 is a nominal 90 percent set.
    version
        Corpus version. The published study uses ``"0.1.0"``.
    progress
        Optional callback ``(message, fraction_done)``, called between
        forest fits, so a long run can report where it is.

    Returns
    -------
    dict
        ``levels`` holds, per alpha, every group of :data:`GROUPS` with
        its row count, alloy-system count, covered count, coverage, mean
        set size, per-fold coverages and fold-to-fold standard error.
        ``n_out_of_domain`` and ``n_out_of_domain_binaries`` count the
        flagged test rows.
    """
    from sklearn.ensemble import RandomForestClassifier

    from .._model_cache import FOREST_JOBS
    from ..benchmark import load_benchmark
    from ..benchmark.corpus import descriptor_matrix, finite_descriptor_indices
    from . import ConformalClassifier, fit_domain
    from .conformal import classifier_scores
    from .phase import calibration_group

    def report(message: str, fraction: float) -> None:
        if progress is not None:
            progress(message, fraction)

    report("loading the benchmark", 0.0)
    bench = load_benchmark(task=task, version=version)
    finite = list(finite_descriptor_indices(bench))
    finite_set = set(finite)
    matrix = dict(zip(finite, descriptor_matrix([bench.rows[i].composition for i in finite])))
    labels = {i: bench.rows[i].label for i in finite}
    families = {i: bench.rows[i].family for i in finite}
    group_of = {i: calibration_group(bench.rows[i].composition) for i in finite}
    fold_rows = [[i for i in fold.test if i in finite_set] for fold in bench.grouped.folds]
    n_folds = len(fold_rows)
    n_fits = n_folds * (n_folds - 1) // 2 + n_folds
    fits = 0

    def without(*folds: int) -> list[int]:
        return [i for number, rows in enumerate(fold_rows) if number not in folds for i in rows]

    def forest(rows: list[int]):
        nonlocal fits
        model = RandomForestClassifier(
            n_estimators=FOREST_TREES, random_state=SEED, n_jobs=FOREST_JOBS
        )
        model.fit([matrix[i] for i in rows], [labels[i] for i in rows])
        fits += 1
        return model

    def scores_of(model, rows: list[int]) -> list[float]:
        return classifier_scores(model, [matrix[i] for i in rows], [labels[i] for i in rows])

    # Calibration scores. A forest without folds a and b scores fold a's
    # alloys for the run that holds out b, and fold b's for the run that
    # holds out a. Only the scores are kept, so one forest is in memory.
    calibration: dict[tuple[int, int], list[float]] = {}
    for a in range(n_folds):
        for b in range(a + 1, n_folds):
            report(
                f"calibration forest {fits + 1} of {n_fits}: without folds {a + 1} and {b + 1}",
                fits / n_fits,
            )
            model = forest(without(a, b))
            calibration[(b, a)] = scores_of(model, fold_rows[a])
            calibration[(a, b)] = scores_of(model, fold_rows[b])
            del model

    pooled = {alpha: {group: [0, 0, 0] for group in GROUPS} for alpha in alphas}
    systems = {alpha: {group: set() for group in GROUPS} for alpha in alphas}
    per_fold: dict = {alpha: defaultdict(list) for alpha in alphas}
    n_out = n_out_binaries = 0

    for number in range(n_folds):
        report(f"fold {number + 1} of {n_folds}: fitting the forest", fits / n_fits)
        train = without(number)
        test = fold_rows[number]
        scores: list[float] = []
        groups: list[str] = []
        for other in range(n_folds):
            if other != number:
                scores += calibration[(number, other)]
                groups += [group_of[i] for i in fold_rows[other]]
        model = forest(train)
        conformal = ConformalClassifier(model).calibrate_scores(scores, groups)
        report(f"fold {number + 1} of {n_folds}: checking the domain", fits / n_fits)
        domain = fit_domain([bench.rows[i] for i in train])
        in_domain = {i: domain.novelty(bench.rows[i].composition)["in_domain"] for i in test}
        n_elements = {i: len(bench.rows[i].composition) for i in test}
        trained = {frozenset(bench.rows[i].composition) for i in train}
        one_step = {
            i: any(len(frozenset(bench.rows[i].composition) ^ known) == 1 for known in trained)
            for i in test
            if n_elements[i] >= 4
        }
        n_out += sum(1 for i in test if not in_domain[i])
        n_out_binaries += sum(1 for i in test if not in_domain[i] and n_elements[i] == 2)

        test_groups = [group_of[i] for i in test]
        for alpha in alphas:
            sets = dict(
                zip(
                    test,
                    conformal.predict_set(
                        [matrix[i] for i in test], alpha=alpha, groups=test_groups
                    ),
                )
            )
            fold_cells: dict = defaultdict(lambda: [0, 0])
            for i in test:
                hit = 1 if labels[i] in sets[i] else 0
                groups_of_row = ["all", "in_domain" if in_domain[i] else "out_of_domain"]
                if n_elements[i] < 4:
                    groups_of_row.append("fewer_than_four")
                else:
                    groups_of_row.append("four_or_more")
                    groups_of_row.append(
                        "four_or_more_one_element_from_training"
                        if one_step[i]
                        else "four_or_more_farther"
                    )
                for group in groups_of_row:
                    cell = pooled[alpha][group]
                    cell[0] += hit
                    cell[1] += 1
                    cell[2] += len(sets[i])
                    systems[alpha][group].add(families[i])
                    fold_cells[group][0] += hit
                    fold_cells[group][1] += 1
            for group, (hits, total) in fold_cells.items():
                per_fold[alpha][group].append(hits / total)
        del model, conformal

    report("done", 1.0)
    levels = []
    for alpha in alphas:
        groups_out = {}
        for group in GROUPS:
            covered, total, size_sum = pooled[alpha][group]
            folds = per_fold[alpha].get(group, [])
            groups_out[group] = {
                "n": total,
                "n_systems": len(systems[alpha][group]),
                "covered": covered,
                "set_size_sum": size_sum,
                "coverage": covered / total if total else None,
                "mean_set_size": size_sum / total if total else None,
                "fold_coverage": folds,
                "fold_se": (
                    statistics.stdev(folds) / math.sqrt(len(folds)) if len(folds) > 1 else None
                ),
            }
        levels.append({"alpha": alpha, "target": 1.0 - alpha, "groups": groups_out})

    return {
        "task": task,
        "corpus_version": version,
        "n_rows": len(finite),
        "n_out_of_domain": n_out,
        "n_out_of_domain_binaries": n_out_binaries,
        "settings": {
            "forest_trees": FOREST_TREES,
            "seed": SEED,
            "calibration": (
                "cross-validation over the other folds, by element-count group "
                "(fewer than four, four or more)"
            ),
            "n_folds": n_folds,
        },
        "levels": levels,
    }


__all__ = [
    "ALPHAS",
    "FOREST_TREES",
    "GROUPS",
    "SEED",
    "coverage_study",
]
