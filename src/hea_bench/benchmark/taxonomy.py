"""Canonical phase-label taxonomy for the consolidated benchmark.

For v0.1.0 we adopt a deliberately coarse 4-class taxonomy:

    BCC          : single-phase body-centred-cubic solid solution
    FCC          : single-phase face-centred-cubic solid solution
    HCP          : single-phase hexagonal-close-packed solid solution
    multi-phase  : everything else — including dual-phase solid solutions,
                   intermetallics (IM), amorphous (AM), Laves, B2,
                   and any combination thereof

This is the lowest-common-denominator that all three v0.1.0 source datasets
(Borg 2020, Pei 2020, Peivaste) can map into without ambiguity. Sources
with finer labels (Borg's full Microstructure column with 30+ sublabels;
Peivaste's 12-category column distinguishing AM, IM, HCP, and various
multi-phase combinations) **retain their original labels as side-channel
columns** in the consolidated CSV — so a future v0.2.0 release can ship
a finer canonical taxonomy without re-acquiring data.

Naming note. "multi-phase" follows Pei (2020) convention and is the most
common literature usage, but is technically broader than its name
suggests: it includes amorphous alloys (which are *not* multi-phase in
the crystallographic sense — they are single-phase non-crystalline) and
single-phase intermetallics. A more accurate name would be "not-single-
phase-crystalline-SS" but that is unwieldy and unstandard. Users with
strict definitions should consult the side-channel columns.
"""

from __future__ import annotations

from enum import Enum


class PhaseClass(str, Enum):
    """Canonical 4-class phase taxonomy. Subclasses `str` so it serializes
    cleanly to CSV / JSON without explicit conversion."""

    BCC = "BCC"
    FCC = "FCC"
    HCP = "HCP"
    MULTI = "multi-phase"


# Per-source mappings from upstream label → canonical class.
# Where a mapping is lossy (collapsing AM and IM into MULTI), the
# information is preserved separately in the consolidated CSV's
# `source_label` column.

# Borg 2020 — simplified column `PROPERTY: BCC/FCC/other`.
# Borg's full `PROPERTY: Microstructure` column has 30+ sublabels and is
# preserved separately as `borg_microstructure`. The simplified column
# does not distinguish HCP from FCC; an HCP-aware refinement is a v0.2.0
# concern.
BORG_SIMPLE_MAP: dict[str, PhaseClass] = {
    "BCC":   PhaseClass.BCC,
    "FCC":   PhaseClass.FCC,
    "other": PhaseClass.MULTI,
}

# Pei et al. 2020 — lower-case labels, 4-class.
PEI_MAP: dict[str, PhaseClass] = {
    "bcc":         PhaseClass.BCC,
    "fcc":         PhaseClass.FCC,
    "hcp":         PhaseClass.HCP,
    "multi-phase": PhaseClass.MULTI,
}

# Peivaste — 12 source labels collapse to 4 canonical.
# Caveat: AM (amorphous, single-phase non-crystalline) and IM
# (intermetallic, often single-phase ordered) are *both* collapsed into
# MULTI under this taxonomy. The original label is preserved in the
# `peivaste_label` side-channel column.
PEIVASTE_MAP: dict[str, PhaseClass] = {
    "BCC":         PhaseClass.BCC,
    "FCC":         PhaseClass.FCC,
    "HCP":         PhaseClass.HCP,
    "AM":          PhaseClass.MULTI,
    "IM":          PhaseClass.MULTI,
    "BCC+FCC":     PhaseClass.MULTI,
    "FCC+IM":      PhaseClass.MULTI,
    "BCC+IM":      PhaseClass.MULTI,
    "BCC+FCC+IM":  PhaseClass.MULTI,
    "FCC+AM":      PhaseClass.MULTI,
    "BCC+AM":      PhaseClass.MULTI,
    "BCC+FCC+AM":  PhaseClass.MULTI,
}

# Chizhevskiy et al. 2026 — LLM-extracted, free-text `Phase` column.
# Unlike the other three sources there is no small fixed label set: the
# column is messy free text ("BCC B2 + FCC L12", "C14 Laves phase + FCC",
# "cubic", "not specified", ...). We map to the coarse canonical class with a
# small parser rather than a dict. The full raw string is always preserved as
# the `source_label` side-channel for the finer SS/ORD/LAV intermetallic-typing
# analysis (which needs the named phases this canonical mapping deliberately
# collapses). See data/raw/chizhevskiy2026/README.md.

# Tokens that carry no usable phase information → skip the row.
_CHIZH_UNKNOWN = frozenset({
    "", "nan", "not specified", "unknown", "n/a", "na", "none", "-", "cubic",
})
# Substrings marking an ordered/intermetallic or amorphous phase anywhere in
# the string → the alloy is not a clean single-phase solid solution → MULTI.
_CHIZH_NONSS_MARKERS = (
    "b2", "l12", "l1_2", "laves", "sigma", "σ", "intermetallic",
    "amorphous", "mu phase", "mu-phase",
)
_CHIZH_CLEAN_SS = {"bcc": PhaseClass.BCC, "fcc": PhaseClass.FCC, "hcp": PhaseClass.HCP}


