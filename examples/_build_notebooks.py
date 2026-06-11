"""Build the example .ipynb files from the source-of-truth .py scripts.

The pairing is:

  examples/01_cantor_walkthrough.py        -> 01_cantor_walkthrough.ipynb

Each source script is divided into cells by  ``# %% [markdown]`` and
``# %%`` markers (Jupytext "percent" style). This builder runs each
code cell in a single fresh Python process, captures its stdout, and
writes a clean .ipynb with embedded outputs so the notebooks render
correctly on GitHub without users needing to execute them first.

Run from the repo root::

    PYTHONPATH=src python examples/_build_notebooks.py
"""

from __future__ import annotations

import contextlib
import io
import json
import pathlib
import re
import sys
import traceback

HERE = pathlib.Path(__file__).resolve().parent
SOURCES = ["01_cantor_walkthrough.py", "02_oxides_walkthrough.py"]


def parse_cells(text: str) -> list[tuple[str, str]]:
    """Split a percent-format script into (cell_type, source) tuples."""
    cells: list[tuple[str, str]] = []
    current_type: str | None = None
    current_lines: list[str] = []
    for line in text.splitlines():
        m = re.match(r"#\s*%%\s*(\[markdown\])?\s*$", line)
        if m:
            if current_type is not None:
                cells.append((current_type, "\n".join(current_lines).strip("\n")))
            current_type = "markdown" if m.group(1) else "code"
            current_lines = []
            continue
        current_lines.append(line)
    if current_type is not None:
        cells.append((current_type, "\n".join(current_lines).strip("\n")))
    # Strip leading shebang/encoding from the first cell if it was an
    # implicit (non-marker-headed) prelude — discard if empty.
    return [(t, src) for (t, src) in cells if src.strip()]


def strip_markdown_comments(md_src: str) -> str:
    """Markdown cells are written as Python comments (``# ...``). Strip
    the leading ``# `` from each line for the rendered notebook."""
    out: list[str] = []
    for line in md_src.splitlines():
        if line.startswith("# "):
            out.append(line[2:])
        elif line.startswith("#"):
            out.append(line[1:])
        else:
            out.append(line)
    return "\n".join(out)


def run_code_cell(code: str, ns: dict) -> str:
    """Run ``code`` in namespace ``ns`` and return captured stdout."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            exec(compile(code, "<cell>", "exec"), ns)
    except Exception:
        traceback.print_exc(file=buf)
    return buf.getvalue()


def build_ipynb(cells: list[tuple[str, str]]) -> dict:
    """Execute code cells in order, capture outputs, return nbformat dict."""
    ns: dict = {"__name__": "__main__"}
    out_cells: list[dict] = []
    code_count = 0
    for cell_type, src in cells:
        if cell_type == "markdown":
            out_cells.append({
                "cell_type": "markdown",
                "metadata": {},
                "source": _split_lines(strip_markdown_comments(src)),
            })
        else:
            code_count += 1
            stdout = run_code_cell(src, ns)
            outputs: list[dict] = []
            if stdout:
                outputs.append({
                    "output_type": "stream",
                    "name": "stdout",
                    "text": _split_lines(stdout.rstrip("\n")),
                })
            out_cells.append({
                "cell_type": "code",
                "execution_count": code_count,
                "metadata": {},
                "outputs": outputs,
                "source": _split_lines(src),
            })
    return {
        "cells": out_cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _split_lines(text: str) -> list[str]:
    """nbformat wants each line as its own string with the trailing
    newline, except for the last line."""
    if not text:
        return []
    lines = text.split("\n")
    return [ln + "\n" for ln in lines[:-1]] + [lines[-1]]


def main() -> int:
    for src_name in SOURCES:
        src_path = HERE / src_name
        if not src_path.exists():
            print(f"skip: {src_path} does not exist")
            continue
        cells = parse_cells(src_path.read_text(encoding="utf-8"))
        nb = build_ipynb(cells)
        out_path = src_path.with_suffix(".ipynb")
        out_path.write_text(json.dumps(nb, indent=1), encoding="utf-8")
        n_code = sum(1 for c in nb["cells"] if c["cell_type"] == "code")
        n_md = sum(1 for c in nb["cells"] if c["cell_type"] == "markdown")
        print(f"built {out_path.name}: {n_md} markdown + {n_code} code cells")
    return 0


if __name__ == "__main__":
    sys.exit(main())
