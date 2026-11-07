# examples/

Worked examples of the `hea-bench` API. Each notebook renders inline on
GitHub with its embedded outputs, so you can read it without running
anything. To execute and edit one, open it in Jupyter or VS Code.

| Notebook | What it shows |
|---|---|
| [`01_cantor_walkthrough.ipynb`](./01_cantor_walkthrough.ipynb) | Every descriptor and every rule applied to the canonical CoCrFeMnNi alloy, the formula-parsing surface, and what happens to Guo–Liu VEC predictions as Al content rises in Al<sub>x</sub>CoCrFeNi. |
| [`02_oxides_walkthrough.ipynb`](./02_oxides_walkthrough.ipynb) | The high-entropy-oxide module on its literature anchors: (MgCoNiCuZn)O rock salt, the Jiang 2018 perovskites and their tolerance factors, the Spiridigliozzi fluorite radius-dispersion rule (reproducing the published SDs), the pyrochlore radius-ratio window, and how to override the oxidation-state solver. |

## How these notebooks are built

Each `.ipynb` is generated from a paired `.py` source-of-truth file
using a small builder script:

```
examples/01_cantor_walkthrough.py     # paired source
examples/01_cantor_walkthrough.ipynb  # rendered for GitHub display
examples/_build_notebooks.py           # builder
```

The `.py` files use the Jupytext percent cell-marker convention
(`# %% [markdown]` for prose cells, `# %%` for code cells). The
builder executes each code cell in a fresh Python process, captures
its stdout, and embeds it as the cell's output. **Every number shown
in the rendered notebooks therefore comes from a real run, not a
copy-paste of expected values.**

After modifying any descriptor code or notebook source, rebuild:

```bash
PYTHONPATH=src python examples/_build_notebooks.py
```

Pairing in this style keeps git diffs readable (you review the `.py`,
not the JSON `.ipynb`) and guarantees the embedded outputs match the
current code.

## Required to run them yourself

```bash
pip install -e .
```

The examples need no notebook-specific dependencies. Everything in them
uses the standard `hea_bench` API.
