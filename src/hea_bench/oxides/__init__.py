"""Closed-form descriptors and empirical formability screens for
high-entropy oxides (HEOs).

This subpackage extends hea-bench from metallic alloys to ionic
oxides. The physics changes with the chemistry: descriptors are
computed per sublattice over Shannon (1976) effective ionic radii
instead of metallic radii, charge neutrality against the oxygen
sublattice is enforced by an explicit oxidation-state solver, and the
phase screens are the structure-family geometric rules of the HEO
literature. Everything remains a transparent closed-form expression
over vendored, citable data tables — no DFT, no fitted model.

Entry points are the per-family report functions:

>>> from hea_bench import oxides
>>> j14 = oxides.describe_rock_salt({"Mg": 1, "Co": 1, "Ni": 1, "Cu": 1, "Zn": 1})
>>> j14["verdicts"]["entropy"]
'high-entropy'

plus the low-level pieces (``shannon_radius``,
``assign_oxidation_states``, and the descriptor functions) for
power users. Verdicts are weak empirical screens calibrated on small
historical datasets, exactly like the alloy-side rules; never treat
one as ground truth. The alloy descriptors in the parent package are
untouched by this subpackage.
"""

from .descriptors import (
    OXYGEN_RADIUS,
    R_GAS,
    bartel_tau,
    combined_size_disorder,
    delta_chi,
    goldschmidt_t,
    mean_chi,
    octahedral_factor,
    radius_ratio,
    radius_sample_std,
    size_disorder,
    sublattice_entropy,
)
from .families import (
    describe_fluorite,
    describe_perovskite,
    describe_pyrochlore,
    describe_rock_salt,
)
from .radii import shannon_radius
from .states import assign_oxidation_states

__all__ = [
    "OXYGEN_RADIUS",
    "R_GAS",
    "assign_oxidation_states",
    "bartel_tau",
    "combined_size_disorder",
    "delta_chi",
    "describe_fluorite",
    "describe_perovskite",
    "describe_pyrochlore",
    "describe_rock_salt",
    "goldschmidt_t",
    "mean_chi",
    "octahedral_factor",
    "radius_ratio",
    "radius_sample_std",
    "shannon_radius",
    "size_disorder",
    "sublattice_entropy",
]
