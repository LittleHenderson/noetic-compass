"""Corrected 'chainness' probe: distance from the chain model to the ORDER-FREE model
built from the SAME W,b,Rd (best scalar rescale allowed). Small = the chain has stopped
using its own order."""
import itertools, numpy as np
from core import *
perms=list(itertools.permutations(range(K)))
E=np.random.default_rng(22).normal(size=(2048,K,DE))
def pm(p,sig): return dict(W=p["W"][list(sig)],U=p["U"][list(sig)],b=p["b"][list(sig)],Rd=p["Rd"])
def cen(A,B):
    Bc=B-B.mean(0,keepdims=True); return float(np.sqrt(np.sum((A-B)**2)/np.sum(Bc**2)))
def flat(p,E):
    tot=0.0
    for k in range(K): tot=tot+np.tanh(E[:,k,:]@p["W"][k]+p["b"][k])@p["Rd"]
    return tot
def dist_to_flat(p,E):
    B=forward(p,E); F=flat(p,E)
    Bc=B-B.mean(0,keepdims=True); Fc=F-F.mean(0,keepdims=True)
    a=np.sum(Bc*Fc)/np.sum(Fc*Fc)
    return float(np.sqrt(np.sum((Bc-a*Fc)**2)/np.sum(Bc**2)))
base=rand_params(42); I=np.eye(H)
print(f"{'setting':<30} {'absorb CEN(max/119)':>20} {'dist to order-free model':>26}")
def row(name,p):
    ce=[]
    for pi in perms[1:]:
        t=forward(p,E,assign=np.array(pi))
        ce.append(min(cen(forward(pm(p,s2),E),t) for s2 in perms))
    print(f"{name:<30} {max(ce):20.4e} {dist_to_flat(p,E):26.4e}")
row("GENERIC (seed 42)", base)
for s in [1e-1,1e-2,1e-3,1e-4]:
    row(f"C4 U=I, s={s:g}", dict(W=s*base["W"],U=np.stack([I]*K),b=s*base["b"],Rd=base["Rd"]/s))
for s in [1e-1,1e-2,1e-4]:
    row(f"C4c U=random, s={s:g}", dict(W=s*base["W"],U=base["U"],b=s*base["b"],Rd=base["Rd"]/s))
p1=rand_params(42); p1["W"]=p1["W"].copy(); p1["W"][1:]=0.0; row("C1 W_k=0 k>=1",p1)
p2=rand_params(42); p2["U"]=np.zeros_like(p2["U"]); row("C2 U_k=0",p2)
