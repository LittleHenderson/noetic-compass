"""Structure only (no machine scores): how many candidates n, how many true k, random top-k odds."""
import sys, json, pathlib
from math import comb
from collections import Counter
HOME = pathlib.Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE")
sys.path.insert(0, str(HOME)); sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))
from cas_meta2.typed_teaching import checker, course, slots, worker_contract
fc, _, _ = worker_contract.load_material(HOME)
preds = json.loads((HOME / "records/typed_matched_001/receipt_20260919_m/collected/results/artifacts/final_predictions.json").read_text(encoding="utf-8"))["predictions"]
FIELD = {"parts": "node", "edge_account": "edge", "context": "participant"}
hist = {k: Counter() for k in FIELD}; exp = Counter(); cnt = Counter(); forced = Counter(); defn = Counter()
for p in preds:
    pk = course.model_packet(fc, p["record_id"]); q = pk["record"]["query"]; kind = q["kind"]
    if kind == "definition":
        defn[len(pk["source"]["worlds"])] += 1; continue
    if kind not in FIELD: continue
    plan = slots.compile_slots(pk)
    focus = next(w for w in pk["source"]["worlds"] if w["world_id"] == q["focus_world_id"])
    n = sum(1 for s in plan["slots"] if s["field"] == FIELD[kind])
    if kind == "edge_account": k = len(focus["contains"])
    elif kind == "parts": k = sum(1 for e in focus["contains"] if e["source"] == q["arguments"]["whole"])
    else: k = 3
    hist[kind][(n, k)] += 1; cnt[kind] += 1
    if k <= n: exp[kind] += 1 / comb(n, k); forced[kind] += comb(n, k) == 1
for kind in FIELD:
    print(f"{kind:13s} questions {cnt[kind]}  (n,k) {dict(sorted(hist[kind].items()))}")
    print(f"{'':13s} forced by count alone (C(n,k)=1): {forced[kind]}/{cnt[kind]}   random top-k expected exact: {exp[kind]:.4f}/{cnt[kind]} = {exp[kind]/cnt[kind]:.4%}")
print("definition: worlds per packet ->", dict(defn))
