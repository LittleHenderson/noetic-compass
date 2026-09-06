"""Pure inventory and aggregate tests; simulated rows are not native execution."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import pytest
from tools import audit_ablation_stored_v4 as audit
from tools import inspect_cloud_packet as helper
from cas_meta2.campaign_v3 import aggregate_cases

pytestmark = pytest.mark.not_gpu


def rows_and_metrics():
    rows, native = [], []
    for index in range(2):
        valid = index == 0
        derived = {**{field: valid for field in audit.FIELDS}, 'native_runs': int(valid),
                   'reserved_policy_units': 10 * int(valid), 'model_rejection': not valid}
        rows.append({'case_index': index, 'arms': {arm: deepcopy(derived) for arm in audit.ARMS}})
        native.append({'case_index': index, 'arms': {arm: {
            'verification': {**derived, 'repair_required': False, 'repair_success': None},
            'model_rejection': not valid, 'execution_status': 'EXECUTED' if valid else 'REJECTED',
            'wall_seconds': 0.0} for arm in audit.ARMS}})
    return rows, aggregate_cases(native, 2)


def test_recount_uses_all_rows_including_rejections():
    rows, metrics = rows_and_metrics()
    result = audit.recount(rows, metrics)
    assert all(row['total'] == 2 and row['task_correct'] == 1 and row['model_rejection'] == 1
               for row in result.values())
    assert 'torch' not in sys.modules


@pytest.mark.parametrize('field,value', [
    ('task_correct', 2), ('binding_correct', 2), ('actual_output_correct', 2),
    ('trace_valid', True), ('total', 1), ('native_runs', 2),
    ('reserved_policy_units', 0), ('model_rejections', 0),
    ('native_executed', 2), ('task_accuracy', 1.0),
    ('all_cases_in_denominator', False), ('repair_required_total', 1), ('repair_success', 1)])
def test_changed_metrics_refused(field, value):
    rows, metrics = rows_and_metrics()
    metrics['cas_trained'][field] = value
    with pytest.raises(ValueError, match='AGGREGATE'):
        audit.recount(rows, metrics)


def make_inventory(tmp_path):
    raw = b'{"stored":true}\n'
    root = tmp_path / 'data_extracted'
    root.mkdir()
    (root / 'document.json').write_bytes(raw)
    receipt = {'schema': 'cas-meta2-retrospective-inspection/0.2',
        'status': 'RETROSPECTIVE_RECEIPT_CHECKS_PASSED', 'issues': [],
        'original_full_index_verified': True, 'archive_safety_and_all_included_bytes_checked': True,
        'packet_sha256': 'a' * 64, 'member_files': 1,
        'extraction': {'path': str(root), 'files_verified': 1, 'all_member_bytes_verified_after_write': True}}
    index = {'schema': 'cas-meta2-full-packet-index/1', 'packet_sha256': 'a' * 64,
             'entries': [{'path': 'document.json', 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}]}
    return root, receipt, index


def test_checked_inventory_rechecks_files(tmp_path):
    root, receipt, index = make_inventory(tmp_path)
    packet = audit.Files(receipt, index, helper)
    assert packet.json('document.json') == {'stored': True}
    (root / 'document.json').write_bytes(b'{"stored":false}\n')
    with pytest.raises(ValueError, match='MEMBER_CHANGED'):
        packet.raw('document.json')
    with pytest.raises(ValueError, match='EXTRACTED_FILE_CHANGED'):
        packet.verify_all()


def test_added_file_refused(tmp_path):
    root, receipt, index = make_inventory(tmp_path)
    packet = audit.Files(receipt, index, helper)
    (root / 'extra.json').write_bytes(b'{}')
    with pytest.raises(ValueError, match='UNINDEXED_EXTRACTED_FILE'):
        packet.verify_all()


@pytest.mark.parametrize('mutation', ['failed', 'wrong_packet', 'duplicate', 'escape', 'missing'])
def test_unqualified_inventory_refused(tmp_path, mutation):
    root, receipt, index = make_inventory(tmp_path)
    if mutation == 'failed': receipt['status'] = 'RETROSPECTIVE_FAILED_OR_PARTIAL_RUN'
    elif mutation == 'wrong_packet': index['packet_sha256'] = 'b' * 64
    elif mutation == 'duplicate': index['entries'].append(deepcopy(index['entries'][0]))
    elif mutation == 'escape': index['entries'][0]['path'] = '../document.json'
    elif mutation == 'missing': (root / 'document.json').unlink()
    with pytest.raises(ValueError):
        audit.Files(receipt, index, helper)


def test_audit_requires_external_identity_before_source_or_model_access():
    with pytest.raises(ValueError, match='EXACT_SOURCE_SHA_REQUIRED'):
        audit.audit('missing', inspection_sha256='a' * 64, source_archive='missing',
            source_sha256='b' * 64, source_sha='main', job='invalid', packet_sha256='c' * 64, output='missing')
    assert 'torch' not in sys.modules


def test_source_changes_refused_before_engine_import(tmp_path, monkeypatch):
    root = tmp_path / 'research' / 'candidate'
    root.mkdir(parents=True)
    (root / 'file.py').write_bytes(b'changed')
    monkeypatch.setattr(audit, 'ROOT', root)
    manifest = {'files_sha256': {'research/candidate/file.py': '0' * 64},
                'protected_baseline_files': 316}
    with pytest.raises(ValueError, match='LOCAL_REPLAY_SOURCE_CHANGED'):
        audit.load_engine(manifest, helper)
    assert 'torch' not in sys.modules


def simulated_mode():
    """Test orchestration with an injected replay engine, never native tensors."""
    from tools import audit_stored_packet_v3 as frozen
    documents, raw_files, inventory, calls = {}, {}, {}, []
    base = audit.BASE + 'prediction/viability_v4/'
    rejected = {**{field: False for field in audit.FIELDS}, 'native_runs': 0,
                'reserved_policy_units': 0, 'repair_required': False, 'repair_success': None}
    wrong = {**rejected, 'trace_valid': True, 'binding_correct': True,
             'native_runs': 1, 'reserved_policy_units': 10}
    reference_verdict = {**wrong, **{field: True for field in audit.FIELDS}}
    tasks, predictions, aggregation = [], [], []
    for index in range(72):
        task = {'public': {'synthetic_case': index}, 'target': {'synthetic': 'gold'},
                'provenance': {'evaluation_group': ('same_depth', 'wording_shift', 'deeper_calls')[index // 24]}}
        tasks.append(task)
        actions = {arm: {'synthetic': 'wrong'} if arm == 'cas_trained' else {'status': 'REJECTED'}
                   for arm in audit.ARMS}
        predictions.append({'case_index': index, 'public_sha256': frozen.digest(task['public']), 'actions': actions})
        folder = base + f'evaluation/case_{index:04d}'
        documents[folder + '/reference_result.json'] = {'runtime_identity': 'synthetic'}
        documents[folder + '/reference_verdict.json'] = deepcopy(reference_verdict)
        arms = {}
        for arm, action in actions.items():
            invalid = arm != 'cas_trained'
            verdict = deepcopy(rejected if invalid else wrong)
            documents[folder + '/' + arm + '/verification.json'] = verdict
            documents[folder + '/' + arm + '/execution_result.json'] = (
                {'status': 'REJECTED', 'action': action, 'failure': 'synthetic rejection',
                 'reserved_policy_units': 0, 'native_runs': 0}
                if invalid else {'runtime_identity': 'synthetic'})
            documents[folder + '/' + arm + '/case_receipt.json'] = {
                'case_index': index, 'arm': arm, 'action': action,
                'verification': verdict, 'model_rejection': invalid}
            arms[arm] = {'verification': verdict, 'model_rejection': invalid,
                         'execution_status': 'REJECTED' if invalid else 'EXECUTED', 'wall_seconds': 0.0}
        aggregation.append({'case_index': index, 'arms': arms})
    raw = b''.join(frozen.canonical(row) + b'\n' for row in predictions)
    raw_files[base + 'predictions.jsonl'] = raw
    documents[base + 'predictions_seal.json'] = {'sha256': sha256(raw).hexdigest()}
    documents[audit.BASE + 'dataset/test_public.json'] = [task['public'] for task in tasks]
    documents[base + 'evaluation_results.json'] = {'results': aggregate_cases(aggregation, 72)}
    positions = {name: list(range(start, start + 24)) for name, start in
                 [('same_depth', 0), ('wording_shift', 24), ('deeper_calls', 48)]}
    groups = {name: aggregate_cases([{**aggregation[index], 'case_index': offset}
                                   for offset, index in enumerate(indices)], 24)
              for name, indices in positions.items()}
    documents[base + 'evaluation_groups.json'] = {'schema': 'cas-meta2-group-results/3',
        'groups': groups, 'group_case_indices': positions}
    documents[base + 'native_receipt.json'] = {'cases': 72, 'arm_verdicts': 360, 'groups': groups}
    def native(packet, result, folder, public, expected_action, *, reference=False):
        # The candidate must receive its sealed wrong action, never substituted gold.
        assert expected_action == {'synthetic': 'gold' if reference else 'wrong'}
        calls.append((public['synthetic_case'], reference, expected_action))
        return {'action': expected_action}
    def same_hash(name, expected):
        assert sha256(raw_files[name]).hexdigest() == expected
    packet = SimpleNamespace(json=lambda name: documents[name], raw=lambda name: raw_files[name],
        inventory=inventory, helper=helper, same_hash=same_hash)
    engine = SimpleNamespace(digest=frozen.digest, _native=native,
        reference_verdict=lambda task, result: deepcopy(reference_verdict),
        candidate_verdict=lambda task, action, actual, reference: deepcopy(wrong),
        compare_verdict=frozen.compare_verdict,
        admission_error=lambda action, public: 'synthetic rejection' if action.get('status') == 'REJECTED' else None)
    return packet, engine, tasks, documents, calls


def test_complete_simulated_mode_does_not_count_valid_trace_as_correct_task():
    packet, engine, tasks, documents, calls = simulated_mode()
    result = audit.audit_mode(packet, engine, 'viability_v4', tasks)
    assert result['references_checked'] == 72 and result['arm_choices_checked'] == 360
    assert len(calls) == 144
    assert result['metrics']['cas_trained']['trace_valid'] == 72
    assert result['metrics']['cas_trained']['task_correct'] == 0
    assert result['metrics']['cas_untrained']['model_rejection'] == 72


@pytest.mark.parametrize('mutation,reason', [
    ('forged_correctness', 'SAVED_CORRECTNESS'),
    ('rejected_native_write', 'REJECTION_HAS_NATIVE_WRITES'),
    ('public_mismatch', 'SEALED_TASK_MAPPING')])
def test_simulated_mode_rejects_forged_or_mismatched_outcomes(mutation, reason):
    packet, engine, tasks, documents, calls = simulated_mode()
    base = audit.BASE + 'prediction/viability_v4/evaluation/case_0000/'
    if mutation == 'forged_correctness':
        documents[base + 'cas_trained/verification.json']['task_correct'] = True
    elif mutation == 'rejected_native_write':
        packet.inventory[base + 'cas_untrained/native/native.db'] = {}
    else:
        tasks[0] = {**tasks[0], 'public': {'synthetic_case': -1}}
    with pytest.raises(ValueError, match=reason):
        audit.audit_mode(packet, engine, 'viability_v4', tasks)
