"""The corpus build must fail loudly and completely when a source is missing.

A silently partial corpus would carry the wrong digests and the wrong
row counts while looking healthy; the build refuses to produce one.
"""

import pathlib

import pytest

from hea_bench.benchmark import consolidate


def test_missing_source_fails_loudly_and_writes_nothing(tmp_path, monkeypatch) -> None:
    bogus = dict(consolidate._SOURCE_PATHS)
    bogus["peivaste"] = pathlib.Path("no-such-directory") / "missing.csv"
    monkeypatch.setattr(consolidate, "_SOURCE_PATHS", bogus)

    out_dir = tmp_path / "v0.1.0"
    with pytest.raises(FileNotFoundError) as caught:
        consolidate.build("0.1.0", out_dir=out_dir)
    message = str(caught.value)
    assert "peivaste" in message
    assert "fetch.py" in message
    assert "partial corpus" in message
    assert not (out_dir / "consolidated.csv").exists()
    assert not (out_dir / "manifest.json").exists()


def test_prefix_table_is_shared_with_the_corpus_package() -> None:
    """One schema authority: the build and the reader must agree."""
    from hea_bench.corpus import SOURCE_COLUMN_PREFIX

    assert consolidate._SOURCE_COLUMN_PREFIX is SOURCE_COLUMN_PREFIX
