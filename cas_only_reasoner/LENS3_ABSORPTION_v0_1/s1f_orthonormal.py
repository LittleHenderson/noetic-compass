"""No-degeneracy-allowed version. Every W_k is projected to (1/sqrt(H))*ORTHOGONAL and
every U_k to ORTHOGONAL after each step: all singular values equal, condition number
exactly 1, no rank deficiency, no vanishing scale. Then minimise the absorption residual."""
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

def orth(M, s):
    u, _, vt = np.linalg.svd(M, full_matrices=False)
    return s * (u @ vt)

def project(p, ws=1.0/np.sqrt(H), us=1.0):
    for k in range(K):
        p["W"][k] = orth(p["W"][k], ws)
        p["U"][k] = orth(p["U"][k], us)
    return p

def loss_and_grad(theta, sig, pi, E):
    q = permute_modules(theta, sig)
    A = forward(q, E); B = forward(theta, E, assign=np.array(pi))
    _, gA = grads(q, E, B); _, gB = grads(theta, E, A, assign=np.array(pi))
    g = {k: np.zeros_like(v) for k, v in theta.items()}
    for k in range(K):
        g["W"][sig[k]] += gA["W"][k]; g["U"][sig[k]] += gA["U"][k]; g["b"][sig[k]] += gA["b"][k]
    g["Rd"] += gA["Rd"] + gB["Rd"]
    for k in ["W","U","b"]: g[k] += gB[k]
    return g

pi=(1,2,3,4,0); sig=inv(pi)
print("constraint: every W_k = (1/sqrt5)*orthogonal, every U_k = orthogonal  -> cond = 1 exactly")
print(f"target relabelling pi={pi}, compensating module perm sig={sig}\n")
best=None
for seed in range(6):
    th=project(rand_params(seed*17+3))
    m={k:np.zeros_like(v) for k,v in th.items()}; v={k:np.zeros_like(x) for k,x in th.items()}
    lr,b1,b2,eps=2e-2,0.9,0.999,1e-8
    for t in range(1,8001):
        if t==5000: lr=5e-3
        if t==7000: lr=1e-3
        g=loss_and_grad(th,sig,pi,Etr)
        for key in th:
            m[key]=b1*m[key]+(1-b1)*g[key]; v[key]=b2*v[key]+(1-b2)*g[key]**2
            th[key]-=lr*(m[key]/(1-b1**t))/(np.sqrt(v[key]/(1-b2**t))+eps)
        th=project(th)
    tgt=forward(th,Ete,assign=np.array(pi))
    r=rel_rmse(forward(permute_modules(th,sig),Ete),tgt)
    devU=max(np.linalg.norm(th["U"][k]-np.eye(H)) for k in range(K))
    bn=max(np.linalg.norm(th["b"][k]) for k in range(K))
    print(f"seed {seed}: heldout rel residual={r:.4e}  out rms={np.sqrt(np.mean(tgt**2)):.4f}  "
          f"cond(W)={max(np.linalg.cond(th['W'][k]) for k in range(K)):.4f} "
          f"cond(U)={max(np.linalg.cond(th['U'][k]) for k in range(K)):.4f} "
          f"max||U_k-I||={devU:.4f} max||b_k||={bn:.4f}")
    if best is None or r<best[0]: best=(r,th)
print(f"\nBEST heldout rel residual, perfectly conditioned weights = {best[0]:.6e}")
th=best[1]
vals=[]
for p2 in perms[1:]:
    tgt=forward(th,Ete,assign=np.array(p2))
    vals.append(min(rel_rmse(forward(permute_modules(th,s2),Ete),tgt) for s2 in perms))
vals=np.array(vals)
print(f"all 119 relabelings at this setting: min={vals.min():.4e} median={np.median(vals):.4e} MAX={vals.max():.4e}")
print("U_k of the winner (should show whether the optimiser walked to the identity):")
for k in range(K):
    print(f"  ||U_{k} - I||_F = {np.linalg.norm(th['U'][k]-np.eye(H)):.4f}   ||W_{k}||_F = {np.linalg.norm(th['W'][k]):.4f}")
