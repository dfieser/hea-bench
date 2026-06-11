# web/ — self-contained browser calculator

A self-contained browser calculator for the `hea-bench` descriptors and
rules. It runs entirely client-side. No server, no install, no Python
runtime in the browser.

This same folder is also the frontend bundled into the native desktop
app (`src-tauri/`), so the browser page and the desktop `.exe` are the
identical calculator.

## How to use it

Three equivalent paths:

- **Online:** open <https://dfieser.github.io/hea-bench/>.
- **Offline / from a local copy:** double-click `index.html`. It opens
  in your browser and runs immediately. Everything it needs is in
  this folder.
- **Desktop app:** build the Tauri wrapper in `../src-tauri/` for a
  single offline executable (see the repo `PROJECT_PLAN.md`).

## What it does

For any composition you enter, the page reports:

- **Core descriptors** — mixing entropy ΔS_mix, atomic-size mismatch δ,
  mean melting temperature T_m, mixing enthalpy ΔH_mix,
  valence-electron concentration VEC, Yang-Zhang Ω, Pauling
  electronegativity mismatch Δχ, Mansoori excess entropy `S_E`,
  `DeltaG_ss`, `DeltaG_max`, King `Phi`, and Ye `phi`.
- **Phase-prediction rules** — the verdicts of all six shipped rules:
  Yeh entropy, Zhang size mismatch, Guo-Liu VEC, Yang-Zhang Ω,
  King `Phi`, and Ye `phi`.
- **King-temperature override** — leave it blank to use `T = T_m`, or
  enter an explicit temperature in kelvin for the King `Phi` path.
- **Miedema-model formation enthalpies** — compound enthalpy and the
  solid-solution and amorphous enthalpies decomposed into chemical,
  elastic, structural, and topological contributions.
- **Oxides mode** — a mode switch at the top of the input rail flips the
  calculator to high-entropy oxides: rock salt, perovskite, fluorite,
  and pyrochlore families with automatic charge-balance oxidation-state
  assignment, Shannon radii (95 elements), per-sublattice entropy and
  size-disorder descriptors, the perovskite tolerance factors (t, μ,
  Bartel τ), the fluorite radius-dispersion rule, the pyrochlore
  radius-ratio window, and literature example presets. The oxide math
  is parity-tested against the Python library
  (`tests/test_web_oxides_parity.py`).

## What's here

- `index.html` — the desktop-style calculator UI (title-bar tabs,
  two-pane workspace, Theory/Equations/References views) plus the
  page-side Miedema formation-enthalpy decomposition logic.
- `hea-calculator-core.js` — the shared calculation core for the
  parity-critical descriptor and rule outputs. `Hmix` / `Omega` are
  computed from the single vendored pair-enthalpy table, identical to
  `hea_bench.mixing_enthalpy` / `hea_bench.omega` in the Python library.
- `mathjax/` — bundled MathJax build for math notation rendering.
  Vendored so the page works fully offline.
- `.nojekyll` — marks the directory so GitHub Pages serves files as-is.

## Element coverage

The calculator covers the same 37 elements as the Python library's
`ELEMENTAL_DATA` table: Ag, Al, Au, Be, Ca, Ce, Co, Cr, Cu, Fe, Gd, Hf,
In, Ir, La, Li, Mg, Mn, Mo, Nb, Ni, Os, Pd, Pt, Re, Rh, Ru, Sc, Si, Sn,
Ta, Ti, V, W, Y, Zn, Zr. Compositions containing any element outside
this set surface a warning in the page rather than producing a number.
The JS tables are generated from the Python library by
`tests/data/_sync_js_tables.py`, so the two cannot drift. The Miedema
formation-enthalpy decompositions also cover all 37 elements, using
parameters from the repo's vendored matminer Miedema table. Custom
user-defined elements compute every core descriptor and rule;
electronegativity and decomposition outputs degrade with a warning
when their parameters are not supplied.

## Updating the calculator

For parity-critical descriptor or rule changes, update `hea-calculator-core.js`
and then run the browser parity regression in `tests/test_web_parity.py`.
That test executes the shared JS core under Node and compares the browser-side
results against the matching Python APIs on every binary pair (666 cases) and
the curated multi-element fixtures.

For page-only UI work, edit `index.html`. The calculator stays fully offline,
but the numerical drift risk is now guarded by the automated Python-vs-JS
parity test rather than by manual sanity checks alone.
