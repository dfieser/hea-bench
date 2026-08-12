"""Generate the property model cards in docs/.

Two cards: docs/property-hardness.md (the tier B surrogate: data,
held-out error under a family-grouped protocol, interval behavior, and
the plain statement of what decisions the error supports) and
docs/property-tier-a.md (closed-form estimates validated against the
experimental values the Borg deposit carries). The cards also record
what is deliberately NOT shipped and why, which matters as much as
what is.

    PYTHONPATH=src python tools/property_cards.py
"""

from __future__ import annotations

import datetime
import math
import pathlib
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from hea_bench import __version__ as _hea_bench_version  # noqa: E402
from hea_bench.benchmark.splits import grouped_split  # noqa: E402
from hea_bench.composition import family_of  # noqa: E402
from hea_bench.properties.borg import (  # noqa: E402
    experimental_density_records,
    hardness_records,
)
from hea_bench.properties.hardness import _feature_vector  # noqa: E402
from hea_bench.properties.tier_a import density  # noqa: E402
from hea_bench.uncertainty import ConformalRegressor  # noqa: E402
from hea_bench.uncertainty.splitting import grouped_calibration_split  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ALPHA = 0.1
SEED = 0
TREES = 300


def _hardness_study() -> dict:
    from sklearn.ensemble import RandomForestRegressor

    records = hardness_records()
    usable, features = [], []
    for record in records:
        vector = _feature_vector(record.composition)
        if vector is not None:
            usable.append(record)
            features.append(vector)
    families = [family_of(record.composition) for record in usable]
    values = [record.value for record in usable]

    scheme = grouped_split(families, ["x"] * len(usable), k=5)
    fold_mae, fold_cover, fold_width = [], [], []
    errors_all: list[float] = []
    for fold in scheme.folds:
        proper, calibration = grouped_calibration_split(
            [families[i] for i in fold.train], fraction=0.2, seed=SEED
        )
        train_ids = list(fold.train)
        proper_ids = [train_ids[i] for i in proper]
        calibration_ids = [train_ids[i] for i in calibration]
        model = RandomForestRegressor(n_estimators=TREES, random_state=SEED)
        model.fit([features[i] for i in proper_ids], [values[i] for i in proper_ids])
        conformal = ConformalRegressor(model).fit_calibrate(
            [features[i] for i in calibration_ids], [values[i] for i in calibration_ids]
        )
        predictions = model.predict([features[i] for i in fold.test])
        intervals = conformal.predict_interval([features[i] for i in fold.test], alpha=ALPHA)
        errors = [abs(float(p) - values[i]) for p, i in zip(predictions, fold.test)]
        errors_all.extend(errors)
        fold_mae.append(sum(errors) / len(errors))
        fold_cover.append(
            sum(
                1
                for (low, high), i in zip(intervals, fold.test)
                if low <= values[i] <= high
            )
            / len(fold.test)
        )
        fold_width.append(
            sum(high - low for low, high in intervals if math.isfinite(high - low))
            / len(intervals)
        )

    processing_mix: dict[str, int] = {}
    for record in usable:
        key = record.processing or "(unrecorded)"
        processing_mix[key] = processing_mix.get(key, 0) + 1

    return {
        "n_records": len(records),
        "n_usable": len(usable),
        "n_families": len(set(families)),
        "hv_min": min(values),
        "hv_max": max(values),
        "processing_mix": dict(sorted(processing_mix.items(), key=lambda kv: -kv[1])),
        "mae_mean": statistics.mean(fold_mae),
        "mae_se": statistics.stdev(fold_mae) / math.sqrt(len(fold_mae)),
        "median_abs_error": statistics.median(errors_all),
        "coverage_mean": statistics.mean(fold_cover),
        "width_mean": statistics.mean(fold_width),
    }


def _density_study() -> dict:
    records = experimental_density_records()
    pairs = []
    for record in records:
        estimate = density(record.composition)
        if estimate is not None:
            pairs.append((estimate, record.value))
    errors = [abs(estimate - measured) for estimate, measured in pairs]
    signed = [estimate - measured for estimate, measured in pairs]
    relative = [
        abs(estimate - measured) / measured for estimate, measured in pairs
    ]
    return {
        "n": len(pairs),
        "n_records": len(records),
        "mae": statistics.mean(errors),
        "bias": statistics.mean(signed),
        "mean_relative": statistics.mean(relative),
        "max_abs": max(errors),
    }


