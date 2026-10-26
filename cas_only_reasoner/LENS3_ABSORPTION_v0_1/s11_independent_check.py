"""Independent re-implementation of the forward pass (naive per-sample python loops,
no batching, no fancy indexing) to make sure the exact zeros are not an artefact of the
vectorised code."""
import numpy as np
from core import rand_params, forward, K, DE, H, ACT

def naive(p, e, assign):
    """e: (K,DE) single sample."""
    h = [0.0]*H
    for k in range(K):
        a = [p["b"][k][j] for j in range(H)]
        t = assign[k]
        for j in range(H):
            for i in range(DE):
                a[j] += e[t][i]*p["W"][k][i][j]
            for i in range(H):
                a[j] += h[i]*p["U"][k][i][j]
        h = [np.tanh(x) for x in a]
    return [sum(h[i]*p["Rd"][i][a_] for i in range(H)) for a_ in range(ACT)]

p = rand_params(42); p["W"]=p["W"].copy(); p["W"][1:4]=0.0
rng=np.random.default_rng(777)
Es=rng.normal(size=(200,K,DE))
pi=[0,1,3,2,4]; sig=[0,1,2,3,4]
mx_vec_vs_naive=0.0; mx_absorption=0.0
for n in range(200):
    e=Es[n]
    a=naive(p,e,pi)                       # relabelled model, naive
    b=naive(p,e,sig)                      # baseline (identity module perm), naive
    v=forward(p,Es[n:n+1],assign=np.array(pi))[0]
    mx_vec_vs_naive=max(mx_vec_vs_naive, float(np.max(np.abs(np.array(a)-v))))
    mx_absorption=max(mx_absorption, float(np.max(np.abs(np.array(a)-np.array(b)))))
print("C5 (W_1=W_2=W_3=0), relabel pi=(0,1,3,2,4), identity module permutation")
print(f"  vectorised vs naive forward, max abs diff over 200 samples = {mx_vec_vs_naive:.3e}")
print(f"  NAIVE absorption residual (max abs) over 200 samples        = {mx_absorption:.3e}")
# and the same for the generic model, which must NOT be zero
g=rand_params(42)
mx=0.0
for n in range(50):
    mx=max(mx, float(np.max(np.abs(np.array(naive(g,Es[n],pi))-np.array(naive(g,Es[n],sig))))))
print(f"  same check on the GENERIC model (must be nonzero)           = {mx:.3e}")
