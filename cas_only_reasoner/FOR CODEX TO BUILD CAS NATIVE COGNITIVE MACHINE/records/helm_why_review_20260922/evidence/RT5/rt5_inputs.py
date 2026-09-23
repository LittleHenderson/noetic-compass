"""RT5 step 1: tabulate Helm's node and query INPUT values, trained course packets vs the 59 development packets.
Pure JSON, no torch. Mirrors pointer_inputs._world_reading / read_packet and pointer_learner._graph_blocks /
_degree_features / _query_vector (rank feature OFF: pointer_contract.py:896). Writes rt5_inputs.json next to itself.
Usage: python -B rt5_inputs.py <ROOT>
"""
import json, os, sys
from collections import Counter, defaultdict

ROOT = sys.argv[1]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rt5_inputs.json")
BASE = os.path.join(ROOT, "records", "typed_pointer_001")
RECEIPTS = ["receipt_helm1_certified_%s" % s for s in ("20260917", "20260918", "20260919")] + \
           ["receipt_%s" % s for s in ("20260917", "20260918", "20260919")]
DEGREE_STEPS = 5
WORLD_CHOICE = ("definition", "context", "analogy")


def ref_rank(ref):
    head, sep, tail = ref.rpartition("/n")
    assert head and sep == "/n" and tail.isdigit()
    return int(tail)


def world_reading(world, focus_id, target_id, marks):
    refs = sorted(n["ref"] for n in world["nodes"])
    index = {}
    for r, ref in enumerate(refs):
        assert ref_rank(ref) == r, "rank invariant"
        index[ref] = r
    n = len(refs)
    prank = {index[ref]: i + 1 for i, ref in enumerate(world["declarations"]["participants"])}
    whole = index[world["declared_whole"]]
    edges = sorted([index[e["source"]], index[e["target"]]] for e in world["contains"])
    indeg, outdeg = Counter(), Counter()
    for s, t in set(map(tuple, edges)):
        outdeg[s] += 1; indeg[t] += 1
    is_focus = 1 if world["world_id"] == focus_id else 0
    is_target = 1 if target_id is not None and world["world_id"] == target_id else 0
    rows = []
    for r in range(n):
        rows.append({
            "rank": r,
            "is_declared_whole": 1 if r == whole else 0,
            "participant": prank.get(r, 0),
            "is_whole_arg": 1 if (is_focus and marks.get("whole") == r) else 0,
            "is_part_arg": 1 if (is_focus and marks.get("part") == r) else 0,
            "is_focus": is_focus, "is_target": is_target,
            "in_raw": indeg[r], "out_raw": outdeg[r],
            "in": min(indeg[r], DEGREE_STEPS - 1), "out": min(outdeg[r], DEGREE_STEPS - 1),
        })
    return {"world_id": world["world_id"], "node_count": n, "edges": edges, "rows": rows,
            "participant_count": len(world["declarations"]["participants"])}


def reading(packet_worlds, focus_id, query):
    by_id = {w["world_id"]: w for w in packet_worlds}
    kind = query["kind"]; args = query["arguments"]
    target = args.get("target_world_id") if kind == "correspondence" else None
    focus = by_id[focus_id]
    fidx = {ref: r for r, ref in enumerate(sorted(n["ref"] for n in focus["nodes"]))}
    marks = {f: (fidx[args[f]] if args.get(f) is not None else None) for f in ("whole", "part")}
    keep = sorted(by_id) if kind in WORLD_CHOICE else sorted({focus_id} | ({target} if target else set()))
    worlds = {wid: world_reading(by_id[wid], focus_id, target, marks) for wid in keep}
    return {"kind": kind, "rule": query["rule"], "whole": marks["whole"], "part": marks["part"],
            "world_count": len(keep), "focus_world_id": focus_id, "worlds": worlds}


course = json.load(open(os.path.join(ROOT, "records/typed_course_001/checks_002/public_course.json"), encoding="utf-8"))
registry = {r["record_id"]: r for r in course["registry"]}
bank_worlds = course["bank"]["worlds"]

