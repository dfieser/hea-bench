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
from hea_bench.benchmark.metrics import standard_error  # noqa: E402
from hea_bench.benchmark.splits import grouped_split  # noqa: E402
from hea_bench.composition import family_of  # noqa: E402
from hea_bench.descriptors.backend import matrix_vector  # noqa: E402
from hea_bench.properties.borg import (  # noqa: E402
    experimental_density_records,
    hardness_records,
)
from hea_bench.properties.tier_a import density  # noqa: E402
from hea_bench.uncertainty import ConformalRegressor  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ALPHA = 0.1
SEED = 0
TREES = 300
#: Measured hardness at or above this counts as hard in the coverage check.
HARD_HV = 750


def _hardness_study() -> dict:
    """Nested cross-validation of the released procedure.

    Outer folds hold out whole alloy systems. Inside each outer training
    set, the interval is set exactly as ``hea_bench.properties.hardness``
    sets it on all data: five-fold cross-validation over whole systems
    gives the scores, and a forest refit on the whole training set makes
    the predictions.
    """
    from sklearn.ensemble import RandomForestRegressor

    from hea_bench.properties.hardness import _fitted
    from hea_bench.uncertainty.conformal import cross_val_scores

    records = hardness_records()
    usable, features = [], []
    for record in records:
        vector = matrix_vector(record.composition)
        if vector is not None:
            usable.append(record)
            features.append(vector)
    families = [family_of(record.composition) for record in usable]
    values = [record.value for record in usable]

    def make_forest():
        return RandomForestRegressor(n_estimators=TREES, random_state=SEED, n_jobs=-1)

    scheme = grouped_split(families, ["x"] * len(usable), k=5)
    fold_mae, fold_cover, fold_width = [], [], []
    errors_all: list[float] = []
    hard = [0, 0]
    for fold in scheme.folds:
        train = list(fold.train)
        inner = grouped_split([families[i] for i in train], ["x"] * len(train), k=5)
        X_train = [features[i] for i in train]
        y_train = [values[i] for i in train]
        scores = cross_val_scores(
            make_forest, X_train, y_train, [(list(f.train), list(f.test)) for f in inner.folds]
        )
        model = make_forest().fit(X_train, y_train)
        threshold = ConformalRegressor(model).calibrate_scores(scores)._threshold(ALPHA)
        half = math.inf if threshold is None else threshold
        predictions = [float(p) for p in model.predict([features[i] for i in fold.test])]
        hits = [abs(p - values[i]) <= half for p, i in zip(predictions, fold.test)]
        errors = [abs(p - values[i]) for p, i in zip(predictions, fold.test)]
        errors_all.extend(errors)
        fold_mae.append(sum(errors) / len(errors))
        fold_cover.append(sum(hits) / len(hits))
        fold_width.append(2 * half)
        for hit, i in zip(hits, fold.test):
            if values[i] >= HARD_HV:
                hard[0] += hit
                hard[1] += 1

    processing_mix: dict[str, int] = {}
    for record in usable:
        key = record.processing or "(unrecorded)"
        processing_mix[key] = processing_mix.get(key, 0) + 1

    _model, released, _domain, _n = _fitted(None)
    return {
        "n_records": len(records),
        "n_usable": len(usable),
        "n_families": len(set(families)),
        "n_compositions": len(
            {
                tuple(sorted((element, round(x, 4)) for element, x in record.composition.items()))
                for record in usable
            }
        ),
        "hv_min": min(values),
        "hv_max": max(values),
        "processing_mix": dict(sorted(processing_mix.items(), key=lambda kv: -kv[1])),
        "mae_mean": statistics.mean(fold_mae),
        "mae_se": standard_error(fold_mae),
        "median_abs_error": statistics.median(errors_all),
        "coverage": sum(cover * len(fold.test) for cover, fold in zip(fold_cover, scheme.folds))
        / len(usable),
        "coverage_se": standard_error(fold_cover),
        "hard_covered": hard[0],
        "hard_n": hard[1],
        "width_mean": statistics.mean(fold_width),
        "released_half_width": released._threshold(ALPHA),
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
        f"measurements, test temperature at most 35 C). "
        f"{hardness['n_usable']} of them are fully descriptor-scorable and "
        f"form the training population: {hardness['n_compositions']} distinct "
        f"compositions in {hardness['n_families']} alloy systems, HV "
        f"{hardness['hv_min']:.0f} to {hardness['hv_max']:.0f}. A composition "
        f"measured after two processing routes is two rows, and the model "
        f"pools them, so processing is part of the scatter the interval "
        f"absorbs. Both rows always share a cross-validation fold, because "
        f"folds hold whole systems.",
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
        f"matrix descriptors. The released model trains on every alloy, and "
        f"its 90 percent interval is the prediction plus or minus "
        f"{hardness['released_half_width']:.0f} HV, the conformal threshold "
        f"of its own five-fold cross-validation errors over whole alloy "
        f"systems. The table tests that procedure by nested cross-validation. "
        f"Each of five outer folds holds out whole systems, and the interval "
        f"is set inside the remaining four exactly as the released model sets "
        f"it on all data.",
        "",
        "| quantity | value |",
        "|---|---:|",
        f"| held-out mean absolute error | {hardness['mae_mean']:.0f} HV "
        f"(fold-to-fold standard error {hardness['mae_se']:.0f}) |",
        f"| held-out median absolute error | {hardness['median_abs_error']:.0f} HV |",
        f"| interval coverage, every alloy (nominal 90%) | "
        f"{hardness['coverage']:.3f} (fold-to-fold standard error "
        f"{hardness['coverage_se']:.3f}) |",
        f"| interval coverage, alloys of {HARD_HV} HV or harder | "
        f"{hardness['hard_covered'] / hardness['hard_n']:.3f} "
        f"({hardness['hard_covered']} of {hardness['hard_n']}) |",
        f"| mean interval width in the nested study | {hardness['width_mean']:.0f} HV |",
        f"| released interval width | {2 * hardness['released_half_width']:.0f} HV |",
        "",
        "## What this error does and does not support",
        "",
        f"The interval is a screening tool. Two alloys whose predictions "
        f"differ by more than the released width, "
        f"{2 * hardness['released_half_width']:.0f} HV, have intervals that do "
        f"not overlap, which is enough to triage a palette before synthesis. "
        f"Candidates closer than that are not ranked by this model, and the "
        f"API's intervals overlap visibly for such pairs. Conditioning on one "
        f"processing route is available and shrinks the population (the "
        f"floor refuses below {50} alloys).",
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
        "",
        "## Cost per kg (indicative)",
        "",
        "Mass-weighted over the date-stamped element price table in "
        "`hea_bench.properties.data.element_prices` (assembled 2026-08 from "
        "USGS Mineral Commodity Summaries 2026, LME reference prices, "
        "bullion spot quotes, and named minor-metal and rare-earth market "
        "relays; every row carries its own basis, as-of date, and source). "
        "This is a screening number for comparing palettes, never a quote: "
        "several rows are oxide-basis or contained-element prices because "
        "no pure-metal market exists, Western and Chinese domestic prices "
        "for export-controlled elements differ by factors of 2 to 4, 2026 "
        "spot markets are unusually hot, and processing plus "
        "research-quantity purchasing dominate real lab cost. "
        "`cost_breakdown()` exposes the per-element contributions with "
        "their bases so none of this is hidden behind one number.",
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
