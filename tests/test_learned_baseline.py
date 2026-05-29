"""Regression tests for the learned reference baseline.

The pinned held-out Youden's J values are the headline of the learned-
baseline analysis: a linear logistic regression on the six descriptors
ties the best textbook rule (J ~ 0.09), while adding squared and
interaction terms roughly triples it (J ~ 0.31). Fitting is deterministic
(zero init, fixed gradient-descent schedule), so these reproduce exactly
up to floating-point noise.

Skipped unless numpy (the ``[ml]`` extra) and the v0.1.0 CSV are present.
"""

from __future__ import annotations

import pathlib

import pytest

pytest.importorskip("numpy")

from hea_bench.baselines import LogisticBaseline, descriptor_vector, evaluate

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
V010 = REPO_ROOT / "data" / "consolidated" / "v0.1.0" / "consolidated.csv"

pytestmark = pytest.mark.skipif(not V010.exists(), reason=f"v0.1.0 CSV not at {V010}")

_CANTOR = {"Co": 0.2, "Cr": 0.2, "Fe": 0.2, "Mn": 0.2, "Ni": 0.2}


def test_descriptor_vector_shape_and_cantor() -> None:
    v = descriptor_vector(_CANTOR)
    assert len(v) == 6
    # size mismatch, VEC, mixing entropy match the pinned Cantor descriptors
    assert v[0] == pytest.approx(3.164, abs=0.001)
    assert v[1] == pytest.approx(8.0, abs=1e-9)
    assert v[2] == pytest.approx(13.381, abs=0.001)


def test_linear_baseline_ties_best_rule() -> None:
    """Linear logistic regression: held-out J ~ 0.09, statistically the
    same as the best textbook rule (Zhang delta, J 0.094)."""
    report = evaluate(V010, interactions=False, k=5, seed=0)
    assert report["n_rows"] == 6922
    assert report["youden_j"]["mean"] == pytest.approx(0.092, abs=0.01)
    assert report["accuracy"]["mean"] == pytest.approx(0.549, abs=0.01)


def test_interaction_baseline_triples_discrimination() -> None:
    """Adding squares + pairwise interactions roughly triples J to ~0.31
    and lifts accuracy to ~0.66 -- the headline learned-baseline result."""
    report = evaluate(V010, interactions=True, k=5, seed=0)
    assert report["n_rows"] == 6922
    assert report["youden_j"]["mean"] == pytest.approx(0.313, abs=0.01)
    assert report["accuracy"]["mean"] == pytest.approx(0.662, abs=0.01)


def test_interactions_beat_linear_by_a_wide_margin() -> None:
    linear = evaluate(V010, interactions=False, k=5, seed=0)["youden_j"]["mean"]
    inter = evaluate(V010, interactions=True, k=5, seed=0)["youden_j"]["mean"]
    assert inter - linear > 0.15


def test_fit_predict_roundtrip_is_deterministic() -> None:
    import numpy as np

    rows, features, labels = _load()
    X = np.asarray(features, dtype=float)
    y = np.asarray(labels, dtype=float)
    a = LogisticBaseline(interactions=True).fit(X, y).predict(X)
    b = LogisticBaseline(interactions=True).fit(X, y).predict(X)
    assert a == b


def _load():
    from hea_bench.baselines import load_features

    return load_features(V010)
