# High-entropy ceramics: what ships, what is deferred, and why

Written 2026-08-12 alongside the first `hea_bench.ceramics` release.
This is the ceramics counterpart of a corpus card: it records what the
module computes, which literature backs it, what was deliberately not
built yet, and the license status of every candidate dataset audited
for a future ceramics corpus.

## What ships

Three `describe_*` calls following the oxides module's shape:
`describe_rock_salt_carbide(metals)`, `describe_rock_salt_nitride(metals)`,
and `describe_diboride(metals)`, each returning one dict of normalized
metal sublattice, descriptors, annotated literature reference points,
warnings, and citations.

**Metal-sublattice configurational entropy.** The high-entropy-ceramics
convention (Oses, Toher and Curtarolo, Nat. Rev. Mater. 5, 295 (2020);
Wright and Luo, J. Mater. Sci. 55, 9812 (2020)): disorder lives on the
cation sublattice, the anion sublattice is ordered and contributes
nothing. Published papers switch between per-formula-unit,
per-mole-cation, and per-mole-atom normalizations without warning,
which is exactly why Dippo and Vecchio built a sublattice-resolved
metric (Scr. Mater. 201, 113974 (2021)); an equimolar five-metal
carbide is 1.61 R per mole of cations but 0.80 R per mole of atoms,
and a five-metal diboride 0.54 R per mole of atoms. Every report
therefore carries all conventions, labelled.

**VEC with reference points, not a verdict.** VEC per formula unit is
the composition-weighted metal group count plus the anion's electrons
(4 for C, 5 for N). The rock-salt mechanical-behavior literature marks
reference points rather than one window: a hardness maximum near 8.4
(Jhi, Ihm, Louie and Cohen, Nature 399, 132 (1999)), enhanced fracture
resistance above about 9.4 in five-metal carbides (Sangiovanni,
Kaufmann and Vecchio, Sci. Adv. 9, eadi2960 (2023)), a plasticity
criterion above about 9.5 (Sangiovanni et al., Mater. Des. 209, 109932
(2021)), against binary-systematics trends (Balasubramanian, Khare and
Gall, Acta Mater. 152, 175 (2018)). Because that span is a composite
of separate results, the module annotates the points and refuses to
compress them into a single-word verdict. VEC is not reported for
diborides, where the rock-salt reference points do not transfer.

## What is deferred, with reasons

**Size mismatch.** The carbide formability literature does not use
radius tables: Kretschmer and Mayrhofer (Sci. Rep. 14, 7210 (2024))
build their sigma descriptor from metal-carbon bond lengths of binary
rock-salt cells computed by DFT, explicitly rejecting tabulated radii,
and the diboride literature (Gild et al., Sci. Rep. 6, 37946 (2016))
uses binary MB2 lattice parameters cited through to Zhou et al. 2015.
Adopting a composition-only mismatch descriptor therefore requires
curating a per-row-cited table of binary lattice constants, including
decisions about metastable rock-salt MoC, WC, and CrC that have no
experimental stoichiometric lattice constant. That is real data work
with contestable choices, and rushing it would produce exactly the
kind of quietly sourced table this package refuses to carry. Until
that pass happens, the reports say so in their notes instead of
shipping a mismatch number.

**Entropy-forming ability and DEED.** EFA (Sarker et al., Nat. Commun.
9, 4980 (2018)) is the inverse spread of a DFT energy ensemble; DEED
(Divilov et al., Nature 625, 66 (2024), validated against 952 computed
ceramics) additionally needs convex-hull distances. Neither is
computable from composition, no parity is claimed anywhere in this
package, and the best published composition-only correlate of EFA
explains about R squared 0.58 with a threshold its own authors hedge
(Kretschmer and Mayrhofer 2024). What a composition-only package can
honestly do later is tabulate published EFA and DEED values as
reference labels, which the CC-BY sources below permit.

**A ceramics corpus and benchmark task.** Not built: the available
outcome data is small and fragmented (tens to low hundreds of rows per
class, thinner still for nitrides, where the main bulk dataset holds
eleven samples), and a benchmark task on a dataset that size would
overfit its own noise. The license audit below is the groundwork for a
future consolidation under the same provenance discipline as the alloy
corpus.

## Dataset license audit (verified 2026-08-12)

| candidate | contents | license status |
|---|---|---|
| Sarker et al. 2018, Table 1 (Nat. Commun. 9, 4980) | 56 five-metal rock-salt carbides with EFA; 9 synthesized outcomes | CC-BY-4.0 (table in article body) |
| Divilov et al. 2024, SI Tables 1-3 (Nature 625, 66) | DEED for 952 compositions; 17 syntheses | CC-BY-4.0 (article and SI) |
| Gild et al. 2016 (Sci. Rep. 6, 37946) | 7 five-metal diborides, 6 single-phase, with lattice mismatch values | CC-BY-4.0 |
| Dippo et al. 2020 (Sci. Rep. 10, 21288) | 11 bulk nitrides/carbonitrides with outcomes | CC-BY-4.0 |
| Zhang et al. 2026 (npj Comput. Mater. 12, 22) | 171 experimental carbide outcomes, largest compilation found | CC-BY (npj), data in article and SI |
| Meng et al. 2023 carbides (Cell Rep. Phys. Sci. 4, 101512) | 91 in-house syntheses with outcomes | CC-BY-NC-ND: readable, but NC and ND restrict redistribution |
| Meng et al. 2023 diborides (Acta Mater. 256, 119132) | 70 in-house syntheses | free to read, no open license |
| Harrington et al. 2019 (Acta Mater. 166, 271) | 12 carbides, 9 single-phase | subscription, no open license |
| Kaufmann et al. ML-EFA repository | training and prediction spreadsheets | repository has no license file (all rights reserved by default); the underlying 56 EFA values are CC-BY via Sarker Table 1 |
| AFLOW repository entries | POCC ensembles behind EFA/DEED | free for non-commercial scientific use only; the non-commercial clause conflicts with redistribution inside an MIT package |

The CC-BY rows are sufficient raw material for a properly carded
ceramics corpus; the restricted rows are recorded so nobody has to
re-audit them.
