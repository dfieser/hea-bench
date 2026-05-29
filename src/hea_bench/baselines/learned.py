"""Learned reference baseline for single-phase vs multi-phase prediction.

This is the floor a new phase-prediction method should beat. Unlike the
textbook rules (each a threshold on a single descriptor), it weights all
six descriptors jointly with a logistic regression and, with
``interactions=True``, adds their squares and pairwise products.

On the consolidated v0.1.0 benchmark under the same stratified five-fold
held-out protocol used for the rules, the linear model ties the best
rule (Youden's J ~ 0.09) while the interaction model reaches J ~ 0.31:
the descriptors carry signal the single-threshold rules cannot reach.

Requires the optional ``[ml]`` extra (numpy):

    pip install "hea-bench[ml]"

The descriptor functions and the held-out splitter are dependency-free;
only the model fitting needs numpy, imported lazily so importing this
module never fails on a base install.
"""

from __future__ import annotations

import csv
import itertools
import math
import pathlib
import statistics

from .. import (
    delta,
    melting_temperature,
    mixing_enthalpy,
    omega,
    parse_formula,
    smix,
    vec,
)
from ..benchmark.taxonomy import binary_observed
from ..descriptors.data.elemental import covered_elements
from ..evaluation.holdout import evaluate_binary, stratified_kfold_splits

# Order matters: the feature vector and any interaction expansion follow it.
FEATURE_NAMES = (
    "size_mismatch",        # delta, %
    "vec",                  # valence electron concentration
    "mixing_entropy",       # Delta S_mix, J/(mol K)
    "mixing_enthalpy",      # Delta H_mix, kJ/mol
    "melting_temperature",  # T_m, K
    "omega",                # Yang-Zhang Omega (capped, see below)
)

# Omega diverges as the mixing enthalpy approaches zero. Cap it so the
# feature stays finite without distorting the (already large) values that
# all map to "entropy wins" anyway.
_OMEGA_CAP = 50.0


def _require_numpy():
    try:
        import numpy as np
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise ModuleNotFoundError(
            "the learned baseline needs numpy; install the optional extra: "
            'pip install "hea-bench[ml]"'
        ) from exc
    return np


def descriptor_vector(composition) -> list[float]:
    """Return the six-descriptor feature vector for a composition.

    Pure Python (no numpy); order matches :data:`FEATURE_NAMES`.
    """
    w = omega(composition)
    if not math.isfinite(w) or w > _OMEGA_CAP:
        w = _OMEGA_CAP
    return [
        delta(composition),
        vec(composition),
        smix(composition),
        mixing_enthalpy(composition),
        melting_temperature(composition),
        w,
    ]


class LogisticBaseline:
    """L2-regularised logistic regression on the descriptor vector.

    Features are standardised internally using the training data. With
    ``interactions=True`` the design matrix is expanded with squared and
    pairwise-product terms before standardisation. Gradient descent with
    a fixed schedule makes the fit deterministic.
    """

    def __init__(
        self,
        *,
        interactions: bool = False,
        iters: int = 1500,
        lr: float = 0.3,
        l2: float = 1e-2,
    ) -> None:
        self.interactions = interactions
        self.iters = iters
        self.lr = lr
        self.l2 = l2
        self._np = None
        self._mean = None
        self._std = None
        self._weights = None
        self._bias = 0.0

    def _expand(self, X):
        np = self._np
        if not self.interactions:
            return X
        cols = [X, X**2]
        d = X.shape[1]
        for i, j in itertools.combinations(range(d), 2):
            cols.append((X[:, i] * X[:, j])[:, None])
        return np.hstack(cols)

    def fit(self, X, y) -> "LogisticBaseline":
        np = self._np = _require_numpy()
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        Xe = self._expand(X)
        self._mean = Xe.mean(axis=0)
        self._std = Xe.std(axis=0)
        self._std[self._std == 0] = 1.0
        Xs = (Xe - self._mean) / self._std

        w = np.zeros(Xs.shape[1])
        b = 0.0
        n = len(y)
        for _ in range(self.iters):
            p = 1.0 / (1.0 + np.exp(-np.clip(Xs @ w + b, -30, 30)))
            w -= self.lr * (Xs.T @ (p - y) / n + self.l2 * w)
            b -= self.lr * float((p - y).mean())
        self._weights = w
        self._bias = b
        return self

    def predict_proba(self, X):
        np = self._np
        if np is None:  # pragma: no cover
            raise RuntimeError("call fit() before predict")
        Xe = self._expand(np.asarray(X, dtype=float))
        Xs = (Xe - self._mean) / self._std
        return 1.0 / (1.0 + np.exp(-np.clip(Xs @ self._weights + self._bias, -30, 30)))

    def predict(self, X) -> list[str]:
        return [
            "single-phase" if p > 0.5 else "multi-phase"
            for p in self.predict_proba(X)
        ]


