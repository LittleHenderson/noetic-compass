import itertools, json, collections
def canon(n, edges):
    best=None
    for p in itertools.permutations(range(n)):
        k=tuple(sorted((p[a],p[b]) for a,b in edges))
        if best is None or k<best: best=k
    return best
def weak(n,edges):
    adj={i:set() for i in range(n)}
    for a,b in edges: adj[a].add(b); adj[b].add(a)
    seen={0}; st=[0]
    while st:
        x=st.pop()
        for y in adj[x]:
            if y not in seen: seen.add(y); st.append(y)
    return len(seen)==n
def dags(n):
    # edges i->j only for i<j in some topological order; enumerate all subsets of pairs i<j (covers all DAGs up to iso)
    pairs=[(i,j) for i in range(n) for j in range(i+1,n)]
    out={}
    for m in range(1<<len(pairs)):
        e=[pairs[k] for k in range(len(pairs)) if m>>k&1]
        if not e or not weak(n,e): continue
        c=canon(n,e)
        out.setdefault(c,e)
    return out
def degsig(n,edges):
    ind=[0]*n; outd=[0]*n
    for a,b in edges: outd[a]+=1; ind[b]+=1
    return tuple(sorted(zip(ind,outd)))
def autos(n,edges):
    E=set(edges); c=0
    for p in itertools.permutations(range(n)):
        if {(p[a],p[b]) for a,b in edges}==E: c+=1
    return c
def via_questions(n,edges):
    adj={i:sorted(b for a,b in edges if a==i) for i in range(n)}
    def reach(s,t):
        st=[s];seen={s}
        while st:
            x=st.pop()
            if x==t: return True
            for y in adj[x]:
                if y not in seen: seen.add(y); st.append(y)
        return False
    qs=[]
    for w in range(n):
        for p in range(n):
            if w==p or p in adj[w]: continue
            firsts=[c for c in adj[w] if reach(c,p)]
            if firsts: qs.append((w,p,len(firsts)))
    return qs
res={}
for n in (3,4,5):
    S=dags(n)
    sigs=collections.defaultdict(list)
    for c,e in S.items(): sigs[degsig(n,e)].append(c)
    collide=[v for v in sigs.values() if len(v)>1]
    res[n]={"shapes":len(S),"degree_sig_classes":len(sigs),"shapes_in_colliding_classes":sum(len(v) for v in collide),"colliding_classes":len(collide)}
    if n<=4:
        rows=[]
        for c,e in S.items():
            q=via_questions(n,list(c))
            # orbit reduce by automorphisms
            E=set(c); orbits=set()
            auts=[p for p in itertools.permutations(range(n)) if {(p[a],p[b]) for a,b in c}==E]
            for w,p,k in q:
                orbits.add(min((a[w],a[p]) for a in auts))
            roots=[i for i in range(n) if all(b!=i for a,b in c)]
            rq=[x for x in q if x[0] in roots]
            rows.append({"edges":list(c),"autos":len(auts),"via_labelled":len(q),"via_orbits":len(orbits),
                         "via_tie":sum(1 for x in q if x[2]>1),"via_from_roots":len(rq),"roots":len(roots)})
        res[n]["rows"]=rows
print(json.dumps({k:{kk:vv for kk,vv in v.items() if kk!="rows"} for k,v in res.items()}))
json.dump(res,open("shapes.json","w"),indent=1)
