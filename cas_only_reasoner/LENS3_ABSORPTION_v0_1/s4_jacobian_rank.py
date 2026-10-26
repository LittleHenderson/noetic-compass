"""OPTIMISER-FREE necessary condition for representability.

For ANY member of the class with hidden width H', the LAST chain position is the only
place row K-1 enters, additively inside the final tanh:
    out(E) = tanh( E_{K-1} W'_{K-1} + z(E_0..E_{K-2}) + b' ) Rd'
Therefore the Jacobian of out w.r.t. row K-1 is
    J(E) = W'_{K-1} diag(1 - tanh^2(x)) Rd'          (shape DE x ACT)
which, as E varies, always lies in the LINEAR SPAN of the H' matrices
    W'_{K-1} e_i e_i^T Rd',  i = 1..H'.
So: dim span{ J(E) : E }  <=  H'.
This is a THEOREM about the class, not a fit. Measuring that dimension for a target
function gives a hard LOWER BOUND on the hidden width any exact representation needs.
"""
import numpy as np
from core import *

def jac_last_row(p, E, assign=None):
    """exact d out / d E[:, K-1, :]  -> (N, DE, ACT)"""
    Kk=p["W"].shape[0]
    if assign is None: assign=np.arange(Kk)
    N=E.shape[0]; Hh=p["W"].shape[2]; A=p["Rd"].shape[1]
    out,hs=fwd_cache(p,E,assign)
    J=np.zeros((N,DE,A))
    for a in range(A):
        gh=np.tile(p["Rd"][:,a],(N,1))                 # d out_a / d h_{K-1}
        acc=np.zeros((N,DE))
        for k in range(Kk-1,-1,-1):
            ga=gh*(1.0-hs[k+1]**2)
            if assign[k]==Kk-1:                        # this position reads row K-1
                acc+=ga@p["W"][k].T
            gh=ga@p["U"][k].T
        J[:,:,a]=acc
    return J

def numrank(J, tol=1e-8):
    M=J.reshape(J.shape[0],-1)
    s=np.linalg.svd(M,compute_uv=False)
    return int(np.sum(s>tol*s[0])), s

P=rand_params(42)
E=np.random.default_rng(31).normal(size=(3000,K,DE))
print(f"ambient dimension DE*ACT = {DE*ACT};  class bound = H' (hidden width used by the fit)")
print(f"baseline hidden width H = {H}\n")

# sanity: check the analytic Jacobian against finite differences
h=1e-6; Es=E[:5].copy()
Ja=jac_last_row(P,Es)
Jn=np.zeros_like(Ja)
for j in range(DE):
    Ep=Es.copy(); Ep[:,K-1,j]+=h
    Em=Es.copy(); Em[:,K-1,j]-=h
    Jn[:,j,:]=(forward(P,Ep)-forward(P,Em))/(2*h)
print(f"Jacobian check vs finite differences: max abs err = {np.max(np.abs(Ja-Jn)):.3e}\n")

def rep(name,J):
    r,s=numrank(J)
    sn=s/s[0]
    print(f"{name:<40} numerical rank={r:3d}   top-8 normalised sv: "
          + " ".join(f"{x:.2e}" for x in sn[:8]))
    return r

rep("baseline, assign = identity", jac_last_row(P,E))
for pi in [(1,0,2,3,4),(0,1,2,4,3),(1,2,3,4,0),(4,3,2,1,0),(2,0,4,1,3)]:
    rep(f"relabelled, pi={pi}", jac_last_row(P,E,np.array(pi)))
print()
print("interpretation: rank r means NO member of this architecture class with hidden")
print("width H' < r can represent the function exactly.  H' >= r is necessary.")
