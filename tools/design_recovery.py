"""Retrospective recovery study for the composition search.

Question, stated before the answer: if the search had been run with
constraints matching a heavily studied design space, would it have
surfaced the alloys experimentalists actually made and measured, and
where do those alloys sit relative to the returned front? Two palettes
are studied, both fully inside the Borg hardness data: the Al-Co-Cr-Fe-Ni
family (the classic hardness-versus-density trade space) and the
Mo-Nb-Ta-V-W refractory family. Each palette runs twice: with the
released hardness model, which trained on the palette's measured alloys,
and with a model retrained without any four- or five-element alloy of
the palette, so the second front predicts those alloys out of sample.
The outcome is reported either way, including front members no one has
synthesized (which are suggestions, not validated predictions) and
measured alloys the front rejects (dominated, or filtered by a
constraint).

Needs the properties extra and a built corpus:

    PYTHONPATH=src python tools/design_recovery.py
"""

from __future__ import annotations

import contextlib
import datetime
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import hea_bench.properties.hardness as _hardness  # noqa: E402
from hea_bench import __version__ as _hea_bench_version  # noqa: E402
from hea_bench.design import Maximize, Minimize, search  # noqa: E402
from hea_bench.properties import predict_property  # noqa: E402
from hea_bench.properties.borg import hardness_records  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_MD = REPO_ROOT / "docs" / "design-recovery.md"

PALETTES = {
    "Al-Co-Cr-Fe-Ni": ["Al", "Co", "Cr", "Fe", "Ni"],
    "Mo-Nb-Ta-V-W": ["Mo", "Nb", "Ta", "V", "W"],
}
STEP = 0.05
TOP_N = 10


def _l1(a: dict, b: dict) -> float:
    keys = set(a) | set(b)
    return sum(abs(a.get(key, 0.0) - b.get(key, 0.0)) for key in keys)


def _rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    for position, index in enumerate(order):
        ranks[index] = float(position)
    return ranks


def _spearman(a: list[float], b: list[float]) -> float:
    ranks_a, ranks_b = _rank(a), _rank(b)
    n = len(a)
    mean = (n - 1) / 2.0
    cov = sum((x - mean) * (y - mean) for x, y in zip(ranks_a, ranks_b))
    var = sum((x - mean) ** 2 for x in ranks_a)
    return cov / var if var else 0.0


def _in_palette(record, palette_set: set) -> bool:
    return set(record.composition) <= palette_set and len(record.composition) >= 4


@contextlib.contextmanager
def _palette_held_out(palette_set: set):
    """The hardness model refit without the palette's 4- and 5-element alloys."""
    original = _hardness.hardness_records
    cache = os.environ.pop("HEA_BENCH_MODEL_CACHE", None)
    _hardness.hardness_records = lambda: [
        record for record in original() if not _in_palette(record, palette_set)
    ]
    _hardness._fitted.cache_clear()
    try:
        yield
    finally:
        _hardness.hardness_records = original
        _hardness._fitted.cache_clear()
        if cache is not None:
            os.environ["HEA_BENCH_MODEL_CACHE"] = cache


def _front_check(palette: list[str], measured: list) -> dict:
    """Search the palette, then place the measured alloys against the front."""
    result = search(
        elements=palette,
        n_elements=(4, 5),
        objectives=(Maximize("hardness"), Minimize("density")),
        step=STEP,
        n_candidates=250,
        optimize_bound="lower",
    )
    predicted = [
        predict_property(record.composition, "hardness").value for record in measured
    ]
    distances = [
        min(
            (_l1(record.composition, candidate.composition) for candidate in result.candidates),
            default=float("inf"),
        )
        for record in measured[:TOP_N]
    ]
    return {
        "result": result,
        "rho": _spearman(predicted, [record.value for record in measured]),
        "distances": distances,
        "recovered": sum(1 for distance in distances if distance <= 2 * STEP + 1e-9),
    }


def _study(name: str, palette: list[str]) -> list[str]:
    palette_set = set(palette)
    measured = [record for record in hardness_records() if _in_palette(record, palette_set)]
    measured.sort(key=lambda record: -record.value)

    trained = _front_check(palette, measured)
    with _palette_held_out(palette_set):
        held_out = _front_check(palette, measured)

    top = min(TOP_N, len(measured))
    lines = [
        f"## Palette {name}",
        "",
        f"Search: n_elements 4 to 5, step {STEP}, objectives maximize hardness "
        f"(conservative lower interval end) and minimize density, domain "
        f"constraint on. {trained['result'].n_evaluated} lattice points "
        f"evaluated, {trained['result'].n_feasible} feasible. Front size "
        f"{trained['result'].n_front} with the released model and "
        f"{held_out['result'].n_front} with the palette held out.",
        "",
        f"{len(measured)} measured alloys from the Borg hardness records live "
        f"inside this palette (4 or 5 elements). Rank correlation between the "
        f"model's point predictions and the measured hardness over those "
        f"alloys: Spearman rho {trained['rho']:.2f} with the released model, "
        f"{held_out['rho']:.2f} with the palette held out. Of the {top} hardest "
        f"measured alloys, {trained['recovered']} and {held_out['recovered']} "
        f"respectively sit within two lattice steps (L1) of a front member.",
        "",
        "| measured alloy | HV | processing | L1 to the front, released model | "
        "L1 to the front, palette held out |",
        "|---|---:|---|---:|---:|",
    ]

    def shown(distance: float) -> str:
        return f"{distance:.2f}" if distance != float("inf") else "n/a"

    for record, near, far in zip(measured, trained["distances"], held_out["distances"]):
        lines.append(
            f"| {record.formula_raw} | {record.value:.0f} | "
            f"{record.processing or '-'} | {shown(near)} | {shown(far)} |"
        )
    lines.append("")
    return lines


def main() -> int:
    try:
        import sklearn  # noqa: F401
    except ImportError:
        print('needs scikit-learn: pip install -e ".[properties]"', file=sys.stderr)
        return 2

    lines = [
        "# Retrospective recovery: does the search surface what was actually made?",
        "",
        f"Generated by `tools/design_recovery.py` with hea-bench "
        f"{_hea_bench_version} on {datetime.date.today().isoformat()}.",
        "",
        "Protocol: run the search over a heavily studied palette with the "
        "hardness-versus-density objectives, then place the alloys "
        "experimentalists measured (Borg hardness records inside the palette) "
        "relative to the returned front. Two readings matter and they are "
        "different: whether the hardest measured alloys are recovered near "
        "the front (retrospective sanity), and whether the surrogate ranks "
        "the measured alloys in the measured order (Spearman rho below; the "
        "model card's error analysis applies). Front members with no "
        "measured neighbor are suggestions the study never tested, not "
        "validated predictions, and a measured alloy far from the front is "
        "not refuted, it may simply be dominated on these two objectives or "
        "sit off the lattice.",
        "",
    ]
    for name, palette in PALETTES.items():
        lines += _study(name, palette)

    lines += [
        "## Reading the two columns",
        "",
        "With the released model, recovery is a necessary check rather than "
        "a test, because the model trained on these alloys. The held-out "
        "column is the test. There the model has seen no four- or "
        "five-element alloy of the palette, the situation of a palette no "
        "one has explored, and the front and the rank correlation say how "
        "far the search would have pointed toward the alloys later measured. "
        "The search is a screening aid whose value is receipts and "
        "constraint handling, not oracle ranking.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
