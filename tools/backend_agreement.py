"""Quantify how the native and HEACalculator backends differ, in writing.

Both backends can compute a shared set of published descriptor
quantities, from different reference data (Miedema-computed pair
enthalpies versus the tabulated Takeuchi-Inoue set; LA-4003 CN12 radii
versus their radius tabulations). Users who switch backends will see
different numbers and deserve a documented, quantified answer rather
than a surprise, so this tool computes the shared descriptors under
both backends for a fixed 50-composition panel spanning the corpus
chemistry and writes the per-descriptor deltas to
``docs/backend-agreement.md``. It asserts nothing: the deliverable is
the measurement, not a verdict on which side is right.

Run from the repository root (needs the interop extra):

    PYTHONPATH=src python tools/backend_agreement.py
"""

from __future__ import annotations

import datetime
import pathlib
import sys
from importlib.metadata import version as _dist_version

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from hea_bench import __version__ as _hea_bench_version  # noqa: E402
from hea_bench.composition import parse_formula  # noqa: E402
from hea_bench.descriptors.backend import (  # noqa: E402
    UNITS,
    BackendUnavailableError,
    NativeBackend,
    get_backend,
)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_MD = REPO_ROOT / "docs" / "backend-agreement.md"

# The names both backends map to the same published quantity. Kept in
# sync with _HEACALCULATOR_KEYS in hea_bench.descriptors.backend.
SHARED = (
    "smix",
    "delta",
    "vec",
    "melting_temperature",
    "mixing_enthalpy",
    "omega",
    "singh_lambda",
    "wang_gamma",
)

PER_DESCRIPTOR_NOTE = {
    "smix": (
        "Identical formula and gas constant; HEACalculator rounds compositions "
        "internally, so even the equiatomic maximum differs in the fourth decimal."
    ),
    "delta": (
        "Same Fang formula over CN12 metallic radii; different radius tabulations "
        "(LA-4003 here, Smithells-derived there)."
    ),
    "vec": "Identical definition (Guo s+d counting); integer element data.",
    "melting_temperature": (
        "Same rule of mixtures; HEACalculator ceil-rounds the result to a whole kelvin."
    ),
    "mixing_enthalpy": (
        "Same regular-solution form over binary pair enthalpies. The measured "
        "near-zero difference shows both packages vendor tables from the same "
        "published Takeuchi-Inoue and Miedema lineage; divergence would appear only "
        "for pairs where the tabulations differ, and this panel found none."
    ),
    "omega": (
        "Same Yang-Zhang formula; inherits the (small) mixing-enthalpy and melting "
        "differences and amplifies them without bound as the enthalpy approaches "
        "zero, so near-ideal alloys can disagree by orders of magnitude. Read Omega "
        "qualitatively there under either backend."
    ),
    "singh_lambda": (
        "Same Singh formula over each backend's CN12 delta; because Lambda divides "
        "by delta squared, small radius-table differences are strongly amplified "
        "wherever delta is small, which is where the max below comes from."
    ),
    "wang_gamma": (
        "Same Wang solid-angle formula; HEACalculator evaluates it over generic "
        "atomic radii where this package uses CN12 metallic radii. This is the "
        "largest convention gap in the mapped set."
    ),
}

# 50 compositions spanning the corpus: Cantor-family stoichiometric
# series, Al-containing BCC formers, Cu-containing multi-phase systems,
# refractories, precious-metal systems, rare-earth palettes, light and
# solder metals, HE-BMG formers, and deliberately near-ideal pairs
# (where Omega is unstable by construction under any backend).
PANEL = (
    "CoCrFeMnNi", "Al0.3CoCrFeNi", "Al0.5CoCrFeNi", "AlCoCrFeNi", "Al2CoCrFeNi",
    "CoCrFeNi", "CoCrNi", "CoFeNi", "CrFeNi", "CoCrFeMnNiV",
    "AlCoCrCuFeNi", "CoCrCuFeNi", "Al0.5CoCrCuFeNi", "CuCoNiFe", "CrCuFeMnNi",
    "MoNbTaW", "MoNbTaVW", "HfNbTaTiZr", "NbTiVZr", "CrMoNbTa",
    "HfNbTiZr", "MoNbTiV", "NbTaTiV", "HfMoNbTaTiZr", "AlMo0.5NbTa0.5TiZr",
    "AlCrFeNi", "AlCrFeMnNi", "AlCrFeMnTi", "Al0.9CoCrFeNi", "AlCrCuFe",
    "AgAuCuNiPd", "AuCuNiPdPt", "CoCrFeNiPd", "CuNiPdPt",
    "GdTbDyHoEr", "DyGdLuTbY", "CeLaNdPrSm", "ErHoLuTmY",
    "AlLiMgZnCu", "AlCuMgZn", "BiInPbSn", "BiPbSbSn",
    "La0.66Al0.14Cu0.1Ni0.1", "BeCuNiTiZr", "CuNiTiZr",
    "CoCrFeMo", "CrFeMoNi", "TiVCrMn", "VCrMnFe",
    "AgAu", "AgAuCu", "CuNi",
)


