"""The conformal coverage study: do the prediction sets keep their promise?

Design, stated up front because the numbers only mean something under
it: for each grouped fold of the benchmark, the training rows are split
family-grouped into proper-train (about 80 percent) and calibration
(about 20 percent), a random forest (300 trees, seed 0, the baseline
configuration) is fitted on the proper-train descriptor matrix, a
:class:`~hea_bench.uncertainty.ConformalClassifier` is calibrated on the
calibration rows, and prediction sets at nominal 80, 90 and 95 percent
are scored on the held-out fold. A domain model fitted on the
proper-train rows only flags every test row as in or out of domain.

The grouped split makes test families unseen by construction, so this
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
import random
import statistics
from collections import defaultdict
from collections.abc import Callable

#: Nominal miscoverage levels studied (80, 90 and 95 percent sets).
ALPHAS = (0.2, 0.1, 0.05)
SEED = 0
FOREST_TREES = 300
CALIBRATION_FRACTION = 0.2

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


def family_grouped_calibration_split(indices, families, rng, fraction=CALIBRATION_FRACTION):
    """Split row indices into proper-train and calibration, whole families.

    Consumes ``rng`` (one shuffle per call), so calling it once per fold
    in fold order reproduces the study's draws exactly.
    """
    rows_by_family = defaultdict(list)
    for index in indices:
        rows_by_family[families[index]].append(index)
    family_keys = sorted(rows_by_family)
    rng.shuffle(family_keys)
    target = round(len(indices) * fraction)
    calibration: list[int] = []
    for key in family_keys:
        if len(calibration) >= target:
            break
        calibration.extend(rows_by_family[key])
    calibration_set = set(calibration)
    proper = [index for index in indices if index not in calibration_set]
    return proper, calibration


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
        folds, so a long run can report where it is.

    Returns
    -------
    dict
        ``levels`` holds, per alpha, every group of :data:`GROUPS` with
        its row count, covered count, coverage, mean set size, per-fold
        coverages and fold-to-fold standard error. ``n_out_of_domain``
        and ``n_out_of_domain_binaries`` count the flagged test rows.
    """
    from sklearn.ensemble import RandomForestClassifier

    from ..benchmark import load_benchmark
    from ..benchmark.corpus import descriptor_matrix, finite_descriptor_indices
    from . import ConformalClassifier, fit_domain

    def report(message: str, fraction: float) -> None:
        if progress is not None:
            progress(message, fraction)

    report("loading the benchmark", 0.0)
    bench = load_benchmark(task=task, version=version)
    finite = list(finite_descriptor_indices(bench))
    finite_set = set(finite)
    matrix = dict(zip(finite, descriptor_matrix([bench.rows[i].composition for i in finite])))
    families = {i: bench.rows[i].family for i in finite}
    labels = {i: bench.rows[i].label for i in finite}

    pooled = {alpha: {group: [0, 0, 0] for group in GROUPS} for alpha in alphas}
    per_fold: dict = {alpha: defaultdict(list) for alpha in alphas}
    n_out = n_out_binaries = 0

    rng = random.Random(SEED)
    n_folds = len(bench.grouped.folds)
    for number, fold in enumerate(bench.grouped.folds):
        report(f"fold {number + 1} of {n_folds}: fitting the forest", number / n_folds)
        train = [i for i in fold.train if i in finite_set]
        test = [i for i in fold.test if i in finite_set]
        proper, calibration = family_grouped_calibration_split(train, families, rng)

        model = RandomForestClassifier(n_estimators=FOREST_TREES, random_state=SEED)
        model.fit([matrix[i] for i in proper], [labels[i] for i in proper])
        conformal = ConformalClassifier(model).fit_calibrate(
            [matrix[i] for i in calibration], [labels[i] for i in calibration]
        )
        report(f"fold {number + 1} of {n_folds}: checking the domain", (number + 0.6) / n_folds)
        domain = fit_domain([bench.rows[i] for i in proper])
        in_domain = {i: domain.novelty(bench.rows[i].composition)["in_domain"] for i in test}
        n_elements = {i: len(bench.rows[i].composition) for i in test}
        trained = {frozenset(bench.rows[i].composition) for i in proper}
        one_step = {
            i: any(len(frozenset(bench.rows[i].composition) ^ known) == 1 for known in trained)
            for i in test
            if n_elements[i] >= 4
        }
        n_out += sum(1 for i in test if not in_domain[i])
        n_out_binaries += sum(1 for i in test if not in_domain[i] and n_elements[i] == 2)

        for alpha in alphas:
            sets = dict(zip(test, conformal.predict_set([matrix[i] for i in test], alpha=alpha)))
            fold_cells: dict = defaultdict(lambda: [0, 0])
            for i in test:
                hit = 1 if labels[i] in sets[i] else 0
                groups = ["all", "in_domain" if in_domain[i] else "out_of_domain"]
                if n_elements[i] < 4:
                    groups.append("fewer_than_four")
                else:
                    groups.append("four_or_more")
                    groups.append(
                        "four_or_more_one_element_from_training"
                        if one_step[i]
                        else "four_or_more_farther"
                    )
                for group in groups:
                    cell = pooled[alpha][group]
                    cell[0] += hit
                    cell[1] += 1
                    cell[2] += len(sets[i])
                    fold_cells[group][0] += hit
                    fold_cells[group][1] += 1
            for group, (hits, total) in fold_cells.items():
                per_fold[alpha][group].append(hits / total)

    report("done", 1.0)
    levels = []
    for alpha in alphas:
        groups = {}
        for group in GROUPS:
            covered, total, size_sum = pooled[alpha][group]
            folds = per_fold[alpha].get(group, [])
            groups[group] = {
                "n": total,
                "covered": covered,
                "set_size_sum": size_sum,
                "coverage": covered / total if total else None,
                "mean_set_size": size_sum / total if total else None,
                "fold_coverage": folds,
                "fold_se": (
                    statistics.stdev(folds) / math.sqrt(len(folds)) if len(folds) > 1 else None
                ),
            }
        levels.append({"alpha": alpha, "target": 1.0 - alpha, "groups": groups})

    return {
        "task": task,
        "corpus_version": version,
        "n_rows": len(finite),
        "n_out_of_domain": n_out,
        "n_out_of_domain_binaries": n_out_binaries,
        "settings": {
            "forest_trees": FOREST_TREES,
            "seed": SEED,
            "calibration_fraction": CALIBRATION_FRACTION,
            "n_folds": n_folds,
        },
        "levels": levels,
    }


__all__ = [
    "ALPHAS",
    "CALIBRATION_FRACTION",
    "FOREST_TREES",
    "GROUPS",
    "SEED",
    "coverage_study",
    "family_grouped_calibration_split",
]
