"""run_pathb_a1.py -- PATH-B-A1: the single authorized Recurrent Clause-Entity
Graph Executor (owner directive; earned by A0's GRAPH_EXECUTOR_EARNED).
DEVELOPMENT-ONLY, NON-CLAIM-BEARING. Train/validation only; both protected
splits untouched. Frozen layer 6 (A0's earliest passing layer, frozen rule).

Two preregistered recurrent hops over the bipartite clause-entity graph
(surface-derived membership only; no formal gold edge at runtime):

  r0(c)   = uniform over candidates NAMED IN THE QUESTION (surface anchors)
  hop 1:  s1_i = <Wq1 g, Wk1 h_i>/sqrt(d) + lam1*<Wr1 g, p_i>
                 + mu1 * sum_c r0(c) M_ic
          alpha1 = softmax(s1);  P1(c|i) = softmax_c MLP1([g, h_i, e_ic])
          r1 = sum_i alpha1_i P1(c|i)          # the SOFT BRIDGE POINTER
          b1 = sum_c r1(c) ebar_c ; q1 = GELU(Wu [g ; b1])
  hop 2:  s2_j = <Wq2 q1, Wk2 h_j>/sqrt(d) + lam2*<Wr2 q1, p_j>
                 + mu2 * sum_c r1(c) M_jc
          alpha2 = softmax(s2); P2(c|j) = softmax_c MLP2([q1, h_j, b1, e_jc])
          r2 = sum_j alpha2_j P2(c|j)          # the ANSWER distribution

The intermediate entity pointer r1 is NEVER collapsed before hop 2 (owner
law). Identical executor for S0/S3/S-ALT50/S6; only profiles differ (S0 has
no profile pathway; capacity-matched by widening MLP1's hidden layer).

P0 gates (A1 law): 128-memorization >= 0.95 (bounded 800 updates); gold-path
oracle accuracy >= 0.95 and gold-minus-shuffled-path >= 0.30 (diagnostic
alpha overrides only); bridge top-1 reported; rewired-membership drop
>= 0.30; S3 profile grads nonzero; S3 swap moves logits; S6 exactly
invariant; finite losses; params matched +-1%. Competence/gold failure =>
PATH_B_COMPOSITIONAL_EXECUTOR_FAILED, no P1.

P1 dose law (3 retained families; the ruling's "3 of 4 families" clause is
proportionally registered as "2 of 3" and this adjustment is DISCLOSED):
PROMISING_PATH_B_OPERATION_SIGNAL requires S3-S0>=0.02, S3-S6>=0.02,
S3-SALT50>=0.01, exact>partial>uniform overall AND in >=2/3 families,
S3-S0 exceeding the registered B-KEY increment, S3 corruption reduction,
competence floor (S3 val >= uniform+0.15), and the advantage surviving
removal of its best family. Else NO_PATH_B_OPERATION_SIGNAL.
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
sys.path.insert(0, str(HERE))

from exec.activation_extraction import MODEL_ID, extract_split  # noqa: E402
from run_pilot import lr_lambda, seeded_order  # noqa: E402
from pathb_core import CLASSES, alt50_class  # noqa: E402
from pathb_a0_probe import extract_clause_local, gold_path  # noqa: E402

L_FROZEN = 6                      # A0 earliest passing layer (frozen rule)
FAMS = ("QB_REL", "QB_COMP", "QB_INT")
SEEDS = [11, 23, 47]
CHECKPOINTS = [0, 50, 100, 250, 500, 750, 1000]
BATCH = 32
LR, BETAS, WD, CLIP = 1.0e-3, (0.9, 0.999), 0.01, 1.0
D, D_ATT, HDIM = 896, 64, 256
EPS_P = 1e-9
ARMS = ["S0", "S3", "SALT50", "S6"]
BKEY_INCREMENT = 0.019            # max registered per-family increment (checks)


def load_records(split):
    p = HERE / "data" / f"{split}.jsonl"
    recs = [json.loads(l) for l in p.read_text("utf-8").splitlines() if l]
    return [r for r in recs if r["question_type"] in FAMS]


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


def pack(records, acts, loc, arm, order):
    import torch
    out = []
    ordered = [records[i] for i in order]
    for start in range(0, len(ordered), BATCH):
        chunk = ordered[start:start + BATCH]
        b = len(chunk)
        maxc = max(len(r["candidates"]) for r in chunk)
        N = 6
        h = torch.zeros(b, N, D)
        g = torch.zeros(b, D)
        e = torch.zeros(b, N, maxc, D)
        m = torch.zeros(b, N, maxc, dtype=torch.bool)
        cmask = torch.zeros(b, maxc, dtype=torch.bool)
        imask = torch.zeros(b, N, dtype=torch.bool)
        r0 = torch.zeros(b, maxc)
        p = None if arm == "S0" else torch.zeros(b, N, 4)
        ans = torch.zeros(b, dtype=torch.long)
        qt, sel_g, fin_g, br_g = [], [], [], []
        for j, rec in enumerate(chunk):
            pid = rec["passage_id"]
            n = len(rec["clauses"])
            C = len(rec["candidates"])
            hg = acts[pid]["layers"][L_FROZEN]
            h[j, :n] = hg[0].float()
            g[j] = hg[1].float()
            imask[j, :n] = True
            cmask[j, :C] = True
            for (i, k), v in loc[pid][L_FROZEN].items():
                e[j, i, k] = v.float()
                m[j, i, k] = True
            qtext = f" {rec['question'].lower()} "
            named = [k for k, cand in enumerate(rec["candidates"])
                     if f" {cand.lower()} " in qtext.replace("?", " ")]
            if named:
                for k in named:
                    r0[j, k] = 1.0 / len(named)
            else:
                r0[j, :C] = 1.0 / C
            prof = profiles_for(rec, arm)
            if p is not None:
                p[j, :n] = torch.tensor(prof, dtype=torch.float32)
            ans[j] = rec["candidates"].index(rec["answer"])
            qt.append(rec["question_type"])
            s_, br_, f_ = gold_path(rec)
            sel_g.append(s_)
            fin_g.append(f_)
            br_g.append(rec["candidates"].index(br_))
        out.append({"h": h, "g": g, "p": p, "e": e, "m": m, "cmask": cmask,
                    "imask": imask, "r0": r0, "ans": ans, "qt": qt,
                    "sel": sel_g, "fin": fin_g, "bridge": br_g})
    return out


def build_executor(use_profiles: bool, widen: int = 0):
    import torch
    import torch.nn as nn

    class GraphExecutor(nn.Module):
        def __init__(self, use_p, w):
            super().__init__()
            self.use_p = use_p
            self.wq1 = nn.Linear(D, D_ATT)
            self.wk1 = nn.Linear(D, D_ATT)
            self.wq2 = nn.Linear(D, D_ATT)
            self.wk2 = nn.Linear(D, D_ATT)
            if use_p:
                self.wr1 = nn.Linear(D, 4)
                self.wr2 = nn.Linear(D, 4)
                self.lam1 = nn.Parameter(torch.ones(1))
                self.lam2 = nn.Parameter(torch.ones(1))
            self.mu1 = nn.Parameter(torch.ones(1))
            self.mu2 = nn.Parameter(torch.ones(1))
            h1 = HDIM + w
            self.mlp1 = nn.Sequential(nn.Linear(3 * D, h1), nn.GELU(),
                                      nn.Linear(h1, HDIM), nn.GELU(),
                                      nn.Linear(HDIM, 1))
            self.mlp2 = nn.Sequential(nn.Linear(4 * D, HDIM), nn.GELU(),
                                      nn.Linear(HDIM, HDIM), nn.GELU(),
                                      nn.Linear(HDIM, 1))
            self.wu = nn.Linear(2 * D, D)

        def forward(self, bt, device, alpha_ovr=None, pmap=None,
                    return_diag=False, rewire_perm=None):
            import torch
            h = bt["h"].to(device)
            g = bt["g"].to(device)
            e = bt["e"].to(device)
            m = bt["m"].to(device)
            if rewire_perm is not None:                  # destructive control
                e = e[:, rewire_perm]
                m = m[:, rewire_perm]
            cmask = bt["cmask"].to(device)
            imask = bt["imask"].to(device)
            r0 = bt["r0"].to(device)
            p = None
            if self.use_p and bt["p"] is not None:
                p = bt["p"].to(device)
                if pmap is not None:
                    p = pmap(p)
            B, N, C, _ = e.shape
            neg = torch.finfo(h.dtype).min
            ebar = (e * m.unsqueeze(-1)).sum(1) / \
                m.sum(1).clamp(min=1).unsqueeze(-1)      # (B,C,D)

            def hop(q, r_in, wq, wk, wr, lam, mu, mlp, extra):
                s = (wq(q).unsqueeze(1) * wk(h)).sum(-1) / (D_ATT ** 0.5)
                if self.use_p and p is not None:
                    s = s + lam * (wr(q).unsqueeze(1) * p).sum(-1)
                s = s + mu * (r_in.unsqueeze(1) * m.float()).sum(-1)
                s = s.masked_fill(~imask, neg)
                alpha = torch.softmax(s, dim=1)
                feats = torch.cat(
                    [q.unsqueeze(1).unsqueeze(1).expand(B, N, C, D),
                     h.unsqueeze(2).expand(B, N, C, D)] + extra + [e],
                    dim=-1)
                l = mlp(feats).squeeze(-1)
                l = l.masked_fill(~m, neg)
                P = torch.softmax(l, dim=2)
                P = torch.where(m.any(2, keepdim=True), P,
                                torch.zeros_like(P))
                return alpha, P

            a1, P1 = hop(g, r0, self.wq1, self.wk1,
                         getattr(self, "wr1", None),
                         getattr(self, "lam1", None), self.mu1,
                         self.mlp1, [])
            if alpha_ovr is not None:
                a1 = alpha_ovr[0]
            r1 = (a1.unsqueeze(-1) * P1).sum(1)
            r1 = r1.masked_fill(~cmask, 0.0)
            b1 = (r1.unsqueeze(-1) * ebar).sum(1)        # (B,D)
            q1 = torch.nn.functional.gelu(
                self.wu(torch.cat([g, b1], dim=-1)))
            a2, P2 = hop(q1, r1, self.wq2, self.wk2,
                         getattr(self, "wr2", None),
                         getattr(self, "lam2", None), self.mu2,
                         self.mlp2,
                         [b1.unsqueeze(1).unsqueeze(1).expand(B, N, C, D)])
            if alpha_ovr is not None:
                a2 = alpha_ovr[1]
            r2 = (a2.unsqueeze(-1) * P2).sum(1)
            r2 = r2.masked_fill(~cmask, 0.0)
            logp = (r2 + EPS_P).log().masked_fill(~cmask, neg)
            if return_diag:
                return logp, {"r1": r1, "a1": a1, "a2": a2}
            return logp

    return GraphExecutor(use_profiles, widen)


def param_count(mdl):
    return sum(p.numel() for p in mdl.parameters() if p.requires_grad)


def match_s0(ref):
    for w in range(0, 4096, 2):
        if abs(param_count(build_executor(False, w)) - ref) <= 0.01 * ref:
            return w
    raise RuntimeError("CAPACITY_MATCH_FAILURE")


def gold_alpha(bt, device, shuffled=False, seed=13):
    import torch
    B, N = bt["h"].shape[0], 6
    a1 = torch.zeros(B, N)
    a2 = torch.zeros(B, N)
    gen = torch.Generator().manual_seed(seed)
    for j in range(B):
        sel = bt["sel"][j]
        fins = bt["fin"][j]
        if shuffled:
            n_live = int(bt["imask"][j].sum())
            sel = int(torch.randint(0, n_live, (1,), generator=gen))
            fins = [int(torch.randint(0, n_live, (1,), generator=gen))]
        a1[j, min(sel, N - 1)] = 1.0
        for f in fins:
            a2[j, min(f, N - 1)] = 1.0 / len(fins)
    return a1.to(device), a2.to(device)


def train_model(arm, seed, widen, tb, vb, updates, device, grad_log_steps=()):
    import torch
    torch.manual_seed(seed)
    if device.startswith("cuda"):
        torch.cuda.manual_seed_all(seed)
    mdl = build_executor(arm != "S0", widen).float().to(device)
    opt = torch.optim.AdamW(mdl.parameters(), lr=LR, betas=BETAS,
                            weight_decay=WD)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lr_lambda(updates))
    nll = torch.nn.NLLLoss()
    curve, glog = [], []
    cps = set(CHECKPOINTS)

    def evaluate(batches):
        mdl.eval()
        cor = tot = 0
        ls = 0.0
        per = {}
        br_cor = 0
        with torch.no_grad():
            for bt in batches:
                logp, diag = mdl(bt, device, return_diag=True)
                tgt = bt["ans"].to(device)
                ls += float(torch.nn.functional.nll_loss(
                    logp, tgt, reduction="sum").item())
                ok = logp.argmax(1) == tgt
                cor += int(ok.sum()); tot += len(tgt)
                br = diag["r1"].argmax(1)
                for j, q in enumerate(bt["qt"]):
                    a, c = per.get(q, (0, 0))
                    per[q] = (a + int(ok[j].item()), c + 1)
                    br_cor += int(int(br[j]) == bt["bridge"][j])
        mdl.train()
        return {"val_accuracy": cor / tot, "val_loss": ls / tot,
                "bridge_top1": br_cor / tot,
                "per_question_type": {k: {"accuracy": a / c, "correct": a,
                                          "total": c}
                                      for k, (a, c) in sorted(per.items())}}

    if 0 in cps and updates >= 1000:
        curve.append({"step": 0, "train_loss": None, **evaluate(vb)})
    pos = 0
    for step in range(updates):
        bt = tb[pos]; pos = (pos + 1) % len(tb)
        logp = mdl(bt, device)
        loss = nll(logp, bt["ans"].to(device))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        if (step + 1) in grad_log_steps and arm not in ("S0", "S6"):
            glog.append({"step": step + 1,
                         "wr1_grad": float(mdl.wr1.weight.grad.norm())
                         if mdl.wr1.weight.grad is not None else 0.0,
                         "wr2_grad": float(mdl.wr2.weight.grad.norm())
                         if mdl.wr2.weight.grad is not None else 0.0})
        torch.nn.utils.clip_grad_norm_(mdl.parameters(), CLIP)
        opt.step(); sched.step()
        last = float(loss.item())
        if not math.isfinite(last):
            raise RuntimeError(f"NONFINITE_LOSS {arm} s{seed} step {step}")
        if (step + 1) in cps and updates >= 1000:
            curve.append({"step": step + 1, "train_loss": last,
                          **evaluate(vb)})
    final = curve[-1] if curve else evaluate(vb)
    tr_eval = evaluate(tb[:8])
    return mdl, {"arm": arm, "seed": seed,
                 "trainable_params": param_count(mdl),
                 "final": final, "curve": curve,
                 "train_subset_accuracy": tr_eval["val_accuracy"],
                 "grad_log": glog or None}


def eval_variant(mdl, batches, device, pmap=None, alpha_mode=None,
                 rewire=False):
    import torch
    mdl.eval()
    cor = tot = 0
    dsum = dn = 0.0
    gen = torch.Generator().manual_seed(20260901)
    with torch.no_grad():
        for bt in batches:
            kw = {}
            if alpha_mode == "gold":
                kw["alpha_ovr"] = gold_alpha(bt, device)
            elif alpha_mode == "shuffled":
                kw["alpha_ovr"] = gold_alpha(bt, device, shuffled=True)
            if rewire:
                n_live = 6
                kw["rewire_perm"] = torch.randperm(n_live, generator=gen)
            lt = mdl(bt, device)
            lv = mdl(bt, device, pmap=pmap, **kw) \
                if (pmap or kw) else lt
            msk = bt["cmask"].to(device)
            dsum += float((lv - lt).abs()[msk].sum()); dn += float(msk.sum())
            tgt = bt["ans"].to(device)
            cor += int((lv.argmax(1) == tgt).sum()); tot += len(tgt)
    mdl.train()
    return {"accuracy": round(cor / tot, 4),
            "mean_abs_logit_delta": round(dsum / max(dn, 1), 4)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["P0", "P1"])
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out-dir", default=str(HERE / "results_pathb_a1"))
    args = ap.parse_args()
    import torch
    if args.device.startswith("cuda") and not torch.cuda.is_available():
        raise SystemExit("GPU_REQUIRED: no CPU neural fallback")
    device = args.device
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    train_recs = load_records("train")
    val_recs = load_records("val")
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
            acts.update(torch.load(f1, map_location="cpu",
                                   weights_only=False))
            loc.update(torch.load(f2, map_location="cpu",
                                  weights_only=False))
        else:
            te = time.time()
            a = extract_split(recs, tok, model, [L_FROZEN], device)
            l = extract_clause_local(recs, tok, model, device, [L_FROZEN])
            torch.save(a, f1); torch.save(l, f2)
            acts.update(a); loc.update(l)
            print(f"[extract] {split} {len(recs)} recs {time.time()-te:.0f}s")
    assert len(acts) == len(train_recs) + len(val_recs), "PID_COLLISION"
    del model
    torch.cuda.empty_cache()

    ref = param_count(build_executor(True, 0))
    widen = {a: (match_s0(ref) if a == "S0" else 0) for a in ARMS}
    counts = {a: param_count(build_executor(a != "S0", widen[a]))
              for a in ARMS}
    print(f"[capacity] ref={ref} counts={counts} widen={widen}")

    vb_by_arm = {a: pack(val_recs, acts, loc, a,
                         list(range(len(val_recs)))) for a in ARMS}
    unif = {q: float(sum(1.0 / len(r["candidates"])
                         for r in val_recs if r["question_type"] == q)
                     / sum(1 for r in val_recs if r["question_type"] == q))
            for q in FAMS}
    unif_all = float(sum(1.0 / len(r["candidates"]) for r in val_recs)
                     / len(val_recs))

    if args.stage == "P0":
        # memorization (bounded 800 updates)
        sub = train_recs[:129]
        tb_sub = pack(sub, acts, loc, "S3", seeded_order(len(sub), 11))
        mdl_mem, r_mem = train_model("S3", 11, 0, tb_sub, tb_sub, 800,
                                     device, grad_log_steps=(50, 400, 800))
        mem_eval = eval_variant(mdl_mem, tb_sub, device)
        mem_acc = mem_eval["accuracy"]
        gold_ev = eval_variant(mdl_mem, tb_sub, device, alpha_mode="gold")
        shuf_ev = eval_variant(mdl_mem, tb_sub, device, alpha_mode="shuffled")
        rew_ev = eval_variant(mdl_mem, tb_sub, device, rewire=True)
        # arm smoke runs (100 updates, seed 11) for the dose gates
        runs = {}
        for arm in ARMS:
            tb = pack(train_recs, acts, loc, arm,
                      seeded_order(len(train_recs), 11))
            mdl, r = train_model(arm, 11, widen[arm], tb, vb_by_arm[arm],
                                 100, device, grad_log_steps=(50, 100))
            sens = None
            if arm != "S0":
                perm = [2, 3, 0, 1]
                sens = {
                    "true": eval_variant(mdl, vb_by_arm[arm], device),
                    "permuted": eval_variant(
                        mdl, vb_by_arm[arm], device,
                        pmap=lambda p: p[:, :, perm]),
                    "uniform": eval_variant(
                        mdl, vb_by_arm[arm], device,
                        pmap=lambda p: torch.full_like(p, 0.25))}
            r["profile_sensitivity"] = sens
            runs[arm] = r
            print(f"[P0] {arm:7} acc={r['final']['val_accuracy']:.4f} "
                  f"bridge={r['final']['bridge_top1']:.3f} "
                  f"swapD={sens['permuted']['mean_abs_logit_delta'] if sens else None}")
        s3 = runs["S3"]
        g = {"gate_memorize_ge_95": mem_acc >= 0.95,
             "gate_goldpath_ge_95": gold_ev["accuracy"] >= 0.95,
             "gate_gold_minus_shuffled_ge_30":
                 gold_ev["accuracy"] - shuf_ev["accuracy"] >= 0.30,
             "gate_rewire_drop_ge_30":
                 mem_acc - rew_ev["accuracy"] >= 0.30,
             "gate_s3_profile_grads":
                 bool(s3["grad_log"] and all(
                     e["wr1_grad"] > 1e-9 for e in s3["grad_log"])),
             "gate_s3_swap_moves_logits":
                 s3["profile_sensitivity"]["permuted"]
                 ["mean_abs_logit_delta"] > 1e-4,
             "gate_s6_invariant":
                 runs["S6"]["profile_sensitivity"]["permuted"]
                 ["mean_abs_logit_delta"] < 1e-6,
             "gate_params_matched":
                 abs(counts["S0"] - counts["S3"]) <= 0.01 * counts["S3"]
                 and counts["S3"] == counts["SALT50"] == counts["S6"]}
        failed = [k for k, v in g.items() if not v]
        status = "P0_SMOKE_OK" if not failed else \
            "PATH_B_COMPOSITIONAL_EXECUTOR_FAILED"
        raw = {"pilot": "PATH-B-A1 P0", "non_claim_bearing": True,
               "is_real_model": is_real, "layer_frozen": L_FROZEN,
               "memorization": {"accuracy": mem_acc,
                                "gold_path": gold_ev,
                                "shuffled_path": shuf_ev,
                                "rewired": rew_ev,
                                "bridge_top1_mem":
                                    r_mem["final"]["bridge_top1"]},
               "arms_100u": {a: {"val_accuracy":
                                 runs[a]["final"]["val_accuracy"],
                                 "bridge_top1":
                                 runs[a]["final"]["bridge_top1"],
                                 "profile_sensitivity":
                                 runs[a]["profile_sensitivity"],
                                 "params": counts[a]} for a in ARMS},
               "p0_gates": g, "failed_gates": failed,
               "development_status": status,
               "total_wall_clock_seconds": round(time.time() - t0, 1)}
        (out / "PATHB_A1_P0_RESULTS.json").write_text(
            json.dumps(raw, indent=2) + "\n", encoding="utf-8")
        print(f"\nA1 P0 STATUS: {status} failed={failed}")
        return 0

    # ---- P1 ----
    runs = []
    for arm in ARMS:
        for seed in SEEDS:
            tb = pack(train_recs, acts, loc, arm,
                      seeded_order(len(train_recs), seed))
            mdl, r = train_model(arm, seed, widen[arm], tb, vb_by_arm[arm],
                                 1000, device)
            if arm != "S0":
                perm = [2, 3, 0, 1]
                r["profile_sensitivity"] = {
                    "true": eval_variant(mdl, vb_by_arm[arm], device),
                    "permuted": eval_variant(mdl, vb_by_arm[arm], device,
                                             pmap=lambda p: p[:, :, perm]),
                    "uniform": eval_variant(
                        mdl, vb_by_arm[arm], device,
                        pmap=lambda p: torch.full_like(p, 0.25))}
            else:
                r["profile_sensitivity"] = None
            runs.append(r)
            print(f"[P1] {arm:7} s{seed} "
                  f"acc={r['final']['val_accuracy']:.4f} "
                  f"bridge={r['final']['bridge_top1']:.3f}")
    by = {}
    for a in ARMS:
        accs = [r["final"]["val_accuracy"] for r in runs if r["arm"] == a]
        mean = sum(accs) / len(accs)
        sd = math.sqrt(sum((x - mean) ** 2 for x in accs) / len(accs))
        per_fam = {}
        for q in FAMS:
            vals = []
            for r in runs:
                if r["arm"] != a:
                    continue
                d = r["final"]["per_question_type"].get(q)
                if d:
                    vals.append(d["accuracy"])
            per_fam[q] = round(sum(vals) / len(vals), 4)
        sens = [r["profile_sensitivity"] for r in runs
                if r["arm"] == a and r["profile_sensitivity"]]
        by[a] = {"mean": round(mean, 6), "std": round(sd, 6),
                 "by_seed": {r["seed"]:
                             round(r["final"]["val_accuracy"], 6)
                             for r in runs if r["arm"] == a},
                 "bridge_top1_mean": round(sum(
                     r["final"]["bridge_top1"] for r in runs
                     if r["arm"] == a) / len(accs), 4),
                 "per_family": per_fam,
                 "profile_sensitivity_mean": (None if not sens else {
                     k: round(sum(x[k]["accuracy"] for x in sens)
                              / len(sens), 4)
                     for k in ("true", "permuted", "uniform")})}
    comp = {"S3_minus_S0": round(by["S3"]["mean"] - by["S0"]["mean"], 6),
            "S3_minus_S6": round(by["S3"]["mean"] - by["S6"]["mean"], 6),
            "S3_minus_SALT50": round(by["S3"]["mean"]
                                     - by["SALT50"]["mean"], 6)}
    ordering_all = by["S3"]["mean"] > by["SALT50"]["mean"] > by["S6"]["mean"]
    fam_order = sum(1 for q in FAMS
                    if by["S3"]["per_family"][q]
                    > by["SALT50"]["per_family"][q]
                    > by["S6"]["per_family"][q])
    s3s = by["S3"]["profile_sensitivity_mean"]
    corrupt_ok = bool(s3s and s3s["true"] > s3s["permuted"]
                      and s3s["true"] > s3s["uniform"])
    floor_ok = by["S3"]["mean"] >= unif_all + 0.15
    # advantage must survive removing S3's best family
    best_fam = max(FAMS, key=lambda q: by["S3"]["per_family"][q]
                   - by["S6"]["per_family"][q])
    rest = [q for q in FAMS if q != best_fam]
    survives = all(sum(by[a]["per_family"][q] for q in rest) / len(rest)
                   < sum(by["S3"]["per_family"][q] for q in rest) / len(rest)
                   for a in ("S6",))
    win = (comp["S3_minus_S0"] >= 0.02 and comp["S3_minus_S6"] >= 0.02
           and comp["S3_minus_SALT50"] >= 0.01 and ordering_all
           and fam_order >= 2 and comp["S3_minus_S0"] > BKEY_INCREMENT
           and corrupt_ok and floor_ok and survives)
    status = "PROMISING_PATH_B_OPERATION_SIGNAL" if win \
        else "NO_PATH_B_OPERATION_SIGNAL"
    raw = {"pilot": "PATH-B-A1 P1", "non_claim_bearing": True,
           "is_real_model": is_real, "layer_frozen": L_FROZEN,
           "arms": by, "comparison": comp,
           "dose_ordering_overall": ordering_all,
           "dose_ordering_families": fam_order,
           "corruption_reduction": corrupt_ok,
           "competence_floor": floor_ok,
           "survives_best_family_removal": survives,
           "candidate_uniform": {"overall": round(unif_all, 4),
                                 **{q: round(u, 4)
                                    for q, u in unif.items()}},
           "bkey_increment_registered": BKEY_INCREMENT,
           "runs": runs,
           "development_status": status,
           "total_wall_clock_seconds": round(time.time() - t0, 1)}
    (out / "PATHB_A1_P1_RESULTS.json").write_text(
        json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    print(f"\nA1 P1 STATUS: {status}")
    print(f"  comp={comp} ordering={ordering_all} fams={fam_order}/3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
