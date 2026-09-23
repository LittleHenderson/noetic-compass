"""F1 preregistered 10-instance saved reach decoder reconstruction; stdlib only."""
import hashlib,json,math,os,platform,threading,time,zipfile
from collections import deque
from pathlib import Path
start=time.monotonic()
watchdog=threading.Timer(115,lambda:os._exit(124));watchdog.daemon=True;watchdog.start()
base=Path(__file__).resolve().parent
manifest_path=base.parents[1]/'SOURCE_AND_EVIDENCE_MANIFEST.json'
manifest=json.loads(manifest_path.read_text(encoding='utf-8-sig'))
locators=json.loads((base/'lost_answers.json').read_text(encoding='utf-8'))
assert len(locators)==5 and len({r['query_id'] for r in locators})==2
fingerprints={}
def load_expected(row):
    path=Path(row['path']);raw=path.read_bytes();h=hashlib.sha256(raw).hexdigest()
    assert h==row['sha256_raw'] and len(raw)==row['bytes'],str(path)
    fingerprints[str(path)]={'sha256':h,'bytes':len(raw)}
    return raw
course_row=next(r for r in manifest['additional_required_sources'] if r['path'].endswith('public_course.json'))
course=json.loads(load_expected(course_row))
registry={r['record_id']:r for r in course['registry']}
worlds={w['world_id']:w for w in course['bank']['worlds']}
subjects={s['seed']:s for s in manifest['subjects'] if s['version'].startswith('Helm 2') and s['seed'] in (20260917,20260919)}
source_receipts=[]
source_ranges={'answers.py':[(135,169),(236,247)],'slots.py':[(28,36),(54,60),(63,84),(106,108),(243,249),(283,296),(344,348)],'pointer_learner.py':[(1446,1466),(1558,1564)]}
expected_members={'answers.py':'4d4cf21b65914c5b6878b58a52ab3cfe2f8864b319a3bb5ad1b95c6780686e5c','slots.py':'3d79db262708264dcd77cd7fb0296e7683849b5967b82d72fd3c51ab85f74487','pointer_learner.py':'21dabd21bb2909ff5990e2b11fd45b75558dce82992c34edfe12f8f556cd5084'}
for seed,subject in subjects.items():
    assert subject['source_commit']=='20208c923d41c24614504d4ecc2b289ecb66eda8'
    ziprow=next(a for a in subject['artifacts'] if a['path'].endswith('source.zip'))
    load_expected(ziprow)
    with zipfile.ZipFile(ziprow['path']) as z:
        for leaf,ranges in source_ranges.items():
            member='research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/'+leaf
            raw=z.read(member);h=hashlib.sha256(raw).hexdigest();assert h==expected_members[leaf]
            lines=raw.decode('utf-8').splitlines()
            source_receipts.append({'seed':seed,'archive':ziprow['path'],'member':member,'sha256':h,'lines':[{'number':n,'text':lines[n-1]} for lo,hi in ranges for n in range(lo,hi+1)]})
# Read original endpoint files, using old report only to locate the preregistered five record IDs.
predictions={}
for seed,subject in subjects.items():
    for phase in (0,10):
        suffix='course_p%02d_predictions.json'%phase
        row=next(a for a in subject['artifacts'] if Path(a['path']).name==suffix)
        doc=json.loads(load_expected(row))
        predictions[(seed,phase)]={p['record_id']:p for p in doc['predictions']}
