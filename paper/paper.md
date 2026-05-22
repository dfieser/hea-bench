---
title: 'hea-bench: An open benchmark suite and reference baselines for high-entropy alloy phase prediction'
tags:
  - Python
  - high-entropy alloys
  - multi-principal element alloys
  - phase prediction
  - materials informatics
  - benchmark
  - Miedema model
authors:
  - name: David Fieser
    orcid: 0009-0007-5754-4331
    affiliation: 1
affiliations:
  - name: Department of Mechanical and Aerospace, University of Tennessee Knoxville, Knoxville, TN, USA
    index: 1
date: 21 May 2026
bibliography: paper.bib
---

# Summary

High-entropy alloys are multi-component alloys with five or more
principal elements near equiatomic composition, in which the
configurational mixing entropy can stabilize a disordered solid
solution in place of intermetallic compounds [@cantor2004]. Because
the compositional space is enormous, four empirical rules are widely
used to pre-screen candidate compositions before any expensive
computation or synthesis. These are the mixing-entropy criterion of
@yeh2004, the atomic-size mismatch criterion of @zhang2008, the
valence-electron-concentration criterion of @guo2011, and the
Omega-parameter criterion of @yang2012. `hea-bench` is an open
Python package that consolidates three primary open phase-label
datasets into a single benchmark of 7,784 unique compositions,
implements the four empirical rules as diagnostic classifiers with
full statistics, and reports their reference performance against
that benchmark. The same package runs both as a standard installable
library and, without modification, inside a web browser through the
Pyodide runtime.

# Statement of need

The accuracies quoted for the four empirical rules in their original
publications were obtained on different, mutually incompatible
datasets, with different preprocessing and phase labeling. The rules
have therefore never been compared head to head on a common open
benchmark. The rules are also typically reported as a single
accuracy figure rather than with the sensitivity, specificity,
confidence intervals, and receiver-operating-characteristic analysis
that properly characterize a classifier. `hea-bench` addresses both
problems. It provides a versioned, deduplicated benchmark with
explicit per-row provenance, and it scores the empirical rules with
the diagnostic-statistics vocabulary that lets any future model be
compared on equal terms. The need is concrete. In prior work on the
thermodynamic stability of femtosecond laser-ablated high-entropy
alloy nanoparticles [@fieser2025surface], the choice of which
empirical rule to trust materially affected the analysis of phase
stability during surface restructuring.

# State of the field

The de facto standard tool for Miedema-model formation enthalpies is
MiedCalc [@zhang2016miedema], a registration-gated, Windows-only
desktop program. General-purpose materials-informatics toolkits such
as matminer [@ward2018] provide descriptor implementations as
machine-learning features but do not assemble a phase-classification
benchmark or evaluate the empirical rules as classifiers. For
materials property prediction more broadly, the MatBench suite
[@dunn2020matbench] established the value of a common benchmark with
reference baselines, but no analogous open resource exists for
high-entropy alloy phase classification. `hea-bench` occupies that
gap. It is the first open tool, to the author's knowledge, that
combines a consolidated multi-source phase benchmark, reference
diagnostic-classifier baselines for the canonical empirical rules,
and a zero-install browser interface that runs the analysis code
itself rather than a reimplementation.

# Software design

The package is organized as a set of independent components for
composition parsing, descriptor computation, the empirical rules,
diagnostic statistics, and benchmark consolidation. The descriptor
component computes the six quantities required by the rule set,
namely the mixing entropy, the atomic-size mismatch, the valence
electron concentration, the average melting temperature, the Miedema
mixing enthalpy, and the Omega parameter. Binary mixing-enthalpy
pairs are drawn from a vendored copy of the matminer Miedema table
[@ward2018], which derives from the de Boer parameter set
[@deboer1988] and is consistent with the open tabulation of
@takeuchi2005. The classifier component reports accuracy,
sensitivity, specificity, Wilson score intervals [@wilson1927], and
receiver-operating-characteristic sweeps with Youden's index
[@youden1950]. The browser interface loads the Pyodide runtime
[@pyodide] and installs the same release wheel that a package
manager would deliver, so the library has one canonical
implementation that both surfaces execute identically. The package
is released under the MIT License and is covered by a regression
test suite that pins every reported benchmark statistic.

# Reference baselines

The consolidated benchmark draws on the datasets of @borg2020,
@pei2020, and @peivaste2023, merged on a composition key with
cross-source label-conflict tracking (\autoref{fig:benchmark}).
Evaluated against this benchmark, the two binary rules return
Youden's index values near zero, which shows that on a consolidated
open dataset they reduce to predicting a single-phase solid solution
almost always.

![Composition of the v0.1.0 consolidated benchmark. Panel (a) is the
canonical phase-class distribution over all 7,784 compositions. Panel
(b) is the cross-source overlap, the number of source datasets that
independently report each composition.\label{fig:benchmark}](figures/benchmark_overview.png){ width=85% }

A receiver-operating-characteristic sweep of the @zhang2008
atomic-size rule places the balance-optimal threshold well below the
canonical value (\autoref{fig:roc}), which demonstrates the kind of
recalibration analysis the package is designed to support. The
reference numbers are reported in full in the package documentation
and are pinned in the test suite.

![Receiver-operating-characteristic curve for the @zhang2008
atomic-size rule on the v0.1.0 benchmark. The curve lies close to
the no-skill diagonal. The canonical and balance-optimal operating
points are marked.\label{fig:roc}](figures/roc_zhang_delta.png){ width=70% }

# AI usage disclosure

This manuscript and the accompanying code documentation were
prepared with computer-assisted text generation. All numerical
parameters, formulae, threshold values, and benchmark results were
independently verified by the author against the cited primary
sources or computed from documented inputs.

# Acknowledgements

The author thanks the matminer maintainers for the open Miedema
pair-enthalpy table, the Pyodide project for the browser-side Python
runtime, and the authors of the three primary source datasets for
releasing their data under reusable terms.

# References
