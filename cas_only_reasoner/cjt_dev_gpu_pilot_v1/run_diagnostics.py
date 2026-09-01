"""run_diagnostics.py -- CJT-DEV-P1.1: Readout Competence and Profile
Sensitivity (owner ruling CJT-DEV-P1.2). DEVELOPMENT-ONLY, NON-CLAIM-BEARING.
Train/validation only; no protected split; no claim promotion.

Diagnoses WHY the ran pilot (9229d8b4) plateaued at ~0.21 val accuracy before
any five-arm relaunch. One cloud GPU session, frozen Qwen2.5-0.5B, layer 24
(the pilot's frozen L*):

  A  correct candidate-uniform baselines (recomputed on-instance)
  B  tiny-set memorization: can the S3 head memorize 128 passages?
  C  same-distribution holdout: train 5400/hold 600 (families A,B) vs the
     cross-family val (family C) -- separates "cannot learn" from
     "cannot transfer across template families"
  D  gold-clause attention oracle: replace learned alpha with the known
     target clause -- is Idea attention the bottleneck?
  E  contextual-candidate oracle: candidates represented by their contextual
     occurrences at L=24 instead of context-free input embeddings -- is
     candidate grounding the bottleneck? (+ D and E combined)
  F  profile sensitivity on the trained S3 head: true vs uniform vs permuted
     vs zeroed-W_p profiles; W_p gradient norms; profile-contribution norms
  G  attention inspection: entropy, gold-clause top-1 rate, gold mass

Writes DIAGNOSTIC_RESULTS.json (+ prints a full log).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "cjt_gate1a_static_neural_v1"
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(PKG / "tools"))
sys.path.insert(0, str(HERE))

from exec.activation_extraction import MODEL_ID, extract_split  # noqa: E402
from exec.arms import (D_ATT, D_HID, D_MODEL, D_PROF, MAX_IDEAS,  # noqa: E402
                       N_CLASSES, build_arm_head, trainable_param_count)
from exec.dataset_assembly import assemble_examples  # noqa: E402
from exec.spans import build_input_text, clause_char_spans  # noqa: E402
from run_pilot import (BATCH_SIZE, LR, BETAS, WD, CLIP, lr_lambda,  # noqa: E402
                       load_records, pack_batches, seeded_order)

L_STAR = 24
QT_OP = {"Q_ATTRACT": "^2", "Q_AVERT": "^3", "Q_PART": "^6", "Q_TRIGGER": "^8"}


# ---- DiagHead: the exact ArmHead forward + oracle/instrumentation hooks ----
def make_diag_head(widen_w: int):
    import torch
    import torch.nn as nn

    class DiagHead(nn.Module):
        """State-dict-compatible with ArmHead(attention=True, profiles=True).
        Adds: alpha_override (gold-clause oracle), zero_wp (profile kill),
        and returns (logits, alpha, profile_contribution_norm)."""

        def __init__(self, w):
            super().__init__()
            self.w_q = nn.Linear(D_MODEL, D_ATT)
            self.w_k = nn.Linear(D_MODEL, D_ATT)
            self.w_p = nn.Linear(N_CLASSES, D_PROF)
            in_dim = D_MODEL + D_PROF + D_MODEL
            self.mlp = nn.Sequential(nn.Linear(in_dim, D_HID), nn.GELU(),
                                     nn.Linear(D_HID, D_HID))
            self.widen = (nn.Sequential(nn.Linear(D_HID, w), nn.GELU(),
                                        nn.Linear(w, D_HID)) if w > 0 else None)
            self.w_o = nn.Linear(D_HID, D_HID)
            self.w_c = nn.Linear(D_MODEL, D_HID)

        def forward(self, h, g, p, idea_mask, cand_enc, cand_mask,
                    alpha_override=None, zero_wp=False):
            neg = torch.finfo(h.dtype).min
            if alpha_override is None:
                scores = (self.w_q(g).unsqueeze(1) * self.w_k(h)).sum(-1) \
                    / (D_ATT ** 0.5)
                scores = scores.masked_fill(~idea_mask, neg)
                alpha = torch.softmax(scores, dim=1)
            else:
                alpha = alpha_override
            c = (alpha.unsqueeze(-1) * h).sum(dim=1)
            q = (alpha.unsqueeze(-1) * p).sum(dim=1)
            prof = self.w_p(q)
            if zero_wp:
                prof = prof * 0.0
            z = self.mlp(torch.cat([c, prof, g], dim=-1))
            if self.widen is not None:
                z = self.widen(z)
            u = self.w_o(z)
            logits = (self.w_c(cand_enc) * u.unsqueeze(1)).sum(-1)
            return logits.masked_fill(~cand_mask, neg), alpha, \
                prof.norm(dim=-1).mean()

    return DiagHead(widen_w)


def gold_clause_index(rec):
    """Deterministic target-clause resolution: the clause whose operator label
    matches the question type AND whose text contains the answer word;
    tie-break by containing a question entity. Returns (idx or None, how)."""
    op = QT_OP[rec["question_type"]]
    ans = rec["answer"].lower()
    q = rec["question"].lower()
    cands = [i for i, (cl, lab) in enumerate(zip(rec["clauses"],
                                                 rec["idea_labels"]))
             if lab == op and re.search(rf"\b{re.escape(ans)}\b",
                                        cl["text"].lower())]
    if len(cands) == 1:
        return cands[0], "unique"
    if len(cands) > 1:
        q_words = set(re.findall(r"[a-z]+", q))
        scored = [(len(set(re.findall(r"[a-z]+",
                                      rec["clauses"][i]["text"].lower()))
                       & q_words), i) for i in cands]
        scored.sort(reverse=True)
        if scored[0][0] > scored[1][0]:
            return scored[0][1], "tiebreak"
        return scored[0][1], "ambiguous_first"
    return None, "unresolved"


def gold_alpha(recs, order, device):
    import torch
    out, stats = [], {"unique": 0, "tiebreak": 0, "ambiguous_first": 0,
                      "unresolved": 0}
    for i in order:
        idx, how = gold_clause_index(recs[i])
        stats[how] += 1
        out.append(idx if idx is not None else 0)
    return out, stats


def batched_gold_alpha(gold_list, batches, device):
    import torch
    per_batch, k = [], 0
    for bt in batches:
        b = bt["h"].shape[0]
        a = torch.zeros(b, MAX_IDEAS)
        for j in range(b):
            a[j, min(gold_list[k + j], MAX_IDEAS - 1)] = 1.0
        per_batch.append(a.to(device))
        k += b
    return per_batch


def train_head(head, train_batches, val_batches, updates, device, seed,
               alpha_tr=None, alpha_va=None, zero_wp=False, log_grad=False):
    import torch
    torch.manual_seed(seed)
    head = head.float().to(device).train()
    opt = torch.optim.AdamW(head.parameters(), lr=LR, betas=BETAS,
                            weight_decay=WD)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lr_lambda(updates))
    loss_fn = torch.nn.CrossEntropyLoss()
    grad_log = []
    idx_cycle = list(range(len(train_batches)))
    pos = 0
    for step in range(updates):
        bi = idx_cycle[pos]; pos = (pos + 1) % len(idx_cycle)
        bt = train_batches[bi]
        ao = alpha_tr[bi] if alpha_tr is not None else None
        logits, _, _ = head(bt["h"].to(device), bt["g"].to(device),
                            bt["p"].to(device), bt["idea_mask"].to(device),
                            bt["cand_enc"].to(device),
                            bt["cand_mask"].to(device),
                            alpha_override=ao, zero_wp=zero_wp)
        loss = loss_fn(logits, bt["answer_index"].to(device))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        if log_grad and (step + 1) in (50, 250, 500, 1000):
            wp = head.w_p.weight.grad
            wq = head.w_q.weight.grad
            grad_log.append({"step": step + 1,
                             "w_p_grad_norm": float(wp.norm()) if wp is not None else 0.0,
                             "w_q_grad_norm": float(wq.norm()) if wq is not None else 0.0,
                             "train_loss": float(loss.item())})
        torch.nn.utils.clip_grad_norm_(head.parameters(), CLIP)
        opt.step(); sched.step()
    return head, grad_log


def eval_head(head, batches, device, alpha_ov=None, zero_wp=False,
              profiles_override=None, want_attention=False, gold_list=None):
    import torch
    head.eval()
    tot = correct = 0
    loss_sum = 0.0
    ce = torch.nn.CrossEntropyLoss(reduction="sum")
    ent_all, gold_top1, gold_mass, prof_norms = [], [], [], []
    k = 0
    with torch.no_grad():
        for bi, bt in enumerate(batches):
            p = bt["p"] if profiles_override is None else profiles_override[bi]
            ao = alpha_ov[bi] if alpha_ov is not None else None
            logits, alpha, pn = head(
                bt["h"].to(device), bt["g"].to(device), p.to(device),
                bt["idea_mask"].to(device), bt["cand_enc"].to(device),
                bt["cand_mask"].to(device), alpha_override=ao,
                zero_wp=zero_wp)
            tgt = bt["answer_index"].to(device)
            loss_sum += float(ce(logits, tgt).item())
            ok = logits.argmax(dim=1) == tgt
            correct += int(ok.sum()); tot += len(tgt)
            prof_norms.append(float(pn))
            if want_attention:
                m = bt["idea_mask"].to(device)
                a = alpha.clamp_min(1e-12)
                ent = -(a * a.log()).masked_fill(~m, 0.0).sum(dim=1)
                n_ideas = m.sum(dim=1).float()
                ent_all += (ent / n_ideas.clamp(min=2).log()).tolist()
                top1 = alpha.argmax(dim=1)
                for j in range(len(tgt)):
                    gi = gold_list[k + j] if gold_list else None
                    if gi is not None:
                        gold_top1.append(int(top1[j].item()) == gi)
                        gold_mass.append(float(alpha[j, min(gi, MAX_IDEAS - 1)]
                                               .item()))
            k += bt["h"].shape[0]
    head.train()
    out = {"accuracy": round(correct / tot, 6),
           "loss": round(loss_sum / tot, 6),
           "mean_profile_contribution_norm": round(
               sum(prof_norms) / len(prof_norms), 6)}
    if want_attention:
        out["attention"] = {
            "mean_normalized_entropy": round(sum(ent_all) / len(ent_all), 6),
            "gold_top1_rate": round(sum(gold_top1) / max(1, len(gold_top1)), 6),
            "mean_gold_mass": round(sum(gold_mass) / max(1, len(gold_mass)), 6),
            "n_gold_resolved": len(gold_top1)}
    return out


def contextual_candidates(records, tok, model, device):
    """Diagnostic E extraction: per candidate, mean of layer-24 hidden states
    over ALL its token occurrences in the passage text."""
    import torch
    out = {}
    with torch.no_grad():
        for rec in records:
            text = build_input_text(rec)
            enc = tok(text, return_offsets_mapping=True, return_tensors="pt")
            offs = enc["offset_mapping"][0].tolist()
            hs = model(input_ids=enc["input_ids"].to(device),
                       attention_mask=enc["attention_mask"].to(device),
                       output_hidden_states=True).hidden_states[L_STAR][0] \
                .float()
            low = text.lower()
            vecs = []
            for cand in rec["candidates"]:
                spans = [(m.start(), m.end()) for m in
                         re.finditer(rf"\b{re.escape(cand.lower())}\b", low)]
                tok_idx = [ti for ti, (a, b) in enumerate(offs)
                           if b > a and any(a < e and b > s for s, e in spans)]
                if tok_idx:
                    vecs.append(hs[torch.tensor(tok_idx,
                                                device=hs.device)].mean(0))
                else:
                    vecs.append(torch.zeros(D_MODEL, device=hs.device))
            out[rec["passage_id"]] = torch.stack(vecs).half().cpu()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out-dir", default=str(HERE / "results_diag"))
    args = ap.parse_args()
    import torch
    if args.device.startswith("cuda") and not torch.cuda.is_available():
        raise SystemExit("GPU_REQUIRED: no CUDA device (no CPU neural fallback)")
    device = args.device
    out_dir = Path(args.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    R = {"diagnostic": "CJT-DEV-P1.1", "non_claim_bearing": True,
         "layer": L_STAR, "model_id": MODEL_ID, "device": device}

    train_recs = load_records("train")
    val_recs = load_records("val")

    # ---- A: candidate-uniform baselines (on-instance) ----
    def unif(recs):
        Cs = [len(r["candidates"]) for r in recs]
        return {"n": len(recs), "mean_candidates": round(sum(Cs) / len(Cs), 3),
                "uniform_accuracy": round(sum(1 / c for c in Cs) / len(Cs), 5),
                "uniform_CE": round(sum(math.log(c) for c in Cs) / len(Cs), 5)}
    R["A_baselines"] = {"train": unif(train_recs), "val": unif(val_recs)}

    # ---- frozen extraction (cache once; L* only for heads) ----
    from transformers import AutoTokenizer, AutoModel
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModel.from_pretrained(MODEL_ID, torch_dtype=torch.float16) \
        .to(device).eval()
    caches = {}
    for split, recs in (("train", train_recs), ("val", val_recs)):
        cf = out_dir / f"{split}_acts.pt"
        if cf.is_file():
            caches[split] = torch.load(cf, map_location="cpu",
                                       weights_only=False)
        else:
            te = time.time()
            caches[split] = extract_split(recs, tok, model, [L_STAR], device)
            torch.save(caches[split], cf)
            print(f"[extract] {split} {time.time()-te:.0f}s")
    # Diagnostic E extraction (contextual candidates)
    ctx = {}
    for split, recs in (("train", train_recs), ("val", val_recs)):
        cf = out_dir / f"{split}_ctx.pt"
        if cf.is_file():
            ctx[split] = torch.load(cf, map_location="cpu", weights_only=False)
        else:
            te = time.time()
            ctx[split] = contextual_candidates(recs, tok, model, device)
            torch.save(ctx[split], cf)
            print(f"[ctx-extract] {split} {time.time()-te:.0f}s")
    del model
    torch.cuda.empty_cache()

    def feats(split, contextual=False):
        src = caches[split]
        return {pid: {"h": v["layers"][L_STAR][0], "g": v["layers"][L_STAR][1],
                      "cand": (ctx[split][pid] if contextual else v["cand"])}
                for pid, v in src.items()}

    widen_s3 = 0
    ref = trainable_param_count(build_arm_head("S3", 0))

    def fresh_head():
        return make_diag_head(widen_s3)

    def prep(recs, arm, split, order=None, contextual=False):
        exs = assemble_examples(recs, arm)
        f = feats(split, contextual)
        o = order if order is not None else list(range(len(exs)))
        return pack_batches(exs, f, o), o

    # ---- B: 128-example memorization ----
    sub = train_recs[:128]
    tb, _ = prep(sub, "S3", "train", seeded_order(128, 11))
    head, _ = train_head(fresh_head(), tb, tb, 600, device, 11)
    evb, _ = prep(sub, "S3", "train")
    R["B_memorization_128"] = eval_head(head, evb, device)
    print(f"[B] memorize-128 train acc = {R['B_memorization_128']['accuracy']}")

    # ---- C: in-distribution holdout vs cross-family val ----
    # NOTE the no-profile comparator here is S1-SHAPED (DiagHead always has
    # learned attention; the profile branch is killed via zero_wp), labeled
    # honestly as such -- the transfer question does not need exact S0.
    idx = seeded_order(len(train_recs), 20260831)
    hold_i, tr_i = idx[:600], idx[600:]
    tr_sub = [train_recs[i] for i in tr_i]
    hold_sub = [train_recs[i] for i in hold_i]
    C_res = {}
    for label, arm, kill in (("S1_style_no_profile", "S0", True),
                             ("S3_cas_profile", "S3", False)):
        tb, _ = prep(tr_sub, arm, "train", seeded_order(len(tr_sub), 11))
        hb, _ = prep(hold_sub, arm, "train")
        vb, _ = prep(val_recs, arm, "val")
        for b in (tb + hb + vb):
            if b["p"] is None:
                b["p"] = torch.full((b["h"].shape[0], MAX_IDEAS, 4), 0.25)
        head, _ = train_head(fresh_head(), tb, tb, 1000, device, 11,
                             zero_wp=kill)
        C_res[label] = {
            "holdout_indistribution": eval_head(head, hb, device,
                                                zero_wp=kill),
            "val_crossfamily": eval_head(head, vb, device, zero_wp=kill)}
        print(f"[C] {label}: "
              f"holdout={C_res[label]['holdout_indistribution']['accuracy']} "
              f"val={C_res[label]['val_crossfamily']['accuracy']}")
    R["C_holdout_vs_crossfamily"] = C_res

    # keep the trained S3 full-config head for F/G (retrain on FULL train,
    # matching the pilot configuration)
    tb_full, o_tr = prep(train_recs, "S3", "train",
                         seeded_order(len(train_recs), 11))
    vb_full, o_va = prep(val_recs, "S3", "val")
    s3_head, grad_log = train_head(fresh_head(), tb_full, vb_full, 1000,
                                   device, 11, log_grad=True)

    # ---- D: gold-clause oracle ----
    gold_tr, st_tr = gold_alpha(train_recs, o_tr, device)
    gold_va, st_va = gold_alpha(val_recs, o_va, device)
    R["D_gold_resolution"] = {"train": st_tr, "val": st_va}
    a_tr = batched_gold_alpha(gold_tr, tb_full, device)
    a_va = batched_gold_alpha(gold_va, vb_full, device)
    d_head, _ = train_head(fresh_head(), tb_full, vb_full, 1000, device, 11,
                           alpha_tr=a_tr)
    R["D_gold_alpha_oracle"] = {
        "val_with_oracle": eval_head(d_head, vb_full, device, alpha_ov=a_va),
        "learned_alpha_reference": eval_head(s3_head, vb_full, device)}
    print(f"[D] oracle-alpha val acc = "
          f"{R['D_gold_alpha_oracle']['val_with_oracle']['accuracy']} vs "
          f"learned {R['D_gold_alpha_oracle']['learned_alpha_reference']['accuracy']}")

    # ---- E: contextual-candidate oracle (+ combined D+E) ----
    tb_ctx, _ = prep(train_recs, "S3", "train",
                     seeded_order(len(train_recs), 11), contextual=True)
    vb_ctx, _ = prep(val_recs, "S3", "val", contextual=True)
    e_head, _ = train_head(fresh_head(), tb_ctx, vb_ctx, 1000, device, 11)
    R["E_contextual_candidates"] = {
        "val": eval_head(e_head, vb_ctx, device)}
    de_head, _ = train_head(fresh_head(), tb_ctx, vb_ctx, 1000, device, 11,
                            alpha_tr=a_tr)
    R["E_plus_D_combined"] = {
        "val": eval_head(de_head, vb_ctx, device, alpha_ov=a_va)}
    print(f"[E] contextual-cand val acc = "
          f"{R['E_contextual_candidates']['val']['accuracy']}; D+E = "
          f"{R['E_plus_D_combined']['val']['accuracy']}")

    # ---- F: profile sensitivity on the trained S3 head ----
    perm = [2, 3, 0, 1]
    perm_p = [b["p"][:, :, perm] for b in vb_full]
    unif_p = [torch.full_like(b["p"], 0.25) for b in vb_full]
    R["F_profile_sensitivity"] = {
        "true_profiles": eval_head(s3_head, vb_full, device),
        "uniform_profiles": eval_head(s3_head, vb_full, device,
                                      profiles_override=unif_p),
        "permuted_profiles": eval_head(s3_head, vb_full, device,
                                       profiles_override=perm_p),
        "zeroed_w_p": eval_head(s3_head, vb_full, device, zero_wp=True),
        "w_p_gradient_log": grad_log}
    print(f"[F] true={R['F_profile_sensitivity']['true_profiles']['accuracy']} "
          f"unif={R['F_profile_sensitivity']['uniform_profiles']['accuracy']} "
          f"perm={R['F_profile_sensitivity']['permuted_profiles']['accuracy']} "
          f"zero={R['F_profile_sensitivity']['zeroed_w_p']['accuracy']}")

    # ---- G: attention inspection ----
    R["G_attention"] = {
        "val": eval_head(s3_head, vb_full, device, want_attention=True,
                         gold_list=gold_va)["attention"],
        "train_first600": eval_head(
            s3_head, [b for b in tb_full][:19], device, want_attention=True,
            gold_list=gold_tr)["attention"]}
    print(f"[G] val attention: {R['G_attention']['val']}")

    R["total_wall_clock_seconds"] = round(time.time() - t0, 1)
    (out_dir / "DIAGNOSTIC_RESULTS.json").write_text(
        json.dumps(R, indent=2) + "\n", encoding="utf-8")
    print(f"\nDIAGNOSTICS COMPLETE in {R['total_wall_clock_seconds']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
