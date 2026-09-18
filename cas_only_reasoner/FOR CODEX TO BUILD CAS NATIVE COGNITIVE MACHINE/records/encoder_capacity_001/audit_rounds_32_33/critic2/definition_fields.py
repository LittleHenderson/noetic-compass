"""Critic check on round 33 definition arm: how much does the machine's own 'whole' slot contribute?
Per-field independent accuracy; joint over the bank with and without the whole-slot score; and
whether the focus world wins. Read-only. Standard library + project pure modules."""
import json, pathlib, sys, time
from collections import Counter
HOME = pathlib.Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path.insert(0, str(HOME)); sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))
from cas_meta2.typed_teaching import checker, course, slots, worker_contract
t0 = time.time()
frozen, _t, _ = worker_contract.load_material(HOME)
R = HOME / "records/typed_matched_001"
receipts = sorted(d for d in R.iterdir() if d.is_dir() and (d/"collected/results/artifacts/final_predictions.json").is_file())
cache = {}; T = Counter()
for rc in receipts:
    art = rc / "collected/results/artifacts"
    preds = json.loads((art/"final_predictions.json").read_text(encoding="utf-8"))["predictions"]
    kinds = {r["record_id"]: r["kind"] for r in json.loads((art/"final_scoring.json").read_text(encoding="utf-8"))["rows"]}
    S = Counter()
    for pr in preds:
        rid = pr["record_id"]
        if kinds[rid] != "definition": continue
        if rid not in cache:
            pk = course.model_packet(frozen, rid); q = pk["record"]["query"]
            plan = slots.compile_slots(pk)
            by = {s["field"]: s for s in plan["slots"]}
            al = {w["world_id"]: w for w in plan["aliases"]["worlds"]}
            focus_alias = al[q["focus_world_id"]]
            fnode = {n["ref"]: n["alias"] for n in focus_alias["nodes"]}
            focus = next(w for w in pk["source"]["worlds"] if w["world_id"] == q["focus_world_id"])
            true = {"whole": fnode[focus["declared_whole"]], "kind_ref": focus_alias["alias"], "function_ref": focus_alias["alias"]}
            cands = []
            for w in pk["source"]["worlds"]:
                o = al[w["world_id"]]; dn = {n["ref"]: n["alias"] for n in o["nodes"]}
                tr = {"whole": dn.get(w["declared_whole"]), "kind_ref": o["alias"], "function_ref": o["alias"]}
                if tr["whole"] is None or any(tr[f] not in by[f]["symbols"] for f in tr): continue
                cands.append((w["world_id"], tr))
            cache[rid] = (by, true, cands, q["focus_world_id"])
        by, true, cands, fid = cache[rid]
        sc = pr["scores"]
        am = {f: max(by[f]["symbols"], key=lambda y, f=f: sc[by[f]["slot_id"]][y]) for f in by}
        for f in by: S["indep_"+f] += am[f] == true[f]
        S["indep_kind_and_function_same_world"] += am["kind_ref"] == am["function_ref"]
        def best(fields):
            return max(cands, key=lambda c: sum(sc[by[f]["slot_id"]][c[1][f]] for f in fields))[0]
        S["joint_all3_focus"] += best(("whole", "kind_ref", "function_ref")) == fid
        S["joint_kind_function_only_focus"] += best(("kind_ref", "function_ref")) == fid
        S["joint_whole_only_focus"] += best(("whole",)) == fid
        S["joint_kind_only_focus"] += best(("kind_ref",)) == fid
        S["joint_function_only_focus"] += best(("function_ref",)) == fid
        S["q"] += 1
    print(rc.name, dict(S), flush=True); T.update(S)
print("POOLED", dict(T)); print("secs", round(time.time()-t0,1))
