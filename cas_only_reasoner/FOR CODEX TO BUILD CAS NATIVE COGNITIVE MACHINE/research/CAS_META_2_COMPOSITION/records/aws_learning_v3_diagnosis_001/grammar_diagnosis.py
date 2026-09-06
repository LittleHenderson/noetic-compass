"""Pure replay of retained rejected token prefixes; no model loading."""
from collections import Counter
from hashlib import sha256
import importlib.abc
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
class NoNeuralImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch','tensorflow','jax','casformer','cas_cjt','cupy','boto3'}:
            raise RuntimeError('PURE_DIAGNOSIS_IMPORT_BLOCKED:' + fullname)
sys.meta_path.insert(0, NoNeuralImports())
sys.path.insert(0, str(ROOT))
manifest = json.loads((ROOT / 'records/aws_learning_v3_source_001/source.receipt.json').read_bytes())['launch_manifest']
for name in ('__init__.py','grammar_v3.py','codec.py','ir.py'):
    key = 'research/CAS_META_2_COMPOSITION/cas_meta2/' + name
    assert sha256((ROOT / 'cas_meta2' / name).read_bytes()).hexdigest() == manifest['files_sha256'][key]
from cas_meta2.grammar_v3 import GrammarState
from cas_meta2.codec import action_to_tokens, ACTION_VOCABULARY

raw = (ROOT / 'records/aws_learning_v3_inspection_002/inspection_receipt.json').read_bytes()
assert sha256(raw).hexdigest() == '86fc7177a29b12836904174413f85f6f03f37ce31ac6a79e8469fa6f8b3fdfb7'
inspection = json.loads(raw)
index_raw = Path(inspection['full_member_index']).read_bytes()
assert sha256(index_raw).hexdigest() == inspection['full_member_index_sha256']
index = {r['path']: r for r in json.loads(index_raw)['entries']}
extracted = Path(inspection['extraction']['path'])
used = {}
def read(name, lines=False):
    raw = (extracted / name).read_bytes()
    assert len(raw) == index[name]['bytes'] and sha256(raw).hexdigest() == index[name]['sha256']
    used[name] = index[name]['sha256']
    return [json.loads(line) for line in raw.splitlines()] if lines else json.loads(raw)

base = 'cloud_job/campaign/'
predictions = read(base + 'predictions.jsonl', True)
summary, details = {}, []
for arm in ('cas_untrained','cas_trained','generic_untrained','generic_trained'):
    counts = Counter()
    for row in predictions:
        action = row['actions'][arm]
        if action.get('status') != 'REJECTED':
            continue
        state = GrammarState.from_ids(action['token_ids'], max_length=256)
        failure = state.completion_error()
        replay = GrammarState(max_length=256)
        extra = None
        for position, token_id in enumerate(action['token_ids']):
            if (ACTION_VOCABULARY[token_id] == 'PROC' and replay.role == 'procedure_or_eos'
                    and replay._machine.procedures and not replay._machine.pending_names()):
                extra = {'token_index': position, 'valid_program_before_extra': '[EOS]' in replay.allowed_tokens()}
                break
            replay = replay.advance_id(token_id)
        key = state.role + ':' + str(failure)
        counts[key] += 1
        details.append({'case_index':row['case_index'], 'arm':arm, 'token_count':len(state.prefix),
            'terminal_role':state.role, 'completion_error':failure, 'dead_end':state.dead_end,
            'extra_declaration_after_closed_graph':extra,
            'declared_procedures':len(state._machine.procedures),
            'pending_names':sorted(state._machine.pending_names()),
            'allowed_tokens':list(state.allowed_tokens())})
    summary[arm] = counts
shapes = {}
for split in ('validation', 'test_private'):
    tasks = read(base + 'dataset/' + split + '.json')
    assert type(tasks) is list
    counts = Counter(len(task['target']['program']['procedures']) for task in tasks)
    lengths = [len(action_to_tokens(task['target'])) for task in tasks]
    shapes[split] = {'cases':len(tasks), 'procedure_counts':counts,
                    'action_tokens_min':min(lengths), 'action_tokens_max':max(lengths),
                    'action_tokens_mean':sum(lengths)/len(lengths)}
receipt = {'schema':'cas-meta2-v3-pure-prefix-diagnosis/0.1', 'summary':summary,
    'task_shapes':shapes, 'details':details, 'read_member_hashes':used,
    'packet_sha256':inspection['packet_sha256'], 'model_loaded':False,
    'neural_execution_performed':False, 'release_accepted':False,
    'boundary':'Exact pure grammar replay of saved prefixes and retained dataset shape counts; no repaired predictions or new inference.'}
with Path(__file__).with_name('grammar_receipt_002.json').open('x',encoding='utf-8') as stream:
    json.dump(receipt,stream,indent=2,sort_keys=True)
    stream.write('\n')
print(json.dumps({'summary':summary,'task_shapes':shapes},indent=2))
