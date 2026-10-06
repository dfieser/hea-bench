"""Every library feature must exist and work in the app (owner rule, 2026-10-05).

About 99% of users only open the app: the site built from web/, and the
desktop exe that wraps the same folder. A feature that exists only in the
Python library or the MCP server is unreachable for anyone who does not
code, so it is a defect. tests/data/app_parity.json lists every public
name exactly once: under a feature with app evidence, under "internal"
with the reason no surface is needed, or under "deferred" with the
owner's dated decision. These tests fail when

- a public name is not listed (a new feature with no app surface),
- a listed name no longer exists (a stale entry),
- a feature's evidence is missing: a DOM id not in web/index.html, a
  bridge method that is not registered or that no app code calls, a
  browser-core function that is not exported or that the page never
  uses, or a named test that does not exist,
- a feature that runs in the in-page engine is not used, through its
  UI, by the browser smoke test tests/app_smoke.cjs.

Every failure message names the exact fix.
"""

from __future__ import annotations

import importlib
import json
import pkgutil
import re
from pathlib import Path

import hea_bench
import hea_bench.rules
from hea_bench import mcp_server, webapp

ROOT = Path(__file__).resolve().parents[1]
REL = "tests/data/app_parity.json"
REGISTRY = json.loads((ROOT / REL).read_text(encoding="utf-8"))
WEB = ROOT / "web"
INDEX = (WEB / "index.html").read_text(encoding="utf-8")
FRONT_END = INDEX + (WEB / "hea-features.js").read_text(encoding="utf-8")
WORKER = (WEB / "hea-engine-worker.js").read_text(encoding="utf-8")
CORE = (WEB / "hea-calculator-core.js").read_text(encoding="utf-8")
SMOKE = (ROOT / "tests" / "app_smoke.cjs").read_text(encoding="utf-8")

DOM_IDS = set(re.findall(r'\bid="([^"$]+)"', INDEX))
_EXPORT_BLOCK = CORE[CORE.rindex("    return {\n") :].split("\n    };", 1)[0]
CORE_EXPORTS = set(re.findall(r"^\s+(\w+): \w+,?$", _EXPORT_BLOCK, re.M))
CALLED = set(re.findall(r'call\("(\w+)"', FRONT_END)) | set(re.findall(r'callPython\("(\w+)"', WORKER))


def public_surface() -> list[str]:
    """Every public name a library, MCP or CLI user can reach."""
    keys = [f"hea_bench.{name}" for name in hea_bench.__all__]
    for info in pkgutil.walk_packages(hea_bench.__path__, "hea_bench."):
        if ".data" in info.name or info.name.endswith("__main__"):
            continue
        module = importlib.import_module(info.name)
        parts = info.name.split(".")
        ancestors = [importlib.import_module(".".join(parts[:k])) for k in range(1, len(parts))]
        for name in getattr(module, "__all__", ()):
            obj = getattr(module, name)
            # A re-export is listed once, under the shallowest package exporting it.
            if not any(
                name in getattr(ancestor, "__all__", ()) and getattr(ancestor, name) is obj
                for ancestor in ancestors
            ):
                keys.append(f"{info.name}.{name}")
    keys += [f"mcp:{tool.__name__}" for tool in mcp_server._TOOLS]
    keys += [
        f"rule:{module.name}"
        for module in pkgutil.iter_modules(hea_bench.rules.__path__)
        if not module.name.startswith("_")
    ]
    cli = (ROOT / "src" / "hea_bench" / "cli.py").read_text(encoding="utf-8")
    keys += [f"cli:{name}" for name in re.findall(r'add_parser\(\s*"([\w-]+)"', cli)]
    return keys


def assignments() -> dict[str, list[str]]:
    where: dict[str, list[str]] = {}
    for feature_id, feature in REGISTRY["features"].items():
        for key in feature["covers"]:
            where.setdefault(key, []).append(f"features.{feature_id}")
    for key in REGISTRY["internal"]:
        where.setdefault(key, []).append("internal")
    for deferred_id, item in REGISTRY["deferred"].items():
        for key in item["covers"]:
            where.setdefault(key, []).append(f"deferred.{deferred_id}")
    return where


def test_every_public_name_has_an_app_surface_or_a_reason() -> None:
    missing = [key for key in public_surface() if key not in assignments()]
    assert not missing, (
        f"{len(missing)} public name(s) have no app surface: {missing}.\n"
        "Every library feature must appear AND work in the app (hea-bench/CLAUDE.md, APP PARITY). "
        "Fix: build the feature in web/ (index.html and hea-features.js, through hea_bench.webapp "
        f"when it needs Python), then add the name to that feature's 'covers' list in {REL}. "
        "If the name has no user-facing behavior (a helper or a type), add it to 'internal' "
        "there with the reason instead."
    )


def test_registry_has_no_stale_or_duplicate_entries() -> None:
    surface = set(public_surface())
    where = assignments()
    stale = sorted(key for key in where if key not in surface)
    assert not stale, f"{REL} lists names the library no longer has: {stale}. Fix: delete them there."
    duplicated = {key: places for key, places in where.items() if len(places) > 1}
    assert not duplicated, f"{REL} lists names more than once: {duplicated}. Fix: keep one entry each."


