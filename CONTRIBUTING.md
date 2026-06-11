# Contributing to hea-bench

Contributions are welcome, whether bug reports, new descriptors or
rules, additional elemental data, UI work, or documentation
improvements.

## Reporting issues and seeking support

- **Bugs and feature requests:** open an issue on the GitHub issue
  tracker. For a bug, please include the `hea-bench` version, your
  Python version and operating system, a minimal composition or
  command that reproduces the problem, and the full traceback.
- **Questions and support:** open a GitHub issue with the
  `question` label, or email the maintainer at `dfieser9@gmail.com`.

## Development setup

```bash
git clone https://github.com/dfieser/hea-bench
cd hea-bench
pip install -e ".[dev]"
python -m pytest tests/ -q          # the parity test needs Node on PATH
```

The core package is dependency-free. The `dev` extra adds `pytest`,
`pytest-cov`, and `ruff`.

## Tests

Every numerical result reported in the documentation is pinned in the
test suite. When you change descriptor code or the vendored data, run
the suite and update the affected pinned values only after confirming
the new number by an independent measurement. The repository convention
is to measure first and assert second, never to write an expected value
from memory. The Python library and the JavaScript calculator core are
parity-locked by `tests/test_web_parity.py`; change both together.

When adding a new descriptor or rule, add tests that cover at least one
canonical reference case (the equiatomic Cantor alloy CoCrFeMnNi is the
standard sanity check) plus the error paths.

## Documentation and writing style

Write so a reader understands the document on the **first read**, in
place. This is a hard rule, not a preference — readability has been a
recurring problem.

Calibrate to the audience: **a reader of the target journal**
(SoftwareX). Terms such a reader would naturally already know (FCC, BCC,
HCP, alloy, phase, entropy, enthalpy, melting temperature, and the like)
need no explanation — do not over-explain them. Everything beyond that
shared background — above all **jargon specific to this project**: its
descriptors, named rules, and symbols (`δ`, `Ω`, `Φ`, …) — must be
minimized, especially early, and explained in plain context the first
time it appears.

- **Minimize jargon, especially at the start** of any document,
  section, abstract, or table. Lead with plain language; introduce a
  technical term only when it is actually needed.
- **Explain any necessary term inline, in plain language, with context,
  the first time it appears** — woven into the sentence. Do **not**
  defer to a glossary: a glossary just relocates the confusion, and
  readers do not jump to one mid-read.
- **State what a metric is measured against.** Never write a bare
  "sensitivity", "specificity", or "FCC sensitivity". Write, in context,
  "of the alloys that are truly single-phase, the fraction the rule
  labels single-phase", and always name the class — a metric with no
  reference class is meaningless.
- **No undefined shorthand** (`n_eval`, `sens`, `spec`, bare `δ`, `Ω`,
  `VEC`, `HEA`, `IM`, "Youden's J", …). Prefer plain words; use a symbol
  only after giving its plain name.
- **Figures** carry no titles and no bare symbols on axes — spell the
  quantity out (e.g. "mixing enthalpy (kJ/mol)", not `ΔH_mix`).

Before committing any prose or figure change, reread it cold as a
non-specialist: if a term would make them stop, rewrite the sentence to
explain it plainly in place, or drop the jargon.

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

When you add or change a parity-relevant descriptor or rule, mirror it
in `web/hea-calculator-core.js` and re-run `tests/test_web_parity.py`
(and `tests/test_web_oxides_parity.py` for the oxide module) so the
Python library and the calculator stay identical.

## Adding elemental coverage

To extend the element data table, add the element to
`src/hea_bench/descriptors/data/elemental.py` with a source comment for
each property (atomic radius, valence-electron count, melting point) and
add the matching entry to the JS core's table, then add a pinned test
for the new values.

## Pull requests

- Open PRs against the default branch.
- Keep the test suite green. New functionality needs new tests.
- Run `ruff` for linting before submitting.
- Describe what changed and why in the PR description.

## Code of conduct

Participation in this project is governed by the
[Code of Conduct](CODE_OF_CONDUCT.md).
