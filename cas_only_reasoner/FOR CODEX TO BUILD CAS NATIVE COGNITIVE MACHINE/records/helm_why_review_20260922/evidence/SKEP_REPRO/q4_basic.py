import json, math, sys, os
R=sys.argv[1]
d=os.path.join(R,'records','q4_authorized_20260922','run_001')
preds=[json.loads(l) for l in open(os.path.join(d,'dev_predictions.jsonl'))]
print('n preds',len(preds),'distinct ast',len({json.dumps(p['ast'],sort_keys=True) for p in preds}),'steps',{p['steps'] for p in preds},'outcomes',{p['outcome'] for p in preds})
u=[json.loads(l) for l in open(os.path.join(d,'updates.jsonl'))]
print('updates',len(u),'classes',{x['class'] for x in u},'lr',{x['learning_rate'] for x in u})
L=[x['loss'] for x in u]
print('first',repr(L[0]),'last',repr(L[-1]),'min',repr(min(L)),'argmin',L.index(min(L))+1)
print('ln34',repr(math.log(34)))
print('last16 mean',repr(sum(L[-16:])/16),'last32',repr(sum(L[-32:])/32))
for i in range(0,128,16): print(i+1,'-',i+16, repr(sum(L[i:i+16])/16))
res=json.load(open(os.path.join(d,'result.json')))
for k in ['actual_updates','learned_parameter_count','dev_by_depth','wall_seconds','elapsed_seconds']:
  print(k,res.get(k))
print([k for k in res if 'sec' in k or 'time' in k or 'wall' in k])
