"""Audit add-on: confusion table of the fitted readout on edge_account slots (same fit as field_bottleneck)."""
import sys, json, struct, pathlib
from collections import Counter
REC = pathlib.Path(r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\records\encoder_capacity_001")
sys.path.insert(0, str(REC))
import measure_field_bottleneck as M

frozen_course, tokenizer, _ = M.worker_contract.load_material(M.HOME)
projection = M.gate(tokenizer)
preds = json.loads((M.RECEIPT / "collected/results/artifacts/final_predictions.json").read_text(encoding="utf-8"))["predictions"]
cases = []
for index, p in enumerate(preds):
    packet = M.course.model_packet(frozen_course, p["record_id"])
    q = packet["record"]["query"]
    if q["kind"] not in M.MANY: continue
    plan = M.slots.compile_slots(packet); validated = M.slots.validate_plan(packet, plan)
    truth = M.checker.derive_target(packet["source"], q)["admissible_answers"][0]
    pv = M.packet_vector(packet, tokenizer, projection)
    rows = []
    for slot in plan["slots"]:
        spec = M.binding._query_spec(validated, slot)
        qv = list(struct.unpack(f"<{M.D_MODEL}f", M.binding.row_bytes(["query", spec], seed=M.SEED)))
        rows.append({"symbols": list(slot["symbols"]), "encoded": M.unit([pv[a]+qv[a] for a in range(M.D_MODEL)]),
                     "label": M.true_symbol(plan["kind"], slot, truth["value"], plan),
                     "self_loop": plan["kind"]=="edge_account" and slot["coordinates"][0]==slot["coordinates"][1]})
    cases.append({"fold": index % M.FOLDS, "kind": plan["kind"], "rows": rows})

conf = Counter(); per_q = []; selfloop = Counter()
for fold in range(M.FOLDS):
    train = [(M.tanh_vector(r["encoded"]), M.SYMBOL_INDEX[r["label"]]) for c in cases if c["fold"] != fold for r in c["rows"]]
    W = M.ridge_weights([x for x,_ in train], [y for _,y in train], nclass=len(M.slots.SYMBOLS), lam=M.LAMBDA)
    for c in cases:
        if c["fold"] != fold or c["kind"] != "edge_account": continue
        wrong = 0
        for r in c["rows"]:
            v = M.tanh_vector(r["encoded"])
            s = {sym: sum(W[a][M.SYMBOL_INDEX[sym]]*v[a] for a in range(M.D_MODEL)) for sym in r["symbols"]}
            b = max(s.values()); pick = sorted(k for k,x in s.items() if x==b)[0]
            conf[(r["label"], pick)] += 1; wrong += pick != r["label"]
            if r["self_loop"]: selfloop[(r["label"], pick)] += 1
        per_q.append((len(c["rows"]), wrong, sum(r["label"]=="PRESENT" for r in c["rows"])))

tp, fn = conf[("PRESENT","PRESENT")], conf[("PRESENT","ABSENT")]
tn, fp = conf[("ABSENT","ABSENT")], conf[("ABSENT","PRESENT")]
n = tp+fn+tn+fp
print(f"edge slots: {n}   truly PRESENT: {tp+fn}   truly ABSENT: {tn+fp}")
print(f"  truly PRESENT -> said PRESENT {tp}, said ABSENT {fn}   (edges found: {tp/(tp+fn):.4%})")
print(f"  truly ABSENT  -> said ABSENT  {tn}, said PRESENT {fp}   (non-edges right: {tn/(tn+fp):.4%})")
print(f"  per-slot accuracy        : {(tp+tn)/n:.4%}")
print(f"  always-ABSENT per slot   : {(tn+fp)/n:.4%}")
print(f"  balanced accuracy        : {(tp/(tp+fn)+tn/(tn+fp))/2:.4%}   (coin flip = 50.0000%)")
print(f"  said PRESENT in total    : {tp+fp} times, right {tp} of those ({tp/max(1,tp+fp):.4%})")
print(f"  self-loop slots (a->a)   : {dict(selfloop)}")
print(f"  questions: {len(per_q)}   fully right: {sum(w==0 for _,w,_ in per_q)}   questions with zero true edges: {sum(k==0 for *_,k in per_q)}")
print(f"  wrong-slot histogram     : {sorted(Counter(w for _,w,_ in per_q).items())}")
