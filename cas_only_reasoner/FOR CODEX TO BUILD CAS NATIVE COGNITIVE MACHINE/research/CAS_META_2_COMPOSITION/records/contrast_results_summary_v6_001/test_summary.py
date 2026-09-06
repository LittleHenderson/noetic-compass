"""Pure synthetic report checks. No current packet, model, or private tasks."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('summary_under_test', HERE/'summary.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
JOB = 'cas-meta2-20000101000000-aaaaaaaa'
SOURCE, SOURCE_HASH, PACKET_HASH, REVIEW_HASH, AUDIT_HASH = 'a'*40, 'b'*64, 'c'*64, 'd'*64, 'e'*64


def bound_receipts():
    common = {'job': JOB, 'source_sha': SOURCE, 'packet_sha256': PACKET_HASH, 'learning_accepted': False}
    review = {**common, 'schema': 'cas-meta2-offline-contrast-review/6', 'status': 'RECORDED_CONTRAST_RECOUNT_PASSED',
        'neural_execution': False, 'provider_calls': False, 'source_and_extraction_rechecked_at_end': True,
        'source_archive_sha256': SOURCE_HASH}
    audit = {**common, 'schema': 'cas-meta2-contrast-stored-audit/6', 'status': 'STORED_CONTRAST_AUDIT_PASSED',
        'completed': True, 'errors': [], 'review_receipt_sha256': REVIEW_HASH,
        'source_archive_sha256': SOURCE_HASH, 'neural_execution_performed': False}
    diag = {**common, 'schema': 'cas-meta2-contrast-error-report/6', 'stored_audit_sha256': AUDIT_HASH, 'neural_execution': False}
    return review, audit, diag


def assembled():
    splits = {}
    counts = {'train': {'1': 128, '2': 256, '3': 256}, 'validation': {'1': 32, '2': 32, '3': 32}, 'test': {'3': 48, '4': 24}}
    for split, depths in counts.items():
        tasks = []
        for depth, count in depths.items():
            for _ in range(count):
                index = len(tasks)
                side = ('same_depth' if index % 2 == 0 else 'wording_shift') if depth == '3' else 'deeper_calls'
                tasks.append({'task_id': split+'-synthetic-'+str(index),
                    'contrast_group': str(index % 24) if split == 'test' else str(index),
                    'contrast_side': side, 'provenance': {'depth': int(depth), 'evaluation_group': split,
                        'graph_signature': split+'-synthetic-signature-'+str(index)}})
        splits[split] = tasks
    manifest = {'splits': {name: {'tasks': len(tasks), 'depths': counts[name],
        'groups': len({t['contrast_group'] for t in tasks})} for name, tasks in splits.items()}}
    old = ['synthetic-excluded-'+str(i) for i in range(256)]
    exclusions = {'schema': 'cas-meta2-known-exposures/6', 'count': 8053,
                  'graph_signatures': old+['synthetic-other-excluded-'+str(i) for i in range(8053-256)],
                  'origins': {'contrast_prototype_seed_926601': {'count': 256, 'graph_signatures': old}}}
    return manifest, splits, exclusions


def outcome_fixture():
    from collections import Counter, defaultdict
    _, splits, _ = assembled()
    tasks = splits['test']
    cases, diagnostics = [], []
    metric = defaultdict(lambda: defaultdict(Counter))
    summaries = defaultdict(Counter)
    for index, task in enumerate(tasks):
        case = {'case_index': index, 'task_id': task['task_id'], 'arms': {}}
        depth, side = task['provenance']['depth'], task['contrast_side']
        for arm in s.ARMS:
            correct = arm == 'rule'
            reject = arm in ('cas_untrained', 'generic_untrained')
            actual = {k: correct for k in s.FIELDS}
            actual.update(trace_valid=not reject, binding_correct=not reject, model_rejection=reject,
                          native_runs=int(not reject), reserved_policy_units=10*int(not reject))
            case['arms'][arm] = actual
            site = {'observation_binding_correct': int(not reject), 'observation_binding_expected': 1,
                'named_input_sites_correct': 4*int(correct), 'named_input_sites_expected': 4,
                'named_child_sites_correct': int(correct), 'named_child_sites_expected': 1}
            row = {'case_index': index, 'task_id': task['task_id'], 'arm': arm, 'depth': depth, 'condition': side,
                'task_correct': correct, 'execution_status': 'REJECTED' if reject else 'EXECUTED',
                'named_site_diagnostic': {'counts': site, 'errors': []}}
            if not correct:
                row['first_observed_boundary'] = 'pre_execution_rejection' if reject else 'recorded_trajectory_divergence'
                if not reject:
                    row['first_observed_difference'] = {'categories': ['input_reference', 'call_target']}
            diagnostics.append(row)
            for group in ('all', 'depth_'+str(depth), side):
                metric[group][arm]['total'] += 1
                metric[group][arm].update({k: int(v) for k, v in actual.items()})
            for group in (arm+'/all', arm+'/depth/'+str(depth), arm+'/condition/'+side):
                summary = summaries[group]
                summary.update(attempted=1, correct=int(correct))
                summary.update(site)
                if not correct:
                    summary[row['first_observed_boundary']] += 1
                    if not reject:
                        summary['first_difference/input_reference'] += 1
                        summary['first_difference/call_target'] += 1
        cases.append(case)
    audit = {'outcomes': {'cases': cases, 'metrics': dict(metric['all']),
                          'groups': {k: dict(v) for k, v in metric.items() if k != 'all'}}}
    return tasks, audit, {'cases': diagnostics, 'summaries': dict(summaries)}


def learning_fixture():
    checkpoints, history, inventory = {}, [], {}
    for epoch in (0, 200):
        score = {'epoch': epoch, 'token_cross_entropy': 1.0 if epoch == 0 else 0.2,
            'generation': {'overall': {'total': 96, 'joint_correct': 0 if epoch == 0 else 60},
                'by_depth': {d: {'total': 32, 'joint_correct': 0 if epoch == 0 else 20} for d in ('1', '2', '3')}}}
        history.append({'epoch': epoch, 'optimizer_steps': {'cas': 0 if epoch == 0 else 8000,
            'generic': 0 if epoch == 0 else 8000}, 'families': {f: {'validation': deepcopy(score), 'selected': epoch > 0}
                                                           for f in ('cas', 'generic')}})
    for family in ('cas', 'generic'):
        record = {'family': family, 'path': family+'_selected_epoch_0200.pt', 'sha256': 'f'*64, 'epoch': 200}
        checkpoints[family] = {'selected': record}
        inventory[s.BASE+'training/'+record['path']] = {'sha256': record['sha256']}
    training = {'schema': 'cas-meta2-contrast-training/6', 'completed': True, 'learning_accepted': False,
        'completed_epochs': 200, 'optimizer_steps': {'cas': 8000, 'generic': 8000}, 'history': history, 'checkpoints': checkpoints}
    registration = {'private_labels_read': False, 'probe_used_for_selection': False,
                    'selection_rule': 'SYNTHETIC VALIDATION RULE', 'parameter_matching': {'synthetic': True}}
    review = {'history': deepcopy(history), 'optimizer_steps': dict(training['optimizer_steps']),
              'training_gate': {'checkpoints': deepcopy(checkpoints)}}
    return training, registration, review, inventory


class SummaryTests(unittest.TestCase):
    def test_no_neural_provider_imports(self):
        import sys
        self.assertFalse(set(sys.modules) & {'torch', 'casformer', 'cas_cjt', 'boto3', 'botocore', 'tensorflow', 'jax', 'cupy'})

    def test_three_completed_receipts_bind_same_run(self):
        review, audit, diag = bound_receipts()
        s.identities(review, audit, diag, packet_sha=PACKET_HASH, source_sha=SOURCE, source_hash=SOURCE_HASH,
                     job=JOB, review_sha=REVIEW_HASH, audit_sha=AUDIT_HASH)
        for target, field, value in [('review', 'source_archive_sha256', '0'*64), ('audit', 'completed', False),
                                    ('audit', 'review_receipt_sha256', '0'*64), ('diag', 'stored_audit_sha256', '0'*64),
                                    ('diag', 'learning_accepted', True), ('diag', 'job', 'different')]:
            with self.subTest(target=target, field=field):
                values = {'review': deepcopy(review), 'audit': deepcopy(audit), 'diag': deepcopy(diag)}
                values[target][field] = value
                with self.assertRaises(ValueError):
                    s.identities(values['review'], values['audit'], values['diag'], packet_sha=PACKET_HASH,
                        source_sha=SOURCE, source_hash=SOURCE_HASH, job=JOB, review_sha=REVIEW_HASH, audit_sha=AUDIT_HASH)

    def test_actual_split_counts_and_old_prototype_exclusion(self):
        manifest, splits, excluded = assembled()
        result = s.split_counts(manifest, splits, excluded)
        self.assertEqual(result['assembled']['train']['tasks'], 640)
        self.assertEqual(result['assembled']['test']['depths'], {'3': 48, '4': 24})
        self.assertFalse(result['familiar_known_program_test_evaluation_in_v6'])
        splits['train'][0]['provenance']['graph_signature'] = excluded['graph_signatures'][0]
        with self.assertRaisesRegex(ValueError, 'EXPOSED_GRAPH'):
            s.split_counts(manifest, splits, excluded)

    def test_manifest_count_cannot_replace_actual_rows(self):
        manifest, splits, excluded = assembled()
        splits['train'].pop()
        with self.assertRaisesRegex(ValueError, 'ASSEMBLED_SPLIT_MANIFEST'):
            s.split_counts(manifest, splits, excluded)

    def test_all_outcomes_derived_and_trace_not_task_success(self):
        tasks, audit, diag = outcome_fixture()
        result = s.outcomes(tasks, audit, diag)
        self.assertEqual(result['arm_choices_bound'], 360)
        groups = result['native_task_outcomes']
        self.assertEqual(groups['all']['cas_trained']['task_correct'], 0)
        self.assertEqual(groups['all']['cas_trained']['trace_valid'], 72)
        self.assertEqual(groups['depth_3']['cas_untrained']['attempted'], 48)
        self.assertEqual(groups['depth_4']['rule']['task_correct'], 24)
        self.assertEqual(result['diagnostics']['cas_trained/all']['first_difference/input_reference'], 72)
        self.assertEqual(result['diagnostics']['cas_trained/all']['first_difference/call_target'], 72)

    def test_missing_duplicate_and_changed_outcome_rows_rejected(self):
        for change in ('missing', 'duplicate', 'correctness', 'depth', 'status', 'named_count', 'summary'):
            with self.subTest(change=change):
                tasks, audit, diag = outcome_fixture()
                if change == 'missing': diag['cases'].pop()
                if change == 'duplicate': diag['cases'][-1] = deepcopy(diag['cases'][0])
                if change == 'correctness': diag['cases'][0]['task_correct'] = True
                if change == 'depth': diag['cases'][0]['depth'] = 4
                if change == 'status': diag['cases'][0]['execution_status'] = 'EXECUTED'
                if change == 'named_count': diag['cases'][0]['named_site_diagnostic']['counts']['named_child_sites_correct'] = 2
                if change == 'summary': diag['summaries']['cas_untrained/all']['attempted'] = 71
                with self.assertRaises(ValueError):
                    s.outcomes(tasks, audit, diag)

    def test_audit_denominator_cannot_change(self):
        tasks, audit, diag = outcome_fixture()
        audit['outcomes']['groups']['depth_4']['cas_trained']['total'] = 25
        with self.assertRaisesRegex(ValueError, 'AUDIT_GROUP_RECOUNT'):
            s.outcomes(tasks, audit, diag)

    def test_budget_missing_is_unavailable_not_zero(self):
        result = s.money(None, None, source_sha=SOURCE, source_hash=SOURCE_HASH, job=JOB, packet_sha=PACKET_HASH)
        self.assertIsNone(result['reservation'])
        self.assertIsNone(result['cost_estimate'])
        self.assertIsNone(result['aws_invoice'])

    def test_budget_reserved_not_cost_and_no_refund(self):
        ledger = {'schema': 'cas-meta-campaign-budget/2', 'owner_task_cap_usd': '400.00',
            'reservations': [{'job': JOB, 'source_sha': SOURCE, 'archive_sha256': SOURCE_HASH,
                'status': 'RESERVED_NO_AUTOMATIC_REFUND', 'reserved_usd': '7.00'}],
            'total_reserved_usd': '7.00', 'remaining_unreserved_usd': '393.00', 'revision': 1, 'updated_utc': 'synthetic'}
        launch = {'job': JOB, 'source_sha': SOURCE, 'archive_sha256': SOURCE_HASH, 'result': {'sha256': PACKET_HASH},
            'cost_estimate': {'compute_ebs_ipv4_usd_estimate': '0.50', 'instance_wall_clock_seconds_upper_observation': 600,
                              'excluded': 'Other charges; not an AWS invoice'}, 'termination_confirmed': True, 'cleanup_errors': []}
        result = s.money(ledger, launch, source_sha=SOURCE, source_hash=SOURCE_HASH, job=JOB, packet_sha=PACKET_HASH)
        self.assertEqual(result['reservation']['job_reserved_usd'], '7.00')
        self.assertEqual(result['cost_estimate']['compute_ebs_ipv4_usd_estimate'], '0.50')
        self.assertIsNone(result['aws_invoice'])
        ledger['remaining_unreserved_usd'] = '393.50'
        with self.assertRaisesRegex(ValueError, 'BUDGET_TOTAL'):
            s.money(ledger, launch, source_sha=SOURCE, source_hash=SOURCE_HASH, job=JOB, packet_sha=PACKET_HASH)

    def test_negative_and_nonfinite_budget_rejected(self):
        for amount in ('-1.0', 'NaN', 'Infinity', '0.0'):
            ledger = {'schema': 'cas-meta-campaign-budget/2', 'owner_task_cap_usd': '400.00',
                'reservations': [{'job': JOB, 'status': 'RESERVED_NO_AUTOMATIC_REFUND', 'reserved_usd': amount}]}
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                s.money(ledger, None, source_sha=SOURCE, source_hash=SOURCE_HASH, job=JOB, packet_sha=PACKET_HASH)

    def test_packet_member_is_bound_to_reviewed_hash(self):
        content = b'{"synthetic":true}'
        memory = io.BytesIO()
        with zipfile.ZipFile(memory, 'w') as archive:
            archive.writestr('synthetic.json', content)
        with zipfile.ZipFile(io.BytesIO(memory.getvalue())) as archive:
            review = {'inventory': [{'path': 'synthetic.json', 'bytes': len(content), 'sha256': sha256(content).hexdigest()}]}
            reader = s.Packet(archive, review)
            self.assertEqual(reader.read('synthetic.json'), {'synthetic': True})
            review['inventory'][0]['sha256'] = '0'*64
            with self.assertRaisesRegex(ValueError, 'MEMBER_HASH_CHANGED'):
                reader.read('synthetic.json')

    def test_duplicate_nonfinite_json_rejected(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                s.decode(raw)

    def test_validation_selection_is_not_native_outcome(self):
        training, registration, review, inventory = learning_fixture()
        result = s.learning(training, registration, review, inventory)
        self.assertTrue(result['validation_only_selection'])
        self.assertFalse(result['probe_used_for_selection'])
        self.assertEqual(result['selected_checkpoints']['cas']['epoch'], 200)
        self.assertEqual(len(result['validation_action_curves']['cas']), 2)
        self.assertIn('not native full-task execution', result['boundary'])

    def test_checkpoint_mismatch_or_test_selection_rejected(self):
        for change in ('checkpoint', 'private_labels', 'probe_selection', 'denominator'):
            with self.subTest(change=change):
                training, registration, review, inventory = learning_fixture()
                if change == 'checkpoint': inventory[s.BASE+'training/cas_selected_epoch_0200.pt']['sha256'] = '0'*64
                if change == 'private_labels': registration['private_labels_read'] = True
                if change == 'probe_selection': registration['probe_used_for_selection'] = True
                if change == 'denominator':
                    training['history'][0]['families']['cas']['validation']['generation']['overall']['total'] = 72
                    review['history'] = deepcopy(training['history'])
                with self.assertRaises(ValueError):
                    s.learning(training, registration, review, inventory)

    def test_markdown_preserves_boundaries_and_attempt_denominators(self):
        manifest, splits, excluded = assembled()
        tasks, audit, diagnostics = outcome_fixture()
        training, registration, review, inventory = learning_fixture()
        result = {'dataset': s.split_counts(manifest, splits, excluded), 'outcomes': s.outcomes(tasks, audit, diagnostics),
            'learning': s.learning(training, registration, review, inventory), 'job': JOB, 'source_sha': SOURCE,
            'packet_sha256': PACKET_HASH, 'historical': {'references': {'familiar_fit': {'path': '/synthetic/fit.json', 'sha256': 'f'*64}}},
            'compute': {'runtime': {'gpu': 'SYNTHETIC GPU NEVER EXECUTED', 'torch': 'synthetic', 'cuda': 'synthetic'},
                'campaign_wall_seconds': 1.0, 'training_wall_seconds': 0.5, 'native_wall_seconds': 0.2,
                'training_step_seconds': {'cas': 0.1, 'generic': 0.1}, 'optimizer_steps': {'cas': 8000, 'generic': 8000}},
            'budget': s.money(None, None, source_sha=SOURCE, source_hash=SOURCE_HASH, job=JOB, packet_sha=PACKET_HASH)}
        text = s.markdown(result)
        for expected in ('0/72 → 0/72', '0/48 → 0/48', '0/24 → 0/24', '24 matched triplets',
            'literal 256 prototype tasks are excluded', 'not native task learning curves',
            'semantically equivalent renaming', 'Categories can overlap', 'not assumed zero',
            'CAS 0/72, generic 12/72, rule 72/72', 'each reached 24/24', 'AWS invoice: not available'):
            with self.subTest(expected=expected):
                self.assertIn(expected, text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