def load_features(csv_path: str | pathlib.Path):
    """Read the benchmark CSV into (rows, features, labels).

    ``rows`` carry ``canonical_phase`` and ``sources`` for the held-out
    stratifier; ``features`` is the list of descriptor vectors; ``labels``
    is 1.0 for single-phase, 0.0 for multi-phase. Rows that are unscorable
    (uncovered element), label-conflicted, or non-finite are skipped.
    """
    elem = covered_elements()
    rows: list[dict[str, str]] = []
    features: list[list[float]] = []
    labels: list[float] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            canonical = (row.get("canonical_phase") or "").strip()
            if not canonical:
                continue
            try:
                comp = parse_formula(row["composition_key"])
            except (KeyError, ValueError):
                continue
            if not set(comp) <= elem:
                continue
            vector = descriptor_vector(comp)
            if not all(math.isfinite(x) for x in vector):
                continue
            rows.append(
                {"canonical_phase": canonical, "sources": row.get("sources", "")}
            )
            features.append(vector)
            labels.append(1.0 if binary_observed(canonical) == "single-phase" else 0.0)
    return rows, features, labels


def evaluate(
    csv_path: str | pathlib.Path,
    *,
    interactions: bool = False,
    k: int = 5,
    seed: int = 0,
) -> dict:
    """Held-out k-fold evaluation of the learned baseline.

    Uses the same stratified split (by phase and source) as the rule
    held-out protocol, so the returned metrics are directly comparable to
    the textbook rules. Returns mean and standard error across folds for
    accuracy, sensitivity, specificity, and Youden's J.
    """
    np = _require_numpy()
    rows, features, labels = load_features(csv_path)
    X = np.asarray(features, dtype=float)
    y = np.asarray(labels, dtype=float)

    accuracy, sensitivity, specificity, youden = [], [], [], []
    for split in stratified_kfold_splits(rows, k=k, seed=seed):
        train = list(split.train_indices)
        test = list(split.test_indices)
        model = LogisticBaseline(interactions=interactions).fit(X[train], y[train])
        preds = model.predict(X[test])
        obs = ["single-phase" if v == 1 else "multi-phase" for v in y[test]]
        stats = evaluate_binary(preds, obs, positive_label="single-phase")
        accuracy.append(stats.accuracy)
        sensitivity.append(stats.sensitivity)
        specificity.append(stats.specificity)
        youden.append(stats.youden_j)

    def summarize(values: list[float]) -> dict[str, float]:
        return {
            "mean": sum(values) / len(values),
            "se": statistics.pstdev(values) / len(values) ** 0.5,
        }

    return {
        "n_rows": len(y),
        "k": k,
        "seed": seed,
        "interactions": interactions,
        "n_descriptors": int(X.shape[1]),
        "accuracy": summarize(accuracy),
        "sensitivity": summarize(sensitivity),
        "specificity": summarize(specificity),
        "youden_j": summarize(youden),
    }
