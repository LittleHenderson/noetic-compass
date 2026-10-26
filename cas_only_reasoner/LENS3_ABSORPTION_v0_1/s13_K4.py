"""Does the counterexample hold at the REAL size K=4 (the P>C>E>O chain), and at other seeds?"""
import itertools, numpy as np
import core
from core import rand_params, forward, rel_rmse

def run(Kk,DEx,Hx,ACTx,seed):
    core.K,core.DE,core.H,core.ACT=Kk,DEx,Hx,ACTx
    perms=list(itertools.permutations(range(Kk)))
    E=np.random.default_rng(22).normal(size=(2048,Kk,DEx))
    def pm(p,sig): return dict(W=p["W"][list(sig)],U=p["U"][list(sig)],b=p["b"][list(sig)],Rd=p["Rd"])
    def cen(A,B):
        Bc=B-B.mean(0,keepdims=True); return float(np.sqrt(np.sum((A-B)**2)/np.sum(Bc**2)))
    base=rand_params(seed,K=Kk,DE=DEx,H=Hx,ACT=ACTx); I=np.eye(Hx)
    gen=[]; abs_=[]
    for pi in perms[1:]:
        t=forward(base,E,assign=np.array(pi))
        gen.append(min(cen(forward(pm(base,s2),E),t) for s2 in perms))
    s=1e-10
    C4=dict(W=s*base["W"],U=np.stack([I]*Kk),b=s*base["b"],Rd=base["Rd"]/s)
    B=forward(C4,E); Bc=B-B.mean(0,keepdims=True)
    for pi in perms[1:]:
        t=forward(C4,E,assign=np.array(pi))
        abs_.append(min(cen(forward(pm(C4,s2),E),t) for s2 in perms))
    print(f"K={Kk} DE={DEx} H={Hx} ACT={ACTx} seed={seed}: n_relab={len(perms)-1}  "
          f"GENERIC cen[min/MAX]={min(gen):.4e}/{max(gen):.4e}   "
          f"C4 cen[min/MAX]={min(abs_):.4e}/{max(abs_):.4e}   "
          f"var_frac={np.sum(Bc**2)/np.sum(B**2):.4f}  #<1e-15: {sum(1 for x in abs_ if x<1e-15)}/{len(abs_)}")

for seed in [42,7,101]:
    run(4,4,4,3,seed)       # the real CAS size: P > C > E > O
for seed in [42,7]:
    run(5,5,5,4,seed)
