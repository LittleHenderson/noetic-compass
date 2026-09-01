"""run_pathb_pilot.py -- PATH B (CJT-T2) P0 smoke on the frozen P1.3 machinery.
DEVELOPMENT-ONLY, NON-CLAIM-BEARING. Train/validation only; the v1 protected
split AND the PATH B protected split are untouched.

Arms (owner D1 dose-response): S0 none | S3 exact operation one-hot |
S-ALT50 frozen 50% corruption map (pathb_core.alt50_class) | S6 uniform.
S-PERM is an implementation-conformance test (test_sperm_equivariance.py),
not a trained arm. Machinery: the FROZEN MixtureHead (router + clause-local
answer experts) from run_pilot_v3 -- no model change, no third binder.

P0 gates: losses finite; profile-arm params identical + S0 capacity within
1%; profile-branch gradients real (S3/S-ALT50; S6 exempt by the invariance
theorem); S3 profile-swap moves logits; S6 exactly invariant; smoke gates
(128-memorization >=95%, gold-vs-shuffled routing >=10pp, binding-shuffle
damage >=5pp); PRB-POS position probe (QB_ORD keep/drop rule); transfer
floor-guard measurement. Return contract (owner v0.3 ruling): the exact
failed gate, or these P0 numbers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "cjt_gate1a_static_neural_v1"
PILOT = HERE.parent / "cjt_dev_gpu_pilot_v1"
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(PKG / "tools"))
sys.path.insert(0, str(PILOT))
sys.path.insert(0, str(HERE))

from exec.activation_extraction import MODEL_ID, extract_split  # noqa: E402
from exec.arms import MAX_IDEAS  # noqa: E402
from exec.spans import build_input_text, clause_char_spans  # noqa: E402
from run_pilot import lr_lambda, seeded_order  # noqa: E402
from run_pilot_v3 import (build_mixture_head, pack_batches_v3,  # noqa: E402
                          train_arm)
from pathb_core import CLASSES, alt50_class  # noqa: E402

CANDIDATE_LAYERS = (6, 12, 18, 24)
ARMS = ["S0", "S3", "SALT50", "S6"]
ARM_TAGS = {
    "S0": {"profile_semantics": "NONE", "authority": "PLAIN_BASELINE"},
    "S3": {"profile_semantics": "EXACT_OPERATION_IDENTITY",
           "authority": "CONSTRUCTION_GOLD"},
    "SALT50": {"profile_semantics": "HALF_CORRUPTED_OPERATION_IDENTITY",
               "authority": "EXPERIMENTAL_CONTROL"},
    "S6": {"profile_semantics": "UNIFORM_CONTROL",
           "authority": "EXPERIMENTAL_CONTROL"},
}


def load_records(split):
    p = HERE / "data" / f"{split}.jsonl"
    return [json.loads(l) for l in p.read_text("utf-8").splitlines() if l]


def profiles_for(rec, arm):
    if arm == "S0":
        return None
    if arm == "S6":
        return [[0.25] * 4 for _ in rec["idea_labels"]]
    out = []
    for k, c in enumerate(rec["idea_labels"]):
        cls = c if arm == "S3" else alt50_class(rec["passage_id"], k, c)
        v = [0.0] * 4
        v[CLASSES.index(cls)] = 1.0
        out.append(v)
    return out


def assemble(records, arm):
    exs = []
    for r in records:
        exs.append({"passage_id": r["passage_id"],
                    "question_type": r["question_type"],
                    "clauses": [c["text"] for c in r["clauses"]],
                    "candidates": list(r["candidates"]),
                    "answer_index": r["candidates"].index(r["answer"]),
                    "profiles": profiles_for(r, arm)})
    return exs


def extract_clause_local_ml(records, tok, model, device, layers):
    """Clause-local candidate occurrence vectors for EVERY candidate layer in
    one forward pass per passage: {pid: {L: {"mask","vecs"}}}."""
    import torch
    out = {}
    with torch.no_grad():
        for rec in records:
            text = build_input_text(rec)
            enc = tok(text, return_offsets_mapping=True, return_tensors="pt")
            offs = enc["offset_mapping"][0].tolist()
            hs = model(input_ids=enc["input_ids"].to(device),
                       attention_mask=enc["attention_mask"].to(device),
                       output_hidden_states=True).hidden_states
            spans, _ = clause_char_spans(rec)
            low = text.lower()
            occ_tok = {}
            for j, cand in enumerate(rec["candidates"]):
                occ = [(m.start(), m.end()) for m in re.finditer(
                    rf"\b{re.escape(cand.lower())}\b", low)]
                for i, (cs, ce) in enumerate(spans):
                    inside = [(s, e) for s, e in occ if s >= cs and e <= ce]
                    if not inside:
                        continue
                    tix = [ti for ti, (a, b) in enumerate(offs)
                           if b > a and any(a < e and b > s
                                            for s, e in inside)]
                    if tix:
                        occ_tok[(i, j)] = torch.tensor(tix)
            per = {}
            for L in layers:
                h_all = hs[L][0].float()
                vecs = {k: h_all[t.to(h_all.device)].mean(0).half().cpu()
                        for k, t in occ_tok.items()}
                mask = [[False] * len(rec["candidates"])
                        for _ in range(len(rec["clauses"]))]
                for (i, j) in vecs:
                    mask[i][j] = True
                per[L] = {"mask": mask, "vecs": vecs}
            out[rec["passage_id"]] = per
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out-dir", default=str(HERE / "results_pathb_p0"))
    ap.add_argument("--updates", type=int, default=100)
    ap.add_argument("--device-note", default="cloud GPU")
    ap.add_argument("--cost-per-hour", type=float, default=0.0)
    args = ap.parse_args()
    import torch
    if args.device.startswith("cuda") and not torch.cuda.is_available():
        raise SystemExit("GPU_REQUIRED: no CPU neural fallback")
    device = args.device
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    train_recs = load_records("train")
    val_recs = load_records("val")
    qfams = sorted({r["question_type"] for r in val_recs})

    from transformers import AutoTokenizer, AutoModel
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModel.from_pretrained(MODEL_ID, torch_dtype=torch.float16) \
        .to(device).eval()
    is_real = device.startswith("cuda") and next(model.parameters()).is_cuda
    cache = out / "cache"; cache.mkdir(exist_ok=True)
    acts, loc = {}, {}
    for split, recs in (("train", train_recs), ("val", val_recs)):
        f1, f2 = cache / f"{split}_acts.pt", cache / f"{split}_loc.pt"
        if f1.is_file():
            acts[split] = torch.load(f1, map_location="cpu",
                                     weights_only=False)
        else:
            te = time.time()
            acts[split] = extract_split(recs, tok, model,
                                        list(CANDIDATE_LAYERS), device)
            torch.save(acts[split], f1)
            print(f"[extract] {split} {time.time()-te:.0f}s")
        if f2.is_file():
            loc[split] = torch.load(f2, map_location="cpu",
                                    weights_only=False)
        else:
            te = time.time()
            loc[split] = extract_clause_local_ml(recs, tok, model, device,
                                                 list(CANDIDATE_LAYERS))
            torch.save(loc[split], f2)
            print(f"[loc-extract] {split} {time.time()-te:.0f}s")

    # ---- PRB-POS: can a linear probe decode clause discourse index? ---------
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    def pos_xy(split, L, n):
        X, y = [], []
        for r in (train_recs if split == "train" else val_recs)[:n]:
            h = acts[split][r["passage_id"]]["layers"][L][0].float().numpy()
            for i in range(h.shape[0]):
                X.append(h[i]); y.append(i)
        return np.array(X), np.array(y)
    Xtr, ytr = pos_xy("train", 18, 400)
    Xva, yva = pos_xy("val", 18, 200)
    probe = LogisticRegression(max_iter=1000).fit(Xtr, ytr)
    prb_pos = float(probe.score(Xva, yva))
    print(f"[PRB-POS] clause-position probe val acc = {prb_pos:.4f}")
    del model
    torch.cuda.empty_cache()

    def feats(split, L):
        return {pid: {"h": v["layers"][L][0], "g": v["layers"][L][1]}
                for pid, v in acts[split].items()}

    def locL(split, L):
        return {pid: per[L] for pid, per in loc[split].items()}

    gold_va = [r["edge_trace"][-1] for r in val_recs]

    ref = sum(p.numel() for p in build_mixture_head(True, 0).parameters())
    counts = {a: sum(p.numel() for p in
                     build_mixture_head(a != "S0", 0).parameters())
              for a in ARMS}

    # ---- layer selection: S0 only, val accuracy, lowest-index tie-break -----
    layer_val = {}
    for L in CANDIDATE_LAYERS:
        ex_tr = assemble(train_recs, "S0")
        ex_va = assemble(val_recs, "S0")
        tb = pack_batches_v3(ex_tr, feats("train", L), locL("train", L),
                             seeded_order(len(ex_tr), 11))
        vb = pack_batches_v3(ex_va, feats("val", L), locL("val", L),
                             list(range(len(ex_va))))
        r, _ = train_arm("S0", 11, 0, tb, vb, args.updates, device)
        layer_val[L] = r["final"]["val_accuracy"]
        print(f"[layer-select] L={L} S0 val_acc={layer_val[L]:.4f}")
    Lstar = max(sorted(layer_val), key=lambda k: (layer_val[k], -k))
    Lstar = sorted(CANDIDATE_LAYERS,
                   key=lambda k: (-layer_val[k], k))[0]
    print(f"[layer-select] L*={Lstar}")

    ftr, fva = feats("train", Lstar), feats("val", Lstar)
    ltr, lva = locL("train", Lstar), locL("val", Lstar)

    # ---- binding smoke gates (memorization + gold-vs-shuffled) --------------
    sub = train_recs[:128]
    ex_sub = assemble(sub, "S3")
    tb_sub = pack_batches_v3(ex_sub, ftr, ltr, seeded_order(128, 11))
    r_mem, head_mem = train_arm("S3", 11, 0, tb_sub, tb_sub, 600, device)
    mem_acc = r_mem["train_subset_accuracy"]
    order = seeded_order(128, 11)
    gold = [sub[i]["edge_trace"][-1] for i in order]
    gen = torch.Generator().manual_seed(47)
    shuf = [gold[i] for i in torch.randperm(128, generator=gen).tolist()]

    def routed(idxs):
        k = cor = tot = 0
        head_mem.eval()
        with torch.no_grad():
            for bt in tb_sub:
                b = bt["h"].shape[0]
                a = torch.zeros(b, MAX_IDEAS)
                for j in range(b):
                    a[j, min(idxs[k + j], MAX_IDEAS - 1)] = 1.0
                logp = head_mem(bt["h"].to(device), bt["g"].to(device),
                                bt["p"].to(device),
                                bt["idea_mask"].to(device),
                                bt["e_loc"].to(device),
                                bt["m_loc"].to(device),
                                bt["cand_mask"].to(device),
                                alpha_override=a.to(device))
                tgt = bt["answer_index"].to(device)
                cor += int((logp.argmax(1) == tgt).sum()); tot += b; k += b
        return cor / tot
    acc_gold, acc_shuf = routed(gold), routed(shuf)
    smoke = {"memorization_128": round(mem_acc, 4),
             "gold_routed": round(acc_gold, 4),
             "shuffled_routed": round(acc_shuf, 4),
             "binding_shuffle_drop": round(
                 mem_acc - r_mem["binding_shuffle"]["accuracy"], 4),
             "gate1_memorize_ge_95": mem_acc >= 0.95,
             "gate2_gold_beats_shuffled_by_10": (acc_gold - acc_shuf) >= 0.10,
             "gate3_binding_shuffle_damages_5":
                 (mem_acc - r_mem["binding_shuffle"]["accuracy"]) >= 0.05}
    print(f"[smoke] {json.dumps(smoke)}")

    # ---- the four P0 arms ---------------------------------------------------
    runs = []
    for arm in ARMS:
        ex_tr = assemble(train_recs, arm)
        ex_va = assemble(val_recs, arm)
        vb = pack_batches_v3(ex_va, fva, lva, list(range(len(ex_va))))
        tb = pack_batches_v3(ex_tr, ftr, ltr,
                             seeded_order(len(ex_tr), 11))
        r, _ = train_arm(arm if arm != "SALT50" else "S3", 11, 0, tb, vb,
                         args.updates, device, gold_va=gold_va)
        r["arm"] = arm
        r["layer"] = Lstar
        runs.append(r)
        sens = r["profile_sensitivity"]
        print(f"[P0] {arm:7} acc={r['final']['val_accuracy']:.4f} "
              f"loss={r['final']['val_loss']:.4f} lam={r['learned_lambda']} "
              f"goldhit={r['attention']['gold_top1_rate']:.3f} "
              f"swapDlogit="
              f"{sens['permuted']['mean_abs_logit_delta_vs_true'] if sens else None}")

    # ---- per-family transfer floor-guard measurement ------------------------
    unif = {q: float(np.mean([1.0 / len(r["candidates"])
                              for r in val_recs if r["question_type"] == q]))
            for q in qfams}
    s0 = next(r for r in runs if r["arm"] == "S0")
    per_qt = s0["final"]["per_question_type"]
    floor = {q: {"s0_acc": round(per_qt[q]["accuracy"], 4),
                 "uniform": round(unif[q], 4),
                 "above": per_qt[q]["accuracy"] >= unif[q] + 0.05}
             for q in qfams}
    floor_pass = sum(1 for q in qfams if floor[q]["above"]) >= 2

    # ---- P0 gate evaluation -------------------------------------------------
    g = {"losses_finite": all(math.isfinite(r["final"]["val_loss"])
                              for r in runs),
         "profile_arm_params_identical":
             len({counts[a] for a in ARMS if a != "S0"}) == 1,
         "s0_capacity_within_1pct":
             abs(counts["S0"] - ref) <= 0.01 * ref}
    grad_ok = True
    for r in runs:
        if r["arm"] in ("S0", "S6"):
            continue
        log = r["profile_grad_log"]
        if not log or not all(e["w_r_grad_norm"] > 1e-9 for e in log):
            grad_ok = False
    g["profile_branch_receives_gradients"] = grad_ok
    s3 = next(r for r in runs if r["arm"] == "S3")
    g["s3_profile_swap_changes_logits"] = bool(
        s3["profile_sensitivity"]["permuted"]
        ["mean_abs_logit_delta_vs_true"] > 1e-4)
    s6 = next(r for r in runs if r["arm"] == "S6")
    g["s6_exactly_invariant"] = bool(
        s6["profile_sensitivity"]["permuted"]
        ["mean_abs_logit_delta_vs_true"] < 1e-6)
    g.update({k: v for k, v in smoke.items() if k.startswith("gate")})
    g["prb_pos_ge_90"] = prb_pos >= 0.90
    g["transfer_floor_2_of_4_families"] = floor_pass
    failed = [k for k, v in g.items() if v is False]
    status = "P0_SMOKE_OK" if not failed else \
        ("BINDING_REPAIR_FAILED" if ("gate1_memorize_ge_95" in failed or
                                     "gate2_gold_beats_shuffled_by_10"
                                     in failed)
         else f"P0_GATES_FAILED({failed})")
    qb_ord_rule = "KEEP" if prb_pos >= 0.90 else \
        "DROP_QB_ORD (PRB-POS below 0.90; owner D3 auto-drop rule)"

    raw = {"pilot": "CJT-T2 PATH B P0", "non_claim_bearing": True,
           "is_real_model": is_real, "device": device, "model_id": MODEL_ID,
           "updates": args.updates, "selected_layer": Lstar,
           "layer_selection_val_accuracy": {str(k): round(v, 6)
                                            for k, v in layer_val.items()},
           "arms": {r["arm"]: {
               "final_val_accuracy": round(r["final"]["val_accuracy"], 6),
               "final_val_loss": round(r["final"]["val_loss"], 6),
               "learned_lambda": r["learned_lambda"],
               "train_subset_accuracy": r["train_subset_accuracy"],
               "gold_top1_rate": r["attention"]["gold_top1_rate"],
               "per_question_type": r["final"]["per_question_type"],
               "profile_sensitivity": r["profile_sensitivity"],
               "trainable_params": counts[r["arm"]], **ARM_TAGS[r["arm"]]}
               for r in runs},
           "smoke_gates": smoke, "prb_pos": round(prb_pos, 4),
           "qb_ord_rule": qb_ord_rule,
           "transfer_floor_guard": floor,
           "p0_gates": g, "failed_gates": failed,
           "development_status": status,
           "total_wall_clock_seconds": round(time.time() - t0, 1),
           "total_cost_usd": round((time.time() - t0) / 3600
                                   * args.cost_per_hour, 4)}
    (out / "PATHB_P0_RAW_RESULTS.json").write_text(
        json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    print(f"\nP0 STATUS: {status}\n  failed={failed}\n  qb_ord={qb_ord_rule}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
