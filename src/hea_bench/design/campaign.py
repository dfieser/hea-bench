"""Active-learning campaigns: bring your own measurements, get a next batch.

A :class:`Campaign` holds an objective (a property name, or any label
for the user's own measured quantity), a palette, constraints, and the
user's observations. :meth:`suggest` fits an ensemble surrogate on
warm-start data plus the observations and ranks unexplored lattice
compositions by an acquisition function. State is plain human-readable
JSON on the user's disk; there are no accounts, no server, and no
telemetry, and the loop runs on the user's data, which is the point.

Design choices, stated rather than implied:

- **Surrogate**: random forest with uncertainty from per-tree
  disagreement. A Gaussian process over variable-length composition
  vectors was considered and rejected as fragile; the ensemble is less
  elegant and much harder to break. Suggestion intervals are the
  ensemble spread (2.5 to 97.5 percentile of tree predictions), which
  is a model-disagreement band, not a coverage-calibrated conformal
  interval; calibrating one would spend scarce user observations, and
  the docstring says so instead of implying a guarantee.
- **Warm start**: when the objective is ``"hardness"`` (the shipped
  tier B property) and ``warm_start=True``, the Borg room-temperature
  records whose chemistry fits the palette are pooled with the user's
  observations, equally weighted; the user's data dominates
  progressively simply by accumulating. Any other objective starts
  cold.
- **Cold-start floor**: below 10 informative rows the loop is close to
  random, so :meth:`suggest` raises :class:`ColdStartError` instead of
  pretending.
- **Batches**: several suggestions per round via the believer loop
  (refit after appending each pick's own predicted value), the standard
  cheap batch heuristic; documented, not hidden.
"""

from __future__ import annotations

import json
import math
import pathlib
import statistics
from dataclasses import dataclass

from .. import __version__
from ..composition import Composition, family_of, normalize
from ..descriptors.backend import NativeBackend, matrix_vector
from ..rules import canonical_rule_name
from ..uncertainty import fit_domain
from ..uncertainty.applicability import DomainRow
from .constraints import (
    CompositionConstraint,
    DomainConstraint,
    PropertyConstraint,
    RuleConstraint,
)
from .search import (
    _lattice_compositions,
    _rule_verdict,
    _validate_step,
    _within_bounds,
)

#: Below this many informative rows suggest() refuses.
COLD_START_FLOOR = 10

_CONSTRAINT_TYPES = {
    "RuleConstraint": RuleConstraint,
    "PropertyConstraint": PropertyConstraint,
    "CompositionConstraint": CompositionConstraint,
    "DomainConstraint": DomainConstraint,
}


class ColdStartError(RuntimeError):
    """Too few observations for suggestions that beat guessing."""


@dataclass(frozen=True)
class Suggestion:
    """One suggested composition, with its uncertainty in plain sight."""

    composition: Composition
    mean: float
    interval: tuple[float, float]
    in_domain: bool | None
    acquisition: float
    strategy: str

    def __repr__(self) -> str:  # noqa: D105 - the repr IS the interface here
        formula = "".join(
            f"{element}{fraction:.2f}" for element, fraction in sorted(self.composition.items())
        )
        return (
            f"Suggestion({formula}, mean={self.mean:.1f}, "
            f"interval=({self.interval[0]:.1f}, {self.interval[1]:.1f}), "
            f"in_domain={self.in_domain}, {self.strategy}={self.acquisition:.3g})"
        )


def _constraint_to_dict(constraint) -> dict:
    data = {"type": type(constraint).__name__}
    data.update(constraint.__dict__)
    if isinstance(constraint, RuleConstraint) and isinstance(constraint.satisfied, tuple):
        data["satisfied"] = list(constraint.satisfied)
    return data


def _constraint_from_dict(data: dict):
    kind = _CONSTRAINT_TYPES[data["type"]]
    kwargs = {key: value for key, value in data.items() if key != "type"}
    if kind is RuleConstraint and isinstance(kwargs.get("satisfied"), list):
        kwargs["satisfied"] = tuple(kwargs["satisfied"])
    return kind(**kwargs)


