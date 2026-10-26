"""Quantifier-explicit empirical statement about GENERIC parameters:
over R independent random parameter draws, what is the SMALLEST absorption residual
found anywhere (any of the 119 relabelings x 120 module permutations)?"""
import itertools, numpy as np
from core import *
perms=list(itertools.permutations(range(K)))
E=np.random.default_rng(22).normal(size=(128,K,DE))
def pm(p,sig): return dict(W=p["W"][list(sig)],U=p["U"][list(sig)],b=p["b"][list(sig)],Rd=p["Rd"])
def cen(A,B):
    Bc=B-B.mean(0,keepdims=True); return float(np.sqrt(np.sum((A-B)**2)/np.sum(Bc**2)))
mins=[]
R=60
for seed in range(R):
    p=rand_params(10000+seed)
    outs=[forward(pm(p,sig),E) for sig in perms]
    best=np.inf
    for pi in perms[1:]:
        t=forward(p,E,assign=np.array(pi))
        for o in outs:
            v=cen(o,t)
            if v<best: best=v
    mins.append(best)
    if (seed+1)%10==0: print(f"  {seed+1}/{R} draws done, running min = {min(mins):.4e}",flush=True)
mins=np.array(mins)
print(f"\nover {R} independent random (W,U,b,Rd) draws, N(0,1) entries:")
print(f"  best absorption (centred) residual found for each draw:")
print(f"    min over draws    = {mins.min():.4e}")
print(f"    median over draws = {np.median(mins):.4e}")
print(f"    max over draws    = {mins.max():.4e}")
print(f"  number of draws with any residual < 1e-2 : {int(np.sum(mins<1e-2))}/{R}")
print(f"  number of draws with any residual < 1e-1 : {int(np.sum(mins<1e-1))}/{R}")
