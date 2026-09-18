"""Independent re-measurement of auditor finding F1. Stdlib + project pure modules only."""
import json, pathlib, sys
from collections import Counter, defaultdict
from fractions import Fraction
HOME = pathlib.Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path.insert(0, str(HOME)); sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))
from cas_meta2.typed_teaching import answers, checker, course, slots, worker_contract


def P(a, b):
    return f"{a}/{b} = {100*a/b:.4f}%"


frozen, _, _ = worker_contract.load_material(HOME)
R = HOME / "records/typed_matched_001"
recs = sorted(d for d in R.iterdir() if d.is_dir() and (d / "collected/results/artifacts/final_predictions.json").is_file())
print("runs", [r.name for r in recs])
runs = {}
for r in recs:
    a = r / "collected/results/artifacts"
    preds = json.loads((a / "final_predictions.json").read_text(encoding="utf-8"))["predictions"]
    sc = {x["record_id"]: x for x in json.loads((a / "final_scoring.json").read_text(encoding="utf-8"))["rows"]}
    runs[r.name] = (preds, sc)
idsets = [frozenset(p["record_id"] for p in v[0]) for v in runs.values()]
print("identical id sets:", len(set(idsets)) == 1, "size", len(idsets[0]))
_, sc0 = next(iter(runs.values()))
kind = {rid: sc0[rid]["kind"] for rid in idsets[0]}
print("kind consistent across runs:", all(runs[n][1][rid]["kind"] == kind[rid] for n in runs for rid in kind))
print("kind counts", dict(Counter(kind.values())))

C = defaultdict(Counter)
cache = {}
for rid in sorted(idsets[0]):
    k_ = kind[rid]
    if k_ not in ("parts", "edge_account", "definition", "context"):
        continue
    pk = course.model_packet(frozen, rid)
    q = pk["record"]["query"]
    tgt = checker.derive_target(pk["source"], q)
    adm = {json.dumps(x["value"], sort_keys=True) for x in tgt["admissible_answers"]}
    C[k_]["q"] += 1
    C[k_]["n_admissible==1"] += len(adm) == 1
    truth = tgt["admissible_answers"][0]["value"]
    worlds = pk["source"]["worlds"]
    C[k_]["query_has_focus_world_id"] += bool(q.get("focus_world_id"))
    C[k_]["focus_eq_record_source_world_eq_packet_focus"] += (
        q["focus_world_id"] == pk["record"]["source_world_id"] == pk["source"]["focus_world_id"])
    f = [w for w in worlds if w["world_id"] == q["focus_world_id"]]
    assert len(f) == 1
    f = f[0]
    pairs = [(e["source"], e["target"]) for e in f["contains"]]
    C[k_]["contains_has_dup_pairs"] += len(pairs) != len(set(pairs))
    if k_ == "parts":
        wh = q["arguments"]["whole"]
        k = sum(1 for e in f["contains"] if e["source"] == wh)  # round-33 line 112
        C[k_]["k==len(truth.nodes)"] += k == len(truth["nodes"])
        mine = {"nodes": sorted({e["target"] for e in f["contains"] if e["source"] == wh})}
        C[k_]["k_hist_%d" % k] += 1
    elif k_ == "edge_account":
        k = len(f["contains"])  # round-33 line 108
        C[k_]["k==len(truth.edges)"] += k == len(truth["edges"])
        mine = {"edges": [{"source": s, "target": t} for s, t in sorted(set(pairs))]}
        C[k_]["k_hist_%d" % k] += 1
    elif k_ == "definition":
        mine = {"whole": f["declared_whole"], "kind_ref": f["world_id"] + "/decl/kind",
                "function_ref": f["world_id"] + "/decl/function"}
    else:
        mine = {"setting_ref": f["world_id"] + "/decl/setting",
                "participants": sorted(f["declarations"]["participants"])}
        C[k_]["participants_len_%d" % len(truth["participants"])] += 1
    C[k_]["packet_reader_correct"] += json.dumps(mine, sort_keys=True) in adm
    cache[rid] = (pk, q, tgt, adm, f)

