"""Deterministic constrained composition search over a simplex lattice.

Answers "what should I make" as a screening aid: enumerate element
subsets of a palette, walk a fixed-step composition lattice inside
each, filter by constraints, and return the Pareto front of the
objectives with a full receipt on every candidate (descriptors, all
nine rule verdicts, property predictions with intervals, novelty,
domain flag and the predicted phase). Exhaustive enumeration was chosen over a stochastic
optimizer deliberately: it is reproducible by construction, debuggable
row by row, and honest about its budget, refusing loudly when the
lattice exceeds ``max_evaluations`` instead of sampling silently.

The front is only as good as the property models under it, which for
tier B carry wide honest intervals; treat results as prioritization
for synthesis, not answers. Because optimizers exploit model error
where data runs out, the domain constraint is ON by default and
``optimize_bound="lower"`` ranks tier B objectives by the conservative
end of their intervals instead of the point prediction.
"""

from __future__ import annotations

import dataclasses
import json
import math
from dataclasses import dataclass, field
from itertools import combinations

from .. import __version__
from .._json import json_safe
from ..composition import Composition
from ..descriptors.backend import NativeBackend, scorable_elements
from ..rules import VERDICT_FUNCTIONS, canonical_rule_name
from .constraints import (
    CompositionConstraint,
    DomainConstraint,
    Maximize,
    Minimize,
    PropertyConstraint,
    RuleConstraint,
)

#: The prediction fields a design receipt carries: the compact subset of
#: ``PropertyPrediction.to_dict()`` (the MCP predict_properties payload
#: is the full set).
_RECEIPT_PROPERTY_KEYS = (
    "value", "unit", "interval", "alpha", "tier", "in_domain",
    "n_training", "warnings",
)


def _rule_verdict(rule: str, comp: Composition):
    """One canonical rule's verdict for one composition; None if not computable."""
    try:
        return VERDICT_FUNCTIONS[rule](comp)
    except Exception:
        return None


def _predicted_phase(comp: Composition, alpha: float) -> dict | None:
    """The four-class phase prediction set for one returned candidate.

    None without scikit-learn or a built corpus: the search itself does
    not need either when its objectives are tier A properties.
    """
    from ..uncertainty.phase import predict_phase_set

    try:
        result = predict_phase_set(comp, task="phase4", alpha=alpha)
    except (ImportError, FileNotFoundError, ValueError):
        return None
    return {
        "task": "phase4",
        "prediction_set": result["prediction_set"],
        "most_likely": result["most_likely"],
    }


@dataclass(frozen=True)
class Candidate:
    """One Pareto-front member with its complete receipt."""

    composition: Composition
    descriptors: dict
    rules: dict
    properties: dict
    novelty: dict | None
    in_domain: bool | None
    objective_values: dict
    phase: dict | None = None

    def to_dict(self) -> dict:
        properties = {}
        for name, prediction in self.properties.items():
            full = prediction.to_dict()
            properties[name] = {key: full[key] for key in _RECEIPT_PROPERTY_KEYS}
        return {
            "composition": dict(self.composition),
            "descriptors": {name: json_safe(v) for name, v in self.descriptors.items()},
            "rules": dict(self.rules),
            "properties": properties,
            "novelty": self.novelty,
            "in_domain": self.in_domain,
            "objective_values": {
                name: json_safe(v) for name, v in self.objective_values.items()
            },
            "phase": self.phase,
        }


