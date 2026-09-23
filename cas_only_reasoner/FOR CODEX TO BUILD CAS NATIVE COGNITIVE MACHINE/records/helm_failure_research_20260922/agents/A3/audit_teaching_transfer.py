"""A3 bounded record audit: no project imports, models, numerical packages or writes outside A3.
Planned checks before execution: frozen identities; literal versus name-free graph overlap;
record/query/support exposure; independent deterministic labels and class balance; actual batch order.
Constants VIA and NO_MATCH are measured only as label marginals, not exact-answer model scores.
"""
from collections import Counter, defaultdict, deque
from hashlib import sha256
from itertools import permutations
from pathlib import Path
import ast, json, os, sys, threading, time, zipfile
START=time.monotonic()
WATCH=threading.Timer(115, lambda: os._exit(124)); WATCH.daemon=True; WATCH.start()
BASE=Path('cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_failure_research_20260922')
OUT=BASE/'agents/A3'
MAN=json.loads((BASE/'SOURCE_AND_EVIDENCE_MANIFEST.json').read_text(encoding='utf-8'))
RESULT={'scope':'Pinned course, development, six configs/source ZIPs and first-pass saved batches; no neural execution','identities':[], 'source_excerpts':[]}
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def digest(b):return sha256(b).hexdigest()
def record_file(path, expected=None):
 raw=Path(path).read_bytes(); h=digest(raw)
 if expected is not None: assert h==expected, (str(path),h,expected)
 RESULT['identities'].append({'path':str(path),'bytes':len(raw),'sha256':h,'manifest_match':None if expected is None else True})
 return raw
def read_artifact(s,name):
 a=next(a for a in s['artifacts'] if Path(a['path']).name==name)
 return record_file(a['path'],a['sha256_raw'])
def graph(w,colors=False):
 ns=sorted(n['ref'] for n in w['nodes']); ix={n:i for i,n in enumerate(ns)}
 es=tuple(sorted((ix[e['source']],ix[e['target']]) for e in w['contains']))
 cs=tuple((int(n==w['declared_whole']),w['declarations']['participants'].index(n)+1 if n in w['declarations']['participants'] else 0) for n in ns)
 assert len(ns)<=4
 best=None
 for p in permutations(range(len(ns))):
  edges=tuple(sorted((p[a],p[b]) for a,b in es))
  color=tuple(sorted((p[i],cs[i]) for i in range(len(ns)))) if colors else ()
  value=(len(ns),edges,color)
  best=value if best is None or value<best else best
 return canonical(best)
def iso_map(left,right):
 a=sorted(n['ref'] for n in left['nodes']);b=sorted(n['ref'] for n in right['nodes'])
 re={(e['source'],e['target']) for e in right['contains']}
 for order in permutations(b):
  mp=dict(zip(a,order))
  if {(mp[e['source']],mp[e['target']]) for e in left['contains']}==re:return mp
 return None
def reach(w,q):
 adj={n['ref']:[] for n in w['nodes']}
 for e in w['contains']:adj[e['source']].append(e['target'])
 for v in adj.values():v.sort()
 whole,part=q['arguments']['whole'],q['arguments']['part']
 if part in adj[whole]:return {'state':'DIRECT','via':None}
 def path(start):
  todo=deque([[start]]);seen={start}
  while todo:
   x=todo.popleft()
   if x[-1]==part:return x
   for nxt in adj[x[-1]]:
    if nxt not in seen:seen.add(nxt);todo.append(x+[nxt])
  return None
 if q['rule']=='first_direct_constituent_lexical_v1':
  for first in adj[whole]:
   if path(first):return {'state':'VIA','via':first}
 elif q['rule']=='bfs_immediate_predecessor_lexical_v1':
  p=path(whole)
  if p:return {'state':'VIA','via':p[-2]}
 else:raise AssertionError(q['rule'])
 return {'state':'ABSENT','via':None}
