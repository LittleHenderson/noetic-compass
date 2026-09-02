"""Is the phase-shuffle control INFORMATIVE, or does it collapse no matter what?

A control that always fails proves nothing. The test: shuffling should be a NO-OP when the
phase field carries no structure (all phases equal -> cos = 1 everywhere -> score = amplitude
= P0), and destructive in proportion to how much structure the field actually has.

DEV WORLDS ONLY (500-505). Held-out 506-535 untouched. NO MEASUREMENT RECORDED.
"""
import sys, math, torch
sys.path.insert(0, r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\CMB_P2_v0_1")
sys.path.insert(0, r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\CMB_P1_v0_1")
sys.path.insert(0, r"C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\CMB_P0_v0_1")
import cmb_p0 as P0, cmb_p1 as P1, run_cmb_p2 as R
P0.require_cuda()

print("Does shuffling collapse EVEN WHEN the phase field carries no structure?")
print(f"{'phase field':>34}{'P0':>9}{'unshuffled':>12}{'SHUFFLED':>10}{'gap':>9}{'coh std':>9}")
for k in (2, 3):
    print(f"  --- K={k} ---")
    for label, om, forced_uniform in (("A. FORCED UNIFORM (no structure)", "ZERO", True),
                                      ("B. zero omega, converged", "ZERO", False),
                                      ("C. spectral omega (the arm)", "SPECTRAL", False)):
        p0v, un, sh, cs = [], [], [], []
        for wid in P0.DEV_WORLDS:
            w = P1.build_world_p1(wid, k); q = P0.build_queries(w)
            ar = torch.arange(P0.QUERIES_PER_WORLD, device=P0.DEV)
            p0v.append(R.score_world(w, q, P0.propagate_scalar(q["seeds"], w["W"]))["top1"])
            omega = None if om == "ZERO" else P1.omega_field(w, om)
            a, th, coh, pair = P1.run_phase_acc(w, q, omega=omega, substeps=200)
            if forced_uniform:
                coh = torch.ones_like(coh)          # the no-structure limit, exactly
            perm = torch.randperm(P0.N_NODES, generator=P0.gen(w["key"]+"|p2shuf"), device=P0.DEV)
            un.append(R.score_world(w, q, a*coh.clamp_min(0))["top1"])
            sh.append(R.score_world(w, q, a*coh[:, perm].clamp_min(0))["top1"])
            cs.append(float(coh.std()))
        m = lambda x: sum(x)/len(x)
        print(f"{label:>34}{m(p0v):>9.3f}{m(un):>12.3f}{m(sh):>10.3f}{m(un)-m(sh):>9.3f}{m(cs):>9.4f}")
print()
print("Reading: row A is the no-information limit. If SHUFFLED there equals P0, the control is")
print("a NO-OP when there is nothing to destroy -- which is what makes it informative.")
print("DEV ONLY. NO MEASUREMENT RECORDED.")
