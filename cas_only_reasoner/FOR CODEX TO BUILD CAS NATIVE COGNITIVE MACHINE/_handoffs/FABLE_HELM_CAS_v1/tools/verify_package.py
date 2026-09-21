#!/usr/bin/env python3
"""Verify delivered bytes and planning references; does not verify future model code."""
from pathlib import Path
import hashlib, json, sys

def load(p):
    return json.loads(p.read_text(encoding='utf-8'))

def verify(root):
    root=root.resolve(); errors=[]
    manifest=load(root/'PACKAGE_MANIFEST.json')
    seen=set()
    for item in manifest['files']:
        rel=item['path']; p=(root/rel).resolve()
        if p==root or root not in p.parents or rel in seen:
            errors.append('Unsafe or duplicate path: '+rel); continue
        seen.add(rel)
        if not p.is_file(): errors.append('Missing: '+rel); continue
        b=p.read_bytes()
        if len(b)!=item['bytes'] or hashlib.sha256(b).hexdigest()!=item['sha256']:
            errors.append('Byte mismatch: '+rel)
    actual={str(p.relative_to(root)).replace('\\','/') for p in root.rglob('*')
            if p.is_file() and p.name!='PACKAGE_MANIFEST.json' and '__pycache__' not in p.parts}
    if actual!=seen: errors.append('Manifest coverage mismatch: '+str(sorted(actual^seen)))
    tasks=load(root/'TASKS.json')['tasks']; vectors=load(root/'ACCEPTANCE_TESTS.json')['vectors']
    ids=[x['id'] for x in tasks]; tids={x['id'] for x in vectors}
    if len(ids)!=len(set(ids)): errors.append('Duplicate task IDs')
    if len(vectors)!=len(tids): errors.append('Duplicate test IDs')
    graph={x['id']:x['depends_on'] for x in tasks}; visited=set();active=set()
    def visit(x):
        if x in active: raise ValueError('Cyclic task dependency: '+x)
        if x in visited: return
        if x not in graph: raise ValueError('Unknown dependency: '+x)
        active.add(x)
        for d in graph[x]:visit(d)
        active.remove(x);visited.add(x)
    try:
        for x in graph: visit(x)
    except ValueError as e:errors.append(str(e))
    owners={p.name.split('_')[0] for p in (root/'agent_prompts').glob('*.md')}
    for x in tasks:
        if x['owner'] not in owners or x['reviewer'] not in owners:errors.append('Missing owner/reviewer: '+x['id'])
        if x['owner']==x['reviewer']:errors.append('Self review: '+x['id'])
        if set(x['acceptance_vectors'])-tids:errors.append('Unknown vector: '+x['id'])
        if x['status']!='PLANNED':errors.append('Unexpected delivery task status: '+x['id'])
    for x in vectors:
        if x['status']!='PLANNED':errors.append('Unexpected delivery test status: '+x['id'])
    for s in load(root/'sources/SOURCE_MANIFEST.json')['sources']:
        p=root/s['package_path'];b=p.read_bytes()
        if len(b)!=s['bytes'] or hashlib.sha256(b).hexdigest()!=s['sha256']:
            errors.append('Source mismatch: '+s['id'])
    return {'status':'PASS' if not errors else 'FAIL','scope':'Delivery integrity, task DAG, source copies and internal references only. Not implementation acceptance or author authentication.',
            'manifest_files':len(seen),'tasks':len(tasks),'planned_vectors':len(vectors),'agent_roles':len(owners),'errors':errors}

def main():
    try:
        result=verify(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1])
    except (OSError,ValueError,KeyError,TypeError) as e:
        result={'status':'FAIL','errors':[str(e)]}
    print(json.dumps(result,indent=2))
    return 0 if result['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
