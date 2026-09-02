"""VERIFY B1 myself: is the gold identifiable from TWO-HOP graph mass alone, with no phase,
no dynamics, and no knowledge of which chains are active?

Uses throwaway world ids (900000+) so no CMB-P2 dev or held-out world is touched.
"""
import sys, torch
sys.path.insert(0, r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\CMB_P2_v0_1")
sys.path.insert(0, r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\CMB_P1_v0_1")
sys.path.insert(0, r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\CMB_P0_v0_1")
import cmb_p0 as P0, cmb_p1 as P1, run_cmb_p2 as R
P0.require_cuda()
W = tuple(range(900000, 900006))

print("STEP 1 -- is the CANDIDATE SET (the completions) recoverable from adjacency alone?")
for k in (2, 3):
    ok = 0
    for wid in W:
        w = P1.build_world_p1(wid, k)
        deg1 = ((w["A"] - 1.0).abs() < 1e-12).sum(0)     # count of weight-1.0 edges
        cand = (deg1 == w["pool"]).nonzero(as_tuple=True)[0]
        ok += int(cand.numel() == w["pool"] and bool(
            (torch.sort(cand).values == torch.sort(w["completions"]).values).all()))
    print(f"   K={k}: exactly recovered in {ok}/{len(W)} worlds  (no seeds, no labels)")

print("\nSTEP 2 -- one hop is flat, but is TWO hops?")
w = P1.build_world_p1(900000, 3); A = w["A"]
c0 = int(w["cues"][0]); comps = w["completions"]
print(f"   A [cue0, completions] = {[round(float(x),4) for x in A[c0, comps]]}")
A2 = A @ A
print(f"   A2[cue0, completions] = {[round(float(x),4) for x in A2[c0, comps]]}")
print(f"   gold for cue0 is completion index 0 -> {float(A2[c0, comps[0]]):.4f} vs max rival "
      f"{float(A2[c0, comps[1:]].max()):.4f}")

print("\nSTEP 3 -- how well does a PHASE-FREE two-hop rule score, vs P0 and the ORACLE?")
print(f"{'K':>3}{'P0':>10}{'ORACLE':>10}{'B_TWOHOP':>11}{'TWOHOP*amp':>12}")
for k in (2, 3):
    p0v, orc, bt, bta = [], [], [], []
    for wid in W:
        w = P1.build_world_p1(wid, k); q = P0.build_queries(w)
        ar = torch.arange(P0.QUERIES_PER_WORLD, device=P0.DEV)
        scal = P0.propagate_scalar(q["seeds"], w["W"])
        p0v.append(R.score_world(w, q, scal)["top1"])
        ch = w["memb"].unsqueeze(0)*q["active_mask"].unsqueeze(-1).to(P0.DT)
        ch[ar, q["target"], q["cue"]] += 1.0
        orc.append(R.score_world(w, q, P0.propagate_channels(ch, w["W"])[ar, q["target"]])["top1"])
        deg1 = ((w["A"]-1.0).abs() < 1e-12).sum(0)
        cand = (deg1 == w["pool"]).nonzero(as_tuple=True)[0]
        mask = torch.full((P0.N_NODES,), -1e18, device=P0.DEV, dtype=P0.DT); mask[cand] = 0.0
        two = (w["A"] @ w["A"])[q["cue"]]
        bt.append(R.score_world(w, q, two + mask)["top1"])
        bta.append(R.score_world(w, q, scal*two + mask)["top1"])
    m = lambda x: sum(x)/len(x)
    print(f"{k:>3}{m(p0v):>10.4f}{m(orc):>10.4f}{m(bt):>11.4f}{m(bta):>12.4f}")
print("\nThrowaway worlds 900000+. No CMB-P2 dev or held-out world was read.")
