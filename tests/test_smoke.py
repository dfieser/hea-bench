"""Phase 0 smoke test: the package imports and reports a version."""

import re

import hea_bench


def test_version_is_string():
    assert isinstance(hea_bench.__version__, str)


def test_version_matches_semver():
    assert re.match(r"^\d+\.\d+\.\d+", hea_bench.__version__)


def test_cli_module_imports():
    from hea_bench import cli  # noqa: F401