def main() -> int:
    try:
        import sklearn  # noqa: F401
    except ImportError:
        print('needs scikit-learn: pip install -e ".[properties]"', file=sys.stderr)
        return 2

    today = datetime.date.today().isoformat()
    hardness = _hardness_study()
    dens = _density_study()

    hardness_lines = [
        "# Model card: hardness (tier B)",
        "",
        f"Generated by `tools/property_cards.py` with hea-bench "
        f"{_hea_bench_version} on {today}.",
        "",
        "## Data",
        "",
        f"Source: Borg et al. 2020 (Sci. Data 7, 430; CC-BY-4.0 figshare "
        f"deposit mirrored in `data/raw/borg2020/`). {hardness['n_records']} "
        f"unique (formula, processing) alloys carry a near-room-temperature "
        f"Vickers hardness after the loader rules (median over repeat "
        f"measurements, test temperature at most 35 C); "
        f"{hardness['n_usable']} of them are fully descriptor-scorable and "
        f"form the training population, spanning {hardness['n_families']} "
        f"alloy families and HV {hardness['hv_min']:.0f} to "
        f"{hardness['hv_max']:.0f}.",
        "",
        "Processing mix of the training population (pooled by default, "
        "conditionable via `processing=`):",
        "",
        "| processing | alloys |",
        "|---|---:|",
    ]
    for key, count in hardness["processing_mix"].items():
        hardness_lines.append(f"| {key} | {count} |")
    hardness_lines += [
        "",
        "## Model and held-out error",
        "",
        f"Random forest ({TREES} trees, seed {SEED}) on the package's 14 "
        f"matrix descriptors, evaluated by family-grouped five-fold cross "
        f"validation (whole alloy families held out, the extrapolative "
        f"protocol), with a family-grouped 20 percent calibration split "
        f"inside each training fold for the conformal interval.",
        "",
        f"| quantity | value |",
        f"|---|---:|",
        f"| grouped CV mean absolute error | {hardness['mae_mean']:.0f} HV "
        f"(fold-to-fold standard error {hardness['mae_se']:.0f}) |",
        f"| grouped CV median absolute error | {hardness['median_abs_error']:.0f} HV |",
        f"| conformal interval empirical coverage (nominal 90%) | "
        f"{hardness['coverage_mean']:.3f} |",
        f"| mean interval width at alpha 0.1 | {hardness['width_mean']:.0f} HV |",
        "",
        "## What this error does and does not support",
        "",
        f"A mean absolute error near {hardness['mae_mean']:.0f} HV against a "
        f"range of roughly 1100 HV supports coarse screening: separating "
        f"soft solid-solution regimes from hard ones, triaging a palette "
        f"before synthesis. It does not support ranking candidates whose "
        f"predicted hardness differs by less than roughly the interval "
        f"width above, and the API's intervals are wide exactly so that "
        f"such pairs visibly overlap. The training data pools processing "
        f"routes; conditioning on one route is available and shrinks the "
        f"population (the floor refuses below {50} alloys).",
        "",
        "## Deliberately not shipped",
        "",
        "Yield strength: the same deposit carries 1,067 strength rows, but "
        "they span test temperatures from ambient to 1000 C with uneven "
        "strain conditions; a pooled fit would predict an ill-defined "
        "quantity, and the near-room-temperature subset thins per system "
        "to where family-grouped validation is not meaningful. Elastic "
        "moduli and experimental ductility: too few rows after the same "
        "filters. Corrosion and oxidation measures: no adequately licensed "
        "public dataset at screening scale. These return as tier B "
        "properties if and when a licensed dataset supports a defensible "
        "held-out error; the omission is the honest outcome, not a "
        "roadmap gap.",
    ]

    tier_a_lines = [
        "# Model card: tier A closed forms",
        "",
        f"Generated by `tools/property_cards.py` with hea-bench "
        f"{_hea_bench_version} on {today}.",
        "",
        "Tier A properties are transparent arithmetic over cited tables, "
        "with no fitted parameters. Their card is a validation, not a "
        "training description.",
        "",
        "## Density (rule of mixtures)",
        "",
        f"`sum(c_i M_i) / sum(c_i V_i)` with IUPAC standard atomic weights "
        f"and the vendored matminer molar volumes. Against the "
        f"{dens['n']} alloys with experimentally measured density in the "
        f"Borg deposit (of {dens['n_records']} density records, those with "
        f"all elements covered):",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| mean absolute error | {dens['mae']:.2f} g/cm3 |",
        f"| mean relative error | {dens['mean_relative']:.1%} |",
        f"| mean signed error (estimate minus measured) | {dens['bias']:+.2f} g/cm3 |",
        f"| worst case | {dens['max_abs']:.2f} g/cm3 |",
        "",
        "Volume additivity ignores excess mixing volume and porosity in "
        "the measured samples; both contribute to the spread. The estimate "
        "is a screening quantity, reported without an interval because "
        "there is no fitted model to calibrate one on; treat the mean "
        "relative error above as its typical scale of wrongness.",
        "",
        "## Melting temperature (rule of mixtures)",
        "",
        "Composition-weighted mean of CRC elemental melting points, shipped "
        "since v1.x as a descriptor and re-exposed as a tier A property. "
        "The Borg deposit carries no measured melting temperatures, so no "
        "validation table exists here; the estimate ignores "
        "solidus/liquidus spread and eutectics, and should be read as the "
        "scale used inside Omega rather than a melting prediction.",
    ]

    (REPO_ROOT / "docs" / "property-hardness.md").write_text(
        "\n".join(hardness_lines) + "\n", encoding="utf-8"
    )
    (REPO_ROOT / "docs" / "property-tier-a.md").write_text(
        "\n".join(tier_a_lines) + "\n", encoding="utf-8"
    )
    print("wrote docs/property-hardness.md and docs/property-tier-a.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
