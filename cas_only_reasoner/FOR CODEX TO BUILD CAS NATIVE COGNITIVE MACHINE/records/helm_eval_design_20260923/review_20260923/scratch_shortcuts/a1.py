import json, itertools, collections
P="D:/tksCAS-worktrees/helm-integration/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/typed_course_001/checks_002/public_course.json"
d=json.load(open(P,encoding='utf-8'))
W=d['bank']['worlds']
def canon(n,E):
    best=None
    for p in itertools.permutations(range(n)):
        k=tuple(sorted((p[a],p[b]) for a,b in E))
        if best is None or k<best: best=k
    return (n,best)
def wgraph(w):
    refs=sorted(x['ref'] for x in w['nodes']); idx={r:i for i,r in enumerate(refs)}
    E=[(idx[c['source']],idx[c['target']]) for c in w['contains']]
    return refs,idx,E
shapes=collections.defaultdict(list)
for w in W:
    refs,idx,E=wgraph(w)
    shapes[canon(len(refs),E)].append(w)
print("worlds",len(W))
for s,ws in sorted(shapes.items(),key=lambda t:(t[0][0],t[0][1])):
    doms=collections.Counter(w['declarations']['domain'] for w in ws)
    kinds=collections.Counter(w['declarations']['kind'] for w in ws)
    print(s, len(ws), dict(doms), "distinct kinds",len(kinds))
# kind -> shapes
k2s=collections.defaultdict(set); f2s=collections.defaultdict(set); s2s=collections.defaultdict(set)
for s,ws in shapes.items():
    for w in ws:
        k2s[w['declarations']['kind']].add(s); f2s[w['declarations']['function']].add(s); s2s[w['declarations']['setting']].add(s)
print("kinds",len(k2s),"kinds mapping to 1 shape",sum(len(v)==1 for v in k2s.values()))
print("functions",len(f2s),"->1 shape",sum(len(v)==1 for v in f2s.values()))
print("settings",len(s2s),"->1 shape",sum(len(v)==1 for v in s2s.values()))
# Declared whole: is it a root? participants structural?
roots=0; wholeiscanonroot=0
for w in W:
    refs,idx,E=wgraph(w); n=len(refs)
    wh=idx[w['declared_whole']]
    indeg=[0]*n
    for a,b in E: indeg[b]+=1
    roots+= indeg[wh]==0
print("declared whole has indegree 0:",roots,"/",len(W))
# Participant-flag correspondence shortcut: map participant rank i -> participant rank i, leftover -> leftover
def isos(n,E1,E2):
    S2=set(E2); out=[]
    for p in itertools.permutations(range(n)):
        if set((p[a],p[b]) for a,b in E1)==S2: out.append(p)
    return out
tot=ok=0; okdeg=0; iso_pairs=0
for s,ws in shapes.items():
    for a in ws:
        for b in ws:
            if a is b: continue
            ra,ia,Ea=wgraph(a); rb,ib,Eb=wgraph(b); n=len(ra)
            pa=[ia[r] for r in a['declarations']['participants']]; pb=[ib[r] for r in b['declarations']['participants']]
            m={pa[i]:pb[i] for i in range(3)}
            la=[i for i in range(n) if i not in pa]; lb=[i for i in range(n) if i not in pb]
            for x,y in zip(la,lb): m[x]=y
            perm=tuple(m[i] for i in range(n))
            tot+=1
            if set((perm[x],perm[y]) for x,y in Ea)==set(Eb): ok+=1
print("participant-rank-flag mapping is a valid isomorphism on same-shape bank pairs:",ok,"/",tot)
