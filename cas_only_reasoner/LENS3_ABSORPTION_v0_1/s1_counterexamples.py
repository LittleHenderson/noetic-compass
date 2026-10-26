"""Hunt for parameter settings where a NON-IDENTITY relabelling IS absorbed."""
import itertools, numpy as np
from core import *

perms = list(itertools.permutations(range(K)))
rng = np.random.default_rng(7)
Eb = rng.normal(size=(4096, K, DE))
Ebig = rng.normal(size=(200000, K, DE))   # for exactness stress test


def permute_modules(p, sig):
    return dict(W=p["W"][list(sig)], U=p["U"][list(sig)], b=p["b"][list(sig)], Rd=p["Rd"])


def ranks(p):
    rW = [int(np.linalg.matrix_rank(p["W"][k])) for k in range(K)]
    rU = [int(np.linalg.matrix_rank(p["U"][k])) for k in range(K)]
    nb = [float(np.min(np.abs(p["b"][k]))) for k in range(K)]
    return rW, rU, nb


def report(name, p, E=Eb, note=""):
    base = forward(p, E)
    rW, rU, nb = ranks(p)
    print(f"\n=== {name} {note}")
    print(f"    rank(W_k)={rW}  rank(U_k)={rU}  min|b_k|={['%.3g'%x for x in nb]}")
    print(f"    baseline out rms={np.sqrt(np.mean(base**2)):.6g}  out std over E={np.std(base):.6g}")
    hits = []
    best = (np.inf, None, None)
    for pi in perms[1:]:
        tgt = forward(p, E, assign=np.array(pi))
        for sig in perms:
            q = permute_modules(p, sig)
            v = rel_rmse(forward(q, E), tgt)
            if v < best[0]:
                best = (v, pi, sig)
            if v == 0.0:
                hits.append((pi, sig))
                break
    print(f"    EXACT-ZERO relabelings (rel residual == 0.0 exactly): {len(hits)} of 119")
    if hits:
        print(f"      examples: {hits[:4]}")
    print(f"    best rel residual over 119x120 = {best[0]:.6e}  (relabel={best[1]}, moduleperm={best[2]})")
    return hits, best


print("#" * 78)
print("# C0  GENERIC CONTROL -- random nondegenerate params (the tested regime)")
p0 = rand_params(42)
report("C0 generic", p0)

print("\n" + "#" * 78)
print("# C1  ZEROED EVIDENCE READS: W_k = 0 for k >= 1  (only position 0 reads E)")
p1 = rand_params(42)
p1["W"] = p1["W"].copy()
p1["W"][1:] = 0.0
h1, _ = report("C1 W_k=0 for k>=1", p1)
# verify on a huge held-out set for the fixing-0 relabelings
pi = (0, 2, 1, 4, 3)
print(f"    HELD-OUT 200000 samples, relabel {pi}, identity module perm:")
print(f"      max abs deviation = {np.max(np.abs(forward(p1, Ebig, assign=np.array(pi)) - forward(p1, Ebig))):.6e}")

print("\n" + "#" * 78)
print("# C2  SEVERED CHAIN: U_k = 0 for all k  (only the LAST position reaches the readout)")
p2 = rand_params(42)
p2["U"] = np.zeros_like(p2["U"])
report("C2 U_k=0", p2)

print("\n" + "#" * 78)
print("# C3  SATURATING GATE: every W_k, U_k FULL RANK and nonzero, b_k nonzero.")
print("#     U_1..U_4 scaled by G so tanh saturates to exactly +-1.0 in float64,")
print("#     which makes rows 1..4 unreadable and the output a function of row 0 only.")
G = 1e6
p3 = rand_params(42)
p3["U"] = p3["U"].copy()
p3["U"][1:] *= G
h3, _ = report("C3 saturating gate", p3, note=f"(G={G:g})")
pi = (0, 2, 1, 4, 3)
d = np.abs(forward(p3, Ebig, assign=np.array(pi)) - forward(p3, Ebig))
print(f"    HELD-OUT 200000 samples, relabel {pi}, identity module perm:")
print(f"      max abs deviation = {np.max(d):.6e}   #rows with any deviation = {int(np.sum(np.any(d>0,axis=1)))}")
print(f"    all |W| entries nonzero: {bool(np.all(p3['W']!=0))}   all |U| entries nonzero: {bool(np.all(p3['U']!=0))}")
print(f"    min |singular value| over all W_k = {min(np.linalg.svd(p3['W'][k],compute_uv=False).min() for k in range(K)):.6g}")
print(f"    min |singular value| over all U_k = {min(np.linalg.svd(p3['U'][k],compute_uv=False).min() for k in range(K)):.6g}")

print("\n" + "#" * 78)
print("# C4  ALIGNED RECURRENCE + SMALL SCALE: U_k = I for all k, W,b scaled by s.")
print("#     Continuum family. Every W_k full rank, every U_k full rank (identity).")
print("#     Relabel pi is absorbed by module permutation sig = pi.")
print(f"{'s':>10} {'rel residual':>16} {'abs residual':>16} {'out rms':>14}")
p4t = rand_params(42)
I = np.eye(H)
for s in [1.0, 3e-1, 1e-1, 3e-2, 1e-2, 3e-3, 1e-3, 3e-4, 1e-4, 3e-5, 1e-5, 1e-6, 1e-7, 1e-8, 1e-9]:
    p4 = dict(W=s * p4t["W"], U=np.stack([I] * K), b=s * p4t["b"], Rd=p4t["Rd"])
    pi = (1, 2, 3, 4, 0)
    tgt = forward(p4, Eb, assign=np.array(pi))
    # compensating module permutation: new W at position k := W from position pi[k]
    q = permute_modules(p4, pi)
    print(f"{s:10.1e} {rel_rmse(forward(q,Eb),tgt):16.6e} {abs_rmse(forward(q,Eb),tgt):16.6e} {np.sqrt(np.mean(tgt**2)):14.6e}")

print("\n    same family, worst case over all 119 relabelings, s=1e-6:")
s = 1e-6
p4 = dict(W=s * p4t["W"], U=np.stack([I] * K), b=s * p4t["b"], Rd=p4t["Rd"])
worst = 0.0
nz = 0
for pi in perms[1:]:
    tgt = forward(p4, Eb, assign=np.array(pi))
    v = rel_rmse(forward(permute_modules(p4, pi), Eb), tgt)
    worst = max(worst, v)
    if v == 0.0:
        nz += 1
print(f"      worst rel residual over 119 relabelings = {worst:.6e}; exactly-zero count = {nz}/119")
print(f"      baseline out std = {np.std(forward(p4,Eb)):.6e} (non-constant in E)")
