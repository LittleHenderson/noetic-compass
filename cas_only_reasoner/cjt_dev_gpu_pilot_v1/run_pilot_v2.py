"""run_pilot_v2.py -- CJT-DEV-P1.2 FIVE-ARM development pilot with the
profile-aware ROUTING architecture (owner ruling section 8). DEVELOPMENT-ONLY,
NON-CLAIM-BEARING. Train/validation only; no protected split; no claim
promotion; no CAS-specific language.

The v1 head showed the profile a dashboard AFTER attention had already chosen
the Ideas. The v2 RoutedHead lets the profile help CHOOSE:

    s_i = (W_q g . W_k h_i)/sqrt(d)  +  lambda * (W_r g . p_i)
    alpha = softmax(s)                     # profile-aware Idea routing
    c = sum_i alpha_i h_i ; q = sum_i alpha_i p_i
    z = MLP([c, W_p q, g]) ; score(e) = (W_o z) . (W_c enc(e))

ONE identical mechanism for every profile arm; only the profile SOURCE differs:

    S3   exact one-hot CAS operation      EXACT_OPERATION_IDENTITY / CONSTRUCTION_GOLD
    S6   uniform [.25 .25 .25 .25]        UNIFORM_CONTROL / EXPERIMENTAL_CONTROL
    S7H  hard WordNet primary-lexname     EXCLUSIVE_LEXICAL_CATEGORY / RESOURCE_DERIVED_CONTROL
    S7D  soft WordNet factor simplex V3   WORDNET_LEXICAL_FACTOR_COMPOSITION / RESOURCE_DERIVED_CONTROL

S0 has no profile branch (no W_r/W_p/lambda) and is capacity-matched by
widening. lambda is initialized at 1.0 (learnable): the P0-failure repair --
a 0 init gated dW_r to zero and the routing branch never trained. Note S6's
uniform profiles make the routing term a softmax-invariant constant, so S6
CANNOT route by design (the correct control behavior); its true dW_r/dlambda
are exactly zero and its logged lambda trajectory is optimizer drift.

--candidates frozen|contextual selects the candidate representation for ALL
arms equally (contextual = mean of the candidate's layer-L* token occurrences,
per Diagnostic E); the choice is made from the P1.1 diagnostic and recorded.

Stages: --stage P0 (all arms, seed 11, 100 updates) then P1 (3 seeds x 1000).
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
from exec.arms import (D_ATT, D_HID, D_MODEL, D_PROF, MAX_IDEAS,  # noqa: E402
                       N_CLASSES)
from exec.dataset_assembly import assemble_examples  # noqa: E402
from exec.baselines import score_split  # noqa: E402
from exec.layer_select import CANDIDATE_LAYERS, select_layer  # noqa: E402
from run_pilot import (lr_lambda, load_records, pack_batches,  # noqa: E402
                       seeded_order)
from exec.spans import build_input_text  # noqa: E402


def contextual_candidates_multilayer(records, tok, model, device, layers):
    """Diagnostic-E repair: per candidate, the mean of its token-occurrence
    hidden states, for EVERY candidate layer in ONE forward pass per passage.
    Returns {pid: {L: (C,896) fp16}}."""
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
            low = text.lower()
            tok_idx_per_cand = []
            for cand in rec["candidates"]:
                spans = [(m.start(), m.end()) for m in
                         re.finditer(rf"\b{re.escape(cand.lower())}\b", low)]
                tok_idx_per_cand.append(
                    [ti for ti, (a, b) in enumerate(offs)
                     if b > a and any(a < e and b > s for s, e in spans)])
            per_layer = {}
            for L in layers:
                h_all = hs[L][0].float()
                vecs = []
                for tix in tok_idx_per_cand:
                    if tix:
                        vecs.append(h_all[torch.tensor(
                            tix, device=h_all.device)].mean(0))
                    else:
                        vecs.append(torch.zeros(D_MODEL,
                                                device=h_all.device))
                per_layer[L] = torch.stack(vecs).half().cpu()
            out[rec["passage_id"]] = per_layer
    return out

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
CAPACITY_TOLERANCE = 0.01


def build_routed_head(use_profiles: bool, widen_w: int = 0):
    import torch
    import torch.nn as nn

    class RoutedHead(nn.Module):
        def __init__(self, use_p, w):
            super().__init__()
            self.use_p = use_p
            self.w_q = nn.Linear(D_MODEL, D_ATT)
            self.w_k = nn.Linear(D_MODEL, D_ATT)
            if use_p:
                self.w_r = nn.Linear(D_MODEL, N_CLASSES)   # routing query
                # P0-failure repair (owner P1.1-closure directive): lambda=0
                # init gated dW_r to zero (ds/dW_r ~ lambda) -- the routing
                # branch received NO gradient in the first five-arm run.
                # lambda now starts at 1.0 so the profile-routing branch is
                # live from step 0; it remains learnable.
                self.lam = nn.Parameter(torch.ones(1))
                self.w_p = nn.Linear(N_CLASSES, D_PROF)
            in_dim = D_MODEL + (D_PROF if use_p else 0) + D_MODEL
            self.mlp = nn.Sequential(nn.Linear(in_dim, D_HID), nn.GELU(),
                                     nn.Linear(D_HID, D_HID))
            self.widen = (nn.Sequential(nn.Linear(D_HID, w), nn.GELU(),
                                        nn.Linear(w, D_HID)) if w > 0 else None)
            self.w_o = nn.Linear(D_HID, D_HID)
            self.w_c = nn.Linear(D_MODEL, D_HID)

        def forward(self, h, g, p, idea_mask, cand_enc, cand_mask,
                    return_alpha=False):
            import torch
            neg = torch.finfo(h.dtype).min
            s = (self.w_q(g).unsqueeze(1) * self.w_k(h)).sum(-1) / (D_ATT ** 0.5)
            if self.use_p:
                s = s + self.lam * (self.w_r(g).unsqueeze(1) * p).sum(-1)
            s = s.masked_fill(~idea_mask, neg)
            alpha = torch.softmax(s, dim=1)
            c = (alpha.unsqueeze(-1) * h).sum(dim=1)
            feats = [c]
            if self.use_p:
                q = (alpha.unsqueeze(-1) * p).sum(dim=1)
                feats.append(self.w_p(q))
            feats.append(g)
            z = self.mlp(torch.cat(feats, dim=-1))
            if self.widen is not None:
                z = self.widen(z)
            u = self.w_o(z)
            logits = (self.w_c(cand_enc) * u.unsqueeze(1)).sum(-1)
            logits = logits.masked_fill(~cand_mask, neg)
            return (logits, alpha) if return_alpha else logits

    return RoutedHead(use_profiles, widen_w)


def param_count(m):
    return sum(p.numel() for p in m.parameters() if p.requires_grad)


def match_s0_capacity(ref: int) -> int:
    for w in range(0, 4096):
        if abs(param_count(build_routed_head(False, w)) - ref) \
                <= CAPACITY_TOLERANCE * ref:
            return w
    raise RuntimeError("CAPACITY_MATCH_FAILURE")


def surface_lookup(clause_text, table):
    hits = [v for v in table
            if re.search(rf"\b{re.escape(v)}\b", clause_text)]
    if len(hits) != 1:
        raise ValueError(f"SURFACE_LOOKUP_FAILURE: {len(hits)} registered "
                         f"verbs in {clause_text!r}")
    return table[hits[0]]


def assemble(records, arm, s7h_v2c, s7d_v2p):
    if arm in ("S0", "S3", "S6"):
        return assemble_examples(records, arm)
    exs = assemble_examples(records, "S0")             # gold-isolated skeleton
    for ex in exs:
        if arm == "S7H":
            profs = []
            for ct in ex["clauses"]:
                v = [0.0] * 4
                v[surface_lookup(ct, s7h_v2c)] = 1.0
                profs.append(v)
        else:                                           # S7D soft simplex
            profs = [[float(x) for x in surface_lookup(ct, s7d_v2p)]
                     for ct in ex["clauses"]]
        ex["profiles"] = profs
    return exs


GRAD_LOG_STEPS = (50, 100, 250, 500, 1000)


def train_arm(arm, seed, widen_w, tb, vb, updates, device, gold_va=None):
    import torch
    torch.manual_seed(seed)
    if device.startswith("cuda"):
        torch.cuda.manual_seed_all(seed)
        torch.cuda.reset_peak_memory_stats()
    head = build_routed_head(arm != "S0", widen_w).float().to(device)
    opt = torch.optim.AdamW(head.parameters(), lr=LR, betas=BETAS,
                            weight_decay=WD)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lr_lambda(updates))
    loss_fn = torch.nn.CrossEntropyLoss()
    curve, cps = [], set(CHECKPOINTS)
    grad_log = []
    t0 = time.time()

    def evaluate():
        head.eval()
        ce = torch.nn.CrossEntropyLoss(reduction="sum")
        tot = cor = 0
        ls = 0.0
        per = {}
        with torch.no_grad():
            for bt in vb:
                logits = head(bt["h"].to(device), bt["g"].to(device),
                              None if bt["p"] is None else bt["p"].to(device),
                              bt["idea_mask"].to(device),
                              bt["cand_enc"].to(device),
                              bt["cand_mask"].to(device))
                tgt = bt["answer_index"].to(device)
                ls += float(ce(logits, tgt).item())
                ok = logits.argmax(1) == tgt
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
    pos, last = 0, None
    for step in range(updates):
        bt = tb[pos]; pos = (pos + 1) % len(tb)
        logits = head(bt["h"].to(device), bt["g"].to(device),
                      None if bt["p"] is None else bt["p"].to(device),
                      bt["idea_mask"].to(device), bt["cand_enc"].to(device),
                      bt["cand_mask"].to(device))
        loss = loss_fn(logits, bt["answer_index"].to(device))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        if (step + 1) in GRAD_LOG_STEPS and arm != "S0":
            grad_log.append({"step": step + 1,
                             "w_r_grad_norm": float(head.w_r.weight.grad.norm()),
                             "w_p_grad_norm": float(head.w_p.weight.grad.norm()),
                             "lam_grad": float(head.lam.grad.item()),
                             "lam_value": float(head.lam.item())})
        torch.nn.utils.clip_grad_norm_(head.parameters(), CLIP)
        opt.step(); sched.step()
        last = float(loss.item())
        if not math.isfinite(last):
            raise RuntimeError(f"NONFINITE_LOSS {arm} seed {seed} step {step}")
        if (step + 1) in cps:
            curve.append({"step": step + 1, "train_loss": last, **evaluate()})

    # ---- post-training instrumentation (owner directive step 7) ----
    def eval_variant(profiles_map=None):
        """val accuracy + mean |delta logits| vs the true-profile logits."""
        head.eval()
        tot = cor = 0
        dsum = dn = 0.0
        with torch.no_grad():
            for bi, bt in enumerate(vb):
                p_true = None if bt["p"] is None else bt["p"].to(device)
                p_use = p_true if profiles_map is None \
                    else profiles_map(bt["p"]).to(device)
                lt = head(bt["h"].to(device), bt["g"].to(device), p_true,
                          bt["idea_mask"].to(device),
                          bt["cand_enc"].to(device), bt["cand_mask"].to(device))
                lv = head(bt["h"].to(device), bt["g"].to(device), p_use,
                          bt["idea_mask"].to(device),
                          bt["cand_enc"].to(device), bt["cand_mask"].to(device))
                m = bt["cand_mask"].to(device)
                dsum += float((lv - lt).abs()[m].sum()); dn += float(m.sum())
                tgt = bt["answer_index"].to(device)
                cor += int((lv.argmax(1) == tgt).sum()); tot += len(tgt)
        head.train()
        return {"accuracy": round(cor / tot, 6),
                "mean_abs_logit_delta_vs_true": round(dsum / max(dn, 1), 6)}

    profile_sensitivity = None
    if arm != "S0":
        perm = [2, 3, 0, 1]
        profile_sensitivity = {
            "true": eval_variant(None),
            "permuted": eval_variant(lambda p: p[:, :, perm]),
            "uniform": eval_variant(
                lambda p: __import__("torch").full_like(p, 0.25)),
            "zeroed": eval_variant(
                lambda p: __import__("torch").zeros_like(p))}

    attention = None
    if gold_va is not None:
        import torch as _t
        ent_l, hit_l, mass_l = [], [], []
        k = 0
        head.eval()
        with _t.no_grad():
            for bt in vb:
                _, alpha = head(bt["h"].to(device), bt["g"].to(device),
                                None if bt["p"] is None else bt["p"].to(device),
                                bt["idea_mask"].to(device),
                                bt["cand_enc"].to(device),
                                bt["cand_mask"].to(device), return_alpha=True)
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

    # train-subset accuracy (first 32 batches = ~1024 examples)
    head.eval()
    tr_cor = tr_tot = 0
    with torch.no_grad():
        for bt in tb[:32]:
            lt = head(bt["h"].to(device), bt["g"].to(device),
                      None if bt["p"] is None else bt["p"].to(device),
                      bt["idea_mask"].to(device), bt["cand_enc"].to(device),
                      bt["cand_mask"].to(device))
            tgt = bt["answer_index"].to(device)
            tr_cor += int((lt.argmax(1) == tgt).sum()); tr_tot += len(tgt)
    head.train()

    lam = (float(head.lam.item()) if arm != "S0" else None)
    return {"arm": arm, "seed": seed, "widen_w": widen_w,
            "trainable_params": param_count(head),
            "learned_lambda": lam, "curve": curve, "final": curve[-1],
            "train_subset_accuracy": round(tr_cor / tr_tot, 6),
            "profile_grad_log": grad_log or None,
            "profile_sensitivity": profile_sensitivity,
            "attention": attention,
            "wall_clock_seconds": round(time.time() - t0, 2),
            "peak_gpu_mem_mb": round(
                (__import__("torch").cuda.max_memory_allocated() / 1e6)
                if device.startswith("cuda") else 0.0, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["P0", "P1"])
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out-dir", default=str(HERE / "results_v2"))
    ap.add_argument("--updates", type=int, default=None)
    ap.add_argument("--candidates", default="frozen",
                    choices=["frozen", "contextual"],
                    help="candidate representation for ALL arms (choice made "
                         "from Diagnostic E, recorded in outputs)")
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

    s7h = json.loads((HERE / "S7_H_WN1.json").read_text("utf-8"))
    s7d = json.loads((HERE / "S7_DELTA_WN1_V3.json").read_text("utf-8"))
    s7h_v2c, s7d_v2p = s7h["verb_to_class"], s7d["verb_to_profile"]
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
    caches, ctx = {}, {}
    for split, recs in (("train", train_recs), ("val", val_recs)):
        cf = cache_dir / f"{split}_acts.pt"
        if cf.is_file():
            caches[split] = torch.load(cf, map_location="cpu",
                                       weights_only=False)
        else:
            caches[split] = extract_split(recs, tok, model,
                                          list(CANDIDATE_LAYERS), device)
            torch.save(caches[split], cf)
        if args.candidates == "contextual":
            xf = cache_dir / f"{split}_ctx.pt"
            if xf.is_file():
                ctx[split] = torch.load(xf, map_location="cpu",
                                        weights_only=False)
            else:
                ctx[split] = contextual_candidates_multilayer(
                    recs, tok, model, device, list(CANDIDATE_LAYERS))
                torch.save(ctx[split], xf)
    del model
    if device.startswith("cuda"):
        torch.cuda.empty_cache()
    for split in ("train", "val"):
        for pid, v in caches[split].items():
            if v["cand"] is None:
                raise RuntimeError(f"CANDIDATE_ENCODING_MISSING {split}/{pid}")

    baselines = {"B0_floor_val": score_split(val_recs, "B0"),
                 "B1_ceiling_val": score_split(val_recs, "B1"),
                 "candidate_uniform_val": {
                     "accuracy": round(sum(1 / len(r["candidates"])
                                           for r in val_recs) / len(val_recs), 5),
                     "cross_entropy": round(sum(math.log(len(r["candidates"]))
                                                for r in val_recs)
                                            / len(val_recs), 5)}}

    def feats(split, layer):
        src = caches[split]
        return {pid: {"h": v["layers"][layer][0], "g": v["layers"][layer][1],
                      "cand": (ctx[split][pid][layer]
                               if args.candidates == "contextual"
                               else v["cand"])}
                for pid, v in src.items()}

    ref = param_count(build_routed_head(True, 0))
    widen = {a: (match_s0_capacity(ref) if a == "S0" else 0) for a in ARMS}
    counts = {a: param_count(build_routed_head(a != "S0", widen[a]))
              for a in ARMS}

    # layer selection: S0 only on val, lowest-index tie-break (frozen protocol)
    layer_val = {}
    for L in CANDIDATE_LAYERS:
        ftr, fva = feats("train", L), feats("val", L)
        ex_tr = assemble(train_recs, "S0", s7h_v2c, s7d_v2p)
        ex_va = assemble(val_recs, "S0", s7h_v2c, s7d_v2p)
        tb = pack_batches(ex_tr, ftr, seeded_order(len(ex_tr), 11))
        vb = pack_batches(ex_va, fva, list(range(len(ex_va))))
        r = train_arm("S0", 11, widen["S0"], tb, vb, updates, device)
        layer_val[L] = r["final"]["val_accuracy"]
        print(f"[layer-select] L={L} S0 val_acc={layer_val[L]:.4f}")
    Lstar = select_layer(layer_val)
    print(f"[layer-select] L*={Lstar}")

    ftr, fva = feats("train", Lstar), feats("val", Lstar)
    seeds = [11] if args.stage == "P0" else SEEDS
    # gold target-clause indices for attention metrics (natural val order;
    # deterministic resolution proven 100% in Diagnostic D). Unresolved rows
    # are counted, not silently mapped (review finding); metrics use index 0
    # for them and the count is recorded in the outputs.
    from run_diagnostics import gold_clause_index
    _gold = [gold_clause_index(r) for r in val_recs]
    gold_unresolved = sum(1 for gi, how in _gold if gi is None)
    gold_va = [(gi if gi is not None else 0) for gi, _ in _gold]
    if gold_unresolved:
        print(f"[gold] WARNING: {gold_unresolved}/{len(_gold)} val gold "
              f"clauses unresolved (attention metrics degrade accordingly)")
    runs = []
    for arm in ARMS:
        ex_tr = assemble(train_recs, arm, s7h_v2c, s7d_v2p)
        ex_va = assemble(val_recs, arm, s7h_v2c, s7d_v2p)
        vb = pack_batches(ex_va, fva, list(range(len(ex_va))))
        for seed in seeds:
            tb = pack_batches(ex_tr, ftr, seeded_order(len(ex_tr), seed))
            r = train_arm(arm, seed, widen[arm], tb, vb, updates, device,
                          gold_va=gold_va)
            r["layer"] = Lstar
            runs.append(r)
            sens = r["profile_sensitivity"]
            print(f"[{args.stage}] {arm:4} seed={seed} "
                  f"acc={r['final']['val_accuracy']:.4f} "
                  f"loss={r['final']['val_loss']:.4f} "
                  f"lam={r['learned_lambda']} "
                  f"trainacc={r['train_subset_accuracy']:.3f} "
                  f"goldhit={r['attention']['gold_top1_rate']:.3f} "
                  f"swapDlogit={(sens['permuted']['mean_abs_logit_delta_vs_true'] if sens else None)} "
                  f"{r['wall_clock_seconds']}s")

    total_wall = time.time() - t_start
    write_outputs(out, args, updates, Lstar, layer_val, counts, baselines,
                  runs, seeds, table_shas, is_real, total_wall, device)
    return 0


def _mean_std(xs):
    m = sum(xs) / len(xs)
    return m, math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def write_outputs(out, args, updates, Lstar, layer_val, counts, baselines,
                  runs, seeds, table_shas, is_real, total_wall, device):
    by_arm = {}
    for a in ARMS:
        rs = [r for r in runs if r["arm"] == a]
        accs = [r["final"]["val_accuracy"] for r in rs]
        losses = [r["final"]["val_loss"] for r in rs]
        m, s = _mean_std(accs)
        sens = [r["profile_sensitivity"] for r in rs if r["profile_sensitivity"]]
        by_arm[a] = {"final_val_accuracy_mean": round(m, 6),
                     "final_val_accuracy_std": round(s, 6),
                     "final_val_accuracy_by_seed": {
                         r["seed"]: round(r["final"]["val_accuracy"], 6)
                         for r in rs},
                     "final_val_loss_mean": round(sum(losses) / len(losses), 6),
                     "learned_lambda_by_seed": [r["learned_lambda"] for r in rs],
                     "train_subset_accuracy_mean": round(
                         sum(r["train_subset_accuracy"] for r in rs) / len(rs), 6),
                     "attention_gold_top1_rate_mean": round(
                         sum(r["attention"]["gold_top1_rate"] for r in rs)
                         / len(rs), 6),
                     "attention_entropy_mean": round(
                         sum(r["attention"]["mean_normalized_entropy"]
                             for r in rs) / len(rs), 6),
                     "profile_sensitivity_mean": (None if not sens else {
                         k: {"accuracy": round(sum(x[k]["accuracy"]
                                                   for x in sens) / len(sens), 6),
                             "mean_abs_logit_delta_vs_true": round(
                                 sum(x[k]["mean_abs_logit_delta_vs_true"]
                                     for x in sens) / len(sens), 6)}
                         for k in ("true", "permuted", "uniform", "zeroed")}),
                     "trainable_params": counts[a], **ARM_TAGS[a]}
    comp = {f"S3_minus_{o}": round(
        by_arm["S3"]["final_val_accuracy_mean"]
        - by_arm[o]["final_val_accuracy_mean"], 6)
        for o in ("S0", "S6", "S7H", "S7D")}

    def p0_gates():
        """Executable P0 pass criteria (owner P1.1-closure directive)."""
        g = {}
        g["losses_finite"] = all(math.isfinite(r["final"]["val_loss"])
                                 for r in runs)
        prof_counts = {counts[a] for a in ARMS if a != "S0"}
        g["profile_arm_params_identical"] = len(prof_counts) == 1
        ref_c = counts["S3"]
        g["s0_capacity_within_1pct"] = abs(counts["S0"] - ref_c) <= 0.01 * ref_c
        # S6's UNIFORM profiles make the routing term a constant shift of every
        # valid attention score; softmax is shift-invariant, so dL/dW_r and
        # dL/dlambda are EXACTLY ZERO for S6 by design of the control (its
        # logged w_r norm is fp32 cancellation noise). S6 is therefore gated on
        # w_p only (which receives real gradient via the pooled-profile MLP
        # path); the routing-gradient check applies to S3/S7H/S7D, whose
        # profiles vary across clauses. (Adversarial pre-launch review finding.)
        grad_ok = True
        for r in runs:
            if r["arm"] == "S0":
                continue
            log = r["profile_grad_log"]
            if not log:                       # vacuous-pass guard: a profile
                grad_ok = False               # arm with NO grad log is a FAIL
                continue
            need_wr = r["arm"] != "S6"
            if not all(e["w_p_grad_norm"] > 1e-9
                       and (not need_wr or e["w_r_grad_norm"] > 1e-9)
                       for e in log):
                grad_ok = False
        g["profile_branch_receives_gradients"] = grad_ok
        s3 = next((r for r in runs if r["arm"] == "S3"), None)
        g["s3_profile_swap_changes_logits"] = bool(
            s3 and s3["profile_sensitivity"]
            and s3["profile_sensitivity"]["permuted"]
                  ["mean_abs_logit_delta_vs_true"] > 1e-4)
        return g

    def status():
        if args.stage == "P0":
            g = p0_gates()
            failed = [k for k, v in g.items() if not v]
            if failed:
                return ("PILOT_PIPELINE_FAILURE",
                        f"P0 gate(s) FAILED: {failed}; gates={g}")
            return ("P0_SMOKE_OK",
                    f"P0 smoke: all five arms trained; gates all pass: {g}")
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
        # owner win-condition 6: S3's benefit must DECLINE when its profiles
        # are shuffled or replaced (proves the content is load-bearing)
        s3s = by_arm["S3"]["profile_sensitivity_mean"]
        content_load_bearing = bool(
            s3s and s3s["true"]["accuracy"] > s3s["permuted"]["accuracy"]
            and s3s["true"]["accuracy"] > s3s["uniform"]["accuracy"])
        if beats and all(sign_ok(o) for o in ("S0", "S6", "S7H", "S7D")) \
                and content_load_bearing:
            return ("PROMISING_DEV_SIGNAL",
                    "S3 beats S0, S6, S7-H and S7-Delta by >=0.02 mean val "
                    "accuracy with >=2/3-seed sign consistency AND its "
                    "accuracy declines under profile shuffle/replacement")
        if beats and all(sign_ok(o) for o in ("S0", "S6", "S7H", "S7D")):
            return ("INCONCLUSIVE_DEV_SIGNAL",
                    "S3 clears all controls but its accuracy does NOT decline "
                    "under profile shuffle/replacement -- the content link is "
                    "not demonstrated")
        if any(comp[f"S3_minus_{o}"] < 0.02
               for o in ("S0", "S6", "S7H", "S7D")):
            return ("NO_DEV_SIGNAL",
                    f"S3 does not clear all four controls by >=0.02: {comp}")
        return ("INCONCLUSIVE_DEV_SIGNAL", "differences conflict across seeds")
    st, reason = status()

    raw = {"pilot": "CJT-DEV-P1.2b", "architecture":
               "RoutedHead (profile-aware Idea routing; lambda init 1.0, "
               "learnable -- the P0-failure repair; S6 cannot route by design: "
               "uniform profiles are a softmax-invariant shift)",
           "stage": args.stage, "non_claim_bearing": True,
           "is_real_model": is_real, "device": device, "model_id": MODEL_ID,
           "candidates_mode": args.candidates,
           "updates": updates, "batch_size": BATCH_SIZE, "seeds": seeds,
           "checkpoints": CHECKPOINTS, "selected_layer": Lstar,
           "layer_selection_val_accuracy": {str(k): round(v, 6)
                                            for k, v in layer_val.items()},
           **table_shas, "baselines": baselines, "arms": by_arm,
           "arm_comparison": comp, "runs": runs,
           "total_wall_clock_seconds": round(total_wall, 1),
           "total_cost_usd": round(total_wall / 3600 * args.cost_per_hour, 4),
           "cost_note": f"{args.device_note}; compute-wall estimate at "
                        f"${args.cost_per_hour:.4f}/hr",
           "development_status": st, "development_status_reason": reason}
    (out / "DEV_PILOT_V2_RAW_RESULTS.json").write_text(
        json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    with (out / "DEV_PILOT_V2_LEARNING_CURVES.csv").open(
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
    (out / "DEV_PILOT_V2_RECEIPT.json").write_text(json.dumps(
        {"receipt_id": "DEV_PILOT_V2_RECEIPT", "stage": args.stage,
         "non_claim_bearing": True, "is_real_model": is_real,
         "raw_results_sha256": hashlib.sha256(
             (out / "DEV_PILOT_V2_RAW_RESULTS.json").read_bytes()).hexdigest(),
         **table_shas, "selected_layer": Lstar, "development_status": st,
         "candidates_mode": args.candidates,
         "total_wall_clock_seconds": round(total_wall, 1)},
        indent=2) + "\n", encoding="utf-8")
    print(f"\nDEVELOPMENT STATUS: {st}\n  {reason}")


if __name__ == "__main__":
    raise SystemExit(main())
