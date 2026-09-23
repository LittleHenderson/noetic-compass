import json, pathlib, hashlib, ast
b=pathlib.Path('cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_failure_research_20260922'); m=json.loads((b/'SOURCE_AND_EVIDENCE_MANIFEST.json').read_text()); a=m['additional_required_sources'][0]; data=pathlib.Path(a['path']).read_bytes(); assert hashlib.sha256(data).hexdigest()==a['sha256_raw']; d=json.loads(data)
print('COURSE_KEYS',list(d));print('BANK_KEYS',list(d['bank']));print('WORLD',json.dumps(d['bank']['worlds'][0],indent=2));print('REGISTRY_LENGTH',len(d['registry']))
for k in ['analogy','reach','correspondence','definition','role_set']:
    rows=[x for x in d['registry'] if x['query']['kind']==k]
    print('EXAMPLE',k,len(rows),json.dumps(rows[0],indent=2))
for v in ['helm1','helm2']:
    path=b/'agents/A2/source_copies'/v/'pointer_learner.py'; tree=ast.parse(path.read_text())
    print('FUNCTION_LINES',v,[(x.name,x.lineno,x.end_lineno) for x in ast.walk(tree) if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) and x.name in ['_rounds','_encode_query','_world_scores','_declaration_embeddings','segments','_graph']])
