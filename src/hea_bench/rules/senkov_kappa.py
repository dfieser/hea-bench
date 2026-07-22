"""Senkov-Miracle κ criterion: solid solution vs intermetallic at T.

The criterion compares the Gibbs energies of the disordered solid
solution and the competing intermetallic at an explicit temperature:

    SS favored  ⇔  ΔH_ss − T·ΔS_ss  <  ΔH_IM − T·ΔS_IM

with the paper's working assumption ΔS_IM = k₂·ΔS_ss, k₂ = 0.6.
For the usual case ΔH_ss < 0 this rearranges to the published
parameterization

    k₁ = ΔH_IM / ΔH_ss   and   k₁^cr(T) = 1 + (1 − k₂) · T·ΔS_ss / |ΔH_ss|

with SS favored when k₁ < k₁^cr. (The (1 − k₂) factor multiplies the
temperature term; deriving the inequality from the Gibbs comparison
fixes the typography ambiguity in some restatements.) This module
always decides the verdict from the direct Gibbs comparison, which
stays well-defined when ΔH_ss ≥ 0 or ΔH_IM ≥ 0; k₁ and k₁^cr are
reported only when ΔH_ss < 0 so the ratio form is meaningful.

ΔH_IM is approximated by the most negative binary pair enthalpy over
the alloy's constituents (``descriptors.phi.delta_g_max``), the same
documented approximation the King Φ implementation uses; see that
function's docstring for the scale caveat.

References
----------
Senkov, O. N. & Miracle, D. B. (2016). A new thermodynamic parameter
to predict formation of solid solution or intermetallic phases in
high entropy alloys. *J. Alloys Compd.* **658**, 603-607.
doi:10.1016/j.jallcom.2015.10.279
"""

from __future__ import annotations

from dataclasses import dataclass

from ..composition import Composition
from ..constants import SENKOV_K2
from ..descriptors.entropy import smix
from ..descriptors.melting import melting_temperature
from ..descriptors.miedema import mixing_enthalpy
from ..descriptors.phi import delta_g_max

DESCRIPTION = "Senkov-Miracle 2016: k1 < k1_cr(T) -> solid_solution"


@dataclass(frozen=True)
class KappaPrediction:
    """κ evaluation at one temperature (energies in kJ/mol)."""

    k1: float | None
    k1_cr: float | None
    g_ss_kj: float
    g_im_kj: float
    ss_favored: bool
    temperature_K: float

    @property
    def verdict(self) -> str:
        return "solid_solution" if self.ss_favored else "intermetallic"


def predict(
    composition: Composition,
    temperature: float | None = None,
) -> KappaPrediction:
    """Evaluate the κ criterion; ``temperature`` defaults to the
    rule-of-mixtures melting temperature (K)."""
    t = melting_temperature(composition) if temperature is None else float(temperature)
    if t <= 0:
        raise ValueError("temperature must be positive (kelvin)")
    h_ss = mixing_enthalpy(composition)
    h_im = delta_g_max(composition)
    s = smix(composition)  # J/(mol K)
    ts_kj = t * s / 1000.0

    g_ss = h_ss - ts_kj
    g_im = h_im - SENKOV_K2 * ts_kj

    k1: float | None = None
    k1_cr: float | None = None
    if h_ss < 0.0:
        k1 = h_im / h_ss
        k1_cr = 1.0 + (1.0 - SENKOV_K2) * ts_kj / abs(h_ss)

    return KappaPrediction(
        k1=k1,
        k1_cr=k1_cr,
        g_ss_kj=g_ss,
        g_im_kj=g_im,
        ss_favored=g_ss < g_im,
        temperature_K=t,
    )
