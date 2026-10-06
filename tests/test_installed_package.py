"""Build the sdist and the wheel, install the wheel fresh, use every feature.

The other tests import the package from this checkout, where the data
files sit in data/ and docs/. PyPI users get the wheel instead, so this
builds it, checks what it ships, installs it with its ``mcp`` extra in a
new virtual environment, and runs tests/package_smoke.py there: every
MCP tool over real stdio, then the library, from an empty per-user data
folder.

Opt-in, because it builds, creates an environment and installs the
dependencies (a few minutes): HEA_BENCH_PACKAGE_SMOKE=1. The release
preflight and the CI ``package`` job set it.
"""

import os
import pathlib
import shutil
import subprocess
import sys
import tarfile
import venv
import zipfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PEIVASTE = ROOT / "data" / "raw" / "peivaste" / "dataset11252_79.csv"

pytestmark = pytest.mark.skipif(
    os.environ.get("HEA_BENCH_PACKAGE_SMOKE") != "1",
    reason="opt-in: set HEA_BENCH_PACKAGE_SMOKE=1 (builds and installs the wheel)",
)


@pytest.fixture(scope="module")
def dist(tmp_path_factory) -> pathlib.Path:
    out = tmp_path_factory.mktemp("dist")
    subprocess.run([sys.executable, "-m", "build", "--outdir", str(out), str(ROOT)], check=True)
    return out


def test_distributions_ship_the_data_but_never_the_unlicensed_file(dist) -> None:
    (wheel,) = dist.glob("*.whl")
    (sdist,) = dist.glob("*.tar.gz")
    shipped = set(zipfile.ZipFile(wheel).namelist())
    for needed in (
        "hea_bench/_data/benchmark-baselines.json",
        "hea_bench/_data/raw/borg2020/MPEA_dataset.csv",
        "hea_bench/_data/raw/pei2020/pei2020_alloys_phases.csv",
        "hea_bench/_data/raw/chizhevskiy2026/database_of_HEAs.csv",
        "hea_bench/_data/raw/peivaste/fetch.py",
        "hea_bench/descriptors/data/miedema_parameters.csv",
    ):
        assert needed in shipped, f"the wheel lacks {needed}; see [tool.hatch.build] in pyproject.toml"
    assert not any("dataset11252_79" in name for name in shipped)
    with tarfile.open(sdist) as archive:
        assert not any("dataset11252_79" in name for name in archive.getnames())


def test_the_installed_wheel_runs_every_feature(dist, tmp_path) -> None:
    (wheel,) = dist.glob("*.whl")
    environment = tmp_path / "venv"
    venv.EnvBuilder(with_pip=True).create(environment)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    subprocess.run(
        [str(python), "-m", "pip", "install", "--quiet", "--disable-pip-version-check", f"{wheel}[mcp]"],
        check=True,
    )
    # An empty per-user data folder on every platform, and nothing that
    # could point the installed package back at this checkout.
    home = tmp_path / "home"
    home.mkdir()
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in {"PYTHONPATH", "HEA_BENCH_BENCHMARK_DIR", "HEA_BENCH_MODEL_CACHE", "VIRTUAL_ENV"}
    }
    env.update(LOCALAPPDATA=str(home), XDG_DATA_HOME=str(home), HOME=str(home), PYTHONIOENCODING="utf-8")
    script = shutil.copy(ROOT / "tests" / "package_smoke.py", tmp_path / "package_smoke.py")
    arguments = [str(python), str(script), str(tmp_path / "work")]
    if PEIVASTE.exists():
        arguments.append(str(PEIVASTE))
    done = subprocess.run(
        arguments, cwd=tmp_path, env=env, capture_output=True, text=True, encoding="utf-8", timeout=1800
    )
    assert done.returncode == 0 and "PACKAGE SMOKE OK" in done.stdout, (
        f"the installed package failed:\n{done.stdout[-4000:]}\n{done.stderr[-4000:]}"
    )
