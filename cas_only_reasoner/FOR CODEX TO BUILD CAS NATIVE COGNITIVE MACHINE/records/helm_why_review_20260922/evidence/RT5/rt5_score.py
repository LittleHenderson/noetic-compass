"""RT5 step 2: apply the flags fixed in 00_DEFINITIONS_WRITTEN_BEFORE_SCORING.txt to the saved development_p10 scoring
for DIRECT (8) and parts (6). Pure JSON. Reads rt5_inputs.json (step 1) and the six receipts' saved scoring/predictions.
Usage: python -B rt5_score.py <ROOT>
"""
import json, os, sys
from collections import Counter, defaultdict, deque

ROOT = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(ROOT, "records", "typed_pointer_001")
RECEIPTS = ["receipt_helm1_certified_%s" % s for s in ("20260917", "20260918", "20260919")] + \
           ["receipt_%s" % s for s in ("20260917", "20260918", "20260919")]
VERSION = {rd: ("1.0" if "helm1" in rd else "2.0") for rd in RECEIPTS}
data = json.load(open(os.path.join(HERE, "rt5_inputs.json"), encoding="utf-8"))
trained, dev = data["trained"], data["dev"]

# ---- reference sets (fixed definitions) ----
WIDE = {"in": set(), "out": set(), "participant": set()}
NARROW = {"in": set(), "out": set(), "participant": set()}
PAIR_WIDE = set()
q_whole, q_part = set(), set()
for r in trained.values():
    for wid, w in r["worlds"].items():
        for row in w["rows"]:
            for k in WIDE: WIDE[k].add(row[k])
            PAIR_WIDE.add((row["in"], row["out"]))
            if wid == r["focus_world_id"] and r["kind"] in ("reach", "parts"):
                for k in NARROW: NARROW[k].add(row[k])
    if r["kind"] in ("reach", "parts") and r["whole"] is not None: q_whole.add(r["whole"])
    if r["kind"] == "reach" and r["part"] is not None: q_part.add(r["part"])
print("WIDE ref:", {k: sorted(v) for k, v in WIDE.items()})
print("NARROW ref:", {k: sorted(v) for k, v in NARROW.items()})
print("query whole-rank ref:", sorted(q_whole), " query part-rank ref:", sorted(q_part))


def node_oor(row, ref):
    return any(row[k] not in ref[k] for k in ref)


def truth(r):
    w = r["worlds"][r["focus_world_id"]]
    kids = defaultdict(list)
    for s, t in w["edges"]: kids[s].append(t)
    if r["kind"] == "parts": return ("PARTS", tuple(sorted(kids.get(r["whole"], []))))
    if r["part"] in kids.get(r["whole"], []): return ("DIRECT", None)
    return ("OTHER", None)


flags = {}
for rid, r in dev.items():
    st = truth(r)[0]
    if st not in ("DIRECT", "PARTS"):
        continue
    w = r["worlds"][r["focus_world_id"]]
    rows = w["rows"]
    kids = sorted(t for s, t in w["edges"] if s == r["whole"])
    key = {r["whole"]} | ({r["part"]} if r["part"] is not None else set()) | (set(kids) if st == "PARTS" else set())
    q_oor = (r["whole"] not in q_whole) or (r["part"] is not None and r["part"] not in q_part)
    key_wide = any(node_oor(rows[n], WIDE) for n in key)
    key_narrow = any(node_oor(rows[n], NARROW) for n in key)
    any_wide = any(node_oor(x, WIDE) for x in rows)
    flags[rid] = {
        "state": st, "node_count": w["node_count"], "whole": r["whole"], "part": r["part"], "kids": kids,
        "key_nodes": sorted(key),
        "key_rows": [(n, rows[n]["in"], rows[n]["out"], rows[n]["participant"]) for n in sorted(key)],
        "PRIMARY": key_wide or q_oor, "node_only_key_WIDE": key_wide, "node_only_key_NARROW": key_narrow,
        "any_focus_node_WIDE": any_wide, "query_rank_OOR": q_oor,
        "whole_rank_OOR": r["whole"] not in q_whole,
        "part_rank_OOR": r["part"] is not None and r["part"] not in q_part,
        # descriptive only (NOT a pre-registered flag): (in,out) PAIR never seen in trained rows, on a key node
        "key_pair_unseen_DESCRIPTIVE": any((rows[n]["in"], rows[n]["out"]) not in PAIR_WIDE for n in key),
    }
