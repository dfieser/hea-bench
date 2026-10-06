"""Descriptor computation backends.

A backend is anything that can turn a composition into a named set of
descriptor values. The package's own stdlib implementations are the
default (:class:`NativeBackend`); an installed HEACalculator can serve
as an alternative through :class:`HEACalculatorBackend`, so a user
already standardized on that tool can keep its numbers while using
everything downstream in this package.

Two honesty rules govern the layer:

- **The union is explicit.** ``compute`` answers for every name in
  :data:`UNION_DESCRIPTOR_NAMES` and returns ``None`` for names the
  active backend cannot produce (either because the quantity is not in
  its repertoire or because an element is missing from its tables).
  ``None`` is the typed "cannot compute" signal; nothing is imputed.
- **Near-equivalents are never swapped silently.** Each backend owns
  its reference data (pair-enthalpy tables, radius tabulations), so the
  same published quantity can return different numbers under different
  backends; the radius conventions differ most in practice. The
  quantified comparison lives in ``docs/backend-agreement.md``; neither
  side is declared correct.

The native backend is dependency-free like the rest of the core. The
HEACalculator backend needs ``pip install "hea-bench[interop]"`` and is
imported lazily, so a missing install surfaces as
:class:`BackendUnavailableError` naming that command rather than as an
ImportError at package import time.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Protocol, runtime_checkable

from ..composition import Composition, accepts_formula, normalize
from .elastic import h_elastic
from .electronegativity import delta_chi, mean_electronegativity
from .entropy import smix
from .gamma import wang_gamma
from .lam import singh_lambda
from .melting import melting_temperature
from .miedema import mixing_enthalpy
from .omega import omega
from .phi import delta_g_max, delta_g_ss, phi_king, phi_ye, s_excess
from .size import delta
from .vec import vec


class BackendUnavailableError(RuntimeError):
    """An optional descriptor backend is not installed.

    The message always names the exact pip install that fixes it.
    """


#: Native descriptor set: Python-API name -> (callable, unit). The names
#: are the library's public function names, which is also the vocabulary
#: the benchmark feature matrix uses.
_NATIVE = {
    "smix": (smix, "J/(mol K)"),
    "delta": (delta, "%"),
    "vec": (vec, "electrons/atom"),
    "melting_temperature": (melting_temperature, "K"),
    "mixing_enthalpy": (mixing_enthalpy, "kJ/mol"),
    "omega": (omega, "dimensionless"),
    "s_excess": (s_excess, "J/(mol K)"),
    "delta_g_ss": (delta_g_ss, "kJ/mol"),
    "delta_g_max": (delta_g_max, "kJ/mol"),
    "phi_king": (phi_king, "dimensionless"),
    "phi_ye": (phi_ye, "dimensionless"),
    "delta_chi": (delta_chi, "Pauling scale"),
    "mean_electronegativity": (mean_electronegativity, "Pauling scale"),
    "singh_lambda": (singh_lambda, "J/(mol K %^2)"),
    "wang_gamma": (wang_gamma, "dimensionless"),
    "h_elastic": (h_elastic, "kJ/mol"),
}

#: Python-API descriptor name -> unit string, for any surface that wants
#: to print units without reimplementing the table.
UNITS = {name: unit for name, (_func, unit) in _NATIVE.items()}

#: The all-float subset used for feature matrices, in the frozen order
#: the benchmark baselines were computed with. singh_lambda is excluded
#: because it is infinite when delta is zero, h_elastic because it is
#: None for elements missing bulk modulus or volume.
_MATRIX_NAMES = (
    "smix", "delta", "vec", "melting_temperature", "mixing_enthalpy",
    "omega", "s_excess", "delta_g_ss", "delta_g_max", "phi_king",
    "phi_ye", "delta_chi", "mean_electronegativity", "wang_gamma",
)

#: Names only the HEACalculator backend defines (the native backend
#: answers None for these). Units for them are added to UNITS below.
_HEACALCULATOR_ONLY: tuple[str, ...] = (
    "density",
    "delta_atomic_radius",
    "delta_chi_allen_pct",
    "delta_chi_pauling_pct",
    "ea_ratio",
    "formation_enthalpy",
    "min_formation_enthalpy",
)

UNITS.update(
    {
        "density": "g/cm^3",
        "delta_atomic_radius": "%",
        "delta_chi_allen_pct": "%",
        "delta_chi_pauling_pct": "%",
        "ea_ratio": "electrons/atom",
        "formation_enthalpy": "meV/atom",
        "min_formation_enthalpy": "meV/atom",
    }
)

#: Every descriptor name any backend knows. compute() answers for all of
#: them, with None where the active backend has nothing to say.
UNION_DESCRIPTOR_NAMES: tuple[str, ...] = tuple(_NATIVE) + _HEACALCULATOR_ONLY


@runtime_checkable
class DescriptorBackend(Protocol):
    """What a descriptor backend must provide."""

    name: str

    def descriptor_names(self) -> tuple[str, ...]:
        """Names this backend can actually produce."""
        ...

    def matrix_names(self) -> tuple[str, ...]:
        """The all-float subset suitable for a feature matrix, in order."""
        ...

    def compute(self, composition: Composition) -> dict[str, float | None]:
        """Every union name -> value, with None for the uncomputable."""
        ...


class NativeBackend:
    """This package's own stdlib descriptor implementations."""

    name = "native"

    def descriptor_names(self) -> tuple[str, ...]:
        return tuple(_NATIVE)

    def matrix_names(self) -> tuple[str, ...]:
        return _MATRIX_NAMES

    def compute(self, composition: Composition) -> dict[str, float | None]:
        """Compute all native descriptors; None where data is missing.

        A descriptor that raises for this composition (an element absent
        from its table) or that returns None itself (h_elastic) reports
        None. Mathematically divergent values (singh_lambda at delta=0)
        stay as the float infinity; JSON-facing surfaces handle those.

        The composition is passed to the descriptor functions untouched
        (they normalize internally), so a value computed here is
        bit-identical to the direct function call.
        """
        values: dict[str, float | None] = dict.fromkeys(UNION_DESCRIPTOR_NAMES)
        for name, (func, _unit) in _NATIVE.items():
            try:
                values[name] = func(composition)
            except Exception:
                values[name] = None
        return values


