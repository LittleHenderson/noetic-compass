import itertools, collections, json
def canon(n,E):
    best=None
    for p in itertools.permutations(range(n)):
        k=tuple(sorted((p[a],p[b]) for a,b in E))
        if best is None or k<best: best=k
    return best
def connected(n,E):
    adj={i:set() for i in range(n)}
    for a,b in E: adj[a].add(b); adj[b].add(a)
    seen={0}; st=[0]
    while st:
        x=st.pop()
        for y in adj[x]:
            if y not in seen: seen.add(y); st.append(y)
    return len(seen)==n
def classes(n):
    # all DAGs: orient pairs i<j under some topological order -> enumerate edge subsets of upper-triangular (every DAG iso to one)
    pairs=[(i,j) for i in range(n) for j in range(n) if i<j]
    out=set()
    for mask in range(1,1<<len(pairs)):
        E=[pairs[k] for k in range(len(pairs)) if mask>>k&1]
        if connected(n,E): out.add(canon(n,E))
    return sorted(out)
bank={3:{((0,1),(1,2))},4:{((0,1),(0,2),(0,3)),((0,1),(0,2),(1,3)),((0,1),(0,2),(1,3),(2,3)),((0,1),(0,2),(3,1)),((0,1),(1,2),(2,3))}}
def degsig(n,E):
    ind=[0]*n; out=[0]*n
    for a,b in E: out[a]+=1; ind[b]+=1
    return [(ind[i],out[i]) for i in range(n)]
def wl(n,E,rounds=4):
    col=[str(x) for x in degsig(n,E)]
    for _ in range(rounds):
        col=[col[i]+"|"+",".join(sorted(col[b] for a,b in E if a==i))+"|"+",".join(sorted(col[a] for a,b in E if b==i)) for i in range(n)]
    return col
def autos(n,E):
    S=set(E); return [p for p in itertools.permutations(range(n)) if set((p[a],p[b]) for a,b in E)==S]
def sig_matching_always_valid(n,E,sigf):
    # every bijection from a relabelled copy that preserves the signature classes is an isomorphism iff
    # #signature-preserving perms == #automorphisms
    s=sigf(n,E); S=set(E)
    pres=[p for p in itertools.permutations(range(n)) if all(s[i]==s[p[i]] for i in range(n))]
    ok=[p for p in pres if set((p[a],p[b]) for a,b in E)==S]
    return len(ok),len(pres)
def reach_state(n,E,w,p):
    adj={i:sorted(b for a,b in E if a==i) for i in range(n)}
    if p in adj[w]: return ("DIRECT",None)
    def bfs(s,g):
        seen={s}; q=[s]
        while q:
            x=q.pop(0)
            if x==g: return True
            for c in adj[x]:
                if c not in seen: seen.add(c); q.append(c)
        return False
    for c in adj[w]:
        if bfs(c,p): return ("VIA",c)
    return ("ABSENT",None)
res={}
for n in (3,4,5):
    C=classes(n)
    new=[c for c in C if c not in bank.get(n,set())]
    ds=collections.Counter(tuple(sorted(degsig(n,c))) for c in C)
    coll_new=sum(1 for c in new if ds[tuple(sorted(degsig(n,c)))]>1)
    wls=collections.Counter(tuple(sorted(wl(n,c))) for c in C)
    coll_wl=sum(1 for c in C if wls[tuple(sorted(wl(n,c)))]>1)
    degmatch=sum(1 for c in new if (lambda r: r[0]==r[1])(sig_matching_always_valid(n,c,degsig)))
    wlmatch=sum(1 for c in new if (lambda r: r[0]==r[1])(sig_matching_always_valid(n,c,wl)))
    # reach over all labellings (rank orders)
    via=tie=r1=two=0; via_shapes=0; shapes_no_via=0
    for c in new:
        has=False
        for perm in itertools.permutations(range(n)):
            E=[(perm[a],perm[b]) for a,b in c]
            adj={i:sorted(b for a,b in E if a==i) for i in range(n)}
            for w in range(n):
                for p in range(n):
                    if w==p: continue
                    st,v=reach_state(n,E,w,p)
                    if st!="VIA": continue
                    has=True; via+=1
                    # tie: more than one child with a path
                    cands=[ch for ch in adj[w] if reach_state(n,E,ch,p)[0]!="ABSENT" or ch==p]
                    cands=[ch for ch in adj[w] if (ch==p) or reach_state(n,E,ch,p)[0] in ("DIRECT","VIA")]
                    if len(cands)>1: tie+=1
                    if adj[w] and adj[w][0]==v: r1+=1      # lowest-rank child, no path check
                    # two-hop rule: lowest-rank child c with p in adj[c]
                    th=[ch for ch in adj[w] if p in adj[ch]]
                    if th and th[0]==v: two+=1
        if has: via_shapes+=1
        else: shapes_no_via+=1
    res[n]=dict(all=len(C),new=len(new),new_degmultiset_collide=coll_new,all_wl_collide=coll_wl,
               new_deg_signature_matching_always_valid=degmatch,new_wl_matching_always_valid=wlmatch,
               via_questions_all_labellings=via,via_ties=tie,rule_lowest_rank_child=r1,rule_two_hop=two,
               new_shapes_with_no_via=shapes_no_via)
    print(n,res[n],flush=True)
