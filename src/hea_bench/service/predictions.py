"""Property estimates, the domain flag and phase sets, as the surfaces serve them.

The MCP tools take batches of formula strings and name the corpus tools
in their errors. The app's engine takes one composition, as a formula or
a mole-fraction dict, and reports progress while a model fits.
"""

from __future__ import annotations

from ._payload import needs_corpus, parse, read_composition, say


def predict_properties(
    compositions: list[str],
    properties: list[str] | None = None,
    alpha: float = 0.1,
    processing: str | None = None,
) -> dict:
    """Every requested property for a batch of compositions (MCP)."""
    from ..properties import (
        PropertyUnavailableError,
        available_properties,
        predict_property,
    )

    known = available_properties()
    wanted = properties or sorted(known)
    for name in wanted:
        if name not in known:
            raise ValueError(
                f"unknown property {name!r}: expected one of {sorted(known)}"
            )

    results = []
    for formula in compositions:
        comp = parse(formula)
        entry: dict = {"input": formula, "composition": comp, "properties": {}}
        for name in wanted:
            try:
                prediction = predict_property(comp, name, alpha=alpha, processing=processing)
            except PropertyUnavailableError as exc:
                raise ValueError(str(exc)) from None
            entry["properties"][name] = prediction.to_dict()
        results.append(entry)
    return {"results": results}


def check_applicability(composition: str) -> dict:
    """The corpus domain flag for one formula, on the default domain (MCP)."""
    from ..uncertainty import default_domain

    comp = parse(composition)
    domain = default_domain()
    if domain is None:
        raise ValueError(
            "the corpus is not built on this machine, so applicability cannot be "
            "assessed. Call the corpus_build tool once, then try again."
        )
    payload = domain.novelty(comp)
    payload["input"] = composition
    payload["corpus_version"] = domain.corpus_version
    return payload


def predict_phase_set(
    compositions: list[str],
    task: str = "single_vs_multi",
    alpha: float = 0.1,
    version: str = "0.1.0",
) -> dict:
    """Conformal phase sets for a batch, with per-entry errors (MCP)."""
    from ..benchmark.corpus import TASKS
    from ..uncertainty.phase import predict_phase_set as predict

    if task not in TASKS:
        raise ValueError(f"unknown task {task!r}: expected one of {sorted(TASKS)}")
    results = []
    for formula in compositions:
        comp = parse(formula)
        try:
            entry = predict(comp, task=task, alpha=alpha, version=version)
        except FileNotFoundError as exc:
            raise needs_corpus(exc) from None
        except ImportError:
            raise ValueError('phase prediction needs scikit-learn: pip install "hea-bench[mcp]"') from None
        except ValueError as exc:
            entry = {"error": str(exc)}
        results.append({"input": formula, "composition": comp, **entry})
    return {"task": task, "alpha": alpha, "corpus_version": version, "results": results}


def properties(
    composition, alpha: float = 0.1, processing: str | None = None, names: list | None = None
) -> dict:
    """Every property for one composition. A property that cannot be
    computed carries its reason instead of hiding the others."""
    from ..properties import (
        PropertyUnavailableError,
        available_properties,
        cost_breakdown,
        predict_property,
    )

    comp = read_composition(composition)
    results: dict = {}
    for name in names or sorted(available_properties()):
        try:
            processing_arg = processing if name == "hardness" else None
            results[name] = predict_property(
                comp, name, alpha=alpha, processing=processing_arg
            ).to_dict()
        except PropertyUnavailableError as error:
            results[name] = {"error": str(error)}
    try:
        breakdown = cost_breakdown(comp)
    except ValueError:
        breakdown = None
    return {
        "composition": comp,
        "properties": results,
        "cost_breakdown": breakdown,
    }


def applicability(composition, version: str = "0.1.0") -> dict:
    """The corpus domain flag and its novelty components."""
    from ..uncertainty.phase import corpus_domain

    comp = read_composition(composition)
    payload = dict(corpus_domain(version).novelty(comp))
    payload["composition"] = comp
    payload["corpus_version"] = version
    return payload


def phase_prediction(
    composition,
    task: str = "single_vs_multi",
    alpha: float = 0.1,
    version: str = "0.1.0",
    progress=None,
) -> dict:
    """Conformal phase prediction set for one composition."""
    from ..uncertainty.phase import predict_phase_set

    say(progress, "fitting the phase model (first call per task only)", 0.2)
    return predict_phase_set(read_composition(composition), task=task, alpha=alpha, version=version)
