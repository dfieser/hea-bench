"""Replay studies: does the campaign loop beat random picks, and do its intervals hold?

Study 1, the loop against random selection, protocol fixed before
looking at results. The pool is every descriptor-scorable Borg hardness
alloy. Each of 25 runs starts from 10 alloys drawn at random (seeded by
the run number) and then asks for batches of five until 50 alloys are
measured, by two rules from the same start: the loop's own ranking
(:func:`hea_bench.design.campaign.rank_candidates`, the exact code behind
:meth:`Campaign.suggest`, expected improvement, maximizing hardness) and
uniform random picks. A pick's measured hardness is revealed only after
it is picked. The study reports how hard the hardest alloy found is
after each batch, how many runs reach the ten hardest alloys of the
pool, and how often a revealed hardness falls inside the 90 percent
interval the loop gave with the suggestion.

Study 2, a chronological replay, the earlier check kept as it was:
within the Al-Co-Cr-Fe-Ni palette, the Borg hardness records are
replayed in publication-year order. The campaign starts cold (no warm
start, because the warm-start pool IS this data), observes each year's
alloys as they were published, and after every year suggests a batch of
five on the 0.1 lattice. The question is when a suggestion first lands
within an L1 mole-fraction distance of 0.2 of the eventual
highest-hardness alloy, versus the year that alloy was published. The
corpus-domain constraint is off because the fitted domain model
summarizes the corpus including years the replay has not reached.

Both are reported as they come out. Neither imports anyone else's
campaign.

    PYTHONPATH=src python tools/campaign_replay.py
"""

from __future__ import annotations

import datetime
import pathlib
import random
import statistics
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from hea_bench import __version__ as _hea_bench_version  # noqa: E402
from hea_bench.descriptors.backend import matrix_vector  # noqa: E402
from hea_bench.design import DomainConstraint  # noqa: E402
from hea_bench.design.campaign import COLD_START_FLOOR, Campaign, rank_candidates  # noqa: E402
from hea_bench.properties.borg import hardness_records  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_MD = REPO_ROOT / "docs" / "campaign-replay.md"

RUNS = 25
START = 10
BATCH = 5
BUDGET = 50
TOP = 10

PALETTE = ["Al", "Co", "Cr", "Fe", "Ni"]
STEP = 0.1
HIT_L1 = 0.2


def _l1(a: dict, b: dict) -> float:
    keys = set(a) | set(b)
    return sum(abs(a.get(key, 0.0) - b.get(key, 0.0)) for key in keys)


def loop_versus_random() -> dict:
    """Study 1. Returns every number the doc reports."""
    pool, values = [], []
    for record in hardness_records():
        vector = matrix_vector(record.composition)
        if vector is not None:
            pool.append(vector)
            values.append(record.value)
    top = set(sorted(range(len(values)), key=lambda i: -values[i])[:TOP])
    checkpoints = list(range(START + BATCH, BUDGET + 1, BATCH))
    best = {"loop": {c: [] for c in checkpoints}, "random": {c: [] for c in checkpoints}}
    reached_top = {"loop": 0, "random": 0}
    covered = suggested = 0
    for run in range(RUNS):
        start = random.Random(run).sample(range(len(pool)), START)
        for rule in ("loop", "random"):
            picker = random.Random(10_000 + run)
            measured = list(start)
            while len(measured) < BUDGET:
                seen = set(measured)
                remaining = [i for i in range(len(pool)) if i not in seen]
                if rule == "loop":
                    picks = rank_candidates(
                        [pool[i] for i in measured],
                        [values[i] for i in measured],
                        [pool[i] for i in remaining],
                        n=BATCH,
                    )
                    chosen = [remaining[position] for position, _v, _iv, _s in picks]
                    for (position, _value, (low, high), _score) in picks:
                        truth = values[remaining[position]]
                        covered += low <= truth <= high
                        suggested += 1
                else:
                    chosen = picker.sample(remaining, BATCH)
                measured += chosen
                best[rule][len(measured)].append(max(values[i] for i in measured))
            reached_top[rule] += bool(top & set(measured))
    return {
        "n_pool": len(pool),
        "hardest": max(values),
        "top_floor": min(values[i] for i in top),
        "checkpoints": checkpoints,
        "best": best,
        "reached_top": reached_top,
        "covered": covered,
        "suggested": suggested,
    }


