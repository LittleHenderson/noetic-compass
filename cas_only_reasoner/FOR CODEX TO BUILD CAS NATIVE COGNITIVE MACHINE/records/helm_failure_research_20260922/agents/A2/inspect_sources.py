import hashlib, json, pathlib, zipfile, sys
base=pathlib.Path('cas_only_reasoner/FOR CODEX TO BUILD CAS NATIVE COGNITIVE MACHINE/records/helm_failure_research_20260922')
out=base/'agents/A2'
m=json.loads((base/'SOURCE_AND_EVIDENCE_MANIFEST.json').read_text(encoding='utf-8'))
rows=[]
for i,p in enumerate(m['source_packages'],1):
    b=pathlib.Path(p['package']['path']).read_bytes()
    assert hashlib.sha256(b).hexdigest()==p['package']['sha256_raw']
    with zipfile.ZipFile(p['package']['path']) as z:
        for member in p['members']:
            n=member['member']
            if n.endswith(('pointer_learner.py','pointer_inputs.py','pointer_contract.py')) or n=='cncm/typed_pointer_worker.py':
                data=z.read(n); assert hashlib.sha256(data).hexdigest()==member['sha256']
                target=out/'source_copies'/f'helm{i}'/pathlib.Path(n).name
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
                rows.append({'version':p['version'],'package':p['package'],'member':n,'sha256':member['sha256'],'local_copy':str(target)})
(out/'source_copy_manifest.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'python':sys.version,'verified_sources':len(rows),'source_hashes':[(r['version'],r['member'],r['sha256']) for r in rows]},indent=2))
