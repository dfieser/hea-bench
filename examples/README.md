# examples/

Worked examples of the `hea-bench` API. Both notebooks render
inline on GitHub with their embedded outputs, so you can read them
without running anything; or open them in Jupyter / VS Code to
execute and edit. Terms (descriptors, metrics, phase labels) are
defined in the repository [glossary](../GLOSSARY.md).

| Notebook | What it shows |
|---|---|
| [`01_cantor_walkthrough.ipynb`](./01_cantor_walkthrough.ipynb) | Every descriptor (the six v0.1.0 descriptors and the v1.1 phi-family) and every rule applied to the canonical CoCrFeMnNi alloy; the formula-parsing surface; what happens to Guo–Liu VEC predictions as Al content rises in Al<sub>x</sub>CoCrFeNi. |
| [`02_benchmark_evaluation.ipynb`](./02_benchmark_evaluation.ipynb) | Loads the consolidated v0.1.0 benchmark, runs all six rules, reproduces the headline scores, examines where the Zhang atomic-size-mismatch (δ) rule errs, and sweeps its cutoff to find the best-separating threshold on this dataset (δ < 2.6%, far tighter than the textbook 6.5%). It ends with the v1.1 intermetallic-aware sub-benchmark, where the Ye φ rule separates solid solutions from intermetallics far better than on the coarse benchmark (Youden's J ≈ +0.19) against Peivaste's fine-grained labels. |

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

After modifying any descriptor code, benchmark data, or notebook
source, rebuild:

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
