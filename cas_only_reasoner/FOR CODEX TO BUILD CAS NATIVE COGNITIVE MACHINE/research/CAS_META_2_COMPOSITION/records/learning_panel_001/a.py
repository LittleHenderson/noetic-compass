"""Pure retained-history/corpus audit. No model, tensor, provider, or final scoring."""
from __future__ import annotations
import sys, importlib.abc, json, re, ast, argparse
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
DENIED = {'torch','numpy','boto3','botocore','cas_cjt','casformer','requests','socket','transformers','safetensors','pickle'}
class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in DENIED:
            raise RuntimeError('PURE_AUDIT_IMPORT_FORBIDDEN:'+fullname)
sys.meta_path.insert(0,Deny())
from tools.check_structural_supply_20260916 import shape_key, topology_key, graph_key
from cas_meta2.complementary_teaching.course import digest
PREP = ROOT/'records/complementary_teaching_001/preparation_20260916'
def read(path): return json.loads(Path(path).read_bytes())
def pin(path):
    path=Path(path); raw=path.read_bytes()
    return {'path':path.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
def write(name,data):
    path=OUT/name
    if path.exists(): raise ValueError('PRESERVE_EXISTING:'+name)
    path.write_text(json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'output':name,'sha256':pin(path)['sha256']}),flush=True)
def modules():
    paths={Path(m.__file__).resolve() for m in tuple(sys.modules.values()) if getattr(m,'__file__',None) and str(ROOT) in str(m.__file__) and str(OUT) not in str(m.__file__)}
    return [pin(p) for p in sorted(paths)]
def supply():
    from tools.compile_complementary_data import compile_exclusions
    from cas_meta2.graph_teaching import final_panel
    from cas_meta2.complementary_teaching.data import validate_manifest
    expected=read(PREP/'historical_exclusions.json')
    rebuilt=compile_exclusions()
    assert rebuilt==expected, 'EXCLUSIONS_REBUILD_DIFF'
    manifest=validate_manifest(read(PREP/'data_manifest.json'))
    assert digest(expected)==manifest['exclusions_sha256']
    patterns={shape_key(s):s for s in final_panel.enumerate_patterns().values()}
    old=read(ROOT/'records/structural_supply_20260916/post_fix/report.json')
    potential=set(old['other_existing_source_supply']['potential_topology_digests'])
    available=set(patterns)-set(expected['excluded_topologies'])
    assert available==potential and len(available)==47
    allocation={r['topology']:r for r in manifest['families']}
    rows=[]
    for key in sorted(patterns):
        shape=patterns[key]
        rows.append({'topology':key,'stats':final_panel.pattern_stats(shape),
          'historically_excluded':key in expected['excluded_topologies'],
          'candidate_pool':key in available,
          'current_allocation':allocation.get(key,{}).get('split','unallocated' if key in available else 'excluded'),
          'supports_all_three_reach_classes':final_panel._supports_all_reach(shape),
          'authoring_examination':'existing deterministic enumerator/reference checker; not learner exposure'})
    write('supply.json',{'schema':'cas.learning-panel-supply-audit/0.1','status':'EXISTING_ALLOCATION_REPRODUCED_NOT_NEW_FREEZE',
      'exclusions_reproduced_exactly':True,'archives':expected['archives'],'rows':rows,
      'counts':dict(Counter(r['current_allocation'] for r in rows)),
      'input_pins':[pin(PREP/n) for n in ['historical_exclusions.json','data_manifest.json','TASK_BINDINGS.json','DESIGN.md','UNSIGNED_EXECUTION_REQUEST.json']],
      'source_pins':modules(),'actual_neural_presentations':0,'actual_optimizer_updates':0,'actual_provider_calls':0})