@lru_cache(maxsize=1)
def scorable_elements() -> frozenset[str]:
    """Elements covered by BOTH the elemental and pair-enthalpy tables.

    This intersection is the single definition of descriptor-scorable
    chemistry: it decides the corpus ``descriptor_ready`` flag, the
    design-search palette check, and the applicability domain model's
    element coverage. Cached, since the tables are frozen per process.
    """
    from .data.elemental import covered_elements as _elemental
    from .data.pair_enthalpies import covered_elements as _pairs

    return frozenset(_elemental() & _pairs())


@accepts_formula
def matrix_vector(
    composition: Composition, backend: "DescriptorBackend | None" = None
) -> list[float] | None:
    """One all-float feature row over the backend's matrix descriptors.

    Computes the active backend's ``matrix_names()`` subset for
    ``composition`` and returns it as a list of floats, or ``None`` when
    any entry is missing or non-finite. This is the benchmark's finite
    filter, the single definition of "descriptor-scorable row" shared by
    the hardness surrogate, campaign training, and the applicability
    domain model; those feature spaces are only meaningful because they
    all come from here.
    """
    resolved = backend if backend is not None else NativeBackend()
    values = resolved.compute(composition)
    vector = [values.get(name) for name in resolved.matrix_names()]
    if all(value is not None and math.isfinite(value) for value in vector):
        return [float(value) for value in vector]
    return None


@lru_cache(maxsize=1)
def _heacalculator_api():
    """Import HEACalculator lazily, translating absence to the typed error."""
    try:
        import HEACalculator
    except ImportError as exc:
        raise BackendUnavailableError(
            'the "heacalculator" descriptor backend needs the optional '
            "HEACalculator package, which is not installed. Install it "
            'with: pip install "hea-bench[interop]"'
        ) from exc
    return HEACalculator


