"""Shannon effective ionic radius lookup.

The Shannon (1976) tables list one radius per (element, oxidation
state, coordination number, spin state). The oxide descriptors need a
single deterministic radius for a cation in a given structural site, so
this module resolves the lookup with two documented fallbacks:

- If the exact coordination number is not tabulated, the nearest
  tabulated coordination is used (preferring the larger one on a tie)
  and a warning is recorded. This mirrors common practice in the HEO
  descriptor literature, where e.g. twelve-fold radii are missing for
  many transition metals.
- 3d transition metals with crystal-field-split entries default to the
  high-spin radius (appropriate at ceramic synthesis temperatures);
  ``spin="low"`` selects the low-spin value where tabulated.

References
----------
Shannon, R. D. (1976). Revised effective ionic radii and systematic
studies of interatomic distances in halides and chalcogenides.
*Acta Crystallographica* **A32**, 751-767.
"""

from __future__ import annotations

from ._data import OXIDE_ELEMENTS

_ROMAN_TO_INT = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7,
    "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12, "XIII": 13, "XIV": 14,
}


def shannon_radius(
    element: str,
    charge: int,
    coordination: int,
    spin: str = "high",
) -> tuple[float, list[str]]:
    """Effective ionic radius in angstroms, plus any fallback warnings.

    Parameters
    ----------
    element
        Element symbol, e.g. ``"Ce"``.
    charge
        Formal oxidation state (signed integer; ``-2`` for the oxide anion).
    coordination
        Target coordination number (6, 8, 12, ...). Falls back to the
        nearest tabulated coordination with a warning.
    spin
        ``"high"`` (default) or ``"low"``; only meaningful for ions with
        spin-split Shannon entries.

    Returns
    -------
    tuple[float, list[str]]
        The radius and a list of human-readable fallback warnings
        (empty when the exact entry existed).

    Raises
    ------
    ValueError
        If the element is not in the vendored table or has no Shannon
        entry for the requested oxidation state.
    """
    if spin not in ("high", "low"):
        raise ValueError(f'spin must be "high" or "low", got {spin!r}')
    entry = OXIDE_ELEMENTS.get(element)
    if entry is None:
        raise ValueError(f"element {element!r} is not in the vendored oxide element table")
    by_charge = entry["shannon_radii"].get(str(int(charge)))
    if by_charge is None:
        have = sorted(entry["shannon_radii"], key=int)
        raise ValueError(
            f"no Shannon radius for {element} in oxidation state {charge:+d} "
            f"(tabulated states: {', '.join(have)})"
        )

    warnings: list[str] = []
    available = {
        _ROMAN_TO_INT[cn_key]: spins
        for cn_key, spins in by_charge.items()
        if cn_key in _ROMAN_TO_INT  # skips square-planar/pyramidal variants
    }
    if not available:
        raise ValueError(
            f"{element}{charge:+d} has only non-standard coordination entries in the Shannon table"
        )
    if coordination in available:
        used_cn = coordination
    else:
        used_cn = min(available, key=lambda n: (abs(n - coordination), -n))
        warnings.append(
            f"{element}{charge:+d}: no Shannon radius at CN={coordination}; "
            f"using the nearest tabulated CN={used_cn}"
        )
    spins = available[used_cn]

    wanted = "High Spin" if spin == "high" else "Low Spin"
    if wanted in spins:
        radius = spins[wanted]
    elif "" in spins:
        radius = spins[""]
    else:
        fallback_key = sorted(spins)[0]
        radius = spins[fallback_key]
        warnings.append(
            f"{element}{charge:+d} CN={used_cn}: no {wanted.lower()} entry; "
            f"using the {fallback_key.lower() or 'unspecified-spin'} radius"
        )
    return float(radius), warnings
