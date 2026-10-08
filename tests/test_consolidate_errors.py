"""The corpus build must fail loudly and completely when a source is missing.

A silently partial corpus would carry the wrong digests and the wrong
row counts while looking healthy; the build refuses to produce one.
"""

import hashlib
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
    assert "reinstall hea-bench" in message
    assert "partial corpus" in message
    assert not (out_dir / "consolidated.csv").exists()
    assert not (out_dir / "manifest.json").exists()


def test_prefix_table_is_shared_with_the_corpus_package() -> None:
    """One schema authority: the build and the reader must agree."""
    from hea_bench.corpus import SOURCE_COLUMN_PREFIX

    assert consolidate._SOURCE_COLUMN_PREFIX is SOURCE_COLUMN_PREFIX


def test_the_shipped_peivaste_file_is_the_pinned_one() -> None:
    """A line-ending conversion would change every published number."""
    from hea_bench import _paths
    from hea_bench.benchmark.loaders import peivaste

    shipped = _paths.raw_dir() / "peivaste" / peivaste.DEFAULT_CSV_NAME
    assert hashlib.sha256(shipped.read_bytes()).hexdigest() == peivaste.SHA256, (
        f"{shipped} is not the pinned file; .gitattributes must keep it -text"
    )


def test_the_peivaste_loader_refuses_other_bytes(tmp_path) -> None:
    from hea_bench.benchmark.loaders import peivaste

    wrong = tmp_path / peivaste.DEFAULT_CSV_NAME
    wrong.write_bytes(b"not the pinned file")
    with pytest.raises(ValueError, match="pinned"):
        next(peivaste.load(wrong))
