"""Independent check of the leaks lens's rule R10, which reopened the rank decision.

R10 is "the reach answer is the alphabetically-last node" (node rank == highest), reading only the rank flag and no
adjacency. The lens reports it solves 4 of the 9 eligible held `reach` questions
(`measurements/leaks_review/lk2_single_flag_out.txt` lines 89-94). That number drove a decision reversal, so it is
re-derived here from the lens's own published caches rather than trusted.

Read-only. Reuses `lk_cache_packets.pkl` and `lk_cache_admissible.json`, both built by the lens. $0, no torch.
Run from a short working directory.
"""
import json
import pickle
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEAKS = HERE.parent / "leaks_review"

packets = pickle.loads((LEAKS / "lk_cache_packets.pkl").read_bytes())
cache = json.loads((LEAKS / "lk_cache_admissible.json").read_text(encoding="utf-8"))

PK, targets, eligible = packets["packets"], cache["targets"], set(cache["eligible"])

# Map question -> its records, and record -> focus world node refs.
by_question = defaultdict(list)
for record_id, packet in PK.items():
    record = packet["record"]
    by_question[record["query"]["query_id"]].append(record_id)


def nodes_of(record):
    world = None
    for w in packet_worlds[record["source_world_id"]]:
        world = w
    return world


# The packet carries every bank world; index them once by world_id.
packet_worlds = {}
for record_id, packet in PK.items():
    for world in packet["source"]["worlds"]:
        packet_worlds.setdefault(world["world_id"], world)

rows = []
for qid in sorted(eligible):
    recs = by_question.get(qid)
    if not recs:
        continue
    kinds = {PK[r]["record"]["query"]["kind"] for r in recs}
    if kinds != {"reach"}:
        continue
    rec = PK[recs[0]]["record"]
    world = packet_worlds[rec["source_world_id"]]
    refs = sorted(node["ref"] for node in world["nodes"])
    highest = refs[-1]  # rank == index == sorted position, measured 244/244 by the lens

    adm = set()
    for r in recs:
        for item in targets.get(r, []):
            adm.add(item)
    # Is "the answer names the highest-rank node" admissible, for any admissible answer set?
    r10_hits = 0
    detail = []
    for item in adm:
        answer = json.loads(item)
        via = answer.get("via")
        if via is not None and via == highest:
            r10_hits += 1
        detail.append((answer.get("state"), via.rsplit("/", 1)[-1] if isinstance(via, str) else None))
    rows.append({"question": qid, "records": len(recs), "highest": highest.rsplit("/", 1)[-1],
                 "r10_solved": r10_hits > 0, "answers": sorted(detail)})

solved = sum(1 for r in rows if r["r10_solved"])
print("eligible held reach questions:", len(rows))
print("R10 solved (answer names the alphabetically-last node):", solved)
print()
for r in rows:
    print("  %-8s highest=%-4s solved=%-5s records=%d answers=%s"
          % (r["question"][-8:], r["highest"], r["r10_solved"], r["records"], r["answers"]))
print()
print("LENS REPORTED: 4 of 9")
print("RE-DERIVED   : %d of %d" % (solved, len(rows)))
print("AGREES:", solved == 4 and len(rows) == 9)
