"""Re-run the perfectly-conditioned optimum (s1f seed 1) and score it with BOTH metrics."""
import itertools, numpy as np
from core import *
perms=list(itertools.permutations(range(K)))
Etr=np.random.default_rng(21).normal(size=(512,K,DE)); Ete=np.random.default_rng(22).normal(size=(4096,K,DE))
def pm(p,sig): return dict(W=p["W"][list(sig)],U=p["U"][list(sig)],b=p["b"][list(sig)],Rd=p["Rd"])
def inv(pi):
    q=[0]*len(pi)
    for k,t in enumerate(pi): q[t]=k
    return tuple(q)
def orth(M,s):
    u,_,vt=np.linalg.svd(M,full_matrices=False); return s*(u@vt)
def project(p):
    for k in range(K):
        p["W"][k]=orth(p["W"][k],1/np.sqrt(H)); p["U"][k]=orth(p["U"][k],1.0)
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
th=project(rand_params(1*17+3))
m={k:np.zeros_like(v) for k,v in th.items()}; v={k:np.zeros_like(x) for k,x in th.items()}
lr,b1,b2,eps=2e-2,0.9,0.999,1e-8
for t in range(1,8001):
    if t==5000: lr=5e-3
    if t==7000: lr=1e-3
    g=lg(th,sig,pi,Etr)
    for key in th:
        m[key]=b1*m[key]+(1-b1)*g[key]; v[key]=b2*v[key]+(1-b2)*g[key]**2
        th[key]-=lr*(m[key]/(1-b1**t))/(np.sqrt(v[key]/(1-b2**t))+eps)
    th=project(th)
np.savez("orth_opt.npz",**th)
def cen(A,B):
    Bc=B-B.mean(0,keepdims=True); return float(np.sqrt(np.sum((A-B)**2)/np.sum(Bc**2)))
B=forward(th,Ete); Bc=B-B.mean(0,keepdims=True)
print(f"var_frac = {np.sum(Bc**2)/np.sum(B**2):.4f}   out rms = {np.sqrt(np.mean(B**2)):.4f}   out std = {np.std(B):.4f}")
print(f"cond(W_k) = {[round(float(np.linalg.cond(th['W'][k])),6) for k in range(K)]}")
print(f"cond(U_k) = {[round(float(np.linalg.cond(th['U'][k])),6) for k in range(K)]}")
print(f"||W_k||_F = {[round(float(np.linalg.norm(th['W'][k])),4) for k in range(K)]}")
print(f"||b_k||   = {[round(float(np.linalg.norm(th['b'][k])),4) for k in range(K)]}")
print(f"||U_k-I|| = {[round(float(np.linalg.norm(th['U'][k]-np.eye(H))),4) for k in range(K)]}")
rel=[];ce=[]
for p2 in perms[1:]:
    tgt=forward(th,Ete,assign=np.array(p2))
    bv,bc=np.inf,np.inf
    for s2 in perms:
        o=forward(pm(th,s2),Ete); vv=rel_rmse(o,tgt)
        if vv<bv: bv,bc=vv,cen(o,tgt)
    rel.append(bv);ce.append(bc)
rel=np.array(rel);ce=np.array(ce)
print(f"ALL 119 relabelings: rel[min/med/MAX]={rel.min():.4e}/{np.median(rel):.4e}/{rel.max():.4e}")
print(f"                     cen[min/med/MAX]={ce.min():.4e}/{np.median(ce):.4e}/{ce.max():.4e}")
