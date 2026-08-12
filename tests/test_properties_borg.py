"""Tests for the Borg mechanical-property loader."""

import pathlib
import textwrap

import pytest

from hea_bench.properties.borg import (
    PropertyRecord,
    experimental_density_records,
    hardness_records,
)

_BORG_CSV = (
    pathlib.Path(__file__).resolve().parents[1]
    / "data"
    / "raw"
    / "borg2020"
    / "MPEA_dataset.csv"
)

needs_borg = pytest.mark.skipif(not _BORG_CSV.exists(), reason="Borg mirror missing")


@needs_borg
def test_hardness_census_is_pinned() -> None:
    """417 unique room-temperature (formula, processing) HV alloys.

    The mirrored CSV is immutable, so these are constants of the tree;
    a change means the loader rules moved, not the data.
    """
    records = hardness_records()
    assert len(records) == 417
    assert all(isinstance(record, PropertyRecord) for record in records)
    assert all(record.value > 0 for record in records)
    values = sorted(record.value for record in records)
    assert values[0] == pytest.approx(109.0)
    assert values[-1] == pytest.approx(1183.0)


@needs_borg
def test_experimental_density_census_is_pinned() -> None:
    records = experimental_density_records()
    assert len(records) == 49
    assert all(0.5 < record.value < 20.0 for record in records)


def _mini_csv(tmp_path: pathlib.Path, body: str) -> pathlib.Path:
    header = (
        "IDENTIFIER: Reference ID,FORMULA,PROPERTY: Processing method,"
        "PROPERTY: HV,PROPERTY: Test temperature ($^\\circ$C),"
        "PROPERTY: Exp. Density (g/cm$^3$),REFERENCE: doi,REFERENCE: year"
    )
    path = tmp_path / "mini.csv"
    path.write_text(textwrap.dedent(header) + "\n" + textwrap.dedent(body), encoding="utf-8")
    return path


def test_duplicate_measurements_collapse_to_the_median(tmp_path) -> None:
    path = _mini_csv(
        tmp_path,
        """\
        r1,Co1 Fe1,CAST,100,,,10.1/x,2019
        r2,Co1 Fe1,CAST,200,25.0,,10.1/x,2019
        r3,Co1 Fe1,CAST,300,,,10.1/x,2019
        """,
    )
    records = hardness_records(path)
    assert len(records) == 1
    assert records[0].value == 200.0
    assert records[0].composition == {"Co": 0.5, "Fe": 0.5}
    assert records[0].processing == "CAST"


def test_elevated_temperature_rows_are_excluded(tmp_path) -> None:
    """Hot hardness is a different quantity; only near-room-T rows load."""
    path = _mini_csv(
        tmp_path,
        """\
        r1,Co1 Fe1,CAST,100,1000.0,,,
        r2,Co1 Fe1,CAST,150,25.0,,,
        """,
    )
    records = hardness_records(path)
    assert len(records) == 1
    assert records[0].value == 150.0


def test_processing_states_stay_distinct(tmp_path) -> None:
    path = _mini_csv(
        tmp_path,
        """\
        r1,Co1 Fe1,CAST,100,,,,
        r2,Co1 Fe1,ANNEAL,300,,,,
        """,
    )
    records = hardness_records(path)
    assert {record.processing for record in records} == {"CAST", "ANNEAL"}
