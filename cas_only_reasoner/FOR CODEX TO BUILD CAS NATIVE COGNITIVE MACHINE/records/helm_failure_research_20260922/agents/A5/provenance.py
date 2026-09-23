import hashlib,json,pathlib,zipfile,datetime
ROOT=pathlib.Path(__file__).resolve().parent;BASE=ROOT.parent.parent
m=json.loads((BASE/'SOURCE_AND_EVIDENCE_MANIFEST.json').read_text('utf-8-sig'))
result={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runs':[],'source_excerpts':[]}
prefix='research/CAS_META_2_COMPOSITION/cas_meta2/typed_teaching/'
files=['answers.py','checker.py','slots.py','learner.py','pointer_inputs.py','pointer_learner.py','course.py']
for s in m['subjects']:
    arts={pathlib.Path(a['path']).name:a for a in s['artifacts']};loaded={};checked=[]
    for name in ['source.zip','config.json','loaded_sources.json']:
        row=arts[name];raw=pathlib.Path(row['path']).read_bytes();sha=hashlib.sha256(raw).hexdigest();assert sha==row['sha256_raw'];checked.append({'path':row['path'],'sha256':sha,'bytes':len(raw)})
        if name.endswith('.json'):loaded[name]=json.loads(raw)
    assert loaded['config.json']['source_sha']==s['source_commit']
    z=zipfile.ZipFile(arts['source.zip']['path']);proof=[]
    for name in files:
        path=prefix+name;sha=hashlib.sha256(z.read(path)).hexdigest()
        hits=[r for phase in ['before','after'] for r in loaded['loaded_sources.json'][phase]['modules'] if r['path']==path]
        assert hits and all(r['sha256']==sha for r in hits)
        proof.append({'member':path,'sha256':sha,'loaded_records_matching':len(hits)})
    result['runs'].append({'version':s['version'],'seed':s['seed'],'source_commit':s['source_commit'],'artifacts':checked,'module_proof':proof})
for pkg in m['source_packages']:
    z=zipfile.ZipFile(pkg['package']['path']);h2='2.0' in pkg['version']
    blocks={'answers.py':[(201,221),(285,304)],'checker.py':[(96,112),(200,237),(243,268)],'slots.py':[(74,118),(259,296)],'pointer_inputs.py':[(169,195),(212,244)],'pointer_learner.py':[(1373,1422),(1484,1516),(1547,1561)] if h2 else [(1252,1265),(1300,1331),(1361,1369)],'learner.py':[(196,227)]}
    for f,ranges in blocks.items():
        raw=z.read(prefix+f);ls=raw.decode('utf-8-sig').splitlines()
        result['source_excerpts'].append({'version':pkg['version'],'package_sha256':pkg['package']['sha256_raw'],'member':prefix+f,'sha256':hashlib.sha256(raw).hexdigest(),'lines':[{'start':a,'end':b,'text':'\n'.join(f'{i+1}: {ls[i]}' for i in range(a-1,b))} for a,b in ranges]})
    name='cncm/typed_pointer_worker.py';raw=z.read(name);ls=raw.decode().splitlines();hits=[i for i,l in enumerate(ls) if '_evaluate(restored, ctx["held_packets"], "ablation_baseline"' in l];assert len(hits)==1;i=hits[0]
    result['source_excerpts'].append({'version':pkg['version'],'member':name,'sha256':hashlib.sha256(raw).hexdigest(),'lines':[{'start':i-1,'end':i+3,'text':'\n'.join(f'{k+1}: {ls[k]}' for k in range(i-2,i+3))}]})
(ROOT/'SOURCE_PROVENANCE.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'six_runs_config_source_and_loaded_module_hashes':'MATCH','modules_per_run':len(files),'source_excerpts':len(result['source_excerpts'])}))
