"""s1f/s1e collapsed to a NEAR-CONSTANT function (var_frac ~ 0) -- the centred metric
rejected them. Rerun with the collapse route closed: biases capped at ||b_k|| <= 0.5 so
the units cannot saturate into constants, W_k and U_k still perfectly conditioned.
Report var_frac and the CENTRED residual, which is the metric that counts."""
import itertools, numpy as np
from core import *
perms=list(itertools.permutations(range(K)))
Etr=np.random.default_rng(21).normal(size=(512,K,DE)); Ete=np.random.default_rng(22).normal(size=(4096,K,DE))
def pm(p,sig): return dict(W=p["W"][list(sig)],U=p["U"][list(sig)],b=p["b"][list(sig)],Rd=p["Rd"])
def inv(pi):
    q=[0]*len(pi)
    for k,t in enumerate(pi): q[t]=k
    return tuple(q)
def cen(A,B):
    Bc=B-B.mean(0,keepdims=True); return float(np.sqrt(np.sum((A-B)**2)/np.sum(Bc**2)))
def vf(B):
    Bc=B-B.mean(0,keepdims=True); return float(np.sum(Bc**2)/np.sum(B**2))
def orth(M,s):
    u,_,vt=np.linalg.svd(M,full_matrices=False); return s*(u@vt)
def project(p,bcap):
    for k in range(K):
        p["W"][k]=orth(p["W"][k],1/np.sqrt(H)); p["U"][k]=orth(p["U"][k],1.0)
        n=np.linalg.norm(p["b"][k])
        if n>bcap: p["b"][k]*=bcap/n
    return p
def lg(theta,sig,pi,E):
    q=pm(theta,sig); A=forward(q,E); B=forward(theta,E,assign=np.array(pi))
    _,gA=grads(q,E,B); _,gB=grads(theta,E,A,assign=np.array(pi))
    g={k:np.zeros_like(v) for k,v in theta.items()}
    for k in range(K):
        g["W"][sig[k]]+=gA["W"][k]; g["U"][sig[k]]+=gA["U"][k]; g["b"][sig[k]]+=gA["b"][k]
    g["Rd"]+=gA["Rd"]+gB["Rd"]
    for k in ["W","U","b"]: g[k]+=gB[k]
    return g
pi=(1,2,3,4,0); sig=inv(pi)
print("W_k=(1/sqrt5)*orthogonal, U_k=orthogonal (cond=1), ||b_k||<=0.5, minimise absorption residual")
print(f"{'seed':>4} {'var_frac':>9} {'rel res':>11} {'CEN res':>11} {'max||U-I||':>11}")
best=None
for seed in range(8):
    th=project(rand_params(seed*17+3),0.5)
    m={k:np.zeros_like(v) for k,v in th.items()}; v={k:np.zeros_like(x) for k,x in th.items()}
    lr,b1,b2,eps=2e-2,0.9,0.999,1e-8
    for t in range(1,8001):
        if t==5000: lr=5e-3
        if t==7000: lr=1e-3
        g=lg(th,sig,pi,Etr)
        for key in th:
            m[key]=b1*m[key]+(1-b1)*g[key]; v[key]=b2*v[key]+(1-b2)*g[key]**2
            th[key]-=lr*(m[key]/(1-b1**t))/(np.sqrt(v[key]/(1-b2**t))+eps)
        th=project(th,0.5)
    B=forward(th,Ete,assign=np.array(pi)); A=forward(pm(th,sig),Ete)
    c=cen(A,B)
    print(f"{seed:>4} {vf(B):9.4f} {rel_rmse(A,B):11.4e} {c:11.4e} "
          f"{max(np.linalg.norm(th['U'][k]-np.eye(H)) for k in range(K)):11.4f}")
    if best is None or c<best[0]: best=(c,th)
th=best[1]
print(f"\nBEST centred residual (5-cycle) = {best[0]:.6e}")
ce=[]
for p2 in perms[1:]:
    tgt=forward(th,Ete,assign=np.array(p2))
    ce.append(min(cen(forward(pm(th,s2),Ete),tgt) for s2 in perms))
ce=np.array(ce)
print(f"all 119 relabelings, CENTRED: min={ce.min():.4e} median={np.median(ce):.4e} MAX={ce.max():.4e}")
print(f"var_frac of this model = {vf(forward(th,Ete)):.4f}")
print(f"||U_k-I||_F = {[round(float(np.linalg.norm(th['U'][k]-np.eye(H))),4) for k in range(K)]}")
