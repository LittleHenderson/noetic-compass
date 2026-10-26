"""C4 rerun. Earlier run used the WRONG compensating permutation (sig=pi instead of
sig=pi^-1). Redone with a FULL search over all 120 module permutations."""
import itertools, time, numpy as np
from core import *

perms = list(itertools.permutations(range(K)))
rng = np.random.default_rng(7)
Eb = rng.normal(size=(1024, K, DE))


def permute_modules(p, sig):
    return dict(W=p["W"][list(sig)], U=p["U"][list(sig)], b=p["b"][list(sig)], Rd=p["Rd"])


base = rand_params(42)
I = np.eye(H)
print("C4  U_k = I (full rank, cond 1) for all k;  W,b scaled by s;  Rd untouched.")
print("    compensating map searched over ALL 120 module permutations.")
print(f"{'s':>9} {'best rel res':>14} {'abs res':>13} {'out rms':>12} {'argmin sig':>16} {'#exact0/119':>12}")
for s in [1.0, 1e-1, 1e-2, 1e-3, 1e-4, 1e-5, 1e-6, 1e-7, 1e-8, 1e-9, 1e-10]:
    p = dict(W=s * base["W"], U=np.stack([I] * K), b=s * base["b"], Rd=base["Rd"])
    bestv, bestsig, nz = np.inf, None, 0
    for pi in perms[1:]:
        tgt = forward(p, Eb, assign=np.array(pi))
        loc = np.inf
        for sig in perms:
            v = rel_rmse(forward(permute_modules(p, sig), Eb), tgt)
            loc = min(loc, v)
            if v < bestv:
                bestv, bestsig, bestpi = v, sig, pi
        if loc == 0.0:
            nz += 1
    tgt = forward(p, Eb, assign=np.array(bestpi))
    a = abs_rmse(forward(permute_modules(p, bestsig), Eb), tgt)
    print(f"{s:9.0e} {bestv:14.6e} {a:13.6e} {np.sqrt(np.mean(tgt**2)):12.4e} "
          f"{str(bestsig):>16} {nz:12d}")

# does the identity-U requirement matter? control: U_k = random full rank, same scaling
print("\nCONTROL C4c: same scaling s but U_k RANDOM full rank (not aligned to identity)")
print(f"{'s':>9} {'best rel res':>14}")
for s in [1.0, 1e-2, 1e-4, 1e-6, 1e-8]:
    p = dict(W=s * base["W"], U=base["U"], b=s * base["b"], Rd=base["Rd"])
    bestv = np.inf
    for pi in perms[1:]:
        tgt = forward(p, Eb, assign=np.array(pi))
        for sig in perms:
            bestv = min(bestv, rel_rmse(forward(permute_modules(p, sig), Eb), tgt))
    print(f"{s:9.0e} {bestv:14.6e}")

# timing probe for the fit script
t0 = time.time()
Et = np.random.default_rng(3).normal(size=(4000, K, DE))
T = forward(base, Et)
for _ in range(200):
    grads(base, Et, T)
print(f"\ngrad call time at N=4000: {(time.time()-t0)/200*1000:.3f} ms")
