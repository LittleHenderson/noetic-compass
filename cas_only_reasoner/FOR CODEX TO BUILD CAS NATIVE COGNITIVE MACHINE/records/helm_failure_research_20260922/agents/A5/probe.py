"""A5 preregistered stdlib saved-record/algebra probe. Never imports project code."""
import collections, datetime, hashlib, itertools, json, math, pathlib, sys, time, zipfile
START=time.monotonic()
ROOT=pathlib.Path(__file__).resolve().parent
BASE=ROOT.parent.parent
M=json.loads((BASE/'SOURCE_AND_EVIDENCE_MANIFEST.json').read_text('utf-8-sig'))
FINGERPRINTS=[]
def load(row):
    p=pathlib.Path(row['path']); raw=p.read_bytes(); h=hashlib.sha256(raw).hexdigest()
    assert h==row['sha256_raw'], str(p)
    FINGERPRINTS.append({'path':str(p),'bytes':len(raw),'sha256':h})
    return json.loads(raw)
def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def digest(x): return hashlib.sha256(canon(x).encode()).hexdigest()
def lse(x):
    a=max(x);return a+math.log(sum(math.exp(v-a) for v in x))
def deadline():
    if time.monotonic()-START>110: raise TimeoutError('A5 110-second internal deadline')
C=load(next(x for x in M['additional_required_sources'] if x['path'].endswith('public_course.json')))
W={w['world_id']:w for w in C['bank']['worlds']}; IDS=sorted(W); WA={w:'W'+str(i) for i,w in enumerate(IDS)}
R={r['record_id']:r for r in C['registry']}
N={w:sorted(x['ref'] for x in z['nodes']) for w,z in W.items()}
E={w:{(e['source'],e['target']) for e in z['contains']} for w,z in W.items()}
D={w:{n:(sum(b==n for a,b in E[w]),sum(a==n for a,b in E[w])) for n in N[w]} for w in W}
SIG={w:sorted(D[w].values()) for w in W}
CACHE={}
def maps(a,b,mode='exact'):
    key=a,b,mode
    if key not in CACHE:
        vals=[]
        if len(N[a])==len(N[b]):
            for perm in itertools.permutations(N[b]):
                mp=dict(zip(N[a],perm))
                ok=all(D[a][n]==D[b][mp[n]] for n in N[a]) if mode=='degree' else {(mp[u],mp[v]) for u,v in E[a]}==E[b]
                if ok: vals.append(perm)
        CACHE[key]=vals
    return CACHE[key]
def map_value(a,perm):
    return {'status':'MAPPING','pairs':[{'source':n,'target':p} for n,p in zip(N[a],perm)]} if perm is not None else {'status':'NO_MATCH','pairs':[]}
def values(q):
    a=q['focus_world_id']
    if q['kind']=='analogy':
        vs=[{'world_id':b} for b in IDS if W[b]['declarations']['domain']!=W[a]['declarations']['domain'] and maps(a,b)]
        return vs or [{'world_id':None}]
    b=q['arguments']['target_world_id']; p=maps(a,b)
    return [map_value(a,x) for x in p] or [map_value(a,None)]
def simple(q):
    a=q['focus_world_id']
    if q['kind']=='analogy':
        diff=[b for b in IDS if W[b]['declarations']['domain']!=W[a]['declarations']['domain']]
        degree=[b for b in diff if SIG[a]==SIG[b]]
        exact=[b for b in diff if maps(a,b)]
        return {k:{'world_id':v[0] if v else None} for k,v in [('name',diff),('degree',degree),('exact',exact)]}
    b=q['arguments']['target_world_id']
    return {'name':map_value(a,tuple(N[b]) if len(N[a])==len(N[b]) else None), **{k:map_value(a,maps(a,b,k)[0] if maps(a,b,k) else None) for k in ['degree','exact']}}
TARGET={rid:values(r['query']) for rid,r in R.items() if r['query']['kind'] in ['analogy','correspondence']}
SIMPLE={rid:simple(R[rid]['query']) for rid in TARGET}
def slot(pred,q,field,coordinates,symbols,scope):
    body={'field':field,'group':'correspondence','coordinates':coordinates,'scope_world_id':scope,'scope_alias':WA[scope],'symbols':symbols}
    sid='typed-slot-'+digest({'packet_digest':pred['packet_digest'],**body})
    assert sid in pred['scores'], ('slot_id_mismatch',pred['record_id'],sid)
    return pred['scores'][sid]
