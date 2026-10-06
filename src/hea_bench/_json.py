"""Strict-JSON value hygiene shared by every JSON-emitting surface."""

from __future__ import annotations

import math


def json_safe(value):
    """Return ``value`` unless it is a non-finite float, then ``None``.

    JSON has no representation for infinity or NaN, and emitting a bare
    ``Infinity`` token (which ``json.dumps`` does by default) produces
    output that strict parsers and MCP clients reject. Divergent
    descriptor values (singh_lambda at delta = 0, the King Phi proxy
    when no binary intermetallic competes) are therefore nulled at the
    serialization boundary; the caller decides whether to attach a
    warning explaining the divergence.
    """
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def strict_json(value):
    """:func:`json_safe` applied all the way down: a strict-JSON copy.

    Non-finite floats become None, tuples become lists and keys become
    strings, so any payload serializes with ``allow_nan=False``.
    """
    if isinstance(value, float):
        return json_safe(value)
    if isinstance(value, dict):
        return {str(key): strict_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [strict_json(item) for item in value]
    return value
