# paper/

SoftwareX submission draft for `hea-bench`.

## Files

- `main.tex` — the paper (Elsevier `elsarticle` class, `review` manuscript layout, 1-inch margins)
- `refs.bib` — bibliography (biblatex/biber, APA style)
- `figures/` — two figures plus the scripts that regenerate them from the committed CSV (`benchmark_overview.png` / `make_benchmark_figure.py`, `roc_zhang_delta.png` / `make_roc_figure.py`)
- `.gitignore` — LaTeX build artifacts

## Build

PDFLaTeX + biber. From this directory:

```bash
pdflatex main
biber    main
pdflatex main
pdflatex main
```

Or with `latexmk`:

```bash
latexmk -pdf -bibtex- -biber main
```

The bibliography uses `biblatex-apa` for APA-style reference
formatting with numeric in-text citations, which requires the
`biber` backend rather than the traditional `bibtex`. Both are
shipped with TeX Live and MiKTeX.

## What's in the draft (v0.1.0)

| Section | Content |
|---|---|
| Required Metadata | SoftwareX-required code-metadata table (version, license, repository link, languages, contact) |
| 1. Motivation and significance | The three gaps in the open HEA literature `hea-bench` addresses |
| 2. Software description | Architecture (six sub-packages); functionalities (numbered list); consolidated benchmark provenance |
| 3. Illustrative examples | Cantor alloy end-to-end; reference rule-baseline table; Zhang δ ROC recalibration (table + curve figure) |
| 4. Impact | Three classes of impact (calibration, substrate, accessibility) |
| 5. Conclusions | Summary + planned v0.2.0 work |
| Acknowledgements | matminer, Pyodide, source-dataset authors |
| References | 17 entries: Cantor 2004, Yeh 2004, Zhang 2008, Guo 2011, Yang 2012, Borg 2020, Pei 2020, Peivaste 2023, Miedema 1973/1980, de Boer 1988, Takeuchi 2005, Zhang 2016 MiedCalc, Senkov 2010, matminer (Ward 2018), MatBench (Dunn 2020), Wilson 1927, Youden 1950, Pyodide |

## Open items before submission

- [ ] Add a real Zenodo DOI to the metadata table once the first
  tagged release is minted.
- [ ] Confirm Cantor δ value pinned in tests (\SI{3.164}{\percent})
  matches the value shown in the example; spot-check before submit.
- [ ] Convert the rule-baseline and ROC tables to publication-grade
  formatting if reviewer asks (currently `booktabs`).
- [ ] Optional: add a single ROC-curve figure for the Zhang δ
  recalibration; the table conveys it, but a curve is clearer.
- [ ] Add author affiliation if shifted from independent.

## Honest caveats baked into the draft

- The "no published MatBench equivalent for HEA phase classification"
  claim is hedged with "to our knowledge" — we did a literature
  scan but cannot prove a negative.
- The Zhang δ recalibration to δ < 2.5% is described as a real
  finding *of this dataset* — the paper does not claim 2.5% is
  the universal correct threshold.
- The matminer Miedema pair table is described as deriving from
  de Boer 1988 and as consistent with the Takeuchi-Inoue 2005
  tabulation; we do not claim numerical identity with Takeuchi-
  Inoue at every pair, only that the four pairs we cross-checked
  by hand agreed.
- AI-assistance is disclosed in the Acknowledgements.

## SoftwareX vs JOSS

The `elsarticle` class targets SoftwareX. To re-target JOSS:
replace `\documentclass[5p,times]{elsarticle}` with their template
(plain `article` class with the OpenJournals header), drop the
metadata table (JOSS handles that out-of-band), and shorten the
paper substantially — JOSS prefers 250-1000-word summaries.

The body content (motivation, headline numbers, ROC finding,
impact) ports cleanly between both venues.