def measure(name,tokenizer,panels,training_publics,scope):
    from cas_meta2.graph_teaching.ordered_encoder import compile_frames
    result={'name':name,'scope':scope,'tokenizer_sha256':tokenizer.digest,
      'fitted_public_sha256':tokenizer.fitted_public_sha256,'fitted_examples':tokenizer.fitted_examples,'max_length':tokenizer.max_length,'panels':{}}
    for key,tasks in {'training_fit':[{'public':p} for p in training_publics],**panels}.items():
        rows=[]
        for i,task in enumerate(tasks):
            public=task['public']; row={'index':i,'public_sha256':digest(public)}
            try:
                row['complete_tokens']=len(tokenizer.encode_public(public)['ids'])
                frames=compile_frames(public,tokenizer)
                row['framed_tokens']=sum(len(f.token_ids) for f in frames)
                row['structural_frames']=sum(f.kind in ('node','rel') for f in frames)
            except Exception as e: row['failure']=str(e)
            rows.append(row)
        result['panels'][key]={'count':len(rows),'failures':sum('failure' in r for r in rows),
          'maximum_complete_tokens':max((r.get('complete_tokens',0) for r in rows),default=0),
          'maximum_framed_tokens':max((r.get('framed_tokens',0) for r in rows),default=0),'rows':rows}
    return result
def envelope():
    from cas_meta2.features_v2 import LosslessPublicTokenizer
    from cas_meta2.graph_teaching import face_worker,face_evaluation,face_schedule,ordered_encoder_probe
    from cas_meta2.complementary_teaching import course
    manifest=read(PREP/'data_manifest.json'); binding=read(PREP/'TASK_BINDINGS.json')
    conditions=[(x['condition'],x['organization'],x['cue']) for x in face_schedule.comparison_conditions()]
    historical=face_worker.public_corpus(None,face_evaluation.panel(),conditions)
    oldtok=LosslessPublicTokenizer.fit_train(historical['publics'],max_length=1024)
    assert oldtok.digest==binding['tokenizer_sha256']
    assert digest(historical)==binding['unchanged_original_encoder_fitting_corpus_sha256']
    train=ordered_encoder_probe.training_publics()
    traintok=LosslessPublicTokenizer.fit_train(train,max_length=1024)
    schedule=course.compile_complementary_course(101,'ALT_COMPONENT_WHOLE')
    # Dedup by full public identity, with lexical order of that digest fixed here.
    unique={digest(t['public']):t['public'] for b in schedule['batches'] for t in b['tasks']}
    course_train=[unique[k] for k in sorted(unique)]
    coursetok=LosslessPublicTokenizer.fit_train(course_train,max_length=1024)
    rows=[measure('historical_face_panel_union',oldtok,manifest['panels'],historical['publics'],
                  'Exact old TASK_BINDINGS tokenizer; includes historically examined old evaluation public inputs. NOT training-only.'),
          measure('ordered_diagnostic_training_only',traintok,manifest['panels'],train,
                  'Actual ordered diagnostic fitting rule: old lesson train/practice, seed20260909; no new candidate final input fitted.'),
          measure('candidate_complementary_course_training_only',coursetok,manifest['panels'],course_train,
                  'Audit-only possible new tokenizer: sorted unique full public packets from seed101 ALT_COMPONENT_WHOLE course. No dev/final fitted; not a frozen run.')]
    write('envelope.json',{'schema':'cas.learning-panel-envelope-audit/0.1','rows':rows,'source_pins':modules(),
      'claim':'Pure complete-input framing only; no numerical encoder, initializer/checkpoint compatibility, learner, update or score measured.'})
