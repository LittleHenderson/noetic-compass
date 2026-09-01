"""run_tier_c_c1.py -- TIER C C1: the transform tournament (owner-authorized,
hard cap $0.80, one GPU instance). DEVELOPMENT-ONLY, NON-CLAIM-BEARING.
Train + C1_TRANSFORM_SELECT half of val ONLY; the C2_STRUCTURE_EVAL half is
never extracted, never evaluated (owner C1 laws 3/4). Both protected splits
untouched. Frozen layer 6.

C1's job (owner ladder): find which neural transform can USE the relation
algebra R. It does NOT establish CAS content vs serious alternatives -- that
is C2, which does not auto-launch. "Specific" language is PROHIBITED here.

ARMS. T0 (no relational structure; the owner's literal arm) + T1..T4, each
with R-CAS, x 3 seeds = 15 runs. T0 is ONE shared baseline: with an all-zero
table every transform's structure term is exactly 0, its structure gradients
are exactly 0, and the shared modules are constructed first from the same
seed, so the four "NULL siblings" are bit-identical models (verified: max
|logp difference| = 0.000e+00 after 25 AdamW steps). Running one T0 per seed
is therefore exact, not an approximation, and it restores the owner's literal
T0 arm. Every arm keeps the exact one-hot operation-label channel, so C1
isolates what the TABLE adds BEYOND labels.

STRUCTURE CHANNEL (hop-2 composition scoring; T4 also refines hop 1):
  T1  additive: s2_j += nu * sum_i a1_i * <w_phi, phi(cls_i, cls_j)>
  T2  op-conditioned matrix: msg_j = sum_i a1_i M[i,j] A[rt(i,j)] k1_i;
      s2_j += nu * <wq2(q1), msg_j>/sqrt(dA)
  T3  bilinear: s2_j += nu * sum_i a1_i M[i,j] (q2^T B[jt(i,j)] k2_j)/sqrt(dA)
  T4  recurrent: a1' = softmax(s1 + nu_a * sum_k a1_k <w_phi1, phi(k,i)>);
      s2_j += nu_b * sum_i a1'_i <w_phi2, phi(i,j)>
Structure parameters are content-indexed (phi channels / result types / J
types), never class-indexed. NO output scaling is applied: a pre-launch
review proved a frozen per-transform scalar (an earlier design) converts a
~50-step init transient -- which AdamW's per-parameter normalization erases
on its own -- into a ~30x between-transform imbalance that persists for the
whole run and would decide the tournament. Instead the structure-term
magnitude and its ratio to the base attention score are LOGGED at every
checkpoint for every arm and REPORTED per arm (flagged above
SCALE_CONFOUND_CAP). The ratio does NOT gate qualification: the owner's
nine C1 laws contain no loudness criterion, an invented cap could
disqualify the true winner (T4 carries two structure terms and starts
above 1.0 by architecture), and the cost of admitting a "loud" socket is
low because C2 freezes the winning transform and swaps rulebooks THROUGH
it, holding channel loudness constant across every C2 arm.

C1 P0 gates: dataset digests match the frozen manifest; C1/C2 split matches
its frozen manifest sha; R_CAS/R_RANDOM match their committed digests; cache
binding verified fail-closed with raw counts persisted; total AND
structure-channel parameter counts reported; EVERY structure parameter of
every Tx receives a nonzero gradient at step 50; T0's structure term is
exactly 0; table swap moves logits.

C1 selection law (frozen, prereg SS6, strengthened only toward owner law 6):
Tx QUALIFIES iff margin over T0 >= 0.02 overall AND >= 0.02 on >= 2/3
primary families AND eval-time R-removal fall >= 0.02 AND max corrupt-table
fall >= 0.02. Winner = qualifying Tx with max overall margin; ties ->
simpler transform (T1<T2<T3<T4). Statuses: TRANSFORM_SELECTED:<Tx> |
NO_TRANSFORM_CONSUMES_STRUCTURE.

SATURATION DISCLOSURE (registered before the run): QB_COMP scored 1.000 for
every arm in the predecessor A1 result, and a family at ceiling cannot
exhibit a 0.02 margin for ANY arm. The frozen ">= 2 of 3 families" law is
applied UNCHANGED -- never weakened -- so in practice it requires QB_REL and
QB_INT to BOTH move. The report carries per-family saturation flags and a
REPORT-ONLY families_at_margin_excluding_saturated field so that a
NO_TRANSFORM_CONSUMES_STRUCTURE outcome caused by saturation is
interpretable rather than silent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "cjt_gate1a_static_neural_v1"
sys.path.insert(0, str(PKG))
sys.path.insert(0, str(HERE))

from exec.activation_extraction import MODEL_ID, extract_split  # noqa: E402
from pathb_core import CLASSES  # noqa: E402
from pathb_a0_probe import extract_clause_local, gold_path  # noqa: E402
import tier_c_structure as ts  # noqa: E402
import tier_c_cache_binding as cbind  # noqa: E402
from tier_c_c1_split import c1_side  # noqa: E402


def seeded_order(n, seed):
    import torch
    return torch.randperm(n, generator=torch.Generator()
                          .manual_seed(seed)).tolist()


def lr_lambda(updates):
    warm = max(1, int(updates * 0.05))

    def f(step):
        if step < warm:
            return (step + 1) / warm
        t = (step - warm) / max(1, updates - warm)
        return 0.5 * (1.0 + math.cos(math.pi * min(1.0, t)))
    return f


L_FROZEN = 6
FAMS = ("QB_REL", "QB_COMP", "QB_INT")
SEEDS = [11, 23, 47]
CHECKPOINTS = [0, 50, 100, 250, 500, 750, 1000]
GRAD_STEPS = (50, 250, 1000)
BATCH = 32
LR, BETAS, WD, CLIP = 1.0e-3, (0.9, 0.999), 0.01, 1.0
D, D_ATT, HDIM = 896, 64, 256
EPS_P = 1e-9
KINDS = ("T1", "T2", "T3", "T4")
T0 = "T0"
MARGIN = 0.02
SCALE_CONFOUND_CAP = 1.0          # |s_str| / |s_base| ceiling for eligibility
SATURATION_CEILING = 0.995        # a family at/above this cannot show margin
ABLATION_PERM = [2, 3, 0, 1]
RATE_PER_HOUR = 0.526             # g4dn.xlarge us-west-2 (cost estimate only)


def load_records(split):
    p = HERE / "data" / f"{split}.jsonl"
    recs = [json.loads(l) for l in p.read_text("utf-8").splitlines() if l]
    return [r for r in recs if r["question_type"] in FAMS]


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def struct_pack(struct_or_null):
    """Frozen structure tensors. None -> the all-zero table (T0)."""
    import torch
    if struct_or_null is None:
        return {"phi": torch.zeros(4, 4, 20), "m": torch.zeros(4, 4),
                "rt": torch.zeros(4, 4, dtype=torch.long),
                "jt": torch.zeros(4, 4, dtype=torch.long)}
    s = struct_or_null
    C = ts.CLASSES
    return {"phi": torch.tensor([[ts.phi(s, a, b) for b in C] for a in C],
                                dtype=torch.float32),
            "m": torch.tensor([[float(ts.m_of(s, a, b)) for b in C]
                               for a in C]),
            "rt": torch.tensor(
                [[ts.RESULT_TYPES.index(ts.cell(s, a, b)["result_type"])
                  for b in C] for a in C], dtype=torch.long),
            "jt": torch.tensor(
                [[ts.J_PAIR_TYPES.index(s["J"]["pair"][f"{a}|{b}"])
                  for b in C] for a in C], dtype=torch.long)}


def profiles_for(rec):
    out = []
    for c in rec["idea_labels"]:
        v = [0.0] * 4
        v[CLASSES.index(c)] = 1.0
        out.append(v)
    return out


def pack(records, acts, loc, order):
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
        p = torch.zeros(b, N, 4)
        cls = torch.zeros(b, N, dtype=torch.long)
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
            p[j, :n] = torch.tensor(profiles_for(rec), dtype=torch.float32)
            cls[j, :n] = torch.tensor(
                [CLASSES.index(c) for c in rec["idea_labels"]],
                dtype=torch.long)
            ans[j] = rec["candidates"].index(rec["answer"])
            qt.append(rec["question_type"])
            s_, br_, f_ = gold_path(rec)
            sel_g.append(s_)
            fin_g.append(f_)
            br_g.append(rec["candidates"].index(br_))
        out.append({"h": h, "g": g, "p": p, "cls": cls, "e": e, "m": m,
                    "cmask": cmask, "imask": imask, "r0": r0, "ans": ans,
                    "qt": qt, "sel": sel_g, "fin": fin_g, "bridge": br_g})
    return out


def build_executor(kind):
    """kind in {T0, T1..T4}. T0 allocates NO structure parameters (the
    owner's literal 'no relational structure' arm)."""
    import torch
    import torch.nn as nn

    class C1Executor(nn.Module):
        def __init__(self, kind):
            super().__init__()
            self.kind = kind
            self.wq1 = nn.Linear(D, D_ATT)
            self.wk1 = nn.Linear(D, D_ATT)
            self.wq2 = nn.Linear(D, D_ATT)
            self.wk2 = nn.Linear(D, D_ATT)
            self.wr1 = nn.Linear(D, 4)
            self.wr2 = nn.Linear(D, 4)
            self.lam1 = nn.Parameter(torch.ones(1))
            self.lam2 = nn.Parameter(torch.ones(1))
            self.mu1 = nn.Parameter(torch.ones(1))
            self.mu2 = nn.Parameter(torch.ones(1))
            self.mlp1 = nn.Sequential(nn.Linear(3 * D, HDIM), nn.GELU(),
                                      nn.Linear(HDIM, HDIM), nn.GELU(),
                                      nn.Linear(HDIM, 1))
            self.mlp2 = nn.Sequential(nn.Linear(4 * D, HDIM), nn.GELU(),
                                      nn.Linear(HDIM, HDIM), nn.GELU(),
                                      nn.Linear(HDIM, 1))
            self.wu = nn.Linear(2 * D, D)
            # structure params: content-indexed only; nu init 1.0, NO
            # frozen output scaling (see module docstring).
            if kind == "T1":
                self.w_phi = nn.Parameter(torch.randn(ts.PHI_DIM) * 0.1)
                self.nu = nn.Parameter(torch.ones(1))
            elif kind == "T2":
                self.A = nn.Parameter(
                    torch.randn(len(ts.RESULT_TYPES), D_ATT, D_ATT) * 0.05)
                self.nu = nn.Parameter(torch.ones(1))
            elif kind == "T3":
                self.B = nn.Parameter(
                    torch.randn(len(ts.J_PAIR_TYPES), D_ATT, D_ATT) * 0.05)
                self.nu = nn.Parameter(torch.ones(1))
            elif kind == "T4":
                self.w_phi1 = nn.Parameter(torch.randn(ts.PHI_DIM) * 0.1)
                self.w_phi2 = nn.Parameter(torch.randn(ts.PHI_DIM) * 0.1)
                self.nu_a = nn.Parameter(torch.ones(1))
                self.nu_b = nn.Parameter(torch.ones(1))

        def structure_params(self):
            names = {"T0": [], "T1": ["w_phi", "nu"], "T2": ["A", "nu"],
                     "T3": ["B", "nu"],
                     "T4": ["w_phi1", "w_phi2", "nu_a", "nu_b"]}[self.kind]
            return {n: getattr(self, n) for n in names}

        def structure_param_count(self):
            return sum(p.numel() for p in self.structure_params().values())

        def set_struct(self, st, device):
            self.st = {k: v.to(device) for k, v in st.items()}

        def _pair(self, tab, cls):                 # (B,N,N): [b,i,j]
            return tab[cls.unsqueeze(2), cls.unsqueeze(1)]

        def forward(self, bt, device, return_diag=False):
            import torch
            h = bt["h"].to(device)
            g = bt["g"].to(device)
            e = bt["e"].to(device)
            m = bt["m"].to(device)
            cmask = bt["cmask"].to(device)
            imask = bt["imask"].to(device)
            r0 = bt["r0"].to(device)
            p = bt["p"].to(device)
            cls = bt["cls"].to(device)
            B, N, C, _ = e.shape
            neg = torch.finfo(h.dtype).min
            ebar = (e * m.unsqueeze(-1)).sum(1) / \
                m.sum(1).clamp(min=1).unsqueeze(-1)
            # pair lookups: [b,i,j] = table[cls_i, cls_j]; i = SOURCE clause
            # (weighted by hop-1 attention), j = TARGET clause being scored.
            phi_p = self.st["phi"][cls.unsqueeze(2), cls.unsqueeze(1)]
            m_p = self._pair(self.st["m"], cls)
            rt_p = self._pair(self.st["rt"], cls)
            jt_p = self._pair(self.st["jt"], cls)

            def hop(q, r_in, wq, wk, wr, lam, mu, mlp, extra, s_extra=None):
                s_base = (wq(q).unsqueeze(1) * wk(h)).sum(-1) / \
                    (D_ATT ** 0.5)
                s = s_base + lam * (wr(q).unsqueeze(1) * p).sum(-1)
                s = s + mu * (r_in.unsqueeze(1) * m.to(s.dtype)).sum(-1)
                if s_extra is not None:
                    s = s + s_extra
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
                return s_base, alpha, P

            sb1, a1, P1 = hop(g, r0, self.wq1, self.wk1, self.wr1,
                              self.lam1, self.mu1, self.mlp1, [])
            str1 = None
            if self.kind == "T4":                  # hop-1 recurrent refine
                pair1 = torch.einsum("f,bijf->bij", self.w_phi1, phi_p)
                str1 = self.nu_a * torch.einsum("bi,bij->bj", a1, pair1)
                s1r = (sb1 + str1).masked_fill(~imask, neg)
                a1 = torch.softmax(s1r, dim=1)
            r1 = (a1.unsqueeze(-1) * P1).sum(1)
            r1 = r1.masked_fill(~cmask, 0.0)
            b1 = (r1.unsqueeze(-1) * ebar).sum(1)
            q1 = torch.nn.functional.gelu(
                self.wu(torch.cat([g, b1], dim=-1)))
            if self.kind == "T0":
                s_str = torch.zeros_like(sb1)
            elif self.kind == "T1":
                pair = torch.einsum("f,bijf->bij", self.w_phi, phi_p)
                s_str = self.nu * torch.einsum("bi,bij->bj", a1, pair)
            elif self.kind == "T2":
                k1 = self.wk1(h)
                Ak = torch.einsum("tde,bie->bitd", self.A, k1)
                rt1h = torch.nn.functional.one_hot(
                    rt_p, len(ts.RESULT_TYPES)).to(Ak.dtype)
                sel = torch.einsum("bitd,bijt->bijd", Ak, rt1h)
                msg = torch.einsum("bi,bij,bijd->bjd", a1, m_p, sel)
                s_str = self.nu * torch.einsum(
                    "bd,bjd->bj", self.wq2(q1), msg) / (D_ATT ** 0.5)
            elif self.kind == "T3":
                qB = torch.einsum("bd,tde->bte", self.wq2(q1), self.B)
                val = torch.einsum("bte,bje->bjt", qB, self.wk2(h))
                jt1h = torch.nn.functional.one_hot(
                    jt_p, len(ts.J_PAIR_TYPES)).to(val.dtype)
                contrib = torch.einsum("bjt,bijt->bij", val, jt1h)
                s_str = self.nu * torch.einsum(
                    "bi,bij,bij->bj", a1, m_p, contrib) / (D_ATT ** 0.5)
            else:                                  # T4 hop-2 additive
                pair2 = torch.einsum("f,bijf->bij", self.w_phi2, phi_p)
                s_str = self.nu_b * torch.einsum("bi,bij->bj", a1, pair2)
            sb2, a2, P2 = hop(q1, r1, self.wq2, self.wk2, self.wr2,
                              self.lam2, self.mu2, self.mlp2,
                              [b1.unsqueeze(1).unsqueeze(1)
                               .expand(B, N, C, D)], s_extra=s_str)
            r2 = (a2.unsqueeze(-1) * P2).sum(1)
            r2 = r2.masked_fill(~cmask, 0.0)
            logp = (r2 + EPS_P).log().masked_fill(~cmask, neg)
            if return_diag:
                live = imask.to(logp.dtype)
                # T4's structure influence spans BOTH hops: report the sum.
                tot = s_str.detach().abs()
                if str1 is not None:
                    tot = tot + str1.detach().abs()
                sd = float((tot * live).sum() / live.sum())
                bd = float(((sb1.detach().abs() + sb2.detach().abs())
                            * live).sum() / live.sum())
                return logp, {"r1": r1, "a1": a1,
                              "s_str_abs_mean": sd,
                              "s_base_abs_mean": bd,
                              "str_to_base_ratio": sd / bd if bd > 0 else 0.0}
            return logp

    return C1Executor(kind)


def param_count(mdl):
    return sum(p.numel() for p in mdl.parameters() if p.requires_grad)


def train_model(kind, st, seed, tb, vb, updates, device):
    import torch
    torch.manual_seed(seed)
    if device.startswith("cuda"):
        torch.cuda.manual_seed_all(seed)
    mdl = build_executor(kind).float().to(device)
    mdl.set_struct(st, device)
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
        sd, bd, rt = [], [], []
        with torch.no_grad():
            for bt in batches:
                logp, diag = mdl(bt, device, return_diag=True)
                tgt = bt["ans"].to(device)
                ls += float(torch.nn.functional.nll_loss(
                    logp, tgt, reduction="sum").item())
                ok = logp.argmax(1) == tgt
                cor += int(ok.sum()); tot += len(tgt)
                br = diag["r1"].argmax(1)
                sd.append(diag["s_str_abs_mean"])
                bd.append(diag["s_base_abs_mean"])
                rt.append(diag["str_to_base_ratio"])
                for j, q in enumerate(bt["qt"]):
                    a, c = per.get(q, (0, 0))
                    per[q] = (a + int(ok[j].item()), c + 1)
                    br_cor += int(int(br[j]) == bt["bridge"][j])
        mdl.train()
        return {"val_accuracy": cor / tot, "val_loss": ls / tot,
                "bridge_top1": br_cor / tot,
                "struct_term_abs_mean": sum(sd) / len(sd),
                "base_term_abs_mean": sum(bd) / len(bd),
                "struct_to_base_ratio": sum(rt) / len(rt),
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
        if (step + 1) in GRAD_STEPS:
            entry = {"step": step + 1}
            for n, prm in mdl.structure_params().items():
                entry[f"{n}_grad_norm"] = \
                    float(prm.grad.norm()) if prm.grad is not None else 0.0
            glog.append(entry)
        torch.nn.utils.clip_grad_norm_(mdl.parameters(), CLIP)
        opt.step(); sched.step()
        last = float(loss.item())
        if not math.isfinite(last):
            raise RuntimeError(f"NONFINITE_LOSS {kind} s{seed} step {step}")
        if (step + 1) in cps and updates >= 1000:
            curve.append({"step": step + 1, "train_loss": last,
                          **evaluate(vb)})
    final = curve[-1] if curve else evaluate(vb)
    return mdl, {"kind": kind, "seed": seed,
                 "trainable_params": param_count(mdl),
                 "structure_params": mdl.structure_param_count(),
                 "final": final, "curve": curve,
                 "struct_grad_log": glog}


def eval_with_struct(mdl, st_swap, batches, device):
    """Accuracy under a swapped frozen table (eval-time ablation)."""
    import torch
    old = mdl.st
    mdl.eval()
    cor = tot = 0
    dsum = dn = 0.0
    with torch.no_grad():
        for bt in batches:
            mdl.st = old
            lt = mdl(bt, device)
            mdl.set_struct(st_swap, device)
            lv = mdl(bt, device)
            mdl.st = old
            msk = bt["cmask"].to(device)
            dsum += float((lv - lt).abs()[msk].sum()); dn += float(msk.sum())
            tgt = bt["ans"].to(device)
            cor += int((lv.argmax(1) == tgt).sum()); tot += len(tgt)
    mdl.st = old
    mdl.train()
    return {"accuracy": round(cor / tot, 6),
            "mean_abs_logit_delta": round(dsum / max(dn, 1), 6)}


def model_identity_digests(tok, model):
    cfg = json.dumps(model.config.to_dict(), sort_keys=True, default=str)
    model_sha = hashlib.sha256((MODEL_ID + "|" + cfg).encode()).hexdigest()
    vocab = sorted(tok.get_vocab().items())
    tok_sha = hashlib.sha256(
        (tok.__class__.__name__ + "|" + str(tok.vocab_size) + "|"
         + str(vocab[:200])).encode()).hexdigest()
    code = ((PKG / "exec" / "activation_extraction.py").read_bytes()
            + (HERE / "pathb_a0_probe.py").read_bytes())
    return model_sha, tok_sha, hashlib.sha256(code).hexdigest()


def preflight():
    """Fail-closed integrity checks BEFORE any GPU work (owner laws 1/3/4)."""
    checks = {}
    man = json.loads((HERE / "PATHB_DATASET_MANIFEST.json")
                     .read_text("utf-8"))
    for rel, want in man["files"].items():
        got = sha_file(HERE / rel)
        checks[f"dataset:{rel}"] = {"expected": want, "got": got,
                                    "ok": got == want}
    split_man = json.loads((HERE / "tier_c" / "C1_SPLIT_MANIFEST.json")
                           .read_text("utf-8"))
    val = load_records("val")
    c1_pids = sorted(r["passage_id"] for r in val if c1_side(r["passage_id"]))
    c2_pids = sorted(r["passage_id"] for r in val
                     if not c1_side(r["passage_id"]))
    got_c1 = hashlib.sha256("\n".join(c1_pids).encode()).hexdigest()
    got_c2 = hashlib.sha256("\n".join(c2_pids).encode()).hexdigest()
    checks["split:c1_pids_sha256"] = {
        "expected": split_man["c1_pids_sha256"], "got": got_c1,
        "ok": got_c1 == split_man["c1_pids_sha256"]}
    checks["split:c2_pids_sha256_unopened"] = {
        "expected": split_man["c2_pids_sha256"], "got": got_c2,
        "ok": got_c2 == split_man["c2_pids_sha256"],
        "note": "recomputed from pids ONLY -- no C2 record content is read, "
                "extracted, or evaluated anywhere in this harness"}
    receipt = json.loads((HERE / "tier_c" / "TIER_C_C0_RECEIPT.json")
                         .read_text("utf-8"))
    for name in ("R_CAS.json", "R_RANDOM.json"):
        want = receipt["artifact_sha256"][name]
        got = sha_file(HERE / "tier_c" / name)
        checks[f"structure:{name}"] = {"expected": want, "got": got,
                                       "ok": got == want}
    failed = [k for k, v in checks.items() if not v["ok"]]
    return checks, failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out-dir", default=str(HERE / "results_tier_c_c1"))
    args = ap.parse_args()
    import torch
    # GPU-first law: fail closed in BOTH directions -- no CPU neural runs.
    if not args.device.startswith("cuda"):
        raise SystemExit("GPU_REQUIRED: --device must be cuda "
                         "(no CPU neural fallback, owner standing law)")
    if not torch.cuda.is_available():
        raise SystemExit("GPU_REQUIRED: no CUDA device present")
    device = args.device
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    def est_cost():
        return round((time.time() - t0) / 3600.0 * RATE_PER_HOUR, 4)

    checks, failed_pre = preflight()
    if failed_pre:
        (out / "TIERC_C1_PREFLIGHT_FAILED.json").write_text(
            json.dumps({"checks": checks, "failed": failed_pre}, indent=2)
            + "\n", encoding="utf-8")
        print(f"PREFLIGHT_FAILED: {failed_pre}")
        return 1
    print(f"[preflight] {len(checks)} integrity checks PASS "
          "(dataset digests, C1/C2 split shas, R_CAS/R_RANDOM digests)")

    r_cas = json.loads((HERE / "tier_c" / "R_CAS.json").read_text("utf-8"))
    r_random = json.loads((HERE / "tier_c" / "R_RANDOM.json")
                          .read_text("utf-8"))
    st_cas = struct_pack(r_cas)
    st_null = struct_pack(None)
    st_perm = struct_pack(ts.permute_structure(r_cas, ABLATION_PERM))
    st_rand = struct_pack(r_random)

    train_recs = load_records("train")
    val_c1 = [r for r in load_records("val") if c1_side(r["passage_id"])]
    print(f"[split] train={len(train_recs)} val_c1={len(val_c1)} "
          "(C2 half never extracted or evaluated)")

    from transformers import AutoTokenizer, AutoModel
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModel.from_pretrained(MODEL_ID, torch_dtype=torch.float16) \
        .to(device).eval()
    is_real = next(model.parameters()).is_cuda
    model_sha, tok_sha, extr_sha = model_identity_digests(tok, model)
    manifest_sha = sha_file(HERE / "PATHB_DATASET_MANIFEST.json")

    cache = out / "cache"; cache.mkdir(exist_ok=True)
    acts, loc = {}, {}
    bind_report = {}
    for name, recs in (("tierc_train", train_recs), ("tierc_valc1", val_c1)):
        f1, f2 = cache / f"{name}_acts.pt", cache / f"{name}_loc.pt"
        fb = cache / f"{name}_binding.json"
        if f1.is_file() and f2.is_file() and fb.is_file():
            binding = json.loads(fb.read_text("utf-8"))
            a = torch.load(f1, map_location="cpu", weights_only=False)
            l = torch.load(f2, map_location="cpu", weights_only=False)
        else:
            te = time.time()
            a = extract_split(recs, tok, model, [L_FROZEN], device)
            l = extract_clause_local(recs, tok, model, device, [L_FROZEN])
            binding = cbind.build_binding(recs, manifest_sha, model_sha,
                                          tok_sha, L_FROZEN, extr_sha)
            torch.save(a, f1); torch.save(l, f2)
            fb.write_text(json.dumps(binding), encoding="utf-8")
            print(f"[extract] {name} {len(recs)} recs "
                  f"{time.time()-te:.0f}s")
        summary = cbind.verify_cache_binding(
            binding, list(a.keys()), recs,
            expected_manifest_sha=manifest_sha, expected_layer=L_FROZEN,
            expected_model_sha=model_sha, expected_tokenizer_sha=tok_sha,
            expected_extraction_code_sha=extr_sha)
        bind_report[name] = {"verified_records": summary["verified_records"],
                             "expected_records": len(recs),
                             "pass": summary["pass"]}
        acts.update(a); loc.update(l)
        print(f"[cache] {name} binding verified: "
              f"{summary['verified_records']} records")
    assert len(acts) == len(train_recs) + len(val_c1), "PID_COLLISION"
    del model
    torch.cuda.empty_cache()

    ALL = (T0,) + KINDS
    protos = {k: build_executor(k) for k in ALL}
    counts = {k: param_count(protos[k]) for k in ALL}
    str_counts = {k: protos[k].structure_param_count() for k in ALL}
    cmax = max(counts.values())
    params_ok = all(abs(v - cmax) <= 0.01 * cmax for v in counts.values())
    print(f"[capacity] total={counts} matched_1pct={params_ok}")
    print(f"[capacity] structure-channel params={str_counts} "
          "(DISCLOSED: transforms differ by design; total counts are what "
          "the +-1% law matches)")
    del protos

    vb = pack(val_c1, acts, loc, list(range(len(val_c1))))

    # ---- C1 P0 smoke gates --------------------------------------------------
    smoke = {}
    tb_p0 = pack(train_recs, acts, loc, seeded_order(len(train_recs), 11))
    for kind in KINDS:
        mdl, r = train_model(kind, st_cas, 11, tb_p0, vb, 100, device)
        g50 = r["struct_grad_log"][0] if r["struct_grad_log"] else {}
        norms = {k2: v for k2, v in g50.items() if k2.endswith("_grad_norm")}
        grads_ok = bool(norms) and all(v > 1e-9 for v in norms.values())
        swap = eval_with_struct(mdl, st_null, vb, device)
        smoke[kind] = {"struct_grads_step50": norms,
                       "all_structure_params_live": grads_ok,
                       "null_swap_logit_delta":
                           swap["mean_abs_logit_delta"],
                       "swap_moves_logits":
                           swap["mean_abs_logit_delta"] > 1e-4,
                       "struct_to_base_ratio_at_100u":
                           round(r["final"]["struct_to_base_ratio"], 6)}
        print(f"[P0] {kind} all_grads_live={grads_ok} "
              f"swapD={swap['mean_abs_logit_delta']} "
              f"ratio={r['final']['struct_to_base_ratio']:.4f}")
        del mdl
        torch.cuda.empty_cache()
    mdl0, r0_ = train_model(T0, st_null, 11, tb_p0, vb, 0, device)
    t0_term = r0_["final"]["struct_term_abs_mean"]
    del mdl0, tb_p0
    torch.cuda.empty_cache()
    p0 = {"pilot": "TIER-C C1 P0", "non_claim_bearing": True,
          "is_real_model": is_real,
          "preflight_checks": checks,
          "cache_binding": bind_report,
          "param_counts_total": counts,
          "param_counts_structure_channel": str_counts,
          "gate_params_matched_1pct": params_ok,
          "t0_structure_term_abs_mean": t0_term,
          "gate_t0_term_zero": t0_term == 0.0,
          "per_kind": smoke}
    p0_fail = ([] if params_ok else ["gate_params_matched_1pct"]) + \
        ([] if t0_term == 0.0 else ["gate_t0_term_zero"]) + \
        [f"{k}:{g}" for k, v in smoke.items()
         for g in ("all_structure_params_live", "swap_moves_logits")
         if not v[g]]
    p0["failed"] = p0_fail
    p0["status"] = "C1_P0_SMOKE_OK" if not p0_fail else "C1_SMOKE_FAILED"
    p0["estimated_cost_usd_so_far"] = est_cost()
    (out / "TIERC_C1_P0_RESULTS.json").write_text(
        json.dumps(p0, indent=2) + "\n", encoding="utf-8")
    if p0_fail:
        print(f"C1 P0 FAILED: {p0_fail} -- no tournament spend")
        return 1

    # ---- P1: the tournament (5 arms x 3 seeds = 15 runs) --------------------
    # Seed is the OUTER loop so exactly ONE 9000-record pack is live at a
    # time (3 packs total instead of 28). Partial results are written after
    # every run so a mid-tournament failure still yields evidence.
    runs = []
    partial = out / "TIERC_C1_PARTIAL_RUNS.json"

    def flush():
        partial.write_text(json.dumps(
            {"completed_runs": len(runs), "runs": runs,
             "estimated_cost_usd_so_far": est_cost()}, indent=2) + "\n",
            encoding="utf-8")

    try:
        for seed in SEEDS:
            tb = pack(train_recs, acts, loc,
                      seeded_order(len(train_recs), seed))
            for kind in ALL:
                st = st_null if kind == T0 else st_cas
                mdl, r = train_model(kind, st, seed, tb, vb, 1000, device)
                if kind != T0:
                    r["ablations"] = {
                        "null_table": eval_with_struct(mdl, st_null, vb,
                                                       device),
                        "permuted_table": eval_with_struct(mdl, st_perm,
                                                           vb, device),
                        "r_random_table": eval_with_struct(mdl, st_rand,
                                                           vb, device)}
                runs.append(r)
                flush()
                print(f"[P1] {kind:3} s{seed} "
                      f"acc={r['final']['val_accuracy']:.4f} "
                      f"ratio={r['final']['struct_to_base_ratio']:.4f}")
                del mdl
                torch.cuda.empty_cache()
            del tb
    except Exception as exc:                       # evidence survives
        flush()
        (out / "TIERC_C1_ABORTED.json").write_text(json.dumps(
            {"error": repr(exc), "traceback": traceback.format_exc(),
             "completed_runs": len(runs),
             "estimated_cost_usd": est_cost()}, indent=2) + "\n",
            encoding="utf-8")
        print(f"C1 ABORTED after {len(runs)} runs: {exc!r}")
        return 1

    return summarize_and_write(runs, val_c1, by_counts=(counts, str_counts),
                               checks=checks, bind_report=bind_report,
                               is_real=is_real, out=out, t0=t0,
                               est_cost=est_cost, torch=torch)


def summarize_and_write(runs, val_c1, by_counts, checks, bind_report,
                        is_real, out, t0, est_cost, torch):
    """Aggregation + frozen selection law. Separated from main() so it can
    be unit-tested offline against synthetic runs BEFORE any GPU spend --
    this code path otherwise executes for the first time only after the
    whole budget has been consumed."""
    counts, str_counts = by_counts

    def agg(kind):
        rs = [r for r in runs if r["kind"] == kind]
        accs = [r["final"]["val_accuracy"] for r in rs]
        mean = sum(accs) / len(accs)
        sd = math.sqrt(sum((x - mean) ** 2 for x in accs) / len(accs))
        per_fam, per_fam_cor, per_fam_seed = {}, {}, {}
        for q in FAMS:
            vals = [r["final"]["per_question_type"][q]["accuracy"]
                    for r in rs]
            cors = [r["final"]["per_question_type"][q]["correct"]
                    for r in rs]
            per_fam[q] = round(sum(vals) / len(vals), 6)
            per_fam_cor[q] = sum(cors) / len(cors)
            per_fam_seed[q] = {r["seed"]:
                               round(r["final"]["per_question_type"][q]
                                     ["accuracy"], 6) for r in rs}
        sens = [r.get("ablations") for r in rs if r.get("ablations")]
        return {"mean": round(mean, 6), "std": round(sd, 6),
                "by_seed": {r["seed"]: round(r["final"]["val_accuracy"], 6)
                            for r in rs},
                "per_family": per_fam,
                "per_family_mean_correct": per_fam_cor,
                "per_family_by_seed": per_fam_seed,
                "struct_term_abs_mean": round(sum(
                    r["final"]["struct_term_abs_mean"] for r in rs)
                    / len(rs), 6),
                "struct_to_base_ratio": round(sum(
                    r["final"]["struct_to_base_ratio"] for r in rs)
                    / len(rs), 6),
                "bridge_top1_mean": round(sum(
                    r["final"]["bridge_top1"] for r in rs) / len(rs), 4),
                "structure_params": rs[0]["structure_params"],
                "ablations_mean": (None if not sens else {
                    k: round(sum(x[k]["accuracy"] for x in sens)
                             / len(sens), 6)
                    for k in ("null_table", "permuted_table",
                              "r_random_table")})}

    ALL = (T0,) + KINDS
    by = {k: agg(k) for k in ALL}
    base = by[T0]
    saturated = {q: bool(base["per_family"][q] >= SATURATION_CEILING
                         or all(by[k]["per_family"][q] >= SATURATION_CEILING
                                for k in ALL)) for q in FAMS}
    verdicts = {}
    for kind in KINDS:
        cas = by[kind]
        overall = round(cas["mean"] - base["mean"], 6)
        fam_m = {q: round(cas["per_family"][q] - base["per_family"][q], 6)
                 for q in FAMS}
        signed_gain = {q: round(cas["per_family_mean_correct"][q]
                                - base["per_family_mean_correct"][q], 4)
                       for q in FAMS}
        extra_correct = round(sum(signed_gain.values()), 4)
        # SIGNED fractions of the NET gain (sign preserved; a family that
        # LOST answers is reported negative, never collapsed to zero).
        net = sum(signed_gain.values())
        gain_frac = {q: (round(signed_gain[q] / net, 4) if net != 0 else None)
                     for q in FAMS}
        removal = {}
        for q in FAMS:
            rest = [x for x in FAMS if x != q]
            removal[f"without_{q}"] = round(
                sum(cas["per_family"][x] for x in rest) / len(rest)
                - sum(base["per_family"][x] for x in rest) / len(rest), 6)
        per_seed_margin = {s: round(cas["by_seed"][s] - base["by_seed"][s], 6)
                           for s in cas["by_seed"]}
        seeds_positive = sum(1 for v in per_seed_margin.values() if v > 0)
        n_eval = len(val_c1)
        se = round(math.sqrt(max(cas["mean"] * (1 - cas["mean"]), 1e-9)
                             / n_eval) * math.sqrt(2), 6)
        abl = cas["ablations_mean"]
        removal_fall = round(cas["mean"] - abl["null_table"], 6)
        corrupt_falls = {k: round(cas["mean"] - abl[k], 6)
                         for k in ("permuted_table", "r_random_table")}
        max_corrupt_fall = max(corrupt_falls.values())
        ratio = cas["struct_to_base_ratio"]
        high_authority = bool(ratio > SCALE_CONFOUND_CAP)
        fams_ok = sum(1 for q in FAMS if fam_m[q] >= MARGIN)
        fams_ok_unsat = sum(1 for q in FAMS
                            if fam_m[q] >= MARGIN and not saturated[q])
        qualifies = bool(overall >= MARGIN and fams_ok >= 2
                         and removal_fall >= MARGIN
                         and max_corrupt_fall >= MARGIN)
        verdicts[kind] = {
            "margin_overall": overall,
            "margin_overall_approx_se": se,
            "margin_per_family": fam_m,
            "margin_per_seed": per_seed_margin,
            "seeds_with_positive_margin": f"{seeds_positive}/3",
            "families_at_margin": fams_ok,
            "families_at_margin_excluding_saturated": fams_ok_unsat,
            "mean_extra_correct_answers": extra_correct,
            "signed_gain_by_family_answers": signed_gain,
            "signed_gain_fraction_by_family": gain_frac,
            "margin_after_removing_each_family": removal,
            "eval_time_R_removal_fall": removal_fall,
            "eval_time_R_corrupt_falls": corrupt_falls,
            "max_corrupt_fall": max_corrupt_fall,
            "struct_to_base_ratio": ratio,
            "high_structure_authority_flag": high_authority,
            "qualifies": qualifies}
    qual = [k for k in KINDS if verdicts[k]["qualifies"]]
    if qual:
        winner = max(qual, key=lambda k:
                     (verdicts[k]["margin_overall"], -KINDS.index(k)))
        status = f"TRANSFORM_SELECTED:{winner}"
    else:
        winner = None
        status = "NO_TRANSFORM_CONSUMES_STRUCTURE"
    gpu_mem = int(torch.cuda.max_memory_allocated())
    wall = round(time.time() - t0, 1)
    raw = {"pilot": "TIER-C C1 TRANSFORM TOURNAMENT",
           "non_claim_bearing": True, "is_real_model": is_real,
           "layer_frozen": L_FROZEN,
           "scope": "C1 finds which transform can USE R. It does NOT "
                    "establish that CAS relational CONTENT beats learned or "
                    "data-derived alternatives -- that is C2, which does "
                    "not auto-launch. 'CAS-specific' and 'specific' claims "
                    "are PROHIBITED at this stage.",
           "eval_split": f"C1_TRANSFORM_SELECT only ({len(val_c1)} records; "
                         "the C2_STRUCTURE_EVAL half was never extracted, "
                         "evaluated, or inspected)",
           "preflight_checks": checks,
           "cache_binding": bind_report,
           "arms": by, "baseline_arm": T0,
           "family_saturation": saturated,
           "saturation_disclosure":
               "a family at/above the ceiling cannot exhibit a 0.02 margin "
               "for ANY arm; the frozen '>=2 of 3 families' law is applied "
               "UNCHANGED (never weakened), and the "
               "families_at_margin_excluding_saturated field is REPORT-ONLY "
               "so a NO_TRANSFORM outcome caused by saturation is "
               "interpretable rather than silent",
           "verdicts": verdicts,
           "selection_margin": MARGIN,
           "structure_channel_scaling":
               "NONE. A pre-launch review proved a frozen per-transform "
               "output scalar converts a ~50-update init transient (which "
               "AdamW's per-parameter normalization erases unaided) into a "
               "~30x between-transform imbalance persisting for the whole "
               "run. Magnitudes are LOGGED, not equalized.",
           "structure_authority_reporting":
               f"struct_to_base_ratio is REPORTED per arm (flag at "
               f">{SCALE_CONFOUND_CAP}) but does NOT gate qualification. "
               "Rationale, registered: the owner's nine C1 laws contain no "
               "loudness criterion, and an invented cap could disqualify "
               "the true winner (T4 carries two structure terms and starts "
               "above 1.0 by architecture). The cost of admitting a 'loud' "
               "socket is low because C2 freezes the winning transform and "
               "swaps rulebooks THROUGH it, so channel loudness is held "
               "constant across every C2 arm and cannot favour R-CAS.",
           "qualifying": qual, "winner": winner,
           "development_status": status,
           "param_counts_total": counts,
           "param_counts_structure_channel": str_counts,
           "gpu_max_memory_allocated_bytes": gpu_mem,
           "runs": runs,
           "total_wall_clock_seconds": wall,
           "cost": {"method": "compute_wall_estimate (harness lower bound); "
                              "the authoritative spend proxy is the "
                              "watchdog's instance_runtime_estimate in the "
                              "run receipt",
                    "rate_per_hour_usd": RATE_PER_HOUR,
                    "estimated_cost_usd": est_cost()}}
    (out / "TIERC_C1_RESULTS.json").write_text(
        json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    print(f"\nC1 STATUS: {status}")
    for k in KINDS:
        v = verdicts[k]
        print(f"  {k}: overall {v['margin_overall']:+.4f} "
              f"(se~{v['margin_overall_approx_se']:.4f}, seeds+ "
              f"{v['seeds_with_positive_margin']}) fams "
              f"{v['families_at_margin']}/3 removal "
              f"{v['eval_time_R_removal_fall']:+.4f} corrupt "
              f"{v['max_corrupt_fall']:+.4f} ratio "
              f"{v['struct_to_base_ratio']:.3f}"
              f"{' HIGH-AUTH' if v['high_structure_authority_flag'] else ''}")
    print(f"  wall {wall}s  est_cost ${est_cost()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
