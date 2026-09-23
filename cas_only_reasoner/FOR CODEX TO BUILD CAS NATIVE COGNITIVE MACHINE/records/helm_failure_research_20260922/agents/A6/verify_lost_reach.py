import hashlib,json,time,zipfile
from collections import deque
from pathlib import Path
start=time.monotonic()
base=Path(__file__).resolve().parent
m=json.loads((base.parents[1]/'SOURCE_AND_EVIDENCE_MANIFEST.json').read_text(encoding='utf-8-sig'))
source=next(a for a in m['additional_required_sources'] if a['path'].endswith('public_course.json'))
blob=Path(source['path']).read_bytes()
assert hashlib.sha256(blob).hexdigest()==source['sha256_raw']
course=json.loads(blob)
worlds={w['world_id']:w for w in course['bank']['worlds']}
lost=json.loads((base/'lost_answers.json').read_text(encoding='utf-8'))
result=[]
for row in lost:
    q=row['packet']['query']; w=worlds[q['focus_world_id']]
    edges=[(e['source'],e['target']) for e in w['contains']]
    origin=q['arguments']['whole']; target=q['arguments']['part']
    todo=deque([[origin]]); paths=[]
    while todo:
        path=todo.popleft()
        if path[-1]==target:
            paths.append(path);continue
        for a,b in sorted(edges):
            if a==path[-1] and b not in path:todo.append(path+[b])
    # Both saved cases have one unique path: tie resolution is therefore immaterial.
    assert len(paths)==1 and len(paths[0])>=3
    path=paths[0]
    via=path[-2] if q['rule']=='bfs_immediate_predecessor_lexical_v1' else path[1]
    expected={'state':'VIA','via':via}
    before=row['before_prediction']['answer']['value'];after=row['after_prediction']['answer']['value']
    assert before==expected and after!=expected
    result.append({'seed':row['seed'],'query_id':q['query_id'],'record_id':row['packet']['record_id'],
        'instruction':row['packet']['instruction'],'rule':q['rule'],'edges':edges,'unique_directed_path':path,
        'expected':expected,'before':before,'after':after,'before_correct':True,'after_correct':False})
print(json.dumps({'lost_record_cases':len(result),'lost_question_cases':len({r['query_id'] for r in result}),'all_checks_match_saved_score':True},sort_keys=True))
# Inspect text only, no imports from the frozen package.
subject=m['subjects'][3]
ziprow=next(a for a in subject['artifacts'] if a['path'].endswith('source.zip'))
zbytes=Path(ziprow['path']).read_bytes()
assert hashlib.sha256(zbytes).hexdigest()==ziprow['sha256_raw']
excerpts=[]
with zipfile.ZipFile(ziprow['path']) as archive:
    for member in ('research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/answers.py','research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/checker.py'):
        raw=archive.read(member); lines=raw.decode('utf-8').splitlines()
        selected=set()
        for n,line in enumerate(lines):
            if any(word in line for word in ('bfs_immediate','first_direct_constituent','def reach','def _reach')):
                selected.update(range(max(0,n-4),min(len(lines),n+45)))
        excerpts.append({'archive':ziprow['path'],'archive_sha256':ziprow['sha256_raw'],'member':member,'member_sha256':hashlib.sha256(raw).hexdigest(),
            'lines':[{'number':n+1,'text':lines[n]} for n in sorted(selected)]})
# Locate exact source IDs in raw JSON. Recorded line numbers refer to unmodified source files.
locations=[]
for item in result:
    for rel in ('course_p00_predictions.json','course_p10_predictions.json','course_p00_scoring.json','course_p10_scoring.json'):
        s=next(s for s in m['subjects'] if s['seed']==item['seed'] and s['version'].startswith('Helm 2'))
        path=Path(s['receipt_root'])/'checkpoints'/rel
        data=path.read_bytes(); expected=next(a for a in s['artifacts'] if a['path']==str(path))
        assert hashlib.sha256(data).hexdigest()==expected['sha256_raw']
        lines=data.decode('utf-8').splitlines()
        locations.append({'path':str(path),'sha256':expected['sha256_raw'],'record_id':item['record_id'],'matching_record_id_lines':[n+1 for n,line in enumerate(lines) if item['record_id'] in line]})
assert time.monotonic()-start<115
(base/'reach_verification.json').write_text(json.dumps({'input_course_sha256':source['sha256_raw'],'results':result,'source_excerpts':excerpts,'raw_locations':locations,'elapsed_seconds':time.monotonic()-start,'test_functions':0,'diagnostic_executions':1},indent=2)+'\n',encoding='utf-8')
for r in result:
    print(r['seed'],r['query_id'],[n.rsplit('/',1)[-1] for n in r['unique_directed_path']])
