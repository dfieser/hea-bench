"""Browser-compatible Miedema descriptor helpers.

The public HTML calculator historically used an on-the-fly Miedema
chemical-term calculation for the displayed ``Hmix`` and ``Omega``
cards instead of the vendored binary pair-enthalpy table used by the
benchmark library's default :mod:`hea_bench.descriptors.miedema`
implementation.

This module exposes that calculator-compatible path explicitly so the
same numbers can be reproduced from Python without mutating the
benchmark-stable default descriptor definitions.
"""

from __future__ import annotations

import math
from itertools import combinations

from ..composition import Composition
from .entropy import smix
from .melting import melting_temperature


# 30-element calculator coverage. The original 24 (v1.1) match the JS
# browser core byte-for-byte; the six v1.2 additions (Au, Li, Mg, Re,
# Sn, Zn) come from matminer's Miedema parameter table with V23 =
# molar_volume**(2/3) and nws13 = electron_density**(1/3), rounded to
# two decimals. The class (TM/NTM) follows Miedema's group convention:
# alkali, alkaline-earth, group 12, and p-block are NTM; everything else
# in our set is TM. The browser core mirrors these values exactly.
_MIEDEMA_PARAMS: dict[str, dict[str, float | str]] = {
    "Ag": {"phi_star": 4.35, "nws13": 1.36, "V23": 4.72, "cls": "TM"},
    "Al": {"phi_star": 4.20, "nws13": 1.39, "V23": 4.64, "cls": "NTM"},
    "Au": {"phi_star": 5.15, "nws13": 1.57, "V23": 4.70, "cls": "TM"},
    "Co": {"phi_star": 5.10, "nws13": 1.75, "V23": 3.55, "cls": "TM"},
    "Cr": {"phi_star": 4.65, "nws13": 1.73, "V23": 3.74, "cls": "TM"},
    "Cu": {"phi_star": 4.45, "nws13": 1.47, "V23": 3.70, "cls": "TM"},
    "Fe": {"phi_star": 4.93, "nws13": 1.77, "V23": 3.69, "cls": "TM"},
    "Hf": {"phi_star": 3.60, "nws13": 1.45, "V23": 5.65, "cls": "TM"},
    "Ir": {"phi_star": 5.55, "nws13": 1.83, "V23": 4.17, "cls": "TM"},
    "Li": {"phi_star": 2.85, "nws13": 0.98, "V23": 5.53, "cls": "NTM"},
    "Mg": {"phi_star": 3.45, "nws13": 1.17, "V23": 5.81, "cls": "NTM"},
    "Mn": {"phi_star": 4.45, "nws13": 1.61, "V23": 3.78, "cls": "TM"},
    "Mo": {"phi_star": 4.65, "nws13": 1.77, "V23": 4.45, "cls": "TM"},
    "Nb": {"phi_star": 4.05, "nws13": 1.64, "V23": 4.89, "cls": "TM"},
    "Ni": {"phi_star": 5.20, "nws13": 1.75, "V23": 3.52, "cls": "TM"},
    "Os": {"phi_star": 5.40, "nws13": 1.85, "V23": 4.15, "cls": "TM"},
    "Pd": {"phi_star": 5.45, "nws13": 1.67, "V23": 4.29, "cls": "TM"},
    "Pt": {"phi_star": 5.65, "nws13": 1.78, "V23": 4.36, "cls": "TM"},
    "Re": {"phi_star": 5.20, "nws13": 1.85, "V23": 4.28, "cls": "TM"},
    "Rh": {"phi_star": 5.40, "nws13": 1.76, "V23": 4.10, "cls": "TM"},
    "Ru": {"phi_star": 5.40, "nws13": 1.83, "V23": 4.60, "cls": "TM"},
    "Si": {"phi_star": 4.70, "nws13": 1.50, "V23": 4.20, "cls": "NTM"},
    "Sn": {"phi_star": 4.15, "nws13": 1.24, "V23": 6.43, "cls": "NTM"},
    "Ta": {"phi_star": 4.05, "nws13": 1.63, "V23": 4.89, "cls": "TM"},
    "Ti": {"phi_star": 3.80, "nws13": 1.52, "V23": 4.12, "cls": "TM"},
    "V": {"phi_star": 4.25, "nws13": 1.64, "V23": 4.12, "cls": "TM"},
    "W": {"phi_star": 4.80, "nws13": 1.81, "V23": 4.50, "cls": "TM"},
    "Y": {"phi_star": 3.20, "nws13": 1.21, "V23": 7.34, "cls": "TM"},
    "Zn": {"phi_star": 4.10, "nws13": 1.32, "V23": 4.38, "cls": "NTM"},
    "Zr": {"phi_star": 3.45, "nws13": 1.41, "V23": 5.81, "cls": "TM"},
}

