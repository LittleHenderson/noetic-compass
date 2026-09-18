"""Parts: is the supplied `whole` always a candidate slot and never a true part? Score-free baseline odds."""
import sys, json, pathlib
from math import comb
HOME = pathlib.Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path.insert(0, str(HOME)); sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))
from cas_meta2.typed_teaching import checker, course, slots, worker_contract
fc, _, _ = worker_contract.load_material(HOME)
R = HOME / "records/typed_matched_001"
tot = dict(q=0, whole_slot=0, whole_true=0, rand_k=0.0, rand_k_nowhole=0.0, machine=0, machine_nowhole=0)
for run in sorted(d for d in R.iterdir() if (d / "collected/results/artifacts/final_predictions.json").is_file()):
    preds = json.loads((run / "collected/results/artifacts/final_predictions.json").read_text(encoding="utf-8"))["predictions"]
    kinds = {r["record_id"]: r["kind"] for r in json.loads((run / "collected/results/artifacts/final_scoring.json").read_text(encoding="utf-8"))["rows"]}
    for p in preds:
        if kinds[p["record_id"]] != "parts": continue
        pk = course.model_packet(fc, p["record_id"]); q = pk["record"]["query"]
        if q["kind"] != "parts": continue
        plan = slots.compile_slots(pk); whole = q["arguments"]["whole"]
        truth = set(checker.derive_target(pk["source"], q)["admissible_answers"][0]["value"]["nodes"])
        cand = [s for s in plan["slots"] if s["field"] == "node"]; n = len(cand); k = len(truth)
        refs = [s["coordinates"][0] for s in cand]
        tot["q"] += 1; tot["whole_slot"] += whole in refs; tot["whole_true"] += whole in truth
        tot["rand_k"] += 1 / comb(n, k)
        tot["rand_k_nowhole"] += 1 / comb(n - (whole in refs), k)
        m = {s["coordinates"][0]: p["scores"][s["slot_id"]]["PRESENT"] - p["scores"][s["slot_id"]]["ABSENT"] for s in cand}
        tot["machine"] += set(sorted(m, key=m.get, reverse=True)[:k]) == truth
        m2 = {r: v for r, v in m.items() if r != whole}
        tot["machine_nowhole"] += set(sorted(m2, key=m2.get, reverse=True)[:k]) == truth
Q = tot["q"]
print(f"parts question-runs: {Q}   whole is a candidate slot: {tot['whole_slot']}/{Q}   whole is a true part: {tot['whole_true']}/{Q}")
for key, label in [("rand_k", "count k + random pick (no scores)"), ("rand_k_nowhole", "count k + skip the whole + random pick (no scores)")]:
    print(f"  {label:52s} expected {tot[key]:.4f}/{Q} = {tot[key]/Q:.4%}")
print(f"  {'count k + machine margin top-k (round 33)':52s} {tot['machine']}/{Q} = {tot['machine']/Q:.4%}")
print(f"  {'count k + skip the whole + machine top-k':52s} {tot['machine_nowhole']}/{Q} = {tot['machine_nowhole']/Q:.4%}")
