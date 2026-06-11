# oxides/data — vendored oxide element table

| File | Origin | License | Loader |
|---|---|---|---|
| `oxide_elements.json` | Extracted from [pymatgen](https://github.com/materialsproject/pymatgen)'s compiled `periodic_table.json.gz` (pymatgen 2025.10.7) by `tests/data/_vendor_oxide_data.py` | MIT (pymatgen) | `_data.py` |
| `LICENSE.pymatgen.txt` | pymatgen's full MIT license | — | — |

## What's in `oxide_elements.json`

For each of the 94 elements that have Shannon-radius entries
(pymatgen's deuterium pseudo-element entry is excluded, since it is an
isotope rather than an element):

- `shannon_radii` — the Shannon (1976) **effective ionic radii** in
  angstroms (the `ionic_radius` field, on the r(O²⁻, VI) = 1.40 Å
  scale; the crystal-radius variant is not vendored), nested as
  oxidation state → coordination number (roman numeral) → spin state
  (`""` / `"High Spin"` / `"Low Spin"`).
- `common_oxidation_states` and `icsd_oxidation_states` — the
  candidate lists used by the charge-neutrality solver.
- `chi` — Pauling electronegativity.

One upstream data quirk is corrected at extraction: pymatgen's Eu entry
contains a malformed empty-string oxidation-state key, which is dropped.

### Primary source

> Shannon, R. D. (1976). Revised effective ionic radii and systematic
> studies of interatomic distances in halides and chalcogenides.
> *Acta Crystallographica* **A32**, 751–767.
> doi:10.1107/S0567739476001551

pymatgen digitized these tables; cite Shannon for the data and
optionally pymatgen for the digitization:

> Ong, S. P., et al. (2013). Python Materials Genomics (pymatgen): A
> robust, open-source python library for materials analysis.
> *Comput. Mater. Sci.* **68**, 314–319.

### Verification

`tests/data/_vendor_oxide_data.py` asserts eight hand-checked values
from the Shannon 1976 paper before writing anything (Mg²⁺ VI 0.72,
Sr²⁺ XII 1.44, Ti⁴⁺ VI 0.605, Zr⁴⁺ VIII 0.84, Ce⁴⁺ VIII 0.97,
Mn⁴⁺ VI 0.53, Co²⁺ VI HS 0.745, O²⁻ VI 1.40). Additionally, the
fluorite descriptor built on this table reproduces the published
radius standard deviations of Spiridigliozzi et al. 2023 (*Materials*
**16**, 2219) to all quoted digits (0.0976 / 0.117 / 0.128 Å), an
independent end-to-end check of the radius values and conventions.

## File integrity (SHA-256, captured 2026-06-10)

```
oxide_elements.json   af47dfe9a9c3586049a5070e0fc8bab918a8300377e42c4a35132bf72044569e
```

## Re-vendoring

Install/upgrade pymatgen, then from the repo root:

```bash
PYTHONPATH=src python tests/data/_vendor_oxide_data.py
```

The script is deterministic for a given pymatgen version; re-running
against the same version must be byte-identical. After re-vendoring
against a newer pymatgen, re-run the test suite and explain any pinned
value that moved.

## Attribution requirement

pymatgen is MIT-licensed; the license text is preserved at
[LICENSE.pymatgen.txt](LICENSE.pymatgen.txt) and must be retained
alongside any redistribution of this data file.
