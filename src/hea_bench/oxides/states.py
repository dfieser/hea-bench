"""Charge-neutrality oxidation-state solver.

In an oxide, the cation oxidation states must exactly offset the
charge of the oxygen sublattice. This solver enumerates plausible
oxidation-state assignments and keeps the charge-neutral ones, in the
spirit of the SMACT screening approach (Davies et al. 2019, *JOSS*
4, 1361).

Candidate states for each element are its tabulated common oxidation
states, restricted to positive states that have a Shannon radius (so
every solution is usable by the geometric descriptors downstream). If
no charge-neutral assignment exists within the common states, the
search widens once to all ICSD-observed / Shannon-tabulated positive
states and records a warning.

When several assignments balance, the tie is broken deterministically:
prefer charge-uniform sublattices (the moles-weighted variance of the
states within each ``groups`` label is minimized first — aliovalent
mixing on one site is the exception in oxide chemistry, not the
default), then more-common states, then assignments that put lower
charges on more electronegative elements, then lexicographic order.
Pass ``allowed`` to pin any element's state explicitly and skip the
heuristics.
"""

from __future__ import annotations

from itertools import product
from typing import Mapping, Sequence

from ._data import OXIDE_ELEMENTS

_CHARGE_TOLERANCE = 1e-6
_MAX_COMBINATIONS = 2_000_000


def _candidates(element: str) -> tuple[list[int], list[int]]:
    """(common, widened) positive oxidation states with Shannon radii."""
    entry = OXIDE_ELEMENTS.get(element)
    if entry is None:
        raise ValueError(f"element {element!r} is not in the vendored oxide element table")
    with_radius = {int(q) for q in entry["shannon_radii"] if int(q) > 0}
    common = [q for q in entry["common_oxidation_states"] if q in with_radius]
    icsd = [q for q in entry["icsd_oxidation_states"] if q > 0 and q in with_radius]
    widened = list(common)
    widened += [q for q in icsd if q not in widened]
    widened += [q for q in sorted(with_radius) if q not in widened]
    if not widened:
        raise ValueError(f"{element} has no positive oxidation state with a Shannon radius")
    return common, widened


def assign_oxidation_states(
    moles: Mapping[str, float],
    target_charge: float,
    allowed: Mapping[str, Sequence[int]] | None = None,
    groups: Mapping[str, str] | None = None,
) -> tuple[dict[str, int], list[str]]:
    """Assign one oxidation state per element so total charge balances.

    Parameters
    ----------
    moles
        Element -> moles per formula unit (cation amounts; need not be
        normalized, but the charge balance is computed on these values
        as given).
    target_charge
        Total positive charge required per formula unit (e.g. ``+6``
        for ABO3, ``2 * oxygen`` for an MO_x oxide).
    allowed
        Optional element -> explicit candidate states, overriding the
        tabulated candidates for those elements.
    groups
        Optional element -> sublattice label. Ties between
        charge-neutral assignments are broken by preferring
        charge-uniform groups. Omitted, all elements form one group.

    Returns
    -------
    tuple[dict[str, int], list[str]]
        The chosen state per element, and warnings (non-empty when the
        search had to widen beyond common oxidation states).

    Raises
    ------
    ValueError
        If no candidate assignment balances the target charge. The
        message reports the closest achievable total charge.
    """
    if not moles:
        raise ValueError("moles must be non-empty")
    elements = sorted(moles)
    allowed = allowed or {}

    common_lists: list[list[int]] = []
    widened_lists: list[list[int]] = []
    for el in elements:
        if el in allowed:
            pinned = [int(q) for q in allowed[el]]
            if not pinned:
                raise ValueError(f"allowed[{el!r}] must be non-empty")
            common_lists.append(pinned)
            widened_lists.append(pinned)
        else:
            common, widened = _candidates(el)
            common_lists.append(common or widened)
            widened_lists.append(widened)

    def solve(cands: list[list[int]]) -> list[tuple[int, ...]]:
        n_combos = 1
        for c in cands:
            n_combos *= len(c)
        if n_combos > _MAX_COMBINATIONS:
            raise ValueError(
                f"oxidation-state search space too large ({n_combos} combinations); "
                f"pin states for some elements via `allowed`"
            )
        return [
            combo
            for combo in product(*cands)
            if abs(sum(moles[el] * q for el, q in zip(elements, combo)) - target_charge)
            < _CHARGE_TOLERANCE
        ]

    warnings: list[str] = []
    solutions = solve(common_lists)
    if not solutions:
        solutions = solve(widened_lists)
        if solutions:
            warnings.append(
                "no charge-neutral assignment using only common oxidation states; "
                "a less common state was used"
            )
    if not solutions:
        best = min(
            (sum(moles[el] * q for el, q in zip(elements, combo)) for combo in product(*widened_lists)),
            key=lambda total: abs(total - target_charge),
        )
        raise ValueError(
            f"no oxidation-state assignment reaches total charge {target_charge:+g} "
            f"(closest achievable: {best:+g}); check the composition, the oxygen "
            f"content, or pass explicit states via `allowed`"
        )

    rank = {
        el: {q: i for i, q in enumerate(widened_lists[j])} for j, el in enumerate(elements)
    }
    group_of = {el: (groups or {}).get(el, "") for el in elements}
    labels = sorted(set(group_of.values()))

    def score(combo: tuple[int, ...]) -> tuple[float, float, float, tuple[int, ...]]:
        states = dict(zip(elements, combo))
        variance = 0.0
        for label in labels:
            members = [el for el in elements if group_of[el] == label]
            weight = sum(moles[el] for el in members)
            mean_q = sum(moles[el] * states[el] for el in members) / weight
            variance += sum(moles[el] * (states[el] - mean_q) ** 2 for el in members)
        commonness = sum(moles[el] * rank[el][q] for el, q in zip(elements, combo))
        chi_weighted = sum(
            moles[el] * q * (OXIDE_ELEMENTS[el]["chi"] or 0.0)
            for el, q in zip(elements, combo)
        )
        return (variance, commonness, chi_weighted, combo)

    chosen = min(solutions, key=score)
    if len(solutions) > 1:
        warnings.append(
            f"{len(solutions)} charge-neutral assignments exist; chose the most "
            f"charge-uniform, most common one (pass `allowed` to override)"
        )
    return dict(zip(elements, chosen)), warnings
