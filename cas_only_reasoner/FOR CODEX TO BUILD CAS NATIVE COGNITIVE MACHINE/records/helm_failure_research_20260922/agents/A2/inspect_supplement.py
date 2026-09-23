import hashlib,json,pathlib,zipfile,ast
base=pathlib.Path('cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_failure_research_20260922');out=base/'agents/A2';m=json.loads((base/'SOURCE_AND_EVIDENCE_MANIFEST.json').read_text()); rows=[]
for i,p in enumerate(m['source_packages'],1):
 with zipfile.ZipFile(p['package']['path']) as z:
  for r in p['members']:
   n=r['member']
   if n.startswith('research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/') and pathlib.PurePosixPath(n).name in ['slots.py','checker.py','course.py','source.py','focal.py']:
    b=z.read(n);assert hashlib.sha256(b).hexdigest()==r['sha256'];dst=out/'source_copies'/f'helm{i}'/pathlib.Path(n).name;dst.write_bytes(b);rows.append({'version':p['version'],'member':n,'sha256':r['sha256']})
(out/'supplemental_source_manifest.json').write_text(json.dumps(rows,indent=2)+'\n');print('SOURCES',json.dumps(rows))
a=m['additional_required_sources'][0];d=json.loads(pathlib.Path(a['path']).read_text());print('WORLD_COUNT',len(d['bank']['worlds']));print('COUNTS',json.dumps(d['counts']));print('PLAN_KEYS',list(d['plan']))
for s in [m['subjects'][0],m['subjects'][3]]:
 print('SUBJECT',s['version'])
 for suffix in ['protocol_material.json','held_final_predictions.json','final_predictions.json','initial_predictions.json','loaded_sources.json']:
  hits=[x for x in s['artifacts'] if pathlib.Path(x['path']).name==suffix]
  for x in hits[:1]:
   raw=pathlib.Path(x['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==x['sha256_raw'];v=json.loads(raw);print('ARTIFACT',suffix,'keys',list(v)[:30]);print('TYPE_SAMPLE',str(v)[:250])
for nm in ['slots.py','checker.py','course.py']:
 t=ast.parse((out/'source_copies/helm2'/nm).read_text());print('FUNCS',nm,[(x.name,x.lineno,x.end_lineno) for x in ast.walk(t) if isinstance(x,ast.FunctionDef)])