_PAIR_P = {"TM-TM": 14.2, "TM-NTM": 12.35, "NTM-NTM": 10.7}
_QP_RATIO = 9.4
# Ionicity correction R/P (matminer R_const). Only NTM elements with a
# meaningful value are listed; TM elements default to 1.0 (this matches
# the legacy v1.1 calculator behavior, which also omitted nonzero R for
# TMs like Ag/Cu/Au, and matches the JS browser core exactly). Li is
# similarly omitted because its R=0 would collide with the JS `||` zero-
# fallback semantics, and Li-NTM-NTM pairs are vanishingly rare in the
# benchmark.
_R_OVER_P = {"Al": 1.9, "Mg": 0.4, "Si": 2.1, "Sn": 2.1, "Zn": 1.4}
_A_VOL = {
    "Ag": 0.07,
    "Al": 0.07,
    "Au": 0.07,
    "Co": 0.04,
    "Cr": 0.04,
    "Cu": 0.07,
    "Fe": 0.04,
    "Hf": 0.04,
    "Ir": 0.04,
    "Li": 0.14,
    "Mg": 0.10,
    "Mn": 0.04,
    "Mo": 0.04,
    "Nb": 0.04,
    "Ni": 0.04,
    "Os": 0.04,
    "Pd": 0.04,
    "Pt": 0.04,
    "Re": 0.04,
    "Rh": 0.04,
    "Ru": 0.04,
    "Si": 0.04,
    "Sn": 0.04,
    "Ta": 0.04,
    "Ti": 0.04,
    "V": 0.04,
    "W": 0.04,
    "Y": 0.04,
    "Zn": 0.10,
    "Zr": 0.04,
}


def covered_elements() -> set[str]:
    """Return the calculator-compatible element set."""
    return set(_MIEDEMA_PARAMS)


def _normalize(composition: Composition) -> dict[str, float]:
    if not composition:
        raise ValueError("composition must be non-empty")

    total = sum(composition.values())
    if total <= 0:
        raise ValueError("composition values must sum to a positive number")

    return {element: amount / total for element, amount in composition.items() if amount > 0}


def browser_pair_enthalpy(elem_a: str, elem_b: str) -> float:
    """Calculator-compatible equiatomic binary mixing enthalpy (kJ/mol)."""
    if elem_a == elem_b:
        return 0.0

    missing = sorted({elem_a, elem_b} - covered_elements())
    if missing:
        raise ValueError(
            "composition contains elements not in browser Miedema calculator data: "
            f"{missing}"
        )

    params_a = _MIEDEMA_PARAMS[elem_a]
    params_b = _MIEDEMA_PARAMS[elem_b]
    cls_a = str(params_a["cls"])
    cls_b = str(params_b["cls"])

    if cls_a == "TM" and cls_b == "TM":
        pair_type = "TM-TM"
    elif cls_a == "NTM" and cls_b == "NTM":
        pair_type = "NTM-NTM"
    else:
        pair_type = "TM-NTM"

    p_const = _PAIR_P[pair_type]
    q_const = p_const * _QP_RATIO

    r_val = 0.0
    if pair_type != "TM-TM":
        r_val = _R_OVER_P.get(elem_a, 1.0) * _R_OVER_P.get(elem_b, 1.0) * p_const

    d_phi = float(params_a["phi_star"]) - float(params_b["phi_star"])
    d_nws = float(params_a["nws13"]) - float(params_b["nws13"])

    v23_a = float(params_a["V23"])
    v23_b = float(params_b["V23"])
    a_a = _A_VOL.get(elem_a, 0.04)
    a_b = _A_VOL.get(elem_b, 0.04)

    for _ in range(5):
        cs_b = v23_b / (v23_a + v23_b)
        cs_a = v23_a / (v23_a + v23_b)
        v23_a = float(params_a["V23"]) * (1.0 + a_a * cs_b * d_phi)
        v23_b = float(params_b["V23"]) * (1.0 - a_b * cs_a * d_phi)

    volume_factor = (2.0 * v23_a * v23_b) / (v23_a + v23_b)
    nws_avg_inv = 0.5 * (1.0 / float(params_a["nws13"]) + 1.0 / float(params_b["nws13"]))
    interfacial_energy = (-p_const * d_phi * d_phi + q_const * d_nws * d_nws - r_val) / nws_avg_inv

    return volume_factor * interfacial_energy


def browser_mixing_enthalpy(composition: Composition) -> float:
    """Calculator-compatible multi-component mixing enthalpy ``Hmix`` (kJ/mol)."""
    norm = _normalize(composition)

    missing = set(norm) - covered_elements()
    if missing:
        raise ValueError(
            "composition contains elements not in browser Miedema calculator data: "
            f"{sorted(missing)}"
        )

    total = 0.0
    for elem_a, elem_b in combinations(sorted(norm), 2):
        total += 4.0 * norm[elem_a] * norm[elem_b] * browser_pair_enthalpy(elem_a, elem_b)
    return total


def browser_omega(composition: Composition) -> float:
    """Calculator-compatible Yang-Zhang ``Omega`` using the browser ``Hmix`` path."""
    entropy = smix(composition)
    temperature = melting_temperature(composition)
    enthalpy = browser_mixing_enthalpy(composition)

    if enthalpy == 0.0:
        return math.inf

    return (temperature * entropy) / (abs(enthalpy) * 1000.0)