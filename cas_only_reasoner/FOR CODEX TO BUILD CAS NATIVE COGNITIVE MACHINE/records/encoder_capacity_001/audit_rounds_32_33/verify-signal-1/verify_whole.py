"""Follow-up: how much of the parts 'signal' is just 'the supplied whole is never its own part'?"""
import json, math, sys
from fractions import Fraction
from collections import Counter
exec(open("verify.py").read().split("frozen, _t, _ =")[0])  # imports + helpers only
frozen, _t, _ = worker_contract.load_material(HOME)
R = HOME / "records/typed_matched_001"
receipts = sorted(d for d in R.iterdir() if d.is_dir() and (d/"collected/results/artifacts/final_predictions.json").is_file())
cache = {}
T = Counter(); allA = []; perrun = {}
for rc in receipts:
    art = rc / "collected/results/artifacts"
    preds = json.loads((art/"final_predictions.json").read_text(encoding="utf-8"))["predictions"]
    kinds = {r["record_id"]: r["kind"] for r in json.loads((art/"final_scoring.json").read_text(encoding="utf-8"))["rows"]}
    S = Counter(); A = []
    for pr in preds:
        rid = pr["record_id"]
        if kinds[rid] != "parts": continue
        if rid not in cache:
            pk = course.model_packet(frozen, rid); q = pk["record"]["query"]
            plan = slots.compile_slots(pk)
            truth = set(checker.derive_target(pk["source"], q)["admissible_answers"][0]["value"]["nodes"])
            focus = next(w for w in pk["source"]["worlds"] if w["world_id"] == q["focus_world_id"])
            whole = q["arguments"]["whole"]
            k = sum(1 for e in focus["contains"] if e["source"] == whole)
            cache[rid] = (plan["slots"], truth, whole, k)
        ns, truth, whole, k = cache[rid]
        sc = pr["scores"]
        m = {s["coordinates"][0]: sc[s["slot_id"]]["PRESENT"] - sc[s["slot_id"]]["ABSENT"] for s in ns}
        refs = [s["coordinates"][0] for s in ns]
        order = sorted(refs, key=lambda r: m[r], reverse=True)
        S["q"] += 1
        S["whole_in_topk"] += whole in order[:k]
        S["whole_ranked_last"] += order[-1] == whole
        S["whole_argmax_PRESENT"] += m[whole] > 0
        S["asis_err_only_whole"] += ({r for r in refs if m[r] > 0} - {whole}) == truth and m[whole] > 0
        rest = [r for r in refs if r != whole]
        # rule: drop the whole, then top-k by margin among rest (same as top-k when whole not in top-k)
        o2 = sorted(rest, key=lambda r: m[r], reverse=True)
        S["topk_nowhole_exact"] += set(o2[:k]) == truth
        # rule: drop whole, keep machine's own threshold on rest (no k)
        S["thr_nowhole_exact"] += {r for r in rest if m[r] > 0} == truth
        if k == len(rest):
            S["trivial_after_whole_removed"] += 1
            S["trivial_topk_exact"] += set(order[:k]) == truth
        else:
            S["nontrivial"] += 1
            S["nontrivial_topk_exact"] += set(order[:k]) == truth
            S["nontrivial_rand_x"] += 0  # placeholder
            S["nontrivial_rand_num"] = S["nontrivial_rand_num"]
            A.append(mw([m[r] for r in rest if r in truth], [m[r] for r in rest if r not in truth]))
    perrun[rc.name] = (dict(S), float(sum(A)/len(A)))
    T.update(S); allA += A
for n, (S, a) in perrun.items():
    print(n, S, "AUC(excl whole, nontrivial)", round(a, 6))
print("POOLED", dict(T))
print("AUC excluding whole over nontrivial", len(allA), "questions:", sum(allA)/len(allA))
print(" AUC=1:", sum(1 for a in allA if a == 1), " AUC<0.5:", sum(1 for a in allA if a < Fraction(1,2)))
