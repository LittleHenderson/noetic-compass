"""Do VIA answers need more than one hop, given that the query marks (is_whole_argument / is_part_argument) are
node INPUT features? For every reach record: BFS path length (checker rules re-implemented), and whether the
correct VIA node is a direct child of `whole` AND a direct parent of `part` (then a node's one-hop neighbourhood,
which includes its neighbours' mark columns, already identifies it). Then Helm accuracy per group. Pure JSON."""
import json, sys, os
from collections import Counter, defaultdict, deque
ROOT = sys.argv[1]
pub = json.load(open(os.path.join(ROOT, "records/typed_course_001/checks_002/public_course.json"), encoding="utf-8"))
W = {w["world_id"]: w for w in pub["bank"]["worlds"]}
reg = {r["record_id"]: r for r in pub["registry"]}
def adj(w):
    a = defaultdict(list)
    for e in w["contains"]:
        a[e["source"]].append(e["target"])
    return {k: sorted(v) for k, v in a.items()}
def bfs(a, s, g):
    prev = {s: None}; dq = deque([s])
    while dq:
        u = dq.popleft()
        if u == g:
            path = [u]
            while prev[path[-1]] is not None: path.append(prev[path[-1]])
            return path[::-1]
        for v in a.get(u, []):
            if v not in prev: prev[v] = u; dq.append(v)
    return None
def answer(rec):
    q = rec["query"]; w = W[q["focus_world_id"]]; a = adj(w)
    wh, pt = q["arguments"]["whole"], q["arguments"]["part"]
    if pt in a.get(wh, []): return ("DIRECT", None, 1)
    if q["rule"] == "first_direct_constituent_lexical_v1":
        for f in a.get(wh, []):
            p = bfs(a, f, pt)
            if p is not None: return ("VIA", f, len(p))      # edges = 1 + (len(p)-1)
        return ("ABSENT", None, None)
    p = bfs(a, wh, pt)
    if p is None: return ("ABSENT", None, None)
    return ("VIA", p[-2], len(p) - 1)
def group(rec):
    st, via, L = answer(rec)
    if st != "VIA": return st
    q = rec["query"]; a = adj(W[q["focus_world_id"]]); wh, pt = q["arguments"]["whole"], q["arguments"]["part"]
    one_hop = via in a.get(wh, []) and pt in a.get(via, [])
    return "VIA_via_is_child_of_whole_and_parent_of_part" if one_hop else "VIA_needs_longer_chain"
base = os.path.join(ROOT, "records", "typed_pointer_001")
reach_ids = [rid for rid, r in reg.items() if r["query"]["kind"] == "reach"]
print("reach records in course:", len(reach_ids), "groups:", dict(Counter(group(reg[r]) for r in reach_ids)))
print("rules:", dict(Counter(reg[r]["query"]["rule"] for r in reach_ids)))
held_q = ("7a391350", "a3e70de9")
for q in held_q:
    rid = [r for r in reach_ids if reg[r]["query"]["query_id"][12:20] == q][0]
    print("question", q, "answer", answer(reg[rid])[:2], "group", group(reg[rid]))
for rdir in ["receipt_helm1_certified_%s" % s for s in ("20260917", "20260918", "20260919")] + ["receipt_%s" % s for s in ("20260917", "20260918", "20260919")]:
    ck = os.path.join(base, rdir, "checkpoints")
    pm = json.load(open(os.path.join(ck, "protocol_material.json"), encoding="utf-8"))
    split = {**{r: "trained" for r in pm["trained_record_ids"]}, **{r: "held" for r in pm["held_back_record_ids"]}, **{r: "excluded" for r in pm["excluded_record_ids"]}}
    out = []
    for tag in ("course_p10", "ablation_round_mix"):
        path = os.path.join(ck, tag + "_scoring.json")
        if not os.path.exists(path): continue
        sc = {r["record_id"]: r["correct"] for r in json.load(open(path, encoding="utf-8"))["rows"]}
        tally = defaultdict(lambda: [0, 0])
        for rid in reach_ids:
            if rid not in sc: continue
            key = (split[rid] if tag == "course_p10" else "held", group(reg[rid]))
            tally[key][0] += sc[rid]; tally[key][1] += 1
        out.append(tag + ": " + "; ".join("%s/%s %d/%d" % (k[0], k[1][:22], v[0], v[1]) for k, v in sorted(tally.items())))
    print(rdir); [print("   ", o) for o in out]
