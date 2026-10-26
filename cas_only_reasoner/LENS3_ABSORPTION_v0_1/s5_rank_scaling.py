"""Does the required-width lower bound grow, or is it just capped by the ambient DE*ACT?"""
import numpy as np, core
from core import rand_params, fwd_cache, forward

def jac_last_row(p,E,assign,DE,ACT):
    Kk=p["W"].shape[0]; N=E.shape[0]
    out,hs=fwd_cache(p,E,assign)
    J=np.zeros((N,DE,ACT))
    for a in range(ACT):
        gh=np.tile(p["Rd"][:,a],(N,1)); acc=np.zeros((N,DE))
        for k in range(Kk-1,-1,-1):
            ga=gh*(1.0-hs[k+1]**2)
            if assign[k]==Kk-1: acc+=ga@p["W"][k].T
            gh=ga@p["U"][k].T
        J[:,:,a]=acc
    return J

print(f"{'K':>3} {'DE':>4} {'H':>4} {'ACT':>5} {'ambient':>8} {'rank(identity)':>15} {'rank(5-cycle relabel)':>22}")
for (Kk,DEx,Hx,ACTx) in [(5,5,5,4),(5,8,5,8),(5,10,5,10),(5,10,8,10),(4,8,6,8),(5,12,5,12)]:
    p=rand_params(42,K=Kk,DE=DEx,H=Hx,ACT=ACTx)
    E=np.random.default_rng(31).normal(size=(4000,Kk,DEx))
    pi=np.array(list(range(1,Kk))+[0])
    def nr(J):
        M=J.reshape(J.shape[0],-1); s=np.linalg.svd(M,compute_uv=False)
        return int(np.sum(s>1e-8*s[0]))
    r0=nr(jac_last_row(p,E,np.arange(Kk),DEx,ACTx))
    r1=nr(jac_last_row(p,E,pi,DEx,ACTx))
    print(f"{Kk:>3} {DEx:>4} {Hx:>4} {ACTx:>5} {DEx*ACTx:>8} {r0:>15} {r1:>22}")
