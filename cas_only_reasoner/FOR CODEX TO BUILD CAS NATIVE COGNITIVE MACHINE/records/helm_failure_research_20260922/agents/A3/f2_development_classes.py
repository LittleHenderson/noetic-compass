"""F2: one bounded stdlib saved-development analysis; no project imports or new predictions.
Predeclared outcomes: aggregate mainly tracks ABSENT; positive-path exact improvement;
or mixed version/seed outcomes. Registered at integration 259ed0be and selected 5c128a33.
"""
from collections import Counter, deque
from hashlib import sha256
from pathlib import Path
import json, os, sys, threading, time, zipfile
started=time.monotonic()
stop=threading.Timer(115, lambda: os._exit(124));stop.daemon=True;stop.start()
base=Path('cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_failure_research_20260922')
out=base/'agents/A3'
manifest=json.loads((base/'SOURCE_AND_EVIDENCE_MANIFEST.json').read_text(encoding='utf-8'))
plan=Path('C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/_worktrees/helm-failure-research')/base/'FOLLOWUP_PLAN.md'
result={'probe':'F2','preregistration_commit':'259ed0be','selection_commit':'5c128a33','plan_sha256':sha256(plan.read_bytes()).hexdigest(),'inputs':[],'source_members':[],'targets':[],'subjects':[],'scoring_disagreements':[]}
def read_artifact(subject,name):
 a=next(x for x in subject['artifacts'] if Path(x['path']).name==name)
 raw=Path(a['path']).read_bytes();h=sha256(raw).hexdigest()
 assert h==a['sha256_raw'] and len(raw)==a['bytes'],a['path']
 result['inputs'].append({'path':a['path'],'sha256':h,'bytes':len(raw),'manifest_match':True})
 return raw

def exact_value(world,query):
 nodes={n['ref'] for n in world['nodes']};adj={n:[] for n in nodes}
 assert world['contains_inventory_complete'] is True
 for e in world['contains']:adj[e['source']].append(e['target'])
 for children in adj.values():children.sort()
 whole=query['arguments']['whole'];assert whole in nodes
 if query['kind']=='parts':
  assert query['rule']=='direct_contains_v1'
  return {'nodes':adj[whole]}
 assert query['kind']=='reach'
 part=query['arguments']['part'];assert part in nodes
 if part in adj[whole]:return {'state':'DIRECT','via':None}
 def path(start):
  queue=deque([[start]]);seen={start}
  while queue:
   p=queue.popleft()
   if p[-1]==part:return p
   for nxt in adj[p[-1]]:
    if nxt not in seen:seen.add(nxt);queue.append(p+[nxt])
  return None
 if query['rule']=='first_direct_constituent_lexical_v1':
  for first in adj[whole]:
   if path(first):return {'state':'VIA','via':first}
 elif query['rule']=='bfs_immediate_predecessor_lexical_v1':
  p=path(whole)
  if p is not None:return {'state':'VIA','via':p[-2]}
 else:raise AssertionError(query['rule'])
 return {'state':'ABSENT','via':None}

compact_pin=None
for subject in manifest['subjects']:
 read_artifact(subject,'source.zip')
 with zipfile.ZipFile(Path(subject['receipt_root'])/'source.zip') as z:
  member='records/typed_matched_001/development_001/compact_development.json';raw=z.read(member);pin=sha256(raw).hexdigest()
  result['source_members'].append({'version':subject['version'],'seed':subject['seed'],'member':member,'sha256':pin,'bytes':len(raw)})
  if compact_pin is None:
   compact_pin=pin;dev=json.loads(raw)
   check=z.read('research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/checker.py');lines=check.decode().splitlines()
   result['semantics_source']={'member':'research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/checker.py','sha256':sha256(check).hexdigest(),'lines_129_199':'\n'.join(f'{i}: {lines[i-1]}' for i in range(129,200))}
  else:assert compact_pin==pin
