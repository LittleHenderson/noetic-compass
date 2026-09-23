import json, collections
P="D:/tksCAS-worktrees/helm-integration/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_course_001/checks_002/public_course.json"
d=json.load(open(P,encoding="utf-8"))
bank=d["bank"]["worlds"]
print("top keys",list(d.keys())[:20])
stats=collections.Counter()
for w in bank:
    nodes=sorted(n["ref"] for n in w["nodes"])
    adj={n:[] for n in nodes}
    for e in sorted((e["source"],e["target"]) for e in w["contains"]): adj[e[0]].append(e[1])
    def reach(s,t):
        st=[s];seen={s}
        while st:
            x=st.pop()
            if x==t:return True
            for y in adj[x]:
                if y not in seen: seen.add(y); st.append(y)
        return False
    whole=w["declared_whole"]; parts=w["declarations"]["participants"]
    roots=[n for n in nodes if all(n not in adj[m] for m in nodes)]
    stats["whole_is_unique_root"]+= (roots==[whole])
    stats["worlds"]+=1
    for wh in nodes:
      for p in nodes:
        if wh==p or p in adj[wh]: continue
        firsts=[c for c in adj[wh] if reach(c,p)]
        if not firsts: continue
        gold=firsts[0]
        key="decl_whole" if wh==whole else "other_whole"
        stats[(key,"via")]+=1
        stats[(key,"via==participant2")]+= gold==parts[1]
        stats[(key,"tie")]+= len(firsts)>1
print(dict(stats))