class Campaign:
    """One optimization campaign over a palette. See the module docstring."""

    def __init__(
        self,
        objective: str,
        palette,
        constraints: tuple = (),
        *,
        direction: str = "maximize",
        seed: int = 0,
        step: float = 0.1,
        n_elements: tuple[int, int] = (3, 5),
        warm_start: bool = True,
    ) -> None:
        if direction not in ("maximize", "minimize"):
            raise ValueError(f"direction must be maximize or minimize, got {direction!r}")
        self.objective = objective
        self.palette = sorted(dict.fromkeys(palette))
        self.constraints = tuple(constraints)
        self.direction = direction
        self.seed = seed
        self.step = step
        self.n_elements = tuple(n_elements)
        self.warm_start = warm_start
        self.observations: list[dict] = []
        # (observation count, training triple) memo: observations are
        # append-only through observe(), so the count keys the cache.
        self._training_cache: tuple[int, tuple] | None = None

    # -- state ---------------------------------------------------------------

    def observe(
        self,
        composition: Composition,
        value: float,
        *,
        processing: str | None = None,
        uncertainty: float | None = None,
    ) -> None:
        """Record one measurement. Uncertainty is stored, not yet modeled."""
        self.observations.append(
            {
                "composition": dict(normalize(composition)),
                "value": float(value),
                "processing": processing,
                "uncertainty": uncertainty,
            }
        )

    def save(self, path: pathlib.Path | str) -> None:
        payload = {
            "schema": 1,
            "hea_bench_version": __version__,
            "objective": self.objective,
            "direction": self.direction,
            "palette": self.palette,
            "constraints": [_constraint_to_dict(c) for c in self.constraints],
            "seed": self.seed,
            "step": self.step,
            "n_elements": list(self.n_elements),
            "warm_start": self.warm_start,
            "observations": self.observations,
        }
        pathlib.Path(path).write_text(
            json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8"
        )

    @classmethod
    def load(cls, path: pathlib.Path | str) -> "Campaign":
        payload = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        if payload.get("schema") != 1:
            raise ValueError(
                f"unsupported campaign schema {payload.get('schema')!r}; this "
                f"version reads schema 1"
            )
        campaign = cls(
            payload["objective"],
            payload["palette"],
            tuple(_constraint_from_dict(c) for c in payload["constraints"]),
            direction=payload["direction"],
            seed=payload["seed"],
            step=payload["step"],
            n_elements=tuple(payload["n_elements"]),
            warm_start=payload["warm_start"],
        )
        campaign.observations = list(payload["observations"])
        return campaign

    # -- modeling ------------------------------------------------------------

    def _warm_rows(self) -> list[tuple[Composition, float]]:
        if not (self.warm_start and self.objective == "hardness"):
            return []
        from ..properties.borg import hardness_records

        palette_set = set(self.palette)
        return [
            (record.composition, record.value)
            for record in hardness_records()
            if set(record.composition) <= palette_set
        ]

    def _training(self):
        key = len(self.observations)
        if self._training_cache is not None and self._training_cache[0] == key:
            return self._training_cache[1]
        backend = NativeBackend()
        rows: list[tuple[Composition, float]] = self._warm_rows()
        rows += [(obs["composition"], obs["value"]) for obs in self.observations]
        X, y, comps = [], [], []
        for comp, value in rows:
            vector = matrix_vector(comp, backend)
            if vector is not None:
                X.append(vector)
                y.append(value)
                comps.append(comp)
        self._training_cache = (key, (X, y, comps))
        return X, y, comps

    def n_informative(self) -> int:
        """Rows the surrogate can actually train on (warm start + observed)."""
        return len(self._training()[0])

    def _pool(self) -> list[Composition]:
        units = _validate_step(self.step)
        bounds = {
            c.element: (c.min, c.max)
            for c in self.constraints
            if isinstance(c, CompositionConstraint)
        }
        rule_constraints = [c for c in self.constraints if isinstance(c, RuleConstraint)]
        domain_constraints = [c for c in self.constraints if isinstance(c, DomainConstraint)]
        domain_required = domain_constraints[0].in_domain if domain_constraints else True

        domain = None
        if domain_required is not None:
            from ..uncertainty import default_domain

            domain = default_domain()
            if domain is None:
                raise RuntimeError(
                    "the campaign's domain constraint needs a built corpus; "
                    "opt out with DomainConstraint(in_domain=None) or build it"
                )

        observed = {
            tuple(sorted(normalize(obs["composition"]).items())) for obs in self.observations
        }
        pool: list[Composition] = []
        low, high = self.n_elements
        for comp in _lattice_compositions(self.palette, low, high, units):
            if not _within_bounds(comp, bounds):
                continue
            if tuple(sorted(comp.items())) in observed:
                continue
            keep = True
            for constraint in rule_constraints:
                verdict = _rule_verdict(canonical_rule_name(constraint.rule), comp)
                if not constraint.matches(verdict):
                    keep = False
                    break
            if not keep:
                continue
            if domain is not None and domain_required is not None:
                if domain.novelty(comp)["in_domain"] != domain_required:
                    continue
            pool.append(comp)
        return pool

    def suggest(self, n: int = 5, strategy: str = "ei") -> list[Suggestion]:
        """Rank the unexplored lattice and return the next batch to make.

        Raises
        ------
        ColdStartError
            Below the 10-row floor, where the loop is close to random.
        ValueError
            Unknown strategy, or an empty candidate pool.
        """
        if strategy not in ("ei", "ucb"):
            raise ValueError(f"unknown strategy {strategy!r}; expected 'ei' or 'ucb'")

        # The floor is checked before the optional dependency on purpose:
        # a user below it should hear about the data problem regardless of
        # what is installed, and the floor check itself is stdlib.
        X, y, _comps = self._training()
        if len(X) < COLD_START_FLOOR:
            raise ColdStartError(
                f"{len(X)} informative rows is below the floor of "
                f"{COLD_START_FLOOR}; below that the surrogate is close to "
                f"random and the loop refuses to pretend otherwise. Add "
                f"observations (or use a palette covered by the warm start)."
            )
        try:
            from sklearn.ensemble import RandomForestRegressor
        except ImportError as exc:
            from ..properties import PropertyUnavailableError

            raise PropertyUnavailableError(
                "campaign suggestions need scikit-learn, which is not "
                'installed. Install it with: pip install "hea-bench[properties]"'
            ) from exc

        pool = self._pool()
        if not pool:
            raise ValueError("no unexplored lattice compositions satisfy the constraints")
        backend = NativeBackend()
        pool_vectors = []
        pool_comps = []
        for comp in pool:
            vector = matrix_vector(comp, backend)
            if vector is not None:
                pool_vectors.append(vector)
                pool_comps.append(comp)

        sign = 1.0 if self.direction == "maximize" else -1.0
        try:
            campaign_domain = fit_domain(
                [DomainRow(comp, family_of(comp)) for comp in _comps]
            )
        except ValueError:
            campaign_domain = None

        # One ndarray for the whole pool: handing the same list-of-lists
        # to all 300 trees would re-validate and re-convert it per tree,
        # per pick. Values are unchanged (numpy ships with sklearn).
        import numpy

        pool_matrix = numpy.asarray(pool_vectors)

        X_now = [list(row) for row in X]
        y_now = list(y)
        chosen: list[Suggestion] = []
        taken: set[int] = set()
        for _pick in range(min(n, len(pool_comps))):
            model = RandomForestRegressor(n_estimators=300, random_state=self.seed)
            model.fit(X_now, y_now)
            per_tree = [tree.predict(pool_matrix) for tree in model.estimators_]
            best = max(sign * value for value in y_now)

            scored: list[tuple[float, int, float, tuple[float, float]]] = []
            for index in range(len(pool_comps)):
                if index in taken:
                    continue
                predictions = sorted(sign * tree[index] for tree in per_tree)
                mean = statistics.fmean(predictions)
                sigma = statistics.pstdev(predictions)
                low_q = predictions[max(0, math.floor(0.025 * len(predictions)))]
                high_q = predictions[min(len(predictions) - 1, math.ceil(0.975 * len(predictions)) - 1)]
                if strategy == "ucb":
                    score = mean + 2.0 * sigma
                else:
                    score = _expected_improvement(mean, sigma, best)
                scored.append((score, index, mean, (low_q, high_q)))

            score, index, mean, (low_q, high_q) = max(
                scored, key=lambda item: (item[0], -item[1])
            )
            taken.add(index)
            comp = pool_comps[index]
            in_domain = (
                campaign_domain.novelty(comp)["in_domain"]
                if campaign_domain is not None
                else None
            )
            chosen.append(
                Suggestion(
                    composition=comp,
                    mean=sign * mean,
                    interval=(
                        (sign * low_q, sign * high_q)
                        if sign > 0
                        else (sign * high_q, sign * low_q)
                    ),
                    in_domain=in_domain,
                    acquisition=score,
                    strategy=strategy,
                )
            )
            # Believer step: pretend the pick came back at its predicted
            # mean so the next pick spreads out instead of clustering.
            # mean is in signed space; sign * mean recovers the raw value
            # for either direction because sign is +-1.
            X_now.append(list(pool_vectors[index]))
            y_now.append(sign * mean)

        return chosen


def _expected_improvement(mean: float, sigma: float, best: float) -> float:
    if sigma <= 0.0:
        return max(0.0, mean - best)
    z = (mean - best) / sigma
    cdf = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    pdf = math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)
    return (mean - best) * cdf + sigma * pdf


__all__ = ["COLD_START_FLOOR", "Campaign", "ColdStartError", "Suggestion"]
