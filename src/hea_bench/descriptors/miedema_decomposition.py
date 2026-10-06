"""Miedema formation enthalpies: compound, solid solution and amorphous.

The calculator's "Miedema-model formation enthalpies" panel, as a
library function. For a multi-component alloy the binary terms are
summed over element pairs:

- the formation enthalpy of the ordered intermetallic compound
  (de Boer et al. 1988, Eqs. 3-6, with the composition-independent
  size factor of Zhang et al. 2016);
- the solid-solution enthalpy as the sum of a chemical term (Eq. 8a),
  an Eshelby-Friedel elastic-mismatch term (Eqs. 9-11) and a structural
  term from the lattice stabilities of Niessen & Miedema (1983);
- the amorphous enthalpy as the chemical term plus the topological term
  of Loeff, Weeber & Miedema (1988), ``beta * sum(c_i Tm_i)`` with beta
  = 3.5 J/(mol K).

Per-element parameters are the vendored matminer Miedema table
(``data/miedema_parameters.csv``); the two qualitative fields it lacks,
the Miedema class and the equilibrium structure, are curated in
:data:`MIEDEMA_CLASSES`, which also fixes which 37 elements have a row.
The browser core's copy of this table is generated from these same
sources by ``tests/data/_sync_js_tables.py``, and
``tests/test_web_miedema.py`` holds both implementations to the same
pinned values.

All enthalpies are in kJ/mol.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
from pathlib import Path

from ..composition import Composition, normalize
from ._tables import element

_CSV_PATH = Path(__file__).resolve().parent / "data" / "miedema_parameters.csv"

#: Per element, the Miedema class (TM or NTM, which picks the P constant
#: and whether the hybridization R term applies) and the equilibrium
#: crystal structure (CRC Handbook, the reference lattice-stability
#: energy of the structural term). The keys define which elements have a
#: decomposition row; everything quantitative comes from the CSV.
MIEDEMA_CLASSES = {
    "Ag": ("TM", "fcc"),
    "Al": ("NTM", "fcc"),
    "Au": ("TM", "fcc"),
    "Be": ("NTM", "hcp"),
    "Ca": ("NTM", "fcc"),
    "Ce": ("TM", "fcc"),
    "Co": ("TM", "hcp"),
    "Cr": ("TM", "bcc"),
    "Cu": ("TM", "fcc"),
    "Fe": ("TM", "bcc"),
    "Gd": ("TM", "hcp"),
    "Hf": ("TM", "hcp"),
    "In": ("NTM", "fcc"),
    "Ir": ("TM", "fcc"),
    "La": ("TM", "hcp"),
    "Li": ("NTM", "bcc"),
    "Mg": ("NTM", "hcp"),
    "Mn": ("TM", "bcc"),
    "Mo": ("TM", "bcc"),
    "Nb": ("TM", "bcc"),
    "Ni": ("TM", "fcc"),
    "Os": ("TM", "hcp"),
    "Pd": ("TM", "fcc"),
    "Pt": ("TM", "fcc"),
    "Re": ("TM", "hcp"),
    "Rh": ("TM", "fcc"),
    "Ru": ("TM", "hcp"),
    "Sc": ("TM", "hcp"),
    "Si": ("NTM", "fcc"),
    "Sn": ("NTM", "bcc"),
    "Ta": ("TM", "bcc"),
    "Ti": ("TM", "hcp"),
    "V": ("TM", "bcc"),
    "W": ("TM", "bcc"),
    "Y": ("TM", "hcp"),
    "Zn": ("NTM", "hcp"),
    "Zr": ("TM", "hcp"),
}

_P_CONST = {"TM-TM": 14.2, "TM-NTM": 12.35, "NTM-NTM": 10.7}
_QP_RATIO = 9.4
#: Topological enthalpy constant beta (Loeff et al., Eq. 16a).
_BETA_TOPO = 3.5
#: (z, E_fcc - E_bcc, E_hcp - E_bcc) in kJ/mol versus valence electron
#: count z, interpolated linearly between integer z.
_LATTICE_STABILITY = (
    (1, -2.0, -2.0),
    (2, -4.0, -3.0),
    (3, 0.5, -1.5),
    (4, 5.5, 2.5),
    (5, 5.5, 3.5),
    (6, 3.5, 2.0),
    (7, -0.5, -0.5),
    (8, -5.5, -3.5),
    (9, -5.5, -3.5),
    (10, 0.0, 0.0),
    (11, 0.0, 0.0),
    (12, 0.0, 0.0),
)


@dataclass(frozen=True)
class _Row:
    phi: float
    nws: float
    vm: float
    k: float
    g: float
    a_vol: float
    r_over_p: float
    h_trans: float
    cls: str
    struct: str


@lru_cache(maxsize=1)
def _table() -> dict[str, _Row]:
    with _CSV_PATH.open(newline="", encoding="utf-8") as handle:
        rows = {row["element"]: row for row in csv.DictReader(handle)}
    return {
        symbol: _Row(
            phi=float(rows[symbol]["electronegativity"]),
            nws=float(rows[symbol]["electron_density"]),
            vm=float(rows[symbol]["molar_volume"]),
            k=float(rows[symbol]["compressibility"]),
            g=float(rows[symbol]["shear_modulus"]),
            a_vol=float(rows[symbol]["a_const"]),
            r_over_p=float(rows[symbol]["R_const"]),
            h_trans=float(rows[symbol]["H_trans"]),
            cls=cls,
            struct=struct,
        )
        for symbol, (cls, struct) in MIEDEMA_CLASSES.items()
    }


def _lattice_stability(z: float) -> dict[str, float]:
    first, last = _LATTICE_STABILITY[0], _LATTICE_STABILITY[-1]
    if z <= first[0]:
        return {"bcc": 0.0, "fcc": first[1], "hcp": first[2]}
    if z >= last[0]:
        return {"bcc": 0.0, "fcc": last[1], "hcp": last[2]}
    for lo, hi in zip(_LATTICE_STABILITY, _LATTICE_STABILITY[1:]):
        if lo[0] <= z <= hi[0]:
            t = (z - lo[0]) / (hi[0] - lo[0])
            return {"bcc": 0.0, "fcc": lo[1] + t * (hi[1] - lo[1]), "hcp": lo[2] + t * (hi[2] - lo[2])}
    return {"bcc": 0.0, "fcc": 0.0, "hcp": 0.0}


def _v23(row: _Row) -> float:
    return row.vm ** (2.0 / 3.0)


def pair_details(a: str, b: str) -> dict | None:
    """Interfacial enthalpy amplitude and dilute-limit interfacial enthalpies
    for one pair (de Boer Eqs. 1 and 2.10), or None outside the table."""
    table = _table()
    pa, pb = table.get(a), table.get(b)
    if pa is None or pb is None:
        return None
    if a == b:
        return {"gammaAB": 0.0, "H_inter_AinB": 0.0, "H_inter_BinA": 0.0,
                "pairType": "TM-TM", "P": 14.2, "Q": 133.48, "R_val": 0.0}
    if pa.cls == "TM" and pb.cls == "TM":
        pair_type = "TM-TM"
    elif pa.cls == "NTM" and pb.cls == "NTM":
        pair_type = "NTM-NTM"
    else:
        pair_type = "TM-NTM"
    p = _P_CONST[pair_type]
    q = p * _QP_RATIO
    r = pa.r_over_p * pb.r_over_p * p if pair_type != "TM-TM" else 0.0
    nws_a, nws_b = math.pow(pa.nws, 1.0 / 3.0), math.pow(pb.nws, 1.0 / 3.0)
    d_phi = pa.phi - pb.phi
    d_nws = nws_a - nws_b
    nws_avg_inv = 0.5 * (1.0 / nws_a + 1.0 / nws_b)
    gamma = (-p * d_phi * d_phi + q * d_nws * d_nws - r) / nws_avg_inv
    v23_a = _v23(pa) * (1.0 + pa.a_vol * d_phi)
    v23_b = _v23(pb) * (1.0 - pb.a_vol * d_phi)
    return {"gammaAB": gamma, "H_inter_AinB": v23_a * gamma, "H_inter_BinA": v23_b * gamma,
            "pairType": pair_type, "P": p, "Q": q, "R_val": r}


def _surface_concentrations(pa: _Row, pb: _Row, ca: float, cb: float) -> tuple[float, float]:
    va, vb = _v23(pa), _v23(pb)
    denominator = ca * va + cb * vb
    if denominator == 0:
        return 0.5, 0.5
    return ca * va / denominator, cb * vb / denominator


def _compound(a: str, b: str, ca: float, cb: float) -> float | None:
    details = pair_details(a, b)
    if details is None:
        return None
    pa, pb = _table()[a], _table()[b]
    va, vb = _v23(pa), _v23(pb)
    csa, csb = _surface_concentrations(pa, pb, ca, cb)
    f_ab = csa * csb * (1.0 + 8.0 * (csa * csb) ** 2)
    h_miedema = f_ab * (ca * va + cb * vb) * details["gammaAB"]
    size_factor = (va * vb) / ((va + vb) / 2.0) ** 2
    return size_factor * h_miedema + ca * pa.h_trans + cb * pb.h_trans


def _ss_chemical(a: str, b: str, ca: float, cb: float) -> float | None:
    details = pair_details(a, b)
    if details is None:
        return None
    pa, pb = _table()[a], _table()[b]
    csa, csb = _surface_concentrations(pa, pb, ca, cb)
    return ca * cb * (csb * _v23(pa) + csa * _v23(pb)) * details["gammaAB"]


def _ss_elastic(a: str, b: str, ca: float, cb: float) -> float:
    pa, pb = _table()[a], _table()[b]
    d_ab = 3.0 * pa.k * pb.vm + 4.0 * pb.g * pa.vm
    h_ab = (2.0 * pa.k * pb.g * (pa.vm - pb.vm) ** 2) / d_ab if d_ab != 0 else 0.0
    d_ba = 3.0 * pb.k * pa.vm + 4.0 * pa.g * pb.vm
    h_ba = (2.0 * pb.k * pa.g * (pb.vm - pa.vm) ** 2) / d_ba if d_ba != 0 else 0.0
    return ca * cb * (cb * h_ab + ca * h_ba)


def _ss_structural(a: str, b: str, ca: float, cb: float) -> float:
    pa, pb = _table()[a], _table()[b]
    za, zb = element(a).valence, element(b).valence
    average = _lattice_stability(ca * za + cb * zb)
    e_avg = min(average["bcc"], average["fcc"], average["hcp"])
    return e_avg - (ca * _lattice_stability(za)[pa.struct] + cb * _lattice_stability(zb)[pb.struct])


def miedema_decomposition(composition: Composition) -> dict:
    """Compound, solid-solution and amorphous formation enthalpies (kJ/mol).

    Parameters
    ----------
    composition
        Mapping of element symbol to amount (normalized here). Pairs
        outside the 37-element Miedema table make the three totals
        unavailable (None) with a warning naming the pairs; the core
        descriptors are unaffected.

    Returns
    -------
    dict
        ``compound`` ({``H_form``}), ``solid_solution`` ({``H_chem``,
        ``H_elast``, ``H_struct``, ``H_total``}), ``amorphous``
        ({``H_chem``, ``H_topo``, ``H_total``}), each None when a pair
        lacks parameters, and ``warnings``.

    Examples
    --------
    >>> d = miedema_decomposition({"Cu": 0.5, "Zr": 0.5})
    >>> round(d["compound"]["H_form"], 2), round(d["amorphous"]["H_total"], 2)
    (-30.78, -16.19)
    """
    fractions = dict(normalize(composition))
    table = _table()
    compound = ss_chem = ss_elast = ss_struct = am_topo = 0.0
    missing = []
    for a, b in combinations(list(fractions), 2):
        ca, cb = fractions[a], fractions[b]
        if a not in table or b not in table:
            missing.append(f"{a}–{b}")
            continue
        h_form = _compound(a, b, ca / (ca + cb), cb / (ca + cb))
        compound += (ca + cb) * h_form
        ss_chem += _ss_chemical(a, b, ca, cb)
        ss_elast += _ss_elastic(a, b, ca, cb)
        ss_struct += _ss_structural(a, b, ca, cb)
        am_topo += _BETA_TOPO * (ca * element(a).melting_K + cb * element(b).melting_K) / 1000.0
    warnings = []
    if missing:
        warnings.append(
            f"Missing Miedema data for {missing[0]} compound enthalpy."
            if len(missing) == 1 else
            f"Miedema decomposition unavailable: {len(missing)} element pairs lack Miedema "
            f"parameters ({', '.join(missing)}). Core descriptors are unaffected; see the Data "
            f"view coverage matrix."
        )
        return {"compound": None, "solid_solution": None, "amorphous": None, "warnings": warnings}
    return {
        "compound": {"H_form": compound},
        "solid_solution": {
            "H_chem": ss_chem,
            "H_elast": ss_elast,
            "H_struct": ss_struct,
            "H_total": ss_chem + ss_elast + ss_struct,
        },
        "amorphous": {"H_chem": ss_chem, "H_topo": am_topo, "H_total": ss_chem + am_topo},
        "warnings": warnings,
    }


__all__ = ["MIEDEMA_CLASSES", "miedema_decomposition", "pair_details"]
