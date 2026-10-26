"""What IS the absorbing corner, in mechanism terms?
Hypothesis: absorption happens exactly where the chain stops chaining and the model
degenerates into the FLAT (order-free) model. Test: distance between the chain model
and the best-matching flat model, alongside the absorption residual."""
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
def order_sens(p,E):
    """how much does the model's output change when the chain ORDER is reversed
    while the type->position map is held fixed?  0 = the chain ignores its own order."""
    q=pm(p,(4,3,2,1,0))
    B=forward(p,E); Bc=B-B.mean(0,keepdims=True)
    return float(np.sqrt(np.sum((forward(q,E)-B)**2)/np.sum(Bc**2)))
base=rand_params(42); I=np.eye(H)
print(f"{'setting':<34} {'||W_k||_F':>10} {'absorb CEN':>11} {'order-sens':>11}")
def row(name,p):
    ce=[]
    for pi in perms[1:]:
        t=forward(p,E,assign=np.array(pi))
        ce.append(min(cen(forward(pm(p,s2),E),t) for s2 in perms))
    print(f"{name:<34} {np.mean([np.linalg.norm(p['W'][k]) for k in range(K)]):10.3e} "
          f"{max(ce):11.4e} {order_sens(p,E):11.4e}")
row("GENERIC (seed 42)", base)
for s in [1e-1,1e-2,1e-3,1e-4]:
    row(f"C4 U=I, s={s:g}", dict(W=s*base["W"],U=np.stack([I]*K),b=s*base["b"],Rd=base["Rd"]/s))
for s in [1e-1,1e-2,1e-4]:
    row(f"C4c U=random, s={s:g}", dict(W=s*base["W"],U=base["U"],b=s*base["b"],Rd=base["Rd"]/s))
