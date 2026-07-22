"""Tests for the vendored Miedema pair-enthalpy table loader."""

import pytest

from hea_bench.descriptors.data import pair_enthalpies as pe
from hea_bench.descriptors.data.elemental import ELEMENTAL_DATA


# ---- Loader cache ----

def test_load_table_returns_dict() -> None:
    table = pe._load_table()
    assert isinstance(table, dict)
    assert len(table) > 2000  # matminer ships ~2628


def test_load_table_is_cached() -> None:
    """LRU cache means second call returns same object."""
    assert pe._load_table() is pe._load_table()


# ---- Spot-check known canonical HEA pair values from the literature ----
# These are pinned ground truth from the vendored matminer table, which
# cross-verifies against Takeuchi-Inoue 2005 Table 1 (see README.md).

CANONICAL_PAIRS = [
    ("Al", "Ni", -22.0),  # classic HEA-forming pair
    ("Al", "Fe", -11.0),
    ("Al", "Co", -19.0),
    ("Cr", "Fe", -1.0),
    ("Co", "Fe", -1.0),
    ("Cu", "Ni",  4.0),   # positive ΔH^mix → unfavourable mixing
    ("Ni", "Fe", -2.0),
    ("Ti", "Ni", -35.0),  # very negative; intermetallic-former
    ("Mo", "Ni", -7.0),
]


@pytest.mark.parametrize("a, b, expected", CANONICAL_PAIRS)
def test_canonical_pair_values(a: str, b: str, expected: float) -> None:
    assert pe.pair_enthalpy(a, b) == expected


@pytest.mark.parametrize("a, b, expected", CANONICAL_PAIRS)
def test_pair_lookup_is_symmetric(a: str, b: str, expected: float) -> None:
    """pair_enthalpy(A, B) == pair_enthalpy(B, A) for every canonical case."""
    assert pe.pair_enthalpy(b, a) == pe.pair_enthalpy(a, b) == expected


# ---- Self-pair convention ----

def test_self_pair_is_zero() -> None:
    """A pure element mixed with itself has zero enthalpy of mixing."""
    for sym in ("Fe", "Co", "Cr", "Ni", "Al", "V", "W"):
        assert pe.pair_enthalpy(sym, sym) == 0.0


# ---- Coverage ----

def test_full_pair_coverage_of_55_element_table_except_th_u() -> None:
    """Every (i, j) pair from our 55-element ELEMENTAL_DATA must be in
    the vendored Miedema table, with exactly one known exception:
    Th-U is absent from matminer's 2628-pair file (the only
    actinide-actinide pair our table would need). The exception is
    pinned exactly so any OTHER vendored-data drift still surfaces.
    Compositions containing both Th and U raise KeyError from
    pair_enthalpy, by design (no silent zero)."""
    our_elements = set(ELEMENTAL_DATA)
    missing = pe.missing_pairs(our_elements)
    assert missing == {frozenset({"Th", "U"})}, f"missing pairs: {sorted(missing)}"


def test_table_covers_more_than_our_table() -> None:
    """matminer ships 75 elements; confirm headroom beyond our 55."""
    elems = pe.covered_elements()
    assert len(elems) >= 70  # exactly 75 today; allow some margin


def test_missing_pair_raises_keyerror() -> None:
    """Pairs involving elements outside the 75 covered must raise."""
    with pytest.raises(KeyError, match="not in Miedema pair-enthalpy table"):
        pe.pair_enthalpy("Fe", "Xe")  # Xe not in matminer's table


# ---- License integrity ----

def test_matminer_license_file_present() -> None:
    """BSD-3 requires retaining the upstream license alongside the data."""
    import importlib.resources
    license_path = (
        importlib.resources.files("hea_bench.descriptors.data")
        .joinpath("LICENSE.matminer.txt")
    )
    text = license_path.read_text(encoding="utf-8")
    assert "matminer" in text
    assert "Lawrence Berkeley National Laboratory" in text
    assert "BSD" not in text  # the BSD-3 text doesn't literally say "BSD"
    assert "Redistribution and use" in text
