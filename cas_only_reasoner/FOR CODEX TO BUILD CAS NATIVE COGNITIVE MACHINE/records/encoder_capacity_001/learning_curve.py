import pickle, pathlib, math, random
CACHE = pathlib.Path(r"C:\Users\wakil\AppData\Local\Temp\cncm_analysis\rowdb.pkl")
feats = pickle.loads(CACHE.read_bytes())
print(f"cached rows: {len(feats)}")

def mat_inv(A):
    n=len(A); M=[row[:]+[1.0 if i==j else 0.0 for j in range(n)] for i,row in enumerate(A)]
    for col in range(n):
        piv=max(range(col,n), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col])<1e-12: return None
        M[col],M[piv]=M[piv],M[col]; pv=M[col][col]; M[col]=[x/pv for x in M[col]]
        for r in range(n):
            if r!=col and M[r][col]:
                f=M[r][col]; M[r]=[a-f*b for a,b in zip(M[r],M[col])]
    return [row[n:] for row in M]

def ridge_cv(X,y,nclass=64,folds=5,lam=1.0):
    n=len(X); order=list(range(n)); buckets=[order[i::folds] for i in range(folds)]; correct=0
    for f in range(folds):
        test=sorted(buckets[f]); trm=set(test); tr=[i for i in order if i not in trm]; nt=len(tr)
        K=[[0.0]*nt for _ in range(nt)]
        for a in range(nt):
            xa=X[tr[a]]
            for b in range(a,nt):
                s=sum(p*q for p,q in zip(xa,X[tr[b]])); K[a][b]=s; K[b][a]=s
        for a in range(nt): K[a][a]+=lam
        inv=mat_inv(K)
        if inv is None: continue
        A=[[sum(inv[a][b]*(1.0 if y[tr[b]]==c else 0.0) for b in range(nt)) for c in range(nclass)] for a in range(nt)]
        for i in test:
            xi=X[i]; sc=[0.0]*nclass
            for a in range(nt):
                k=sum(p*q for p,q in zip(xi,X[tr[a]]))
                if k:
                    Aa=A[a]
                    for c in range(nclass): sc[c]+=k*Aa[c]
            if max(range(nclass), key=lambda c: sc[c])==y[i]: correct+=1
    return correct/n

random.seed(3)
idx=list(range(len(feats)))
print()
print("LEARNING CURVE: does more data raise decodability of the focus world?")
print("chance = 1.5625%")
print()
print(f"  {'n samples':>10s} {'mean (64d)':>13s} {'query (64d)':>13s} {'head (576d)':>13s}")
for n in (50,100,150,200,300,400,500,len(feats)):
    if n>len(feats): continue
    sub=random.sample(idx, n)
    ys=[feats[i]['focus'] for i in sub]
    row=f"  {n:10d}"
    for key in ('mean','query','cat_head'):
        X=[feats[i][key] for i in sub]
        row+=f"{100*ridge_cv(X,ys):12.2f}%"
    print(row, flush=True)
