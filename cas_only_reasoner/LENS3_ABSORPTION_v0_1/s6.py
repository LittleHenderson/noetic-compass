import numpy as np
from core import *
def jac_last_row(p,E,assign=None):
    Kk=p["W"].shape[0]
    if assign is None: assign=np.arange(Kk)
    N=E.shape[0]; A=p["Rd"].shape[1]
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
def nr(J,tol=1e-8):
    M=J.reshape(J.shape[0],-1); s=np.linalg.svd(M,compute_uv=False)
    return int(np.sum(s>tol*s[0])), s/s[0]
E=np.random.default_rng(31).normal(size=(3000,K,DE))
base=rand_params(42); I=np.eye(H)
pi=np.array([1,2,3,4,0])
print("Jacobian-span dimension of the RELABELLED function pi=(1,2,3,4,0), tol=1e-8 relative")
print(f"{'parameter setting':<38} {'rank':>5}  {'sv6..sv9 (normalised)':>34}")
cases={}
cases["GENERIC (seed 42)"]=base
p=rand_params(42); p["W"]=p["W"].copy(); p["W"][1:]=0.0; cases["C1 W_k=0 k>=1"]=p
p=rand_params(42); p["U"]=np.zeros_like(p["U"]); cases["C2 U_k=0"]=p
for s in [1e-1,1e-2,1e-4,1e-8]:
    cases[f"C4 U=I, ||W||_F={s*3.9274:.3e}"]=dict(W=s*base["W"],U=np.stack([I]*K),b=s*base["b"],Rd=base["Rd"]/s)
for name,p in cases.items():
    r,sn=nr(jac_last_row(p,E,pi))
    print(f"{name:<38} {r:>5}  " + " ".join(f"{x:.2e}" for x in sn[5:9]))
