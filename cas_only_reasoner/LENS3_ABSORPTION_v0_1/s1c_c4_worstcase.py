"""C4 hardening:
 (i) worst case over ALL 119 relabelings, not just the best one
 (ii) is the absorbing module permutation exactly pi^{-1}?
 (iii) rescale Rd by 1/s so the output magnitude is O(1) -- does the residual survive?
     (Rd is a shared linear factor, so the RELATIVE residual must be unchanged; this
      rules out "you only made all the numbers small".)
"""
import itertools, numpy as np
from core import *

perms = list(itertools.permutations(range(K)))
Eb = np.random.default_rng(7).normal(size=(1024, K, DE))
base = rand_params(42)
I = np.eye(H)


def permute_modules(p, sig):
    return dict(W=p["W"][list(sig)], U=p["U"][list(sig)], b=p["b"][list(sig)], Rd=p["Rd"])


def inv(pi):
    q = [0] * len(pi)
    for k, t in enumerate(pi):
        q[t] = k
    return tuple(q)


print("C4 worst-case: for EVERY one of the 119 relabelings, best over 120 module perms")
print(f"{'s':>9} {'Rd scale':>10} {'out rms':>11} {'min rel':>12} {'median rel':>12} {'MAX rel':>12} {'argmin=pi^-1?':>14}")
for s in [1e-1, 1e-2, 1e-3, 1e-4, 1e-5, 1e-6, 1e-8, 1e-10]:
    for rd_scale in [1.0, 1.0 / s]:
        p = dict(W=s * base["W"], U=np.stack([I] * K), b=s * base["b"], Rd=rd_scale * base["Rd"])
        vals, agree = [], 0
        for pi in perms[1:]:
            tgt = forward(p, Eb, assign=np.array(pi))
            loc, locsig = np.inf, None
            for sig in perms:
                v = rel_rmse(forward(permute_modules(p, sig), Eb), tgt)
                if v < loc:
                    loc, locsig = v, sig
            vals.append(loc)
            agree += int(locsig == inv(pi))
        vals = np.array(vals)
        print(f"{s:9.0e} {rd_scale:10.1e} {np.sqrt(np.mean(forward(p,Eb)**2)):11.3e} "
              f"{vals.min():12.4e} {np.median(vals):12.4e} {vals.max():12.4e} {agree:6d}/119")
