"""Can an ADDRESSED read recover the focus world where the mean-pooled packet cannot?

Pure Python over the real frozen rows. No torch, no GPU, no model execution.

The proposed architecture replaces  packet = unit_l2(sum of all row vectors)
with a read addressed by the query: score each world by <query, world_row> and
take the argmax. This keeps every world present, so the answer space is unchanged
and nothing leaks, while removing the mean-pooling dilution.

This script tests that directly: for each sampled real packet, does the addressed
read pick the focus world?
"""

import argparse
import math
import pathlib
import sys
import time

HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
COMP = HOME / "research" / "CAS_META_2_COMPOSITION"
sys.path.insert(0, str(COMP))
sys.path.insert(0, str(HOME))

from cas_meta2.typed_teaching import binding, course, worker_contract  # noqa: E402
from cas_meta2.typed_teaching import input_frames as frames_mod  # noqa: E402

SEED = 20260916
D = 64


def unit(v):
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n else v


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packets", type=int, default=40)
    args = ap.parse_args()

    frozen, tokenizer, _ = worker_contract.load_material(HOME)
    base = {i: binding.row_bytes(["token", v], seed=SEED, d_model=D)
            for i, v in enumerate(tokenizer.vocabulary)}

    def rows_of(packet):
        rows = binding.compile_packet(packet, tokenizer, seed=SEED, d_model=D)["rows"]
        built = []
        for row in rows:
            rv = [0.0] * D
            for position, token in enumerate(row["token_ids"]):
                order, signs = binding.signed_permutation(
                    seed=SEED, scope=row["scope"], ordinal=row["ordinal"],
                    position=position, d_model=D)
                b = base[token]
                for dest, (origin, sign) in enumerate(zip(order, signs)):
                    rv[dest] += sign * b[origin]
            built.append((tuple(row["scope"]), unit(rv)))
        return built

    def alias_map(packet):
        frame = frames_mod.compile_packet(packet)
        return {r["alias"]: r["world_id"] for r in frame["aliases"]}, \
               packet["record"]["query"]["focus_world_id"]

    registry = frozen["registry"]
    step = max(1, len(registry) // args.packets)
    sample = registry[::step][:args.packets]
    print(f"sampling {len(sample)} of {len(registry)} registry rows")

    stats = {"addressed_query": 0, "addressed_query_record_support": 0,
             "meanpooled_packet": 0, "n": 0}
    started = time.time()
    for row in sample:
        packet = course.model_packet(frozen, row["record_id"])
        rvs = rows_of(packet)
        aliases, focus = alias_map(packet)
        # world rows, by alias
        world_rows = {s[1]: v for s, v in rvs if s[0] == "WORLD" and len(s) > 1}
        focus_alias = next((a for a, w in aliases.items() if w == focus), None)
        if focus_alias is None or focus_alias not in world_rows:
            continue

        def sel(fams):
            vs = [v for s, v in rvs if s[0] in fams]
            return unit([sum(x) for x in zip(*vs)]) if vs else None

        q_only = sel({"QUERY"})
        q_all = sel({"QUERY", "RECORD", "SUPPORT"})
        mean_pool = unit([sum(x) for x in zip(*[v for _, v in rvs])])

        for name, q in (("addressed_query", q_only),
                        ("addressed_query_record_support", q_all),
                        ("meanpooled_packet", mean_pool)):
            if q is None:
                continue
            scores = {a: dot(q, w) for a, w in world_rows.items()}
            best = max(scores, key=scores.get)
            stats[name] += 1 if best == focus_alias else 0
        stats["n"] += 1
        if stats["n"] % 10 == 0:
            print(f"  ... {stats['n']} packets, {time.time()-started:.0f}s")

    n = stats["n"]
    print()
    print("=" * 84)
    print("CAN THE FOCUS WORLD BE RECOVERED?  (chance = 1/64 = 1.56%)")
    print("=" * 84)
    print(f"  packets evaluated : {n}")
    print()
    for name in ("addressed_query_record_support", "addressed_query", "meanpooled_packet"):
        acc = 100 * stats[name] / n if n else 0
        verdict = "ABOVE CHANCE" if acc > 5 else "at chance"
        print(f"  {name:36s} {stats[name]:4d}/{n:<4d} = {acc:6.2f}%   {verdict}")
    print()
    print("  If the addressed read recovers the focus well and the mean-pooled")
    print("  packet does not, the architectural fix is confirmed before any spend.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
