import json, os, sys, itertools
R=sys.argv[1]; T=os.path.join(R,'records','typed_pointer_001')
runs={('2.0',s):'receipt_'+s for s in ('20260917','20260918','20260919')}
runs.update({('1.0',s):'receipt_helm1_certified_'+s for s in ('20260917','20260918','20260919')})
A={}
for k,rd in runs.items():
    P=json.load(open(os.path.join(T,rd,'checkpoints','course_p10_predictions.json')))['predictions']
    A[k]={p['decisions']['record_id']:json.dumps(p['answer']['value'],sort_keys=True) for p in P if p['answer']['kind']=='reach'}
print({k:len(v) for k,v in A.items()})
for a,b in itertools.combinations(A,2):
    same=sum(A[a][r]==A[b][r] for r in A[a]); print(a,b,'same',same,'/',len(A[a]))
