# hea-bench

> **Status: pre-alpha (Phase 0 skeleton, 2026-05-20).** Not yet usable.
> See [`../PROJECT_PLAN.md`](../PROJECT_PLAN.md) for the roadmap.

An open benchmark suite and reference baselines for **high-entropy alloy (HEA)
phase prediction**. Inspired by [MatBench](https://matbench.materialsproject.org)
for materials property prediction.

## What this is

A standardized, reproducible benchmark that fills two gaps in the current HEA
phase-prediction literature:

1. **No common benchmark dataset.** Every ML paper compiles its own dataset
   from scattered literature sources, with different preprocessing and
   metrics. Head-to-head comparison across methods is currently impossible.
2. **No published implementation of the canonical empirical rules as proper
   diagnostic classifiers.** Existing ROC-AUC work is on ML model outputs;
   the δ < 6.5%, VEC, and Ω > 1.1 rules have never been characterized with
   sensitivity / specificity / Wilson CIs / threshold sweeps on a common
   reference dataset.

`hea-bench` provides:

- A curated, deduplicated, versioned **consolidated dataset** combining
  published open HEA phase-label databases, with cite-back to every alloy's
  original source.
- **Reference baseline implementations** of the canonical empirical
  descriptors (ΔS_mix, δ, VEC, Ω) and phase-prediction rules, treated as
  proper diagnostic classifiers.
- A **standardized evaluation harness** so any user-supplied model can be
  scored against the same dataset and metrics.
- A **CLI and Python API** for both interactive use and programmatic
  evaluation.

## What this is not

- Not a browser tool. Pure Python library + CLI.
- Not a new ML model — `hea-bench` provides *baselines*; ML contributions are
  the user's to add.
- Not a CALPHAD substitute — empirical descriptors only.

## Installation (once Phase 1 is done)

```bash
pip install hea-bench
```

For development:
```bash
git clone https://github.com/USERNAME/hea-bench
cd hea-bench
pip install -e ".[dev,data]"
```

## License

[MIT License](LICENSE). The bundled experimental datasets retain their
original licenses; see [`data/raw/README.md`](data/raw/README.md) for
per-dataset attribution (will exist after Phase 1).

## Citation

If you use `hea-bench`, please cite it via the metadata in
[`CITATION.cff`](CITATION.cff). A DOI will be minted through Zenodo on the
first tagged release.

## Acknowledgements

Development was assisted by large language models (Claude) for code scaffolding
and prose drafting. All numerical parameters, formulas, and threshold values
are taken from the primary literature cited in the source. The author verified
all outputs against the cited sources.

This work draws on data from Borg *et al.* (2020) *Sci. Data* **7**, 430
(CC-BY-4.0), among other open sources. Full per-dataset attribution lives in
[`data/raw/`](data/raw/) once the consolidated benchmark is built.

## Status of Phase 0

The current commit is the empty package skeleton — directory layout, build
metadata, and a single smoke test that verifies the package imports. **No
descriptor code, no rules, no dataset loaders yet.** Phase 1 (dataset
consolidation) and Phase 2 (porting the validator from
`../thermo-descriptor-calculator/`) come next.