zip_members={}
for i,s in enumerate(MAN['subjects']):
 cfg=json.loads(read_artifact(s,'config.json'))
 raw=read_artifact(s,'source.zip')
 z=zipfile.ZipFile(Path(s['receipt_root'])/'source.zip')
 mats={}
 for n in ['records/typed_course_001/checks_002/public_course.json','records/typed_matched_001/development_001/compact_development.json','records/typed_interface_001/checks_002/training_tokenizer.json']:
  data=z.read(n);mats[n]={'sha256':digest(data),'bytes':len(data)}
 zip_members[f"{s['version']}/{s['seed']}"]=mats
 if i==0:
  COURSE=json.loads(z.read('records/typed_course_001/checks_002/public_course.json'))
  DEV=json.loads(z.read('records/typed_matched_001/development_001/compact_development.json'))
  CONFIG=cfg
 if i in (0,3):
  for fn,funcs in {'typed_teaching/practice_contract.py':['split','held_back_questions'], 'typed_teaching/course.py':['_public'], 'typed_teaching/pointer_inputs.py':['read_packet','_world_reading'], 'typed_teaching/checker.py':['_reach','_derive_values'], 'typed_teaching/pointer_learner.py':['_graph_blocks','_graph'], 'typed_teaching/development.py':['build_development']}.items():
   name='research/CAS_META_2_COMPOSITION/cas_meta2/'+fn; data=z.read(name);txt=data.decode();lines=txt.splitlines();tree=ast.parse(txt)
   entry={'version':s['version'],'source_commit':s['source_commit'],'member':name,'sha256':digest(data),'functions':[]}
   for node in ast.walk(tree):
    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in funcs:
     entry['functions'].append({'name':node.name,'start':node.lineno,'end':node.end_lineno,'lines':'\n'.join(f'{j}: {lines[j-1]}' for j in range(node.lineno,node.end_lineno+1))})
   RESULT['source_excerpts'].append(entry)
 RESULT.setdefault('configs',[]).append({'version':s['version'],'seed':s['seed'],'source_sha':cfg['source_sha'],'node_rank_feature':cfg['design']['node_rank_feature'],'schedule':cfg['design']['schedule'],'held_ids':cfg['design']['held_back_record_ids'],'excluded_ids':cfg['design']['excluded_record_ids']})
RESULT['zip_data_identities']=zip_members
assert len({canonical(v) for v in zip_members.values()})==1
W={w['world_id']:w for w in COURSE['bank']['worlds']};R={r['record_id']:r for r in COURSE['registry']}
held=set(CONFIG['design']['held_back_record_ids']);excluded=set(CONFIG['design']['excluded_record_ids']);trained=set(R)-held-excluded
HW=set(CONFIG['design']['held_worlds']);TW={R[k]['source_world_id'] for k in trained}
for c in RESULT['configs']:assert set(c.pop('held_ids'))==held and set(c.pop('excluded_ids'))==excluded
S={k:graph(w) for k,w in W.items()};CS={k:graph(w,True) for k,w in W.items()}
RESULT['graph_counts']={'worlds':len(W),'node_counts':dict(Counter(len(w['nodes']) for w in W.values())),'unrooted_directed_shapes':len(set(S.values())),'colored_shapes_declared_whole_participant_rank':len(set(CS.values())),'trained_focus_worlds':len(TW),'held_focus_worlds':len(HW)}
RESULT['held_structure_overlap']=[]
for h in sorted(HW):
 matches=sorted(t for t in TW if S[h]==S[t]);colored=sorted(t for t in TW if CS[h]==CS[t]);t=matches[0]
 RESULT['held_structure_overlap'].append({'held_world':h,'directed_shape':S[h],'trained_isomorphic_world_count':len(matches),'trained_colored_isomorphic_world_count':len(colored),'example_trained_world':t,'bijection':iso_map(W[h],W[t]),'held_edges':W[h]['contains'],'example_edges':W[t]['contains']})
RESULT['split_counts']={}
for name,ids in [('all',set(R)),('trained',trained),('held',held),('excluded',excluded)]:
 rows=[R[k] for k in sorted(ids)];questions={r['query']['query_id']:r for r in rows}
 RESULT['split_counts'][name]={'records':len(rows),'questions':len(questions),'kind_records':dict(Counter(r['query']['kind'] for r in rows)),'kind_questions':dict(Counter(r['query']['kind'] for r in questions.values())),'query_multiplicity':dict(Counter(Counter(r['query']['query_id'] for r in rows).values()))}
