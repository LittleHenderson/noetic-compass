"""Ten-node development panel (59 questions: 53 reach, 6 parts). Score NO-LEARNING rules that a ONE-HOP network
could compute (given the whole/part mark columns), and compare with Helm's saved dev scores.
Validate the reconstructed answers against every saved Helm dev answer the checker scored. Pure JSON."""
import json, sys, os
from collections import Counter, defaultdict, deque
ROOT = sys.argv[1]
base = os.path.join(ROOT, "records", "typed_pointer_001")
pm = json.load(open(os.path.join(base, "receipt_20260918", "checkpoints", "protocol_material.json"), encoding="utf-8"))["development"]
packets = {p["record"]["record_id"]: p for p in pm["packets"]}
def world(p):
    fid = p["record"]["query"]["focus_world_id"]
    return [w for w in p["source"]["worlds"] if w["world_id"] == fid][0]
def adj(w):
    a = defaultdict(list)
    for e in w["contains"]: a[e["source"]].append(e["target"])
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
def checker(p):
    q = p["record"]["query"]; a = adj(world(p))
    if q["kind"] == "parts": return ("PARTS", tuple(a.get(q["arguments"]["whole"], [])))
    wh, pt = q["arguments"]["whole"], q["arguments"]["part"]
    if pt in a.get(wh, []): return ("DIRECT", None)
    assert q["rule"] == "first_direct_constituent_lexical_v1"
    for f in a.get(wh, []):
        if bfs(a, f, pt) is not None: return ("VIA", f)
    return ("ABSENT", None)
def one_step(p):
    q = p["record"]["query"]; a = adj(world(p))
    if q["kind"] == "parts": return ("PARTS", tuple(a.get(q["arguments"]["whole"], [])))
    wh, pt = q["arguments"]["whole"], q["arguments"]["part"]
    if pt in a.get(wh, []): return ("DIRECT", None)
    for v in a.get(wh, []):
        if pt in a.get(v, []): return ("VIA", v)
    return ("ABSENT", None)
def first_child(p):
    q = p["record"]["query"]; a = adj(world(p))
    if q["kind"] == "parts": return ("PARTS", tuple(a.get(q["arguments"]["whole"], [])))
    wh, pt = q["arguments"]["whole"], q["arguments"]["part"]
    if pt in a.get(wh, []): return ("DIRECT", None)
    kids = a.get(wh, [])
    return ("VIA", kids[0]) if kids else ("ABSENT", None)
ans = {rid: checker(p) for rid, p in packets.items()}
print("dev questions:", len(ans), "answer states:", dict(Counter(v[0] for v in ans.values())))
for name, f in (("one-step rule (DIRECT / VIA through a marked neighbour / ABSENT; parts = children)", one_step),
                ("first-child rule (DIRECT / lexical-first child of whole / ABSENT; parts = children)", first_child),
                ("always ABSENT-or-DIRECT-if-edge, parts = children", lambda p: ("PARTS", tuple(adj(world(p)).get(p["record"]["query"]["arguments"]["whole"], []))) if p["record"]["query"]["kind"] == "parts" else (("DIRECT", None) if p["record"]["query"]["arguments"]["part"] in adj(world(p)).get(p["record"]["query"]["arguments"]["whole"], []) else ("ABSENT", None)))):
    hits = Counter(p["record"]["query"]["kind"] for rid, p in packets.items() if f(p) == ans[rid])
    print("  %-85s %d / 59  %s" % (name, sum(hits.values()), dict(hits)))
agree = Counter()
for rdir in ["receipt_helm1_certified_%s" % s for s in ("20260917", "20260918", "20260919")] + ["receipt_%s" % s for s in ("20260917", "20260918", "20260919")]:
    ck = os.path.join(base, rdir, "checkpoints")
    pred = {p["record_id"]: p for p in json.load(open(os.path.join(ck, "development_p10_predictions.json"), encoding="utf-8"))["predictions"]}
    rows = json.load(open(os.path.join(ck, "development_p10_scoring.json"), encoding="utf-8"))["rows"]
    tot = Counter()
    for r in rows:
        v = pred[r["record_id"]]["answer"]["value"]; mine = ans[r["record_id"]]
        if mine[0] == "PARTS":
            same = tuple(sorted(v.get("nodes", []))) == tuple(sorted(mine[1]))
        else:
            same = (v.get("state"), v.get("via")) == mine
        agree[(r["correct"], same)] += 1; tot[r["correct"]] += 1
    print("  %s dev p10 correct %d / %d" % (rdir, tot[True], sum(tot.values())))
print("validation (checker correct, equals my reconstruction):", dict(agree))
print("per-state accuracy on the dev panel (truth state: correct / n):")
for rdir in ["receipt_helm1_certified_%s" % s for s in ("20260917", "20260918", "20260919")] + ["receipt_%s" % s for s in ("20260917", "20260918", "20260919")]:
    ck = os.path.join(base, rdir, "checkpoints")
    rows = json.load(open(os.path.join(ck, "development_p10_scoring.json"), encoding="utf-8"))["rows"]
    t = defaultdict(lambda: [0, 0])
    for r in rows:
        st = ans[r["record_id"]][0]; t[st][0] += r["correct"]; t[st][1] += 1
    print("  %s %s" % (rdir, "; ".join("%s %d/%d" % (k, v[0], v[1]) for k, v in sorted(t.items()))))
