"""Tests for hea_bench.composition (formula parsing, normalization)."""

import pytest

from hea_bench.composition import (
    from_element_columns,
    normalize,
    parse_formula,
)


def test_parse_unit_amounts_cantor() -> None:
    """Each Cantor element gets equal 0.2 fraction."""
    got = parse_formula("CoCrFeMnNi")
    assert got == {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}


def test_parse_borg_style_with_spaces() -> None:
    """Borg's 'Al0.25 Co1 Fe1 Ni1' parses to proportional amounts then normalizes."""
    got = parse_formula("Al0.25 Co1 Fe1 Ni1")
    # 0.25 + 1 + 1 + 1 = 3.25 total
    assert got["Al"] == pytest.approx(0.25 / 3.25, rel=1e-12)
    assert got["Co"] == pytest.approx(1.0 / 3.25, rel=1e-12)
    assert sum(got.values()) == pytest.approx(1.0, abs=1e-12)


def test_parse_pei_style_no_spaces() -> None:
    """Pei's 'Al0.15Cr0.85' parses with already-summing-to-1 fractions."""
    got = parse_formula("Al0.15Cr0.85")
    assert got == pytest.approx({"Al": 0.15, "Cr": 0.85}, rel=1e-12)


def test_parse_mixed_implicit_explicit_coefficients() -> None:
    """Mix of implicit (=1) and explicit coefficients."""
    got = parse_formula("AlCoCrCu0.5Fe")
    # totals: 1+1+1+0.5+1 = 4.5
    assert got["Al"] == pytest.approx(1 / 4.5, rel=1e-12)
    assert got["Cu"] == pytest.approx(0.5 / 4.5, rel=1e-12)
    assert sum(got.values()) == pytest.approx(1.0, abs=1e-12)


def test_parse_duplicate_element_accumulates() -> None:
    """If the same element appears twice in a formula, sum the amounts."""
    got = parse_formula("Fe1Co1Fe1")
    assert got == pytest.approx({"Fe": 2 / 3, "Co": 1 / 3}, rel=1e-12)


def test_parse_allows_whitespace_between_complete_tokens() -> None:
    got = parse_formula("  Al0.25\tCo1\nFe1 Ni1  ")
    assert got == pytest.approx(
        {"Al": 0.25 / 3.25, "Co": 1 / 3.25, "Fe": 1 / 3.25, "Ni": 1 / 3.25},
        rel=1e-12,
    )


@pytest.mark.parametrize(
    "formula",
    [
        "Fe0.5???Co0.5",
        "Fe-1Co2",
        "Fe1e3Co1",
        "???Fe1Co1",
        "Fe1Co1???",
        "Fe1,Co1",
        "Fe 1 Co 2",
        "(Fe1Co1",
        "Fe1Co1)",
        "()Fe",
        "(CoCrFeNi) 95Al5",
    ],
)
def test_parse_rejects_unconsumed_non_whitespace(formula: str) -> None:
    with pytest.raises(ValueError):
        parse_formula(formula)


def test_parse_rejects_empty() -> None:
    with pytest.raises(ValueError):
        parse_formula("")


def test_parse_rejects_no_elements() -> None:
    with pytest.raises(ValueError):
        parse_formula("12345")


def test_parse_rejects_invalid_element_symbol() -> None:
    """Tokens that look like elements but are not real periodic-table
    symbols must raise rather than silently produce a phantom element."""
    with pytest.raises(ValueError, match="unrecognised element symbol"):
        parse_formula("Al0.5Xy0.5")
    with pytest.raises(ValueError, match="unrecognised element symbol"):
        parse_formula("Qq")
    # Sanity check: a real element next to a bogus one still surfaces the
    # bogus one rather than half-silently parsing.
    with pytest.raises(ValueError, match="Zz"):
        parse_formula("FeZz")


def test_normalize_skips_zero_elements() -> None:
    got = normalize({"Fe": 1.0, "Co": 0.0, "Ni": 1.0})
    assert got == {"Fe": 0.5, "Ni": 0.5}


def test_normalize_rejects_all_zero() -> None:
    with pytest.raises(ValueError):
        normalize({"Fe": 0.0, "Co": 0.0})


def test_from_element_columns_basic() -> None:
    """Peivaste-style parsing: each element is its own column."""
    row = {"Al": "0.0", "Co": "0.2", "Cr": "0.2", "Fe": "0.2", "Mn": "0.2", "Ni": "0.2"}
    got = from_element_columns(row, ["Al", "Co", "Cr", "Fe", "Mn", "Ni"])
    assert got == {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}


def test_from_element_columns_ignores_missing_and_nonnumeric() -> None:
    row = {"Fe": "0.5", "Co": "0.5", "Ni": "", "Cr": "n/a"}
    got = from_element_columns(row, ["Fe", "Co", "Ni", "Cr", "Mn"])
    assert got == {"Fe": 0.5, "Co": 0.5}


def test_parse_group_notation_is_one_unit_with_its_own_amount() -> None:
    """(CoCrFeNi)95Al5 is 95 parts equimolar CoCrFeNi plus 5 parts Al,
    the HEA convention, not Co95Cr95Fe95Ni95Al5."""
    assert parse_formula("(CoCrFeNi)95Al5") == pytest.approx(
        {"Co": 0.2375, "Cr": 0.2375, "Fe": 0.2375, "Ni": 0.2375, "Al": 0.05}, rel=1e-12
    )
    # Ratios inside the group are kept, and groups nest.
    assert parse_formula("(Co2CrFeNi)95Al5")["Co"] == pytest.approx(0.38, rel=1e-12)
    nested = parse_formula("((CoCrFeNi)90Al10)95Ti5")
    assert nested["Al"] == pytest.approx(0.095, rel=1e-12)
    assert nested["Ti"] == pytest.approx(0.05, rel=1e-12)
    # A group with no number counts as one part.
    assert parse_formula("(Fe1Co1)") == pytest.approx({"Fe": 0.5, "Co": 0.5}, rel=1e-12)


def test_every_public_composition_function_accepts_a_formula() -> None:
    """hb.smix("CoCrFeMnNi") must work like hb.smix(parse_formula(...)).
    Every public function whose first argument is ``composition`` wears
    hea_bench.composition.accepts_formula; this fails for one that does not."""
    import importlib
    import inspect
    import json
    from pathlib import Path

    from hea_bench import rules

    registry = json.loads(
        (Path(__file__).resolve().parent / "data" / "feature_parity.json").read_text(encoding="utf-8")
    )
    names = [n for f in registry["features"].values() for n in f.get("covers", [])]
    names += [f"hea_bench.rules.{module}.predict" for module in rules.VERDICT_FUNCTIONS]
    missing = []
    for name in sorted(set(names)):
        if not name.startswith("hea_bench."):
            continue
        module, _, attr = name.rpartition(".")
        try:
            obj = getattr(importlib.import_module(module), attr)
        except (ImportError, AttributeError):
            continue
        if not callable(obj) or isinstance(obj, type):
            continue
        try:
            params = list(inspect.signature(obj).parameters)
        except (TypeError, ValueError):
            continue
        if params[:1] == ["composition"] and getattr(obj, "__wrapped__", None) is None:
            missing.append(name)
    assert not missing, (
        f"{missing} take a composition but not a formula string. Fix: decorate each with "
        "@accepts_formula from hea_bench.composition."
    )
    import hea_bench as hb

    assert hb.smix("CoCrFeMnNi") == hb.smix(parse_formula("CoCrFeMnNi"))
