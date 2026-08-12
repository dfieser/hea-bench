"""Tests for the CLI, including the describe subcommand."""

import json
import sys

import pytest

from hea_bench.cli import main
from hea_bench.descriptors import backend as backend_mod


def test_bare_invocation_prints_version_pointer(capsys) -> None:
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "hea-bench" in out


def test_describe_prints_descriptor_json(capsys) -> None:
    assert main(["describe", "CoCrFeMnNi"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["backend"] == "native"
    assert payload["composition"]["Co"] == pytest.approx(0.2)
    smix = payload["descriptors"]["smix"]
    assert smix["value"] == pytest.approx(13.381, abs=5e-4)
    assert smix["unit"] == "J/(mol K)"


def test_describe_nulls_unbounded_values_for_strict_json(capsys) -> None:
    """Equal radii make singh_lambda infinite; JSON must stay parseable."""
    assert main(["describe", "CoNi"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["descriptors"]["singh_lambda"]["value"] is None
    assert any("singh_lambda" in warning for warning in payload["warnings"])


def test_describe_bad_formula_exits_2(capsys) -> None:
    assert main(["describe", "NotAFormula!!"]) == 2
    assert "could not parse" in capsys.readouterr().err


def test_describe_unknown_backend_is_rejected_by_argparse() -> None:
    with pytest.raises(SystemExit):
        main(["describe", "CoCrFeMnNi", "--backend", "nope"])


def test_describe_missing_heacalculator_is_a_typed_failure(capsys, monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "HEACalculator", None)
    backend_mod._heacalculator_api.cache_clear()
    try:
        assert main(["describe", "CoCrFeMnNi", "--backend", "heacalculator"]) == 2
        assert 'hea-bench[interop]' in capsys.readouterr().err
    finally:
        backend_mod._heacalculator_api.cache_clear()
