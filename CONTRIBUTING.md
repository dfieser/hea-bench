# Contributing to hea-bench

Contributions are welcome, whether bug reports, new datasets, new
descriptors or rules, additional elemental data, or documentation
improvements.

## Reporting issues and seeking support

- **Bugs and feature requests:** open an issue on the GitHub issue
  tracker. For a bug, please include the `hea-bench` version, your
  Python version and operating system, a minimal composition or
  command that reproduces the problem, and the full traceback.
- **Questions and support:** open a GitHub issue with the
  `question` label, or email the maintainer at `davjfies@gmail.com`.

## Development setup

```bash
git clone https://github.com/dfieser/hea-bench
cd hea-bench
pip install -e ".[dev,data,ml]"
python -m pytest tests/ -q
```

The core package is dependency-free. The `dev` extra adds `pytest`,
`pytest-cov`, and `ruff`. The `data` extra adds `pandas` for tabular
work. The `ml` extra adds `numpy` for the learned baseline
(`hea_bench.baselines`).

## Tests

Every numerical result reported in the documentation and in the
paper is pinned in the test suite. When you change descriptor code,
the consolidator, or the vendored data, run the suite and update the
affected pinned values only after confirming the new number by an
independent measurement. The repository convention is to measure
first and assert second, never to write an expected value from
memory.

When adding a new descriptor, rule, or loader, add tests that cover
at least one canonical reference case (the equiatomic Cantor alloy
CoCrFeMnNi is the standard sanity check) plus the error paths.

## Documentation and writing style

A reader must be able to understand any document without already
knowing the jargon. **Define every term, symbol, abbreviation, and
metric at its first use in a document, or link to
[GLOSSARY.md](./GLOSSARY.md).** This applies to every README, the
docs, code comments, and the manuscript. (This is enforced because it
has been a recurring problem; treat it as a hard rule, not a
preference.)

Specifically:

- **State what a metric is measured against.** Never write a bare
  "sensitivity", "specificity", or "FCC sensitivity". Write "of truly
  single-phase alloys, the fraction the rule labels single-phase", and
  always name the class — a metric with no reference class is
  meaningless.
- **No undefined shorthand.** Do not introduce `n_eval`, `sens`,
  `spec`, `δ`, `Ω`, `VEC`, `HEA`, `IM`, `AM`, "Youden's J", etc.
  without defining it on first use or linking the glossary.
- **Plain words first.** Prefer "atomic size mismatch" to a bare `δ`;
  if a symbol or abbreviation is genuinely needed, define it once and
  use it consistently.
- **Figures** carry no titles and no bare symbols on axes — spell the
  quantity out (e.g. "mixing enthalpy (kJ/mol)", not `ΔH_mix`).
- **Keep the glossary in sync.** If you introduce a term anywhere, add
  its definition to `GLOSSARY.md`.

Before committing any prose or figure change, reread it as a newcomer:
if a term would make them stop and search, define it or link the
glossary.

## Adding a rule or descriptor

The descriptor layer lives under `src/hea_bench/descriptors/`. Each
descriptor is a pure function that takes a composition dict and
returns a float, with units documented in the docstring. Add new
descriptors as a sibling module of the existing six (`entropy.py`,
`size.py`, `vec.py`, `melting.py`, `miedema.py`, `omega.py`) and the
v1.1 phi-family (`phi.py`).

The rules layer lives under `src/hea_bench/rules/`. Each rule is a
module exposing `DESCRIPTION`, `DEFAULT_THRESHOLD` (where
applicable), and `predict(composition, ...)`. New rules should follow
the existing module-functional pattern shown by `yang_omega.py`,
`king_phi.py`, and `ye_phi.py`.

If a new rule needs a held-out evaluation, add a rule-specific
helper to `src/hea_bench/evaluation/holdout.py` alongside the
existing `evaluate_*_holdout` functions. The generic
`evaluate_binary_kfold` primitive accepts arbitrary predict / observe
callables, so a wrapper is typically all that is required.

## Adding a dataset

Per-source data lives under `data/raw/<source>/` with a README that
records the citation, the license, the acquisition date, and a
SHA-256 of the file. Datasets under permissive licenses (CC-BY, CC0,
MIT, Apache, BSD) are mirrored directly. Datasets without a
redistributable license are pointer-only: commit a `fetch.py` that
downloads the file on request, and add the file pattern to
`.gitignore`. See `data/raw/README.md` for the policy.

## Adding elemental coverage

To extend the elemental data table, add the element to the table in
`src/hea_bench/descriptors/data/elemental.py` with a source comment
for each property, then run the coverage analysis to confirm the
benchmark coverage improved as expected.

## Pull requests

- Open PRs against the default branch.
- Keep the test suite green. New functionality needs new tests.
- Run `ruff` for linting before submitting.
- Describe what changed and why in the PR description.

## Code of conduct

Participation in this project is governed by the
[Code of Conduct](CODE_OF_CONDUCT.md).
