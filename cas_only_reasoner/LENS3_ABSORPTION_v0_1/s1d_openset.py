"""Is the absorbing region a measure-zero curiosity, or does it have NONEMPTY INTERIOR
at a given tolerance?  Perturb away from U_k = I by delta*R_k (R_k random N(0,1)) and
away from s.  If residual stays under tau for delta>0 then the set of tau-absorbable
parameters is OPEN and non-empty -- 'generic' cannot be strengthened to 'robust'."""
import itertools, numpy as np
from core import *

perms = list(itertools.permutations(range(K)))
Eb = np.random.default_rng(7).normal(size=(512, K, DE))
base = rand_params(42)
R = np.random.default_rng(5).normal(size=(K, H, H))
I = np.eye(H)

def permute_modules(p, sig):
    return dict(W=p["W"][list(sig)], U=p["U"][list(sig)], b=p["b"][list(sig)], Rd=p["Rd"])

s = 1e-4
print(f"perturbation off the absorbing set: U_k = I + delta*R_k, W,b scale s={s:g},")
print("Rd rescaled by 1/s so output rms is O(1). MAX over all 119 relabelings.")
print(f"{'delta':>10} {'out rms':>10} {'min rel':>12} {'MAX rel':>12} {'min sv(U)':>11} {'cond(U)':>10}")
for delta in [0.0, 1e-12, 1e-9, 1e-6, 1e-4, 1e-3, 1e-2, 1e-1, 0.3, 1.0]:
    U = np.stack([I + delta * R[k] for k in range(K)])
    p = dict(W=s*base["W"], U=U, b=s*base["b"], Rd=base["Rd"]/s)
    vals=[]
    for pi in perms[1:]:
        tgt = forward(p, Eb, assign=np.array(pi))
        loc = min(rel_rmse(forward(permute_modules(p,sig),Eb), tgt) for sig in perms)
        vals.append(loc)
    vals=np.array(vals)
    sv=[np.linalg.svd(U[k],compute_uv=False) for k in range(K)]
    print(f"{delta:10.0e} {np.sqrt(np.mean(forward(p,Eb)**2)):10.3f} {vals.min():12.4e} "
          f"{vals.max():12.4e} {min(x.min() for x in sv):11.4f} {max(x.max()/x.min() for x in sv):10.3f}")
