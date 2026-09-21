#!/usr/bin/env python3
"""Offline mathematical illustrations, not Helm or CAS implementation tests."""
from fractions import Fraction as F
import json

def main() -> int:
    # Conditional on matching meanings: 10 Noetics x 4 Domains.
    indices = {(n,d): (4*n+d,10*d+n) for n in range(10) for d in range(4)}
    assert len({x[0] for x in indices.values()}) == 40
    assert len({x[1] for x in indices.values()}) == 40
    for (n,d),(a,b) in indices.items():
        assert (a//4,a%4)==(n,d) and (b%10,b//10)==(n,d)
    # Only the quoted modular rule, not all CAS expression operators.
    compose = lambda a,b: (a+b)%10
    assert all(compose(a,b)==compose(b,a) for a in range(10) for b in range(10))
    assert all(compose(compose(a,b),c)==compose(a,compose(b,c))
               for a in range(10) for b in range(10) for c in range(10))
    p=[[F(40,100),F(35,100),F(25,100)],
       [F(45,100),F(30,100),F(25,100)],
       [F(15,100),F(35,100),F(50,100)]]
    assert all(sum(row)==1 for row in p)
    assert all(sum(p[i][j] for i in range(3))==1 for j in range(3))
    picks=[max(range(3),key=lambda j: row[j]) for row in p]
    assert len(set(picks)) < 3
    # A bag sum loses order even with perfectly distinct primitive vectors.
    vectors={'a':(1,0,0),'minus':(0,1,0),'b':(0,0,1)}
    def bag(seq): return tuple(sum(vectors[t][j] for t in seq) for j in range(3))
    assert bag(['a','minus','b'])==bag(['b','minus','a'])
    print(json.dumps({'status':'PASS','scope':'Four mathematical illustrations only; no repository or learned model executed.',
        'groups':['forty_index_permutation','quoted_modulo_algebra','soft_matching_counterexample','bag_order_collision'],
        'hard_argmax_targets':picks,'unsupported_fraction_17_of_39':17/39},indent=2))
    return 0
if __name__=='__main__': raise SystemExit(main())
