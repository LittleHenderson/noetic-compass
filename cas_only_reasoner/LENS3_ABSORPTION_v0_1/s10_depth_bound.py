"""How far does the optimiser-free bound reach? The Jacobian w.r.t. the evidence row sitting
at depth d from the end passes through d tanh layers, so its span has dimension <= H^d.
The bound bites only while H^d < DE*ACT. Check which relabelings it can actually rule out."""
import numpy as np
from core import rand_params, fwd_cache

def jac_row(p,E,assign,row,DE,ACT):
    Kk=p["W"].shape[0]; N=E.shape[0]
    out,hs=fwd_cache(p,E,assign)
    J=np.zeros((N,DE,ACT))
    for a in range(ACT):
        gh=np.tile(p["Rd"][:,a],(N,1)); acc=np.zeros((N,DE))
        for k in range(Kk-1,-1,-1):
            ga=gh*(1.0-hs[k+1]**2)
            if assign[k]==row: acc+=ga@p["W"][k].T
            gh=ga@p["U"][k].T
        J[:,:,a]=acc
    return J
def nr(J):
    M=J.reshape(J.shape[0],-1); s=np.linalg.svd(M,compute_uv=False)
    return int(np.sum(s>1e-8*s[0]))
K,DE,H,ACT=5,10,5,10
p=rand_params(42,K=K,DE=DE,H=H,ACT=ACT)
E=np.random.default_rng(31).normal(size=(4000,K,DE))
print(f"K={K} DE={DE} H={H} ACT={ACT}, ambient DE*ACT={DE*ACT}; theoretical bound at depth d is H^d")
print(f"{'assign':<20} " + " ".join(f"row{r:>2}" for r in range(K)))
for name,a in [("identity",np.arange(K)),
               ("(1,0,2,3,4) front swap",np.array([1,0,2,3,4])),
               ("(0,1,2,4,3) back swap",np.array([0,1,2,4,3])),
               ("(1,2,3,4,0) 5-cycle",np.array([1,2,3,4,0]))]:
    print(f"{name:<20} " + " ".join(f"{nr(jac_row(p,E,a,r,DE,ACT)):>5}" for r in range(K)))
print("\ndepth of each row (positions from the end), and the bound H^depth:")
for name,a in [("identity",np.arange(K)),("(1,0,2,3,4)",np.array([1,0,2,3,4])),
               ("(0,1,2,4,3)",np.array([0,1,2,4,3])),("(1,2,3,4,0)",np.array([1,2,3,4,0]))]:
    d=[K-int(np.where(a==r)[0][0]) for r in range(K)]
    print(f"{name:<14} depths={d}  bounds={[H**x for x in d]}")
