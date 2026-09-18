"""Independent re-measurement of finding F3 (edge_account negative). Read-only. Stdlib + project pure modules."""
from __future__ import annotations

import json
import math
import pathlib
import random
import sys
from collections import Counter
from fractions import Fraction

HOME = pathlib.Path(
    r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner"
    r"\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE\_worktrees\vision-next"
    r"\cas_only_reasoner\FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
)
sys.path.insert(0, str(HOME))
sys.path.insert(0, str(HOME / "research" / "CAS_META_2_COMPOSITION"))
from cas_meta2.typed_teaching import checker, course, slots, worker_contract  # noqa: E402

RECEIPTS = HOME / "records/typed_matched_001"
NPERM = 2000


def P(a, b):
    return f"{a}/{b} = {100.0 * a / b:.4f}%"


def mw_auc(pairs):
    """pairs: list of (score, is_pos). Mann-Whitney AUC with ties = 0.5, via average ranks."""
    pairs = sorted(pairs, key=lambda t: t[0])
    n = len(pairs)
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and pairs[j + 1][0] == pairs[i][0]:
            j += 1
        r = (i + j) / 2.0 + 1.0
        for t in range(i, j + 1):
            ranks[t] = r
        i = j + 1
    npos = sum(1 for _, y in pairs if y)
    nneg = n - npos
    if npos == 0 or nneg == 0:
        return None
    rs = sum(r for r, (_, y) in zip(ranks, pairs) if y)
    return (rs - npos * (npos + 1) / 2.0) / (npos * nneg)