def inspect_pred(p):
    rid=p['record_id'];q=R[rid]['query']; a=q['focus_world_id'];valid=TARGET[rid]
    row={'record_id':rid,'query_id':q['query_id'],'kind':q['kind'],'correct':p['answer']['value'] in valid,'valid_count':len(valid)}
    if q['kind']=='analogy':
        scores=next(iter(p['scores'].values())); syms=['NO_MATCH']+[WA[x] for x in IDS]; vv={WA[x['world_id']] if x['world_id'] else 'NO_MATCH' for x in valid}
        win=max(syms,key=lambda s:scores[s]); top=max(scores.values());best=max(scores[x] for x in vv)
        row.update(decoded={'world_id':None if win=='NO_MATCH' else IDS[int(win[1:])]},top_ties=sum(scores[x]==top for x in syms),top_tie_valid=sum(scores[x]==top and x in vv for x in syms),best_valid_rank=1+sum(scores[x]>best for x in syms))
    else:
        b=q['arguments']['target_world_id']; mode=slot(p,q,'mode',[],['NO_MATCH','MAPPING'],a)
        ms=[slot(p,q,'mapping_target',[n],['N'+str(j) for j in range(len(N[b]))],b) for n in N[a]]
        perms=list(itertools.permutations(range(len(N[b])))) if len(N[a])==len(N[b]) else []
        raw=[sum(ms[i]['N'+str(j)] for i,j in enumerate(perm)) for perm in perms]
        vals=[map_value(a,None)]+[map_value(a,[N[b][j] for j in perm]) for perm in perms]
        score=[0.] if not raw else [mode['NO_MATCH']-lse(list(mode.values()))]+[mode['MAPPING']-lse(list(mode.values()))+v-lse(raw) for v in raw]
        winner=max(range(len(score)),key=lambda i:score[i]);best=max(score[i] for i,v in enumerate(vals) if v in valid)
        mode_win=0 if not raw or mode['NO_MATCH']>=mode['MAPPING'] else 1+max(range(len(raw)),key=lambda i:raw[i])
        rowmax=[max(range(len(N[b])),key=lambda j:m['N'+str(j)]) for m in ms]
        row.update(decoded=vals[winner],top_ties=sum(s==max(score) for s in score),top_tie_valid=sum(s==max(score) and v in valid for s,v in zip(score,vals)),best_valid_rank=1+sum(s>best for s in score),mapping_total_spread=max(raw)-min(raw) if raw else None,matrix_identical_rows=all(m==ms[0] for m in ms),independent_row_argmax_duplicates=len(set(rowmax))<len(rowmax),mode_first_correct=vals[mode_win] in valid,mode_first_changes=mode_win!=winner,status=p['answer']['value']['status'],mapping_is_bijective=p['answer']['value']['status']!='MAPPING' or (sorted(x['source'] for x in p['answer']['value']['pairs'])==N[a] and sorted(x['target'] for x in p['answer']['value']['pairs'])==N[b]))
    row['decoder_matches_saved']=row['decoded']==p['answer']['value']
    assert row['decoder_matches_saved'],('decoder_mismatch',rid)
    return row
RESULT={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'preregistration_sha256':hashlib.sha256((ROOT/'PREREGISTRATION.md').read_bytes()).hexdigest(),'comparisons':{},'runs':[],'algebra':[]}
HELD=None
for s in M['subjects']:
    deadline()
    arts={pathlib.Path(x['path']).name:x for x in s['artifacts']}
    for phase in ['course_p00','course_p10','ablation_baseline']:
        preds=load(arts[phase+'_predictions.json'])['predictions'];scoring=load(arts[phase+'_scoring.json']); sr={r['record_id']:r for r in scoring['rows']}
        if phase=='ablation_baseline':
            ids={p['record_id'] for p in preds}
            if HELD is None:HELD=ids
            assert HELD==ids
        rows=[]
        for p in preds:
            if p['record_id'] not in TARGET:continue
            row=inspect_pred(p); row['checker_agrees']=row['correct']==sr[p['record_id']]['correct']; assert row['checker_agrees']
            rows.append(row)
        RESULT['runs'].append({'version':s['version'],'seed':s['seed'],'phase':phase,'all_kind_records':len(preds),'rows':rows})
