# couzinie2018/ — refractory HEA / RCCA mechanical property database

> **Per-source documentation.** Acquisition attempted 2026-05-20 but
> data not yet available in machine-readable form. **Deprioritized** —
> see "Why we're not chasing this further right now" below.

## Source

- **Citation:** Couzinié, J.-P., Senkov, O. N., Miracle, D. B., & Dirras, G.
  (2018). Comprehensive data compilation on the mechanical properties of
  refractory high-entropy alloys. *Data in Brief* **21**, 1622–1641.
- **DOI:** [10.1016/j.dib.2018.10.071](https://doi.org/10.1016/j.dib.2018.10.071)
- **PMC mirror (open access):** [PMC6247412](https://pmc.ncbi.nlm.nih.gov/articles/PMC6247412/)
- **License:** CC-BY-4.0 (Data in Brief open-access policy). Would be
  mirror-eligible under our hybrid policy *if* we had a clean
  machine-readable file.

## Scope

- 122 refractory HEAs / refractory complex concentrated alloys (RCCAs)
- 340 individual mechanical tests
- Period covered: 2010 – January 2018
- Columns (per the published article): alloy composition (elements,
  atomic fractions), metallurgical state (as-cast, annealed, etc.), phase
  content, mechanical test type, testing temperature, experimental Young
  modulus, yield strength, calculated density.

## Acquisition attempt log (2026-05-20)

Probed Elsevier's CDN for the article's supplementary files. Both slots
were hit:

| URL | Size | What's there |
|---|---|---|
| `ars.els-cdn.com/…S2352340918312800-mmc1.pdf` | 654 KB | **Mis-attributed.** Conflict-of-interest disclosure forms for a *different* Data in Brief article (DIB-D-18-02265, Wiese & Caven, on Green Ash riparian woodlands along the central Platte River). Not Couzinié's data. |
| `ars.els-cdn.com/…S2352340918312800-mmc2.csv` | 2 KB | **Mis-attributed.** Tree-borer field data (LotID, latitude, DBH, age, …) from the same Green Ash paper. Not Couzinié's data. |

This appears to be an actual file-routing bug on Elsevier's CDN — both
supplementary slots for Couzinié's PII (`S2352340918312800`) serve content
from manuscript `DIB-D-18-02265`. The real Couzinié data lives in **Table
1 of the published article body**, not as a separate downloadable file.

## Why we're not chasing this further right now

- **Subsumption by Borg 2020.** Borg, Frey, Moy, Pollock & Gorsse (2020)
  explicitly built their MPEA dataset on top of earlier compilations
  including Couzinié 2018. The 122 refractory alloys in Couzinié are
  almost certainly already in Borg's 630, with the same primary-literature
  citations. Marginal data gain from Couzinié as a *separate* source is
  small.
- **Acquisition cost.** Pulling the data would require either (a) OCR'ing
  Table 1 from the article PDF and verifying every entry, or (b) waiting
  for Elsevier to fix the CDN file mapping. Neither is a good use of
  Phase 1 time.

## What Couzinié still adds (for a later pass)

- **Cross-verification.** Same composition in two sources with consistent
  phase labels is a quality signal; conflicts flag re-examination.
- **Provenance back to 2010–2018 primary literature** that Borg may have
  abridged.

These are worth pulling in eventually, but not on the Phase 1 critical
path. Revisit after the Phase 1 baseline benchmark is shipped.
