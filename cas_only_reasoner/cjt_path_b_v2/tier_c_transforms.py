"""tier_c_transforms.py -- Tier C tournament transforms T1-T4 (+ the label
channel shared with T0) in the minimal conformance form used by the C0
PROOF_OF_NON_EQUIVARIANCE. The SAME classes are reused by the C1 harness over
real activations (only d and the content encoder change).

Design laws:
  * Every learned parameter in the STRUCTURE pathway is indexed by R-CELL
    CONTENT TYPES (phi features, result types, J-pair types, M gate), never
    by raw class indices. The ONLY class-indexed parameter is the label
    channel's W_r (shared by all arms; its permutation-absorbability is
    exactly what A1's S-PERM test proved at 7.15e-07).
  * STRUCTURE_VIEW_MUST_CONTAIN_M: every transform's structure term is gated
    or informed by the M bit (T1/T4 read the full phi whose dim 0 is M;
    T2/T3 multiply by the M gate).
  * lambda_structure initialized 1.0 (the lambda-lock law).

Pair-tensor convention: index [b, k, l] means source clause k (weighted by
the previous-hop pointer) composing INTO target clause l, i.e. the ordered
cell (cls_k, cls_l).

Development-only, non-claim-bearing. CPU-safe.
"""
from __future__ import annotations

import itertools

import torch
import torch.nn as nn
import torch.nn.functional as F

import tier_c_structure as ts

L_CLAUSES = 6
N_CLASSES = 4
TRANSFORMS = ("T1", "T2", "T3", "T4")


# ---- frozen structure tensors ----------------------------------------------
class StructTensors:
    """Typed lookup tensors for one structure dict. All frozen (no grads)."""

    def __init__(self, struct):
        C = ts.CLASSES
        self.phi = torch.tensor(
            [[ts.phi(struct, a, b) for b in C] for a in C],
            dtype=torch.float32)                       # (4,4,20)
        self.m = torch.tensor(
            [[float(ts.m_of(struct, a, b)) for b in C] for a in C])
        self.rt = torch.tensor(
            [[ts.RESULT_TYPES.index(ts.cell(struct, a, b)["result_type"])
              for b in C] for a in C], dtype=torch.long)
        self.jt = torch.tensor(
            [[ts.J_PAIR_TYPES.index(struct["J"]["pair"][f"{a}|{b}"])
              for b in C] for a in C], dtype=torch.long)


def view_tensors(struct, kind):
    """The exact frozen tensors a transform consumes (its 'view')."""
    st = StructTensors(struct)
    if kind in ("T1", "T4"):
        return {"phi": st.phi.tolist()}
    if kind == "T2":
        return {"m": st.m.tolist(), "rt": st.rt.tolist()}
    if kind == "T3":
        return {"m": st.m.tolist(), "jt": st.jt.tolist()}
    raise ValueError(kind)


def view_automorphisms(struct, kind):
    """Permutations preserving the transform's view alone (a superset of the
    full-structure group; persisted for interpreting Test B)."""
    base = view_tensors(struct, kind)
    auts = []
    for perm in itertools.permutations(range(4)):
        pv = view_tensors(ts.permute_structure(struct, perm), kind)
        if pv == base:
            auts.append(list(perm))
    return auts


