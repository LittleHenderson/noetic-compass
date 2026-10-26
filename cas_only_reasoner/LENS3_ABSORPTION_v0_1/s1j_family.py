"""How big is the absorbing family, and where is its boundary in interpretable units?
(1) boundary: centred residual vs ||W_k||_F along the U=I family.
(2) is U_k = I special, or does any COMMON U work? test U_k = Q for all k, Q orthogonal,
    and Q an involution (Q^2 = I)."""
import itertools, numpy as np
from core import *
perms=list(itertools.permutations(range(K)))
Ete=np.random.default_rng(22).normal(size=(2048,K,DE))
def pm(p,sig): return dict(W=p["W"][list(sig)],U=p["U"][list(sig)],b=p["b"][list(sig)],Rd=p["Rd"])
def cen(A,B):
    Bc=B-B.mean(0,keepdims=True); return float(np.sqrt(np.sum((A-B)**2)/np.sum(Bc**2)))
def vf(B):
    Bc=B-B.mean(0,keepdims=True); return float(np.sum(Bc**2)/np.sum(B**2))
def scan(p):
    ce=[]
    for pi in perms[1:]:
        tgt=forward(p,Ete,assign=np.array(pi))
        ce.append(min(cen(forward(pm(p,s2),Ete),tgt) for s2 in perms))
    return np.array(ce)

base=rand_params(42); I=np.eye(H)
print("(1) BOUNDARY of the U=I absorbing family, in units of ||W_k||_F")
print(f"{'s':>9} {'||W_k||_F':>11} {'var_frac':>9} {'CEN min':>11} {'CEN med':>11} {'CEN MAX':>11}")
for s in [1.0,3e-1,1e-1,3e-2,1e-2,1e-3,1e-4,1e-6,1e-10]:
    p=dict(W=s*base["W"],U=np.stack([I]*K),b=s*base["b"],Rd=base["Rd"]/max(s,1e-300))
    ce=scan(p); wn=np.mean([np.linalg.norm(p["W"][k]) for k in range(K)])
    print(f"{s:9.0e} {wn:11.4e} {vf(forward(p,Ete)):9.4f} {ce.min():11.4e} {np.median(ce):11.4e} {ce.max():11.4e}")

print("\n(2) is U=I special? COMMON U_k = Q for all k, W,b at s=1e-4")
s=1e-4
r=np.random.default_rng(3)
Qr,_=np.linalg.qr(r.normal(size=(H,H)))                 # generic orthogonal
D=np.diag([1.,-1.,1.,-1.,1.])                           # involution, Q^2=I
Pm=np.eye(H)[[1,0,3,2,4]]                               # permutation, order 2
cases={"Q = I":I, "Q = generic orthogonal":Qr, "Q = sign-diagonal (Q^2=I)":D,
       "Q = 2-cycle permutation (Q^2=I)":Pm, "Q = 5-cycle permutation (Q^5=I)":np.eye(H)[[1,2,3,4,0]]}
for name,Q in cases.items():
    p=dict(W=s*base["W"],U=np.stack([Q]*K),b=s*base["b"],Rd=base["Rd"]/s)
    ce=scan(p)
    print(f"  {name:<34} var_frac={vf(forward(p,Ete)):.4f}  CEN min={ce.min():.4e} med={np.median(ce):.4e} MAX={ce.max():.4e}  #<1e-5: {int(np.sum(ce<1e-5))}/119")
print("\n(3) DIFFERENT U per position but all equal to each other is required? U_k = I for k in S only")
for nfix in [5,4,3]:
    U=np.stack([I]*K); 
    for k in range(nfix,K): U[k]=base["U"][k]
    p=dict(W=s*base["W"],U=U,b=s*base["b"],Rd=base["Rd"]/s)
    ce=scan(p)
    print(f"  first {nfix} positions have U=I, rest random: CEN min={ce.min():.4e} MAX={ce.max():.4e} #<1e-5: {int(np.sum(ce<1e-5))}/119")
