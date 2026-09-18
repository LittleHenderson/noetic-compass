"""Critic check: does ranking by PRESENT alone (committed cncm/answer_constraints._apply_cardinality)
vs PRESENT-minus-ABSENT (round 33 script) explain parts 257/318 vs 277/318 and edge 0 vs 18 of 420?
Read-only. Standard library + project pure modules."""
import json, pathlib, sys, time
from collections import Counter
HOME = pathlib.Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path.insert(0, str(HOME)); sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))
from cas_meta2.typed_teaching import checker, course, slots, worker_contract
t0 = time.time()
frozen, _t, _ = worker_contract.load_material(HOME)
print("loaded", round(time.time()-t0,1), flush=True)
R = HOME / "records/typed_matched_001"
receipts = sorted(d for d in R.iterdir() if d.is_dir() and (d/"collected/results/artifacts/final_predictions.json").is_file())
cache = {}
T = Counter()
for rc in receipts:
    art = rc / "collected/results/artifacts"
    preds = json.loads((art/"final_predictions.json").read_text(encoding="utf-8"))["predictions"]
    kinds = {r["record_id"]: r["kind"] for r in json.loads((art/"final_scoring.json").read_text(encoding="utf-8"))["rows"]}
    S = Counter()
    for pr in preds:
        rid = pr["record_id"]; kind = kinds[rid]
        if kind not in ("parts", "edge_account"): continue
        if rid not in cache:
            pk = course.model_packet(frozen, rid); q = pk["record"]["query"]
            plan = slots.compile_slots(pk)
            tgt = checker.derive_target(pk["source"], q)
            adm = {json.dumps(a["value"], sort_keys=True) for a in tgt["admissible_answers"]}
            focus = next(w for w in pk["source"]["worlds"] if w["world_id"] == q["focus_world_id"])
            if kind == "parts":
                whole = q["arguments"]["whole"]; fld = "node"
                k = sum(1 for e in focus["contains"] if e["source"] == whole)
                excl = lambda s, whole=whole: s["coordinates"][0] == whole
            else:
                fld = "edge"; k = len(focus["contains"])
                excl = lambda s: s["coordinates"][0] == s["coordinates"][1]
            cache[rid] = (pk, plan, adm, fld, k, excl)
        pk, plan, adm, fld, k, excl = cache[rid]
        sc = pr["scores"]
        base = {s["slot_id"]: max(s["symbols"], key=lambda y, s=s: sc[s["slot_id"]][y]) for s in plan["slots"]}
        def ok(sel):
            try:
                v = slots.assemble_answer(pk, {**pr["decisions"], "selected": sel})["value"]
            except Exception:
                return False
            return json.dumps(v, sort_keys=True) in adm
        field_slots = [s for s in plan["slots"] if s["field"] == fld]
        for rule in ("margin", "present"):
            for excl_on in (False, True):
                sel = dict(base)
                cands = field_slots
                if excl_on:
                    for s in field_slots:
                        if excl(s): sel[s["slot_id"]] = "ABSENT"
                    cands = [s for s in field_slots if not excl(s)]
                key = (lambda s: -(sc[s["slot_id"]]["PRESENT"] - sc[s["slot_id"]]["ABSENT"])) if rule == "margin" else (lambda s: -sc[s["slot_id"]]["PRESENT"])
                ranked = sorted(cands, key=lambda s: (key(s), s["slot_id"]))
                for i, s in enumerate(ranked):
                    sel[s["slot_id"]] = "PRESENT" if i < k else "ABSENT"
                S[(kind, rule, "excl" if excl_on else "all")] += ok(sel)
        # self-exclusion only, no cardinality
        sel = dict(base)
        for s in field_slots:
            if excl(s): sel[s["slot_id"]] = "ABSENT"
        S[(kind, "none", "excl")] += ok(sel)
        S[(kind, "q")] += 1
    print(rc.name, sorted(S.items()), flush=True)
    T.update(S)
print("POOLED")
for kk in sorted(T): print(kk, T[kk])
print("secs", round(time.time()-t0,1))