def test_every_feature_has_working_app_evidence() -> None:
    problems = []
    for feature_id, feature in REGISTRY["features"].items():
        app = feature.get("app", {})
        if not app.get("dom"):
            problems.append(f"{feature_id}: no 'dom' ids. Fix: list the ids of the elements a user sees and uses for it.")
        for element_id in app.get("dom", []):
            if element_id not in DOM_IDS:
                problems.append(
                    f'{feature_id}: id="{element_id}" is not in web/index.html. '
                    f"Fix: add the element, or correct the id in {REL}."
                )
        for method in app.get("bridge", []):
            if method not in webapp.METHODS:
                problems.append(
                    f"{feature_id}: bridge method {method!r} is not in hea_bench.webapp.METHODS. Fix: register it there."
                )
            elif method not in CALLED:
                problems.append(
                    f"{feature_id}: no app code calls the bridge method {method!r}. "
                    f'Fix: call it from web/hea-features.js with engine.call("{method}", ...).'
                )
        for name in app.get("core", []):
            if name not in CORE_EXPORTS:
                problems.append(
                    f"{feature_id}: {name} is not exported by web/hea-calculator-core.js. "
                    "Fix: add it to the export object at the end of that file."
                )
            elif not re.search(rf"\b(?:core|calcCore)\.{name}\b", FRONT_END):
                problems.append(
                    f"{feature_id}: the page never uses core.{name}. Fix: use it in web/index.html "
                    f"or web/hea-features.js, or remove it from {REL}."
                )
        if not feature.get("tests"):
            problems.append(f"{feature_id}: no tests. Fix: name a test that proves the app computes what the library computes.")
        for node in feature.get("tests", []):
            path, _, name = node.partition("::")
            source = ROOT / path
            if not source.exists() or not re.search(
                rf"^def {re.escape(name)}\(", source.read_text(encoding="utf-8"), re.M
            ):
                problems.append(f"{feature_id}: test {node} does not exist. Fix: correct the node id in {REL}.")
    assert not problems, "\n".join(problems)


def test_every_bridge_method_is_reachable_from_the_app() -> None:
    orphans = sorted(set(webapp.METHODS) - CALLED)
    assert not orphans, (
        f"hea_bench.webapp methods that no app code calls: {orphans}. Fix: call each one from "
        "web/hea-features.js (engine.call) or web/hea-engine-worker.js (callPython), or delete it."
    )


def test_every_engine_feature_is_used_in_the_browser_smoke_test() -> None:
    """The Node engine tests prove the answers; only a browser proves the tab works."""
    problems = []
    for feature_id, feature in REGISTRY["features"].items():
        dom = feature.get("app", {}).get("dom", [])
        if feature.get("app", {}).get("bridge") and not any(f'"{element_id}"' in SMOKE for element_id in dom):
            problems.append(
                f"{feature_id}: tests/app_smoke.cjs never uses its UI. Fix: add a step to STEPS there that "
                f"uses it the way a person would, through one of its elements {dom}, then run "
                "pytest tests/test_app_smoke.py (needs the engine build and Chrome or Edge)."
            )
    assert not problems, "\n".join(problems)


def test_internal_and_deferred_entries_are_justified() -> None:
    problems = []
    for key, reason in REGISTRY["internal"].items():
        if len(reason.strip()) < 40:
            problems.append(f"internal {key}: state in a full sentence why it needs no app surface.")
    for deferred_id, item in REGISTRY["deferred"].items():
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", item.get("date", "")):
            problems.append(f"deferred {deferred_id}: 'date' must be the ISO date of the owner's decision.")
        if not item.get("decision", "").startswith("Owner"):
            problems.append(
                f"deferred {deferred_id}: only the owner can defer a feature. Fix: quote the owner's "
                "decision in 'decision', or build the feature and move it to 'features'."
            )
    assert not problems, "\n".join(problems)


def test_app_constants_match_the_library() -> None:
    from hea_bench.properties.hardness import N_MIN

    match = re.search(r"HARDNESS_MIN_ROWS = (\d+);", FRONT_END)
    assert match and int(match.group(1)) == N_MIN, (
        "web/hea-features.js HARDNESS_MIN_ROWS must equal hea_bench.properties.hardness.N_MIN. "
        f"Fix: set it to {N_MIN}."
    )


def test_reworded_library_warnings_still_exist() -> None:
    # appWording() in web/hea-features.js rewrites this library warning in
    # terms of the page's own controls. If the library rewords it, the page
    # would silently fall back to API wording, so the two move together.
    source = (ROOT / "src" / "hea_bench" / "properties" / "hardness.py").read_text(encoding="utf-8")
    assert "training data pools multiple processing routes" in source, (
        "hea_bench.properties.hardness changed its processing-route warning. Fix: update the "
        "matching pattern in appWording() in web/hea-features.js, then this assertion."
    )
