"""The import rules of ARCHITECTURE.md, enforced on every module of hea_bench.

Read ARCHITECTURE.md before adding code. This test parses every module
under src/hea_bench (nothing is imported or run) and checks each import,
including the ones inside functions, against the six rules there. Each
failure names the module, the line, the import and the fix.

A new module lands in the layer of the longest prefix in LAYERS that
matches its name. A new top-level module or package needs its own entry,
and the test says so.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "hea_bench"

#: Layer -> module-name prefixes, in the order of the table in ARCHITECTURE.md.
#: A layer may import only from its own layer and the layers above it.
LAYERS = {
    0: ("hea_bench.constants", "hea_bench._overrides", "hea_bench._paths", "hea_bench._json",
        "hea_bench.descriptors.data", "hea_bench.oxides._data", "hea_bench.properties.data"),
    1: ("hea_bench.composition", "hea_bench.custom", "hea_bench.descriptors",
        "hea_bench.rules", "hea_bench.oxides", "hea_bench.ceramics", "hea_bench.properties.tier_a"),
    2: ("hea_bench.benchmark", "hea_bench.corpus", "hea_bench.uncertainty", "hea_bench.properties",
        "hea_bench.design", "hea_bench._model_cache"),
    3: ("hea_bench.service",),
    4: ("hea_bench.mcp_server", "hea_bench.webapp", "hea_bench.cli"),
}
LAYER_NAMES = {0: "foundation", 1: "core", 2: "analysis", 3: "service", 4: "interfaces"}
INTERFACES = set(LAYERS[4])
#: Rule 2's one exception: the optional HEACalculator adapter.
THIRD_PARTY_ALLOWED = {("hea_bench.descriptors.backend", "HEACalculator")}
#: Rule 4: underscore modules that are shared on purpose.
SHARED_UNDERSCORE = {"_paths", "_json", "_overrides", "_model_cache", "_tables", "_payload"}
#: Rule 5: the corpus builder and the reader it must not import.
BUILDER = ("hea_bench.benchmark.consolidate", "hea_bench.benchmark.loaders")
READER = "hea_bench.corpus"


def _module_name(path: Path) -> str:
    parts = list(path.relative_to(PACKAGE.parent).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


MODULES = {_module_name(path): path for path in sorted(PACKAGE.rglob("*.py"))}
PACKAGES = {name for name, path in MODULES.items() if path.name == "__init__.py"}


def _layer(module: str) -> int | None:
    if module == "hea_bench":  # the package root re-exports the core names
        return 1
    best = None
    for layer, prefixes in LAYERS.items():
        for prefix in prefixes:
            if module == prefix or module.startswith(prefix + "."):
                if best is None or len(prefix) > len(best[1]):
                    best = (layer, prefix)
    return best[0] if best else None


def _resolve(module: str, node: ast.ImportFrom) -> str:
    if not node.level:
        return node.module or ""
    base = module.split(".") if module in PACKAGES else module.split(".")[:-1]
    base = base[: len(base) - (node.level - 1)]
    return ".".join(base + ([node.module] if node.module else []))


def _imports(module: str):
    """(line, imported module, imported name or None) for every import in ``module``."""
    tree = ast.parse(MODULES[module].read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name, None
        elif isinstance(node, ast.ImportFrom):
            source = _resolve(module, node)
            for alias in node.names:
                submodule = f"{source}.{alias.name}"
                if submodule in MODULES:
                    yield node.lineno, submodule, None
                else:
                    yield node.lineno, source, alias.name


def _internal(target: str) -> str | None:
    """The hea_bench module an import lands in, or None for a third-party or stdlib one."""
    while target and target not in MODULES:
        target = target.rpartition(".")[0]
    return target or None


def _package_of(module: str) -> str:
    return module if module in PACKAGES else module.rpartition(".")[0]


EDGES = {
    module: [(line, target, name, _internal(target)) for line, target, name in _imports(module)]
    for module in MODULES
}


def test_every_module_has_a_layer() -> None:
    missing = sorted(module for module in MODULES if _layer(module) is None)
    assert not missing, (
        f"modules with no layer: {missing}. Fix: add each to LAYERS in tests/test_architecture.py "
        "and to the layer table in ARCHITECTURE.md, after deciding which layer it belongs to."
    )


def test_layers_import_only_from_their_own_layer_or_above() -> None:
    problems = []
    for module, edges in EDGES.items():
        mine = _layer(module)
        for line, _target, _name, internal in edges:
            if internal is None or internal == module:
                continue
            theirs = _layer(internal)
            if theirs is not None and theirs > mine:
                problems.append(
                    f"{MODULES[module].relative_to(ROOT)}:{line}: {LAYER_NAMES[mine]} module {module} "
                    f"imports {internal}, which is {LAYER_NAMES[theirs]}. Fix: move the code that "
                    f"needs it up to layer {theirs}, or move what it uses down to layer {mine}."
                )
    assert not problems, "\n".join(problems)


def test_foundation_and_core_use_only_the_standard_library() -> None:
    stdlib = set(sys.stdlib_module_names)
    problems = []
    for module, edges in EDGES.items():
        if _layer(module) not in (0, 1):
            continue
        for line, target, _name, internal in edges:
            top = target.split(".")[0]
            if internal is None and top not in stdlib and (module, top) not in THIRD_PARTY_ALLOWED:
                problems.append(
                    f"{MODULES[module].relative_to(ROOT)}:{line}: {module} imports {target}. The "
                    "core is dependency-free (pyproject dependencies = []). Fix: move the code "
                    "that needs it to the analysis layer and import it inside a function there."
                )
    assert not problems, "\n".join(problems)


def test_interfaces_never_import_each_other() -> None:
    problems = []
    for module in INTERFACES:
        for line, _target, _name, internal in EDGES[module]:
            if internal in INTERFACES and internal != module:
                problems.append(
                    f"{MODULES[module].relative_to(ROOT)}:{line}: {module} imports {internal}. "
                    "Fix: move what both need into hea_bench.service and call it from both."
                )
    assert not problems, "\n".join(problems)


def test_no_private_name_crosses_a_package() -> None:
    problems = []
    for module, edges in EDGES.items():
        for line, target, name, internal in edges:
            if internal is None or _package_of(internal) == _package_of(module):
                continue
            private = name if name is not None else internal.rpartition(".")[2]
            if private.startswith("_") and not private.startswith("__") and private not in SHARED_UNDERSCORE:
                problems.append(
                    f"{MODULES[module].relative_to(ROOT)}:{line}: {module} imports {private} from "
                    f"{target}. Fix: give it a public name in its own module first."
                )
    assert not problems, "\n".join(problems)


def test_the_corpus_builder_never_imports_the_reader() -> None:
    problems = []
    for module, edges in EDGES.items():
        if not module.startswith(BUILDER):
            continue
        for line, _target, _name, internal in edges:
            if internal is not None and (internal == READER or internal.startswith(READER + ".")):
                problems.append(
                    f"{MODULES[module].relative_to(ROOT)}:{line}: {module} imports {internal}. "
                    "Fix: put what both need in hea_bench._paths, as SOURCE_COLUMN_PREFIX is."
                )
    assert not problems, "\n".join(problems)


def test_no_import_cycle_crosses_a_package() -> None:
    graph = {
        module: {internal for _line, _target, _name, internal in edges if internal and internal != module}
        for module, edges in EDGES.items()
    }
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    cycles: list[list[str]] = []

    def visit(node: str) -> None:
        index[node] = low[node] = len(index)
        stack.append(node)
        on_stack.add(node)
        for other in graph[node]:
            if other not in index:
                visit(other)
                low[node] = min(low[node], low[other])
            elif other in on_stack:
                low[node] = min(low[node], index[other])
        if low[node] == index[node]:
            component = []
            while True:
                member = stack.pop()
                on_stack.discard(member)
                component.append(member)
                if member == node:
                    break
            if len({_package_of(member) for member in component}) > 1:
                cycles.append(sorted(component))

    for node in graph:
        if node not in index:
            visit(node)
    assert not cycles, (
        f"import cycles across packages, lazy imports included: {cycles}. Fix: move the shared "
        "piece to the lower layer both can import, as hea_bench._paths does for the corpus."
    )
