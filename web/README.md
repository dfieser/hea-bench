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

## What's here

- `index.html` — the calculator. Contains the descriptor implementations,
  the elemental-property table, the Miedema pair-enthalpy table, and the
  UI all inlined.
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
