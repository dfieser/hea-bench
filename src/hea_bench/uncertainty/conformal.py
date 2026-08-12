"""Split conformal prediction over any fitted model, standard library only.

Split (inductive) conformal prediction turns a fitted point predictor
into a set- or interval-valued predictor with a distribution-free,
finite-sample marginal coverage guarantee: at miscoverage level alpha,
the returned set contains the true label (or the interval the true
value) with probability at least 1 - alpha, on average over draws of
calibration and test data. The guarantee needs no assumption about the
model, only that calibration and test rows are exchangeable.

That assumption is the honest print in the corner. A query in a novel
chemistry is precisely not exchangeable with corpus calibration rows,
and the guarantee weakens there; that failure mode is why
:mod:`hea_bench.uncertainty.applicability` ships alongside and why every
prediction surface in this package carries an ``in_domain`` flag next to
its interval. Empirical behavior on the corpus, in and out of domain, is
measured in ``docs/uncertainty-coverage.md``.

Scores are the standard ones: ``1 - p_model(true class)`` for
classification, absolute residual for regression. The calibration
quantile uses the finite-sample correction, the k-th smallest score
with ``k = ceil((n + 1) * (1 - alpha))``. When k exceeds n the
requested level is unreachable with this calibration size; the
classifier then returns the full class set and the regressor an
unbounded interval, and :meth:`degenerate` reports it, because a
maximal prediction is the truthful answer rather than an error.

Classification sets can also be empty: when no class reaches the
calibrated probability bar, the honest statement at that level is that
no label is credible, not a forced best guess.

This module wraps models duck-typed to the scikit-learn interface
(``predict_proba`` plus ``classes_``, or ``predict``) but does not
import scikit-learn; it is standard-library only, like the core.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def _check_alpha(alpha: float) -> None:
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be strictly between 0 and 1, got {alpha!r}")


def _quantile_rank(n: int, alpha: float) -> int:
    """Rank (1-based) of the calibration score used as the threshold."""
    return math.ceil((n + 1) * (1.0 - alpha))


class ConformalClassifier:
    """Wrap a fitted probabilistic classifier with conformal sets.

    Parameters
    ----------
    model
        A fitted classifier exposing ``predict_proba(X)`` and
        ``classes_``, scikit-learn style. The model is used as-is and
        never refitted here.
    """

    def __init__(self, model) -> None:
        if not callable(getattr(model, "predict_proba", None)) or not hasattr(
            model, "classes_"
        ):
            raise ValueError(
                "model must expose predict_proba and classes_ (a fitted "
                "sklearn-style probabilistic classifier)"
            )
        self._model = model
        self._classes: tuple[str, ...] = tuple(str(cls) for cls in model.classes_)
        self._scores: list[float] | None = None

    def fit_calibrate(self, X_cal: Sequence, y_cal: Sequence[str]) -> "ConformalClassifier":
        """Store sorted nonconformity scores from held-out calibration rows.

        Calibration rows must be disjoint from the rows the model was
        fitted on, or the guarantee is void.
        """
        if len(X_cal) == 0 or len(X_cal) != len(y_cal):
            raise ValueError("calibration data must be non-empty and aligned in length")
        index_of = {label: index for index, label in enumerate(self._classes)}
        scores: list[float] = []
        for row, label in zip(self._model.predict_proba(list(X_cal)), y_cal):
            key = str(label)
            if key not in index_of:
                raise ValueError(
                    f"calibration label {label!r} is not among the model classes "
                    f"{self._classes}"
                )
            scores.append(1.0 - float(row[index_of[key]]))
        self._scores = sorted(scores)
        return self

    def _threshold(self, alpha: float) -> float | None:
        _check_alpha(alpha)
        if self._scores is None:
            raise ValueError("call fit_calibrate before predicting")
        rank = _quantile_rank(len(self._scores), alpha)
        if rank > len(self._scores):
            return None
        return self._scores[rank - 1]

    def degenerate(self, alpha: float = 0.1) -> bool:
        """True when this alpha is unreachable with the calibration size.

        In that regime :meth:`predict_set` returns the full class set for
        every query, which satisfies the guarantee vacuously.
        """
        return self._threshold(alpha) is None

    def predict_set(self, X: Sequence, alpha: float = 0.1) -> list[set[str]]:
        """One label set per query row; may be empty, may be the full set."""
        threshold = self._threshold(alpha)
        rows = self._model.predict_proba(list(X))
        if threshold is None:
            return [set(self._classes) for _ in rows]
        return [
            {
                cls
                for cls, probability in zip(self._classes, row)
                if 1.0 - float(probability) <= threshold
            }
            for row in rows
        ]


class ConformalRegressor:
    """Wrap a fitted regressor with symmetric conformal intervals."""

    def __init__(self, model) -> None:
        if not callable(getattr(model, "predict", None)):
            raise ValueError("model must expose predict (a fitted sklearn-style regressor)")
        self._model = model
        self._scores: list[float] | None = None

    def fit_calibrate(self, X_cal: Sequence, y_cal: Sequence[float]) -> "ConformalRegressor":
        """Store sorted absolute residuals from held-out calibration rows."""
        if len(X_cal) == 0 or len(X_cal) != len(y_cal):
            raise ValueError("calibration data must be non-empty and aligned in length")
        predictions = self._model.predict(list(X_cal))
        self._scores = sorted(
            abs(float(observed) - float(predicted))
            for observed, predicted in zip(y_cal, predictions)
        )
        return self

    def _threshold(self, alpha: float) -> float | None:
        _check_alpha(alpha)
        if self._scores is None:
            raise ValueError("call fit_calibrate before predicting")
        rank = _quantile_rank(len(self._scores), alpha)
        if rank > len(self._scores):
            return None
        return self._scores[rank - 1]

    def degenerate(self, alpha: float = 0.1) -> bool:
        """True when this alpha is unreachable with the calibration size."""
        return self._threshold(alpha) is None

    def predict_interval(
        self, X: Sequence, alpha: float = 0.1
    ) -> list[tuple[float, float]]:
        """One symmetric interval per query row; unbounded when degenerate."""
        threshold = self._threshold(alpha)
        predictions = self._model.predict(list(X))
        if threshold is None:
            return [(-math.inf, math.inf) for _ in predictions]
        return [
            (float(predicted) - threshold, float(predicted) + threshold)
            for predicted in predictions
        ]


__all__ = ["ConformalClassifier", "ConformalRegressor"]
