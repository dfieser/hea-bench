"""Conformal prediction over any fitted model, standard library only.

Conformal prediction turns a fitted point predictor into a set- or
interval-valued predictor with a distribution-free, finite-sample
marginal coverage guarantee: at miscoverage level alpha, the returned
set contains the true label (or the interval the true value) with
probability at least 1 - alpha, on average over draws of calibration
and test data. The guarantee needs no assumption about the model, only
that calibration and test rows are exchangeable.

Calibration scores come from one of two places. :meth:`fit_calibrate`
scores held-out calibration rows with the fitted model (split
conformal). :meth:`calibrate_scores` takes scores made elsewhere, and
:func:`cross_val_scores` makes them by cross-validation: every row is
scored by a model fitted without the fold that holds it, so every row
calibrates and the final model can train on all of them. With folds
that keep whole alloy systems together, the scores measure the error a
model makes on systems it has never seen, which is the conservative
case for a query. The finite-sample guarantee above is exact for split
conformal. Pairing cross-validation scores with a model refit on every
row is the cross-validation method that Barber et al. (Ann. Statist.
49, 486, 2021) analyze next to the jackknife+, and it carries no exact
guarantee, so the package measures the coverage it delivers
(``docs/uncertainty-coverage.md``, ``docs/property-hardness.md``).

Scores can be calibrated per group (Mondrian conformal prediction):
each group gets its own threshold from its own scores, and the
guarantee then holds within every group, not just on average over a
mix. The phase sets use this to calibrate alloys with fewer than four
elements apart from the multi-principal alloys, whose errors differ.

The exchangeability assumption is the honest print in the corner. A
query in a novel chemistry is not exchangeable with the calibration
rows, and the guarantee weakens there; that is why
:mod:`hea_bench.uncertainty.applicability` ships alongside and why
every prediction surface in this package carries an ``in_domain`` flag
next to its interval. Empirical behavior on the corpus is measured in
``docs/uncertainty-coverage.md``.

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
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence

#: The group key of an uncalibrated-by-group (pooled) wrapper.
POOLED = None


def _check_alpha(alpha: float) -> None:
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be strictly between 0 and 1, got {alpha!r}")


def _quantile_rank(n: int, alpha: float) -> int:
    """Rank (1-based) of the calibration score used as the threshold."""
    return math.ceil((n + 1) * (1.0 - alpha))


def classifier_scores(model, X: Sequence, y: Sequence[str]) -> list[float]:
    """``1 - p_model(true class)`` per row.

    A label the model never saw in training gets probability zero, so
    score 1.0: a cross-validation fold may lack a rare class, and that
    model really does rule the class out.
    """
    index_of = {str(label): index for index, label in enumerate(model.classes_)}
    return [
        1.0 - (float(row[index_of[str(label)]]) if str(label) in index_of else 0.0)
        for row, label in zip(model.predict_proba(list(X)), y)
    ]


def regressor_scores(model, X: Sequence, y: Sequence[float]) -> list[float]:
    """Absolute residual per row."""
    return [
        abs(float(observed) - float(predicted))
        for observed, predicted in zip(y, model.predict(list(X)))
    ]


def cross_val_scores(
    make_model: Callable[[], object],
    X: Sequence,
    y: Sequence,
    folds: Iterable[tuple[Sequence[int], Sequence[int]]],
) -> list[float]:
    """Every row's nonconformity score from a model fitted without its fold.

    ``make_model()`` returns a fresh unfitted estimator; ``folds`` yields
    ``(train_positions, test_positions)`` pairs whose test parts cover
    every row exactly once. Classifiers (anything with
    ``predict_proba``) get :func:`classifier_scores`, regressors
    :func:`regressor_scores`.
    """
    scores: list[float | None] = [None] * len(y)
    for train, test in folds:
        model = make_model()
        model.fit([X[i] for i in train], [y[i] for i in train])
        score = (
            classifier_scores
            if callable(getattr(model, "predict_proba", None))
            else regressor_scores
        )
        for position, value in zip(test, score(model, [X[i] for i in test], [y[i] for i in test])):
            if scores[position] is not None:
                raise ValueError("folds must hold every row in exactly one test part")
            scores[position] = value
    if any(value is None for value in scores):
        raise ValueError("folds must hold every row in exactly one test part")
    return scores  # type: ignore[return-value]


class _SplitConformal:
    """Calibration-quantile machinery shared by both wrappers.

    Subclasses store sorted nonconformity scores per group in
    ``_scores`` (the key :data:`POOLED` when not calibrated by group);
    everything about turning those scores into a finite-sample threshold
    lives here, once, because this is the trust layer and divergence
    between the two wrappers would be worst.
    """

    _scores: dict | None

    @staticmethod
    def _check_calibration(X_cal: Sequence, y_cal: Sequence) -> None:
        if len(X_cal) == 0 or len(X_cal) != len(y_cal):
            raise ValueError("calibration data must be non-empty and aligned in length")

    def _store(self, scores: Sequence[float], groups: Sequence | None) -> None:
        if len(scores) == 0:
            raise ValueError("calibration scores must be non-empty")
        if groups is not None and len(groups) != len(scores):
            raise ValueError("groups must align with the calibration scores")
        by_group: dict = defaultdict(list)
        for position, score in enumerate(scores):
            by_group[POOLED if groups is None else groups[position]].append(float(score))
        self._scores = {group: sorted(values) for group, values in by_group.items()}

    def calibrate_scores(self, scores: Sequence[float], groups: Sequence | None = None):
        """Calibrate from nonconformity scores made elsewhere.

        Pass scores from :func:`cross_val_scores` (or any rows the model
        did not train on). With ``groups``, each group gets its own
        threshold and every query must then name its group.
        """
        self._store(scores, groups)
        return self

    @property
    def groups(self) -> tuple:
        """Calibration groups, empty when calibrated as one pool."""
        if self._scores is None or set(self._scores) == {POOLED}:
            return ()
        return tuple(sorted(self._scores, key=str))

    def n_calibration(self, group=POOLED) -> int:
        """Calibration scores behind the threshold for this group."""
        if self._scores is None:
            raise ValueError("call fit_calibrate before predicting")
        if group is POOLED and POOLED not in self._scores:
            return sum(len(values) for values in self._scores.values())
        return len(self._scores.get(group, ()))

    def _threshold(self, alpha: float, group=POOLED) -> float | None:
        _check_alpha(alpha)
        if self._scores is None:
            raise ValueError("call fit_calibrate before predicting")
        if group is POOLED and POOLED not in self._scores:
            raise ValueError("this wrapper is calibrated by group; name the query's group")
        scores = self._scores.get(group, ())
        rank = _quantile_rank(len(scores), alpha)
        if rank > len(scores):
            return None
        return scores[rank - 1]

    def _thresholds(self, alpha: float, n_rows: int, groups: Sequence | None) -> list:
        if groups is None:
            return [self._threshold(alpha)] * n_rows
        if len(groups) != n_rows:
            raise ValueError("groups must align with the query rows")
        cache: dict = {}
        out = []
        for group in groups:
            if group not in cache:
                cache[group] = self._threshold(alpha, group)
            out.append(cache[group])
        return out

    def degenerate(self, alpha: float = 0.1, group=POOLED) -> bool:
        """True when this alpha is unreachable with the calibration size.

        In that regime the prediction is maximal for every query (the
        full class set, or an unbounded interval), which satisfies the
        guarantee vacuously. A group with no calibration scores is
        degenerate at every alpha.
        """
        return self._threshold(alpha, group) is None


class ConformalClassifier(_SplitConformal):
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
        self._scores: dict | None = None

    def fit_calibrate(
        self, X_cal: Sequence, y_cal: Sequence[str], groups: Sequence | None = None
    ) -> "ConformalClassifier":
        """Store sorted nonconformity scores from held-out calibration rows.

        Calibration rows must be disjoint from the rows the model was
        fitted on, or the guarantee is void.
        """
        self._check_calibration(X_cal, y_cal)
        for label in y_cal:
            if str(label) not in self._classes:
                raise ValueError(
                    f"calibration label {label!r} is not among the model classes "
                    f"{self._classes}"
                )
        self._store(classifier_scores(self._model, X_cal, y_cal), groups)
        return self

    def predict_set(
        self, X: Sequence, alpha: float = 0.1, groups: Sequence | None = None
    ) -> list[set[str]]:
        """One label set per query row; may be empty, may be the full set."""
        rows = self._model.predict_proba(list(X))
        return [
            set(self._classes)
            if threshold is None
            else {
                cls
                for cls, probability in zip(self._classes, row)
                if 1.0 - float(probability) <= threshold
            }
            for row, threshold in zip(rows, self._thresholds(alpha, len(rows), groups))
        ]


class ConformalRegressor(_SplitConformal):
    """Wrap a fitted regressor with symmetric conformal intervals."""

    def __init__(self, model) -> None:
        if not callable(getattr(model, "predict", None)):
            raise ValueError("model must expose predict (a fitted sklearn-style regressor)")
        self._model = model
        self._scores: dict | None = None

    def fit_calibrate(
        self, X_cal: Sequence, y_cal: Sequence[float], groups: Sequence | None = None
    ) -> "ConformalRegressor":
        """Store sorted absolute residuals from held-out calibration rows."""
        self._check_calibration(X_cal, y_cal)
        self._store(regressor_scores(self._model, X_cal, y_cal), groups)
        return self

    def predict_interval(
        self, X: Sequence, alpha: float = 0.1, groups: Sequence | None = None
    ) -> list[tuple[float, float]]:
        """One symmetric interval per query row; unbounded when degenerate."""
        predictions = self._model.predict(list(X))
        return [
            (-math.inf, math.inf)
            if threshold is None
            else (float(predicted) - threshold, float(predicted) + threshold)
            for predicted, threshold in zip(
                predictions, self._thresholds(alpha, len(predictions), groups)
            )
        ]


__all__ = ["ConformalClassifier", "ConformalRegressor"]