rows=[]
for locator in locators:
    seed=locator['seed'];rid=locator['packet']['record_id'];packet=registry[rid];query=packet['query'];world=worlds[query['focus_world_id']]
    assert query['kind']=='reach' and query['query_id']==locator['query_id']
    refs=sorted(n['ref'] for n in world['nodes'])
    candidates=[('ABSENT',{'state':'ABSENT','via':None}),('DIRECT',{'state':'DIRECT','via':None})]+[('VIA_N'+str(i),{'state':'VIA','via':ref}) for i,ref in enumerate(refs)]
    # Independent path enumeration reconfirms the semantic target in these exact two unique-path graphs.
    edges=[(e['source'],e['target']) for e in world['contains']]
    origin=query['arguments']['whole'];target=query['arguments']['part'];queue=deque([[origin]]);paths=[]
    while queue:
        path=queue.popleft()
        if path[-1]==target:paths.append(path);continue
        for a,b in sorted(edges):
            if a==path[-1] and b not in path:queue.append(path+[b])
    assert len(paths)==1 and len(paths[0])==3
    correct={'state':'VIA','via':paths[0][-2] if query['rule']=='bfs_immediate_predecessor_lexical_v1' else paths[0][1]}
    correct_symbol=next(symbol for symbol,value in candidates if value==correct)
    for phase in (0,10):
        pred=predictions[(seed,phase)][rid]
        assert pred['answer']['query_id']==query['query_id'] and pred['answer']['kind']=='reach'
        scores=pred['scores'];assert len(scores)==1
        slot_id=next(iter(scores));raw=scores[slot_id]
        order=[symbol for symbol,_ in candidates]
        complete=set(raw)==set(order)
        finite=all(type(v) in (int,float) and math.isfinite(v) and abs(v)<=1000000 for v in raw.values())
        output={'seed':seed,'phase':phase,'record_id':rid,'query_id':query['query_id'],'slot_id':slot_id,'raw_prediction':pred,
            'candidate_order':order,'constructed_candidates':[{'symbol':s,'answer':a} for s,a in candidates],
            'all_candidate_scores_present':complete,'finite_and_within_frozen_bound':finite,'semantic_target':correct,
            'correct_symbol':correct_symbol,'unique_graph_path':paths[0],'normalization':'NONE in the actual reach selector; each symbol already denotes one complete answer.'}
        if not complete or not finite:
            output['classification']='INCOMPLETE_OR_NUMERIC_INVALID'
        else:
            # Translate first-maximum reference semantics into a strict-improvement scan.
            winner=order[0]
            for symbol in order[1:]:
                if raw[symbol]>raw[winner]:winner=symbol
            winner_answer=dict(candidates)[winner]
            max_value=raw[winner];ties=[s for s in order if raw[s]==max_value]
            ranking=sorted(order,key=lambda s:(-raw[s],order.index(s)))
            selected=pred['decisions']['selected'];expected_selection={slot_id:winner}
            match=selected==expected_selection and pred['answer']['value']==winner_answer and pred['decisions']['correspondence_candidate_id'] is None
            output.update({'translated_selected_symbol':winner,'translated_answer':winner_answer,'saved_selection_matches':match,
                'maximum_tie_symbols_in_declared_order':ties,'candidate_rank_order':ranking,
                'candidate_scores_and_ranks':[{'symbol':s,'raw_score':raw[s],'strict_score_rank':1+sum(raw[t]>raw[s] for t in order),'tie_order_rank':ranking.index(s)+1} for s in order],
                'selected_raw_score':raw[winner],'correct_raw_score':raw[correct_symbol],
                'correct_strict_rank':1+sum(raw[t]>raw[correct_symbol] for t in order),'correct_tie_order_rank':ranking.index(correct_symbol)+1,
                'winner_minus_correct':raw[winner]-raw[correct_symbol],
                'winner_margin_to_runnerup':raw[ranking[0]]-raw[ranking[1]],
                'classification':'DECODER_DISCREPANCY' if not match else 'CORRECT_SELECTION' if winner_answer==correct else 'WRONG_LEARNED_RANKING'})
        rows.append(output)
assert len(rows)==10
summary={'status':'COMPLETE','preregistration_commit_prefix':'259ed0be','dispatch_integration_commit_prefix':'5c128a33','source_commit':'20208c923d41c24614504d4ecc2b289ecb66eda8',
    'python':platform.python_version(),'probe_executions':1,'repeat_executions':0,'test_functions':0,'seed_cases':2,'unique_query_cases':2,'input_record_cases':5,'saved_prediction_instances':10,
    'all_finite':all(r['finite_and_within_frozen_bound'] for r in rows),'all_candidates_available':all(r['all_candidate_scores_present'] for r in rows),
    'decoder_discrepancies':sum(r['classification']=='DECODER_DISCREPANCY' for r in rows),
    'classifications':{name:sum(r['classification']==name for r in rows) for name in sorted({r['classification'] for r in rows})},
    'elapsed_seconds':time.monotonic()-start,'neural_execution':False,'implementation':'Independent stdlib translation; no project-module imports, historical decoder execution, or reconstruction of model-generated logits.',
    'scope_limit':'Full model-packet and slot-plan digest reconstruction not repeated; original candidate inventory, score coverage, chosen symbol, answer assembly, and exact tie rule checked for these ten instances only.'}
result={'summary':summary,'input_fingerprints':fingerprints,'manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),'source_receipts':source_receipts,'rows':rows}
with (base/'F1_RESULTS.json').open('w',encoding='utf-8',newline='\n') as f:json.dump(result,f,indent=2);f.write('\n')
stdout=json.dumps(summary,sort_keys=True)+'\n'
for r in rows:stdout+=json.dumps({k:r.get(k) for k in ('seed','phase','record_id','classification','translated_selected_symbol','selected_raw_score','correct_raw_score','correct_strict_rank','winner_minus_correct')},sort_keys=True)+'\n'
with (base/'F1_STDOUT.txt').open('w',encoding='utf-8',newline='\n') as f:f.write(stdout)
print(stdout,end='');watchdog.cancel()
