"""(1) Validate my re-implemented reach answers against every saved Helm reach answer the frozen checker scored.
(2) Score a NO-LEARNING 'one step through a marked neighbour' rule on the frozen 18 population:
    DIRECT if whole->part; else VIA lexical-first v with whole->v and v->part; else ABSENT.
Pure JSON: public course + saved predictions/scoring + admission_001 gate reading (population ids)."""
import json, sys, os, importlib.util
from collections import Counter
ROOT = sys.argv[1]
spec = importlib.util.spec_from_file_location("rh", os.path.join(os.path.dirname(os.path.abspath(__file__)), "reach_hops_lib.py"))
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "reach_hops.py"), encoding="utf-8").read().split("base = os.path.join")[0]
ns = {"__name__": "lib"}; sys.argv = [sys.argv[0], ROOT]; exec(compile(src, "reach_hops", "exec"), ns)
reg, W, adj, answer, group = ns["reg"], ns["W"], ns["adj"], ns["answer"], ns["group"]
base = os.path.join(ROOT, "records", "typed_pointer_001")
# (1) validation
agree = Counter()
for rdir in ["receipt_helm1_certified_%s" % s for s in ("20260917", "20260918", "20260919")] + ["receipt_%s" % s for s in ("20260917", "20260918", "20260919")]:
    ck = os.path.join(base, rdir, "checkpoints")
    pred = {p["record_id"]: p for p in json.load(open(os.path.join(ck, "course_p10_predictions.json"), encoding="utf-8"))["predictions"]}
    for r in json.load(open(os.path.join(ck, "course_p10_scoring.json"), encoding="utf-8"))["rows"]:
        if r["kind"] != "reach": continue
        v = pred[r["record_id"]]["answer"]["value"]
        mine = answer(reg[r["record_id"]])
        same = (v.get("state"), v.get("via")) == mine[:2]
        agree[(r["correct"], same)] += 1
print("validation over 6 runs x 107 reach records, (checker correct, equals my reconstruction):", dict(agree))
if not agree: print("no rows")
# (2) the frozen 18
gr = json.load(open(os.path.join(base, "admission_001", "gate_reading.json"), encoding="utf-8"))
def find_pop(x):
    if isinstance(x, dict):
        for k, v in x.items():
            if k == "question_ids" and isinstance(v, list) and len(v) == 18:
                return v
            got = find_pop(v)
            if got: return got
    return None
pop = find_pop(gr)
print("frozen population found:", pop is not None, len(pop) if pop else None)
qrec = {}
for rid, r in reg.items():
    qrec.setdefault(r["query"]["query_id"], []).append(rid)
def one_step(rec):
    q = rec["query"]; a = adj(W[q["focus_world_id"]]); wh, pt = q["arguments"]["whole"], q["arguments"]["part"]
    if pt in a.get(wh, []): return ("DIRECT", None)
    for v in a.get(wh, []):
        if pt in a.get(v, []): return ("VIA", v)
    return ("ABSENT", None)
kinds = Counter(); solved = []
for qid in pop:
    recs = qrec[qid]; kind = reg[recs[0]]["query"]["kind"]; kinds[kind] += 1
    if kind == "reach":
        ok = all(one_step(reg[r]) == answer(reg[r])[:2] for r in recs)
        print("  reach %s records %d group %s | one-step rule exact on all records: %s" % (qid[12:20], len(recs), group(reg[recs[0]]), ok))
        if ok: solved.append(qid)
print("population kinds:", dict(kinds))
print("reach questions in the 18 solved by the one-step rule:", len(solved))
