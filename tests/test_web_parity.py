from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

import pytest

import hea_bench as hb
from hea_bench.rules import (
    guo_vec,
    king_phi,
    senkov_kappa,
    sheikh_ductility,
    tsai_sigma,
    yang_omega,
    ye_phi,
    yeh_smix,
    zhang_delta,
)

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "tests" / "data" / "web_parity_cases.json"
NODE_SNAPSHOT_SCRIPT = ROOT / "tests" / "web_parity_snapshot.cjs"

DESCRIPTOR_KEYS = (
    "Smix",
    "delta",
    "Tm_K",
    "Tm_C",
    "Hmix",
    "VEC",
    "Omega",
    "delta_chi",
    "mean_chi",
    "S_excess",
    "DeltaG_ss",
    "DeltaG_max",
    "Phi_king",
    "Phi_ye",
    "King_temperature_K",
    "Lambda_singh",
    "gamma_wang",
    "H_elastic",
)

RULE_KEYS = (
    "yeh_smix",
    "zhang_delta",
    "guo_vec",
    "yang_omega",
    "king_phi",
    "ye_phi",
    "senkov_kappa",
    "tsai_sigma",
    "sheikh_ductility",
)


def _load_cases() -> list[dict]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def _node_executable() -> str | None:
    path = shutil.which("node")
    if path:
        return path

    try:
        import nodejs  # type: ignore
    except ImportError:
        return None

    candidate = getattr(nodejs, "path", None)
    return str(candidate) if candidate else None


def _python_snapshot() -> dict[str, dict]:
    snapshot: dict[str, dict] = {}

    for case in _load_cases():
        composition = {str(key): float(value) for key, value in case["composition"].items()}
        king_temperature = case.get("king_temperature")

        melting_temperature = hb.melting_temperature(composition)
        effective_temperature = (
            float(king_temperature) if king_temperature is not None else melting_temperature
        )
        hmix = hb.mixing_enthalpy(composition)
        omega_value = hb.omega(composition)

        descriptors = {
            "Smix": hb.smix(composition),
            "delta": hb.delta(composition),
            "Tm_K": melting_temperature,
            "Tm_C": melting_temperature - 273.15,
            "Hmix": hmix,
            "VEC": hb.vec(composition),
            "Omega": omega_value,
            "delta_chi": hb.delta_chi(composition),
            "mean_chi": hb.mean_electronegativity(composition),
            "S_excess": hb.s_excess(composition),
            "DeltaG_ss": hb.delta_g_ss(composition, temperature=king_temperature),
            "DeltaG_max": hb.delta_g_max(composition),
            "Phi_king": hb.phi_king(composition, temperature=king_temperature),
            "Phi_ye": hb.phi_ye(composition),
            "King_temperature_K": effective_temperature,
            "Lambda_singh": hb.singh_lambda(composition),
            "gamma_wang": hb.wang_gamma(composition),
            "H_elastic": hb.h_elastic(composition),
        }

        rules = {
            "yeh_smix": {"verdict": yeh_smix.predict(composition)},
            "zhang_delta": {"verdict": zhang_delta.predict(composition)},
            "guo_vec": {"verdict": guo_vec.predict(composition)},
            "yang_omega": {
                "verdict": (
                    "single-phase"
                    if omega_value > yang_omega.DEFAULT_THRESHOLD
                    else "multi-phase"
                )
            },
            "king_phi": {
                "verdict": king_phi.predict(composition, temperature_policy=king_temperature)
            },
            "ye_phi": {"verdict": ye_phi.predict(composition)},
            "senkov_kappa": {
                "verdict": senkov_kappa.predict(
                    composition, temperature=king_temperature
                ).verdict
            },
            "tsai_sigma": {"verdict": tsai_sigma.predict(composition).verdict},
            "sheikh_ductility": {
                "verdict": sheikh_ductility.predict(composition).verdict
            },
        }

        snapshot[case["name"]] = {
            "descriptors": descriptors,
            "rules": rules,
        }

    return snapshot


def _decode_special_numbers(value):
    if isinstance(value, dict):
        return {key: _decode_special_numbers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_decode_special_numbers(item) for item in value]
    if value == "__Infinity__":
        return math.inf
    if value == "__-Infinity__":
        return -math.inf
    return value


def _js_snapshot() -> dict[str, dict]:
    node = _node_executable()
    if node is None:
        pytest.skip("Node.js executable not available for browser parity snapshot")

    completed = subprocess.run(
        [node, str(NODE_SNAPSHOT_SCRIPT)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return _decode_special_numbers(json.loads(completed.stdout))


def _assert_close(left: float, right: float, label: str) -> None:
    if math.isinf(left) or math.isinf(right):
        assert left == right, f"{label}: expected {left}, got {right}"
        return

    assert math.isclose(left, right, rel_tol=5e-4, abs_tol=5e-6), (
        f"{label}: expected {left}, got {right}"
    )


def test_browser_core_matches_python_descriptors_and_rules() -> None:
    python_snapshot = _python_snapshot()
    js_snapshot = _js_snapshot()

    assert set(js_snapshot) == set(python_snapshot)

    for case_name, expected in python_snapshot.items():
        actual = js_snapshot[case_name]
        assert actual["warnings"] == []

        for key in DESCRIPTOR_KEYS:
            left = expected["descriptors"][key]
            right = actual["descriptors"][key]
            assert right is not None, f"{case_name}.{key} should not be null"
            _assert_close(left, right, f"{case_name}.{key}")

        for key in RULE_KEYS:
            assert actual["rules"][key]["verdict"] == expected["rules"][key]["verdict"]