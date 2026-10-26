"""Final consolidated table of the decisive numbers, recomputed in one place."""
import itertools, numpy as np
from core import *
perms=list(itertools.permutations(range(K)))
E=np.random.default_rng(22).normal(size=(4096,K,DE))
def pm(p,sig): return dict(W=p["W"][list(sig)],U=p["U"][list(sig)],b=p["b"][list(sig)],Rd=p["Rd"])
def cen(A,B):
    Bc=B-B.mean(0,keepdims=True); return float(np.sqrt(np.sum((A-B)**2)/np.sum(Bc**2)))
base=rand_params(42); I=np.eye(H)
s=1e-10
C4=dict(W=s*base["W"],U=np.stack([I]*K),b=s*base["b"],Rd=base["Rd"]/s)
print("C4 FINAL, s=1e-10, Rd rescaled by 1/s:")
print(f"  rank(W_k)={[int(np.linalg.matrix_rank(C4['W'][k])) for k in range(K)]}  "
      f"rank(U_k)={[int(np.linalg.matrix_rank(C4['U'][k])) for k in range(K)]}")
print(f"  cond(W_k)={[round(float(np.linalg.cond(C4['W'][k])),3) for k in range(K)]}")
print(f"  cond(U_k)={[round(float(np.linalg.cond(C4['U'][k])),3) for k in range(K)]}")
B=forward(C4,E); Bc=B-B.mean(0,keepdims=True)
print(f"  out rms={np.sqrt(np.mean(B**2)):.4f}  fraction of output energy that varies with E={np.sum(Bc**2)/np.sum(B**2):.4f}")
ce=[];rl=[]
for pi in perms[1:]:
    t=forward(C4,E,assign=np.array(pi))
    bb=min((rel_rmse(forward(pm(C4,s2),E),t),cen(forward(pm(C4,s2),E),t)) for s2 in perms)
    rl.append(bb[0]); ce.append(bb[1])
print(f"  absorbed relabelings with centred residual < 1e-15: {int(np.sum(np.array(ce)<1e-15))}/119")
print(f"  centred residual over all 119: min={min(ce):.4e} median={np.median(ce):.4e} MAX={max(ce):.4e}")
print(f"  float64 machine epsilon = {np.finfo(np.float64).eps:.4e}")
