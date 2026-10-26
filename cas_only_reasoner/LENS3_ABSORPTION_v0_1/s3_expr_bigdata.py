"""Expressivity, overfitting removed: 10000 training samples (40000 target numbers) and
hidden widths H, 2H, 3H. Floor controls at every width."""
import numpy as np
from core import *
rng=np.random.default_rng(11)
NTR,NTE=10000,10000
Etr=rng.normal(size=(NTR,K,DE)); Ete=rng.normal(size=(NTE,K,DE))
P=rand_params(42)
def fit(ttr,tte,Hfit=H,steps=6000,restarts=2,seed0=0):
    best=(np.inf,np.inf)
    for r in range(restarts):
        q=rand_params(3000+seed0+r,H=Hfit,scale=0.7)
        m={k:np.zeros_like(v) for k,v in q.items()}; v={k:np.zeros_like(x) for k,x in q.items()}
        lr,b1,b2,eps=3e-2,0.9,0.999,1e-8
        for t in range(1,steps+1):
            if t==int(steps*0.6): lr=6e-3
            if t==int(steps*0.85): lr=1e-3
            _,g=grads(q,Etr,ttr)
            for key in q:
                m[key]=b1*m[key]+(1-b1)*g[key]; v[key]=b2*v[key]+(1-b2)*g[key]**2
                q[key]-=lr*(m[key]/(1-b1**t))/(np.sqrt(v[key]/(1-b2**t))+eps)
        a=rel_rmse(forward(q,Etr),ttr); b=rel_rmse(forward(q,Ete),tte)
        if a<best[0]: best=(a,b)
    return best
pi=np.array([1,2,3,4,0])
print(f"N_train={NTR} N_heldout={NTE}, Adam 6000 steps x 2 restarts")
print(f"{'target':<42} {'train rel':>11} {'heldout rel':>12}",flush=True)
for Hf in [H,2*H,3*H]:
    r=fit(forward(P,Etr),forward(P,Ete),Hfit=Hf,seed0=Hf*7)
    print(f"{'FLOOR-ID   baseline itself, H_fit=%d'%Hf:<42} {r[0]:11.4e} {r[1]:12.4e}",flush=True)
    r=fit(forward(P,Etr,assign=pi),forward(P,Ete,assign=pi),Hfit=Hf,seed0=Hf*13)
    print(f"{'RELABEL    pi=(1,2,3,4,0), H_fit=%d'%Hf:<42} {r[0]:11.4e} {r[1]:12.4e}",flush=True)
