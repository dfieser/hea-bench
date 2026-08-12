"""Deterministic constrained composition search over a simplex lattice.

Answers "what should I make" as a screening aid: enumerate element
subsets of a palette, walk a fixed-step composition lattice inside
each, filter by constraints, and return the Pareto front of the
objectives with a full receipt on every candidate (descriptors, all
nine rule verdicts, property predictions with intervals, novelty and
domain flag). Exhaustive enumeration was chosen over a stochastic
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

import json
import math
from dataclasses import dataclass, field
from itertools import combinations

from .. import __version__
from ..composition import Composition
from ..descriptors.backend import NativeBackend
from ..rules import (
    guo_vec,
    king_phi,
    senkov_kappa,
    sheikh_ductility,
    tsai_sigma,
    yang_omega,
    ye_phi,
    yeh_smix,
    zhang_delta,
)
from .constraints import (
    CompositionConstraint,
    DomainConstraint,
    Maximize,
    Minimize,
    PropertyConstraint,
    RuleConstraint,
)

_RULES = {
    "yeh_smix": lambda comp: yeh_smix.predict(comp),
    "zhang_delta": lambda comp: zhang_delta.predict(comp),
    "guo_vec": lambda comp: guo_vec.predict(comp),
    "yang_omega": lambda comp: yang_omega.predict(comp),
    "king_phi": lambda comp: king_phi.predict(comp),
    "ye_phi": lambda comp: ye_phi.predict(comp),
    "senkov_kappa": lambda comp: senkov_kappa.predict(comp).verdict,
    "tsai_sigma": lambda comp: tsai_sigma.predict(comp).verdict,
    "sheikh_ductility": lambda comp: sheikh_ductility.predict(comp).verdict,
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

    def to_dict(self) -> dict:
        def clean(value):
            if isinstance(value, float) and not math.isfinite(value):
                return None
            return value

        properties = {}
        for name, prediction in self.properties.items():
            properties[name] = {
                "value": clean(prediction.value),
                "unit": prediction.unit,
                "interval": (
                    [clean(prediction.interval[0]), clean(prediction.interval[1])]
                    if prediction.interval is not None
                    else None
                ),
                "alpha": prediction.alpha,
                "tier": prediction.tier,
                "in_domain": prediction.in_domain,
                "n_training": prediction.n_training,
                "warnings": list(prediction.warnings),
            }
        return {
            "composition": dict(self.composition),
            "descriptors": {name: clean(v) for name, v in self.descriptors.items()},
            "rules": dict(self.rules),
            "properties": properties,
            "novelty": self.novelty,
            "in_domain": self.in_domain,
            "objective_values": {name: clean(v) for name, v in self.objective_values.items()},
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

    def to_json(self) -> str:
        return json.dumps(
            {
                "seed": self.seed,
                "settings": self.settings,
                "n_evaluated": self.n_evaluated,
                "n_feasible": self.n_feasible,
                "n_front": self.n_front,
                "candidates": [candidate.to_dict() for candidate in self.candidates],
            },
            indent=2,
        )


def _lattice(units: int, k: int):
    """All k-tuples of positive ints summing to units, lexicographic."""
    if k == 1:
        yield (units,)
        return
    for first in range(1, units - k + 2):
        for rest in _lattice(units - first, k - 1):
            yield (first, *rest)


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
    from ..properties import PropertyUnavailableError, available_properties, predict_property
    from ..uncertainty import default_domain

    palette = sorted(dict.fromkeys(elements))
    if len(palette) < 2:
        raise ValueError("palette needs at least two elements")
    backend = NativeBackend()
    from ..descriptors.data.elemental import covered_elements as _elemental
    from ..descriptors.data.pair_enthalpies import covered_elements as _pairs

    covered = _elemental() & _pairs()
    missing = [element for element in palette if element not in covered]
    if missing:
        raise ValueError(
            f"palette elements not covered by the descriptor tables: "
            f"{', '.join(missing)}"
        )

    units = round(1.0 / step)
    if abs(units * step - 1.0) > 1e-9 or units < 2:
        raise ValueError(f"step must divide 1 exactly (got {step!r}); try 0.05, 0.1, 0.2, 0.25")

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
        if constraint.rule not in _RULES:
            raise ValueError(
                f"unknown rule {constraint.rule!r}; available: {sorted(_RULES)}"
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

    n_evaluated = 0
    feasible: list[Candidate] = []
    for k in range(low, high + 1):
        for subset in combinations(palette, k):
            for point in _lattice(units, k):
                n_evaluated += 1
                comp = {el: n / units for el, n in zip(subset, point)}
                if any(
                    not bounds.get(el, (0.0, 1.0))[0] - 1e-9
                    <= comp.get(el, 0.0)
                    <= bounds.get(el, (0.0, 1.0))[1] + 1e-9
                    for el in set(comp) | set(bounds)
                ):
                    continue

                verdicts = {}
                for name, rule in _RULES.items():
                    try:
                        verdicts[name] = rule(comp)
                    except Exception:
                        verdicts[name] = None
                if not all(c.matches(verdicts[c.rule]) for c in rule_constraints):
                    continue

                predictions = {}
                unavailable = False
                for name in needed_properties:
                    try:
                        predictions[name] = predict_property(comp, name, alpha=alpha)
                    except PropertyUnavailableError:
                        unavailable = True
                        break
                if unavailable:
                    continue

                ok = True
                for constraint in property_constraints:
                    prediction = predictions[constraint.prop]
                    if prediction.interval is not None and constraint.bound == "lower":
                        compared = prediction.interval[0]
                    elif prediction.interval is not None and constraint.bound == "upper":
                        compared = prediction.interval[1]
                    else:
                        compared = prediction.value
                    if constraint.min is not None and compared < constraint.min - 1e-9:
                        ok = False
                    if constraint.max is not None and compared > constraint.max + 1e-9:
                        ok = False
                if not ok:
                    continue

                novelty = domain.novelty(comp) if domain is not None else None
                in_domain = novelty["in_domain"] if novelty is not None else None
                if domain_required is not None and in_domain != domain_required:
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
                        rules=verdicts,
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
        vectors = [minimized(candidate) for candidate in feasible]
        front = [
            candidate
            for candidate, vector in zip(feasible, vectors)
            if not any(
                all(o <= v for o, v in zip(other, vector)) and other != vector
                for other in vectors
            )
        ]
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
    return ParetoResult(
        candidates=tuple(front[:n_candidates]),
        seed=seed,
        settings=settings,
        n_evaluated=n_evaluated,
        n_feasible=len(feasible),
        n_front=len(front),
    )


__all__ = ["Candidate", "ParetoResult", "search"]
