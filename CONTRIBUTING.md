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
pip install -e ".[dev,data]"
python -m pytest tests/ -q
```

The core package is dependency-free. The `dev` extra adds `pytest`,
`pytest-cov`, and `ruff`. The `data` extra adds `pandas` for tabular
work.

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
