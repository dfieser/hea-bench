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
