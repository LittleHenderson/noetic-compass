"""Round-32 context: is k constant, how much does k alone give, and do the recorded scores rank?"""
from __future__ import annotations

import json
import math
import pathlib
import sys
from collections import Counter

HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))
from cas_meta2.typed_teaching import checker, course, slots, worker_contract  # noqa: E402

RECEIPTS = HOME / "records/typed_matched_001"


def auc(pos, neg):
    w = sum(1.0 if p > n else 0.5 if p == n else 0.0 for p in pos for n in neg)
    return w / (len(pos) * len(neg)) if pos and neg else None


def main():
    frozen, _t, _ = worker_contract.load_material(HOME)
    receipts = sorted(d for d in RECEIPTS.iterdir()
                      if d.is_dir() and (d / "collected/results/artifacts/final_predictions.json").is_file())
    cache = {}
    for r in receipts:
        a = r / "collected/results/artifacts"
        preds = json.loads((a / "final_predictions.json").read_text(encoding="utf-8"))["predictions"]
        scoring = {row["record_id"]: row for row in json.loads((a / "final_scoring.json").read_text(encoding="utf-8"))["rows"]}
        nk = Counter()
        exp = 0.0
        q = topk_ok = tp_only = tp_tn = bits = 0
        pos, neg = [], []
        for p in preds:
            rid = p["record_id"]
            if scoring[rid]["kind"] != "context":
                continue
            if rid not in cache:
                packet = course.model_packet(frozen, rid)
                plan = slots.compile_slots(packet)
                target = checker.derive_target(packet["source"], packet["record"]["query"])
                truth = target["admissible_answers"][0]["value"]
                focus = next(w for w in packet["source"]["worlds"] if w["world_id"] == packet["record"]["query"]["focus_world_id"])
                cache[rid] = (plan, truth, focus)
            plan, truth, focus = cache[rid]
            part = [s for s in plan["slots"] if s["field"] == "participant"]
            tset = set(truth["participants"])
            k_truth = len(tset)
            k_packet = len(focus["declarations"]["participants"])
            n = len(part)
            nk[(n, k_truth, k_packet, focus["declarations"].get("participants_basis"))] += 1
            exp += 1.0 / math.comb(n, k_truth)
            q += 1
            sc = p["scores"]
            m = {s["slot_id"]: sc[s["slot_id"]]["PRESENT"] - sc[s["slot_id"]]["ABSENT"] for s in part}
            ranked = sorted(part, key=lambda s: m[s["slot_id"]], reverse=True)
            chosen = {s["coordinates"][0] for s in ranked[:k_truth]}
            topk_ok += 1 if chosen == tset else 0
            tp_only += sum(1 for s in ranked[:k_truth] if s["coordinates"][0] in tset)
            tp_tn += sum(1 for s in part if (s["coordinates"][0] in chosen) == (s["coordinates"][0] in tset))
            bits += n
            pos += [m[s["slot_id"]] for s in part if s["coordinates"][0] in tset]
            neg += [m[s["slot_id"]] for s in part if s["coordinates"][0] not in tset]
        print(f"{r.name}: q={q} (n,k_truth,k_packet,basis) counts={dict(nk)}")
        print(f"   random-rank-with-k expected participant-set exact = {100 * exp / q:.4f}%  (sum 1/C(n,k) = {exp:.4f} of {q})")
        print(f"   recorded top-k participant-set exact = {topk_ok}/{q} = {100 * topk_ok / q:.4f}%")
        print(f"   pooled AUC of margin, true vs false participants = {auc(pos, neg):.4f}")
        print(f"   round-32 'bits top3' formula (TP only / all bits) = {tp_only}/{bits} = {100 * tp_only / bits:.4f}%;"
              f" true per-bit accuracy after top-k (TP+TN) = {tp_tn}/{bits} = {100 * tp_tn / bits:.4f}%")


if __name__ == "__main__":
    main()
