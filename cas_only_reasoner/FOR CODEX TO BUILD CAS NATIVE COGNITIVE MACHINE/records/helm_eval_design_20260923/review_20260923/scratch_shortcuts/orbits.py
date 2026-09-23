import itertools, collections
from math import comb
exec(open('dagenum.py').read().split('res={}')[0])
tot=0; shapes_with=0
for n in (3,4):
    C=classes(n); new=[c for c in C if c not in bank.get(n,set())]
    for c in new:
        E=list(c); A=autos(n,E)
        pairs=set()
        for w in range(n):
            for p in range(n):
                if w!=p and reach_state(n,E,w,p)[0]=="VIA":
                    orb=min((a[w],a[p]) for a in A); pairs.add(orb)
        tot+=len(pairs); shapes_with+= bool(pairs)
print("distinct VIA (whole,part) orbits over all 22 new same-size shapes:",tot,"in",shapes_with,"shapes")
# hypergeometric: 22 shapes, 11 VIA-capable, TEST_NEW draws 11
P=[comb(11,k)*comb(11,11-k)/comb(22,11) for k in range(12)]
print("P(TEST_NEW has k VIA-capable shapes):",{k:round(p,4) for k,p in enumerate(P)})
print("P(k<=3)=",round(sum(P[:4]),4),"P(k<=4)=",round(sum(P[:5]),4))
# 3-node vs 4-node split