def history():
    candidate={r['topology'] for r in read(OUT/'supply.json')['rows'] if r['candidate_pool']}
    rows=[]; matches=[]; failures=[]; cache={}; schema_counts=Counter(); runrows=[]
    def topology(nodes,edges):
        if not (8<=len(nodes)<=10):return None
        key=digest([nodes,edges])
        if key not in cache:cache[key]=topology_key(nodes,edges)
        return cache[key]
    def walk(v,pointer,found):
        if isinstance(v,dict):
            if isinstance(v.get('nodes'),list) and isinstance(v.get('relations'),list):
                ns=v['nodes']; es=v['relations']
                if 8<=len(ns)<=10 and all(isinstance(n,dict) and 'identifier' in n for n in ns) and all(isinstance(e,dict) and e.get('kind')=='contains' for e in es):
                    try:k=topology([n['identifier'] for n in ns],[(e['source'],e['target']) for e in es])
                    except Exception:k=None
                    if k in candidate: found.append({'pointer':pointer,'topology':k,'form':'graph_record'})
            if isinstance(v.get('problem'),str):
                lines=v['problem'].splitlines(); ns=[]; es=[]
                for line in lines:
                    n=re.fullmatch(r'node (\S+) kind=\S+.*',line.strip())
                    e=re.fullmatch(r'rel (\S+) --contains--> (\S+)',line.strip())
                    if n:ns.append(n[1])
                    if e:es.append((e[1],e[2]))
                if 8<=len(ns)<=10:
                    try:k=topology(ns,es)
                    except Exception:k=None
                    if k in candidate:found.append({'pointer':pointer+'/problem','topology':k,'form':'public_graph_lines'})
            for key,item in v.items():walk(item,pointer+'/'+str(key),found)
        elif isinstance(v,list):
            for i,item in enumerate(v):walk(item,pointer+'/'+str(i),found)
    paths=sorted(p for p in (ROOT/'records').rglob('*') if p.is_file() and p.suffix in ('.json','.jsonl') and OUT not in p.parents)
    for i,p in enumerate(paths):
        raw=p.read_bytes(); meta={'path':p.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':sha256(raw).hexdigest()}; rows.append(meta)
        try:documents=[json.loads(raw)] if p.suffix=='.json' else [json.loads(line) for line in raw.splitlines() if line.strip()]
        except Exception as e: failures.append({**meta,'error_type':type(e).__name__});continue
        for j,d in enumerate(documents):
            if isinstance(d,dict):
                schema=str(d.get('schema',''));schema_counts[schema]+=1
                if any(x in schema for x in ('graph-training','cube-face','recurrent-cjt','graph6-contrast','ordered-encoder','complementary')) and any(x in schema for x in ('result','failure','launch','config','manifest','inventory')):
                    runrows.append({**meta,'schema':schema,'status':d.get('status'),'job':d.get('job'),'top_keys':sorted(d)})
            found=[];walk(d,'' if p.suffix=='.json' else '/line/'+str(j),found)
            if found:matches.append({**meta,'schema':d.get('schema') if isinstance(d,dict) else None,'matches':found})
        if i%300==0:print('history',i,len(paths),flush=True)
    archive_rows=[]
    for p in sorted((ROOT/'records').rglob('*.zip')):
        # Byte pins and source metadata only: no extracted/executed model files.
        row=pin(p); members=[]
        try:
            with ZipFile(p) as z:
                for name in z.namelist():
                    if '/graph_teaching/' in name and name.endswith('.py') and Path(name).name in {'lessons.py','fresh_panel.py','curriculum.py','final_panel.py','face_corpus.py','face_tasks.py','face_evaluation.py','verified_training.py','candidate_experiment.py','cube_profile.py'}:
                        raw=z.read(name);members.append({'name':name,'sha256':sha256(raw).hexdigest(),'ast_sha256':sha256(ast.dump(ast.parse(raw)).encode()).hexdigest()})
            row['relevant_source_members']=members
        except Exception as e:row['error_type']=type(e).__name__
        archive_rows.append(row)
    write('history.json',{'schema':'cas.learning-panel-retained-history-scan/0.1','scope':'All JSON/JSONL and ZIP files under this retained research records tree at path inventory time; checkpoints never opened. Authoring occurrences are not learner exposures.',
      'files':rows,'schema_counts':schema_counts,'parse_failures':failures,'candidate_occurrences':matches,'run_metadata':runrows,'archives':archive_rows,'source_pins':modules(),
      'limitations':['No claim about unretained external history. A source archive alone does not prove which inputs reached a learner.','Embedded graph/public text matching does not classify training vs evaluation without executed-path context.','Other domains, raw log text and non-JSON binary data are outside this semantic scan.']})
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['supply','envelope','history']);args=parser.parse_args()
    globals()[args.mode]()
