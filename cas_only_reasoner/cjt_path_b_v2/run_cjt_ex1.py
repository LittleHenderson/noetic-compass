"""run_cjt_ex1.py -- CJT-EX1: Expert Specialization and Transfer Pilot.

Owner ruling (2026-09-01): the standalone lookup-table lane is CLOSED; the
next primary experiment asks whether operation-specific CJT experts do
ARCHITECTURAL work -- specialize, transfer and retain better -- than a
matched generic expert bank. J is carried forward not as a table but as a
COMPUTATIONAL CONSTRAINT between related experts.

DEVELOPMENT-ONLY, NON-CLAIM-BEARING. Train (families A,B) + the
C1_TRANSFORM_SELECT half of val (family C) ONLY. The C2_STRUCTURE_EVAL half
stays sealed and both protected splits are untouched. Frozen layer 6.

THE FIVE CONDITIONS. Everything is held identical -- executor, router
inputs, data, seeds, optimizer, schedule, updates, total expert capacity --
and ONLY the expert ORGANIZATION differs:

  E0 SHARED     one expert handles every clause.
  E1 ANON_MOE   4 experts, DENSE soft mixture by a LEARNED router over
                clause content. Retained as the dense-MoE comparator.
  E1S ANON_SPARSE 4 experts, LEARNED content router, TOP-1 straight-through
                -- exactly ONE expert active per clause, no CAS labels in
                the routing. THE KILLER CONTROL (owner ruling): it gives the
                generic architecture the same sparse machinery as E2, so an
                E2 win cannot be explained by sparsity alone.
  E2 CAS_EXPERT 4 experts, hard-routed by the TRUE operation class
                (^2/^3/^6/^8 -> expert 0/1/2/3).
  E3 CAS_STRUCT E2 plus a REGISTERED COMPUTATIONAL CONSTRAINT expressing the
                canonical ^2<->^3 involution ("affinity for / attracted
                toward" vs "adverse to / repelled by"): the aversion expert
                is the attraction expert read with reversed orientation --
                they share a body and their output vectors are tied
                v3 = -v2. J becomes a rule about how two experts TRANSFORM,
                not a table saying they are related.
  E4 SHUFFLED   4 experts, hard-routed by a FROZEN PER-CLAUSE hash. The
                ROUTING carries no operation information; the arm still
                sees the class profile via the attention path. Same
                machinery, same capacity, same hard routing -- only the
                correspondence between operation and expert is destroyed.

  DISCLOSED (C0 review): pack() writes the exact one-hot operation class
  into `p` for EVERY condition, and hop() adds lam*<W_r q, p> to the clause
  attention score in every condition. So no arm is label-blind; the arms
  are EXPERT-ORGANIZATION-blind. That is deliberate -- stripping labels from
  E1/E4 would confound expert organization with label availability, and the
  question is about organization. Stated here so the docstrings cannot be
  read as claiming otherwise.

  ALSO DISCLOSED (C0 review): E1 is a DENSE mixture -- all four experts fire
  on every clause -- while E2/E3/E4 select exactly one. So E2-vs-E1 differs
  in TWO ways at once: routing IDENTITY (CAS class vs learned) and routing
  SPARSITY (one expert vs four). Measured active body parameters per clause:
  E1 1,442,816 vs E2 360,704. The asymmetry favours E1 and therefore makes
  the E2-E1 gate HARDER, never easier -- the safe direction -- but the
  confound is real and is recorded rather than glossed.

  E4 DESIGN NOTE (registered): a fixed BIJECTION class->expert would NOT be
  a control at all -- it is a pure relabeling of expert indices and trains
  to a bit-identical model (the C1 review taught this lesson when the four
  "NULL siblings" turned out to be one model). The scramble is therefore
  per-clause, not per-class, and the bijection-is-identity claim is verified
  in the P0 smoke gates rather than assumed.

THE KILLER COMPARISON is E2 vs E1S (owner ruling): both select exactly ONE
expert per clause with matched parameters, width and active-expert count --
one selects by CAS operation identity, the other by a learned content
router. E1 (dense) then tells us whether sparsity itself helps, and E4 tells
us whether the stable operation-to-expert ASSIGNMENT matters.

TRANSFER is built into the data, not bolted on: train families A,B use verbs
0-5 and forms 0-3; the evaluation family C uses verbs 6-7 and form 4, which
the model never sees in training. Every reported accuracy is therefore
already an unseen-verb, unseen-template number.

RETENTION (sequential learning), AMENDED per owner ruling. Phase 1 =
QB_INT (^2, ^6); phase 2 = QB_COMP (^2, ^6, and ^8 NEWLY INTRODUCED). The
original protocol (QB_REL then QB_COMP) was rejected before spend because
QB_COMP contains ZERO ^3 clauses, so a hard-routed ^3 expert received no
phase-2 gradient and could not forget -- CAS arms were shielded by the
clause template rather than by expert organization.

Precise claim (owner correction, adopted): NOT "every expert is exercised in
both phases" -- ^2 and ^6 are, ^8 is new in phase 2, and ^3 appears in
NEITHER. The accurate statement is: every expert relevant to the RETAINED
phase-1 skill (^2 and ^6) remains EXPOSED to phase-2 learning, while ^8
enters as a new specialist.

A retention advantage additionally requires REAL INTERFERENCE PRESSURE: if
phase 2 produces almost no learning or no parameter movement in the shared
experts, the run emits RETENTION_STRESS_INSUFFICIENT and no retention claim
is made.
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
import tier_c_cache_binding as cbind  # noqa: E402
from tier_c_c1_split import c1_side  # noqa: E402

L_FROZEN = 6
FAMS = ("QB_REL", "QB_COMP", "QB_INT")
SEEDS = [11, 23, 47]
CHECKPOINTS = [0, 50, 100, 250, 500, 750, 1000]
GRAD_STEPS = (50, 250, 1000)
BATCH = 32
LR, BETAS, WD, CLIP = 1.0e-3, (0.9, 0.999), 0.01, 1.0
D, D_ATT = 896, 64
N_EXPERTS = 4
EPS_P = 1e-9
CONDITIONS = ("E0", "E1", "E1S", "E2", "E3", "E4")
COND_NAME = {"E0": "SHARED", "E1": "ANON_MOE", "E1S": "ANON_SPARSE",
             "E2": "CAS_EXPERT", "E3": "CAS_STRUCT", "E4": "SHUFFLED"}
KILLER_CONTROL = "E1S"            # owner ruling: the fair race is E2 vs E1S
CAS_ARMS = ("E2", "E3")
MARGIN = 0.02                     # overall primary effect (unchanged)
FAMILY_GAIN = 0.005               # eligible-family improvement threshold
FAMILY_SEEDS = 2                  # of 3 seeds must be positive
SATURATED_ACC = 0.99              # family saturated at/above this baseline
SATURATED_HEADROOM = 0.01         # ...or with less headroom than this
RETENTION_MARGIN = 0.02           # CAS must forget this much LESS than E1S
ACQUISITION_TOL = 0.02            # ...while learning phase 2 within this
STRESS_MIN_GAIN = 0.05            # phase-2 learning needed for a valid test
COMPETENCE_FLOOR_MARGIN = 0.15    # over candidate-uniform chance
E4_MAX_MUTUAL_INFO_BITS = 0.01    # E4 routing must be class-independent
RETENTION_PHASE1 = "QB_INT"       # owner ruling: ^2, ^6
RETENTION_PHASE2 = "QB_COMP"      # owner ruling: ^2, ^6, + NEW ^8
RETENTION_UPDATES = 500
RATE_PER_HOUR = 0.526


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


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_records(split):
    p = HERE / "data" / f"{split}.jsonl"
    recs = [json.loads(l) for l in p.read_text("utf-8").splitlines() if l]
    return [r for r in recs if r["question_type"] in FAMS]


def scramble_expert(pid, clause_idx):
    """FROZEN per-clause expert assignment carrying NO operation content."""
    h = hashlib.sha256(f"CJTEX1_SCRAMBLE|{pid}|{clause_idx}".encode())
    return int.from_bytes(h.digest()[:4], "big") % N_EXPERTS


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
        scr = torch.zeros(b, N, dtype=torch.long)
        ans = torch.zeros(b, dtype=torch.long)
        qt, br_g = [], []
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
            for k, c in enumerate(rec["idea_labels"]):
                p[j, k, CLASSES.index(c)] = 1.0
                cls[j, k] = CLASSES.index(c)
                scr[j, k] = scramble_expert(pid, k)
            ans[j] = rec["candidates"].index(rec["answer"])
            qt.append(rec["question_type"])
            _s, br_, _f = gold_path(rec)
            br_g.append(rec["candidates"].index(br_))
        out.append({"h": h, "g": g, "p": p, "cls": cls, "scr": scr, "e": e,
                    "m": m, "cmask": cmask, "imask": imask, "r0": r0,
                    "ans": ans, "qt": qt, "bridge": br_g})
    return out


# ---- the expert bank --------------------------------------------------------
def build_executor(cond, hidden, involution_hidden=None):
    """The A1 recurrent clause-entity graph executor with its two
    clause-local scorers replaced by EXPERT BANKS. Only the bank's
    organization differs across conditions."""
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    n_e = 1 if cond == "E0" else N_EXPERTS

    class Bank(nn.Module):
        """n_e experts over a feature vector, selected per CLAUSE.

        E3 ties the aversion expert to the attraction expert: they share a
        body and their read-out vectors satisfy v[1] = -v[0], so '^3' is
        literally '^2 read with reversed orientation'. That is the canonical
        ^2<->^3 involution expressed as a COMPUTATIONAL RULE."""

        def __init__(self, in_dim, hid, n_experts, mode):
            super().__init__()
            self.mode = mode
            self.n_e = n_experts
            self.hid = hid
            # C0-review fix: E3 now ACTUALLY shares the body of the
            # involution pair. The previous version allocated four
            # independent bodies for every mode and tied only the readout,
            # while the docstring claimed a shared body -- a registered
            # mechanism that the code did not implement. E3 stores
            # n_experts-1 bodies and expands index 1 from index 0.
            n_body = (n_experts - 1) if mode == "E3" else n_experts
            self.n_body = n_body
            self.w1 = nn.Parameter(torch.randn(n_body, in_dim, hid)
                                   * (in_dim ** -0.5))
            self.b1 = nn.Parameter(torch.zeros(n_body, hid))
            self.w2 = nn.Parameter(torch.randn(n_body, hid, hid)
                                   * (hid ** -0.5))
            self.b2 = nn.Parameter(torch.zeros(n_body, hid))
            self.v = nn.Parameter(torch.randn(n_body, hid) * (hid ** -0.5))
            self.vb = nn.Parameter(torch.zeros(n_body))
            if mode in ("E1", "E1S"):
                self.router = nn.Linear(D, n_experts)

        def _expand(self, t):
            """E3: expert 1 (aversion ^3) IS expert 0 (attraction ^2) --
            same body, readout negated. Everything else is identity."""
            if self.mode != "E3":
                return t
            return torch.cat([t[0:1], t[0:1], t[1:]], dim=0)

        def bodies(self):
            return (self._expand(self.w1), self._expand(self.b1),
                    self._expand(self.w2), self._expand(self.b2))

        def readout(self):
            if self.mode != "E3":
                return self.v, self.vb
            # index 0 = attraction (^2); index 1 = aversion (^3) = the same
            # body read with REVERSED orientation; 2,3 free.
            v0 = self.v[0:1]
            v = torch.cat([v0, -v0, self.v[1:]], dim=0)
            b0 = self.vb[0:1]
            b = torch.cat([b0, -b0, self.vb[1:]], dim=0)
            return v, b

        def forward(self, feats, cls, scr, hclause, imask):
            """feats (B,N,C,F) -> scores (B,N,C). Expert chosen per clause."""
            B, N, C, Fd = feats.shape
            w1, b1, w2, b2 = self.bodies()
            x = torch.einsum("bncf,efh->bnceh", feats, w1) \
                + b1.view(1, 1, 1, self.n_e, self.hid)
            x = F.gelu(x)
            x = torch.einsum("bnceh,ehk->bncek", x, w2) \
                + b2.view(1, 1, 1, self.n_e, self.hid)
            x = F.gelu(x)
            v, vb = self.readout()
            s = torch.einsum("bncek,ek->bnce", x, v) \
                + vb.view(1, 1, 1, self.n_e)               # (B,N,C,E)
            if self.mode == "E0":
                return s[..., 0], None
            if self.mode == "E1":                       # DENSE mixture
                w = torch.softmax(self.router(hclause), dim=-1)  # (B,N,E)
                w = w * imask.unsqueeze(-1)
                return torch.einsum("bnce,bne->bnc", s, w), w
            if self.mode == "E1S":                      # SPARSE top-1
                # Straight-through: the forward pass uses an exact one-hot
                # (so exactly ONE expert is active, matching E2/E3/E4's
                # regime and output magnitude) while the backward pass sees
                # the soft router probabilities, so the router still learns.
                soft = torch.softmax(self.router(hclause), dim=-1)
                hard = F.one_hot(soft.argmax(-1), self.n_e).to(soft.dtype)
                w = hard + soft - soft.detach()
                w = w * imask.unsqueeze(-1)
                return torch.einsum("bnce,bne->bnc", s, w), hard
            idx = cls if self.mode in ("E2", "E3") else scr
            oh = F.one_hot(idx, self.n_e).to(s.dtype)        # (B,N,E)
            return torch.einsum("bnce,bne->bnc", s, oh), oh

    class Executor(nn.Module):
        def __init__(self):
            super().__init__()
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
            self.wu = nn.Linear(2 * D, D)
            h1 = hidden if involution_hidden is None else involution_hidden
            self.bank1 = Bank(3 * D, h1, n_e, cond)
            self.bank2 = Bank(4 * D, h1, n_e, cond)

        def _routing_weights(self, bt, device):
            import torch
            h = bt["h"].to(device)
            mode = self.bank1.mode
            if mode == "E0":
                return torch.ones(h.shape[0], h.shape[1], 1, device=device)
            if mode == "E1":
                return torch.softmax(self.bank1.router(h), dim=-1)
            if mode == "E1S":
                soft = torch.softmax(self.bank1.router(h), dim=-1)
                return torch.nn.functional.one_hot(
                    soft.argmax(-1), self.bank1.n_e).float()
            idx = bt["cls"].to(device) if mode in ("E2", "E3")                 else bt["scr"].to(device)
            return torch.nn.functional.one_hot(
                idx, self.bank1.n_e).float()

        def expert_usage(self, batches, device):
            """Per-class expert distribution over the FULL evaluation
            surface (C0-review fix: previously computed on a single
            32-record batch that happened to be entirely QB_REL), plus the
            class-by-expert contingency table and the mutual information in
            bits -- which is how E4's class-independence is PROVEN rather
            than asserted (owner ruling section 7)."""
            import torch
            if isinstance(batches, dict):
                batches = [batches]
            n_e = self.bank1.n_e
            table = torch.zeros(4, n_e)
            with torch.no_grad():
                for bt in batches:
                    cls = bt["cls"].to(device)
                    imask = bt["imask"].to(device)
                    w = self._routing_weights(bt, device)
                    for k in range(4):
                        sel = (cls == k) & imask
                        if sel.any():
                            table[k] += w[sel].sum(0).cpu()
            tot = table.sum()
            usage = {}
            for k in range(4):
                rs = table[k].sum()
                if rs > 0:
                    usage[CLASSES[k]] = (table[k] / rs).tolist()
            mi = 0.0
            if tot > 0:
                pj = table / tot
                pc = pj.sum(1, keepdim=True).expand_as(pj)
                pe = pj.sum(0, keepdim=True).expand_as(pj)
                nz = pj > 0
                mi = float((pj[nz] * torch.log2(
                    pj[nz] / (pc[nz] * pe[nz]))).sum())
            return {"usage_by_class": usage,
                    "contingency_class_by_expert": table.tolist(),
                    "mutual_information_bits": round(mi, 6)}

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
            scr = bt["scr"].to(device)
            B, N, C, _ = e.shape
            neg = torch.finfo(h.dtype).min
            ebar = (e * m.unsqueeze(-1)).sum(1) / \
                m.sum(1).clamp(min=1).unsqueeze(-1)

            def hop(q, r_in, wq, wk, wr, lam, mu, bank, extra):
                s = (wq(q).unsqueeze(1) * wk(h)).sum(-1) / (D_ATT ** 0.5)
                s = s + lam * (wr(q).unsqueeze(1) * p).sum(-1)
                s = s + mu * (r_in.unsqueeze(1) * m.to(s.dtype)).sum(-1)
                s = s.masked_fill(~imask, neg)
                alpha = torch.softmax(s, dim=1)
                feats = torch.cat(
                    [q.unsqueeze(1).unsqueeze(1).expand(B, N, C, D),
                     h.unsqueeze(2).expand(B, N, C, D)] + extra + [e],
                    dim=-1)
                l, w = bank(feats, cls, scr, h, imask)
                l = l.masked_fill(~m, neg)
                P = torch.softmax(l, dim=2)
                P = torch.where(m.any(2, keepdim=True), P,
                                torch.zeros_like(P))
                return alpha, P, w

            a1, P1, w1 = hop(g, r0, self.wq1, self.wk1, self.wr1,
                             self.lam1, self.mu1, self.bank1, [])
            r1 = ((a1.unsqueeze(-1) * P1).sum(1)).masked_fill(~cmask, 0.0)
            b1 = (r1.unsqueeze(-1) * ebar).sum(1)
            q1 = torch.nn.functional.gelu(
                self.wu(torch.cat([g, b1], dim=-1)))
            a2, P2, w2 = hop(q1, r1, self.wq2, self.wk2, self.wr2,
                             self.lam2, self.mu2, self.bank2,
                             [b1.unsqueeze(1).unsqueeze(1)
                              .expand(B, N, C, D)])
            r2 = ((a2.unsqueeze(-1) * P2).sum(1)).masked_fill(~cmask, 0.0)
            logp = (r2 + EPS_P).log().masked_fill(~cmask, neg)
            if return_diag:
                return logp, {"r1": r1, "a1": a1, "w1": w1}
            return logp

    return Executor()


def param_count(mdl):
    return sum(p.numel() for p in mdl.parameters() if p.requires_grad)


def match_capacity(cond, target, lo=8, hi=1024):
    """Hidden width whose parameter count is CLOSEST to target.

    C0-review fix: the earlier version returned the FIRST width inside the
    +-1% band while scanning upward. Parameter count is monotone in width,
    so "first inside the band" meant "low edge of the tolerance" for every
    control while the hypothesis arms hit the target exactly (E1 landed
    0.908% BELOW E2). That bias ran toward the hypothesis -- the dangerous
    direction. Monotonicity also makes binary search exact, so the closest
    width is found without scanning the range."""
    def n(h):
        return param_count(build_executor(cond, h))
    a, b = lo, hi
    while a < b:                       # smallest width with n(mid) >= target
        mid = (a + b) // 2
        if n(mid) < target:
            a = mid + 1
        else:
            b = mid
    cands = {h for h in (a - 2, a - 1, a, a + 1, a + 2) if lo <= h <= hi}
    best = None
    for h in sorted(cands):
        c = n(h)
        if best is None or abs(c - target) < abs(best[1] - target):
            best = (h, c)
    return best


def evaluate(mdl, batches, device, keep_per_record=True):
    """Adds (C0 review + owner ruling): a PER-RECORD correctness vector so
    every arm-vs-arm comparison can use PAIRED statistics -- all arms are
    evaluated on the same records, so the independent-samples standard error
    is an overestimate -- plus per-family loss."""
    import torch
    mdl.eval()
    cor = tot = 0
    ls = 0.0
    per = {}
    per_loss = {}
    br = 0
    rec_ok, rec_fam = [], []
    with torch.no_grad():
        for bt in batches:
            logp, diag = mdl(bt, device, return_diag=True)
            tgt = bt["ans"].to(device)
            li = torch.nn.functional.nll_loss(logp, tgt, reduction="none")
            ls += float(li.sum().item())
            ok = logp.argmax(1) == tgt
            cor += int(ok.sum()); tot += len(tgt)
            b = diag["r1"].argmax(1)
            for j, q in enumerate(bt["qt"]):
                a, c = per.get(q, (0, 0))
                per[q] = (a + int(ok[j].item()), c + 1)
                sl, sc = per_loss.get(q, (0.0, 0))
                per_loss[q] = (sl + float(li[j].item()), sc + 1)
                br += int(int(b[j]) == bt["bridge"][j])
                if keep_per_record:
                    rec_ok.append(int(ok[j].item()))
                    rec_fam.append(q)
    mdl.train()
    out = {"accuracy": cor / tot, "loss": ls / tot, "bridge_top1": br / tot,
           "per_question_type": {k: {"accuracy": a / c, "correct": a,
                                     "total": c,
                                     "loss": per_loss[k][0] / per_loss[k][1]}
                                 for k, (a, c) in sorted(per.items())}}
    if keep_per_record:
        out["per_record_correct"] = rec_ok
        out["per_record_family"] = rec_fam
    return out


def train(mdl, tb, vb, updates, device, seed, checkpoints=True, opt=None):
    import torch
    nll = torch.nn.NLLLoss()
    if opt is None:
        opt = torch.optim.AdamW(mdl.parameters(), lr=LR, betas=BETAS,
                                weight_decay=WD)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lr_lambda(updates))
    curve, glog = [], []
    nonzero_updates = [0]
    cps = set(CHECKPOINTS) if checkpoints else set()
    pos = 0
    for step in range(updates):
        bt = tb[pos % len(tb)]; pos += 1
        logp = mdl(bt, device)
        loss = nll(logp, bt["ans"].to(device))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        if (step + 1) in GRAD_STEPS:
            ent = {"step": step + 1}
            for bname in ("bank1", "bank2"):
                bank = getattr(mdl, bname)
                for pn, pp in bank.named_parameters():
                    ent[f"{bname}.{pn}"] = (float(pp.grad.norm())
                                            if pp.grad is not None else 0.0)
                if bank.w1.grad is not None:      # PER-EXPERT gradient
                    ent[f"{bname}.per_expert_w1"] = [
                        float(g.norm()) for g in bank.w1.grad]
            glog.append(ent)
        if mdl.bank1.w1.grad is not None                 and float(mdl.bank1.w1.grad.norm()) > 0:
            nonzero_updates[0] += 1
        torch.nn.utils.clip_grad_norm_(mdl.parameters(), CLIP)
        opt.step(); sched.step()
        if not math.isfinite(float(loss.item())):
            raise RuntimeError(f"NONFINITE_LOSS seed {seed} step {step}")
        if (step + 1) in cps:
            curve.append({"step": step + 1,
                          "train_loss": float(loss.item()),
                          **evaluate(mdl, vb, device)})
    return opt, curve, glog, nonzero_updates[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out-dir", default=str(HERE / "results_cjt_ex1"))
    ap.add_argument("--updates", type=int, default=1000)
    args = ap.parse_args()
    import torch
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

    # ---- preflight (fail closed) -----------------------------------------
    man = json.loads((HERE / "PATHB_DATASET_MANIFEST.json")
                     .read_text("utf-8"))
    checks = {}
    for rel, want in man["files"].items():
        got = sha_file(HERE / rel)
        checks[f"dataset:{rel}"] = {"expected": want, "got": got,
                                    "ok": got == want}
    split_man = json.loads((HERE / "tier_c" / "C1_SPLIT_MANIFEST.json")
                           .read_text("utf-8"))
    val_all = load_records("val")
    c1_pids = sorted(r["passage_id"] for r in val_all
                     if c1_side(r["passage_id"]))
    c2_pids = sorted(r["passage_id"] for r in val_all
                     if not c1_side(r["passage_id"]))
    for nm, pids, key in (("c1", c1_pids, "c1_pids_sha256"),
                          ("c2_sealed", c2_pids, "c2_pids_sha256")):
        got = hashlib.sha256("\n".join(pids).encode()).hexdigest()
        checks[f"split:{nm}"] = {"expected": split_man[key], "got": got,
                                 "ok": got == split_man[key]}
    failed_pre = [k for k, v in checks.items() if not v["ok"]]
    if failed_pre:
        (out / "CJT_EX1_PREFLIGHT_FAILED.json").write_text(
            json.dumps({"checks": checks, "failed": failed_pre}, indent=2),
            encoding="utf-8")
        print(f"PREFLIGHT_FAILED: {failed_pre}")
        return 1
    print(f"[preflight] {len(checks)} integrity checks PASS")

    train_recs = load_records("train")
    val_c1 = [r for r in val_all if c1_side(r["passage_id"])]
    print(f"[split] train={len(train_recs)} (families A,B; verbs 0-5, "
          f"forms 0-3) eval={len(val_c1)} (family C; verbs 6-7, form 4 -- "
          f"UNSEEN); C2 half sealed={len(c2_pids)}")

    from transformers import AutoTokenizer, AutoModel
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModel.from_pretrained(MODEL_ID, torch_dtype=torch.float16) \
        .to(device).eval()
    is_real = next(model.parameters()).is_cuda
    cfg = json.dumps(model.config.to_dict(), sort_keys=True, default=str)
    model_sha = hashlib.sha256((MODEL_ID + "|" + cfg).encode()).hexdigest()
    tok_sha = hashlib.sha256(
        (tok.__class__.__name__ + "|" + str(tok.vocab_size)).encode()
    ).hexdigest()
    extr_sha = hashlib.sha256(
        (PKG / "exec" / "activation_extraction.py").read_bytes()
        + (HERE / "pathb_a0_probe.py").read_bytes()).hexdigest()
    manifest_sha = sha_file(HERE / "PATHB_DATASET_MANIFEST.json")

    cache = out / "cache"; cache.mkdir(exist_ok=True)
    acts, loc, bind_report = {}, {}, {}
    for name, recs in (("ex1_train", train_recs), ("ex1_eval", val_c1)):
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
        summ = cbind.verify_cache_binding(
            binding, list(a.keys()), recs,
            expected_manifest_sha=manifest_sha, expected_layer=L_FROZEN,
            expected_model_sha=model_sha, expected_tokenizer_sha=tok_sha,
            expected_extraction_code_sha=extr_sha)
        bind_report[name] = {"verified_records": summ["verified_records"],
                             "expected": len(recs), "pass": summ["pass"]}
        acts.update(a); loc.update(l)
        print(f"[cache] {name} binding verified: "
              f"{summ['verified_records']} records")
    assert len(acts) == len(train_recs) + len(val_c1), "PID_COLLISION"
    del model
    torch.cuda.empty_cache()

    # ---- capacity matching (total trainable params within 1%) -------------
    ref_hidden = 128
    target = param_count(build_executor("E2", ref_hidden))
    hid, counts = {}, {}
    for c in CONDITIONS:
        h_, n_ = match_capacity(c, target)
        hid[c] = h_
        counts[c] = n_
    cmax = max(counts.values())
    params_ok = all(abs(v - cmax) <= 0.01 * cmax for v in counts.values())
    print(f"[capacity] target={target} hidden={hid} counts={counts} "
          f"matched_1pct={params_ok}")

    vb = pack(val_c1, acts, loc, list(range(len(val_c1))))
    chance = float(sum(1.0 / len(r["candidates"]) for r in val_c1)
                   / len(val_c1))
    ACTIVE_EXPERTS = {"E0": 1, "E1": N_EXPERTS, "E1S": 1, "E2": 1,
                      "E3": 1, "E4": 1}
    print(f"[floor] candidate-uniform chance {chance:.4f}; competence floor "
          f"{chance + COMPETENCE_FLOOR_MARGIN:.4f}")

    # ---- P0 smoke gates ---------------------------------------------------
    p0 = {"pilot": "CJT-EX1 P0", "non_claim_bearing": True,
          "is_real_model": is_real, "preflight_checks": checks,
          "cache_binding": bind_report, "hidden": hid,
          "param_counts": counts, "gate_params_matched_1pct": params_ok}
    # bijection-is-identity check (the C1 lesson, verified not assumed)
    tb_s = pack(train_recs[:256], acts, loc, seeded_order(256, 11))
    torch.manual_seed(11)
    m_a = build_executor("E2", hid["E2"]).float().to(device)
    torch.manual_seed(11)
    m_b = build_executor("E2", hid["E2"]).float().to(device)
    with torch.no_grad():                       # permute expert slots
        perm = torch.tensor([1, 0, 3, 2])
        for bank_a, bank_b in ((m_a.bank1, m_b.bank1),
                               (m_a.bank2, m_b.bank2)):
            bank_b.w1.copy_(bank_a.w1[perm]); bank_b.b1.copy_(bank_a.b1[perm])
            bank_b.w2.copy_(bank_a.w2[perm]); bank_b.b2.copy_(bank_a.b2[perm])
            bank_b.v.copy_(bank_a.v[perm]); bank_b.vb.copy_(bank_a.vb[perm])
    bt0 = dict(tb_s[0])
    bt0_perm = dict(bt0)
    bt0_perm["cls"] = perm.to(bt0["cls"].device)[bt0["cls"]]
    with torch.no_grad():
        d = float((m_a(bt0, device) - m_b(bt0_perm, device)).abs().max())
    p0["bijection_is_relabeling_max_logit_diff"] = d
    p0["bijection_is_relabeling_confirmed"] = d < 1e-4
    print(f"[P0] a fixed class->expert BIJECTION is a pure relabeling: "
          f"max|logit diff| = {d:.3e} -> {'CONFIRMED' if d < 1e-4 else 'NO'}"
          f" (this is why E4 scrambles PER CLAUSE)")
    del m_a, m_b
    torch.cuda.empty_cache()
    # every condition trains and routes
    smoke = {}
    step_ms = {}
    for c in CONDITIONS:
        torch.manual_seed(11)
        mdl = build_executor(c, hid[c]).float().to(device)
        t_s = time.time()
        _o, _cv, gl, _nz = train(mdl, tb_s, vb, 60, device, 11,
                                 checkpoints=False)
        if device.startswith("cuda"):
            torch.cuda.synchronize()
        step_ms[c] = round((time.time() - t_s) / 60 * 1000, 3)
        use = mdl.expert_usage(vb, device)          # FULL eval surface
        ev = evaluate(mdl, vb, device, keep_per_record=False)
        g50 = gl[0] if gl else {}
        norms = {k: v for k, v in g50.items()
                 if isinstance(v, float) and k != "step"}
        smoke[c] = {"bank_grads_step50": g50,
                    "all_bank_tensors_live": bool(norms)
                    and all(v > 1e-9 for k, v in norms.items()
                            if not k.endswith(".vb")),
                    "expert_usage": use,
                    "smoke_accuracy": ev["accuracy"],
                    "ms_per_step": step_ms[c],
                    "active_experts_per_clause": ACTIVE_EXPERTS[c]}
        print(f"[P0] {c} {COND_NAME[c]:12} live="
              f"{smoke[c]['all_bank_tensors_live']} "
              f"{step_ms[c]:.1f}ms/step MI="
              f"{use['mutual_information_bits']:.4f} bits acc="
              f"{ev['accuracy']:.4f}")
        del mdl
        torch.cuda.empty_cache()
    p0["per_condition"] = smoke
    p0["measured_ms_per_step"] = step_ms
    p0["candidate_uniform_chance"] = chance
    p0["active_experts_per_clause"] = ACTIVE_EXPERTS
    e4_mi_p0 = smoke["E4"]["expert_usage"]["mutual_information_bits"]
    p0["e4_class_independence_bits"] = e4_mi_p0
    p0["gate_e4_class_independent"] = e4_mi_p0 <= E4_MAX_MUTUAL_INFO_BITS
    print(f"[P0] E4 routing/class mutual information {e4_mi_p0:.5f} bits "
          f"(max {E4_MAX_MUTUAL_INFO_BITS}) -> "
          f"{'VALID CONTROL' if p0['gate_e4_class_independent'] else 'INVALID'}")
    p0_fail = ([] if params_ok else ["gate_params_matched_1pct"]) + \
        ([] if p0["bijection_is_relabeling_confirmed"]
         else ["gate_bijection_relabeling"]) + \
        ([] if p0["gate_e4_class_independent"]
         else ["gate_e4_class_independent"]) +         [f"{c}:dead_bank_tensor" for c in CONDITIONS
         if not smoke[c]["all_bank_tensors_live"]]
    p0["failed"] = p0_fail
    p0["status"] = "CJT_EX1_P0_SMOKE_OK" if not p0_fail else \
        "CJT_EX1_SMOKE_FAILED"
    p0["estimated_cost_usd_so_far"] = est_cost()
    (out / "CJT_EX1_P0_RESULTS.json").write_text(
        json.dumps(p0, indent=2) + "\n", encoding="utf-8")
    if p0_fail:
        print(f"P0 FAILED: {p0_fail} -- no main spend")
        return 1

    # ---- MAIN: 5 conditions x 3 seeds ------------------------------------
    runs = []
    partial = out / "CJT_EX1_PARTIAL_RUNS.json"

    def flush():
        partial.write_text(json.dumps(
            {"completed": len(runs), "runs": runs,
             "estimated_cost_usd_so_far": est_cost()}, indent=2) + "\n",
            encoding="utf-8")

    try:
        for seed in SEEDS:
            tb = pack(train_recs, acts, loc,
                      seeded_order(len(train_recs), seed))
            for c in CONDITIONS:
                torch.manual_seed(seed)
                torch.cuda.manual_seed_all(seed)
                mdl = build_executor(c, hid[c]).float().to(device)
                _o, curve, gl, _nz = train(mdl, tb, vb, args.updates, device,
                                           seed)
                fin = evaluate(mdl, vb, device)
                runs.append({"phase": "main", "cond": c, "seed": seed,
                             "params": param_count(mdl), "hidden": hid[c],
                             "final": fin, "curve": curve, "grad_log": gl,
                             "expert_usage": mdl.expert_usage(vb, device)})
                flush()
                print(f"[MAIN] {c} {COND_NAME[c]:10} s{seed} "
                      f"acc={fin['accuracy']:.4f} "
                      f"fam={ {k: round(v['accuracy'],3) for k,v in fin['per_question_type'].items()} }")
                del mdl
                torch.cuda.empty_cache()
            del tb

        # ---- RETENTION: sequential learning (AMENDED per owner ruling) --
        # phase 1 = QB_INT (^2, ^6); phase 2 = QB_COMP (^2, ^6, + NEW ^8).
        # Every expert relevant to the RETAINED phase-1 skill stays EXPOSED
        # to phase-2 learning; ^8 enters as a new specialist. (^3 appears in
        # neither phase -- stated, not glossed.)
        ph1 = [r for r in train_recs
               if r["question_type"] == RETENTION_PHASE1]
        ph2 = [r for r in train_recs
               if r["question_type"] == RETENTION_PHASE2]
        print(f"[RET ] phase1={RETENTION_PHASE1} (n={len(ph1)}) "
              f"phase2={RETENTION_PHASE2} (n={len(ph2)})")
        for seed in SEEDS:
            tb1 = pack(ph1, acts, loc, seeded_order(len(ph1), seed))
            tb2 = pack(ph2, acts, loc, seeded_order(len(ph2), seed))
            for c in CONDITIONS:
                torch.manual_seed(seed)
                torch.cuda.manual_seed_all(seed)
                mdl = build_executor(c, hid[c]).float().to(device)
                opt, _c1, g1, nz1 = train(mdl, tb1, vb, RETENTION_UPDATES,
                                          device, seed, checkpoints=False)
                after1 = evaluate(mdl, vb, device)
                # snapshot the SHARED experts before phase 2
                snap = {n_: pp.detach().clone()
                        for n_, pp in mdl.bank1.named_parameters()}
                _o, _c2, g2, nz2 = train(mdl, tb2, vb, RETENTION_UPDATES,
                                         device, seed, checkpoints=False,
                                         opt=opt)
                after2 = evaluate(mdl, vb, device)
                move = {n_: float((pp.detach() - snap[n_]).norm())
                        for n_, pp in mdl.bank1.named_parameters()}
                w1_now = mdl.bank1.w1.detach()
                per_expert_move = [
                    float((w1_now[k] - snap["w1"][k]).norm())
                    for k in range(w1_now.shape[0])]
                a1 = after1["per_question_type"].get(
                    RETENTION_PHASE1, {"accuracy": 0.0})["accuracy"]
                a2 = after2["per_question_type"].get(
                    RETENTION_PHASE1, {"accuracy": 0.0})["accuracy"]
                q1 = after1["per_question_type"].get(
                    RETENTION_PHASE2, {"accuracy": 0.0})["accuracy"]
                q2 = after2["per_question_type"].get(
                    RETENTION_PHASE2, {"accuracy": 0.0})["accuracy"]
                l1 = after1["per_question_type"].get(
                    RETENTION_PHASE2, {"loss": None}).get("loss")
                l2 = after2["per_question_type"].get(
                    RETENTION_PHASE2, {"loss": None}).get("loss")
                runs.append({
                    "phase": "retention", "cond": c, "seed": seed,
                    "phase1_family": RETENTION_PHASE1,
                    "phase2_family": RETENTION_PHASE2,
                    "retained_acc_before": a1,       # NUMERATOR + DENOMINATOR
                    "retained_acc_after": a2,        # both, never ratio-only
                    "forgetting": a1 - a2,
                    "retention_ratio": (a2 / a1) if a1 > 0 else None,
                    "newtask_acc_before": q1, "newtask_acc_after": q2,
                    "newtask_gain": q2 - q1,
                    "newtask_loss_before": l1, "newtask_loss_after": l2,
                    "nonzero_grad_updates": {"phase1": nz1, "phase2": nz2},
                    "bank1_param_movement_phase2": move,
                    "bank1_per_expert_w1_movement": per_expert_move,
                    "grad_log_phase1": g1, "grad_log_phase2": g2,
                    "after_phase1": {k: v for k, v in after1.items()
                                     if not k.startswith("per_record")},
                    "after_phase2": {k: v for k, v in after2.items()
                                     if not k.startswith("per_record")}})
                flush()
                print(f"[RET ] {c} {COND_NAME[c]:12} s{seed} "
                      f"{RETENTION_PHASE1} {a1:.4f}->{a2:.4f} "
                      f"(forgot {a1-a2:+.4f}) | {RETENTION_PHASE2} "
                      f"{q1:.4f}->{q2:.4f} (gain {q2-q1:+.4f}) "
                      f"nz2={nz2}")
                del mdl
                torch.cuda.empty_cache()
            del tb1, tb2
    except Exception as exc:
        flush()
        (out / "CJT_EX1_ABORTED.json").write_text(json.dumps(
            {"error": repr(exc), "traceback": traceback.format_exc(),
             "completed": len(runs), "estimated_cost_usd": est_cost()},
            indent=2) + "\n", encoding="utf-8")
        print(f"ABORTED after {len(runs)} runs: {exc!r}")
        return 1

    usage = {}
    for c in CONDITIONS:
        m_ = next((r for r in runs if r["phase"] == "main"
                   and r["cond"] == c), None)
        usage[c] = m_["expert_usage"] if m_ else None
    res = summarize(runs, counts, hid, checks, bind_report, is_real,
                    len(val_c1), est_cost, time.time() - t0, torch,
                    chance, usage, ACTIVE_EXPERTS, step_ms)
    (out / "CJT_EX1_RESULTS.json").write_text(
        json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(f"\nCJT-EX1 STATUS: {res['development_status']}")
    print(f"  secondary: {res['secondary_status']}")
    for c in CONDITIONS:
        a = res["arms"][c]
        print(f"  {c} {COND_NAME[c]:12} acc {a['mean']:.4f}+-{a['std']:.4f} "
              f"| forget {a['forgetting_mean']} "
              f"| newtask {a['newtask_acc_after_mean']}")
    km = res["key_margins"]
    print(f"  E2-E1S (KILLER) {km['E2_minus_E1S_KILLER']:+.4f} | "
          f"E2-E1 {km['E2_minus_E1_dense']:+.4f} | "
          f"E2-E4 {km['E2_minus_E4_shuffle']:+.4f} | "
          f"E3-E2 {km['E3_minus_E2_structure']:+.4f}")
    print(f"  eligible families {res['eligible_families_frozen']} improved "
          f"{res['families_improved']}")
    print(f"  wall {round(time.time()-t0,1)}s  est_cost ${est_cost()}")
    return 0


def summarize(runs, counts, hid, checks, bind_report, is_real, n_eval,
              est_cost, wall, torch, chance, usage, active_experts,
              step_ms):
    """Frozen aggregation and the AMENDED status law (owner ruling
    2026-09-01). Every threshold, the eligible-family set, and the result
    vocabulary are fixed here BEFORE the run."""
    KC = KILLER_CONTROL

    def mains(c):
        return [r for r in runs if r["phase"] == "main" and r["cond"] == c]

    def rets(c):
        return [r for r in runs if r["phase"] == "retention"
                and r["cond"] == c]

    def agg(c):
        ms, rs = mains(c), rets(c)
        accs = [r["final"]["accuracy"] for r in ms]
        mean = sum(accs) / len(accs)
        sd = math.sqrt(sum((x - mean) ** 2 for x in accs) / len(accs))
        fam = {}
        for q in FAMS:
            v = [r["final"]["per_question_type"][q]["accuracy"] for r in ms
                 if q in r["final"]["per_question_type"]]
            fam[q] = round(sum(v) / len(v), 6) if v else None
        mv_rows = [r["bank1_per_expert_w1_movement"] for r in rs]
        return {"mean": round(mean, 6), "std": round(sd, 6),
                "by_seed": {r["seed"]: round(r["final"]["accuracy"], 6)
                            for r in ms},
                "per_family": fam,
                "per_family_by_seed": {
                    q: {r["seed"]: round(
                        r["final"]["per_question_type"][q]["accuracy"], 6)
                        for r in ms if q in r["final"]["per_question_type"]}
                    for q in FAMS},
                "bridge_top1_mean": round(sum(r["final"]["bridge_top1"]
                                              for r in ms) / len(ms), 4),
                "retained_acc_before_mean": round(sum(
                    r["retained_acc_before"] for r in rs) / len(rs), 6)
                if rs else None,
                "retained_acc_after_mean": round(sum(
                    r["retained_acc_after"] for r in rs) / len(rs), 6)
                if rs else None,
                "forgetting_mean": round(sum(r["forgetting"] for r in rs)
                                         / len(rs), 6) if rs else None,
                "newtask_gain_mean": round(sum(r["newtask_gain"] for r in rs)
                                           / len(rs), 6) if rs else None,
                "newtask_acc_after_mean": round(sum(
                    r["newtask_acc_after"] for r in rs) / len(rs), 6)
                if rs else None,
                "nonzero_grad_updates_phase2_mean": round(sum(
                    r["nonzero_grad_updates"]["phase2"] for r in rs)
                    / len(rs), 1) if rs else None,
                "bank1_per_expert_w1_movement_mean": (
                    [round(sum(row[k] for row in mv_rows) / len(mv_rows), 6)
                     for k in range(len(mv_rows[0]))] if mv_rows else None),
                "expert_usage": usage.get(c),
                "active_experts_per_clause": active_experts[c],
                "measured_ms_per_step": step_ms.get(c),
                "params": counts[c], "hidden": hid[c]}

    arms = {c: agg(c) for c in CONDITIONS}

    # ---- PAIRED statistics: every arm sees the SAME records -------------
    def paired(a, b):
        das = []
        for sd_ in SEEDS:
            ra = next((r for r in mains(a) if r["seed"] == sd_), None)
            rb = next((r for r in mains(b) if r["seed"] == sd_), None)
            if not ra or not rb:
                continue
            va = ra["final"].get("per_record_correct")
            vb_ = rb["final"].get("per_record_correct")
            if not va or not vb_ or len(va) != len(vb_):
                continue
            das.append([x - y for x, y in zip(va, vb_)])
        if not das:
            return None
        flat = [d for row in das for d in row]
        n = len(flat)
        m = sum(flat) / n
        var = sum((d - m) ** 2 for d in flat) / max(1, n - 1)
        seed_means = [sum(row) / len(row) for row in das]
        return {"paired_mean_diff": round(m, 6),
                "paired_se_over_records": round(math.sqrt(var / n), 6),
                "per_seed_mean_diff": [round(x, 6) for x in seed_means],
                "seeds_positive": sum(1 for x in seed_means if x > 0),
                "n_paired_records": n}

    def paired_family(a, b, q):
        das = []
        for sd_ in SEEDS:
            ra = next((r for r in mains(a) if r["seed"] == sd_), None)
            rb = next((r for r in mains(b) if r["seed"] == sd_), None)
            if not ra or not rb:
                continue
            fa = ra["final"].get("per_record_family") or []
            va = ra["final"].get("per_record_correct") or []
            vb_ = rb["final"].get("per_record_correct") or []
            d = [x - y for x, y, f in zip(va, vb_, fa) if f == q]
            if d:
                das.append(sum(d) / len(d))
        if not das:
            return None
        return {"mean_paired_gain": round(sum(das) / len(das), 6),
                "per_seed": [round(x, 6) for x in das],
                "seeds_positive": sum(1 for x in das if x > 0)}

    # ---- family eligibility, FROZEN before the run ----------------------
    base = arms[KC]["per_family"]
    saturation = {}
    for q in FAMS:
        b = base[q] if base[q] is not None else 0.0
        sat = (b >= SATURATED_ACC) or ((1.0 - b) < SATURATED_HEADROOM)
        saturation[q] = {"killer_control_baseline": b,
                         "headroom": round(1.0 - b, 6), "saturated": sat,
                         "eligible_for_breadth_gate": not sat}
    eligible = [q for q in FAMS if not saturation[q]["saturated"]]

    families = {}
    for q in FAMS:
        pf = paired_family("E2", KC, q)
        b = base[q] if base[q] is not None else 0.0
        e2 = arms["E2"]["per_family"][q]
        gain = (e2 - b) if e2 is not None else None
        headroom = 1.0 - b
        n_fam = n_eval / len(FAMS)
        families[q] = {
            "killer_control_accuracy": b, "E2_accuracy": e2,
            "absolute_gain": round(gain, 6) if gain is not None else None,
            "remaining_error_reduction": (round(gain / headroom, 6)
                                          if gain is not None
                                          and headroom > 1e-9 else None),
            "raw_additional_correct_answers": (round(gain * n_fam, 2)
                                               if gain is not None else None),
            "paired": pf, "saturated": saturation[q]["saturated"],
            "counts_as_improved": bool(
                not saturation[q]["saturated"] and pf
                and pf["mean_paired_gain"] >= FAMILY_GAIN
                and pf["seeds_positive"] >= FAMILY_SEEDS)}
    fams_improved = [q for q in eligible if families[q]["counts_as_improved"]]

    # ---- retention: numerator AND denominator, never a bare ratio -------
    ret_seed_delta = []
    for sd_ in SEEDS:
        rc = next((r for r in rets("E2") if r["seed"] == sd_), None)
        rk = next((r for r in rets(KC) if r["seed"] == sd_), None)
        if rc and rk:
            ret_seed_delta.append(rk["forgetting"] - rc["forgetting"])
    ret_advantage = (sum(ret_seed_delta) / len(ret_seed_delta)
                     if ret_seed_delta else None)
    ret_seeds_pos = sum(1 for x in ret_seed_delta if x > 0)
    acq_ok = None
    if arms["E2"]["newtask_acc_after_mean"] is not None:
        others = [arms[c]["newtask_acc_after_mean"] for c in CONDITIONS
                  if c != "E2"
                  and arms[c]["newtask_acc_after_mean"] is not None]
        if others:
            acq_ok = bool(arms["E2"]["newtask_acc_after_mean"]
                          >= max(others) - ACQUISITION_TOL)
    # REAL INTERFERENCE PRESSURE gate (owner ruling, check A)
    stress = {}
    for c in CONDITIONS:
        mv = arms[c]["bank1_per_expert_w1_movement_mean"]
        stress[c] = {"newtask_gain": arms[c]["newtask_gain_mean"],
                     "max_expert_param_movement": (max(mv) if mv else None),
                     "nonzero_grad_updates_phase2":
                         arms[c]["nonzero_grad_updates_phase2_mean"]}
    stress_ok = all(
        (stress[c]["newtask_gain"] is not None
         and stress[c]["newtask_gain"] >= STRESS_MIN_GAIN
         and (stress[c]["max_expert_param_movement"] or 0) > 1e-6)
        for c in CONDITIONS)
    retention_ok = bool(stress_ok and ret_advantage is not None
                        and ret_advantage >= RETENTION_MARGIN
                        and ret_seeds_pos >= FAMILY_SEEDS and acq_ok)

    # ---- E4 must be PROVEN class-independent ----------------------------
    e4_mi = (usage.get("E4") or {}).get("mutual_information_bits")
    e4_valid = bool(e4_mi is not None and e4_mi <= E4_MAX_MUTUAL_INFO_BITS)

    floor = chance + COMPETENCE_FLOOR_MARGIN
    floor_ok = {c: bool(arms[c]["mean"] >= floor) for c in CONDITIONS}

    p_e2_kc = paired("E2", KC)
    p_e2_e1 = paired("E2", "E1")
    p_e2_e4 = paired("E2", "E4")
    p_e3_e2 = paired("E3", "E2")
    m_e2_kc = round(arms["E2"]["mean"] - arms[KC]["mean"], 6)
    m_e2_e1 = round(arms["E2"]["mean"] - arms["E1"]["mean"], 6)
    m_e2_e4 = round(arms["E2"]["mean"] - arms["E4"]["mean"], 6)
    m_e3_e2 = round(arms["E3"]["mean"] - arms["E2"]["mean"], 6)

    conds = {
        "1_beats_killer_control_E1S": m_e2_kc >= MARGIN,
        "2_unseen_verbs_and_templates":
            "BY CONSTRUCTION -- every accuracy is on family C (verbs 6-7, "
            "form 4), disjoint from training",
        "3_breadth_over_eligible_families": len(fams_improved) >= 2,
        "4_shuffling_removes_the_advantage": m_e2_e4 >= MARGIN,
        "5_structured_sharing_helps_EXPLORATORY": m_e3_e2 >= MARGIN,
        "6_better_retention_than_E1S": retention_ok,
        "7_matched_params_compute_seeds":
            max(counts.values()) - min(counts.values())
            <= 0.01 * max(counts.values()),
        "8_E4_proven_class_independent": e4_valid,
        "9_competence_floor": all(floor_ok.values())}

    # ---- the RULED result vocabulary ------------------------------------
    beats_kc = m_e2_kc >= MARGIN
    beats_e1 = m_e2_e1 >= MARGIN
    e4_ge_e2 = arms["E4"]["mean"] >= arms["E2"]["mean"]
    if e4_ge_e2 and e4_valid:
        status = "CAS_EXPERT_MEANINGS_NOT_LOAD_BEARING"
    elif not beats_kc and beats_e1:
        status = "SPARSITY_ADVANTAGE_ONLY"
    elif (beats_kc and conds["3_breadth_over_eligible_families"]
          and conds["4_shuffling_removes_the_advantage"]
          and conds["6_better_retention_than_E1S"]):
        status = "CJT_EXPERT_SPECIALIZATION_SIGNAL"
    else:
        status = "NO_CJT_EXPERT_SPECIALIZATION_SIGNAL"
    secondary = ("STRUCTURED_WEIGHT_SHARING_SIGNAL"
                 if m_e3_e2 >= MARGIN else None)
    if not stress_ok:
        status = status + " | RETENTION_STRESS_INSUFFICIENT"

    return {
        "pilot": "CJT-EX1 EXPERT SPECIALIZATION AND TRANSFER (AMENDED)",
        "non_claim_bearing": True, "is_real_model": is_real,
        "layer_frozen": L_FROZEN,
        "owner_ruling": "amended 2026-09-01: headroom-aware breadth; "
                        "retention phase1=QB_INT phase2=QB_COMP with a "
                        "real-interference gate; E1S anonymous sparse top-1 "
                        "added as THE killer control; E3 exploratory only; "
                        "E4 must be proven class-independent",
        "scope": "Permitted at most: 'CJT-organized expert modules improved "
                 "specialization, transfer, or retention relative to a "
                 "matched generic SPARSE expert architecture in a controlled "
                 "development task.' An E3 advantage is reported as "
                 "STRUCTURED_WEIGHT_SHARING_SIGNAL, never as an "
                 "involution-specific CAS advantage (this run has no matched "
                 "generic pair-sharing control). 'CAS-specific' and "
                 "'specific' remain PROHIBITED.",
        "eval_split": f"family C, {n_eval} records (C1_TRANSFORM_SELECT "
                      "half; C2_STRUCTURE_EVAL sealed). Verbs and forms are "
                      "disjoint from training: all accuracies are transfer.",
        "killer_control": KC,
        "preflight_checks": checks, "cache_binding": bind_report,
        "arms": arms,
        "candidate_uniform_chance": chance,
        "competence_floor": floor, "competence_floor_ok": floor_ok,
        "family_saturation": saturation,
        "eligible_families_frozen": eligible,
        "families": families, "families_improved": fams_improved,
        "key_margins": {
            "E2_minus_E1S_KILLER": m_e2_kc, "paired_E2_vs_E1S": p_e2_kc,
            "E2_minus_E1_dense": m_e2_e1, "paired_E2_vs_E1": p_e2_e1,
            "E2_minus_E4_shuffle": m_e2_e4, "paired_E2_vs_E4": p_e2_e4,
            "E3_minus_E2_structure": m_e3_e2, "paired_E3_vs_E2": p_e3_e2},
        "retention": {
            "phase1_family": RETENTION_PHASE1,
            "phase2_family": RETENTION_PHASE2,
            "note": "^2 and ^6 are exposed in BOTH phases; ^8 enters as a "
                    "NEW specialist in phase 2; ^3 appears in NEITHER phase "
                    "(stated, not glossed)",
            "forgetting_by_condition": {c: arms[c]["forgetting_mean"]
                                        for c in CONDITIONS},
            "retained_before_by_condition": {
                c: arms[c]["retained_acc_before_mean"] for c in CONDITIONS},
            "retained_after_by_condition": {
                c: arms[c]["retained_acc_after_mean"] for c in CONDITIONS},
            "newtask_after_by_condition": {
                c: arms[c]["newtask_acc_after_mean"] for c in CONDITIONS},
            "E2_forgets_less_than_E1S_by": ret_advantage,
            "per_seed_advantage": [round(x, 6) for x in ret_seed_delta],
            "seeds_positive": ret_seeds_pos,
            "acquisition_within_tolerance": acq_ok,
            "interference_pressure": stress,
            "interference_pressure_sufficient": stress_ok,
            "retention_advantage_established": retention_ok},
        "e4_class_independence": {
            "mutual_information_bits": e4_mi,
            "max_allowed_bits": E4_MAX_MUTUAL_INFO_BITS,
            "valid_control": e4_valid,
            "contingency": (usage.get("E4") or {}).get(
                "contingency_class_by_expert")},
        "success_conditions": conds,
        "failed_conditions": [k for k, v in conds.items() if v is False],
        "development_status": status, "secondary_status": secondary,
        "param_counts": counts, "hidden_widths": hid,
        "active_experts_per_clause": active_experts,
        "measured_ms_per_step": step_ms,
        "gpu_max_memory_allocated_bytes":
            int(torch.cuda.max_memory_allocated()),
        "runs": runs, "total_wall_clock_seconds": round(wall, 1),
        "cost": {"method": "compute_wall_estimate (LOWER BOUND); the "
                           "authoritative spend proxy is the watchdog's "
                           "instance_runtime_estimate in the receipt",
                 "rate_per_hour_usd": RATE_PER_HOUR,
                 "estimated_cost_usd": est_cost()}}


if __name__ == "__main__":
    raise SystemExit(main())