def chronological() -> dict:
    """Study 2. Returns every number the doc reports."""
    palette_set = set(PALETTE)
    records = [
        record
        for record in hardness_records()
        if set(record.composition) <= palette_set and record.year is not None
    ]
    records.sort(key=lambda record: (record.year, record.formula_raw))
    winner = max(records, key=lambda record: record.value)
    years = sorted({record.year for record in records})
    campaign = Campaign(
        "hardness",
        PALETTE,
        (DomainConstraint(in_domain=None),),
        seed=0,
        step=STEP,
        n_elements=(4, 5),
        warm_start=False,
    )
    rows = []
    first_hit_year = None
    for year in years:
        for record in records:
            if record.year == year:
                campaign.observe(record.composition, record.value, processing=record.processing)
        n_seen = campaign.n_informative()
        if n_seen < COLD_START_FLOOR:
            rows.append((year, n_seen, None))
            continue
        if winner.year is not None and year >= winner.year:
            break
        suggestions = campaign.suggest(n=BATCH)
        distance = min(_l1(s.composition, winner.composition) for s in suggestions)
        rows.append((year, n_seen, distance))
        if distance <= HIT_L1 and first_hit_year is None:
            first_hit_year = year
    return {
        "records": records,
        "years": years,
        "winner": winner,
        "rows": rows,
        "first_hit_year": first_hit_year,
    }


def main() -> int:
    try:
        import sklearn  # noqa: F401
    except ImportError:
        print('needs scikit-learn: pip install -e ".[properties]"', file=sys.stderr)
        return 2

    one = loop_versus_random()
    two = chronological()

    coverage = one["covered"] / one["suggested"]
    lines = [
        "# Campaign replays on the Borg hardness record",
        "",
        f"Generated by `tools/campaign_replay.py` with hea-bench "
        f"{_hea_bench_version} on {datetime.date.today().isoformat()}; "
        f"protocols in the tool docstring.",
        "",
        "## The loop against random selection",
        "",
        f"Pool: the {one['n_pool']} descriptor-scorable Borg hardness alloys "
        f"(hardest {one['hardest']:.0f} HV; the ten hardest are at least "
        f"{one['top_floor']:.0f} HV). {RUNS} runs, each starting from {START} "
        f"random alloys and measuring batches of {BATCH} up to {BUDGET}, by "
        f"the loop's expected-improvement ranking and by random picks from "
        f"the same start.",
        "",
        "| alloys measured | hardest found, loop (mean HV) | hardest found, random (mean HV) |",
        "|---:|---:|---:|",
    ]
    for checkpoint in one["checkpoints"]:
        lines.append(
            f"| {checkpoint} | {statistics.mean(one['best']['loop'][checkpoint]):.0f} | "
            f"{statistics.mean(one['best']['random'][checkpoint]):.0f} |"
        )
    lines += [
        "",
        f"Runs that measured one of the ten hardest alloys within {BUDGET}: "
        f"{one['reached_top']['loop']} of {RUNS} by the loop, "
        f"{one['reached_top']['random']} of {RUNS} by random picks.",
        "",
        f"The loop's 90 percent intervals held the revealed hardness for "
        f"{one['covered']} of its {one['suggested']} suggestions "
        f"({coverage:.3f}). Suggestions are chosen for high predicted "
        f"hardness and high model disagreement, which is where intervals "
        f"are most likely to miss, so this is coverage under selection, the "
        f"case a user meets.",
        "",
        "## Chronological replay on the Al-Co-Cr-Fe-Ni palette",
        "",
    ]
    winner = two["winner"]
    lines += [
        f"{len(two['records'])} palette alloys with a publication year replay "
        f"across {len(two['years'])} years (batch {BATCH}, expected improvement, "
        f"lattice step {STEP}, hit radius L1 {HIT_L1}, cold start). The eventual "
        f"hardest alloy is {winner.formula_raw} (HV {winner.value:.0f}, "
        f"{winner.processing or 'unrecorded processing'}, published {winner.year}).",
        "",
        "| year observed through | informative rows | min L1 from that round's "
        "suggestions to the eventual winner |",
        "|---:|---:|---:|",
    ]
    for year, n_seen, distance in two["rows"]:
        shown = f"{distance:.2f}" if distance is not None else "(below cold-start floor)"
        lines.append(f"| {year} | {n_seen} | {shown} |")
    first = two["first_hit_year"]
    lead = (winner.year - first) if first is not None else None
    lines += [
        "",
        (
            f"The loop first suggested within the hit radius of the eventual "
            f"winner after observing data through {first}, {lead} years before "
            f"the winner's own publication year."
            if lead is not None and lead > 0
            else (
                f"The loop first reached the hit radius in {first}, which gives "
                f"no lead over the winner's publication year ({winner.year})."
                if first is not None
                else (
                    f"The loop never suggested within the hit radius before the "
                    f"winner's publication year ({winner.year})."
                )
            )
        ),
        "",
        "One family and one ordering, on a lattice that cannot express every "
        "published stoichiometry exactly: an anecdote with a fixed protocol, "
        "where the first study is the test.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
