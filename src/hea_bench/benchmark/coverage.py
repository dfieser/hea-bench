"""Coverage analysis of the consolidated benchmark against the
descriptor data tables.

For each composition in ``data/consolidated/v<version>/consolidated.csv``,
checks whether all of its elements are present in:

(a) :data:`hea_bench.descriptors.data.elemental.ELEMENTAL_DATA`
    — needed for δ, VEC, T_m (the "basic" descriptor set)
(b) the Miedema pair table at
    :mod:`hea_bench.descriptors.data.pair_enthalpies`
    — needed for ΔH_mix and Ω

Outputs:

- per-composition counts (in_basic_only / in_miedema_only / in_both / no_coverage)
- ranked list of elements missing from each table, by alloy frequency
- the "next-best-add" candidates — elements present in the pair table
  but missing from ELEMENTAL_DATA, sorted by how many alloys they'd
  unlock if added

Run as a module to score the released v0.1.0:

    python -m hea_bench.benchmark.coverage
"""

from __future__ import annotations

import csv
import json
import pathlib
import sys
from collections import Counter
from collections.abc import Iterable

from ..composition import parse_formula
from ..descriptors.data.elemental import covered_elements as _elemental_covered
from ..descriptors.data.pair_enthalpies import covered_elements as _pair_covered

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_DEFAULT_CSV = _REPO_ROOT / "data" / "consolidated" / "v0.1.0" / "consolidated.csv"


def analyze(csv_path: pathlib.Path = _DEFAULT_CSV) -> dict:
    """Compute coverage of the consolidated benchmark.

    Returns a dict with:

    - ``total`` : total compositions in the CSV
    - ``in_basic``, ``in_miedema``, ``in_both``, ``in_neither`` : counts
    - ``missing_from_basic`` : ``Counter`` of element → alloy frequency
      for elements that appear in compositions but are absent from
      ELEMENTAL_DATA
    - ``missing_from_miedema`` : same for the pair table
    - ``next_best_adds`` : list of (element, n_alloys_unlocked,
      already_in_pair_table) tuples, sorted descending — these are
      the highest-leverage elements to add to ELEMENTAL_DATA next
    """
    basic = _elemental_covered()
    miedema = _pair_covered()

    total = 0
    in_basic = 0
    in_miedema = 0
    in_both = 0
    in_neither = 0
    missing_from_basic: Counter[str] = Counter()
    missing_from_miedema: Counter[str] = Counter()

    # For "next-best-add": map each currently-uncovered element to the
    # number of compositions whose ONLY missing element(s) are inside
    # the set that would be unlocked by adding it. Simpler proxy:
    # count how many compositions contain each uncovered element.
    per_element_alloys: Counter[str] = Counter()

    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            total += 1
            try:
                comp = parse_formula(row["composition_key"])
            except (KeyError, ValueError):
                continue
            elems = set(comp)
            miss_b = elems - basic
            miss_m = elems - miedema

            if not miss_b:
                in_basic += 1
            if not miss_m:
                in_miedema += 1
            if not miss_b and not miss_m:
                in_both += 1
            if miss_b and miss_m:
                in_neither += 1

            for e in miss_b:
                missing_from_basic[e] += 1
            for e in miss_m:
                missing_from_miedema[e] += 1
            for e in elems - basic:
                per_element_alloys[e] += 1

    # Next-best-add ranking: elements outside ELEMENTAL_DATA, by alloy
    # count, with a flag indicating whether they're already in the
    # pair table (low-effort wins) vs. need full sourcing.
    next_best: list[tuple[str, int, bool]] = []
    for el, cnt in per_element_alloys.most_common():
        next_best.append((el, cnt, el in miedema))

    return {
        "csv_path": str(csv_path),
        "total": total,
        "in_basic": in_basic,
        "in_miedema": in_miedema,
        "in_both": in_both,
        "in_neither": in_neither,
        "missing_from_basic": dict(missing_from_basic),
        "missing_from_miedema": dict(missing_from_miedema),
        "next_best_adds": next_best,
    }


def format_report(report: dict) -> str:
    """Render `analyze()` output as a human-readable text report."""
    out: list[str] = []
    total = report["total"]
    pct = lambda n: f"{n/total*100:.1f}%" if total else "0.0%"

    out.append(f"=== Coverage report: {report['csv_path']} ===")
    out.append(f"")
    out.append(f"total compositions:       {total:>5}")
    out.append(f"")
    out.append(f"Coverage by descriptor data table:")
    out.append(f"  ELEMENTAL_DATA (δ/VEC/T_m):  {report['in_basic']:>5} / {total}  ({pct(report['in_basic'])})")
    out.append(f"  Miedema pair table (ΔH/Ω):   {report['in_miedema']:>5} / {total}  ({pct(report['in_miedema'])})")
    out.append(f"  both (all 6 descriptors):    {report['in_both']:>5} / {total}  ({pct(report['in_both'])})")
    out.append(f"  neither (cannot score):      {report['in_neither']:>5} / {total}  ({pct(report['in_neither'])})")
    out.append(f"")
    out.append(f"Top 15 elements missing from ELEMENTAL_DATA (basic descriptors):")
    items = sorted(report["missing_from_basic"].items(), key=lambda kv: -kv[1])[:15]
    for el, cnt in items:
        out.append(f"  {el:>3}  appears in {cnt:>5} alloys  ({pct(cnt)})")
    out.append(f"")
    out.append(f"Next-best-add ranking (elements outside ELEMENTAL_DATA, by alloy count):")
    out.append(f"  symbol  alloys-unlocked  already-in-pair-table")
    for el, cnt, in_pair in report["next_best_adds"][:15]:
        flag = "YES (low-effort win)" if in_pair else "no  (needs full sourcing)"
        out.append(f"  {el:>3}     {cnt:>5}            {flag}")
    return "\n".join(out)


def main(argv: Iterable[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    report = analyze()
    print(format_report(report))
    # Persist machine-readable form alongside the v0.1.0 release.
    out_json = pathlib.Path(report["csv_path"]).parent / "coverage_report.json"
    out_json.write_text(json.dumps(
        {k: (dict(v) if isinstance(v, Counter) else v) for k, v in report.items()},
        indent=2,
    ))
    print(f"\nwrote {out_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
