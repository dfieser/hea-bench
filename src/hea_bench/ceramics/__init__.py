"""High-entropy ceramics descriptors: rock-salt carbides, nitrides, diborides.

Extends the calculator beyond metallic HEAs following the shape of
:mod:`hea_bench.oxides`: one ``describe_*`` call per structure family
returning a single dict of normalized inputs, descriptors, annotated
literature reference points, warnings, and citations. Everything is
composition-only, which in the ceramics literature buys less than it
does for alloys, and this module says so instead of pretending:

- **Configurational entropy** follows the high-entropy-ceramics
  convention (Oses, Toher and Curtarolo 2020; Wright and Luo 2020):
  mixing disorder lives on the metal sublattice, the anion sublattice
  is ordered and contributes nothing. Because published papers switch
  between per-formula-unit, per-mole-cation, and per-mole-atom
  normalizations without warning (Dippo and Vecchio 2021 built a metric
  precisely because of that), every report carries all of them,
  labelled.
- **VEC** per formula unit is the composition-weighted metal group
  electron count plus the anion's (4 for C, 5 for N), the convention of
  the rock-salt mechanical-behavior literature. The literature marks
  reference points rather than one window: a hardness maximum near 8.4
  (Jhi et al. 1999), enhanced fracture resistance above about 9.4
  (Sangiovanni et al. 2023), plasticity above about 9.5 (Sangiovanni et
  al. 2021), against the binary-systematics backdrop of Balasubramanian
  et al. 2018. The report annotates those points; it deliberately emits
  no verdict, because no single published window exists.
- **Size mismatch is deferred, with the reason stated.** The carbide
  formability literature computes it from metal-carbon bond lengths of
  binary rock-salt cells obtained by DFT (Kretschmer and Mayrhofer
  2024, explicitly rejecting tabulated radii), and the diboride
  literature from binary MB2 lattice parameters (Gild et al. 2016).
  Adopting such a table is a data-curation task with real choices
  (metastable rock-salt MoC, WC, CrC have no experimental stoichiometric
  lattice constant), and this module refuses to rush it; a future
  change can add the descriptor with a properly per-row-cited table.
- **Entropy-forming ability and DEED are DFT-ensemble quantities**
  (Sarker et al. 2018; Divilov et al. 2024) and cannot be computed from
  composition. Nothing here claims parity with them; the best published
  composition-only correlate of EFA explains about R squared 0.58 and
  its authors hedge its threshold.

The screens here are context for reading literature and planning
syntheses, weaker than the alloy rules; treat every number accordingly.
"""

from __future__ import annotations

import math

from ..composition import Composition, normalize
from ..descriptors.data.elemental import ELEMENTAL_DATA as _ELEMENTS
from ..oxides.descriptors import R_GAS

SOURCES = {
    "Oses2020": (
        "Oses, Toher and Curtarolo (2020). Nat. Rev. Mater. 5, 295. "
        "High-entropy ceramics review; cation-sublattice entropy convention."
    ),
    "WrightLuo2020": (
        "Wright and Luo (2020). J. Mater. Sci. 55, 9812. Sublattice mixing "
        "entropy formulation for compositionally complex ceramics."
    ),
    "Dippo2021": (
        "Dippo and Vecchio (2021). Scr. Mater. 201, 113974. Sublattice-"
        "resolved entropy metric; the normalization ambiguity this module "
        "reports around."
    ),
    "Jhi1999": (
        "Jhi, Ihm, Louie and Cohen (1999). Nature 399, 132. VEC 8.4 hardness "
        "maximum in rock-salt carbonitrides."
    ),
    "Sangiovanni2021": (
        "Sangiovanni, Mellor, Harrington, Kaufmann and Vecchio (2021). "
        "Mater. Des. 204, 109932. VEC above about 9.5 for plasticity in B1 "
        "high-entropy carbides."
    ),
    "Sangiovanni2023": (
        "Sangiovanni, Kaufmann and Vecchio (2023). Sci. Adv. 9, eadi2960. "
        "VEC controls fracture resistance; enhanced above about 9.4."
    ),
    "Balasubramanian2018": (
        "Balasubramanian, Khare and Gall (2018). Acta Mater. 152, 175. VEC "
        "systematics for rock-salt nitrides and carbides."
    ),
    "Sarker2018": (
        "Sarker et al. (2018). Nat. Commun. 9, 4980. Entropy-forming "
        "ability; a DFT-ensemble descriptor, not computable from composition."
    ),
    "Divilov2024": (
        "Divilov et al. (2024). Nature 625, 66. DEED; DFT ensemble plus "
        "convex hull, not computable from composition."
    ),
    "Kretschmer2024": (
        "Kretschmer and Mayrhofer (2024). Sci. Rep. 14, 7210. Carbide size "
        "mismatch from DFT binary bond lengths; the deferred descriptor."
    ),
    "Gild2016": (
        "Gild et al. (2016). Sci. Rep. 6, 37946. High-entropy diborides; "
        "lattice-parameter mismatch bracketing."
    ),
}