print("\nDIRECT/parts records and their flags:")
for rid in sorted(flags, key=lambda x: (flags[x]["state"], x)):
    f = flags[rid]
    print("  %s %-6s n=%d whole=%s part=%s kids=%s PRIMARY=%s nodeKeyWIDE=%s nodeKeyNARROW=%s anyNodeWIDE=%s qOOR=%s pairUnseen=%s keyrows(n,in,out,prank)=%s"
          % (rid[:20], f["state"], f["node_count"], f["whole"], f["part"], f["kids"], f["PRIMARY"],
             f["node_only_key_WIDE"], f["node_only_key_NARROW"], f["any_focus_node_WIDE"], f["query_rank_OOR"],
             f["key_pair_unseen_DESCRIPTIVE"], f["key_rows"]))

# ---- saved scoring ----
pairs = []  # (receipt, rid, correct, predicted value)
for rd in RECEIPTS:
    ck = os.path.join(BASE, rd, "checkpoints")
    rows = json.load(open(os.path.join(ck, "development_p10_scoring.json"), encoding="utf-8"))["rows"]
    pred = {p["record_id"]: p for p in json.load(open(os.path.join(ck, "development_p10_predictions.json"), encoding="utf-8"))["predictions"]}
    seen = 0
    for row in rows:
        if row["record_id"] in flags:
            seen += 1
            pairs.append((rd, row["record_id"], bool(row["correct"]), pred[row["record_id"]]["answer"]["value"]))
    assert seen == 14, (rd, seen)
print("\n(receipt, record) pairs:", len(pairs))


def share(sub, flag):
    n = len(sub); k = sum(1 for p in sub if flags[p[1]][flag])
    return k, n


def report(label, sel):
    sub = [p for p in pairs if sel(p)]
    miss = [p for p in sub if not p[2]]; hit = [p for p in sub if p[2]]
    print("== %s: pairs %d, misses %d, hits %d" % (label, len(sub), len(miss), len(hit)))
    for flag in ("PRIMARY", "node_only_key_WIDE", "node_only_key_NARROW", "any_focus_node_WIDE", "query_rank_OOR",
                 "whole_rank_OOR", "part_rank_OOR", "key_pair_unseen_DESCRIPTIVE"):
        km, nm = share(miss, flag); kh, nh = share(hit, flag)
        sm = (100.0 * km / nm) if nm else None; sh = (100.0 * kh / nh) if nh else None
        diff = (sm - sh) if (sm is not None and sh is not None) else None
        print("   %-30s misses OOR %d/%d (%s%%)   hits OOR %d/%d (%s%%)   diff %s pp"
              % (flag, km, nm, sm, kh, nh, sh, diff))
    return miss, hit


report("ALL 6 receipts, DIRECT+parts", lambda p: True)
report("ALL 6 receipts, DIRECT", lambda p: flags[p[1]]["state"] == "DIRECT")
report("ALL 6 receipts, parts", lambda p: flags[p[1]]["state"] == "PARTS")
report("Helm 1.0, DIRECT+parts", lambda p: VERSION[p[0]] == "1.0")
report("Helm 2.0, DIRECT+parts", lambda p: VERSION[p[0]] == "2.0")

print("\nPer record: hits over 6 receipts, and per receipt correct bits (1.0 x3 then 2.0 x3):")
for rid in sorted(flags, key=lambda x: (flags[x]["state"], x)):
    bits = [int(c) for rd in RECEIPTS for (r2, rr, c, v) in pairs if r2 == rd and rr == rid]
    print("  %s %-6s whole=%s part=%s  hits %d/6  bits %s" % (rid[:20], flags[rid]["state"], flags[rid]["whole"],
                                                            flags[rid]["part"], sum(bits), bits))

print("\nWhat Helm answered on the misses (state / via / nodes), counted:")
for st in ("DIRECT", "PARTS"):
    c = Counter()
    for rd, rid, ok, v in pairs:
        if flags[rid]["state"] != st or ok: continue
        if st == "DIRECT":
            c[(v.get("state"), v.get("via") is not None)] += 1
        else:
            got = tuple(sorted(int(x.rpartition("/n")[2]) for x in v.get("nodes", []))); want = tuple(flags[rid]["kids"])
            c[("returned %d nodes vs %d true; %d of true included; extra ranks %s"
               % (len(got), len(want), len(set(got) & set(want)), sorted(set(got) - set(want))),)] += 1
    print("  ", st, dict(c))
