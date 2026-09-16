"""Pin the independent pure-boundary test run; never invoke a neural worker."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent/'adversarial_final_001'


def put(name, value):
    with (OUTPUT/name).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,sort_keys=True,separators=(',',':'));stream.write('\n')


def inventory():
    paths = set((ROOT/'cncm').rglob('*.py'))
    paths.update((ROOT/'research/CAS_META_2_COMPOSITION/cas_meta2').rglob('*.py'))
    paths.add(ROOT/'tests/test_rpa_learning_adversarial.py')
    paths.add(Path(__file__).resolve())
    return [{'path':p.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
            for p in sorted(paths) for raw in [p.read_bytes()]]


def main():
    OUTPUT.mkdir(exist_ok=False)
    before=inventory();put('sources_before.json',before)
    command=[sys.executable,'-B','-m','pytest','-q','tests/test_rpa_learning_adversarial.py',
             '--junitxml='+str(OUTPUT/'tests.xml'),'--basetemp='+str(OUTPUT/'temporary')]
    put('launch.json',{'argv':command,'cwd':str(ROOT),'python':sys.version,
                      'boundary':'Pure tokenizer/framing/control tests with explicit metadata test doubles; no tensor or neural execution authorized.'})
    print('Starting source-pinned independent learner-boundary tests',flush=True)
    with (OUTPUT/'stdout.txt').open('xb') as out,(OUTPUT/'stderr.txt').open('xb') as err:
        result=subprocess.run(command,cwd=ROOT,stdout=out,stderr=err)
    after=inventory();put('sources_after.json',after)
    suites=ET.parse(OUTPUT/'tests.xml').getroot().findall('testsuite')
    counts={k:sum(int(row.get(k,0)) for row in suites) for k in ('tests','failures','errors','skipped')}
    passed=result.returncode==0 and before==after and counts['tests']>0 and not any(counts[k] for k in ('failures','errors','skipped'))
    artifacts=[{'path':p.name,'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
               for p in sorted(OUTPUT.iterdir()) if p.is_file() for raw in [p.read_bytes()]]
    receipt={'status':'PASS' if passed else 'FAIL','exit_code':result.returncode,
             'counts':counts,'sources_unchanged':before==after,'source_file_count':len(before),
             'source_inventory_boundary':'All cncm Python sources, all cas_meta2 Python sources, this runner and the independent test module; not an observed import inventory.',
             'artifacts':artifacts,'actual_neural_execution_claimed':False,
             'boundary':'Independent local pure-contract regressions only. Source-only CUDA code review does not establish worker execution or learning gain.'}
    put('receipt.json',receipt)
    print(json.dumps({**receipt,'receipt_sha256':sha256((OUTPUT/'receipt.json').read_bytes()).hexdigest()}),flush=True)
    raise SystemExit(0 if passed else 1)


if __name__=='__main__':main()
