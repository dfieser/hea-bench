# web/ — self-contained browser calculator

A single self-contained HTML page that computes the high-entropy
alloy phase descriptors and applies the canonical empirical rules
entirely client-side. No server, no install, no Python runtime in the
browser.

## How to use it

Two equivalent paths:

- **Online:** open <https://dfieser.github.io/hea-bench/>.
- **Offline / from a local copy:** double-click `index.html`. It opens
  in your browser and runs immediately. Everything it needs is in
  this folder.

## What it does

For any composition you enter, the page reports:

- **Descriptors** — mixing entropy ΔS_mix, atomic-size mismatch δ,
  mean melting temperature T_m, mixing enthalpy ΔH_mix,
  valence-electron concentration VEC, and the Yang-Zhang Ω parameter.
- **Phase-prediction rules** — for the same composition, the verdict
  of each of the four canonical empirical rules side by side
  (Yeh entropy, Zhang size-mismatch, Guo-Liu VEC, Yang-Zhang Ω). The
  rule logic mirrors the Python library exactly, including the
  six-decimal VEC rounding that handles the equiatomic-CrFeNi
  boundary case.
- **Miedema-model formation enthalpies** — compound enthalpy and the
  solid-solution and amorphous enthalpies decomposed into chemical,
  elastic, structural, and topological contributions.

## What's here

- `index.html` — the calculator. Contains the descriptor implementations,
  the rule-prediction logic, the elemental-property table, the Miedema
  pair-enthalpy table, and the UI all inlined.
- `mathjax/` — bundled MathJax build for math notation rendering.
  Vendored so the page works fully offline.
- `.nojekyll` — marks the directory so GitHub Pages serves files as-is.

## Updating the calculator

The HTML page is the source of truth. Edit `index.html` directly. The
Python library and the calculator are independent implementations.
This keeps the offline experience truly stand-alone at the cost of a
small risk of numerical drift between the two; the test suite pins
the Python numbers, and the calculator's results should be sanity-checked
against the Cantor alloy values listed in `../README.md` after any
non-cosmetic change.
