# web/ — self-contained browser calculator

A self-contained browser calculator for the `hea-bench` descriptors and
rules. It runs entirely client-side. No server, no install, no Python
runtime in the browser. Descriptor symbols and terms used below are
defined in the repository [glossary](../GLOSSARY.md).

## How to use it

Two equivalent paths:

- **Online:** open <https://dfieser.github.io/hea-bench/>.
- **Offline / from a local copy:** double-click `index.html`. It opens
  in your browser and runs immediately. Everything it needs is in
  this folder.

## What it does

For any composition you enter, the page reports:

- **Core descriptors** — mixing entropy ΔS_mix, atomic-size mismatch δ,
  mean melting temperature T_m, mixing enthalpy ΔH_mix,
  valence-electron concentration VEC, Yang-Zhang Ω, Mansoori excess
  entropy `S_E`, `DeltaG_ss`, `DeltaG_max`, King `Phi`, and Ye `phi`.
- **Phase-prediction rules** — the verdicts of all six shipped rules:
  Yeh entropy, Zhang size mismatch, Guo-Liu VEC, Yang-Zhang Ω,
  King `Phi`, and Ye `phi`.
- **King-temperature override** — leave it blank to use `T = T_m`, or
  enter an explicit temperature in kelvin for the King `Phi` path.
- **Miedema-model formation enthalpies** — compound enthalpy and the
  solid-solution and amorphous enthalpies decomposed into chemical,
  elastic, structural, and topological contributions.

## What's here

- `index.html` — the calculator UI, the extended Miedema panel, and the
  page-specific fallback logic.
- `hea-calculator-core.js` — shared browser-side calculation core for the
  parity-critical descriptor and rule outputs. It also exports the
  browser-compatible Miedema chemical-term helper used for the page's
  displayed `Hmix` / `Omega` path.
- `mathjax/` — bundled MathJax build for math notation rendering.
  Vendored so the page works fully offline.
- `.nojekyll` — marks the directory so GitHub Pages serves files as-is.

## Updating the calculator

For parity-critical descriptor or rule changes, update `hea-calculator-core.js`
and then run the browser parity regression in `tests/test_web_parity.py`.
That test executes the shared JS core under Node and compares the browser-side
results against the matching Python APIs on canonical alloys, including the
calculator-specific `Hmix` / `Omega` path.

For page-only UI work, edit `index.html`. The calculator stays fully offline,
but the numerical drift risk is now guarded by the automated Python-vs-JS
parity test rather than by manual sanity checks alone.
