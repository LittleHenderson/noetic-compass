"""Cold pure verification of saved contrast data, independent of its builder."""
from collections import Counter
from hashlib import sha256
import importlib.abc
import json
from pathlib import Path
import struct
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EXPECTED_TASKS = 'ed6bb0978d34b549917e1ea1b846091f103577936f846bc01db152b19ddbac46'


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch','casformer','cas_cjt','tensorflow','jax','cupy','boto3','botocore'}:
            raise RuntimeError('LOCAL_NEURAL_OR_PROVIDER_IMPORT_FORBIDDEN')


sys.meta_path.insert(0,Guard())
sys.path.insert(0,str(ROOT))
from cas_meta2.curriculum import parse_problem, graph_signature, check_native_topology
from cas_meta2.ir import validate_program
from cas_meta2.codec import action_to_tokens
from cas_meta2.features_v2 import LosslessPublicTokenizer


def leaves(value, path=()):
    if isinstance(value,dict):
        return {p:v for k,x in value.items() for p,v in leaves(x,path+(k,)).items()}
    if isinstance(value,list):
        return {p:v for k,x in enumerate(value) for p,v in leaves(x,path+(k,)).items()}
    return {path:value}


def main():
    output = HERE/'verification.json'
    if output.exists():
        raise ValueError('NEW_COLD_VERIFICATION_REQUIRED')
    raw = (HERE/'tasks.json').read_bytes()
    assert sha256(raw).hexdigest() == EXPECTED_TASKS
    receipt = json.loads((HERE/'receipt.json').read_bytes())
    assert sha256((HERE/'build.py').read_bytes()).hexdigest() == receipt['script_sha256']
    source_paths = {ROOT/'cas_meta2'/n:h for n,h in receipt['source_sha256'].items()}
    assert all(sha256(p.read_bytes()).hexdigest()==h for p,h in source_paths.items())
    tasks = json.loads(raw)
    by_id = {t['task_id']:t for t in tasks}
    assert len(by_id)==len(tasks)==256 and len(receipt['pairs'])==128
    counts, signatures, payload_owner = Counter(), set(), {}
    for pair in receipt['pairs']:
        left,right = [by_id[i] for i in pair['task_ids']]
        assert [left['contrast']['side'],right['contrast']['side']]==['left','right']
        assert left['public']['observations']==right['public']['observations']
        assert left['target']['binding']==right['target']['binding']
        assert left['public']['problem']!=right['public']['problem']
        for task in (left,right):
            assert set(task['public'])=={'problem','observations'}
            assert task['contrast']['pair_id']==pair['pair_id']
            assert task['contrast']['family']==pair['family']
            assert parse_problem(task['public'])==task['target']
            program=task['target']['program']
            stats=validate_program(program)
            assert stats['max_call_depth']==pair['depth'] and stats['procedure_count']==4
            assert stats['expanded_run_count']<=15
            action_to_tokens(task['target'],max_length=256)
            signature=graph_signature(program)
            assert signature not in signatures
            signatures.add(signature)
            for observation in task['public']['observations']:
                payload=struct.pack('<8f',*observation['values'])
                assert payload not in payload_owner or payload_owner[payload]==pair['pair_id']
                payload_owner[payload]=pair['pair_id']
        a,b=leaves(left['target']['program']),leaves(right['target']['program'])
        assert set(a)==set(b)
        differences=[p for p in a if a[p]!=b[p]]
        assert differences==[tuple(pair['changed_target_path'])]
        assert differences[0][-1]==('input' if pair['family']=='step_input' else 'procedure')
        plans=[check_native_topology(t['target']['program']) for t in (left,right)]
        work=[{'runs':[(r['cjt_id'],r['input_node']) for r in p['runs']],
               'return_node':p['return_node']} for p in plans]
        assert work[0]!=work[1]
        counts[str(pair['depth'])+'/'+pair['family']]+=1
    assert counts=={'2/step_input':32,'2/call_target':32,'3/step_input':32,'3/call_target':32}
    assert sorted(signatures)==receipt['exposed_graph_signatures']
    tokenizer=LosslessPublicTokenizer.fit_train([t['public'] for t in tasks],max_length=1024)
    for task in tasks:
        tokenizer.encode_public(task['public'])
    assert all(sha256(p.read_bytes()).hexdigest()==h for p,h in source_paths.items())
    assert sha256((HERE/'tasks.json').read_bytes()).hexdigest()==EXPECTED_TASKS
    result={'schema':'cas-meta2-cold-contrast-verification/0.1','passed':True,
            'pairs_verified':128,'tasks_verified':256,'pair_counts':dict(counts),
            'tasks_sha256':EXPECTED_TASKS,'builder_receipt_sha256':sha256((HERE/'receipt.json').read_bytes()).hexdigest(),
            'verifier_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
            'neural_execution':False,'provider_calls':False,'native_outcome_verification':False,
            'boundary':'Cold data/meaning verification, not neural learning or held-out generalization. All prototype graphs remain exposed.'}
    with output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2,sort_keys=True)
        stream.write('\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
