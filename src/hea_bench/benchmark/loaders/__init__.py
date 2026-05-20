"""Per-source dataset loaders.

Each loader returns an iterable of `AlloyRecord` rows in a canonical
schema, hiding the upstream column conventions, formula syntax, and
phase-label vocabulary from the consolidator.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..composition import Composition
from ..taxonomy import PhaseClass


@dataclass(frozen=True)
class AlloyRecord:
    """One row in the consolidated benchmark schema.

    Attributes
    ----------
    source
        Identifier of the upstream source (e.g., ``"borg2020"``,
        ``"pei2020"``, ``"peivaste"``).
    source_row_id
        Stable identifier from the upstream row — index, Reference ID,
        whatever the source uses to point back to its own records.
    formula_raw
        The composition string as it appeared in the upstream CSV,
        verbatim. Useful for traceability.
    composition
        Normalized mole-fraction dict (sums to 1.0).
    canonical_phase
        One of the `PhaseClass` values: ``BCC``, ``FCC``, ``HCP``, or
        ``multi-phase``.
    source_label
        The upstream phase label string, preserved verbatim for users
        who want finer granularity than the canonical 4-class.
    processing
        Processing route, if the upstream source records it (Borg only).
        ``None`` for sources that don't.
    source_doi
        DOI of the primary-literature paper this alloy was reported in,
        if the upstream source records it (Borg only).
    """

    source: str
    source_row_id: str
    formula_raw: str
    composition: Composition
    canonical_phase: PhaseClass
    source_label: str
    processing: str | None = None
    source_doi: str | None = None
