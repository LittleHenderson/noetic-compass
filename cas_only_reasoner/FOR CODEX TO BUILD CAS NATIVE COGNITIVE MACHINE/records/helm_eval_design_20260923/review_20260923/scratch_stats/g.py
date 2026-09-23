import json, collections, re
D="D:/tksCAS-worktrees/helm-integration/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/research/helm_cas_expression_lab/data/q3_v0_7/"
def load(f): return [json.loads(l) for l in open(D+f,encoding='utf-8') if l.strip()]
def parse(s):
    i=0
    def node():
        nonlocal i
        if s[i]=='(':
            i+=1; l=node()
            while s[i]==' ': i+=1
            op=s[i]; i+=1
            while s[i]==' ': i+=1
            r=node()
            assert s[i]==')',(s,i); i+=1
            return ('N',op,l,r)
        j=i
        depth=0
        while i<len(s) and not (depth==0 and s[i] in ' )'):
            if s[i]=='{': depth+=1
            if s[i]=='}': depth-=1
            i+=1
        return ('L',s[j:i])
    t=node(); assert i==len(s),(s,i); return t
def bare(t): return '*' if t[0]=='L' else '('+bare(t[2])+bare(t[3])+')'
def opshape(t): return '*' if t[0]=='L' else '('+opshape(t[2])+t[1]+opshape(t[3])+')'
def depth(t): return 0 if t[0]=='L' else 1+max(depth(t[2]),depth(t[3]))
def leaves(t): return [t[1]] if t[0]=='L' else leaves(t[2])+leaves(t[3])
tr=load('visible_G_train.jsonl'); dv=load('visible_G_dev.jsonl')
T=[parse(r['observation']) for r in tr]; V=[parse(r['observation']) for r in dv]
print("train",len(tr),"unique strings",len({r['observation'] for r in tr}))
bt=collections.Counter(bare(t) for t in T); bd=collections.Counter(bare(t) for t in V)
print("train bare shapes",len(bt),"dev bare shapes",len(bd),"shared",len(set(bt)&set(bd)))
print("train depth",collections.Counter(depth(t) for t in T),"dev depth",collections.Counter(depth(t) for t in V))
print("train op-shapes",len({opshape(t) for t in T}),"dev op-shapes",len({opshape(t) for t in V}))
print("train shape counts",sorted(bt.values()))
for N in (8,16,256,2048):
    teach=T[:N]; tshapes={bare(t) for t in teach}; tstr={r['observation'] for r in tr[:N]}
    fam=[i for i in range(N,len(T)) if bare(T[i]) in tshapes and tr[i]['observation'] not in tstr]
    # also exclude rows whose leaf sequence identical to some teaching row?
    tleaf={tuple(leaves(t)) for t in teach}
    fam_leaf_rep=sum(1 for i in fam if tuple(leaves(T[i])) in tleaf)
    topsh={opshape(t) for t in teach}
    fam_op=sum(1 for i in fam if opshape(T[i]) in topsh)
    print("N",N,"teach shapes",len(tshapes),"familiar rows",len(fam),"of which leaf-seq repeats",fam_leaf_rep,"same op-shape",fam_op,
          "familiar shape dist",sorted(collections.Counter(bare(T[i]) for i in fam).values()))
# leaves atom overlap dev vs train
la=set(x for t in T for x in leaves(t)); print("dev leaf atoms unseen in train",sum(1 for t in V for x in leaves(t) if x not in la))
