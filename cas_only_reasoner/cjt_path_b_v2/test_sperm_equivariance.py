"""test_sperm_equivariance.py -- S-PERM as an IMPLEMENTATION-CONFORMANCE test
(owner v0.3 ruling: 'implementation-equivariance check only; not a scientific
opponent; test with paired parameter and optimizer-state permutation').

Theorem under test: with profiles entering the frozen P1.3 MixtureHead only
through s += lam * (W_r g . p), a global class permutation P satisfies
(P W_r g) . (P p) = (W_r g) . p. Therefore the run (profiles=P p, W_r'=P W_r,
optimizer state permuted to match) must reproduce the base run EXACTLY:
identical logits, losses, gradients (after inverse permutation), and parameter
trajectories, to frozen numerical tolerance, over several optimizer steps on
identical batches.

SYNTHETIC-CONFORMANCE posture: synthetic CPU tensors, no model, no GPU, no
dataset -- a software math proof, not a neural workload.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / "cjt_dev_gpu_pilot_v1"
sys.path.insert(0, str(PILOT))
sys.path.insert(0, str(HERE))

TOL = 1e-5
STEPS = 5
PERM = [2, 0, 3, 1]                                   # a nontrivial 4-perm


def main():
    import torch
    from run_pilot_v3 import build_mixture_head
    torch.manual_seed(7)

    B, N, C, D = 4, 6, 9, 896
    batches = []
    for _ in range(STEPS):
        h = torch.randn(B, N, D)
        g = torch.randn(B, D)
        p = torch.softmax(torch.randn(B, N, 4), dim=-1)
        idea_mask = torch.ones(B, N, dtype=torch.bool)
        e_loc = torch.randn(B, N, C, D)
        m_loc = torch.rand(B, N, C) > 0.4
        m_loc[:, :, 0] = True                          # every clause non-empty
        cand_mask = torch.ones(B, C, dtype=torch.bool)
        tgt = torch.randint(0, C, (B,))
        batches.append((h, g, p, idea_mask, e_loc, m_loc, cand_mask, tgt))

    def make(seed):
        torch.manual_seed(seed)
        head = build_mixture_head(True, 0).float()
        opt = torch.optim.AdamW(head.parameters(), lr=1e-3,
                                betas=(0.9, 0.999), weight_decay=0.01)
        return head, opt

    base_head, base_opt = make(11)
    perm_head, perm_opt = make(11)                     # identical init
    P = torch.tensor(PERM)
    with torch.no_grad():                              # W_r' = P W_r
        perm_head.w_r.weight.copy_(base_head.w_r.weight[P])
        perm_head.w_r.bias.copy_(base_head.w_r.bias[P])

    nll = torch.nn.NLLLoss()
    max_dev = 0.0
    for step, (h, g, p, im, el, ml, cm, tgt) in enumerate(batches):
        lp_b = base_head(h, g, p, im, el, ml, cm)
        lp_p = perm_head(h, g, p[:, :, P], im, el, ml, cm)
        d_log = float((lp_b - lp_p).abs().max())
        loss_b = nll(lp_b, tgt)
        loss_p = nll(lp_p, tgt)
        d_loss = abs(float(loss_b) - float(loss_p))
        base_opt.zero_grad(set_to_none=True)
        loss_b.backward()
        perm_opt.zero_grad(set_to_none=True)
        loss_p.backward()
        # relation: perm.weight[i] = base.weight[P[i]]  =>  base row j
        # corresponds to perm row inv[j] with inv = argsort(P); the same
        # relation holds for gradients and optimizer trajectories.
        inv = torch.argsort(P)
        d_grad = float((base_head.w_r.weight.grad
                        - perm_head.w_r.weight.grad[inv]).abs().max())
        d_other = max(float((a.grad - b.grad).abs().max())
                      for (na, a), (nb, b) in zip(
                          base_head.named_parameters(),
                          perm_head.named_parameters())
                      if a.grad is not None and not na.startswith("w_r"))
        base_opt.step()
        perm_opt.step()
        d_par = float((base_head.w_r.weight - perm_head.w_r.weight[inv])
                      .abs().max())
        dev = max(d_log, d_loss, d_grad, d_other, d_par)
        max_dev = max(max_dev, dev)
        print(f"step {step}: dlogits={d_log:.2e} dloss={d_loss:.2e} "
              f"dgrad_wr={d_grad:.2e} dgrad_other={d_other:.2e} "
              f"dparam_wr={d_par:.2e}")
    verdict = "SPERM_EQUIVARIANCE_CONFIRMED" if max_dev <= TOL \
        else "SPERM_EQUIVARIANCE_VIOLATED"
    print(f"\n{verdict} (max deviation {max_dev:.3e}, tol {TOL})")
    return 0 if max_dev <= TOL else 4


if __name__ == "__main__":
    raise SystemExit(main())
