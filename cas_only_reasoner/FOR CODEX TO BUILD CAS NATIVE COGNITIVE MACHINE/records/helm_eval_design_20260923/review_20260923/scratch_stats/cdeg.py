import itertools, collections
from shapes import dags, canon
bank={canon(3,[(0,1),(1,2)]),canon(4,[(0,1),(0,2),(0,3)]),canon(4,[(0,1),(0,2),(1,3),(2,3)]),canon(4,[(0,1),(1,2),(2,3)]),canon(4,[(0,1),(0,2),(3,1)]),canon(4,[(0,1),(0,2),(1,3)])}
def deg(n,E):
    i=[0]*n;o=[0]*n
    for a,b in E:o[a]+=1;i[b]+=1
    return list(zip(i,o))
def cdeg_correct_frac(n,E):
    # focus labelling fixed canonical; target = all relabellings of E; lexical-first degree preserving permutation
    ok=tot=0
    for q in itertools.permutations(range(n)):
        T={(q[a],q[b]) for a,b in E}
        df,dt=deg(n,E),deg(n,T)
        first=None
        for p in itertools.permutations(range(n)):
            if all(df[x]==dt[p[x]] for x in range(n)): first=p;break
        tot+=1
        ok+= {(first[a],first[b]) for a,b in E}==T
    return ok/tot
for n in (3,4):
    S=dags(n); vals=[]
    for c in S:
        f=cdeg_correct_frac(n,list(c)); vals.append((c in bank,round(f,4)))
    new=[v for b,v in vals if not b]; old=[v for b,v in vals if b]
    print(n,"new",new,"mean",round(sum(new)/len(new),4),"bank",old)
