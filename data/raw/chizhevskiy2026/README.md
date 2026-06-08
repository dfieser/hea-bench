# chizhevskiy2026/ — LLM-extracted HEA database (Chizhevskiy et al. 2026)

> **The named-intermetallic dataset at scale.** 12,427 HEA records mined
> from 4,625 papers by an LLM pipeline. Unlike Peivaste (lumped "any-IM")
> and far larger than Borg, its `Phase` column distinguishes **named
> intermetallics** — `B2`, `L12`, `Laves`, `σ` — which is exactly what the
> intermetallic-**typing** result (ordered-vs-Laves held-out J ≈ 0.81 on
> Borg, n≈100) needs to be confirmed at scale. Acquired 2026-06-06.

## Source

- **Citation:** Chizhevskiy, V., Marković, G., Benrazzouq, S., Cvelbar, U.,
  Nominé, A., & Zavašnik, J. (2026). High Entropy Alloys Database generated
  with Large Language Model. *Scientific Data* **13**(1), 612.
- **DOI (paper):** [10.1038/s41597-026-06930-z](https://doi.org/10.1038/s41597-026-06930-z)
- **Data repository:** [github.com/Vladimirchizh/hea_database](https://github.com/Vladimirchizh/hea_database)
- **Acquired by hea-bench on:** 2026-06-06 (from the GitHub repo above)
- **Files & integrity:**
  - `database_of_HEAs.csv` — 3,528,107 bytes —
    SHA-256 `F310B439AEBE7D801A23BDA7231D89DD84D98630F06CEA8CB60A1BCA91BF0A22`
  - `database_of_raw_responses.csv` — 60,983,308 bytes —
    SHA-256 `ECDD92734F0CA3F5DEE23723EC906CC15E8B87A0E765C0EB45D73DFD60878CBB`

## License

*Scientific Data* mandates open licensing (CC-BY-4.0) for article-associated
datasets. **Not yet confirmed against a LICENSE file in the GitHub repo** —
verify before redistribution. Cite Chizhevskiy *et al.* (2026) when using.

## Files

- **`database_of_HEAs.csv`** — the structured DB, 12,428 lines (1 header +
  12,427 records). The working file.
- **`database_of_raw_responses.csv`** — 58 MB of raw per-paper LLM responses
  (prompts 1–5, PDF URLs). Kept for **provenance / spot-checking
  extractions** against sources. **Gitignore this when git is initialized**
  (large, derived).
- **`UPSTREAM_README.md`** — the dataset authors' own field documentation,
  preserved verbatim.

## Schema — `database_of_HEAs.csv` (11 columns)

| Column | Meaning |
|---|---|
| `id` | Unique row identifier |
| `Paper` / `Name` | Source-paper ID / filename — **provenance link for vetting** |
| `Alloy` | Composition (e.g., `AlCoCrFeNi`; equiatomic shorthand and subscripted forms both occur — parser must handle both) |
| `Nb of phase` | Integer phase count (1: 6827, 2: 3135, 3: 1631, 4+: 828) |
| `Phase` | **Free-text phase content with named IMs** — `FCC`, `BCC`, `BCC B2 + FCC L12`, `C14 Laves phase + FCC`, `BCC B2 (Intermetallic) + FCC`, … (also noisy tokens: `cubic`, `martensite`, `not specified`, `unknown`, `nan`) |
| `Experimental or theoretical` | Study type |
| `Experimental details` | Free text — **processing route lives here** (no clean column): cast 600, anneal 354, homogenize 385, quench 863 |
| `Theoretical details` | DFT/CALPHAD methods (if theoretical) |
| `Special conditions` | Free-text notes (e.g., "classified as High Entropy Intermetallic") |
| `Type of solution` | Coarse class: Single Solid Solution 5644 · Mixed 5695 · Intermetallic 827 · Amorphous 239 · High Entropy Intermetallic 20 |

### Verified named-IM granularity (substring row counts, n=12,427)

`B2` 1,149 · `L12` 464 · `Laves` 655 · `σ` 62 — vs Borg's ORD≈70 / LAV≈34.
This is the ~10× scale-up the typing analysis was data-limited on.

## Caveats (read before relying on it — verify-everything)

1. **LLM-extracted → extraction noise** on top of the inherent ~33%
   inter-study label noise. **Must be spot-checked**: sample rows, trace via
   `Paper` + `database_of_raw_responses.csv` to the source paper, confirm the
   phase call. Do this before any headline claim.
2. **`Phase` is messy free-text** — needs normalization into the project
   taxonomy (SS = {BCC,FCC,HCP} only; ORD = contains B2/L12; LAV = contains
   Laves; AM = amorphous; σ tracked separately). Hundreds of
   `not specified`/`unknown`/`nan`/`cubic` rows to exclude.
3. **No processing-route column** — must parse `Experimental details` to
   recover cast/annealed for the equilibrium re-test; noisier than Borg's
   tagged routes.
4. **`Alloy` formula parsing** — mixed equiatomic-shorthand and subscripted
   notations; reuse/extend `hea_bench.composition` and validate coverage.

## Downstream consolidation notes

- **Primary use:** scale the SS/ORD/LAV three-class boundary map
  (`analysis/stage4b_boundary_map.py`) from n≈100 to n≈1,000+ per IM family,
  and power the annealed re-test once routes are parsed.
- **Dedup key:** composition-level (`Alloy`); no clean (formula, processing)
  key as Borg has — keep parsed route as a side-channel.
- **Taxonomy mapping** mirrors `stage3c_borg_heldout.classify_detail`:
  reuse that logic, extend the token set for this DB's richer `Phase`
  vocabulary.
- Build a loader (`hea_bench/benchmark/loaders/chizhevskiy2026.py`) +
  tests, following the borg2020/peivaste loader pattern.