assert compact_pin=='5780ffacf3f36ed6d17522fc875212f5239c98f11ba1dda3c56b9967309200b4'
worlds={w['world_id']:w for w in dev['worlds']}
records={x['record']['record_id']:x for x in dev['records']}
assert len(records)==59
truth={}
for rid,row in records.items():
 q=row['record']['query'];value=exact_value(worlds[row['focus_world_id']],q)
 group=value['state'] if q['kind']=='reach' else 'PARTS'
 answer={'schema':'cas.typed-teaching-answer/0.1','query_id':q['query_id'],'kind':q['kind'],'value':value}
 truth[rid]={'record_id':rid,'query_id':q['query_id'],'world_id':row['focus_world_id'],'rule':q['rule'],'arguments':q['arguments'],'group':group,'answer':answer}
result['targets']=list(truth.values())
assert len({t['query_id'] for t in truth.values()})==59
counts=Counter(t['group'] for t in truth.values());assert counts=={'ABSENT':42,'DIRECT':8,'VIA':3,'PARTS':6}
result['class_denominators']=dict(counts)
for subject in manifest['subjects']:
 entry={'version':subject['version'],'seed':subject['seed'],'source_commit':subject['source_commit'],'endpoints':{},'paired':{}}
 correctness={}
 for phase in ['p00','p10']:
  saved=json.loads(read_artifact(subject,f'development_{phase}_predictions.json'))
  scoring=json.loads(read_artifact(subject,f'development_{phase}_scoring.json'))
  predictions={p['record_id']:p for p in saved['predictions']};scored={p['record_id']:p for p in scoring['rows']}
  assert len(predictions)==len(saved['predictions'])==len(scored)==59
  assert set(predictions)==set(scored)==set(records)
  summary={g:{'total':n,'correct':0,'mode_correct':0 if g!='PARTS' else None,'predicted_states':Counter()} for g,n in counts.items()}
  checked=[];correctness[phase]={}
  for rid,t in truth.items():
   prediction=predictions[rid];answer=prediction['answer'];correct=answer==t['answer'];historical=scored[rid]
   assert answer['query_id']==t['query_id'] and answer['kind']==t['answer']['kind']
   assert historical['prediction_id']==prediction['prediction_id'] and historical['query_id']==t['query_id']
   if correct!=historical['correct']:result['scoring_disagreements'].append({'subject':subject['job'],'phase':phase,'record_id':rid,'independent':correct,'saved':historical['correct']})
   group=t['group'];summary[group]['correct']+=int(correct);correctness[phase][rid]=correct
   if group!='PARTS':
    summary[group]['mode_correct']+=int(answer['value']['state']==t['answer']['value']['state'])
    summary[group]['predicted_states'][answer['value']['state']]+=1
   checked.append({'record_id':rid,'query_id':t['query_id'],'group':group,'saved_answer':answer,'independent_correct':correct,'historical_correct':historical['correct'],'prediction_id':prediction['prediction_id']})
  total=sum(s['correct'] for s in summary.values())
  assert total==scoring['correct'] and scoring['total']==59
  entry['endpoints'][phase]={'classes':summary,'correct_total':total,'total':59,'checked':checked}
 for g in counts:
  keys=[k for k,t in truth.items() if t['group']==g]
  entry['paired'][g]={'gains':sum(not correctness['p00'][k] and correctness['p10'][k] for k in keys),'losses':sum(correctness['p00'][k] and not correctness['p10'][k] for k in keys)}
 result['subjects'].append(entry)
assert not result['scoring_disagreements']
result['execution']={'python':sys.version,'elapsed_seconds':time.monotonic()-started,'formal_test_functions':0,'substantive_executions':1,'repeat_executions':0,'subjects':6,'unique_data_packets':59,'unique_queries':59,'focus_worlds':6,'prediction_files':12,'saved_scoring_crosscheck_files':12,'prediction_instances':708,'reach_prediction_instances':636,'parts_prediction_instances':72,'model_operations':0,'exit_status':'completed_no_assertion_failure'}
(out/'F2_RESULTS.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print('version,seed,ABSENT/42,DIRECT/8,VIA/3,PARTS/6,ALL/59')
for s in result['subjects']:
 a,b=s['endpoints']['p00'],s['endpoints']['p10']
 values=[f"{a['classes'][g]['correct']}->{b['classes'][g]['correct']}" for g in ['ABSENT','DIRECT','VIA','PARTS']]
 print(','.join([s['version'],str(s['seed']),*values,f"{a['correct_total']}->{b['correct_total']}"]))
print(json.dumps(result['execution'],indent=2));print('scoring_disagreements',len(result['scoring_disagreements']));stop.cancel()