def chizhevskiy_canonical_phase(raw: str) -> PhaseClass | None:
    """Map a free-text Chizhevskiy `Phase` string to the canonical 4-class.

    Conservative by design — anything that is not unambiguously a clean
    single-phase or multi-phase *solid solution* is either flagged MULTI (if it
    names an intermetallic/amorphous phase) or skipped (``None``) if it is
    ambiguous/uninformative (``cubic``, ``martensite``, ``not specified`` …).
    The finer SS/ORD/LAV distinction is intentionally *not* made here; that
    lives in the typing analysis, which reads the preserved raw string.

    Returns ``None`` for rows to skip.
    """
    s = (raw or "").strip()
    low = s.lower()
    if low in _CHIZH_UNKNOWN:
        return None
    if any(m in low for m in _CHIZH_NONSS_MARKERS):
        return PhaseClass.MULTI
    tokens = [t.strip().lower() for t in s.split("+") if t.strip()]
    if not tokens:
        return None
    mapped = [_CHIZH_CLEAN_SS.get(t) for t in tokens]
    if any(m is None for m in mapped):
        return None  # an unrecognised token (e.g. "hcp martensite") — skip
    if len(mapped) == 1:
        return mapped[0]
    return PhaseClass.MULTI  # multi-phase solid-solution mixture, e.g. BCC+FCC


# Set of canonical labels that count as single-phase / solid solution
# under the v1.1 evaluator. The three crystalline single-phase classes
# all collapse to "single-phase" for the four binary textbook rules and
# to "solid_solution" for the two phi-family rules; "multi-phase"
# becomes the negative class in both vocabularies.
SINGLE_PHASE_CLASSES = frozenset({"BCC", "FCC", "HCP"})


def binary_observed(canonical_phase: str) -> str | None:
    """Project a canonical 4-class label to the textbook binary vocabulary.

    Returns ``"single-phase"`` for BCC/FCC/HCP, ``"multi-phase"`` for
    ``multi-phase``, and ``None`` for an empty / conflict label so the
    caller can skip the row.
    """
    if not canonical_phase:
        return None
    return "single-phase" if canonical_phase in SINGLE_PHASE_CLASSES else "multi-phase"


def phi_observed(canonical_phase: str) -> str | None:
    """Project a canonical 4-class label to the phi-family binary vocabulary.

    The two phi-family rules (``king_phi``, ``ye_phi``) emit
    ``solid_solution`` or ``intermetallic`` natively. When scored against
    the consolidated benchmark, ``multi-phase`` rows act as the negative
    (intermetallic) class. Returns ``None`` for an empty / conflict label.
    """
    if not canonical_phase:
        return None
    return "solid_solution" if canonical_phase in SINGLE_PHASE_CLASSES else "intermetallic"


# Peivaste 12-class labels that signal explicit intermetallic content.
# These are the rows on which an intermetallic-aware phi evaluation
# has direct ground truth: each label names at least one ordered
# intermetallic phase coexisting in the alloy.
PEIVASTE_INTERMETALLIC_LABELS = frozenset({"IM", "FCC+IM", "BCC+IM", "BCC+FCC+IM"})

# Peivaste 12-class labels that are unambiguously solid solution
# (single-phase BCC / FCC / HCP or a two-phase mixture of solid
# solutions). These are paired with the intermetallic labels above to
# form the binary ground truth of the intermetallic sub-benchmark.
PEIVASTE_SOLID_SOLUTION_LABELS = frozenset({"BCC", "FCC", "HCP", "BCC+FCC"})


def peivaste_intermetallic_label(peivaste_raw_label: str) -> str | None:
    """Project a raw Peivaste 12-class label to the intermetallic sub-benchmark.

    The intermetallic sub-benchmark scores the phi-family rules
    (``king_phi``, ``ye_phi``) against ground truth that explicitly
    separates intermetallic content from solid-solution-only alloys.
    Returns ``"solid_solution"`` for BCC/FCC/HCP/BCC+FCC labels,
    ``"intermetallic"`` for IM-containing labels, and ``None`` for any
    AM-containing (amorphous) label or an empty label. AM alloys are
    neither solid solution nor intermetallic in the crystallographic
    sense and the phi rules do not claim to predict their formation,
    so they are excluded from this sub-benchmark.
    """
    label = (peivaste_raw_label or "").strip()
    if not label:
        return None
    if label in PEIVASTE_SOLID_SOLUTION_LABELS:
        return "solid_solution"
    if label in PEIVASTE_INTERMETALLIC_LABELS:
        return "intermetallic"
    # AM, FCC+AM, BCC+AM, BCC+FCC+AM and any unknown label
    return None
