"""Is 'rank 5' vs 'rank 20' a tolerance artefact? Print the full normalised spectrum."""
import numpy as np
from core import *
def jac(p,E,assign):
    Kk=p["W"].shape[0]; N=E.shape[0]; A=p["Rd"].shape[1]
    out,hs=fwd_cache(p,E,assign)
    J=np.zeros((N,DE,A))
    for a in range(A):
        gh=np.tile(p["Rd"][:,a],(N,1)); acc=np.zeros((N,DE))
        for k in range(Kk-1,-1,-1):
            ga=gh*(1.0-hs[k+1]**2)
            if assign[k]==Kk-1: acc+=ga@p["W"][k].T
            gh=ga@p["U"][k].T
        J[:,:,a]=acc
    return J
P=rand_params(42); E=np.random.default_rng(31).normal(size=(3000,K,DE))
for name,a in [("identity",np.arange(K)),("5-cycle (1,2,3,4,0)",np.array([1,2,3,4,0]))]:
    M=jac(P,E,a).reshape(3000,-1); s=np.linalg.svd(M,compute_uv=False); s=s/s[0]
    print(f"{name}:")
    print("  " + " ".join(f"{x:.2e}" for x in s))
    print(f"  ratio sv5/sv6 = {s[4]/s[5]:.3e}   smallest sv = {s[-1]:.3e}")
