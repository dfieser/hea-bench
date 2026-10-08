"""Grouped calibration splitting for split conformal prediction.

The shipped models calibrate by cross-validation over whole alloy
systems instead (:func:`hea_bench.uncertainty.conformal.cross_val_scores`),
so every alloy both trains and calibrates. This helper remains for
anyone calibrating on a held-out split of their own.

Split conformal calibration must be disjoint from training; when the
data is organized in families of near-duplicate compositions, an
honest split keeps whole families on one side, otherwise calibration
scores are measured on close relatives of training rows and the
intervals come out optimistically narrow.
"""

from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Sequence


def grouped_calibration_split(
    families: Sequence[str],
    *,
    fraction: float = 0.2,
    seed: int = 0,
) -> tuple[list[int], list[int]]:
    """Split positions into (proper_train, calibration), whole families.

    Families are shuffled with the seed and moved into calibration until
    at least ``fraction`` of the rows is there, so the achieved fraction
    can overshoot slightly (families move as blocks).
    """
    if not 0.0 < fraction < 1.0:
        raise ValueError(f"fraction must be strictly between 0 and 1, got {fraction!r}")
    rows_by_family: dict[str, list[int]] = defaultdict(list)
    for index, family in enumerate(families):
        rows_by_family[family].append(index)
    if len(rows_by_family) < 2:
        raise ValueError("need at least two families to split calibration off")
    keys = sorted(rows_by_family)
    random.Random(seed).shuffle(keys)
    target = round(len(families) * fraction)
    calibration: list[int] = []
    for key in keys:
        if len(calibration) >= target:
            break
        calibration.extend(rows_by_family[key])
    calibration_set = set(calibration)
    proper = [index for index in range(len(families)) if index not in calibration_set]
    return proper, calibration


__all__ = ["grouped_calibration_split"]
