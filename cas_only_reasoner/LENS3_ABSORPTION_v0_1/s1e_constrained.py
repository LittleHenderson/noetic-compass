"""STRONGEST form of the counterexample search.
Directly MINIMISE the absorption residual over parameters, under a normalisation that
forbids the cheap route ("make W tiny so tanh is linear"):
      ||W_k||_F = 1 and ||U_k||_F = sqrt(H) (= the Frobenius norm of the identity) for all k.
If the residual still goes low with WELL-SCALED, WELL-CONDITIONED weights, the
non-absorption claim fails outside the degenerate corner too.
"""
import itertools, numpy as np
from core import *

perms = list(itertools.permutations(range(K)))
Etr = np.random.default_rng(21).normal(size=(512, K, DE))
Ete = np.random.default_rng(22).normal(size=(4096, K, DE))

def permute_modules(p, sig):
    return dict(W=p["W"][list(sig)], U=p["U"][list(sig)], b=p["b"][list(sig)], Rd=p["Rd"])

def inv(pi):
    q=[0]*len(pi)
    for k,t in enumerate(pi): q[t]=k
    return tuple(q)

def project(p, wn=1.0, un=np.sqrt(H)):
    for k in range(K):
        p["W"][k] *= wn/np.linalg.norm(p["W"][k])
        p["U"][k] *= un/np.linalg.norm(p["U"][k])
    return p

def loss_and_grad(theta, sig, pi, E):
    q = permute_modules(theta, sig)
    A = forward(q, E)
    B = forward(theta, E, assign=np.array(pi))
    lA, gA = grads(q, E, B)                      # d/d(permuted params), B frozen
    lB, gB = grads(theta, E, A, assign=np.array(pi))
    g = {k: np.zeros_like(v) for k, v in theta.items()}
    for k in range(K):
        g["W"][sig[k]] += gA["W"][k]; g["U"][sig[k]] += gA["U"][k]; g["b"][sig[k]] += gA["b"][k]
    g["Rd"] += gA["Rd"]
    for k in ["W","U","b","Rd"]: g[k] += gB[k]
    return lA, g

pi = (1, 2, 3, 4, 0)      # the 5-cycle -- hardest relabelling in the anchor
sig = inv(pi)
print(f"target relabelling pi={pi}, compensating module permutation sig=pi^-1={sig}")
print("constraint: ||W_k||_F=1, ||U_k||_F=sqrt(5)=2.2361 for every k\n")
best=None
for seed in range(6):
    th = rand_params(seed*17+3); th = project(th)
    m={k:np.zeros_like(v) for k,v in th.items()}; v={k:np.zeros_like(x) for k,x in th.items()}
    lr,b1,b2,eps=2e-2,0.9,0.999,1e-8
    for t in range(1,8001):
        if t==5000: lr=5e-3
        if t==7000: lr=1e-3
        _,g = loss_and_grad(th, sig, pi, Etr)
        for key in th:
            m[key]=b1*m[key]+(1-b1)*g[key]; v[key]=b2*v[key]+(1-b2)*g[key]**2
            th[key]-= lr*(m[key]/(1-b1**t))/(np.sqrt(v[key]/(1-b2**t))+eps)
        th = project(th)
    tgt=forward(th,Ete,assign=np.array(pi))
    r=rel_rmse(forward(permute_modules(th,sig),Ete),tgt)
    sw=min(np.linalg.svd(th["W"][k],compute_uv=False).min() for k in range(K))
    su=min(np.linalg.svd(th["U"][k],compute_uv=False).min() for k in range(K))
    cu=max(np.linalg.cond(th["U"][k]) for k in range(K))
    dev=max(np.linalg.norm(th["U"][k]-np.eye(H)) for k in range(K))
    print(f"seed {seed}: heldout rel residual={r:.4e}  out rms={np.sqrt(np.mean(tgt**2)):.4f}  "
          f"min sv(W)={sw:.4f} min sv(U)={su:.4f} max cond(U)={cu:.2f} max||U_k-I||={dev:.4f}")
    if best is None or r<best[0]: best=(r,th)
print(f"\nBEST heldout rel residual with normalised weights = {best[0]:.6e}")
th=best[1]
print("worst over ALL 119 relabelings for this parameter setting (best sig each):")
vals=[]
for p2 in perms[1:]:
    tgt=forward(th,Ete,assign=np.array(p2))
    vals.append(min(rel_rmse(forward(permute_modules(th,s2),Ete),tgt) for s2 in perms))
vals=np.array(vals)
print(f"   min={vals.min():.4e}  median={np.median(vals):.4e}  MAX={vals.max():.4e}")
gen = rand_params(42)
gvals=[]
for p2 in perms[1:]:
    tgt=forward(gen,Ete,assign=np.array(p2))
    gvals.append(min(rel_rmse(forward(permute_modules(gen,s2),Ete),tgt) for s2 in perms))
gvals=np.array(gvals)
print(f"   GENERIC control (seed 42, unnormalised): min={gvals.min():.4e} median={np.median(gvals):.4e} MAX={gvals.max():.4e}")