def main():
    frozen, _tok, _ = worker_contract.load_material(HOME)
    receipts = sorted(d for d in RECEIPTS.iterdir()
                      if d.is_dir() and (d / "collected/results/artifacts/final_predictions.json").is_file())
    print("runs:", [r.name for r in receipts], flush=True)

    # Per-question course facts (run independent).
    qinfo = {}
    first_preds = json.loads((receipts[0] / "collected/results/artifacts/final_predictions.json")
                             .read_text(encoding="utf-8"))["predictions"]
    first_scoring = {row["record_id"]: row for row in json.loads(
        (receipts[0] / "collected/results/artifacts/final_scoring.json").read_text(encoding="utf-8"))["rows"]}
    for pred in first_preds:
        rid = pred["record_id"]
        kind = first_scoring[rid]["kind"]
        if kind not in ("edge_account", "parts"):
            continue
        packet = course.model_packet(frozen, rid)
        query = packet["record"]["query"]
        plan = slots.compile_slots(packet)
        target = checker.derive_target(packet["source"], query)
        adm = {json.dumps(a["value"], sort_keys=True) for a in target["admissible_answers"]}
        truth = target["admissible_answers"][0]["value"]
        field = "edge" if kind == "edge_account" else "node"
        cands = [s for s in plan["slots"] if s["field"] == field]
        # Independent truth-slot derivation: flip each slot alone and see if assembled answer contains it.
        # Simpler & direct: build truth selection by trying membership via assemble of the truth-set.
        if kind == "edge_account":
            tset = {(e["source"], e["target"]) for e in truth["edges"]}
            tslots = {s["slot_id"] for s in cands if (s["coordinates"][0], s["coordinates"][1]) in tset}
        else:
            tset = set(truth["nodes"])
            tslots = {s["slot_id"] for s in cands if s["coordinates"][0] in tset}
        # Validate mapping by assembling the truth selection through the project's own assembler.
        sel = {s["slot_id"]: ("PRESENT" if s["slot_id"] in tslots else "ABSENT") for s in cands}
        other = [s for s in plan["slots"] if s["field"] != field]
        assert not other, (kind, [s["field"] for s in other])
        dec = {**pred["decisions"], "selected": sel}
        val = slots.assemble_answer(packet, dec)["value"]
        assert json.dumps(val, sort_keys=True) in adm, rid
        assert len(tslots) == len(tset), rid
        focus = next(w for w in packet["source"]["worlds"] if w["world_id"] == query["focus_world_id"])
        if kind == "edge_account":
            k = len(focus["contains"])
        else:
            k = sum(1 for e in focus["contains"] if e["source"] == query["arguments"]["whole"])
        qinfo[rid] = dict(kind=kind, cands=[s["slot_id"] for s in cands], tslots=tslots, k=k, n=len(cands),
                          adm=adm, packet=packet)
    print("truth-selection assembled == admissible for every question: OK", flush=True)

    for kind in ("edge_account", "parts"):
        qs = [r for r in qinfo if qinfo[r]["kind"] == kind]
        shape = Counter((qinfo[r]["n"], qinfo[r]["k"], len(qinfo[r]["tslots"])) for r in qs)
        print(f"\n[{kind}] questions/run={len(qs)} (n, k, |truth|) counts: {dict(shape)}")
        print(f"   k == |truth| in {sum(1 for r in qs if qinfo[r]['k'] == len(qinfo[r]['tslots']))}/{len(qs)}")
        exp_exact = sum(Fraction(1, math.comb(qinfo[r]["n"], qinfo[r]["k"])) for r in qs) / len(qs)
        # expected per-bit accuracy of a random exactly-k chooser: 1 - 2k(n-k)/n^2 per slot pooled
        num = sum(Fraction(qinfo[r]["n"]) - Fraction(2 * qinfo[r]["k"] * (qinfo[r]["n"] - qinfo[r]["k"]), qinfo[r]["n"]) for r in qs)
        den = sum(qinfo[r]["n"] for r in qs)
        npos = sum(len(qinfo[r]["tslots"]) for r in qs)
        p = Fraction(npos, den)
        print(f"   random-with-k expected exact = {float(exp_exact) * 100:.4f}%")
        print(f"   random-with-k expected per-bit = {float(num / den) * 100:.4f}%")
        print(f"   truth PRESENT rate = {P(npos, den)}; chance p^2+(1-p)^2 = {float(p*p + (1-p)*(1-p)) * 100:.4f}%;"
              f" always-ABSENT = {P(den - npos, den)}")

    rng = random.Random(918)
    pooled_rows = {}
    for rc in receipts:
        a = rc / "collected/results/artifacts"
        preds = json.loads((a / "final_predictions.json").read_text(encoding="utf-8"))["predictions"]
        for kind in ("edge_account", "parts"):
            sel_hit = arg_hit = bits = 0
            topk_hit = topk_exact = tp_topk = 0
            pooled = []
            per_q = []
            within = []
            nq = 0
            indep_exact = 0
            for pred in preds:
                rid = pred["record_id"]
                if rid not in qinfo or qinfo[rid]["kind"] != kind:
                    continue
                qi = qinfo[rid]
                sc = pred["scores"]
                nq += 1
                marg = {sid: sc[sid]["PRESENT"] - sc[sid]["ABSENT"] for sid in qi["cands"]}
                chosen_sel = {sid for sid in qi["cands"] if pred["decisions"]["selected"][sid] == "PRESENT"}
                chosen_arg = {sid for sid in qi["cands"] if sc[sid]["PRESENT"] > sc[sid]["ABSENT"]}
                indep_exact += 1 if chosen_sel == qi["tslots"] else 0
                for sid in qi["cands"]:
                    y = sid in qi["tslots"]
                    bits += 1
                    sel_hit += 1 if (sid in chosen_sel) == y else 0
                    arg_hit += 1 if (sid in chosen_arg) == y else 0
                    pooled.append((marg[sid], y))
                ranked = sorted(qi["cands"], key=lambda s: marg[s], reverse=True)
                top = set(ranked[:qi["k"]])
                # tie check at the k boundary
                if 0 < qi["k"] < qi["n"] and marg[ranked[qi["k"] - 1]] == marg[ranked[qi["k"]]]:
                    print("   TIE at k boundary", rc.name, rid)
                topk_exact += 1 if top == qi["tslots"] else 0
                tp_topk += len(top & qi["tslots"])
                topk_hit += sum(1 for s in qi["cands"] if (s in top) == (s in qi["tslots"]))
                qpairs = [(marg[s], s in qi["tslots"]) for s in qi["cands"]]
                per_q.append(qpairs)
                w = mw_auc(qpairs)
                if w is not None:
                    within.append(w)
            auc = mw_auc(pooled)
            mwithin = sum(within) / len(within)
            # permutation null: shuffle truth labels among slots WITHIN each question (keeps k per question)
            ge_pool = ge_within = 0
            for _ in range(NPERM):
                allp = []
                ws = []
                for qp in per_q:
                    labs = [y for _, y in qp]
                    rng.shuffle(labs)
                    z = [(m, y) for (m, _), y in zip(qp, labs)]
                    allp.extend(z)
                    ws.append(mw_auc(z))
                if mw_auc(allp) >= auc:
                    ge_pool += 1
                if sum(ws) / len(ws) >= mwithin:
                    ge_within += 1
            npos = sum(len(qinfo[r]["tslots"]) for r in qinfo if qinfo[r]["kind"] == kind)
            print(f"{rc.name:>20} {kind:>12} q={nq} selected_per_bit={P(sel_hit, bits)} argmax_per_bit={P(arg_hit, bits)}"
                  f" indep_exact={P(indep_exact, nq)}")
            print(f"{'':>20} {'':>12} pooled_AUC={auc:.4f} (perm p={(ge_pool + 1) / (NPERM + 1):.4f})"
                  f" mean_within_AUC={mwithin:.4f} (perm p={(ge_within + 1) / (NPERM + 1):.4f}, n_q={len(within)})")
            print(f"{'':>20} {'':>12} topk_exact={P(topk_exact, nq)} topk_per_bit={P(topk_hit, bits)}"
                  f" topk_true_found={P(tp_topk, npos)}", flush=True)
            agg = pooled_rows.setdefault(kind, Counter())
            agg["topk_hit"] += topk_hit
            agg["bits"] += bits
            agg["tp"] += tp_topk
            agg["pos"] += npos
            agg["sel_hit"] += sel_hit
    for kind, agg in pooled_rows.items():
        print(f"\nPOOLED six runs {kind}: topk_per_bit={P(agg['topk_hit'], agg['bits'])}"
              f" selected_per_bit={P(agg['sel_hit'], agg['bits'])} topk_true_found={P(agg['tp'], agg['pos'])}")


if __name__ == "__main__":
    main()
