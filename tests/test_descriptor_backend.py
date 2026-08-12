"""Tests for the descriptor backend abstraction.

The backend layer lets a caller compute descriptors with this package's
own stdlib implementations (the default) or with an external calculator
adapted to the same protocol. The native path must agree exactly with
the direct function calls, and a missing optional backend must fail
with a typed error naming the install, never a bare ImportError.
"""

import math
import sys

import pytest

import hea_bench as hb
from hea_bench.descriptors import backend as backend_mod
from hea_bench.descriptors.backend import (
    UNION_DESCRIPTOR_NAMES,
    BackendUnavailableError,
    NativeBackend,
    get_backend,
)

CANTOR = {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}


def test_native_backend_matches_direct_functions() -> None:
    """The native backend is a view over the library, not a reimplementation."""
    values = NativeBackend().compute(CANTOR)
    assert values["smix"] == pytest.approx(hb.smix(CANTOR))
    assert values["smix"] == pytest.approx(13.381, abs=5e-4)
    assert values["delta"] == pytest.approx(3.164, abs=5e-4)
    assert values["vec"] == pytest.approx(8.0, abs=5e-4)
    assert values["omega"] == pytest.approx(5.794, abs=5e-4)
    assert values["h_elastic"] == pytest.approx(hb.h_elastic(CANTOR))


def test_native_backend_covers_every_union_name() -> None:
    """compute() answers for the whole union, with None for foreign names."""
    values = NativeBackend().compute(CANTOR)
    assert set(values) == set(UNION_DESCRIPTOR_NAMES)
    for name in NativeBackend().descriptor_names():
        assert name in values


def test_native_backend_returns_none_for_uncovered_elements() -> None:
    """Missing element data yields None per descriptor, never an exception."""
    values = NativeBackend().compute({"Co": 0.5, "Fr": 0.5})
    # smix is pure math over the fractions and needs no element table.
    assert values["smix"] == pytest.approx(hb.smix({"Co": 0.5, "Fr": 0.5}))
    # delta needs a radius for Fr, which the table does not carry.
    assert values["delta"] is None
    # h_elastic already returns None for missing mechanics data.
    assert values["h_elastic"] is None


def test_native_matrix_names_match_benchmark_descriptor_names() -> None:
    """The matrix subset must stay aligned with the benchmark feature order."""
    from hea_bench.benchmark.corpus import descriptor_names

    assert NativeBackend().matrix_names() == descriptor_names()


def test_get_backend_defaults_to_native() -> None:
    assert isinstance(get_backend(), NativeBackend)
    assert isinstance(get_backend(None), NativeBackend)
    assert isinstance(get_backend("native"), NativeBackend)


def test_get_backend_passes_instances_through() -> None:
    instance = NativeBackend()
    assert get_backend(instance) is instance


def test_get_backend_rejects_unknown_names() -> None:
    with pytest.raises(ValueError, match="native"):
        get_backend("not-a-backend")


def test_missing_heacalculator_raises_typed_error(monkeypatch) -> None:
    """The optional backend must name its install, not traceback on import."""
    monkeypatch.setitem(sys.modules, "HEACalculator", None)
    backend_mod._heacalculator_api.cache_clear()
    try:
        with pytest.raises(BackendUnavailableError, match=r"hea-bench\[interop\]"):
            get_backend("heacalculator")
    finally:
        backend_mod._heacalculator_api.cache_clear()


def test_union_names_are_unique_and_include_native() -> None:
    assert len(UNION_DESCRIPTOR_NAMES) == len(set(UNION_DESCRIPTOR_NAMES))
    assert set(NativeBackend().descriptor_names()) <= set(UNION_DESCRIPTOR_NAMES)


def test_native_compute_handles_unbounded_values() -> None:
    """A mathematically divergent descriptor stays a float, not a crash.

    Equal tabulated radii make delta zero and singh_lambda infinite; the
    backend reports the infinity and leaves JSON-safety to the surfaces
    that need it (the MCP layer nulls it there).
    """
    values = NativeBackend().compute({"Co": 0.5, "Ni": 0.5})
    assert values["singh_lambda"] == math.inf or values["singh_lambda"] > 0


