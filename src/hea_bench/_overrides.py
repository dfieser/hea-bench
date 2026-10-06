"""Context-local custom element data and pair enthalpies.

Set only by :func:`hea_bench.custom.custom_data`; read by the element
table, the pair-enthalpy table and the formula parser. A leaf module
with no package imports, so those low-level modules can all read it
without import cycles. Context variables keep concurrent callers
(threads, asyncio tasks, the MCP server) from seeing each other's
overrides.
"""

from __future__ import annotations

from contextvars import ContextVar

#: label -> ElementProperties for custom elements, or None.
ELEMENTS: ContextVar[dict | None] = ContextVar("hea_bench_custom_elements", default=None)

#: frozenset({a, b}) -> pair enthalpy in kJ/mol, or None.
PAIRS: ContextVar[dict | None] = ContextVar("hea_bench_custom_pairs", default=None)


def custom_labels() -> frozenset[str]:
    """Labels of the custom elements active in this context."""
    return frozenset(ELEMENTS.get() or ())