@dataclass(frozen=True)
class ParetoResult:
    """The front plus everything needed to reproduce it."""

    candidates: tuple[Candidate, ...]
    seed: int
    settings: dict = field(repr=False)
    n_evaluated: int
    n_feasible: int
    n_front: int

    def to_dict(self) -> dict:
        return {
            "seed": self.seed,
            "settings": self.settings,
            "n_evaluated": self.n_evaluated,
            "n_feasible": self.n_feasible,
            "n_front": self.n_front,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def _lattice(units: int, k: int):
    """All k-tuples of positive ints summing to units, lexicographic."""
    if k == 1:
        yield (units,)
        return
    for first in range(1, units - k + 2):
        for rest in _lattice(units - first, k - 1):
            yield (first, *rest)


def _validate_step(step: float) -> int:
    """Turn a lattice step into integer units, or raise the shared error."""
    units = round(1.0 / step)
    if abs(units * step - 1.0) > 1e-9 or units < 2:
        raise ValueError(
            f"step must divide 1 exactly (got {step!r}); try 0.05, 0.1, 0.2, 0.25"
        )
    return units


def _within_bounds(comp: Composition, bounds: dict) -> bool:
    """Every present or bounded element inside its [min, max] window."""
    return all(
        bounds.get(el, (0.0, 1.0))[0] - 1e-9
        <= comp.get(el, 0.0)
        <= bounds.get(el, (0.0, 1.0))[1] + 1e-9
        for el in set(comp) | set(bounds)
    )


def passes_property_constraints(predictions: dict, property_constraints) -> bool:
    """True when every PropertyConstraint holds for these predictions.

    ``bound`` picks what is compared for a fitted property: the point
    prediction, or the lower or upper end of its interval. Tier A
    properties have no interval and always compare the value.
    """
    for constraint in property_constraints:
        prediction = predictions[constraint.prop]
        if prediction.interval is not None and constraint.bound == "lower":
            compared = prediction.interval[0]
        elif prediction.interval is not None and constraint.bound == "upper":
            compared = prediction.interval[1]
        else:
            compared = prediction.value
        if constraint.min is not None and compared < constraint.min - 1e-9:
            return False
        if constraint.max is not None and compared > constraint.max + 1e-9:
            return False
    return True


def _lattice_compositions(palette, low: int, high: int, units: int):
    """Every composition on the step lattice, by subset size then order.

    The deterministic enumeration both the search and the campaign pool
    walk: element subsets of ``palette`` of size ``low``..``high``
    (clamped to the palette size), each filled with the positive integer
    lattice points summing to ``units``.
    """
    for k in range(low, min(high, len(palette)) + 1):
        for subset in combinations(palette, k):
            for point in _lattice(units, k):
                yield {el: n / units for el, n in zip(subset, point)}


def search(
    elements,
    n_elements: tuple[int, int] = (3, 5),
    constraints: tuple = (),
    objectives: tuple = (),
    *,
    n_candidates: int = 50,
    seed: int = 0,
    step: float = 0.05,
    max_evaluations: int = 200_000,
    optimize_bound: str = "point",
    alpha: float = 0.1,
) -> ParetoResult:
    """Screen a palette and return the Pareto front with receipts.

    Parameters
    ----------
    elements
        The palette to draw from. Every element must be covered by the
        descriptor tables (typed error otherwise).
    n_elements
        Inclusive range of subset sizes.
    constraints
        Tuple of constraint objects from
        :mod:`hea_bench.design.constraints`. A
        ``DomainConstraint(in_domain=True)`` is added automatically
        unless a DomainConstraint is already present; pass
        ``DomainConstraint(in_domain=None)`` to opt out explicitly.
    objectives
        ``Maximize``/``Minimize`` over property names. With no
        objectives the result is the feasible set (first
        ``n_candidates`` in deterministic order).
    n_candidates
        Cap on returned candidates. The full front size is reported as
        ``n_front`` so truncation is visible, never silent.
    seed
        Recorded in the result for provenance. The lattice enumeration
        is deterministic and consumes no randomness; the parameter
        exists so future stochastic refinement stays reproducible.
    step
        Lattice resolution in mole fraction; 1/step must be an integer.
    max_evaluations
        Hard budget on lattice points. Exceeding it raises with
        guidance (larger step, smaller palette) rather than sampling
        silently.
    optimize_bound
        ``"point"`` ranks tier B objectives by the point prediction,
        ``"lower"`` by the conservative end of the conformal interval
        (the optimizer-exploits-error mitigation). Tier A objectives
        have no interval and always use the value.
    alpha
        Miscoverage level for the tier B intervals in the receipts.

    Raises
    ------
    ValueError
        Uncovered palette elements, a step that does not divide 1, a
        lattice over budget, unknown objective or constraint names.
    RuntimeError
        A domain constraint was requested but no corpus is built.
    """
    from ..properties import (
        PropertyUnavailableError,
        available_properties,
        predict_property_batch,
    )
    from ..uncertainty import default_domain

    palette = sorted(dict.fromkeys(elements))
    if len(palette) < 2:
        raise ValueError("palette needs at least two elements")
    backend = NativeBackend()
    covered = scorable_elements()
    missing = [element for element in palette if element not in covered]
    if missing:
        raise ValueError(
            f"palette elements not covered by the descriptor tables: "
            f"{', '.join(missing)}"
        )

    units = _validate_step(step)

    low, high = n_elements
    if not 1 <= low <= high <= len(palette):
        raise ValueError(
            f"n_elements range {n_elements!r} is inconsistent with a "
            f"{len(palette)}-element palette"
        )

    known_properties = available_properties()
    objective_specs: list[tuple[str, bool]] = []
    for objective in objectives:
        if isinstance(objective, Maximize):
            objective_specs.append((objective.name, True))
        elif isinstance(objective, Minimize):
            objective_specs.append((objective.name, False))
        else:
            raise ValueError(f"objectives must be Maximize/Minimize, got {objective!r}")
        name = objective_specs[-1][0]
        if name not in known_properties:
            raise ValueError(
                f"unknown objective property {name!r}; available: {sorted(known_properties)}"
            )
    if optimize_bound not in ("point", "lower"):
        raise ValueError(f"optimize_bound must be 'point' or 'lower', got {optimize_bound!r}")

    domain_constraints = [c for c in constraints if isinstance(c, DomainConstraint)]
    if not domain_constraints:
        constraints = (*constraints, DomainConstraint(in_domain=True))
        domain_constraints = [constraints[-1]]
    domain_required = domain_constraints[0].in_domain

    rule_constraints = [c for c in constraints if isinstance(c, RuleConstraint)]
    for constraint in rule_constraints:
        if canonical_rule_name(constraint.rule) not in VERDICT_FUNCTIONS:
            raise ValueError(
                f"unknown rule {constraint.rule!r}; available: {sorted(VERDICT_FUNCTIONS)}"
            )
    property_constraints = [c for c in constraints if isinstance(c, PropertyConstraint)]
    for constraint in property_constraints:
        if constraint.prop not in known_properties:
            raise ValueError(f"unknown constraint property {constraint.prop!r}")
    bounds = {c.element: (c.min, c.max) for c in constraints if isinstance(c, CompositionConstraint)}

    needed_properties = sorted(
        {name for name, _ in objective_specs} | {c.prop for c in property_constraints}
    )

    total = sum(
        math.comb(len(palette), k) * math.comb(units - 1, k - 1)
        for k in range(low, high + 1)
    )
    if total > max_evaluations:
        raise ValueError(
            f"the lattice has {total} points, over the max_evaluations budget "
            f"of {max_evaluations}. Increase step, narrow n_elements, shrink "
            f"the palette, or raise the budget deliberately; the search never "
            f"samples silently."
        )

    domain = default_domain()
    if domain_required is not None and domain is None:
        raise RuntimeError(
            "the domain constraint needs the corpus-fitted domain model, and "
            "no corpus is built in this environment. Build it (see the corpus "
            "card) or opt out explicitly with DomainConstraint(in_domain=None)."
        )

    # Filters run cheapest-first (bounds, then only the constrained
    # rules, then the domain flag, then fitted properties); the full
    # receipt, every rule verdict plus all descriptors, is computed only
    # for candidates that survive them all. The surviving set is
    # identical to filtering in any other order.
    constrained_rules = tuple(
        dict.fromkeys(canonical_rule_name(c.rule) for c in rule_constraints)
    )
    n_evaluated = 0
    survivors: list[tuple[Composition, dict, dict | None, bool | None]] = []
    for comp in _lattice_compositions(palette, low, high, units):
        n_evaluated += 1
        if not _within_bounds(comp, bounds):
            continue

        verdicts = {name: _rule_verdict(name, comp) for name in constrained_rules}
        if not all(
            c.matches(verdicts[canonical_rule_name(c.rule)]) for c in rule_constraints
        ):
            continue

        novelty = domain.novelty(comp) if domain is not None else None
        in_domain = novelty["in_domain"] if novelty is not None else None
        if domain_required is not None and in_domain != domain_required:
            continue
        survivors.append((comp, verdicts, novelty, in_domain))

    # Properties for every survivor at once: a fitted model scores the
    # whole batch in one call instead of one call per lattice point,
    # with identical numbers (see predict_property_batch).
    batches = {
        name: predict_property_batch([entry[0] for entry in survivors], name, alpha=alpha)
        for name in needed_properties
    }

    feasible: list[Candidate] = []
    for position, (comp, verdicts, novelty, in_domain) in enumerate(survivors):
        predictions = {name: batches[name][position] for name in needed_properties}
        if any(isinstance(p, PropertyUnavailableError) for p in predictions.values()):
            continue
        if not passes_property_constraints(predictions, property_constraints):
            continue

        objective_values = {}
        for name, maximize in objective_specs:
            prediction = predictions[name]
            if prediction.interval is not None and optimize_bound == "lower":
                value = prediction.interval[0] if maximize else prediction.interval[1]
            else:
                value = prediction.value
            objective_values[name] = value

        feasible.append(
            Candidate(
                composition=comp,
                descriptors=backend.compute(comp),
                rules={
                    name: (
                        verdicts[name]
                        if name in verdicts
                        else _rule_verdict(name, comp)
                    )
                    for name in VERDICT_FUNCTIONS
                },
                properties=predictions,
                novelty=novelty,
                in_domain=in_domain,
                objective_values=objective_values,
            )
        )

    def minimized(candidate: Candidate) -> tuple:
        out = []
        for name, maximize in objective_specs:
            value = candidate.objective_values[name]
            out.append(-value if maximize else value)
        return tuple(out)

    if objective_specs:
        # Simple cull against the running front instead of all pairs.
        # Equal vectors never dominate each other, so exact ties are all
        # kept; the surviving set is the same non-dominated set the
        # all-pairs comparison produced.
        front_pairs: list[tuple[Candidate, tuple]] = []
        for candidate in feasible:
            vector = minimized(candidate)
            if any(
                all(o <= v for o, v in zip(other, vector)) and other != vector
                for _c, other in front_pairs
            ):
                continue
            front_pairs = [
                (c, other)
                for c, other in front_pairs
                if not (all(v <= o for v, o in zip(vector, other)) and vector != other)
            ]
            front_pairs.append((candidate, vector))
        front = [candidate for candidate, _vector in front_pairs]
    else:
        front = list(feasible)

    def sort_key(candidate: Candidate):
        return (
            minimized(candidate),
            tuple(sorted(candidate.composition.items())),
        )

    front.sort(key=sort_key)
    settings = {
        "palette": palette,
        "n_elements": list(n_elements),
        "step": step,
        "objectives": [
            ("maximize" if maximize else "minimize", name) for name, maximize in objective_specs
        ],
        "constraints": [repr(c) for c in constraints],
        "optimize_bound": optimize_bound,
        "alpha": alpha,
        "max_evaluations": max_evaluations,
        "n_candidates": n_candidates,
        "hea_bench_version": __version__,
    }
    # The phase model runs only on what is returned, so it costs a few
    # predictions, not one per lattice point.
    shown = tuple(
        dataclasses.replace(candidate, phase=_predicted_phase(candidate.composition, alpha))
        for candidate in front[:n_candidates]
    )
    return ParetoResult(
        candidates=shown,
        seed=seed,
        settings=settings,
        n_evaluated=n_evaluated,
        n_feasible=len(feasible),
        n_front=len(front),
    )


__all__ = ["Candidate", "ParetoResult", "search"]
