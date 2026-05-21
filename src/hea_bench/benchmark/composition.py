"""Re-export of composition primitives from the package root.

`composition.py` was originally defined here; it moved to the package
root so descriptor modules can consume it without depending on the
benchmark subpackage. This shim preserves the historical import path
for any external code that grew to depend on it.
"""

from ..composition import (
    Composition,
    from_element_columns,
    normalize,
    parse_formula,
)

__all__ = ["Composition", "from_element_columns", "normalize", "parse_formula"]
