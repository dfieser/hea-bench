"""hea-bench: an open, interpretable calculator of the standard high-entropy
alloy and high-entropy oxide thermodynamic and geometric descriptors plus the
canonical empirical phase-prediction rules (oxides in ``hea_bench.oxides``).

Every quantity is a transparent closed-form expression over a curated
element-property table — no fitted model, no black box. The same calculation
core ships as this Python library, a zero-install browser app, and a native
desktop app; the browser core is parity-tested against this library.

Top-level convenience imports for the most-used names; full surface
documented in ``README.md``.

Quick start::

    from hea_bench import smix, delta, vec, mixing_enthalpy, omega
    cantor = {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}
    print(smix(cantor), delta(cantor), vec(cantor),
          mixing_enthalpy(cantor), omega(cantor))
"""

from .composition import Composition, normalize, parse_formula
from .descriptors.electronegativity import delta_chi, mean_electronegativity
from .descriptors.entropy import smix
from .descriptors.melting import melting_temperature
from .descriptors.miedema import mixing_enthalpy
from .descriptors.omega import omega
from .descriptors.phi import delta_g_max, delta_g_ss, delta_h_ss, phi_king, phi_ye, s_excess
from .descriptors.size import delta
from .descriptors.vec import vec

__version__ = "2.0.10"

__all__ = [
    "__version__",
    # core type + parsing
    "Composition",
    "parse_formula",
    "normalize",
    # descriptors
    "smix",
    "delta",
    "vec",
    "melting_temperature",
    "mixing_enthalpy",
    "omega",
    "delta_h_ss",
    "delta_g_ss",
    "delta_g_max",
    "s_excess",
    "phi_king",
    "phi_ye",
    "delta_chi",
    "mean_electronegativity",
]
