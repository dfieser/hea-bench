"""Where hea-bench reads and writes its data files.

There are two layouts. A repository checkout keeps the mirrored source
datasets in ``data/raw`` and built corpora in ``data/consolidated``, and
so does the web app's in-page engine, which mirrors a checkout. An
installed wheel carries the mirrored datasets inside the package
(``_data``, put there by the wheel build in pyproject.toml) and keeps
what it builds in a per-user folder, because site-packages may not be
writable. Every data path in the package comes from this module, so the
two layouts cannot drift apart.
"""

from __future__ import annotations

import os
import pathlib
import sys

_PACKAGE = pathlib.Path(__file__).resolve().parent
_BUNDLED = _PACKAGE / "_data"
REPO_ROOT = _PACKAGE.parents[1]


def installed() -> bool:
    """True in an installed wheel, False in a checkout or the app's engine."""
    return _BUNDLED.is_dir()


def user_dir() -> pathlib.Path:
    """The per-user folder a wheel install builds into."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or pathlib.Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        base = pathlib.Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_DATA_HOME") or pathlib.Path.home() / ".local" / "share"
    return pathlib.Path(base) / "hea-bench"


def raw_dir() -> pathlib.Path:
    """The mirrored source datasets, read-only."""
    return _BUNDLED / "raw" if installed() else REPO_ROOT / "data" / "raw"


def consolidated_dir() -> pathlib.Path:
    """The default parent folder of built corpus versions."""
    return user_dir() / "consolidated" if installed() else REPO_ROOT / "data" / "consolidated"


def baselines_json() -> pathlib.Path:
    """The published benchmark baseline table."""
    if installed():
        return _BUNDLED / "benchmark-baselines.json"
    return REPO_ROOT / "docs" / "benchmark-baselines.json"


#: Points corpus reads and builds at another folder, with ``v<version>`` appended.
CORPUS_DIR_ENV = "HEA_BENCH_BENCHMARK_DIR"

#: Source name -> short CSV column prefix. The consolidated CSV schema
#: derives its per-source label columns from this table (the build in
#: hea_bench.benchmark.consolidate and the reader in hea_bench.corpus
#: both import it from here).
SOURCE_COLUMN_PREFIX = {
    "borg2020": "borg",
    "pei2020": "pei",
    "peivaste": "peivaste",
    "chizhevskiy2026": "chizhevskiy",
}


def corpus_location(version: str, corpus_dir: pathlib.Path | None = None) -> pathlib.Path:
    """Resolve the directory a corpus version is read from.

    Explicit ``corpus_dir`` wins, then the ``HEA_BENCH_BENCHMARK_DIR``
    environment variable (with ``v<version>`` appended), then the
    default: ``data/consolidated/v<version>`` in a repository checkout,
    and ``consolidated/v<version>`` in the per-user hea-bench folder for
    an installed package (``%LOCALAPPDATA%\\hea-bench`` on Windows,
    ``~/.local/share/hea-bench`` on Linux and
    ``~/Library/Application Support/hea-bench`` on macOS).
    """
    if corpus_dir is not None:
        return pathlib.Path(corpus_dir)
    override = os.environ.get(CORPUS_DIR_ENV)
    if override:
        return pathlib.Path(override) / f"v{version}"
    return consolidated_dir() / f"v{version}"