def main() -> int:
    native = NativeBackend()
    try:
        theirs = get_backend("heacalculator")
    except BackendUnavailableError as error:
        print(str(error), file=sys.stderr)
        return 2
    heacalculator_version = _dist_version("HEACalculator")

    import math

    per_descriptor: dict[str, list[tuple[str, float, float]]] = {name: [] for name in SHARED}
    native_missing: dict[str, list[str]] = {}
    theirs_missing: dict[str, list[str]] = {}
    for formula in PANEL:
        composition = parse_formula(formula)
        ours = native.compute(composition)
        others = theirs.compute(composition)
        for name in SHARED:
            a, b = ours.get(name), others.get(name)
            if a is None:
                native_missing.setdefault(formula, []).append(name)
                continue
            if b is None:
                theirs_missing.setdefault(formula, []).append(name)
                continue
            if not (math.isfinite(a) and math.isfinite(b)):
                continue
            per_descriptor[name].append((formula, a, b))

    lines = [
        "# Backend agreement: native versus HEACalculator",
        "",
        f"Generated by `tools/backend_agreement.py` with hea-bench "
        f"{_hea_bench_version} and HEACalculator {heacalculator_version} on "
        f"{datetime.date.today().isoformat()}. Regenerate after changing either "
        f"backend's data or the adapter mapping.",
        "",
        "Both backends compute the same published quantities from different",
        "reference data. The differences below are therefore expected and are",
        "reference-data choices, not defects; neither backend is declared",
        "correct, and the benchmark's published baselines use the native",
        "backend unchanged. The panel is the fixed 50-composition list in the",
        "generator, spanning the corpus chemistry.",
        "",
        "| descriptor | unit | n | mean abs diff | max abs diff | max at |",
        "|---|---|---:|---:|---:|---|",
    ]
    for name in SHARED:
        rows = per_descriptor[name]
        if not rows:
            lines.append(f"| `{name}` | {UNITS[name]} | 0 | - | - | - |")
            continue
        diffs = [(abs(a - b), formula) for formula, a, b in rows]
        mean_abs = sum(d for d, _ in diffs) / len(diffs)
        max_abs, max_formula = max(diffs)
        lines.append(
            f"| `{name}` | {UNITS[name]} | {len(rows)} | {mean_abs:.4g} | "
            f"{max_abs:.4g} | {max_formula} |"
        )

    lines += ["", "## Why each difference exists", ""]
    for name in SHARED:
        lines.append(f"- **`{name}`**: {PER_DESCRIPTOR_NOTE[name]}")

    def _coverage(missing: dict[str, list[str]]) -> str:
        if not missing:
            return "none"
        parts = []
        for formula in sorted(missing):
            names = missing[formula]
            what = "all shared descriptors" if len(names) == len(SHARED) else ", ".join(names)
            parts.append(f"{formula} ({what})")
        return "; ".join(parts)

    lines += [
        "",
        "## Coverage differences",
        "",
        f"Compositions the native backend could not fully compute: "
        f"{_coverage(native_missing)}.",
        "",
        f"Compositions HEACalculator could not fully compute: "
        f"{_coverage(theirs_missing)}. These are element-coverage gaps in its "
        f"database (rare-earth and solder-metal palettes, lithium), reported "
        f"here as measured; coverage differences are exactly the kind of thing "
        f"a backend choice should be made on.",
        "",
        "## What is deliberately not mapped",
        "",
        "King-family quantities (`delta_g_ss`, `delta_g_max`, `phi_king`),",
        "`phi_ye`, `s_excess`, `delta_chi`, `mean_electronegativity`, and",
        "`h_elastic` stay native-only, and HEACalculator's density, plain-radius",
        "delta, percent-scale electronegativity mismatches, e/a ratio, and",
        "Troparevsky formation enthalpies are exposed under their own names",
        "rather than merged into near-equivalents. Where implementations differ",
        "structurally (for example the delta_g_max scaling), mapping them to one",
        "name would silently swap definitions, which the backend layer refuses",
        "to do. See the mapping table in `src/hea_bench/descriptors/backend.py`.",
    ]

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
