import itertools, collections
exec(open('dagenum.py').read().split('res={}')[0])
for n in (3,4):
    C=classes(n); new=[c for c in C if c not in bank.get(n,set())]
    ds=collections.defaultdict(list)
    for c in C: ds[tuple(sorted(degsig(n,c)))].append(c)
    print(n,"degree-multiset collisions:",[v for v in ds.values() if len(v)>1])
    tot=rl=0; per=[]
    for c in new:
        v=t=r1=rlc=0
        for perm in itertools.permutations(range(n)):
            E=[(perm[a],perm[b]) for a,b in c]
            adj={i:sorted(b for a,b in E if a==i) for i in range(n)}
            for w in range(n):
                for p in range(n):
                    if w==p: continue
                    st,via=reach_state(n,E,w,p)
                    if st!="VIA": continue
                    v+=1
                    if via==n-1: rlc+=1
                    if adj[w][0]==via: r1+=1
                    if sum(1 for ch in adj[w] if ch==p or reach_state(n,E,ch,p)[0]!="ABSENT")>1: t+=1
        per.append((c,v//1,t,r1,rlc))
        tot+=v; rl+=rlc
    for row in per: print(" ",row)
    print(n,"VIA total",tot,"rank-last correct",rl)
