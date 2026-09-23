import json
ROOT = r"C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/q4-live/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE"
A = ROOT+'/records/typed_pointer_001/receipt_20260917/collected/results/artifacts/'
s = json.load(open(A+'course_p00_scoring.json','rb'))
print(type(s), list(s.keys()) if isinstance(s, dict) else len(s))
for k,v in s.items():
    if k!='rows': print(k, str(v)[:300])
print(len(s['rows'])); print(s['rows'][0])
p = json.load(open(A+'course_p00_predictions.json','rb'))
print(type(p), list(p.keys()) if isinstance(p, dict) else len(p))
for k,v in p.items():
    if not isinstance(v, list): print(k, str(v)[:300])
    else: print(k, 'list', len(v), str(v[0])[:600])
r = json.load(open(A+'retention_before_scoring.json','rb'))
print('ret keys', list(r.keys()), len(r['rows']))
for k,v in r.items():
    if k!='rows': print(k, str(v)[:300])
w = json.load(open(A+'worker_report.json','rb'))
print('wr keys', list(w.keys()))
print('retention_scores', json.dumps(w.get('retention_scores'))[:1500])
print('development_scores', json.dumps(w.get('development_scores'))[:1500])
