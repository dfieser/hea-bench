"""Use every feature of an INSTALLED hea-bench: the MCP server, then the library.

tests/test_installed_package.py runs this inside a fresh virtual
environment that has only the built wheel installed (with its ``mcp``
extra), from a folder outside the repository, with the per-user data
folder pointed at an empty temporary one. So it sees exactly what a
PyPI user gets, and it proves that

1. the package imports from the environment, never from a checkout,
2. every MCP tool answers over real stdio from the installed
   ``hea-bench-mcp`` command, the way an MCP client starts it, starting
   from an unbuilt corpus (``corpus_build`` comes first),
3. the library's features work from the wheel's own data.

Usage: python package_smoke.py <work-dir> [<peivaste-csv>]
Without the Peivaste CSV the corpus build downloads it (6.4 MB).
"""

from __future__ import annotations

import asyncio
import csv
import json
import os
import pathlib
import shutil
import subprocess
import sys

WORK = pathlib.Path(sys.argv[1]).resolve()
PEIVASTE = sys.argv[2] if len(sys.argv) > 2 else None
BIN = pathlib.Path(sys.executable).parent

XX = {"Xx": {"radius_pm": 140.0, "melting_K": 1800.0, "valence": 6, "electronegativity": 1.7}}
XX_PAIRS = {"Co-Xx": -5.0, "Cr-Xx": -3.0, "Fe-Xx": -4.0, "Ni-Xx": -6.0}
CAMPAIGN = {
    "schema": 1,
    "objective": "hardness",
    "direction": "maximize",
    "palette": ["Al", "Co", "Cr", "Fe", "Ni"],
    "constraints": [{"type": "DomainConstraint", "in_domain": None}],
    "seed": 0,
    "step": 0.25,
    "n_elements": [4, 5],
    "warm_start": True,
    "observations": [{"composition": "AlCoCrFe", "value": 480.0}],
}

#: Every MCP tool, in call order, with arguments that use the feature and a
#: check on the answer. tests/test_feature_parity.py fails when a tool is
#: missing here.
TOOL_CALLS = [
    ("about", {}, lambda r: r["capabilities"]["corpus"] is False),
    ("corpus_build", {"peivaste_csv": PEIVASTE} if PEIVASTE else {},
     lambda r: r["built"]["0.1.0"]["totals"]["unique_compositions"] == 7783
     and "0.2.0" in r["built"]),
    ("parse_composition", {"formula": "Al0.3CoCrFeNi"}, lambda r: abs(sum(r["composition"].values()) - 1) < 1e-9),
    ("alloy_descriptors", {"compositions": ["CoCrFeMnNi", "CoCrFeNiXx"], "custom_elements": XX,
                           "pair_enthalpies": XX_PAIRS},
     lambda r: abs(r["results"][0]["descriptors"]["s_mix"]["value"] - 13.381) < 1e-3
     and r["results"][0]["miedema_enthalpies"]["compound"] is not None
     and r["results"][1]["descriptors"]["omega"]["value"] is not None),
    ("alloy_rules", {"compositions": ["CoCrFeMnNi"]}, lambda r: r["results"][0]["rules"]["guo_vec"]["verdict"]),
    ("omega_sensitivity", {"composition": "CoCrFeMnNi"}, lambda r: r["omega"] is not None),
    ("oxide_report", {"family": "rock_salt", "cations": "MgCoNiCuZn"}, lambda r: "warnings" in r),
    ("ceramic_report", {"structure": "rock_salt_carbide", "metals": "HfNbTaTiZr"},
     lambda r: r["vec_per_formula_unit"] is not None),
    ("element_data", {"elements": ["Co", "Cr"]}, lambda r: set(r["elements"]) == {"Co", "Cr"}),
    ("element_coverage", {}, lambda r: r["alloy_count"] == 55),
    ("corpus_query", {"contains": ["Al"], "phase": "BCC", "limit": 3},
     lambda r: r["corpus_version"] == "0.2.0" and r["n_matching"] > 0 and len(r["sample"]) == 3),
    ("corpus_describe", {"version": "0.1.0"}, lambda r: r["n_rows"] == 7783),
    ("corpus_export", {"path": str(WORK / "titanium.csv"), "contains": ["Ti"]}, lambda r: r["n_rows"] > 0),
    ("measured_properties", {"prop": "hardness", "contains": ["Al"], "limit": 3},
     lambda r: r["unit"] == "HV" and len(r["rows"]) == 3),
    ("predict_properties", {"compositions": ["AlCoCrFeNi"]},
     lambda r: r["results"][0]["properties"]["hardness"]["tier"] == "B"),
    ("predict_phase_set", {"compositions": ["CoCrFeMnNi"], "task": "phase4"},
     lambda r: r["results"][0]["prediction_set"]),
    ("check_applicability", {"composition": "CoCrFeMnNi"}, lambda r: r["in_domain"] is True),
    ("design_search", {"elements": ["Al", "Fe", "W"], "n_elements_min": 2, "n_elements_max": 3, "step": 0.2,
                       "objectives": [["minimize", "density"]], "include_out_of_domain": True},
     lambda r: r["candidates"]),
    ("campaign_suggest", {"campaign": CAMPAIGN, "n": 2}, lambda r: len(r["suggestions"]) == 2),
    ("benchmark_summary", {}, lambda r: r["digests"]["verified"] is True),
    ("benchmark_run", {"model": "rule:yang_omega"}, lambda r: "gap" in r),
    ("benchmark_folds", {"path": str(WORK / "folds.csv")}, lambda r: r["n_rows"] > 0),
    ("benchmark_score", {"predictions_path": str(WORK / "predictions.csv"), "model_name": "all multi"},
     lambda r: r["model"] == "all multi" and "gap" in r),
    ("coverage_study", {}, lambda r: r["levels"]),
]


