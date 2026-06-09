# examples/

Worked examples of the `hea-bench` API. The notebook renders inline on
GitHub with its embedded outputs, so you can read it without running
anything; or open it in Jupyter / VS Code to execute and edit.

| Notebook | What it shows |
|---|---|
| [`01_cantor_walkthrough.ipynb`](./01_cantor_walkthrough.ipynb) | Every descriptor and every rule applied to the canonical CoCrFeMnNi alloy; the formula-parsing surface; what happens to Guo–Liu VEC predictions as Al content rises in Al<sub>x</sub>CoCrFeNi. |

## How these notebooks are built

Each `.ipynb` is generated from a paired `.py` source-of-truth file
using a small builder script:

```
examples/01_cantor_walkthrough.py     # paired source
examples/01_cantor_walkthrough.ipynb  # rendered for GitHub display
examples/_build_notebooks.py           # builder
```

The `.py` files use the "percent" cell-marker convention
(`# %% [markdown]` for prose cells, `# %%` for code cells). The
builder executes each code cell in a fresh Python process, captures
its stdout, and embeds it as the cell's output. **This means every
number shown in the rendered notebooks comes from a real run, not a
copy-paste of expected values.**

After modifying any descriptor code or notebook source, rebuild:

```bash
PYTHONPATH=src python examples/_build_notebooks.py
```

Pairing in this style keeps git diffs readable (you review the `.py`
not the JSON `.ipynb`) and guarantees the embedded outputs match the
current code.

## Required to run them yourself

```bash
pip install -e .
```

No notebook-specific dependencies; everything in these examples uses
the standard `hea_bench` API.