RESULT['exposure']={'trained_record_text_held_references':sum(any(h in canonical({k:v for k,v in r.items() if k!='record_id'}) for h in HW) for r in [R[k] for k in trained]),'trained_world_choice_records':dict(Counter(R[k]['query']['kind'] for k in trained if R[k]['query']['kind'] in ('definition','context','analogy'))),'full_bank_worlds_in_world_choice_reading':len(W),'held_worlds_in_world_choice_reading':sorted(HW),'supports_per_record':dict(Counter(len(r['supports']) for r in R.values())),'main_record_answer_keys':[{'record':r['record_id'],'keys':[k for k in r if 'answer' in k or 'target' in k]} for r in R.values() if any('answer' in k or 'target' in k for k in r)]}
RESULT['labels']={}
for name,rows,worlds in [('trained',[R[k] for k in sorted(trained)],W),('held',[R[k] for k in sorted(held)],W),('development',[r['record'] for r in DEV['records']],{w['world_id']:w for w in DEV['worlds']})]:
 rows=list({r['query']['query_id']:r for r in rows}.values());counts=Counter();details=[]
 for r in rows:
  q=r['query'];kind=q['kind'];w=worlds[q['focus_world_id']]
  if kind=='reach':
   val=reach(w,q);counts['reach:'+val['state']]+=1;details.append({'record_id':r['record_id'],'query_id':q['query_id'],'rule':q['rule'],'value':val})
  if kind=='correspondence':counts['correspondence:'+('MAPPING' if S[w['world_id']]==S[q['arguments']['target_world_id']] else 'NO_MATCH')]+=1
  if kind=='analogy':counts['analogy:matching_world_count:'+str(sum(S[k]==S[w['world_id']] and worlds[k]['declarations']['domain']!=w['declarations']['domain'] for k in W))]+=1
 RESULT['labels'][name]={'unique_question_class_counts':dict(sorted(counts.items())),'reach_labels':details}
RESULT['development']={'packets':len(DEV['records']),'focus_worlds':len({r['focus_world_id'] for r in DEV['records']}),'focus_node_counts':dict(Counter(len(next(w for w in DEV['worlds'] if w['world_id']==r['focus_world_id'])['nodes']) for r in DEV['records'])),'kind_packets':dict(Counter(r['record']['query']['kind'] for r in DEV['records'])),'training_focus_overlap':len({r['focus_world_id'] for r in DEV['records']}&set(W)),'metadata_policy':DEV['document_metadata'].get('policy')}
RESULT['actual_first_pass']=[]
orders=[]
for s in MAN['subjects']:
 batches=[json.loads(x) for x in read_artifact(s,'pass_01_batches.jsonl').splitlines()]
 sequence=[[p['record_id'] for p in batch['predictions']] for batch in batches]
 flat=[r for batch in sequence for r in batch];orders.append(sequence)
 RESULT['actual_first_pass'].append({'version':s['version'],'seed':s['seed'],'batches':len(sequence),'presentations':len(flat),'distinct_records':len(set(flat)),'distinct_questions':len({R[k]['query']['query_id'] for k in flat}),'kind_presentations':dict(Counter(R[k]['query']['kind'] for k in flat)),'record_repetition_histogram':dict(Counter(Counter(flat).values())),'question_repetition_histogram':dict(Counter(Counter(R[k]['query']['query_id'] for k in flat).values())),'every_batch_one_each_kind':all(len({R[k]['query']['kind'] for k in batch})==8 and len(batch)==8 for batch in sequence),'held_or_excluded_training_presentations':sum(k in held|excluded for k in flat),'world_choice_presentations':sum(R[k]['query']['kind'] in ('definition','context','analogy') for k in flat),'order_digest':digest(canonical(sequence).encode())})
RESULT['all_first_pass_record_orders_equal']=all(o==orders[0] for o in orders)
RESULT['elapsed_seconds']=round(time.monotonic()-START,6)
RESULT['counting_boundary']={'formal_test_functions':0,'diagnostic_program_runs':1,'repeat_runs':0,'data_variants':1,'study_configs':6,'source_packages':6,'first_pass_record_logs':6,'first_pass_rows_per_log':147,'all_bank_graph_cases':64,'held_overlap_cases':5,'development_packet_cases':len(DEV['records']),'models_loaded_or_run':0}
(OUT/'PROBE_RESULTS.json').write_text(json.dumps(RESULT,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
brief={k:v for k,v in RESULT.items() if k not in ['source_excerpts','identities','configs','zip_data_identities','held_structure_overlap','labels']}
brief['held_overlap_counts']=[{k:v for k,v in r.items() if k in ['held_world','trained_isomorphic_world_count','trained_colored_isomorphic_world_count']} for r in RESULT['held_structure_overlap']]
brief['label_counts']={k:v['unique_question_class_counts'] for k,v in RESULT['labels'].items()}
print(json.dumps(brief,indent=2)); WATCH.cancel()
