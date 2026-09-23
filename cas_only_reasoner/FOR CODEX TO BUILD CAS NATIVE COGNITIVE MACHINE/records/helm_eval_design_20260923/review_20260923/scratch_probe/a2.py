import json, itertools, collections
P="D:/tksCAS-worktrees/helm-integration/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_course_001/checks_002/public_course.json"
c=json.load(open(P,encoding="utf-8"))
bank={w["world_id"]:w for w in c["bank"]["worlds"]}
def canon_e(n,E): return (n,min(tuple(sorted((p[a],p[b]) for a,b in E)) for p in itertools.permutations(range(n))))
def idxE(w):
    refs=sorted(x["ref"] for x in w["nodes"]); idx={r:i for i,r in enumerate(refs)}
    return len(refs),[(idx[e["source"]],idx[e["target"]]) for e in w["contains"]], idx
dom={k:w["declarations"]["domain"] for k,w in bank.items()}
shape={k:canon_e(*idxE(w)[:2]) for k,w in bank.items()}
# alternatives like probe
alts={}
for w in bank.values():
    refs=[x["ref"] for x in w["nodes"]]; i={r:j for j,r in enumerate(refs)}
    s=canon_e(len(refs),[(i[e["source"]],i[e["target"]]) for e in w["contains"]]); alts[s]=list(s[1])
for ex in ([(0,1),(0,2)],[(0,2),(1,2)]):
    s=canon_e(3,ex); alts.setdefault(s,list(s[1]))
by={}
for s,e in alts.items(): by.setdefault(s[0],[]).append((s,e))
print({n:len(v) for n,v in by.items()})
an=[r for r in c["registry"] if r["query"]["kind"]=="analogy"]
acc_sizes=[]; nomatch=0; rew_nomatch=0; rew_total=0; whole_root=0; rew_sizes=[]
per_focus=collections.Counter()
for r in an:
    f=r["source_world_id"]; per_focus[f]+=1
    A=[k for k in bank if dom[k]!=dom[f] and shape[k]==shape[f]]
    acc_sizes.append(len(A)); nomatch+= (len(A)==0)
    n,E,idx=idxE(bank[f]); whole=idx[bank[f]["declared_whole"]]
    indeg=[0]*n
    for a,b in E: indeg[b]+=1
    whole_root+= indeg[whole]==0
    own=canon_e(n,E)
    for s,e in by.get(n,[]):
        if s==own: continue
        order=[whole]+[i for i in range(n) if i!=whole]
        R=[(order[a],order[b]) for a,b in e]
        assert canon_e(n,R)==s
        A2=[k for k in bank if dom[k]!=dom[f] and shape[k]==s]
        rew_total+=1; rew_nomatch+= len(A2)==0; rew_sizes.append(len(A2))
print("analogy",len(an),"acc sizes",collections.Counter(acc_sizes),"NO_MATCH gold",nomatch)
print("declared whole is root in",whole_root,"of",len(an))
print("rewires",rew_total,"with empty new answer set",rew_nomatch, collections.Counter(rew_sizes))
print("records per distinct focus", sorted(per_focus.values()))
sh=collections.Counter(shape[k] for k in bank); print(sh)
# witness shared set
W=["typed-input-092dc3b89a0480d462945ca7447bac511c81358714e48059922cd9b469f8a53e","typed-input-0df25be340de7c545d7cdac679233a291d8d134b872c808ff098130afae7171a"]
fa,fb=[next(r for r in an if r["record_id"]==w)["source_world_id"] for w in W]
print("witness same domain", dom[fa]==dom[fb], "shapes", shape[fa], shape[fb])
Aa=set(k for k in bank if dom[k]!=dom[fa] and shape[k]==shape[fa]); Ab=set(k for k in bank if dom[k]!=dom[fb] and shape[k]==shape[fb])
print("acc sets sizes",len(Aa),len(Ab),"overlap",len(Aa&Ab),"shared non-focus",62)
# 3-node foci share
print("3-node foci records", sum(1 for r in an if shape[r["source_world_id"]][0]==3))
