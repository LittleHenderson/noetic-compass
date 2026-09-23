from math import comb
def tail(n,k,p): return sum(comb(n,i)*p**i*(1-p)**(n-i) for i in range(k,n+1))
def crit(n,p0,a=0.01):
    for k in range(n+1):
        if tail(n,k,p0)<=a: return k
for n in (18,40,60,80):
    k=crit(n,0.25); pw=tail(n,k,0.5)
    print(n,"crit",k,"power",round(pw,4),"3run",round(pw**3,4))
# sign test minimal b with c=0
for b in range(1,12):
    print("b",b,"c=0 p",0.5**b)
# minimal b given c for p<=0.01
def signp(b,c): return tail(b+c,b,0.5)
for c in range(0,8):
    b=next(b for b in range(1,200) if b>c and signp(b,c)<=0.01)
    print("c",c,"min b",b)
