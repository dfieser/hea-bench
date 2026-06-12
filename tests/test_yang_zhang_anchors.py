"""Literature anchors: Yang & Zhang (2012) Table 1 per-alloy values.

Pins the engine against the published per-alloy descriptor values of
Yang & Zhang, Mater. Chem. Phys. 132, 233 (2012), Table 1 — the paper
that defines Ω. These are the manuscript's alloy-side anchor rows
(Table "Yang–Zhang reference alloys"), so a change that moves any of
them must fail the build.

Tolerances are quantity-specific and reflect convention boundaries,
not slack:

* dHmix: ±0.01 kJ/mol. Yang & Zhang used the Takeuchi–Inoue pair
  table; our vendored matminer table digitizes the same source, so
  agreement is exact up to their two-decimal rounding.
* smix: ±0.02 J/(mol K). Convention-free (ideal mixing identity);
  the band covers Yang & Zhang's own printed rounding (their
  Ti0.8CoCrFeNiCu row prints 14.89 where the identity gives 14.871).
* omega: ±2.5% relative. Inherits the elemental melting-temperature
  compilation difference through the rule-of-mixtures T_m.
* delta: ±0.35 absolute (percentage points). The atomic-radius set
  differs between compilations; the formula is identical.
"""

import pytest

from hea_bench.descriptors.entropy import smix
from hea_bench.descriptors.miedema import mixing_enthalpy
from hea_bench.descriptors.omega import omega
from hea_bench.descriptors.size import delta

# (composition, published delta %, published dHmix kJ/mol,
#  published smix J/(mol K), published omega)
# Verbatim from Yang & Zhang 2012, Table 1.
YZ_ROWS = [
    ({"Co": 1, "Cr": 1, "Fe": 1, "Ni": 1, "Mo": 0.3},
     2.92, -4.15, 12.83, 5.97),
    ({"Co": 1, "Cr": 1, "Fe": 1, "Ni": 1, "Al": 0.3, "Mo": 0.1},
     3.74, -7.26, 13.44, 3.37),
    ({"Co": 1, "Cr": 1, "Fe": 1, "Ni": 1, "Cu": 1, "Al": 1, "Mo": 0.2},
     4.95, -4.47, 15.60, 5.70),
    ({"Ti": 0.8, "Co": 1, "Cr": 1, "Fe": 1, "Ni": 1, "Cu": 1},
     5.26, -6.75, 14.89, 3.95),
    ({"Ti": 1, "Co": 1, "Cr": 1, "Fe": 1, "Ni": 1, "Cu": 1},
     5.65, -8.44, 14.90, 3.17),
    ({"Ti": 1.5, "Co": 1, "Cr": 1, "Fe": 1, "Ni": 1, "Al": 1},
     6.93, -23.91, 14.78, 1.08),
    ({"Co": 1, "Cr": 1, "Fe": 1, "Ni": 1, "Cu": 1, "Al": 1, "Mn": 1},
     4.57, -5.63, 16.18, 4.61),
    ({"Cr": 1, "Fe": 1, "Ni": 1, "Cu": 1, "Zr": 1},
     9.91, -14.40, 13.38, 1.70),
]

_IDS = [
    "CoCrFeNiMo0.3", "CoCrFeNiAl0.3Mo0.1", "CoCrFeNiCuAlMo0.2",
    "Ti0.8CoCrFeNiCu", "TiCoCrFeNiCu", "Ti1.5CoCrFeNiAl",
    "CoCrFeNiCuAlMn", "CrFeNiCuZr",
]


def _norm(comp):
    total = sum(comp.values())
    return {el: amt / total for el, amt in comp.items()}


@pytest.mark.parametrize("comp,d,h,s,o", YZ_ROWS, ids=_IDS)
def test_yz_dhmix_matches_published(comp, d, h, s, o) -> None:
    assert mixing_enthalpy(_norm(comp)) == pytest.approx(h, abs=0.01)


@pytest.mark.parametrize("comp,d,h,s,o", YZ_ROWS, ids=_IDS)
def test_yz_smix_matches_published(comp, d, h, s, o) -> None:
    assert smix(_norm(comp)) == pytest.approx(s, abs=0.02)


@pytest.mark.parametrize("comp,d,h,s,o", YZ_ROWS, ids=_IDS)
def test_yz_omega_within_tm_convention_band(comp, d, h, s, o) -> None:
    assert omega(_norm(comp)) == pytest.approx(o, rel=0.025)


@pytest.mark.parametrize("comp,d,h,s,o", YZ_ROWS, ids=_IDS)
def test_yz_delta_within_radius_convention_band(comp, d, h, s, o) -> None:
    assert delta(_norm(comp)) == pytest.approx(d, abs=0.35)
