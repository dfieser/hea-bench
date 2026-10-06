"""Where hea-bench reads and writes its data files.

There are two layouts. In a repository checkout, and in the web app's
in-page engine, which mirrors one, the mirrored source datasets live in
``data/raw`` and built corpora in ``data/consolidated``. An installed
wheel carries the mirrored datasets inside the package (``_data``, put
there by the wheel build in pyproject.toml) and keeps what it downloads
and builds in a per-user folder, because site-packages may not be
writable. Every data path in the package comes from this module, so the
two layouts cannot drift apart.
"""

from __future__ import annotations

import os
import pathlib
import runpy
import sys

_PACKAGE = pathlib.Path(__file__).resolve().parent
_BUNDLED = _PACKAGE / "_data"
REPO_ROOT = _PACKAGE.parents[1]


def installed() -> bool:
    """True in an installed wheel, False in a checkout or the app's engine."""
    return _BUNDLED.is_dir()


def user_dir() -> pathlib.Path:
    """The per-user folder a wheel install downloads and builds into."""
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


def peivaste_csv() -> pathlib.Path:
    """Where the Peivaste file is kept once downloaded. It is never shipped."""
    folder = user_dir() / "raw" / "peivaste" if installed() else raw_dir() / "peivaste"
    return folder / "dataset11252_79.csv"


def peivaste_recipe() -> dict:
    """The Peivaste download recipe: its URL and pinned size and SHA-256."""
    return runpy.run_path(str(raw_dir() / "peivaste" / "fetch.py"))


def consolidated_dir() -> pathlib.Path:
    """The default parent folder of built corpus versions."""
    return user_dir() / "consolidated" if installed() else REPO_ROOT / "data" / "consolidated"


def baselines_json() -> pathlib.Path:
    """The published benchmark baseline table."""
    if installed():
        return _BUNDLED / "benchmark-baselines.json"
    return REPO_ROOT / "docs" / "benchmark-baselines.json"
