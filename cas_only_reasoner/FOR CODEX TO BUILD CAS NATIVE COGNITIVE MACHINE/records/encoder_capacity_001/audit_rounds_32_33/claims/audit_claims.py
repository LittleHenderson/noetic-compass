"""Read-only audit of round 33 claims. Standard library + project pure modules. No torch."""
from __future__ import annotations

import itertools
import json
import math
import pathlib
import random
import sys
from collections import Counter, defaultdict

HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))
from cas_meta2.typed_teaching import checker, course, slots, worker_contract  # noqa: E402

RECEIPTS = HOME / "records/typed_matched_001"
KINDS = ("edge_account", "parts", "definition", "context")


def pct(a, b):
    return f"{a}/{b} = {100.0 * a / b:.4f}%" if b else f"{a}/0"


def auc(pos, neg):
    if not pos or not neg:
        return None
    wins = 0.0
    for p in pos:
        for n in neg:
            wins += 1.0 if p > n else 0.5 if p == n else 0.0
    return wins / (len(pos) * len(neg))


def main():
    frozen, _tok, _ = worker_contract.load_material(HOME)
    receipts = sorted(d for d in RECEIPTS.iterdir()
                      if d.is_dir() and (d / "collected/results/artifacts/final_predictions.json").is_file())
    print("runs:", [r.name for r in receipts])
    runs = {}
    for r in receipts:
        a = r / "collected/results/artifacts"
        preds = json.loads((a / "final_predictions.json").read_text(encoding="utf-8"))["predictions"]
        scoring = {row["record_id"]: row for row in
                   json.loads((a / "final_scoring.json").read_text(encoding="utf-8"))["rows"]}
        runs[r.name] = (preds, scoring)
    ids_by_run = {name: [p["record_id"] for p in preds] for name, (preds, _) in runs.items()}
    first = next(iter(ids_by_run.values()))
    print("same record ids in all runs:", all(sorted(v) == sorted(first) for v in ids_by_run.values()))
    kind_of = {rid: runs[next(iter(runs))][1][rid]["kind"] for rid in first}
    print("kind counts:", dict(Counter(kind_of.values())))

    # ---------- course-only facts per question ----------
    info = {}
    stats = defaultdict(Counter)
    for rid in first:
        kind = kind_of[rid]
        if kind not in KINDS:
            continue
        packet = course.model_packet(frozen, rid)
        query = packet["record"]["query"]
        plan = slots.compile_slots(packet)
        target = checker.derive_target(packet["source"], query)
        admissible = {json.dumps(x["value"], sort_keys=True) for x in target["admissible_answers"]}
        truth = target["admissible_answers"][0]["value"]
        focus = next(w for w in packet["source"]["worlds"] if w["world_id"] == query["focus_world_id"])
        st = stats[kind]
        st["questions"] += 1
        st["admissible_count_%d" % len(admissible)] += 1
        # Packet-only answer, no checker: read directly from the packet.
        if kind == "parts":
            whole = query["arguments"]["whole"]
            read = {"nodes": sorted(e["target"] for e in focus["contains"] if e["source"] == whole)}
        elif kind == "edge_account":
            read = {"edges": [{"source": a, "target": b} for a, b in
                              sorted((e["source"], e["target"]) for e in focus["contains"])]}
        elif kind == "definition":
            read = {"whole": focus["declared_whole"],
                    "kind_ref": truth["kind_ref"] if False else None}
            # build via the declaration-ref helper only from packet fields
            from cas_meta2.typed_teaching import answers as A
            read = {"whole": focus["declared_whole"],
                    "kind_ref": A.declaration_ref(focus["world_id"], "kind"),
                    "function_ref": A.declaration_ref(focus["world_id"], "function")}
        elif kind == "context":
            from cas_meta2.typed_teaching import answers as A
            read = {"setting_ref": A.declaration_ref(focus["world_id"], "setting"),
                    "participants": sorted(focus["declarations"]["participants"])}
        st["packet_read_correct"] += 1 if json.dumps(read, sort_keys=True) in admissible else 0

        rec = {"packet": packet, "plan": plan, "admissible": admissible, "truth": truth, "focus": focus,
               "query": query}
        if kind in ("parts", "edge_account"):
            field = "node" if kind == "parts" else "edge"
            cands = [s for s in plan["slots"] if s["field"] == field]
            if kind == "parts":
                whole = query["arguments"]["whole"]
                k = sum(1 for e in focus["contains"] if e["source"] == whole)
                truth_set = set(truth["nodes"])
                truth_slots = {s["slot_id"] for s in cands if s["coordinates"][0] in truth_set}
            else:
                k = len(focus["contains"])
                truth_set = {(e["source"], e["target"]) for e in truth["edges"]}
                truth_slots = {s["slot_id"] for s in cands if tuple(s["coordinates"]) in truth_set}
            n = len(cands)
            st["k_equals_true_answer_size"] += 1 if k == len(truth_slots) else 0
            st["k_equals_len_truth_value"] += 1 if k == len(truth_set) else 0
            st["k0_or_kn_(answer_forced_by_k_alone)"] += 1 if k in (0, n) else 0
            st["n_%d_k_%d" % (n, k)] += 1
            st["_randk_expected_x1e6"] += round(1e6 / math.comb(n, k)) if k <= n else 0
            rec.update(k=k, n=n, cands=cands, truth_slots=truth_slots)
        if kind == "definition":
            by_field = {s["field"]: s for s in plan["slots"]}
            aliases = {w["world_id"]: w for w in plan["aliases"]["worlds"]}
            legal, focus_legal = 0, False
            for w in packet["source"]["worlds"]:
                other = aliases[w["world_id"]]
                declared = {nd["ref"]: nd["alias"] for nd in other["nodes"]}
                triple = {"whole": declared.get(w["declared_whole"]), "kind_ref": other["alias"],
                          "function_ref": other["alias"]}
                if triple["whole"] is None or any(triple[f] not in by_field[f]["symbols"] for f in triple):
                    continue
                legal += 1
                if w["world_id"] == query["focus_world_id"]:
                    focus_legal = True
            st["bank_worlds_total_sum"] += len(packet["source"]["worlds"])
            st["legal_candidates_sum"] += legal
            st["_uniform_pick_expected_x1e6"] += round(1e6 / legal) if legal else 0
            st["focus_is_a_legal_candidate"] += 1 if focus_legal else 0
            st["query_carries_focus_world_id"] += 1 if query.get("focus_world_id") else 0
        info[rid] = rec

    print("\n==== COURSE-ONLY FACTS (per question; same set of records in every run) ====")
    for kind in KINDS:
        st = stats[kind]
        q = st["questions"]
        print(f"\n[{kind}] questions per run = {q}")
        for key in sorted(st):
            if key == "questions":
                continue
            v = st[key]
            if key.startswith("_"):
                print(f"   {key[1:]}: expected exact rate = {v / 1e6 / q * 100:.4f}%")
            elif key.endswith("_sum"):
                print(f"   {key}: total {v}, mean {v / q:.4f}")
            else:
                print(f"   {key}: {pct(v, q)}")

    # ---------- recorded-score facts: rank AUC, and random-with-k baseline ----------
    print("\n==== RECORDED SCORES: ranking signal (AUC of PRESENT-ABSENT margin), per run ====")
    rng = random.Random(20260918)
    for name, (preds, scoring) in runs.items():
        for kind in ("parts", "edge_account"):
            pos, neg = [], []
            within = []
            constrained_ok = rand_ok = 0
            bits_after = bits_total = 0
            q = 0
            for p in preds:
                rid = p["record_id"]
                if kind_of[rid] != kind:
                    continue
                rec = info[rid]
                sc = p["scores"]
                q += 1
                m = {s["slot_id"]: sc[s["slot_id"]]["PRESENT"] - sc[s["slot_id"]]["ABSENT"] for s in rec["cands"]}
                pq = [m[s] for s in m if s in rec["truth_slots"]]
                nq = [m[s] for s in m if s not in rec["truth_slots"]]
                pos += pq
                neg += nq
                a = auc(pq, nq)
                if a is not None:
                    within.append(a)
                ranked = sorted(rec["cands"], key=lambda s: m[s["slot_id"]], reverse=True)
                chosen = {s["slot_id"] for s in ranked[:rec["k"]]}
                constrained_ok += 1 if chosen == rec["truth_slots"] else 0
                bits_after += sum(1 for s in rec["cands"] if (s["slot_id"] in chosen) == (s["slot_id"] in rec["truth_slots"]))
                bits_total += len(rec["cands"])
                shuffled = list(rec["cands"])
                rng.shuffle(shuffled)
                rchosen = {s["slot_id"] for s in shuffled[:rec["k"]]}
                rand_ok += 1 if rchosen == rec["truth_slots"] else 0
            pooled = auc(pos, neg)
            mean_within = sum(within) / len(within) if within else float("nan")
            print(f"{name:>20} {kind:>13} q={q} pooled_AUC={pooled:.4f} mean_within_question_AUC={mean_within:.4f}"
                  f" (n_q_with_both={len(within)}) topk_exact(recomputed)={pct(constrained_ok, q)}"
                  f" random_rank_with_k_exact(1 draw)={pct(rand_ok, q)} per_bit_after_topk={pct(bits_after, bits_total)}")


if __name__ == "__main__":
    main()
