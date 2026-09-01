"""run_pilot_v3.py -- CJT-DEV-P1.3: the FINAL binding-conversion round (owner
ruling "we won a component-level mechanism result; we did not win the full
task"). DEVELOPMENT-ONLY, NON-CLAIM-BEARING. Train/validation only.

FROZEN from P1.2b (owner order -- only the binder changes): Qwen2.5-0.5B
checkpoint; LAYER 18; contextual candidate mode; all profile tables (S3 CAS
one-hot, S6 uniform, S7-H hard lexname, S7-Delta-WN1-V3 soft simplex); the
router design (content score + lambda*(W_r g . p_i), lambda init 1.0
learnable); datasets; seeds 11/23/47; AdamW settings; 1000-update schedule;
checkpoints 0/50/100/250/500/750/1000.

REPLACED: the pooled binder (weighted-average passage vector -> compare with
every candidate) becomes CLAUSE-LOCAL ANSWER EXPERTS:

    l_{i,c} = <U_g g, U_e e_{i,c}>/sqrt(d) + <U_h h_i, U_e e_{i,c}>/sqrt(d)
    P(c|i)  = softmax_c over candidates PRESENT in clause i (absent = masked)
    P(c|x)  = sum_i alpha_i * P(c|i)          # router-weighted mixture
    loss    = -log P(answer|x)

where e_{i,c} is candidate c's contextual occurrence INSIDE clause i (mean of
its layer-18 token states within the clause span). Each clause is a local
answer expert; the profile helps ROUTE to the experts; no gold clause enters
training or evaluation.

SMOKE GATES (owner-specified; failure of 1 or 2 => BINDING_REPAIR_FAILED):
  1. 128-example memorization >= 95% training accuracy
  2. gold-clause routing beats SHUFFLED routing by >= 10 points (on the
     memorization head's own examples -- a pure mechanism test)
  3. shuffling candidate-to-clause links damages accuracy by >= 5 points
  4. S3 profile variants produce measurably different logits
  5. S6 exactly invariant under profile replacement
  6. finite losses, matched params (+-1%), GPU-only, auto-termination

Win law (P1): S3 must beat EVERY control by >= 0.02 mean val accuracy, with
the advantage positive in >= 2/3 seeds AND reduced by profile corruption.
Otherwise: close the static v1 readout line, preserve all results, pivot to
PATH B -- no third binder.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
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
from exec.arms import D_ATT, D_MODEL, MAX_IDEAS, N_CLASSES  # noqa: E402
from exec.dataset_assembly import assemble_examples  # noqa: E402
from exec.baselines import score_split  # noqa: E402
from exec.spans import build_input_text, clause_char_spans  # noqa: E402
from run_pilot import lr_lambda, load_records, seeded_order  # noqa: E402
from run_pilot_v2 import assemble  # noqa: E402  (S7H/S7D profile sources)
from run_diagnostics import gold_clause_index  # noqa: E402

L_FROZEN = 18                       # owner-frozen layer (P1.2b selection)
D_EXP = 256
SEEDS = [11, 23, 47]
CHECKPOINTS = [0, 50, 100, 250, 500, 750, 1000]
BATCH_SIZE = 32
LR, BETAS, WD, CLIP = 1.0e-3, (0.9, 0.999), 0.01, 1.0
ARMS = ["S0", "S3", "S6", "S7H", "S7D"]
ARM_TAGS = {
    "S0": {"profile_semantics": "NONE", "authority": "PLAIN_BASELINE"},
    "S3": {"profile_semantics": "EXACT_OPERATION_IDENTITY",
           "authority": "CONSTRUCTION_GOLD"},
    "S6": {"profile_semantics": "UNIFORM_CONTROL",
           "authority": "EXPERIMENTAL_CONTROL"},
    "S7H": {"profile_semantics": "EXCLUSIVE_LEXICAL_CATEGORY",
            "authority": "RESOURCE_DERIVED_CONTROL"},
    "S7D": {"profile_semantics": "WORDNET_LEXICAL_FACTOR_COMPOSITION",
            "authority": "RESOURCE_DERIVED_CONTROL"},
}
GRAD_LOG_STEPS = (50, 100, 250, 500, 1000)
EPS_P = 1e-9


# ---------------- clause-local candidate extraction (layer 18) ---------------
def extract_clause_local(records, tok, model, device):
    """{pid: {"mask": (N,C) bool, "vecs": {(i,j): (896,) fp16}}} -- candidate
    j's mean layer-18 token state within clause i's char span."""
    import torch
    out = {}
    with torch.no_grad():
        for rec in records:
            text = build_input_text(rec)
            enc = tok(text, return_offsets_mapping=True, return_tensors="pt")
            offs = enc["offset_mapping"][0].tolist()
            hs = model(input_ids=enc["input_ids"].to(device),
                       attention_mask=enc["attention_mask"].to(device),
                       output_hidden_states=True).hidden_states[L_FROZEN][0] \
                .float()
            spans, _ = clause_char_spans(rec)
            low = text.lower()
            N, C = len(rec["clauses"]), len(rec["candidates"])
            mask = [[False] * C for _ in range(N)]
            vecs = {}
            for j, cand in enumerate(rec["candidates"]):
                occ = [(m.start(), m.end()) for m in
                       re.finditer(rf"\b{re.escape(cand.lower())}\b", low)]
                for i, (cs, ce) in enumerate(spans):
                    inside = [(s, e) for s, e in occ if s >= cs and e <= ce]
                    if not inside:
                        continue
                    tix = [ti for ti, (a, b) in enumerate(offs)
                           if b > a and any(a < e and b > s for s, e in inside)]
                    if tix:
                        mask[i][j] = True
                        vecs[(i, j)] = hs[torch.tensor(
                            tix, device=hs.device)].mean(0).half().cpu()
            out[rec["passage_id"]] = {"mask": mask, "vecs": vecs}
    return out


# ---------------- batching with clause-local tensors -------------------------
def pack_batches_v3(examples, feats, loc, order):
    import torch
    ordered = [examples[i] for i in order]
    batches = []
    for start in range(0, len(ordered), BATCH_SIZE):
        chunk = ordered[start:start + BATCH_SIZE]
        b = len(chunk)
        max_c = max(len(ex["candidates"]) for ex in chunk)
        h = torch.zeros(b, MAX_IDEAS, D_MODEL)
        g = torch.zeros(b, D_MODEL)
        idea_mask = torch.zeros(b, MAX_IDEAS, dtype=torch.bool)
        e_loc = torch.zeros(b, MAX_IDEAS, max_c, D_MODEL)
        m_loc = torch.zeros(b, MAX_IDEAS, max_c, dtype=torch.bool)
        cand_mask = torch.zeros(b, max_c, dtype=torch.bool)
        answer_index = torch.zeros(b, dtype=torch.long)
        has_p = chunk[0]["profiles"] is not None
        p = torch.zeros(b, MAX_IDEAS, N_CLASSES) if has_p else None
        qts = []
        for j, ex in enumerate(chunk):
            pid = ex["passage_id"]
            f = feats[pid]
            n, c = f["h"].shape[0], len(ex["candidates"])
            h[j, :n] = f["h"].float(); g[j] = f["g"].float()
            idea_mask[j, :n] = True
            cand_mask[j, :c] = True
            answer_index[j] = ex["answer_index"]
            qts.append(ex["question_type"])
            L = loc[pid]
            for (i, k), v in L["vecs"].items():
                if i < MAX_IDEAS:
                    e_loc[j, i, k] = v.float()
                    m_loc[j, i, k] = True
            if p is not None:
                p[j, :n] = torch.tensor(ex["profiles"], dtype=torch.float32)
        batches.append({"h": h, "g": g, "p": p, "idea_mask": idea_mask,
                        "e_loc": e_loc, "m_loc": m_loc, "cand_mask": cand_mask,
                        "answer_index": answer_index, "qt": qts})
    return batches


# ---------------- the MixtureHead: frozen router + clause-local experts ------
def build_mixture_head(use_profiles: bool, widen_w: int = 0):
    import torch
    import torch.nn as nn

    class MixtureHead(nn.Module):
        def __init__(self, use_p, w):
            super().__init__()
            self.use_p = use_p
            # FROZEN router design (P1.2b): content + lambda*(W_r g . p)
            self.w_q = nn.Linear(D_MODEL, D_ATT)
            self.w_k = nn.Linear(D_MODEL, D_ATT)
            if use_p:
                self.w_r = nn.Linear(D_MODEL, N_CLASSES)
                self.lam = nn.Parameter(torch.ones(1))
            # NEW clause-local answer experts
            self.u_g = nn.Linear(D_MODEL, D_EXP)
            self.u_h = nn.Linear(D_MODEL, D_EXP)
            self.u_e = (nn.Linear(D_MODEL, D_EXP) if w == 0 else
                        nn.Sequential(nn.Linear(D_MODEL, w), nn.GELU(),
                                      nn.Linear(w, D_EXP)))

        def forward(self, h, g, p, idea_mask, e_loc, m_loc, cand_mask,
                    alpha_override=None, return_alpha=False):
            import torch
            neg = torch.finfo(h.dtype).min
            s = (self.w_q(g).unsqueeze(1) * self.w_k(h)).sum(-1) / (D_ATT ** 0.5)
            if self.use_p:
                s = s + self.lam * (self.w_r(g).unsqueeze(1) * p).sum(-1)
            s = s.masked_fill(~idea_mask, neg)
            alpha = torch.softmax(s, dim=1) if alpha_override is None \
                else alpha_override
            qe = self.u_g(g)                                    # (B,d)
            he = self.u_h(h)                                    # (B,N,d)
            ee = self.u_e(e_loc)                                # (B,N,C,d)
            l_ic = (qe[:, None, None, :] * ee).sum(-1) / (D_EXP ** 0.5) \
                + (he[:, :, None, :] * ee).sum(-1) / (D_EXP ** 0.5)   # (B,N,C)
            l_ic = l_ic.masked_fill(~m_loc, neg)
            # clause-local answer distributions; a clause with NO present
            # candidate contributes a zero row (guarded), and its alpha mass
            # is effectively wasted -- correct fail-safe behavior
            has_any = m_loc.any(dim=2)                          # (B,N)
            P_ci = torch.softmax(l_ic, dim=2)
            P_ci = torch.where(has_any.unsqueeze(-1), P_ci,
                               torch.zeros_like(P_ci))
            P = (alpha.unsqueeze(-1) * P_ci).sum(dim=1)         # (B,C)
            P = P.masked_fill(~cand_mask, 0.0)
            logp = (P + EPS_P).log()
            logp = logp.masked_fill(~cand_mask, neg)
            return (logp, alpha) if return_alpha else logp

    return MixtureHead(use_profiles, widen_w)


def param_count(m):
    return sum(p.numel() for p in m.parameters() if p.requires_grad)


def match_s0_capacity(ref: int) -> int:
    for w in range(0, 4096):
        if abs(param_count(build_mixture_head(False, w)) - ref) <= 0.01 * ref:
            return w
    raise RuntimeError("CAPACITY_MATCH_FAILURE")


# ---------------- training + instrumentation --------------------------------
def _fwd(head, bt, device, **kw):
    return head(bt["h"].to(device), bt["g"].to(device),
                None if bt["p"] is None else bt["p"].to(device),
                bt["idea_mask"].to(device), bt["e_loc"].to(device),
                bt["m_loc"].to(device), bt["cand_mask"].to(device), **kw)


def train_arm(arm, seed, widen_w, tb, vb, updates, device, gold_va=None):
    import torch
    torch.manual_seed(seed)
    if device.startswith("cuda"):
        torch.cuda.manual_seed_all(seed)
        torch.cuda.reset_peak_memory_stats()
    head = build_mixture_head(arm != "S0", widen_w).float().to(device)
    opt = torch.optim.AdamW(head.parameters(), lr=LR, betas=BETAS,
                            weight_decay=WD)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lr_lambda(updates))
    nll = torch.nn.NLLLoss()
    curve, cps, grad_log = [], set(CHECKPOINTS), []
    t0 = time.time()

    def evaluate():
        head.eval()
        tot = cor = 0
        ls = 0.0
        per = {}
        with torch.no_grad():
            for bt in vb:
                logp = _fwd(head, bt, device)
                tgt = bt["answer_index"].to(device)
                ls += float(torch.nn.functional.nll_loss(
                    logp, tgt, reduction="sum").item())
                ok = logp.argmax(1) == tgt
                cor += int(ok.sum()); tot += len(tgt)
                for i, qt in enumerate(bt["qt"]):
                    a, c = per.get(qt, (0, 0))
                    per[qt] = (a + int(ok[i].item()), c + 1)
        head.train()
        return {"val_accuracy": cor / tot, "val_loss": ls / tot,
                "per_question_type": {k: {"accuracy": a / c, "correct": a,
                                          "total": c}
                                      for k, (a, c) in sorted(per.items())}}

    if 0 in cps:
        curve.append({"step": 0, "train_loss": None, **evaluate()})
    pos = 0
    for step in range(updates):
        bt = tb[pos]; pos = (pos + 1) % len(tb)
        logp = _fwd(head, bt, device)
        loss = nll(logp, bt["answer_index"].to(device))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        if (step + 1) in GRAD_LOG_STEPS and arm != "S0":
            grad_log.append({"step": step + 1,
                             "w_r_grad_norm": float(head.w_r.weight.grad.norm())
                             if head.w_r.weight.grad is not None else 0.0,
                             "lam_grad": float(head.lam.grad.item())
                             if head.lam.grad is not None else 0.0,
                             "lam_value": float(head.lam.item())})
        torch.nn.utils.clip_grad_norm_(head.parameters(), CLIP)
        opt.step(); sched.step()
        last = float(loss.item())
        if not math.isfinite(last):
            raise RuntimeError(f"NONFINITE_LOSS {arm} seed {seed} step {step}")
        if (step + 1) in cps:
            curve.append({"step": step + 1, "train_loss": last, **evaluate()})

    # profile sensitivity (variants of p; "zeroed" kills the routing signal)
    def eval_variant(pmap=None, alpha_ov=None, shuffle_binding=False):
        head.eval()
        tot = cor = 0
        dsum = dn = 0.0
        gen = __import__("torch").Generator().manual_seed(20260831)
        with __import__("torch").no_grad():
            for bi, bt in enumerate(vb):
                import torch as _t
                kw = {}
                if alpha_ov is not None:
                    kw["alpha_override"] = alpha_ov[bi]
                bt2 = bt
                if shuffle_binding:
                    # PER-EXAMPLE permutation restricted to the LIVE clause
                    # prefix (0..n_ideas-1): measures pure candidate-to-clause
                    # RE-LINKING. Permuting the full padded axis would park
                    # real evidence rows under masked alpha=0 positions --
                    # deletion, not mislinking (74.6% of records have <6
                    # clauses; adversarial pre-launch review finding). Perms
                    # are drawn sequentially from the seeded generator, so the
                    # sequence is deterministic and identical across arms.
                    import torch as _t
                    bt2 = dict(bt)
                    e2 = bt["e_loc"].clone()
                    m2 = bt["m_loc"].clone()
                    n_live = bt["idea_mask"].sum(dim=1)
                    for j in range(e2.shape[0]):
                        n = int(n_live[j])
                        if n > 1:
                            prm = _t.randperm(n, generator=gen)
                            e2[j, :n] = bt["e_loc"][j, prm]
                            m2[j, :n] = bt["m_loc"][j, prm]
                    bt2["e_loc"] = e2
                    bt2["m_loc"] = m2
                p_true = None if bt["p"] is None else bt["p"]
                lt = _fwd(head, bt, device)
                if pmap is None and not shuffle_binding and alpha_ov is None:
                    lv = lt
                else:
                    b3 = dict(bt2)
                    if pmap is not None and p_true is not None:
                        b3["p"] = pmap(p_true)
                    lv = _fwd(head, b3, device, **kw)
                m = bt["cand_mask"].to(device)
                dsum += float((lv - lt).abs()[m].sum()); dn += float(m.sum())
                tgt = bt["answer_index"].to(device)
                cor += int((lv.argmax(1) == tgt).sum()); tot += len(tgt)
        head.train()
        return {"accuracy": round(cor / tot, 6),
                "mean_abs_logit_delta_vs_true": round(dsum / max(dn, 1), 6)}

    import torch as _t
    profile_sensitivity = None
    if arm != "S0":
        perm = [2, 3, 0, 1]
        profile_sensitivity = {
            "true": eval_variant(),
            "permuted": eval_variant(pmap=lambda p: p[:, :, perm]),
            "uniform": eval_variant(pmap=lambda p: _t.full_like(p, 0.25)),
            "zeroed": eval_variant(pmap=lambda p: _t.zeros_like(p))}
    binding_shuffle = eval_variant(shuffle_binding=True)

    attention = None
    if gold_va is not None:
        ent_l, hit_l, mass_l = [], [], []
        k = 0
        head.eval()
        with _t.no_grad():
            for bt in vb:
                _, alpha = _fwd(head, bt, device, return_alpha=True)
                m = bt["idea_mask"].to(device)
                a = alpha.clamp_min(1e-12)
                ent = -(a * a.log()).masked_fill(~m, 0.0).sum(1)
                n_i = m.sum(1).float().clamp(min=2)
                ent_l += (ent / n_i.log()).tolist()
                top1 = alpha.argmax(1)
                for j in range(alpha.shape[0]):
                    gi = gold_va[k + j]
                    hit_l.append(int(top1[j].item()) == gi)
                    mass_l.append(float(alpha[j, min(gi, MAX_IDEAS - 1)].item()))
                k += alpha.shape[0]
        head.train()
        attention = {"mean_normalized_entropy": round(sum(ent_l) / len(ent_l), 6),
                     "gold_top1_rate": round(sum(hit_l) / len(hit_l), 6),
                     "mean_gold_mass": round(sum(mass_l) / len(mass_l), 6)}

    head.eval()
    tr_cor = tr_tot = 0
    with _t.no_grad():
        for bt in tb[:32]:
            lt = _fwd(head, bt, device)
            tgt = bt["answer_index"].to(device)
            tr_cor += int((lt.argmax(1) == tgt).sum()); tr_tot += len(tgt)
    head.train()

    return {"arm": arm, "seed": seed, "widen_w": widen_w,
            "trainable_params": param_count(head),
            "learned_lambda": (float(head.lam.item()) if arm != "S0" else None),
            "curve": curve, "final": curve[-1],
            "train_subset_accuracy": round(tr_cor / tr_tot, 6),
            "profile_grad_log": grad_log or None,
            "profile_sensitivity": profile_sensitivity,
            "binding_shuffle": binding_shuffle,
            "attention": attention,
            "wall_clock_seconds": round(time.time() - t0, 2),
            "peak_gpu_mem_mb": round(
                (_t.cuda.max_memory_allocated() / 1e6)
                if device.startswith("cuda") else 0.0, 1)}, head


# ---------------- smoke gates 1-3 (memorization + routing exploitation) ------
def smoke_binding_gates(train_recs, feats_tr, loc_tr, s7h, s7d, device):
    import torch
    sub = train_recs[:128]
    exs = assemble(sub, "S3", s7h, s7d)
    tb = pack_batches_v3(exs, feats_tr, loc_tr, seeded_order(128, 11))
    r, head = train_arm("S3", 11, 0, tb, tb, 600, device)
    mem_acc = r["train_subset_accuracy"]                    # on its own 128
    # gold vs shuffled routing on the SAME 128 (mechanism test)
    order = seeded_order(128, 11)
    gold = [(gold_clause_index(sub[i])[0] or 0) for i in order]
    gen = torch.Generator().manual_seed(47)
    shuf = [gold[i] for i in torch.randperm(128, generator=gen).tolist()]

    def routed_acc(idxs):
        k = 0
        cor = tot = 0
        head.eval()
        with torch.no_grad():
            for bt in tb:
                b = bt["h"].shape[0]
                a = torch.zeros(b, MAX_IDEAS)
                for j in range(b):
                    a[j, min(idxs[k + j], MAX_IDEAS - 1)] = 1.0
                logp = _fwd(head, bt, device, alpha_override=a.to(device))
                tgt = bt["answer_index"].to(device)
                cor += int((logp.argmax(1) == tgt).sum()); tot += b
                k += b
        return cor / tot
    acc_gold, acc_shuf = routed_acc(gold), routed_acc(shuf)
    bind = r["binding_shuffle"]  # measured on vb=tb here (its own examples)
    return {"memorization_128_train_accuracy": round(mem_acc, 6),
            "gold_routed_accuracy": round(acc_gold, 6),
            "shuffled_routed_accuracy": round(acc_shuf, 6),
            "gold_minus_shuffled": round(acc_gold - acc_shuf, 6),
            "binding_shuffle_accuracy": bind["accuracy"],
            "binding_shuffle_drop": round(mem_acc - bind["accuracy"], 6),
            "gate1_memorize_ge_95": mem_acc >= 0.95,
            "gate2_gold_beats_shuffled_by_10": (acc_gold - acc_shuf) >= 0.10,
            "gate3_binding_shuffle_damages_5": (mem_acc - bind["accuracy"])
            >= 0.05}


# ---------------- main -------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["P0", "P1"])
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out-dir", default=str(HERE / "results_v3"))
    ap.add_argument("--updates", type=int, default=None)
    ap.add_argument("--device-note", default="cloud GPU")
    ap.add_argument("--cost-per-hour", type=float, default=0.0)
    args = ap.parse_args()
    import torch
    if args.device.startswith("cuda") and not torch.cuda.is_available():
        raise SystemExit("GPU_REQUIRED: no CPU neural fallback")
    device = args.device
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    updates = args.updates or (100 if args.stage == "P0" else 1000)
    t_start = time.time()

    s7h = json.loads((HERE / "S7_H_WN1.json").read_text("utf-8"))["verb_to_class"]
    s7d = json.loads((HERE / "S7_DELTA_WN1_V3.json").read_text("utf-8"))["verb_to_profile"]
    table_shas = {
        "s7_h_table_sha256": hashlib.sha256(
            (HERE / "S7_H_WN1.json").read_bytes()).hexdigest(),
        "s7_delta_v3_table_sha256": hashlib.sha256(
            (HERE / "S7_DELTA_WN1_V3.json").read_bytes()).hexdigest()}
    train_recs = load_records("train")
    val_recs = load_records("val")

    from transformers import AutoTokenizer, AutoModel
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModel.from_pretrained(MODEL_ID, torch_dtype=torch.float16) \
        .to(device).eval()
    is_real = device.startswith("cuda") and next(model.parameters()).is_cuda
    cache_dir = out / "cache"; cache_dir.mkdir(exist_ok=True)
    caches, loc = {}, {}
    for split, recs in (("train", train_recs), ("val", val_recs)):
        cf = cache_dir / f"{split}_acts.pt"
        if cf.is_file():
            caches[split] = torch.load(cf, map_location="cpu",
                                       weights_only=False)
        else:
            caches[split] = extract_split(recs, tok, model, [L_FROZEN], device)
            torch.save(caches[split], cf)
        lf = cache_dir / f"{split}_loc.pt"
        if lf.is_file():
            loc[split] = torch.load(lf, map_location="cpu", weights_only=False)
        else:
            te = time.time()
            loc[split] = extract_clause_local(recs, tok, model, device)
            torch.save(loc[split], lf)
            print(f"[loc-extract] {split} {time.time()-te:.0f}s")
    del model
    if device.startswith("cuda"):
        torch.cuda.empty_cache()

    def feats(split):
        return {pid: {"h": v["layers"][L_FROZEN][0],
                      "g": v["layers"][L_FROZEN][1]}
                for pid, v in caches[split].items()}
    ftr, fva = feats("train"), feats("val")

    # answer-present sanity: every answer must occur in >=1 clause
    missing = 0
    for recs, l in ((train_recs, loc["train"]), (val_recs, loc["val"])):
        for r in recs:
            j = r["candidates"].index(r["answer"])
            if not any(row[j] for row in l[r["passage_id"]]["mask"]):
                missing += 1
    print(f"[sanity] answers with no clause-local occurrence: {missing}")

    baselines = {"B0_floor_val": score_split(val_recs, "B0"),
                 "B1_ceiling_val": score_split(val_recs, "B1"),
                 "candidate_uniform_val": {
                     "accuracy": round(sum(1 / len(r["candidates"])
                                           for r in val_recs) / len(val_recs), 5),
                     "cross_entropy": round(sum(math.log(len(r["candidates"]))
                                                for r in val_recs)
                                            / len(val_recs), 5)}}

    ref = param_count(build_mixture_head(True, 0))
    widen = {a: (match_s0_capacity(ref) if a == "S0" else 0) for a in ARMS}
    counts = {a: param_count(build_mixture_head(a != "S0", widen[a]))
              for a in ARMS}
    print(f"[capacity] ref={ref} counts={counts} widen={widen}")

    smoke = None
    if args.stage == "P0":
        smoke = smoke_binding_gates(train_recs, ftr, loc["train"],
                                    s7h, s7d, device)
        print(f"[smoke] {json.dumps(smoke)}")

    _gold = [gold_clause_index(r) for r in val_recs]
    gold_unresolved = sum(1 for gi, _ in _gold if gi is None)
    gold_va = [(gi if gi is not None else 0) for gi, _ in _gold]
    if gold_unresolved:
        print(f"[gold] WARNING: {gold_unresolved} unresolved")

    seeds = [11] if args.stage == "P0" else SEEDS
    runs = []
    for arm in ARMS:
        ex_tr = assemble(train_recs, arm, s7h, s7d)
        ex_va = assemble(val_recs, arm, s7h, s7d)
        vb = pack_batches_v3(ex_va, fva, loc["val"],
                             list(range(len(ex_va))))
        for seed in seeds:
            tb = pack_batches_v3(ex_tr, ftr, loc["train"],
                                 seeded_order(len(ex_tr), seed))
            r, _ = train_arm(arm, seed, widen[arm], tb, vb, updates, device,
                             gold_va=gold_va)
            r["layer"] = L_FROZEN
            runs.append(r)
            sens = r["profile_sensitivity"]
            print(f"[{args.stage}] {arm:4} seed={seed} "
                  f"acc={r['final']['val_accuracy']:.4f} "
                  f"loss={r['final']['val_loss']:.4f} "
                  f"lam={r['learned_lambda']} "
                  f"trainacc={r['train_subset_accuracy']:.3f} "
                  f"goldhit={r['attention']['gold_top1_rate']:.3f} "
                  f"bindshuf={r['binding_shuffle']['accuracy']:.3f} "
                  f"{r['wall_clock_seconds']}s")

    total_wall = time.time() - t_start
    write_outputs(out, args, updates, counts, baselines, runs, seeds,
                  table_shas, is_real, total_wall, device, smoke,
                  gold_unresolved)
    return 0


def _mean_std(xs):
    m = sum(xs) / len(xs)
    return m, math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def write_outputs(out, args, updates, counts, baselines, runs, seeds,
                  table_shas, is_real, total_wall, device, smoke,
                  gold_unresolved):
    by_arm = {}
    for a in ARMS:
        rs = [r for r in runs if r["arm"] == a]
        accs = [r["final"]["val_accuracy"] for r in rs]
        m, s = _mean_std(accs)
        sens = [r["profile_sensitivity"] for r in rs if r["profile_sensitivity"]]
        by_arm[a] = {"final_val_accuracy_mean": round(m, 6),
                     "final_val_accuracy_std": round(s, 6),
                     "final_val_accuracy_by_seed": {
                         r["seed"]: round(r["final"]["val_accuracy"], 6)
                         for r in rs},
                     "final_val_loss_mean": round(
                         sum(r["final"]["val_loss"] for r in rs) / len(rs), 6),
                     "learned_lambda_by_seed": [r["learned_lambda"]
                                                for r in rs],
                     "train_subset_accuracy_mean": round(
                         sum(r["train_subset_accuracy"] for r in rs)
                         / len(rs), 6),
                     "attention_gold_top1_rate_mean": round(
                         sum(r["attention"]["gold_top1_rate"] for r in rs)
                         / len(rs), 6),
                     "binding_shuffle_accuracy_mean": round(
                         sum(r["binding_shuffle"]["accuracy"] for r in rs)
                         / len(rs), 6),
                     "profile_sensitivity_mean": (None if not sens else {
                         k: {"accuracy": round(sum(x[k]["accuracy"]
                                                   for x in sens)
                                               / len(sens), 6)}
                         for k in ("true", "permuted", "uniform", "zeroed")}),
                     "trainable_params": counts[a], **ARM_TAGS[a]}
    comp = {f"S3_minus_{o}": round(
        by_arm["S3"]["final_val_accuracy_mean"]
        - by_arm[o]["final_val_accuracy_mean"], 6)
        for o in ("S0", "S6", "S7H", "S7D")}

    def status():
        if args.stage == "P0":
            g = {"losses_finite": all(math.isfinite(r["final"]["val_loss"])
                                      for r in runs),
                 "profile_arm_params_identical":
                     len({counts[a] for a in ARMS if a != "S0"}) == 1,
                 "s0_capacity_within_1pct":
                     abs(counts["S0"] - counts["S3"]) <= 0.01 * counts["S3"]}
            grad_ok = True
            for r in runs:
                if r["arm"] in ("S0", "S6"):
                    continue                       # S6: routing grad is 0 by design
                if not r["profile_grad_log"] or not all(
                        e["w_r_grad_norm"] > 1e-9
                        for e in r["profile_grad_log"]):
                    grad_ok = False
            g["profile_branch_receives_gradients"] = grad_ok
            s3 = next((r for r in runs if r["arm"] == "S3"), None)
            g["gate4_s3_profile_swap_changes_logits"] = bool(
                s3 and s3["profile_sensitivity"]["permuted"]
                ["mean_abs_logit_delta_vs_true"] > 1e-4)
            s6 = next((r for r in runs if r["arm"] == "S6"), None)
            g["gate5_s6_invariant"] = bool(
                s6 and s6["profile_sensitivity"]["permuted"]
                ["mean_abs_logit_delta_vs_true"] < 1e-6)
            g.update({k: v for k, v in smoke.items() if k.startswith("gate")})
            failed = [k for k, v in g.items() if v is False]
            if smoke and (not smoke["gate1_memorize_ge_95"]
                          or not smoke["gate2_gold_beats_shuffled_by_10"]):
                return ("BINDING_REPAIR_FAILED",
                        f"the new binder itself is defective: {failed}; "
                        f"smoke={smoke}")
            if failed:
                return ("PILOT_PIPELINE_FAILURE",
                        f"P0 gate(s) FAILED: {failed}; gates={g}; smoke={smoke}")
            return ("P0_SMOKE_OK", f"all gates pass: {g}; smoke={smoke}")
        beats = all(comp[f"S3_minus_{o}"] >= 0.02
                    for o in ("S0", "S6", "S7H", "S7D"))

        def sign_ok(o):
            c = 0
            for sd in seeds:
                a3 = next(r["final"]["val_accuracy"] for r in runs
                          if r["arm"] == "S3" and r["seed"] == sd)
                ao = next(r["final"]["val_accuracy"] for r in runs
                          if r["arm"] == o and r["seed"] == sd)
                c += 1 if (a3 - ao) >= 0.02 else 0
            return c >= 2
        s3s = by_arm["S3"]["profile_sensitivity_mean"]
        load_bearing = bool(
            s3s and s3s["true"]["accuracy"] > s3s["permuted"]["accuracy"]
            and s3s["true"]["accuracy"] > s3s["uniform"]["accuracy"])
        if beats and all(sign_ok(o) for o in ("S0", "S6", "S7H", "S7D")) \
                and load_bearing:
            return ("PROMISING_DEV_SIGNAL",
                    "S3 beats every control by >=0.02 with >=2/3-seed "
                    "consistency and profile-corruption reduction")
        return ("NO_DEV_SIGNAL",
                f"S3 does not clear every control by >=0.02 with the required "
                f"consistency: {comp}. Owner disposition: close the static v1 "
                f"readout line, preserve all results, pivot to PATH B -- no "
                f"third binder.")
    st, reason = status()

    raw = {"pilot": "CJT-DEV-P1.3 (binding-conversion round)",
           "architecture": "MixtureHead: FROZEN P1.2b router (content + "
                           "lambda*(W_r g . p), lambda init 1.0 learnable) + "
                           "clause-local answer experts P(c|x) = sum_i "
                           "alpha_i softmax_c(l_ic); candidates absent from a "
                           "clause are masked; no gold clause in train/eval",
           "stage": args.stage, "non_claim_bearing": True,
           "is_real_model": is_real, "device": device, "model_id": MODEL_ID,
           "layer_frozen": L_FROZEN, "candidates_mode": "clause_local_contextual",
           "updates": updates, "batch_size": BATCH_SIZE, "seeds": seeds,
           "checkpoints": CHECKPOINTS, **table_shas,
           "gold_unresolved_count": gold_unresolved,
           "smoke_gates": smoke, "baselines": baselines, "arms": by_arm,
           "arm_comparison": comp, "runs": runs,
           "total_wall_clock_seconds": round(total_wall, 1),
           "total_cost_usd": round(total_wall / 3600 * args.cost_per_hour, 4),
           "cost_note": f"{args.device_note}; compute-wall estimate at "
                        f"${args.cost_per_hour:.4f}/hr",
           "development_status": st, "development_status_reason": reason}
    (out / "DEV_PILOT_V3_RAW_RESULTS.json").write_text(
        json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    with (out / "DEV_PILOT_V3_LEARNING_CURVES.csv").open(
            "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["arm", "seed", "layer", "step", "train_loss", "val_loss",
                    "val_accuracy"])
        for r in runs:
            for c in r["curve"]:
                w.writerow([r["arm"], r["seed"], r["layer"], c["step"],
                            "" if c["train_loss"] is None
                            else round(c["train_loss"], 6),
                            round(c["val_loss"], 6),
                            round(c["val_accuracy"], 6)])
    (out / "DEV_PILOT_V3_RECEIPT.json").write_text(json.dumps(
        {"receipt_id": "DEV_PILOT_V3_RECEIPT", "stage": args.stage,
         "non_claim_bearing": True, "is_real_model": is_real,
         "raw_results_sha256": hashlib.sha256(
             (out / "DEV_PILOT_V3_RAW_RESULTS.json").read_bytes()).hexdigest(),
         **table_shas, "layer_frozen": L_FROZEN, "development_status": st,
         "total_wall_clock_seconds": round(total_wall, 1)},
        indent=2) + "\n", encoding="utf-8")
    print(f"\nDEVELOPMENT STATUS: {st}\n  {reason[:400]}")


if __name__ == "__main__":
    raise SystemExit(main())
