"""The frozen facts of every published corpus version, in one place.

These digests ARE the frozen splits. A change to the corpus, the row
order, the grouping rule, or the assignment rule moves them. If a check
against them fails, do not edit a constant to make it pass: work out what
moved and whether the benchmark needs a new version. Rewriting a
published split silently is how a benchmark stops being one.

Every digest was computed with math.fsum-based normalization (see
:func:`hea_bench.composition.normalize`) and verified byte-identical
across Python 3.10 and 3.13 on Windows and Python 3.12 on Linux before
pinning. A version's numbers never change once published; adding data
means adding a version with its own block here. The test suite, the CI
``benchmark-freeze`` job and the web app all check against this table.
"""

from __future__ import annotations

FROZEN: dict[str, dict] = {
    "0.1.0": {
        "rows": 7683,
        "families": 1259,
        "element_covered": 7373,
        "conflicts": 100,
        "digests": {
            "single_vs_multi": {
                "grouped": "a1d87ef65c5a96485edecbb6fea4ec8c10b82ef303de300b43292adb7b485226",
                "random": "33a2cbffce2b7c0657bd1962ba6f73559a54e7247c172f3f49940293cb5e820a",
            },
            "phase4": {
                "grouped": "3996c5a68b58a07c31b2586efdc0c7b1415108391e2a674641b226a8814fda16",
                "random": "171fdb33115efe7701eb96b289ec2db7073a4897e18eead91162b6b934ac0531",
            },
        },
    },
    # v0.2.0 adds the Chizhevskiy LLM-extracted database (CC-BY-4.0 since
    # 2026-08-10). Conflicts jump 100 -> 226 because its labels disagree
    # with the v0.1.0 consensus on ~30% of overlapping alloys and every
    # disagreement is quarantined rather than voted on.
    "0.2.0": {
        "rows": 10064,
        "families": 2257,
        "element_covered": 9480,
        "conflicts": 226,
        "digests": {
            "single_vs_multi": {
                "grouped": "7bb76d59a8f5c88be3ee3ec9bf6bed249e6864a07353d99746aea4c8e7b63060",
                "random": "e3d2d94ed5774569cb0825eb6d4744a0e96db16d991dba8070c8f8bccc1f75ed",
            },
            "phase4": {
                "grouped": "861c255c34337a0be7b265e7dae0189f912aecb9137ec7d8dc9ac5feb40382a6",
                "random": "36751215d7e0d549bec2e4c7e551aad0ee63d4f346035092afa29372bd8c4e64",
            },
        },
    },
}


def verify_split_digests(benchmark) -> dict:
    """Compare a loaded benchmark's fold digests with the frozen ones.

    Returns ``{"grouped": {...}, "random": {...}, "verified": bool}``,
    each scheme carrying its computed and frozen digest. A version with
    no frozen block reports ``verified`` False with frozen digests None,
    because an unpinned split cannot be checked, only described.
    """
    pinned = FROZEN.get(benchmark.corpus_version, {}).get("digests", {}).get(benchmark.task, {})
    result: dict = {}
    for name, scheme in (("grouped", benchmark.grouped), ("random", benchmark.random)):
        frozen = pinned.get(name)
        result[name] = {
            "computed": scheme.digest,
            "frozen": frozen,
            "match": frozen is not None and frozen == scheme.digest,
        }
    result["verified"] = all(result[name]["match"] for name in ("grouped", "random"))
    return result


__all__ = ["FROZEN", "verify_split_digests"]
