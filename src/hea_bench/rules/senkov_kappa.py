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
function's docstring for the scale caveat. That pair counts in full
however little of its elements the alloy holds, so when one of them is
under 10 at.% the prediction carries a ``note`` saying so.

References
----------
Senkov, O. N. & Miracle, D. B. (2016). A new thermodynamic parameter
to predict formation of solid solution or intermetallic phases in
high entropy alloys. *J. Alloys Compd.* **658**, 603-607.
doi:10.1016/j.jallcom.2015.10.279
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from ..composition import Composition, accepts_formula, normalize
from ..constants import SENKOV_K2
from ..descriptors.entropy import smix
from ..descriptors.melting import melting_temperature
from ..descriptors.miedema import mixing_enthalpy
from ..descriptors.data.pair_enthalpies import pair_enthalpy
from ..descriptors.phi import delta_g_max

DESCRIPTION = "Senkov-Miracle 2016: k1 < k1_cr(T) -> solid_solution"

#: An element of the ΔH_IM pair below this mole fraction earns a note.
DILUTE_FRACTION = 0.10


@dataclass(frozen=True)
class KappaPrediction:
    """κ evaluation at one temperature (energies in kJ/mol)."""

    k1: float | None
    k1_cr: float | None
    g_ss_kj: float
    g_im_kj: float
    ss_favored: bool
    temperature_K: float
    im_pair: tuple[str, str] | None = None
    note: str | None = None

    @property
    def verdict(self) -> str:
        return "solid_solution" if self.ss_favored else "intermetallic"


@accepts_formula
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

    im_pair, note = _im_pair_note(composition, h_im)
    return KappaPrediction(
        k1=k1,
        k1_cr=k1_cr,
        g_ss_kj=g_ss,
        g_im_kj=g_im,
        ss_favored=g_ss < g_im,
        temperature_K=t,
        im_pair=im_pair,
        note=note,
    )


def _im_pair_note(
    composition: Composition, h_im: float
) -> tuple[tuple[str, str] | None, str | None]:
    """The pair behind ΔH_IM, and a caution when it is dilute.

    ``rulePredictionsFromDescriptors`` in ``web/hea-calculator-core.js``
    writes the same text, which the parity tests check.
    """
    norm = normalize(composition)
    pairs = list(combinations(sorted(norm), 2))
    if not pairs:
        return None, None
    a, b = min(pairs, key=lambda pair: pair_enthalpy(*pair))
    dilute = [el for el in (a, b) if norm[el] < DILUTE_FRACTION - 1e-9]
    if h_im >= 0.0 or not dilute:
        return (a, b), None
    who = " and ".join(dilute) + (" is" if len(dilute) == 1 else " are")
    return (a, b), (
        f"κ takes ΔH_IM from the strongest pair, {a}-{b}, without weighting it "
        f"by amount, and {who} under 10 at.% here, so read the verdict with caution."
    )