# --- descriptor_matrix threading ------------------------------------------


def test_descriptor_matrix_backend_native_is_identical() -> None:
    from hea_bench.benchmark.corpus import descriptor_matrix

    assert descriptor_matrix([CANTOR], backend="native") == descriptor_matrix([CANTOR])


def test_descriptor_matrix_rejects_unknown_backend() -> None:
    from hea_bench.benchmark.corpus import descriptor_matrix

    with pytest.raises(ValueError, match="native"):
        descriptor_matrix([CANTOR], backend="not-a-backend")


def test_descriptor_matrix_backend_none_value_raises_typed() -> None:
    """A backend gap must raise naming the descriptor, never impute."""
    from hea_bench.benchmark.corpus import descriptor_matrix

    class OneHoleBackend(NativeBackend):
        def compute(self, composition):
            values = super().compute(composition)
            values["omega"] = None
            return values

    with pytest.raises(ValueError, match="omega"):
        descriptor_matrix([CANTOR], backend=OneHoleBackend())


def test_descriptor_names_accepts_backend() -> None:
    from hea_bench.benchmark.corpus import descriptor_names

    assert descriptor_names() == descriptor_names(backend="native")
    assert descriptor_names() == NativeBackend().matrix_names()


# --- HEACalculator adapter (needs the interop extra) ----------------------


heacalculator = pytest.importorskip("HEACalculator")


def test_heacalculator_backend_answers_the_union() -> None:
    values = get_backend("heacalculator").compute(CANTOR)
    assert set(values) == set(UNION_DESCRIPTOR_NAMES)


def test_heacalculator_identical_definitions_agree() -> None:
    """Same-definition quantities agree closely, not exactly.

    VEC comes out exact for the Cantor alloy. smix is the same formula
    with the same gas constant, but HEACalculator rounds compositions
    internally, so even the equiatomic maximum R ln 5 differs in the
    fourth decimal. The documented comparison lives in
    docs/backend-agreement.md; this only pins that the mapping points at
    the right quantity.
    """
    values = get_backend("heacalculator").compute(CANTOR)
    assert values["vec"] == pytest.approx(8.0, abs=1e-9)
    assert values["smix"] == pytest.approx(hb.smix(CANTOR), abs=2e-2)


def test_heacalculator_same_quantity_different_tables_is_close_not_equal() -> None:
    """delta maps to their CN12 delta: same formula, different radius table.

    The window is deliberately loose; the exact deltas belong in
    docs/backend-agreement.md, not in an equality assertion.
    """
    values = get_backend("heacalculator").compute(CANTOR)
    assert values["delta"] == pytest.approx(hb.delta(CANTOR), abs=0.5)
    assert values["mixing_enthalpy"] is not None


def test_heacalculator_native_only_names_are_none() -> None:
    """Quantities we deliberately do not map must come back None."""
    values = get_backend("heacalculator").compute(CANTOR)
    for name in ("phi_king", "phi_ye", "delta_chi", "s_excess", "h_elastic"):
        assert values[name] is None


def test_heacalculator_only_names_are_none_under_native() -> None:
    values = NativeBackend().compute(CANTOR)
    for name in ("density", "ea_ratio", "formation_enthalpy"):
        assert values[name] is None


def test_heacalculator_uncovered_composition_is_all_none() -> None:
    """Their calculator refuses at construction for uncovered elements."""
    values = get_backend("heacalculator").compute({"U": 0.5, "Th": 0.5})
    assert all(value is None for value in values.values())


def test_heacalculator_values_are_plain_floats() -> None:
    """numpy scalars from upstream are cast so payloads stay stdlib."""
    values = get_backend("heacalculator").compute(CANTOR)
    for name, value in values.items():
        assert value is None or type(value) is float, name
