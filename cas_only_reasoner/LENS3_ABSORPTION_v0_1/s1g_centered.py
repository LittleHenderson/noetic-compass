"""HONESTY CHECK on every counterexample.
rel_rmse divides by ||target||_F, which INCLUDES the constant (bias-driven) part of the
output. A near-constant model would look absorbed for a trivial reason. Re-score every
counterexample with a CENTRED metric that divides by the E-dependent variation only:
      cen(A,B) = ||A-B||_F / ||B - mean_E(B)||_F
Also report var_frac = ||B-mean||_F^2 / ||B||_F^2  (how much of the output actually moves
with E). A counterexample only counts if var_frac is not tiny AND cen is small."""
import itertools, numpy as np
from core import *

perms=list(itertools.permutations(range(K)))
Ete=np.random.default_rng(22).normal(size=(4096,K,DE))
def pm(p,sig): return dict(W=p["W"][list(sig)],U=p["U"][list(sig)],b=p["b"][list(sig)],Rd=p["Rd"])
def inv(pi):
    q=[0]*len(pi)
    for k,t in enumerate(pi): q[t]=k
    return tuple(q)
def cen(A,B):
    Bc=B-B.mean(0,keepdims=True)
    return float(np.sqrt(np.sum((A-B)**2)/np.sum(Bc**2)))
def varfrac(B):
    Bc=B-B.mean(0,keepdims=True)
    return float(np.sum(Bc**2)/np.sum(B**2))

def score(name,p):
    rel=[];ce=[]
    for pi in perms[1:]:
        tgt=forward(p,Ete,assign=np.array(pi))
        bv,bc=np.inf,np.inf
        for sig in perms:
            o=forward(pm(p,sig),Ete)
            v=rel_rmse(o,tgt)
            if v<bv: bv,bc=v,cen(o,tgt)
        rel.append(bv);ce.append(bc)
    rel=np.array(rel);ce=np.array(ce)
    vf=varfrac(forward(p,Ete))
    print(f"{name:<34} var_frac={vf:7.4f}  rel[min/med/MAX]={rel.min():.3e}/{np.median(rel):.3e}/{rel.max():.3e}"
          f"  cen[min/med/MAX]={ce.min():.3e}/{np.median(ce):.3e}/{ce.max():.3e}")

I=np.eye(H); base=rand_params(42)
score("GENERIC control (seed 42)", base)
p1=rand_params(42); p1["W"]=p1["W"].copy(); p1["W"][1:]=0.0
score("C1 W_k=0 for k>=1", p1)
p2=rand_params(42); p2["U"]=np.zeros_like(p2["U"])
score("C2 U_k=0", p2)
p3=rand_params(42); p3["U"]=p3["U"].copy(); p3["U"][1:]*=1e6
score("C3 saturating gate G=1e6", p3)
for s in [1e-2,1e-4,1e-10]:
    p4=dict(W=s*base["W"],U=np.stack([I]*K),b=s*base["b"],Rd=base["Rd"]/s)
    score(f"C4 U=I, s={s:g}, Rd/s", p4)