for scope,ids in [('all',set(TARGET)),('held',HELD&set(TARGET))]:
    RESULT['comparisons'][scope]={}
    for kind in ['analogy','correspondence']:
        selected=[rid for rid in sorted(ids) if R[rid]['query']['kind']==kind]
        RESULT['comparisons'][scope][kind]={'records':len(selected),'methods':{method:sum(SIMPLE[rid][method] in TARGET[rid] for rid in selected) for method in ['name','degree','exact']},'valid_counts':dict(collections.Counter(len(TARGET[rid]) for rid in selected)),'rows':[{'record_id':rid,'valid_count':len(TARGET[rid]),'correct':{method:SIMPLE[rid][method] in TARGET[rid] for method in SIMPLE[rid]}} for rid in selected]}
for n in [2,3,4]:
    mats=[[[0. for j in range(n)] for i in range(n)],[[float(j-2) for j in range(n)] for i in range(n)],[[float(i==j)*3 for j in range(n)] for i in range(n)],[[float((i*7+j*3+i*j)%11-5) for j in range(n)] for i in range(n)]]
    for tag,mat in zip(['zero','column_only','identity','asymmetric'],mats):
        pp=list(itertools.permutations(range(n)))
        def distribution(mm):
            ss=[sum(mm[i][j] for i,j in enumerate(p)) for p in pp];z=lse(ss);return [math.exp(s-z) for s in ss]
        original=distribution(mat);normal=[r[:] for r in mat]
        for _ in range(3):
            for i in range(n):
                z=lse(normal[i]);normal[i]=[v-z for v in normal[i]]
            for j in range(n):
                z=lse([normal[i][j] for i in range(n)])
                for i in range(n):normal[i][j]-=z
        error=max(abs(x-y) for x,y in zip(original,distribution(normal)))
        assert error<=1e-12
        RESULT['algebra'].append({'n':n,'matrix':tag,'permutations':len(pp),'max_probability_difference':error})
RESULT['counts']={'comparison_methods':6,'saved_decoder_reconstruction_function':1,'algebra_property_function':1,'algebra_input_cases':12,'complete_probe_executions':1,'unique_selected_records':len(TARGET),'saved_selected_occurrences':sum(len(r['rows']) for r in RESULT['runs']),'source_packages':2,'runs':6,'phases_per_run':3,'elapsed_seconds':time.monotonic()-START}
(ROOT/'RESULTS.json').write_text(json.dumps(RESULT,indent=2)+'\n',encoding='utf-8')
(ROOT/'CONSUMED_FILES.json').write_text(json.dumps(FINGERPRINTS,indent=2)+'\n',encoding='utf-8')
summary={'counts':RESULT['counts'],'comparisons':{scope:{kind:{k:v for k,v in data.items() if k!='rows'} for kind,data in d.items()} for scope,d in RESULT['comparisons'].items()},'runs':[],'algebra_max_error':max(x['max_probability_difference'] for x in RESULT['algebra'])}
for r in RESULT['runs']:
    rr={k:v for k,v in r.items() if k!='rows'};rr['kinds']={}
    for kind in ['analogy','correspondence']:
        rows=[x for x in r['rows'] if x['kind']==kind]
        rr['kinds'][kind]={'correct':sum(x['correct'] for x in rows),'total':len(rows),'top_tie_cases':sum(x['top_ties']>1 for x in rows),'wrong_tie_with_valid':sum(not x['correct'] and x['top_tie_valid']>0 for x in rows),'best_valid_ranks':dict(collections.Counter(x['best_valid_rank'] for x in rows))}
        if kind=='correspondence':rr['kinds'][kind].update({key:sum(x[key] for x in rows) for key in ['mode_first_correct','mode_first_changes','mapping_is_bijective','matrix_identical_rows','independent_row_argmax_duplicates']},statuses=dict(collections.Counter(x['status'] for x in rows)))
    summary['runs'].append(rr)
(ROOT/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