#: Union descriptor name -> HEACalculator ``get_dict`` key. Verified
#: against HEACalculator 2.0.1. Only same-published-quantity mappings
#: appear here; a name absent from this table is deliberately unmapped:
#:
#: - ``smix``/``vec``/``omega``/``melting_temperature``: identical
#:   definitions (their melting point is ceil-rounded, a sub-kelvin
#:   difference).
#: - ``delta`` maps to their ``delta_cn12``: both are the Fang formula
#:   over CN12 metallic radii, from different radius tabulations. Their
#:   plain ``delta`` uses generic atomic radii and is exposed separately
#:   as ``delta_atomic_radius``.
#: - ``mixing_enthalpy``: same regular-solution form over binary pair
#:   enthalpies. Both packages vendor tables in the Takeuchi-Inoue and
#:   Miedema lineage (ours via matminer), and the agreement panel
#:   measures them as near-identical; the mapping still treats the value
#:   as backend-owned data (docs/backend-agreement.md).
#: - ``singh_lambda``: same Singh formula, both over CN12 delta.
#: - ``wang_gamma``: same Wang formula; they evaluate it over generic
#:   atomic radii where we use CN12, the largest convention gap in the
#:   mapped set.
#: - King-family quantities (delta_g_ss, delta_g_max, phi_king), phi_ye,
#:   s_excess, delta_chi, mean_electronegativity, h_elastic are NOT
#:   mapped: their implementations differ structurally from ours (for
#:   example their delta_g_max scales the Miedema intermetallic term by
#:   j/2 where ours is the unscaled most-negative pair), and mapping
#:   near-equivalents silently is exactly what this layer refuses to do.
#: - Their verdict strings (microstructure, model_1..model_8) are rules,
#:   not descriptors, and are out of scope for this backend.
_HEACALCULATOR_KEYS = {
    "smix": "mixing_entropy",
    "delta": "delta_cn12",
    "vec": "vec",
    "melting_temperature": "melting_temperature",
    "mixing_enthalpy": "mixing_enthalpy",
    "omega": "omega",
    "singh_lambda": "lambda",
    "wang_gamma": "gamma",
    "density": "density",
    "delta_atomic_radius": "delta",
    "delta_chi_allen_pct": "delta_chi_allen",
    "delta_chi_pauling_pct": "delta_chi_pauling",
    "ea_ratio": "ea_ratio",
    "formation_enthalpy": "formation_enthalpy",
    "min_formation_enthalpy": "min_formation_enthalpy",
}


class HEACalculatorBackend:
    """Adapter over an installed HEACalculator (optional interop extra).

    HEACalculator raises at construction for compositions containing
    elements outside its database; the adapter reports such compositions
    as all-None rather than propagating upstream exception types. Their
    missing-pair sentinel (NaN) also becomes None.
    """

    name = "heacalculator"

    def __init__(self) -> None:
        self._api = _heacalculator_api()

    def descriptor_names(self) -> tuple[str, ...]:
        return tuple(_HEACALCULATOR_KEYS)

    def matrix_names(self) -> tuple[str, ...]:
        # singh_lambda is excluded for the same reason the native matrix
        # excludes it: infinite whenever the CN12 delta is zero.
        return tuple(name for name in _HEACALCULATOR_KEYS if name != "singh_lambda")

    def compute(self, composition: Composition) -> dict[str, float | None]:
        comp = normalize(composition)
        formula = "".join(f"{element}{comp[element]:.6f}" for element in sorted(comp))
        values: dict[str, float | None] = dict.fromkeys(UNION_DESCRIPTOR_NAMES)
        try:
            data = self._api.HEACalculator(formula).get_dict()
        except Exception:
            return values
        for name, key in _HEACALCULATOR_KEYS.items():
            raw = data.get(key)
            if raw is None:
                continue
            value = float(raw)
            values[name] = None if value != value else value
        return values


def get_backend(backend: str | DescriptorBackend | None = None) -> DescriptorBackend:
    """Resolve a backend name or instance; None means the native default.

    Raises
    ------
    ValueError
        If a name is not one of ``"native"`` or ``"heacalculator"``.
    BackendUnavailableError
        If ``"heacalculator"`` is requested but not installed.
    """
    if backend is None:
        return NativeBackend()
    if isinstance(backend, str):
        if backend == "native":
            return NativeBackend()
        if backend == "heacalculator":
            return HEACalculatorBackend()
        raise ValueError(
            f"unknown descriptor backend {backend!r}; expected 'native', "
            f"'heacalculator', or a DescriptorBackend instance"
        )
    return backend


__all__ = [
    "UNION_DESCRIPTOR_NAMES",
    "UNITS",
    "BackendUnavailableError",
    "DescriptorBackend",
    "HEACalculatorBackend",
    "NativeBackend",
    "get_backend",
    "matrix_vector",
    "scorable_elements",
]