_VEC_REFERENCE_POINTS = (
    {
        "value": 8.4,
        "marks": "hardness maximum in rock-salt carbonitrides",
        "source": "Jhi et al. 1999 (Nature 399, 132)",
    },
    {
        "value": 9.4,
        "marks": "enhanced fracture resistance in five-metal rock-salt carbides",
        "source": "Sangiovanni et al. 2023 (Sci. Adv. 9, eadi2960)",
    },
    {
        "value": 9.5,
        "marks": "plasticity criterion for B1 high-entropy ceramics",
        "source": "Sangiovanni et al. 2021 (Mater. Des. 204, 109932)",
    },
)

_NOTES = (
    "size mismatch is deferred: the literature computes it from DFT binary "
    "cell bond lengths (Kretschmer2024) or binary lattice parameters "
    "(Gild2016), and no per-row-cited composition-only table has been "
    "adopted yet",
    "entropy-forming ability and DEED are DFT-ensemble descriptors "
    "(Sarker2018, Divilov2024) and are deliberately absent",
    "no verdict is emitted: the VEC literature marks reference points, not "
    "one published window",
)


def _entropy(metals: Composition, atoms_per_formula_unit: int) -> dict:
    # The single-sublattice case of oxides.descriptors.sublattice_entropy,
    # kept inline (in R units) so the R-unit field is exact; the gas
    # constant is shared with the oxide surface rather than re-declared.
    per_cation_r = -sum(x * math.log(x) for x in metals.values() if x > 0)
    return {
        "per_mole_cation_r_units": per_cation_r,
        "per_mole_cation_j_mol_k": R_GAS * per_cation_r,
        "per_formula_unit_j_mol_k": R_GAS * per_cation_r,
        "per_mole_atoms_j_mol_k": R_GAS * per_cation_r / atoms_per_formula_unit,
        "note": (
            "metal-sublattice ideal mixing; anion sublattice ordered "
            "(Oses2020). All normalization conventions reported because "
            "papers switch between them without warning (Dippo2021): per "
            "mole of cations equals per formula unit here, and per mole of "
            f"atoms divides by {atoms_per_formula_unit} for this structure."
        ),
    }


def _vec(metals: Composition, anion_electrons: int, warnings: list[str]) -> float | None:
    total = 0.0
    for symbol, fraction in metals.items():
        row = _ELEMENTS.get(symbol)
        if row is None:
            warnings.append(
                f"{symbol}: no valence entry in the element table, VEC not computable"
            )
            return None
        total += fraction * row.valence
    return total + anion_electrons


def _describe(
    metals: Composition,
    *,
    structure: str,
    anion: str,
    anion_electrons: int | None,
    atoms_per_formula_unit: int,
) -> dict:
    normalized = normalize(metals)
    warnings: list[str] = []
    report: dict = {
        "structure": structure,
        "anion": anion,
        "metals": normalized,
        "n_metals": len(normalized),
        "entropy": _entropy(normalized, atoms_per_formula_unit),
        "notes": list(_NOTES),
        "warnings": warnings,
        "sources": dict(SOURCES),
    }
    if anion_electrons is not None:
        report["vec_per_formula_unit"] = _vec(normalized, anion_electrons, warnings)
        report["vec_reference_points"] = [dict(point) for point in _VEC_REFERENCE_POINTS]
    return report


def describe_rock_salt_carbide(metals: Composition) -> dict:
    """Composition-only descriptors for a rock-salt high-entropy carbide.

    ``metals`` is the metal-sublattice composition (amounts normalize
    internally); carbon fills the anion sublattice at one per metal.
    """
    return _describe(
        metals,
        structure="rock_salt_carbide",
        anion="C",
        anion_electrons=4,
        atoms_per_formula_unit=2,
    )


def describe_rock_salt_nitride(metals: Composition) -> dict:
    """Composition-only descriptors for a rock-salt high-entropy nitride."""
    return _describe(
        metals,
        structure="rock_salt_nitride",
        anion="N",
        anion_electrons=5,
        atoms_per_formula_unit=2,
    )


def describe_diboride(metals: Composition) -> dict:
    """Composition-only descriptors for an AlB2-type high-entropy diboride.

    VEC reference points from the rock-salt literature do not transfer
    to the AlB2 structure, so the diboride report carries entropy only.
    """
    return _describe(
        metals,
        structure="diboride",
        anion="B2",
        anion_electrons=None,
        atoms_per_formula_unit=3,
    )


__all__ = [
    "SOURCES",
    "describe_diboride",
    "describe_rock_salt_carbide",
    "describe_rock_salt_nitride",
]