for k_, c in C.items():
    print("\n[%s] q = %d" % (k_, c["q"]))
    for key in sorted(c):
        if key != "q":
            print("  %s: %s" % (key, P(c[key], c["q"])))

dleg = []
for rid, (pk, q, tgt, adm, f) in cache.items():
    if kind[rid] != "definition":
        continue
    plan = slots.compile_slots(pk)
    byf = {s["field"]: s for s in plan["slots"]}
    al = {w["world_id"]: w for w in plan["aliases"]["worlds"]}
    legal = []
    for w in pk["source"]["worlds"]:
        o = al[w["world_id"]]
        dec = {n["ref"]: n["alias"] for n in o["nodes"]}
        tr = {"whole": dec.get(w["declared_whole"]), "kind_ref": o["alias"], "function_ref": o["alias"]}
        if tr["whole"] is None or any(tr[x] not in byf[x]["symbols"] for x in tr):
            continue
        legal.append(w["world_id"])
    dleg.append((len(legal), q["focus_world_id"] in legal, len(pk["source"]["worlds"])))
n = len(dleg)
print("\n[definition candidates] questions", n)
print("bank sizes", dict(Counter(b for _, _, b in dleg)))
print("legal candidates: mean %.4f (sum %d), min %d max %d" % (
    sum(l for l, _, _ in dleg) / n, sum(l for l, _, _ in dleg), min(l for l, _, _ in dleg), max(l for l, _, _ in dleg)))
print("focus world is a legal candidate:", P(sum(fl for _, fl, _ in dleg), n))
u = sum(Fraction(1, l) for l, _, _ in dleg) / n
print("uniform pick expected exact rate: %.4f%%  (expected per 420: %.4f)" % (100 * float(u), 420 * float(u)))

tot = Counter()
per = Counter()
for name, (preds, sc) in runs.items():
    for p in preds:
        rid = p["record_id"]
        if kind[rid] != "definition":
            continue
        pk, q, tgt, adm, f = cache[rid]
        plan = slots.compile_slots(pk)
        byf = {s["field"]: s for s in plan["slots"]}
        al = {w["world_id"]: w for w in plan["aliases"]["worlds"]}
        s = p["scores"]
        best = bs = bw = None
        for w in pk["source"]["worlds"]:
            o = al[w["world_id"]]
            dec = {nn["ref"]: nn["alias"] for nn in o["nodes"]}
            tr = {"whole": dec.get(w["declared_whole"]), "kind_ref": o["alias"], "function_ref": o["alias"]}
            if tr["whole"] is None or any(tr[x] not in byf[x]["symbols"] for x in tr):
                continue
            t = sum(s[byf[x]["slot_id"]][v] for x, v in tr.items())
            if bs is None or t > bs:
                best, bs, bw = tr, t, w["world_id"]
        tot["q"] += 1
        tot["picked_focus_world"] += bw == q["focus_world_id"]
        sel = dict(p["decisions"]["selected"])
        for x, v in best.items():
            sel[byf[x]["slot_id"]] = v
        try:
            val = slots.assemble_answer(pk, {**p["decisions"], "selected": sel})["value"]
            ok = json.dumps(val, sort_keys=True) in adm
            tot["correct"] += ok
            per[name] += ok
        except Exception:
            tot["err"] += 1
        o = al[q["focus_world_id"]]
        dec = {nn["ref"]: nn["alias"] for nn in o["nodes"]}
        tr = {"whole": dec.get(f["declared_whole"]), "kind_ref": o["alias"], "function_ref": o["alias"]}
        sel2 = dict(p["decisions"]["selected"])
        for x, v in tr.items():
            sel2[byf[x]["slot_id"]] = v
        val2 = slots.assemble_answer(pk, {**p["decisions"], "selected": sel2})["value"]
        tot["focus_forced_correct"] += json.dumps(val2, sort_keys=True) in adm
print("\nround-33 definition arm re-run:", P(tot["correct"], tot["q"]), "| picked focus world",
      P(tot["picked_focus_world"], tot["q"]), "| errors", tot["err"])
print("per run correct:", dict(per))
print("force-FOCUS-triple arm:", P(tot["focus_forced_correct"], tot["q"]))