# ---- the conformance model --------------------------------------------------
class ConformanceModel(nn.Module):
    """Minimal clause-scoring executor: content + label channel + one
    structure transform. Scores L clauses; CE loss against a gold clause."""

    def __init__(self, kind, struct, d=32, seed=0):
        super().__init__()
        assert kind in TRANSFORMS
        self.kind = kind
        self.d = d
        self.st = StructTensors(struct)
        g = torch.Generator().manual_seed(seed)

        def init(*shape):
            return nn.Parameter(torch.randn(*shape, generator=g) * 0.1)
        self.w_r = init(N_CLASSES, d)                  # class-indexed (only)
        self.lam_lbl = nn.Parameter(torch.tensor(1.0))
        self.lam_str = nn.Parameter(torch.tensor(1.0))   # lambda-lock law
        if kind == "T1":
            self.w_phi = init(ts.PHI_DIM)
        elif kind == "T2":
            self.A = init(len(ts.RESULT_TYPES), d, d)  # content-indexed
        elif kind == "T3":
            self.B = init(len(ts.J_PAIR_TYPES), d, d)  # content-indexed
        else:                                          # T4: recurrent
            self.w_phi1 = init(ts.PHI_DIM)
            self.w_phi2 = init(ts.PHI_DIM)
            self.W_u = init(d, d)

    def swap_structure(self, struct):
        """Frozen-table swap (used by Test A twins and mutants)."""
        self.st = StructTensors(struct)

    # pair lookups: [b,k,l] = table[cls_k, cls_l] (source k -> target l)
    def _pair_phi(self, cls):                          # (B,L,L,20)
        return self.st.phi[cls.unsqueeze(2), cls.unsqueeze(1)]

    def _pair(self, tab, cls):                         # (B,L,L)
        return tab[cls.unsqueeze(2), cls.unsqueeze(1)]

    def forward(self, h, q, cls):
        """h: (B,L,d) clause features; q: (B,d); cls: (B,L) class indices.
        Returns clause scores (B,L)."""
        B, L, d = h.shape
        s_content = torch.einsum("bd,bld->bl", q, h) / d ** 0.5
        p = F.one_hot(cls, N_CLASSES).float()          # (B,L,4)
        s_lbl = torch.einsum("bd,cd,blc->bl", q, self.w_r, p)
        r_prev = torch.softmax(s_content, dim=1)       # hop-0 pointer
        if self.kind == "T1":
            pair = torch.einsum("f,bklf->bkl", self.w_phi,
                                self._pair_phi(cls))
            s_str = torch.einsum("bk,bkl->bl", r_prev, pair)
        elif self.kind == "T2":
            # s_str(l) = sum_k r(k) * M[k,l] * <q, A[rt(k,l)] h_k>/sqrt(d)
            qah = torch.einsum("bd,tde,bke->bkt", q, self.A, h) / d ** 0.5
            rt1h = F.one_hot(self._pair(self.st.rt, cls),
                             len(ts.RESULT_TYPES)).float()   # (B,K,L,T)
            contrib = torch.einsum("bkt,bklt->bkl", qah, rt1h)
            contrib = contrib * self._pair(self.st.m, cls)
            s_str = torch.einsum("bk,bkl->bl", r_prev, contrib)
        elif self.kind == "T3":
            # s_str(l) = sum_k r(k) * M[k,l] * q^T B[jt(k,l)] h_l /sqrt(d)
            qbh = torch.einsum("bd,tde,ble->blt", q, self.B, h) / d ** 0.5
            jt1h = F.one_hot(self._pair(self.st.jt, cls),
                             len(ts.J_PAIR_TYPES)).float()   # (B,K,L,T)
            contrib = torch.einsum("blt,bklt->bkl", qbh, jt1h)
            contrib = contrib * self._pair(self.st.m, cls)
            s_str = torch.einsum("bk,bkl->bl", r_prev, contrib)
        else:                                          # T4: two-hop recurrent
            feat = self._pair_phi(cls)
            pair1 = torch.einsum("f,bklf->bkl", self.w_phi1, feat)
            s1 = s_content + torch.einsum("bk,bkl->bl", r_prev, pair1)
            r1 = torch.softmax(s1, dim=1)              # carried soft pointer
            bvec = torch.einsum("bk,bkd->bd", r1, h)   # bridge state
            s_a = torch.einsum("bd,de,ble->bl", bvec, self.W_u, h) / d ** 0.5
            pair2 = torch.einsum("f,bklf->bkl", self.w_phi2, feat)
            s_str = s_a + torch.einsum("bk,bkl->bl", r1, pair2)
        return s_content + self.lam_lbl * s_lbl + self.lam_str * s_str


# ---- synthetic conformance data --------------------------------------------
def make_synth(seed, n=64, d=32):
    g = torch.Generator().manual_seed(seed)
    h = torch.randn(n, L_CLAUSES, d, generator=g)
    q = torch.randn(n, d, generator=g)
    cls = torch.randint(0, N_CLASSES, (n, L_CLAUSES), generator=g)
    gold = torch.randint(0, L_CLAUSES, (n,), generator=g)
    return h, q, cls, gold


def train_losses(model, data, steps=5, lr=1e-2, label_perm=None):
    """k AdamW steps. Returns (mean_losses, per_example) where mean_losses
    is the per-step batch-mean loss list and per_example is the
    (steps, n) tensor of per-example losses -- the conformance criterion
    runs on PER-EXAMPLE trajectories (C0 review hardening: n*steps
    residuals cannot be curve-fit by an init search the way 5 batch means
    can). label_perm (len-4) relabels classes cls -> perm[cls]."""
    h, q, cls, gold = data
    if label_perm is not None:
        lut = torch.tensor(label_perm, dtype=torch.long)
        cls = lut[cls]
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    means, per_ex = [], []
    for _ in range(steps):
        opt.zero_grad()
        losses = F.cross_entropy(model(h, q, cls), gold, reduction="none")
        loss = losses.mean()
        loss.backward()
        opt.step()
        means.append(float(loss.detach()))
        per_ex.append(losses.detach().clone())
    return means, torch.stack(per_ex)


def absorb_wr(model, perm):
    """The full CLASS-INDEXED absorption recipe (recipe-scoped, per spec
    section 3 -- not a claim that no other parameter map exists; the
    per-example trajectory criterion plus the recipe-validity baseline
    carry that weight). With labels relabeled cls' = perm[cls], setting
    W_r' = W_r[argsort(perm)] makes the label channel (and its whole AdamW
    trajectory) identical to the original: W_r'[perm[i]] = W_r[i]. This is
    the complete canonical group action on the only class-indexed
    parameter; A1's S-PERM test confirmed it exact (7.15e-07) when no
    frozen structure blocks it."""
    with torch.no_grad():
        inv = torch.argsort(torch.tensor(perm, dtype=torch.long))
        model.w_r.copy_(model.w_r[inv])
    return model
