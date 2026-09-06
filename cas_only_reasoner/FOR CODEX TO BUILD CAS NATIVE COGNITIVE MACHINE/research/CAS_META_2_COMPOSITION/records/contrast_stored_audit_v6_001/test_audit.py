"""Pure synthetic audit tests. No registered tasks, model execution, or provider."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('contrast_audit_under_test', HERE/'audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
sys.meta_path.insert(0, audit.Guard())
from tools import inspect_cloud_packet as helper
from tools import audit_stored_packet_v3 as frozen
from cas_meta2.campaign_v3 import aggregate_cases


def fixture():
    """72 invented identifiers, no problem grammar or curriculum seed."""
    docs, raws, inventory, calls = {}, {}, {}, []
    tasks, predictions, neural, cases = [], [], [], []
    rejected = {**{k: False for k in audit.FIELDS}, 'native_runs': 0, 'reserved_policy_units': 0,
                'repair_required': False, 'repair_success': None}
    wrong = {**rejected, 'trace_valid': True, 'binding_correct': True, 'native_runs': 1, 'reserved_policy_units': 10}
    correct = {**wrong, **{k: True for k in audit.FIELDS}}
    for i in range(72):
        side = ('same_depth', 'wording_shift', 'deeper_calls')[i % 3]
        task = {'task_id': 'synthetic-'+str(i), 'public': {'synthetic_case': i},
                'target': {'synthetic': 'gold'}, 'contrast_side': side,
                'provenance': {'depth': 4 if side == 'deeper_calls' else 3, 'evaluation_group': 'test'}}
        tasks.append(task)
        actions = {arm: {'synthetic': 'wrong' if arm == 'cas_trained' else 'gold'}
                   if arm in ('cas_trained', 'rule') else {'status': 'REJECTED'} for arm in audit.ARMS}
        prediction = {'case_index': i, 'public_sha256': frozen.digest(task['public']), 'actions': actions}
        predictions.append(prediction)
        neural.append({**prediction, 'actions': {a: v for a, v in actions.items() if a != 'rule'}})
        folder = audit.NATIVE+f'evaluation/case_{i:04d}'
        docs[folder+'/reference_result.json'] = {'runtime_identity': 'SYNTHETIC ONLY'}
        docs[folder+'/reference_verdict.json'] = deepcopy(correct)
        arms = {}
        for arm, action in actions.items():
            invalid = action.get('status') == 'REJECTED'
            verdict = deepcopy(rejected if invalid else correct if arm == 'rule' else wrong)
            result = ({'status': 'REJECTED', 'action': action, 'failure': 'synthetic rejection',
                       'reserved_policy_units': 0, 'native_runs': 0} if invalid else
                      {'status': 'EXECUTED', 'runtime_identity': 'SYNTHETIC ONLY'})
            row = {'case_index': i, 'arm': arm, 'action': action, 'verification': verdict,
                   'model_rejection': invalid, 'execution_status': result['status'],
                   'failure': result.get('failure'), 'wall_seconds': 0.0}
            docs[folder+'/'+arm+'/execution_result.json'] = result
            docs[folder+'/'+arm+'/verification.json'] = verdict
            docs[folder+'/'+arm+'/case_receipt.json'] = row
            arms[arm] = row
        whole = {'case_index': i, 'task_id': task['task_id'], 'arms': arms, 'reference_verification': deepcopy(correct)}
        docs[folder+'/case_receipt.json'] = whole
        cases.append(whole)
    def raw(name, value, lines=False):
        data = b''.join(audit.canonical(x)+b'\n' for x in value) if lines else audit.canonical(value)
        raws[name] = data
        inventory[name] = {'path': name, 'bytes': len(data), 'sha256': sha256(data).hexdigest()}
        if not lines:
            docs[name] = value
        return sha256(data).hexdigest()
    public_hash = raw(audit.BASE+'dataset/test_public.json', [task['public'] for task in tasks])
    private_hash = raw(audit.BASE+'dataset/test_private.json', tasks)
    manifest_hash = raw(audit.BASE+'dataset/manifest.json', {'sha256': {
        'test_public.json': public_hash, 'test_private.json': private_hash}})
    neural_hash = raw(audit.BASE+'training/neural_predictions.jsonl', neural, True)
    prediction_hash = raw(audit.NATIVE+'predictions.jsonl', predictions, True)
    seal = {'schema': 'cas-meta2-contrast-evaluation-seal/6', 'arms': list(audit.ARMS), 'test_examples': 72,
            'prediction_count': 360, 'sha256': prediction_hash, 'neural_predictions_sha256': neural_hash,
            'manifest_sha256': manifest_hash}
    docs[audit.NATIVE+'predictions_seal.json'] = seal
    results = aggregate_cases(cases, 72)
    positions = audit.group_positions(tasks)
    groups = {name: aggregate_cases([{**cases[i], 'case_index': offset} for offset, i in enumerate(indices)], len(indices))
              for name, indices in positions.items()}
    docs[audit.NATIVE+'evaluation_results.json'] = {'cases': cases, 'results': results, 'groups': groups}
    docs[audit.NATIVE+'native_receipt.json'] = {'schema': 'cas-meta2-contrast-native-evaluation/6',
        'completed': True, 'cases': 72, 'reference_cases': 72, 'arm_verdicts': 360,
        'learning_accepted': False, 'seal': seal, 'results': results, 'groups': groups}
    def native(packet, result, folder, public, expected_action, *, reference=False):
        assert '/native/evaluation/case_' in folder
        assert expected_action['synthetic'] in (('gold',) if reference else ('gold', 'wrong'))
        calls.append((public['synthetic_case'], reference, expected_action))
        return expected_action
    def same_hash(name, expected):
        audit.require(inventory[name]['sha256'] == expected, 'MEMBER_SEAL_MISMATCH')
    packet = SimpleNamespace(json=lambda name: docs[name], raw=lambda name: raws[name],
        inventory=inventory, same_hash=same_hash)
    engine = SimpleNamespace(digest=frozen.digest, _native=native,
        reference_verdict=lambda task, result: deepcopy(correct),
        candidate_verdict=lambda task, action, actual, ref: deepcopy(correct if action['synthetic'] == 'gold' else wrong),
        compare_verdict=frozen.compare_verdict,
        parse_problem=lambda public: {'synthetic': 'gold'},
        admission_error=lambda action, public: 'synthetic rejection' if action.get('status') == 'REJECTED' else None)
    return packet, engine, docs, tasks, calls


class AuditTests(unittest.TestCase):
    def setUp(self):
        (HERE/'scratch').mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix='pure-', dir=HERE/'scratch')
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def files(self):
        root = self.root/'extraction'
        root.mkdir()
        raw = b'{"synthetic":true}\n'
        (root/'example.json').write_bytes(raw)
        inventory = [{'path': 'example.json', 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}]
        return root, inventory, audit.Files(root, inventory, helper)

    def test_valid_trace_is_not_correct_answer(self):
        packet, engine, docs, tasks, calls = fixture()
        result = audit.audit_outcomes(packet, engine)
        self.assertEqual(len(calls), 216)
        self.assertEqual(result['references_checked'], 72)
        self.assertEqual(result['arm_choices_checked'], 360)
        self.assertEqual(result['metrics']['cas_trained']['task_correct'], 0)
        self.assertEqual(result['metrics']['cas_trained']['trace_valid'], 72)
        self.assertEqual(result['metrics']['rule']['task_correct'], 72)
        self.assertEqual(result['groups']['depth_3']['cas_trained']['total'], 48)
        self.assertEqual(result['groups']['depth_4']['cas_trained']['total'], 24)
        self.assertEqual(result['groups']['wording_shift']['cas_untrained']['model_rejection'], 24)

    def test_changed_saved_verdict_rejected(self):
        packet, engine, docs, tasks, calls = fixture()
        docs[audit.NATIVE+'evaluation/case_0000/cas_trained/verification.json']['task_correct'] = True
        with self.assertRaisesRegex(ValueError, 'SAVED_CORRECTNESS'):
            audit.audit_outcomes(packet, engine)

    def test_rejected_native_writes_refused(self):
        packet, engine, docs, tasks, calls = fixture()
        packet.inventory[audit.NATIVE+'evaluation/case_0000/cas_untrained/native/native.db'] = {}
        with self.assertRaisesRegex(ValueError, 'REJECTION_HAS_NATIVE_WRITES'):
            audit.audit_outcomes(packet, engine)

    def test_reference_identity_mismatch_refused(self):
        packet, engine, docs, tasks, calls = fixture()
        docs[audit.NATIVE+'evaluation/case_0000/cas_trained/execution_result.json']['runtime_identity'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'CANDIDATE_REFERENCE_IDENTITY'):
            audit.audit_outcomes(packet, engine)

    def test_neural_action_cannot_be_changed_after_seal(self):
        packet, engine, docs, tasks, calls = fixture()
        name = audit.NATIVE+'predictions.jsonl'
        old_raw = packet.raw
        rows = [audit.decode(line) for line in old_raw(name).splitlines()]
        rows[0]['actions']['cas_trained'] = {'synthetic': 'gold'}
        changed = b''.join(audit.canonical(row)+b'\n' for row in rows)
        packet.raw = lambda key: changed if key == name else old_raw(key)
        with self.assertRaisesRegex(ValueError, 'SEALED_TASK_MAPPING'):
            audit.audit_outcomes(packet, engine)

    def test_native_seal_schema_required(self):
        packet, engine, docs, tasks, calls = fixture()
        docs[audit.NATIVE+'predictions_seal.json']['schema'] = 'cas-meta2-prediction-seal/1'
        with self.assertRaisesRegex(ValueError, 'V6_NATIVE_SEAL'):
            audit.audit_outcomes(packet, engine)

    def test_rule_uses_only_frozen_public_parser(self):
        packet, engine, docs, tasks, calls = fixture()
        engine.parse_problem = lambda public: {'synthetic': 'different'}
        with self.assertRaisesRegex(ValueError, 'RULE_PUBLIC_INPUT'):
            audit.audit_outcomes(packet, engine)

    def test_baseline_private_hash_required(self):
        packet, engine, docs, tasks, calls = fixture()
        docs[audit.BASE+'dataset/manifest.json']['sha256']['test_private.json'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'MEMBER_SEAL'):
            audit.audit_outcomes(packet, engine)

    def test_current_top_level_group_key_required(self):
        _, _, _, tasks, _ = fixture()
        tasks[0]['provenance']['contrast_side'] = tasks[0].pop('contrast_side')
        with self.assertRaises(KeyError):
            audit.group_positions(tasks)

    def test_old_evaluation_group_refused(self):
        _, _, _, tasks, _ = fixture()
        tasks[0]['provenance']['evaluation_group'] = 'same_depth'
        with self.assertRaisesRegex(ValueError, 'V6_GROUP_MAPPING'):
            audit.group_positions(tasks)

    def test_wrong_depth_refused(self):
        _, _, _, tasks, _ = fixture()
        tasks[0]['provenance']['depth'] = 4
        with self.assertRaisesRegex(ValueError, 'V6_GROUP_MAPPING'):
            audit.group_positions(tasks)

    def test_group_coverage_refused(self):
        _, _, _, tasks, _ = fixture()
        tasks[0]['contrast_side'] = 'wording_shift'
        with self.assertRaisesRegex(ValueError, 'GROUP_COUNTS'):
            audit.group_positions(tasks)

    def test_aggregate_changes_refused(self):
        packet, engine, docs, tasks, calls = fixture()
        derived = audit.audit_outcomes(packet, engine)['cases']
        saved = docs[audit.NATIVE+'evaluation_results.json']['results']
        for field, value in [('task_correct', 72), ('trace_valid', True), ('total', 71),
            ('model_rejections', True), ('native_executed', False), ('native_runs', 0),
            ('reserved_policy_units', 0), ('task_accuracy', 1.0), ('all_cases_in_denominator', False),
            ('repair_required_total', 1), ('repair_success', 1)]:
            with self.subTest(field=field):
                changed = deepcopy(saved)
                changed['cas_trained'][field] = value
                with self.assertRaisesRegex(ValueError, 'AGGREGATE'):
                    audit.recount(derived, changed)

    def test_file_change_is_detected_on_read(self):
        root, inventory, packet = self.files()
        self.assertEqual(packet.json('example.json'), {'synthetic': True})
        (root/'example.json').write_bytes(b'{"synthetic":false}')
        with self.assertRaisesRegex(ValueError, 'MEMBER_CHANGED'):
            packet.raw('example.json')

    def test_added_file_is_rejected(self):
        root, inventory, packet = self.files()
        (root/'added.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'UNINDEXED_MEMBER'):
            packet.verify_all()

    def test_removed_file_is_rejected(self):
        root, inventory, packet = self.files()
        (root/'example.json').unlink()
        with self.assertRaisesRegex(ValueError, 'EXTRACTED_INVENTORY'):
            packet.verify_all()

    def test_bad_inventory_rows_refused(self):
        root, inventory, packet = self.files()
        for field, value in [('path', '../example.json'), ('bytes', True), ('bytes', -1), ('sha256', 'bad')]:
            with self.subTest(field=field, value=value):
                changed = deepcopy(inventory)
                changed[0][field] = value
                with self.assertRaises(ValueError):
                    audit.Files(root, changed, helper)
        with self.assertRaisesRegex(ValueError, 'INVENTORY_ROW'):
            audit.Files(root, inventory+inventory, helper)

    def test_duplicate_and_nonfinite_json_refused(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                audit.decode(raw)

    def test_external_source_identity_required_before_file_access(self):
        with self.assertRaisesRegex(ValueError, 'EXACT_SOURCE_SHA'):
            audit.audit('missing', review_sha256='a'*64, source_archive='missing', source_sha256='b'*64,
                source_sha='main', packet='missing', packet_sha256='c'*64, job='bad', extracted='missing', output='missing')

    def test_changed_source_rejected_before_engine_load(self):
        root = self.root/'research'/'candidate'
        root.mkdir(parents=True)
        (root/'file.py').write_bytes(b'changed')
        with patch.object(audit, 'ROOT', root), self.assertRaisesRegex(ValueError, 'LOCAL_REPLAY_SOURCE_CHANGED'):
            audit.load_engine({'protected_baseline_files': 316,
                'files_sha256': {'research/candidate/file.py': '0'*64}}, helper)

    def test_forbidden_import_guard(self):
        for name in audit.FORBIDDEN:
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'NEURAL_OR_PROVIDER_IMPORT'):
                audit.Guard().find_spec(name)
        self.assertFalse(set(sys.modules) & audit.FORBIDDEN)

    def test_every_trace_export_is_checked_against_database(self):
        root = self.root/'exports'
        root.mkdir()
        trace = {'schema_version': 'cas.neural-cjt.tick-trace/0.2', 'contract_type': 'TICK_TRACE', 'synthetic': True}
        database = root/'native.db'
        conn = sqlite3.connect(database)
        conn.execute('CREATE TABLE trace_events (sequence INTEGER, payload_json TEXT)')
        conn.execute('INSERT INTO trace_events VALUES (1, ?)', (audit.canonical(trace).decode(),))
        conn.commit()
        conn.close()
        name = 'synthetic/native_traces.json'
        data = {name: [trace]}
        packet = SimpleNamespace(inventory={name: {}, 'synthetic/native.db': {}},
                                 json=lambda n: data[n], path=lambda n: database)
        validated = []
        validator = SimpleNamespace(validate=lambda value: validated.append(value))
        result = audit.validate_exports(packet, validator)
        self.assertEqual(result['stored_traces'], 1)
        self.assertEqual(validated, [trace])
        data[name] = [{**trace, 'synthetic': False}]
        with self.assertRaisesRegex(ValueError, 'TRACE_EXPORT_DATABASE_MISMATCH'):
            audit.validate_exports(packet, validator)


if __name__ == '__main__':
    unittest.main(verbosity=2)