pms = {rd: json.load(open(os.path.join(BASE, rd, "checkpoints", "protocol_material.json"), encoding="utf-8")) for rd in RECEIPTS}
trained_sets = {rd: tuple(sorted(pm["trained_record_ids"])) for rd, pm in pms.items()}
dev_digests = {rd: pm["development"]["development_digest"] for rd, pm in pms.items()}
inter_sets = {rd: tuple(sorted({r for b in pm["interference_batches"] for r in b["record_ids"]})) for rd, pm in pms.items()}
sched_sets = {rd: tuple(sorted({r for b in pm["schedule"]["batches"] for r in b["record_ids"]})) for rd, pm in pms.items()}
print("trained id sets identical across 6 receipts:", len(set(trained_sets.values())) == 1, "size", len(trained_sets[RECEIPTS[0]]))
print("schedule-batch record sets identical:", len(set(sched_sets.values())) == 1, "size", len(sched_sets[RECEIPTS[0]]),
      "schedule == trained ids:", set(sched_sets[RECEIPTS[0]]) == set(trained_sets[RECEIPTS[0]]))
print("interference record sets identical:", len(set(inter_sets.values())) == 1, "size", len(inter_sets[RECEIPTS[0]]),
      "interference within trained ids:", len(set(inter_sets[RECEIPTS[0]]) & set(trained_sets[RECEIPTS[0]])))
print("development digests identical:", len(set(dev_digests.values())) == 1)
dev_packets_by_receipt = {rd: [p for p in pm["development"]["packets"]] for rd, pm in pms.items()}
dev_json = {rd: json.dumps(v, sort_keys=True) for rd, v in dev_packets_by_receipt.items()}
print("development packets byte-identical across receipts (canonical json):", len(set(dev_json.values())) == 1)

trained_ids = list(trained_sets[RECEIPTS[0]])
inter_only = sorted(set(inter_sets[RECEIPTS[0]]) - set(trained_ids))


def course_reading(rid):
    row = registry[rid]
    return reading(bank_worlds, row["source_world_id"], row["query"])


trained = {rid: course_reading(rid) for rid in trained_ids}
inter = {rid: course_reading(rid) for rid in inter_only}
dev = {}
for p in dev_packets_by_receipt[RECEIPTS[0]]:
    q = p["record"]["query"]
    assert q["focus_world_id"] == p["source"]["focus_world_id"]
    dev[p["record"]["record_id"]] = reading(p["source"]["worlds"], p["source"]["focus_world_id"], q)


def tab(readings, focus_only=False, kinds=None):
    t = defaultdict(Counter)
    for r in readings.values():
        if kinds and r["kind"] not in kinds:
            continue
        t["kind"][r["kind"]] += 1
        t["world_count"][r["world_count"]] += 1
        if r["whole"] is not None: t["query_whole_rank"][r["whole"]] += 1
        if r["part"] is not None: t["query_part_rank"][r["part"]] += 1
        for wid, w in r["worlds"].items():
            if focus_only and wid != r["focus_world_id"]:
                continue
            t["node_count"][w["node_count"]] += 1
            t["participant_count"][w["participant_count"]] += 1
            for row in w["rows"]:
                t["in_clamped"][row["in"]] += 1; t["out_clamped"][row["out"]] += 1
                t["in_raw"][row["in_raw"]] += 1; t["out_raw"][row["out_raw"]] += 1
                t["participant_rank"][row["participant"]] += 1
                t["in_out_pair"][(row["in"], row["out"])] += 1
    return {k: dict(sorted(v.items())) for k, v in t.items()}


def show(name, d):
    print("==", name)
    for k, v in d.items():
        print("   %-18s %s" % (k, v))


show("TRAINED all kinds, every node row of every carried world (WIDE)", tab(trained))
show("TRAINED all kinds, focus-world rows only", tab(trained, focus_only=True))
show("TRAINED reach+parts, focus-world rows (NARROW)", tab(trained, focus_only=True, kinds=("reach", "parts")))
show("INTERFERENCE-only records (not in trained ids)", tab(inter) if inter else {})
show("DEV all 59, focus-world rows", tab(dev, focus_only=True))
show("DEV reach+parts, focus-world rows", tab(dev, focus_only=True, kinds=("reach", "parts")))

json.dump({"trained": {k: v for k, v in trained.items()}, "dev": dev, "interference_only": inter},
          open(OUT, "w", encoding="utf-8"), sort_keys=True)
print("wrote", OUT)
