"""Recount retained verdicts only. Not stored semantic replay or acceptance."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECORDS = ROOT / 'records'
inspection_path = RECORDS / 'aws_learning_v3_inspection_002/inspection_receipt.json'
inspection_raw = inspection_path.read_bytes()
assert sha256(inspection_raw).hexdigest() == '86fc7177a29b12836904174413f85f6f03f37ce31ac6a79e8469fa6f8b3fdfb7'
inspection = json.loads(inspection_raw)
assert inspection['status'] == 'CAS_META_2_V3_PACKET_PARTIAL_EVIDENCE'
assert inspection['archive_safety_and_all_included_bytes_checked'] is True
index_raw = Path(inspection['full_member_index']).read_bytes()
assert sha256(index_raw).hexdigest() == inspection['full_member_index_sha256']
entries = {r['path']: r for r in json.loads(index_raw)['entries']}
extracted = Path(inspection['extraction']['path'])
used = {}

def read(name):
    row = entries[name]
    raw = (extracted / name).read_bytes()
    assert len(raw) == row['bytes'] and sha256(raw).hexdigest() == row['sha256']
    used[name] = row['sha256']
    return json.loads(raw)

arms = ('cas_untrained', 'cas_trained', 'generic_untrained', 'generic_trained', 'rule')
totals = {arm: Counter() for arm in arms}
reasons = {arm: Counter() for arm in arms}
base = 'cloud_job/campaign/'
groups = read(base + 'evaluation_groups.json')
for i in range(72):
    folder = base + 'evaluation/case_' + str(i).zfill(4) + '/'
    case = read(folder + 'case_receipt.json')
    assert case['case_index'] == i and set(case['arms']) == set(arms)
    for arm in arms:
        row = read(folder + arm + '/case_receipt.json')
        assert row == case['arms'][arm]
        verdict = read(folder + arm + '/verification.json')
        assert verdict == row['verification']
        totals[arm]['total'] += 1
        for key in ('task_correct', 'procedure_correct', 'binding_correct', 'actual_output_correct', 'trace_valid'):
            assert type(verdict[key]) is bool
            totals[arm][key] += int(verdict[key])
        totals[arm]['model_rejections'] += int(row['model_rejection'])
        if row['model_rejection']:
            reasons[arm][row['action'].get('reason', 'UNSPECIFIED')] += 1
for arm in arms:
    for key, value in totals[arm].items():
        assert value == sum(group[arm][key] for group in groups['groups'].values())
receipt = {'schema': 'cas-meta2-v3-partial-verdict-recount/0.1',
    'source_sha': 'ec9d161908ab4ed8a4fb300ca31cb089ac0c3b70',
    'packet_sha256': inspection['packet_sha256'],
    'inspection_sha256': sha256(inspection_raw).hexdigest(),
    'cases': 72, 'arm_verdicts': 360, 'counts': totals, 'rejection_reasons': reasons,
    'read_member_hashes': used, 'native_semantic_replay_performed': False,
    'neural_execution_performed': False, 'release_accepted': False,
    'boundary': 'Checked retained JSON verdict consistency only. Original packet omitted 423 files; full stored semantic and complete learning acceptance gates remain failed/open.'}
target = Path(__file__).with_name('receipt.json')
with target.open('x', encoding='utf-8') as f:
    json.dump(receipt, f, indent=2, sort_keys=True)
    f.write('\n')
print(json.dumps({'counts': totals, 'rejection_reasons': reasons, 'release_accepted': False}, indent=2))
