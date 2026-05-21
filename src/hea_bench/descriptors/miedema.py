"""Miedema multi-component mixing enthalpy.

ΔH_mix = Σ_{i<j} 4 · c_i · c_j · ΔH^{pair}_{ij}

where ``ΔH^{pair}_{ij}`` is the *equiatomic* binary mixing enthalpy
for the A-B liquid alloy from the Miedema model (kJ/mol). The factor
of 4 normalizes for arbitrary composition: at equiatomic
``c_A = c_B = 0.5``, the prefactor ``4 · 0.5 · 0.5 = 1`` recovers the
tabulated pair value.

The pair enthalpies come from :mod:`hea_bench.descriptors.data.pair_enthalpies`,
which wraps the matminer-vendored Miedema table (75 elements, BSD-3;
cross-verified against Takeuchi & Inoue 2005 *Mater. Trans.* **46**, 2817).

References
----------
Zhang, R. F. *et al.* (2016). Miedema Calculator: A thermodynamic
platform for predicting formation enthalpies of alloys within
framework of Miedema's theory. *Comput. Phys. Commun.* **209**, 58-69.

Takeuchi, A. & Inoue, A. (2005). Classification of bulk metallic
glasses by atomic size difference, heat of mixing and period of
constituent elements and its application to characterization of the
main alloying element. *Materials Transactions* **46**, 2817-2829.
"""

from __future__ import annotations

from itertools import combinations

from ..composition import Composition
from .data.pair_enthalpies import covered_elements as _pair_covered
from .data.pair_enthalpies import pair_enthalpy


def mixing_enthalpy(composition: Composition) -> float:
    """Miedema multi-component mixing enthalpy ΔH_mix (kJ/mol).

    Parameters
    ----------
    composition
        Mapping of element symbol to mole fraction (or proportional
        amount — values are normalized to sum to 1 internally).

    Returns
    -------
    float
        ΔH_mix in kJ/mol. Sign convention: negative = exothermic mixing
        (favours formation), positive = endothermic (favours
        segregation).

    Raises
    ------
    ValueError
        If composition is empty, if values sum to zero, or if any
        elements are not in the Miedema pair table. The error message
        lists the missing elements.

    Examples
    --------
    Cantor alloy CoCrFeMnNi at equimolar:

    >>> round(mixing_enthalpy({"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}), 2)
    -4.16
    """
    if not composition:
        raise ValueError("composition must be non-empty")

    total = sum(composition.values())
    if total <= 0:
        raise ValueError("composition values must sum to a positive number")
    norm = {el: amount / total for el, amount in composition.items() if amount > 0}

    missing = set(norm) - _pair_covered()
    if missing:
        raise ValueError(
            f"composition contains elements not in Miedema pair table: "
            f"{sorted(missing)}"
        )

    h = 0.0
    for a, b in combinations(sorted(norm), 2):
        h += 4.0 * norm[a] * norm[b] * pair_enthalpy(a, b)
    return h
