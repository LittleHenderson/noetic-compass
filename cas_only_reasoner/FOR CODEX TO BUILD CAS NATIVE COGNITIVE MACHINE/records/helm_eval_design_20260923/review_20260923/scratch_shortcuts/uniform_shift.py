# Replays the probe's verdict arithmetic (analogy_wiring_probe.py:198-221) on a synthetic scorer whose
# candidate scores are a FIXED focus-independent ranking plus ONE focus-dependent constant added to every candidate.
import random
random.seed(0)
TAU_ZERO,TAU_PRESENT,SHARE=1e-6,1e-4,0.90
cands=["W%d"%i for i in range(64)]; base={c:random.gauss(0,1) for c in cands}
def shift(focus_edges): return 0.01*len(focus_edges)+0.003*sum(a*b for a,b in focus_edges)
def scorer(focus,edges): return {c:base[c]+shift(edges) for c in cands}
recs=[("W%d"%i,[(0,1),(1,2)] if i%2 else [(0,1),(0,2),(0,3)]) for i in range(70)]
alts=[[(0,1),(1,2),(2,3)],[(0,1),(0,2),(1,3),(2,3)]]
basesc={}; m3={}; top_changes=0; rewires=0
for k,(f,e) in enumerate(recs):
    s=scorer(f,e); basesc[k]=(f,s); worst=0
    for alt in alts:
        if alt==e: continue
        ch=scorer(f,alt); rewires+=1
        worst=max(worst,max(abs(ch[c]-s[c]) for c in s if c!=f))
        top=lambda d:max((c for c in d if c!=f),key=d.get)
        top_changes+= top(ch)!=top(s)
    m3[k]=worst
fa,sa=basesc[0]; fb,sb=basesc[1]
m1=max(abs(sa[c]-sb[c]) for c in sa if c not in (fa,fb))
share=sum(v>TAU_PRESENT for v in m3.values())/len(m3)
verdict="PRESENT" if (m1>TAU_PRESENT and share>=SHARE) else "other"
print("M1",round(m1,6),"share",share,"verdict",verdict,"non-focus top-1 changes",top_changes,"of",rewires)
