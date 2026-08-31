"""arms.py -- the FROZEN S0-S7 head modules + the deterministic capacity matcher.

One module class (ArmHead) parameterized by exactly two structural flags; every
profile-bearing arm (S2-S7) is the IDENTICAL module -- arms differ only in the
profile SOURCE supplied at assembly time (exec/labels.py) and in whether
attention is learned. That makes the structural-identity laws checkable:
S6 and S7 are the same nn.Module configuration as S3 (state-dict keys and
shapes equal); they receive different profile inputs.

Shapes (CJT_T1_STATIC_NEURAL_ARCHITECTURE.md):
    W_q, W_k: 896 -> 64      (learned Idea attention)
    W_p:      4   -> 64      (profile lift)
    MLP:      (896 [+64] + 896) -> 256 -> 256, GELU between
    widening: 256 -> w -> 256, GELU (capacity matching only; w=0 means absent)
    W_o:      256 -> 256
    W_c:      896 -> 256     (candidate projection; context-free encodings)
    score(e) = dot(W_o z, W_c enc(e)) over the passage's closed candidate set
"""
from __future__ import annotations

D_MODEL, D_ATT, D_PROF, D_HID, N_CLASSES, MAX_IDEAS = 896, 64, 64, 256, 4, 6

ARM_IDS = ("S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7")

# structural flags per arm -- S4/S5/S6/S7 are structurally EXACTLY S3
ARM_STRUCT = {
    "S0": {"attention": False, "profiles": False},
    "S1": {"attention": True, "profiles": False},
    "S2": {"attention": False, "profiles": True},
    "S3": {"attention": True, "profiles": True},
    "S4": {"attention": True, "profiles": True},
    "S5": {"attention": True, "profiles": True},
    "S6": {"attention": True, "profiles": True},
    "S7": {"attention": True, "profiles": True},
}

CAPACITY_TOLERANCE = 0.01     # +/-1% of S3's trainable count (frozen)


def build_arm_head(arm_id: str, widen_w: int = 0):
    import torch.nn as nn

    class ArmHead(nn.Module):
        def __init__(self, use_attention: bool, use_profiles: bool, w: int):
            super().__init__()
            self.use_attention, self.use_profiles = use_attention, use_profiles
            if use_attention:
                self.w_q = nn.Linear(D_MODEL, D_ATT)
                self.w_k = nn.Linear(D_MODEL, D_ATT)
            if use_profiles:
                self.w_p = nn.Linear(N_CLASSES, D_PROF)
            in_dim = D_MODEL + (D_PROF if use_profiles else 0) + D_MODEL
            self.mlp = nn.Sequential(nn.Linear(in_dim, D_HID), nn.GELU(),
                                     nn.Linear(D_HID, D_HID))
            self.widen = (nn.Sequential(nn.Linear(D_HID, w), nn.GELU(),
                                        nn.Linear(w, D_HID))
                          if w > 0 else None)
            self.w_o = nn.Linear(D_HID, D_HID)
            self.w_c = nn.Linear(D_MODEL, D_HID)

        def forward(self, h, g, p, idea_mask, cand_enc, cand_mask):
            """h (B,N,896)  g (B,896)  p (B,N,4) or None  idea_mask (B,N) bool
            cand_enc (B,C,896)  cand_mask (B,C) bool  ->  logits (B,C),
            masked-out candidates at -inf."""
            import torch
            neg = torch.finfo(h.dtype).min
            if self.use_attention:
                scores = (self.w_q(g).unsqueeze(1) * self.w_k(h)).sum(-1) / (D_ATT ** 0.5)
                scores = scores.masked_fill(~idea_mask, neg)
                alpha = torch.softmax(scores, dim=1)
            else:
                alpha = idea_mask.float()
                alpha = alpha / alpha.sum(dim=1, keepdim=True)
            c = (alpha.unsqueeze(-1) * h).sum(dim=1)
            feats = [c]
            if self.use_profiles:
                q = (alpha.unsqueeze(-1) * p).sum(dim=1)      # q = alpha^T P
                feats.append(self.w_p(q))
            feats.append(g)
            z = self.mlp(torch.cat(feats, dim=-1))
            if self.widen is not None:
                z = self.widen(z)
            u = self.w_o(z)
            logits = (self.w_c(cand_enc) * u.unsqueeze(1)).sum(-1)
            return logits.masked_fill(~cand_mask, neg)

    s = ARM_STRUCT[arm_id]
    return ArmHead(s["attention"], s["profiles"], widen_w)


def trainable_param_count(module) -> int:
    return sum(p.numel() for p in module.parameters() if p.requires_grad)


def match_capacity(arm_id: str, reference_count: int = None) -> int:
    """Deterministic capacity matcher: the SMALLEST integer w >= 0 whose widening
    pair puts the arm within +/-1% of S3's trainable count (w searched ascending
    from 0; frozen in CJT_T1_STATIC_NEURAL_ARCHITECTURE.md)."""
    if reference_count is None:
        reference_count = trainable_param_count(build_arm_head("S3", 0))
    for w in range(0, 4096):
        count = trainable_param_count(build_arm_head(arm_id, w))
        if abs(count - reference_count) <= CAPACITY_TOLERANCE * reference_count:
            return w
    raise RuntimeError(f"CAPACITY_MATCH_FAILURE: no w<4096 matches {arm_id}")


def matched_heads():
    """{arm_id: (module, widen_w, trainable_count)} for all 8 arms, matched."""
    ref = trainable_param_count(build_arm_head("S3", 0))
    out = {}
    for arm in ARM_IDS:
        w = 0 if ARM_STRUCT[arm] == ARM_STRUCT["S3"] else match_capacity(arm, ref)
        m = build_arm_head(arm, w)
        out[arm] = (m, w, trainable_param_count(m))
    return out
