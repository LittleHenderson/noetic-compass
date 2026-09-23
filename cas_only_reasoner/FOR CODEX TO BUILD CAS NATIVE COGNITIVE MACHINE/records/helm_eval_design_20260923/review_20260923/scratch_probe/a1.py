import json, itertools, collections
P="D:/tksCAS-worktrees/helm-integration/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_course_001/checks_002/public_course.json"
c=json.load(open(P,encoding="utf-8"))
print(list(c.keys()))
reg=c["registry"]; print("registry",len(reg))
bank={w["world_id"]:w for w in c["bank"]["worlds"]}
print("bank keys", list(next(iter(bank.values())).keys()))
def canon(w):
    refs=sorted(x["ref"] for x in w["nodes"]); idx={r:i for i,r in enumerate(refs)}; n=len(refs)
    E=[(idx[e["source"]],idx[e["target"]]) for e in w["contains"]]
    return (n,min(tuple(sorted((p[a],p[b]) for a,b in E)) for p in itertools.permutations(range(n))))
an=[r for r in reg if r["query"]["kind"]=="analogy"]
print("analogy", len(an))
print("rules", collections.Counter(r["query"]["rule"] for r in an))
print("arg keys", collections.Counter(tuple(sorted(r["query"]["arguments"].items())) if False else tuple(sorted(r["query"]["arguments"])) for r in an))
print("query keys", set(k for r in an for k in r["query"]))
foci=collections.Counter(r["source_world_id"] for r in an); print("distinct foci",len(foci), "max repeats", max(foci.values()))
W=["typed-input-092dc3b89a0480d462945ca7447bac511c81358714e48059922cd9b469f8a53e","typed-input-0df25be340de7c545d7cdac679233a291d8d134b872c808ff098130afae7171a"]
for wid in W:
    r=next(x for x in reg if x["record_id"]==wid)
    f=bank[r["source_world_id"]]
    print(wid[:24], r["query"]["kind"], r["source_world_id"], f.get("declarations",{}).get("domain"), canon(f), "cue",r["cue"])
shapes=collections.Counter(canon(bank[r["source_world_id"]]) for r in an); print(shapes)
