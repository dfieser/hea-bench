"""The composition search and campaign suggestions, as the surfaces serve them.

The MCP tools and the app's Design tab both call these, under the same
caps, so the two return the same candidates and the same suggestions.
"""

from __future__ import annotations

from .._json import json_safe
from ._payload import (
    CAMPAIGN_MAX_BATCH,
    DESIGN_BUDGET,
    DESIGN_MAX_CANDIDATES,
    DESIGN_MAX_PALETTE,
    DESIGN_MIN_STEP,
    read_composition,
    say,
    stamp,
)


def design_search(
    elements: list[str],
    n_elements_min: int = 3,
    n_elements_max: int = 5,
    step: float = 0.1,
    objectives: list[list[str]] | None = None,
    composition_constraints: list[dict] | None = None,
    rule_constraints: list[dict] | None = None,
    property_constraints: list[dict] | None = None,
    include_out_of_domain: bool = False,
    optimize_bound: str = "lower",
    max_candidates: int = 10,
    alpha: float = 0.1,
) -> dict:
    """The constrained Pareto search from plain values, within the tool caps."""
    from ..design import (
        CompositionConstraint,
        DomainConstraint,
        Maximize,
        Minimize,
        PropertyConstraint,
        RuleConstraint,
        search,
    )

    if len(elements) > DESIGN_MAX_PALETTE:
        raise ValueError(
            f"palette of {len(elements)} exceeds the tool cap of "
            f"{DESIGN_MAX_PALETTE} elements. Screen a narrower palette."
        )
    if max_candidates > DESIGN_MAX_CANDIDATES:
        raise ValueError(
            f"max_candidates {max_candidates} exceeds the tool cap of "
            f"{DESIGN_MAX_CANDIDATES}"
        )
    if step < DESIGN_MIN_STEP:
        raise ValueError(
            f"step {step} is below the tool floor of {DESIGN_MIN_STEP}. "
            f"Finer lattices belong in the Python API with an explicit budget."
        )

    objective_objects = []
    for pair in objectives or []:
        direction, name = pair
        if direction == "maximize":
            objective_objects.append(Maximize(name))
        elif direction == "minimize":
            objective_objects.append(Minimize(name))
        else:
            raise ValueError(f"objective direction must be maximize or minimize, got {direction!r}")

    constraints: list = []
    for entry in composition_constraints or []:
        constraints.append(
            CompositionConstraint(
                entry["element"], min=entry.get("min", 0.0), max=entry.get("max", 1.0)
            )
        )
    for entry in rule_constraints or []:
        satisfied = entry["satisfied"]
        constraints.append(
            RuleConstraint(
                entry["rule"],
                tuple(satisfied) if isinstance(satisfied, list) else satisfied,
            )
        )
    for entry in property_constraints or []:
        constraints.append(
            PropertyConstraint(
                entry["prop"],
                min=entry.get("min"),
                max=entry.get("max"),
                bound=entry.get("bound", "point"),
            )
        )
    if include_out_of_domain:
        constraints.append(DomainConstraint(in_domain=None))

    try:
        result = search(
            elements,
            n_elements=(n_elements_min, n_elements_max),
            constraints=tuple(constraints),
            objectives=tuple(objective_objects),
            n_candidates=max_candidates,
            step=step,
            max_evaluations=DESIGN_BUDGET,
            optimize_bound=optimize_bound,
            alpha=alpha,
        )
    except (RuntimeError, ValueError) as exc:
        raise ValueError(str(exc)) from None

    return result.to_dict()


def check_batch(n: int) -> None:
    if n > CAMPAIGN_MAX_BATCH:
        raise ValueError(f"batch of {n} exceeds the tool cap of {CAMPAIGN_MAX_BATCH}")


def suggestions(campaign, n: int, strategy: str) -> dict:
    """A loaded campaign's next batch, capped, in the tool's payload shape."""
    check_batch(n)
    try:
        suggested = campaign.suggest(n=n, strategy=strategy)
    except (RuntimeError, ValueError) as exc:  # ColdStartError is a RuntimeError
        raise ValueError(str(exc)) from None
    return {
        "objective": campaign.objective,
        "direction": campaign.direction,
        "n_observations": len(campaign.observations),
        "n_informative": campaign.n_informative(),
        "strategy": strategy,
        "suggestions": [
            {
                "composition": dict(s.composition),
                "mean": json_safe(float(s.mean)),
                "interval": [
                    json_safe(float(s.interval[0])),
                    json_safe(float(s.interval[1])),
                ],
                "in_domain": s.in_domain,
                "acquisition": json_safe(float(s.acquisition)),
            }
            for s in suggested
        ],
    }


def suggest_inline(campaign: dict, n: int = 5, strategy: str = "ei", progress=None) -> dict:
    """Next suggestions for a campaign file's contents (schema 1).

    Observation compositions may be formulas, which this function
    normalizes. The response carries the campaign back in canonical
    form, which is what the app saves.
    """
    from ..design.campaign import Campaign

    payload = dict(campaign)
    payload["observations"] = [
        {**obs, "composition": read_composition(obs["composition"])}
        for obs in payload.get("observations", [])
    ]
    loaded = Campaign.from_dict(payload)
    say(progress, "fitting the campaign surrogate", 0.2)
    result = stamp(suggestions(loaded, n, strategy))
    result["campaign"] = loaded.to_dict()
    return result
