import json, os, sys
from fractions import Fraction
from math import comb
R=sys.argv[1]; T=os.path.join(R,'records','typed_pointer_001')
A=json.load(open(os.path.join(T,'trust_anchor_helm2_experimental_20208c92.json')))
kind_of=A['population']['kind_of']; world_of=A['population']['world_of']; pop=sorted(kind_of)
print('pop',len(pop))
def tail(b,n): return Fraction(sum(comb(n,k) for k in range(b,n+1)),2**n)
def load(rd,ph):
    s=json.load(open(os.path.join(T,rd,'checkpoints','%s_scoring.json'%ph)))
    return {r['query_id']:r['correct'] for r in s['rows']}
def test(before,after):
    b=[q for q in pop if not before[q] and after[q]]; c=[q for q in pop if before[q] and not after[q]]
    p=tail(len(b),len(b)+len(c))
    ok=len(b)>len(c) and p<=Fraction(1,100) and len({kind_of[q] for q in b})>=2 and len({world_of[q] for q in b})>=2
    return len(b),len(c),p,ok
runs={('2.0',s):'receipt_'+s for s in ('20260917','20260918','20260919')}
runs.update({('1.0',s):'receipt_helm1_certified_'+s for s in ('20260917','20260918','20260919')})
starts={k:load(v,'course_p00') for k,v in runs.items()}
q369=[q for q in pop if '36988555' in q][0]
fin=load(runs[('2.0','20260919')],'course_p10')
print('2.0/20260919 final vs each start:')
for k,st in starts.items(): print('  start',k,'36988555 right at start',st[q369],'->',test(st,fin))
print('2.0/20260919 checkpoints vs own start:')
for ph in ('heldback_p02','heldback_p04','heldback_p06','heldback_p08','course_p10'):
    print('  ',ph,test(starts[('2.0','20260919')],load(runs[('2.0','20260919')],ph)))
print('course_p01',test(starts[('2.0','20260919')],load(runs[('2.0','20260919')],'course_p01')))
for ph in ('heldback_p08','course_p10'):
    P=json.load(open(os.path.join(T,runs[('2.0','20260919')],'checkpoints','%s_predictions.json'%ph)))['predictions']
    for p in P:
        if p['answer']['query_id']==q369: print(ph, json.dumps(p['answer']['value']), json.dumps(p.get('decisions'))[:1500])
