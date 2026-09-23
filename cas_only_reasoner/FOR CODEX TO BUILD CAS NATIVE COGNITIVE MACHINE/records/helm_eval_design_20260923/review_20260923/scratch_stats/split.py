import json, itertools, collections, random
res=json.load(open("shapes.json"))
from shapes import canon
bank={canon(3,[(0,1),(1,2)]),canon(4,[(0,1),(0,2),(0,3)]),canon(4,[(0,1),(0,2),(1,3),(2,3)]),canon(4,[(0,1),(1,2),(2,3)]),canon(4,[(0,1),(0,2),(3,1)]),canon(4,[(0,1),(0,2),(1,3)])}
new=[r for n in ("3","4") for r in res[n]["rows"] if tuple(tuple(e) for e in r["edges"]) not in bank]
nt=[r["via_labelled"]-r["via_tie"] for r in new]
print("new shapes",len(new),"nontie via per shape",nt,"total",sum(nt))
dist=collections.Counter(); shp=collections.Counter()
for combo in itertools.combinations(range(22),11):
    dist[sum(nt[i] for i in combo)]+=1
    shp[sum(1 for i in combo if nt[i]>0)]+=1
tot=sum(dist.values())
print("TEST half non-tie VIA questions: distribution", {k:round(v/tot,4) for k,v in sorted(dist.items())})
print("TEST half shapes with >=1 non-tie VIA", {k:round(v/tot,4) for k,v in sorted(shp.items())})
