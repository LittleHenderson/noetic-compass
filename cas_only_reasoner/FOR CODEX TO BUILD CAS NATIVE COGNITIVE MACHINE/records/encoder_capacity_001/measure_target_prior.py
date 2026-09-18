"""Every run converges on `W36`. Is `W36` simply the commonest training target?

Pure standard library. No torch, no device, no target opened. Reads the frozen public course and the
run's own schedule.

The finding this tests
----------------------
`measure_all_runs_concentration.py` measured, from the workers' own recorded predictions, that **all
six runs** end with **`W36` as the commonest emitted alias** at the world-typed reference slots:

    receipt            arm  seed   cursor 160: distinct, commonest, share
    20260917_a         ALT  17     11, W36, 60.0%
    20260917_m         MIX  17     11, W36, 54.8%
    20260918_a         ALT  18     11, W36, 49.0%
    20260918_m         MIX  18     10, W36, 48.6%
    20260919_a         ALT  19      9, W36, 47.6%
    20260919_m         MIX  19      9, W36, 44.3%

**Three independent model initialisations and two curriculum orders all land on the same alias.**
That is worth explaining before it is called a collapse, and there is one obvious candidate:

> the training objective rewards raising the target symbol's rank, so if one world alias is
> over-represented among the training targets, a block that outputs the *marginal prior* instead of
> reading its input scores well on average — and converges on exactly that alias.

That would make the concentration **the training prior being learned as a constant**, which is a much
more ordinary and much more actionable statement than "the block collapsed".

What this measures
------------------
1. The alias frequency of the focus worlds the schedule actually presented, from the run's own
   `schedule.batches` and the public course.
2. The same for the 564-packet registry as a whole.
3. Whether `W36` is over-represented in either, which is the precondition for the hypothesis.

**A negative result is as useful as a positive one here.** If `W36` is *not* over-represented, the
prior hypothesis is dead and the convergence on `W36` needs another explanation.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from collections import Counter

HOME = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))

RECEIPT = HOME / "records/typed_matched_001/receipt_20260919_m"
RECEIVED = Counter()


def focus_aliases() -> dict:
    """``record_id -> (focus_world_id, focus_alias)`` for the whole public registry."""
    from cas_meta2.typed_teaching import course, input_frames, worker_contract

    frozen, _tokenizer, _source = worker_contract.load_material(HOME)
    out = {}
    for index, record in enumerate(frozen["registry"], 1):
        packet = course.model_packet(frozen, record["record_id"])
        frame = input_frames.compile_packet(packet)
        aliases = {a["world_id"]: a["alias"] for a in frame["aliases"]}
        focus = packet["record"]["query"]["focus_world_id"]
        out[record["record_id"]] = (focus, aliases.get(focus))
        if index % 200 == 0:
            print(f"  focus aliases: {index}/{len(frozen['registry'])}", flush=True)
    return out


def report(label: str, counts: Counter) -> None:
    total = sum(counts.values())
    if not total:
        print(f"  {label}: nothing")
        return
    entropy = 0.0
    import math
    for count in counts.values():
        p = count / total
        entropy -= p * math.log2(p)
    ordered = counts.most_common(8)
    print(f"  {label}")
    print(f"    presentations {total}   distinct aliases {len(counts)}   entropy {entropy:.3f} bits"
          f"   (max {math.log2(64):.3f})")
    print(f"    most frequent: " + ", ".join(
        f"{name}={count}({100 * count / total:.1f}%)" for name, count in ordered))
    top = ordered[0][0]
    if "W36" in counts:
        rank = sorted(counts, key=lambda name: (-counts[name], name)).index("W36") + 1
        standing = (f"W36's share = {100 * counts['W36'] / total:.1f}% and its rank is "
                    f"{rank} of {len(counts)}")
    else:
        standing = "** W36 IS NOT PRESENT AT ALL **"
    print(f"    commonest is {top};  {standing}")
    print()


def main() -> int:
    print("building focus aliases for the public registry...")
    aliases = focus_aliases()
    print(f"  records: {len(aliases)}")
    print()

    registry = Counter(alias for _world, alias in aliases.values() if alias)

    protocol = json.loads(
        (RECEIPT / "checkpoints/protocol_material.json").read_text(encoding="utf-8")
    )
    schedule = protocol["schedule"]["batches"]
    presented = Counter()
    unique_packets = set()
    for batch in schedule:
        for record_id in batch["record_ids"]:
            alias = aliases.get(record_id, (None, None))[1]
            if alias:
                presented[alias] += 1
                unique_packets.add(record_id)

    print("=" * 100)
    print("ALIAS FREQUENCY AMONG TRAINING TARGETS")
    print("=" * 100)
    print()
    report(f"every presentation across the {len(schedule)} main batches", presented)
    report(f"the {len(unique_packets)} distinct training packets", Counter(
        aliases[r][1] for r in unique_packets if aliases.get(r, (None, None))[1]
    ))
    report(f"the whole {len(registry)}-packet registry (what the model is scored on)", registry)

    print("=" * 100)
    print("READING")
    print("=" * 100)
    print()
    top_registry = registry.most_common(1)[0][0] if registry else None
    top_presented = presented.most_common(1)[0][0] if presented else None
    print(f"  commonest training target : {top_presented}")
    print(f"  commonest registry target : {top_registry}")
    print(f"  the alias every run converges on : W36")
    print()
    if "W36" in (top_presented, top_registry):
        print("  -> W36 IS over-represented. The prior hypothesis survives as a candidate: a block")
        print("     that outputs the marginal prior instead of reading its input scores well on")
        print("     average, and W36 would be what it converges on.")
    else:
        print("  -> W36 IS NOT the commonest target. The PRIOR HYPOTHESIS IS DEAD and the")
        print("     convergence on W36 in all six runs needs another explanation.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
