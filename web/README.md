# web/ — self-contained browser calculator

The browser surface of `hea-bench`. It runs entirely client-side. No
server, no install, no Python runtime in the browser.

This same folder is also the frontend bundled into the native desktop
app (`src-tauri/`), so the browser page and the desktop `.exe` are the
identical calculator. It is likewise what GitHub Pages deploys, so the
folder is the site root of <https://dfieser.github.io/hea-bench/>.

## How to use it

Three equivalent paths:

- **Online:** open <https://dfieser.github.io/hea-bench/>. It opens on
  the landing page; press **Open the calculator** to start.
- **Offline / from a local copy:** double-click `index.html`. It opens
  in your browser and runs immediately. Everything it needs is in this
  folder.
- **Desktop app:** build the Tauri wrapper in `../src-tauri/` for a
  single offline executable (see the repo `README.md`).

## What it does

For any composition you enter, the calculator reports:

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
  assignment, Shannon radii (94 elements), per-sublattice entropy and
  size-disorder descriptors, the perovskite tolerance factors (t, μ,
  Bartel τ), the fluorite radius-dispersion rule, the pyrochlore
  radius-ratio window, and literature example presets. The oxide math
  is parity-tested against the Python library
  (`tests/test_web_oxides_parity.py`).

The calculator also ships its own documentation: a **Theory** view that
derives every alloy and oxide formula with citations, a grouped,
filterable **Equations** reference, and a grouped **References**
bibliography. Deep links open a view directly:
`index.html#theory`, `#equations`, `#refs`, or any theory section
id such as `index.html#sec-perovskite`.

## What's here

- `index.html` — the whole front end in one file: a short landing page
  (hero, the four surfaces, citation) plus the calculator itself
  (title-bar tabs, the two-pane workspace, the Theory/Equations/References
  views, the Miedema decomposition). The landing shows first; **Open the
  calculator** or any deep link such as `#theory` switches to the app via
  the URL hash. This single file is what the hosted site serves and what
  the desktop app loads.
- `hea-calculator-core.js` — the shared calculation core for the
  parity-critical descriptor and rule outputs. `Hmix` / `Omega` are
  computed from the single vendored pair-enthalpy table, identical to
  `hea_bench.mixing_enthalpy` / `hea_bench.omega` in the Python library.
  The alloy and oxide data tables inside it are GENERATED from the
  Python library by `tests/data/_sync_js_tables.py` and
  `tests/data/_sync_js_oxide_tables.py`; never hand-edit those blocks.
- `mathjax/` — bundled MathJax build for math notation rendering.
  Vendored so the page works fully offline.
- `.nojekyll` — marks the directory so GitHub Pages serves files as-is.

## Element coverage

The calculator covers the same 37 elements as the Python library's
`ELEMENTAL_DATA` table: Ag, Al, Au, Be, Ca, Ce, Co, Cr, Cu, Fe, Gd, Hf,
In, Ir, La, Li, Mg, Mn, Mo, Nb, Ni, Os, Pd, Pt, Re, Rh, Ru, Sc, Si, Sn,
Ta, Ti, V, W, Y, Zn, Zr. Compositions containing any element outside
this set surface a warning in the page rather than producing a number.
The Miedema formation-enthalpy decompositions also cover all 37
elements, using parameters from the repo's vendored matminer Miedema
table. The oxide mode draws on a 94-element Shannon ionic-radius table
vendored from pymatgen. Custom user-defined elements compute every core
descriptor and rule; electronegativity and decomposition outputs
degrade with a warning when their parameters are not supplied.

## Updating the calculator

For parity-critical descriptor or rule changes, update
`hea-calculator-core.js` and then run the parity regressions in
`tests/test_web_parity.py` (alloys, 666 pairs plus multi-element
fixtures) and `tests/test_web_oxides_parity.py` (oxides, including
exact warning strings). Both execute the shared JS core under Node and
compare against the matching Python APIs.

For page-only UI work, edit `index.html`. The calculator stays fully
offline, and the numerical drift risk is guarded by the automated
Python-vs-JS parity tests.
