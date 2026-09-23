import json, itertools, collections
from shapes import canon, degsig, dags
res=json.load(open("shapes.json"))
bank={canon(3,[(0,1),(1,2)]),canon(4,[(0,1),(0,2),(0,3)]),canon(4,[(0,1),(0,2),(1,3),(2,3)]),canon(4,[(0,1),(1,2),(2,3)]),canon(4,[(0,1),(0,2),(3,1)]),canon(4,[(0,1),(0,2),(1,3)])}
tot=collections.Counter()
for n in ("3","4"):
    for r in res[n]["rows"]:
        c=tuple(tuple(e) for e in r["edges"])
        isbank=c in bank
        key="bank" if isbank else "new"
        tot[(key,"shapes")]+=1
        tot[(key,"via_orbits")]+=r["via_orbits"]
        tot[(key,"via_labelled")]+=r["via_labelled"]
        tot[(key,"via_tie")]+=r["via_tie"]
        tot[(key,"shapes_with_any_via")]+= r["via_labelled"]>0
        tot[(key,"shapes_with_nontie_via")]+= (r["via_labelled"]-r["via_tie"])>0
        print(n,key,r)
print(dict(tot))
# colliding pair at 4
S=dags(4); sig=collections.defaultdict(list)
for c in S: sig[degsig(4,list(c))].append(c)
print("collide4",[v for v in sig.values() if len(v)>1], "in bank:",[[x in bank for x in v] for v in sig.values() if len(v)>1])
