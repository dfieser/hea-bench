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
