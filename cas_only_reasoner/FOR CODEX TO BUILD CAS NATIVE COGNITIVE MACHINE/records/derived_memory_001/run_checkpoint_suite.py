"""Retain a full symbolic CNCM regression run and exact before/after inputs."""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'records/derived_memory_001/final_suite_001'

def put(name,value):
    with (OUTPUT/name).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,sort_keys=True,separators=(',',':'));stream.write('\n')

def inputs():
    paths=set()
    for folder,pattern in (('cncm','*.py'),('tests','*.py'),('tools','*.py'),('schemas','*.json'),('spec','*.md'),('authority','*.json')):
        paths.update((ROOT/folder).rglob(pattern))
    paths.add(ROOT/'AUTHORITY_MANIFEST.yaml');paths.add(ROOT/'cas_reasoner.txt');paths.add(Path(__file__))
    return [{'path':path.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
            for path in sorted(paths) for raw in [path.read_bytes()]]

def main():
    OUTPUT.mkdir(exist_ok=False)
    before=inputs();put('inputs_before.json',before)
    command=[sys.executable,'-B','-m','pytest','-q','tests','--junitxml='+str(OUTPUT/'tests.xml')]
    put('launch.json',{'argv':command,'python':sys.version,'cwd':str(ROOT),'scope':'Root symbolic CNCM tests only; research training suites excluded'})
    print('Starting full symbolic CNCM regression',flush=True)
    with (OUTPUT/'stdout.txt').open('xb') as out,(OUTPUT/'stderr.txt').open('xb') as err:
        result=subprocess.run(command,cwd=ROOT,stdout=out,stderr=err,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    after=inputs();put('inputs_after.json',after)
    suites=ET.parse(OUTPUT/'tests.xml').getroot().findall('testsuite')
    counts={name:sum(int(row.attrib.get(name,0)) for row in suites) for name in ('tests','failures','errors','skipped')}
    status='PASS' if result.returncode==0 and before==after and not any(counts[k] for k in ('failures','errors','skipped')) else 'FAIL'
    put('receipt.json',{'status':status,'exit_code':result.returncode,'counts':counts,'inputs_unchanged':before==after,
        'artifacts':[{'path':path.name,'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
                     for path in sorted(OUTPUT.iterdir()) if path.is_file() for raw in [path.read_bytes()]]})
    print(json.dumps({'status':status,'counts':counts,'inputs_unchanged':before==after}),flush=True)
    raise SystemExit(0 if status=='PASS' else 1)

if __name__=='__main__':main()