def write_predictions() -> None:
    """A trivial model's predictions for benchmark_score: multi-phase everywhere."""
    with (WORK / "folds.csv").open(newline="", encoding="utf-8") as handle:
        keys = [row["composition_key"] for row in csv.DictReader(handle)]
    with (WORK / "predictions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["composition_key", "grouped", "random"])
        writer.writerows([key, "multi-phase", "multi-phase"] for key in keys)


async def use_every_mcp_tool() -> None:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    command = shutil.which("hea-bench-mcp", path=str(BIN))
    assert command, f"the installed hea-bench-mcp command is missing from {BIN}"
    server = StdioServerParameters(command=command, env=dict(os.environ), cwd=str(WORK))
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = {tool.name for tool in (await session.list_tools()).tools}
            called = [name for name, _, _ in TOOL_CALLS]
            assert listed == set(called), f"listed but not called: {listed - set(called)}"
            for name, arguments, check in TOOL_CALLS:
                if name == "benchmark_score":
                    write_predictions()
                result = await session.call_tool(name, arguments, read_timeout_seconds=900)
                text = result.content[0].text if result.content else ""
                assert not result.is_error, f"{name} failed: {text}"
                payload = json.loads(text)
                assert check(payload), f"{name} answered unexpectedly: {text[:600]}"
                print(f"mcp {name}: ok", flush=True)


def use_the_library() -> None:
    import hea_bench as hb
    from hea_bench import _paths
    from hea_bench.benchmark import load_benchmark
    from hea_bench.benchmark.frozen import verify_split_digests
    from hea_bench.corpus import build_corpus, load_corpus
    from hea_bench.descriptors.elements import element_data
    from hea_bench.descriptors.miedema_decomposition import miedema_decomposition
    from hea_bench.properties import predict_property
    from hea_bench.uncertainty.phase import predict_phase_set

    assert _paths.installed(), f"imported a checkout, not the wheel: {hb.__file__}"
    cantor = hb.parse_formula("CoCrFeMnNi")
    assert abs(hb.smix(cantor) - 13.381) < 1e-3
    with hb.custom_data(elements=XX, pair_enthalpies=XX_PAIRS):
        assert hb.omega(hb.parse_formula("CoCrFeNiXx")) > 0
    assert hb.omega_sensitivity(cantor)["omega"] > 0
    assert len(element_data()["elements"]) == 55
    assert round(miedema_decomposition({"Cu": 0.5, "Zr": 0.5})["compound"]["H_form"], 2) == -30.78
    assert predict_property(cantor, "hardness").value > 0
    built = build_corpus(peivaste_csv=PEIVASTE)
    assert set(built) == {"0.1.0", "0.2.0"}
    assert load_corpus().version == "0.2.0"
    assert len(load_corpus(version="0.1.0")) == 7783
    assert verify_split_digests(load_benchmark())["verified"]
    assert predict_phase_set(cantor)["prediction_set"]
    version = subprocess.run(
        [str(BIN / "hea-bench"), "--version"], capture_output=True, text=True, check=True
    ).stdout
    assert hb.__version__ in version, version
    print("library: ok", flush=True)


if __name__ == "__main__":
    WORK.mkdir(parents=True, exist_ok=True)
    asyncio.run(use_every_mcp_tool())
    use_the_library()
    print("PACKAGE SMOKE OK")
