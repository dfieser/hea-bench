# Glossary

Every term, symbol, abbreviation, and metric used anywhere in this
project is defined here, once. Other documents link here on first use
instead of re-defining. If you add a term to any doc, add it here too
(see the documentation rule in [CONTRIBUTING.md](./CONTRIBUTING.md)).

## How to read the scoring tables (metrics)

Each rule is treated as a yes/no classifier and scored against the
experimentally observed phase. For a rule that predicts a "positive"
class (e.g. single-phase) versus a "negative" class (e.g. multi-phase):

- **n_eval** (also written *n evaluated*) — the number of alloys the
  rule was actually scored on, after dropping any it cannot be applied
  to (an element missing from the property table, a conflicting phase
  label, or a phase the rule does not address). It is usually smaller
  than the full benchmark.
- **accuracy** — of all evaluated alloys, the fraction the rule labels
  correctly (both positives and negatives). On a near-50/50 dataset, a
  rule that always guesses the more common class already scores about
  50%, so accuracy alone is not enough — see Youden's J.
- **sensitivity** (= *recall* of the positive class; *true-positive
  rate*) — **of the alloys that truly are the positive class, the
  fraction the rule labels positive.** Always stated with the class it
  refers to, e.g. *sensitivity (single-phase)* = of truly single-phase
  alloys, the fraction the rule calls single-phase.
- **specificity** (= recall of the negative class; *true-negative
  rate*) — **of the alloys that truly are the negative class, the
  fraction the rule labels negative**, e.g. *specificity (multi-phase)*
  = of truly multi-phase alloys, the fraction the rule calls
  multi-phase.
- **per-class recall** (used for the structure rule, which has three
  classes rather than two) — for a given class, the fraction of alloys
  truly in that class that the rule predicts as that class. For
  example, *FCC recall* (sometimes written "FCC sensitivity") = of the
  alloys observed to be FCC, the fraction the rule predicts FCC.
  *Always name the class*; "sensitivity" with no class is meaningless.
- **Youden's J** — a single number for how well a rule separates the
  two classes: `J = sensitivity + specificity − 1`. It runs from −1 to
  +1. **J = 0 means no better than guessing** (including any rule that
  always predicts one class); J = 1 is perfect. This is the headline
  metric, because accuracy can look fine while J ≈ 0.
- **Wilson 95% confidence interval** — a confidence interval for a
  proportion (here, accuracy) that stays sensible near 0% and 100%,
  unlike the textbook normal approximation.
- **confusion matrix** — the four raw counts behind the metrics above:
  true positives, false positives, true negatives, false negatives.

## Validation terms

- **in-sample** — measured on the same data used to choose the rule's
  threshold. Optimistic.
- **held-out** / **cross-validation** — the threshold is chosen on a
  training portion and the rule is scored on a separate, unseen
  portion, so the number is an honest estimate of new-alloy
  performance.
- **stratified k-fold** — the benchmark is split into *k* equal parts
  ("folds") so each fold has the same mix of phases and data sources;
  each fold is held out in turn. We use *k* = 5.
- **conflict rows** — compositions where two source datasets report
  different phases. Their `canonical_phase` is left blank and both
  labels are kept rather than silently picking one.

## Phase outcomes and structures

- **single-phase** — the alloy forms one solid phase.
- **multi-phase** — anything not single-phase: two or more coexisting
  phases, an ordered compound, or a glass. (In this benchmark's coarse
  labels, amorphous is bundled here too.)
- **FCC / BCC / HCP** — the three common crystal structures of a
  single-phase solid solution: face-centred cubic, body-centred cubic,
  hexagonal close-packed.
- **solid solution (SS)** — the elements share one crystal lattice at
  random (FCC, BCC, or HCP).
- **intermetallic (IM)** — an ordered compound with a fixed structure
  and stoichiometry (e.g. Laves phases, B2), distinct from a random
  solid solution.
- **amorphous (AM)** — a glassy, non-crystalline solid.
- **HEA / MEA / dilute** — high-, medium-, and low-entropy composition
  classes from the mixing entropy (Yeh's descriptive bins; see ΔS_mix).

## Descriptors (the per-alloy quantities the rules use)

- **δ** (atomic size mismatch) — how spread out the constituent atomic
  radii are about their mean, in percent. Large δ destabilises a solid
  solution.
- **VEC** (valence electron concentration) — the composition-weighted
  average number of valence electrons per atom.
- **ΔS_mix** (mixing entropy) — the configurational entropy of randomly
  mixing the elements, in J/(mol·K). Higher for more, more-equal
  components.
- **ΔH_mix** (mixing enthalpy) — the heat of mixing, in kJ/mol,
  estimated from the Miedema model (see below). Negative favours mixing.
- **T_m** (melting temperature) — the composition-weighted (rule-of-
  mixtures) average melting point, in kelvin.
- **Ω** (Yang–Zhang parameter) — `T_m · ΔS_mix / |ΔH_mix|`,
  dimensionless. It weighs entropy (which favours a solid solution)
  against enthalpy (which can favour ordered or separated phases).
- **S_E** (excess / mismatch entropy) — a hard-sphere packing-entropy
  penalty from atoms being different sizes; used by the Ye φ rule.
- **ΔG_ss** — Gibbs energy of forming the disordered solid solution.
- **ΔG_max** — the most stable competing binary intermetallic's energy
  (here approximated by the most negative Miedema pair enthalpy).
- **Φ** (capital phi, King) — `ΔG_ss / −|ΔG_max|`; > 1 predicts a solid
  solution beats the best competing intermetallic.
- **φ** (lowercase phi, Ye) — `(ΔS_mix − |ΔH_mix|/T_m) / |S_E|`;
  entropic stabilisation versus the enthalpy-plus-size-misfit penalty.

## Models and methods

- **Miedema model** — a semi-empirical model that estimates the mixing
  enthalpy of a metal pair; the source of the ΔH_mix values.
- **rule (textbook rule)** — one of the published single-threshold
  criteria (Yeh ΔS_mix, Zhang δ, Guo–Liu VEC, Yang–Zhang Ω, King Φ,
  Ye φ), each wrapped as a classifier.
- **learned baseline** — a logistic regression on the descriptors
  (`hea_bench.baselines`); the floor a new method should beat.
- **R** — the ideal-gas constant, 8.314 J/(mol·K); thresholds like
  "ΔS_mix > 1.5R" are written as multiples of it.
