from fractions import Fraction
from math import comb
def tail(b,n): return Fraction(sum(comb(n,k) for k in range(b,n+1)),2**n)
A=Fraction(1,100)
g_not_r=[];r_not_g=[]
for b in range(0,19):
    for c in range(0,19-b):
        g = b>c and tail(b,b+c)<=A
        r = b>=7 and c==0
        if g and not r: g_not_r.append((b,c))
        if r and not g: r_not_g.append((b,c))
print('grader passes, rescorer fails',len(g_not_r),g_not_r)
print('rescorer passes, grader fails',len(r_not_g))
for b,c in [(11,1),(12,0),(7,1),(10,1),(9,1),(10,0),(11,0)]: print(b,c,tail(b,b+c),float(tail(b,b+c)))
