"""Andreoli elastic-strain energy criterion ΔH_el.

    ΔH_el = Σ_i c_i · B_i · (V_i − V̄)² / (2 V_i)
    V̄    = Σ_i c_i B_i V_i / Σ_i c_i B_i

(Eqs. 9-10 of the defining paper.) With B_i in GPa and V_i in
cm³/mol the product is exactly kJ/mol, no unit factor. Windows from
the paper's 235-alloy survey: fcc solid solutions form mainly for
0 ≤ ΔH_el ≤ 6.05 kJ/mol (96.4% of their fcc SS), bcc solid solutions
for 6.05 < ΔH_el ≤ 22 kJ/mol (86.2%), and everything above 22 kJ/mol
is bulk-metallic-glass or single-phase-intermetallic territory.

Our B_i and V_i come from the vendored matminer Miedema table
(``data/mechanics.py``), which differs from the paper's own elastic
sources; absolute values can shift by tenths of kJ/mol, so treat the
windows as the calibrated object, not the third decimal.

References
----------
Andreoli, A. F., Orava, J., Liaw, P. K., Weber, H., de Oliveira,
M. F., Nielsch, K. & Kaban, I. (2019). The elastic-strain energy
criterion of phase formation for complex concentrated alloys.
*Materialia* **5**, 100222. doi:10.1016/j.mtla.2019.100222
"""

from __future__ import annotations

from ..composition import Composition
from .data.mechanics import mechanics


def _h_elastic_from_tables(
    fractions: dict[str, float],
    bulk_gpa: dict[str, float],
    volume_cm3: dict[str, float],
) -> float:
    """ΔH_el from explicit tables (testable core; kJ/mol)."""
    total = sum(fractions.values())
    norm = {k: v / total for k, v in fractions.items() if v > 0}
    weight = sum(norm[k] * bulk_gpa[k] for k in norm)
    v_bar = sum(norm[k] * bulk_gpa[k] * volume_cm3[k] for k in norm) / weight
    return sum(
        norm[k] * bulk_gpa[k] * (volume_cm3[k] - v_bar) ** 2 / (2.0 * volume_cm3[k])
        for k in norm
    )


def h_elastic(composition: Composition) -> float | None:
    """ΔH_el in kJ/mol, or None when any element lacks usable B or V."""
    if not composition:
        raise ValueError("composition must be non-empty")
    bulk: dict[str, float] = {}
    volume: dict[str, float] = {}
    for el, amount in composition.items():
        if amount <= 0:
            continue
        m = mechanics(el)
        if m is None or m.bulk_modulus_gpa <= 0.0 or m.molar_volume_cm3 <= 0.0:
            return None
        bulk[el] = m.bulk_modulus_gpa
        volume[el] = m.molar_volume_cm3
    if not bulk:
        raise ValueError("composition values must sum to a positive number")
    return _h_elastic_from_tables(dict(composition), bulk, volume)
