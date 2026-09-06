"""Pure synthetic checker tests: no real model, CUDA receipt, or native execution.

Uses only the already exposed seed-926603 saved development fixture. Never
generates tasks or reads the current registered campaign's output packet.
"""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('synthetic_contrast_review', HERE/'review.py')
r = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = r
spec.loader.exec_module(r)
sys.meta_path.insert(0, r.Guard())
from cas_meta2.contrast_v6 import curriculum as c, data as d, checks
from cas_meta2.codec import canonical_sha256

MANIFEST = {'pilot_dir': 'research/CAS_META_2_COMPOSITION'}
REMOTE = '/opt/cas-meta2/package/research/CAS_META_2_COMPOSITION/runs/cloud_job/campaign'
JOB = 'cas-meta2-20200101000000-01234567'
CFG = c.Config(train_flat=32, train_pairs_per_cell=8, validation_flat=8,
               validation_pairs_per_cell=2, test_triplets=3)
FIELDS = ('task_correct', 'procedure_correct', 'binding_correct', 'dependency_correct',
          'actual_output_correct', 'trace_valid')
ARMS = ('cas_untrained', 'cas_trained', 'generic_untrained', 'generic_trained', 'rule')


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(c.canonical(value)+b'\n')


class Packet:
    """In-memory fixture, not an AWS artifact or provider receipt."""
    def __init__(self):
        self.payload = {}
        self.inventory = {}

    def put(self, name, value):
        raw = value if type(value) is bytes else c.canonical(value)+b'\n'
        self.payload[name] = raw
        self.inventory[name] = {'path': name, 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}

    def raw(self, path, limit=None):
        return self.payload[path]

    def json(self, path):
        return d.decode(self.raw(path))


def gpu_fixture():
    packet, campaign = Packet(), {'processes': {}}
    expected, commands = r.gpu_cases(), r.gpu_commands(MANIFEST)
    for name, identities in expected.items():
        tree = ET.Element('testsuites')
        suite = ET.SubElement(tree, 'testsuite', tests=str(len(identities)), failures='0', errors='0', skipped='0')
        for cls, test in identities:
            ET.SubElement(suite, 'testcase', classname=cls, name=test, time='0')
        raw = ET.tostring(tree)
        if name != 'contrast_pipeline':
            prefix = 'cloud_job/gpu_'+('contract' if name == 'native' else 'policy')
            packet.put(prefix+'_tests.xml', raw)
            packet.put(prefix+'_command.json', commands[name])
            packet.put(prefix+'_receipt.json', {'passed': len(identities), 'tests': len(identities),
                                               'failures': 0, 'errors': 0, 'skipped': 0})
            packet.put(prefix+'_tests.log', b'SYNTHETIC ONLY - NOT A GPU RUN\n')
        else:
            packet.put(r.BASE+'gpu_test.xml', raw)
            campaign['gpu_gate'] = {'path': commands[name][-1], 'sha256': sha256(raw).hexdigest(),
                'tests': 1, 'passed': 1, 'failed': 0, 'errors': 0, 'skipped': 0,
                'cases': [{'classname': cls, 'name': test, 'failed': False, 'error': False, 'skipped': False}
                          for cls, test in identities]}
            process = {'command': commands[name], 'synthetic_fixture_only': True}
            campaign['processes']['gpu_gate'] = process
            packet.put(r.BASE+'processes/gpu_gate/process_receipt.json', process)
    return packet, campaign


def process_fixture(root, name, command, start, finish):
    directory = root/'processes'/name
    directory.mkdir(parents=True, exist_ok=True)
    for label in ('stdout', 'stderr'):
        (directory/(label+'.txt')).write_bytes(b'SYNTHETIC ONLY - NO PROCESS OR PROVIDER RUN\n')
    record = {'schema': 'cas-meta2-campaign-subprocess/3', 'completed': True,
        'returncode': 0, 'timed_out': False, 'pid': 123, 'new_process_group': True, 'automatic_retry': False,
        'command': command, 'started_utc': start, 'finished_utc': finish, 'wall_seconds': 1,
        'stdout_sha256': checks.file_hash(directory/'stdout.txt'), 'stderr_sha256': checks.file_hash(directory/'stderr.txt')}
    put(directory/'process_receipt.json', record)
    return record


def native_fixture(root):
    shutil.copytree(ROOT/'records/contrast_v6_bundle_probe_001/dataset', root/'dataset')
    m = checks.read(root/'dataset/manifest.json')
    tasks, publics = checks.read(root/'dataset/test_private.json'), checks.read(root/'dataset/test_public.json')
    native, training = root/'native', root/'training'
    native.mkdir()
    training.mkdir()
    report = {k: v for k, v in m.items() if k not in ('seed', 'config', 'sha256')}
    put(native/'cold_dataset_validation.json', report)
    process_fixture(root, 'training', ['SYNTHETIC TRAINING COMMAND'],
                    '2020-01-01T00:00:00+00:00', '2020-01-01T00:00:01+00:00')
    process_fixture(root, 'evaluate', ['/opt/cas-meta2/venv/bin/python', '-B', '-m',
        'cas_meta2.contrast_v6.campaign', '--output', REMOTE, '--job', JOB, '--phase', 'evaluate'],
        '2020-01-01T00:00:02+00:00', '2020-01-01T00:00:05+00:00')
    model = [{'case_index': i, 'public_sha256': canonical_sha256(public),
              'actions': {arm: None for arm in ARMS[:-1]}} for i, public in enumerate(publics)]
    raw_model = b''.join(c.canonical(row)+b'\n' for row in model)
    (training/'neural_predictions.jsonl').write_bytes(raw_model)
    gate = {'schema': 'cas-meta2-training-parent-gate/6', 'completed': True,
            'manifest_sha256': checks.file_hash(root/'dataset/manifest.json'),
            'predictions_sha256': sha256(raw_model).hexdigest(),
            'process_receipt_sha256': checks.file_hash(root/'processes/training/process_receipt.json')}
    put(native/'training_parent_gate.json', gate)
    rows = [{**row, 'actions': {**row['actions'], 'rule': task['target']}} for row, task in zip(model, tasks)]
    raw = b''.join(c.canonical(row)+b'\n' for row in rows)
    (native/'predictions.jsonl').write_bytes(raw)
    seal = {'schema': 'cas-meta2-contrast-evaluation-seal/6', 'sha256': sha256(raw).hexdigest(),
        'neural_predictions_sha256': gate['predictions_sha256'], 'parent_gate_sha256': canonical_sha256(gate),
        'manifest_sha256': gate['manifest_sha256'], 'arms': list(ARMS), 'test_examples': len(tasks),
        'prediction_count': len(tasks)*5, 'rule_input': 'public problem and permitted observations only',
        'sealed_utc': '2020-01-01T00:00:03+00:00'}
    put(native/'predictions_seal.json', seal)
    put(native/'native_receipt.json', {'seal': seal, 'synthetic_fixture_only': True})
    put(native/'private_opening_receipt.json', {'opened_utc': '2020-01-01T00:00:04+00:00',
        'prediction_sha256': seal['sha256'], 'training_exit_receipt_sha256': gate['process_receipt_sha256'],
        'private_sha256': m['sha256']['test_private.json']})
    cases = []
    for i, (task, row) in enumerate(zip(tasks, rows)):
        folder = native/'evaluation'/f'case_{i:04d}'
        reference = {'status': 'EXECUTED', 'reference': True, 'selected_action': task['target'],
                     'public_digest': canonical_sha256(task['public']), 'synthetic_fixture_only': True}
        ref_verdict = {field: True for field in FIELDS}
        put(folder/'reference_result.json', reference)
        put(folder/'reference_verdict.json', ref_verdict)
        case = {'case_index': i, 'task_id': task['task_id'], 'reference_verification': ref_verdict, 'arms': {}}
        for arm in ARMS:
            success = arm == 'rule'
            verdict = {**{field: success for field in FIELDS}, 'repair_required': False, 'repair_success': None}
            execution = {'status': 'EXECUTED' if success else 'REJECTED', 'synthetic_fixture_only': True}
            if success:
                execution.update(reference=False, selected_action=row['actions'][arm],
                                 public_digest=canonical_sha256(task['public']))
            else:
                execution['action'] = row['actions'][arm]
            item = {'case_index': i, 'arm': arm, 'action': row['actions'][arm], 'verification': verdict,
                    'execution_status': execution['status'], 'model_rejection': not success}
            case['arms'][arm] = item
            put(folder/arm/'case_receipt.json', item)
            put(folder/arm/'execution_result.json', execution)
            put(folder/arm/'verification.json', verdict)
        put(folder/'case_receipt.json', case)
        cases.append(case)
    put(native/'evaluation_results.json', {'cases': cases})
    return {'gate': gate, 'manifest': m, 'tasks': tasks, 'publics': publics, 'remote_output': REMOTE, 'job': JOB}


class ReviewTests(unittest.TestCase):
    def setUp(self):
        original_open = Path.open
        def no_current_results(path, *args, **kwargs):
            if path.absolute().is_relative_to(r.PACKET.parent.absolute()):
                raise AssertionError('CURRENT_CAMPAIGN_RESULT_READ_FORBIDDEN_IN_SYNTHETIC_TEST')
            return original_open(path, *args, **kwargs)
        trap = patch.object(Path, 'open', no_current_results)
        trap.start()
        self.addCleanup(trap.stop)
        self.temp = tempfile.TemporaryDirectory(prefix='synthetic_review_', dir=HERE)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_gpu_exact_identities_and_commands(self):
        packet, campaign = gpu_fixture()
        self.assertEqual({k: v['passed'] for k, v in r.check_gpu_gates(packet, MANIFEST, campaign).items()},
                         {'native': 4, 'policy': 27, 'contrast_pipeline': 1})
        self.assertEqual(r.gpu_cases()['contrast_pipeline'], [('tests.test_contrast_v6_train_gpu',
            'test_full_matched_cuda_training_exit_and_native_evaluation')])
        commands = r.gpu_commands(MANIFEST)
        self.assertEqual(commands['native'][5], 'tests/test_execution_contract.py')
        self.assertEqual(commands['policy'][5:8], ['tests/test_policy_gpu.py', 'tests/test_policy_v3_gpu.py', 'tests/test_loss_v3_gpu.py'])

    def test_gpu_wrong_xml_identity_count_and_status_rejected(self):
        for mutation in ('name', 'class', 'duplicate', 'count', 'negative', 'failure_total', 'error_total', 'skip_total', 'failure', 'error', 'skipped'):
            with self.subTest(mutation=mutation):
                packet, campaign = gpu_fixture()
                name = 'cloud_job/gpu_policy_tests.xml'
                tree = ET.fromstring(packet.raw(name))
                cases, suite = list(tree.iter('testcase')), next(tree.iter('testsuite'))
                if mutation == 'name': cases[0].set('name', 'unrelated_test')
                elif mutation == 'class': cases[0].set('classname', 'wrong_module')
                elif mutation == 'duplicate': cases[0].attrib.update(cases[1].attrib)
                elif mutation == 'count': suite.set('tests', '26')
                elif mutation == 'negative': suite.set('failures', '-1')
                elif mutation.endswith('_total'):
                    suite.set({'failure_total': 'failures', 'error_total': 'errors', 'skip_total': 'skipped'}[mutation], '1')
                else: ET.SubElement(cases[0], mutation)
                packet.put(name, ET.tostring(tree))
                with self.assertRaises(ValueError): r.check_gpu_gates(packet, MANIFEST, campaign)

    def test_gpu_wrong_commands_and_receipts_rejected(self):
        for mutation in ('native_command', 'policy_command', 'pipeline_command', 'native_receipt', 'policy_receipt', 'pipeline_receipt', 'boolean_count', 'boolean_zero', 'log'):
            with self.subTest(mutation=mutation):
                packet, campaign = gpu_fixture()
                if mutation.endswith('_command'):
                    family = mutation.removesuffix('_command')
                    if family == 'pipeline':
                        name = r.BASE+'processes/gpu_gate/process_receipt.json'
                        record = packet.json(name)
                        record['command'] = ['unregistered']
                        packet.put(name, record)
                    else:
                        packet.put('cloud_job/gpu_'+('contract' if family == 'native' else 'policy')+'_command.json', ['unregistered'])
                elif mutation == 'pipeline_receipt': campaign['gpu_gate']['passed'] = 0
                elif mutation == 'boolean_count': campaign['gpu_gate']['passed'] = True
                elif mutation == 'boolean_zero':
                    name = 'cloud_job/gpu_contract_receipt.json'
                    record = packet.json(name)
                    record['failures'] = False
                    packet.put(name, record)
                elif mutation == 'log': packet.inventory.pop('cloud_job/gpu_contract_tests.log')
                else:
                    label = 'contract' if mutation == 'native_receipt' else 'policy'
                    packet.put('cloud_job/gpu_'+label+'_receipt.json', {'passed': 0})
                with self.assertRaises(ValueError): r.check_gpu_gates(packet, MANIFEST, campaign)

    def test_saved_dataset_and_native_attribution_pass(self):
        arguments = native_fixture(self.root)
        m, tasks, publics = r.check_dataset(self.root, pin=arguments['gate']['manifest_sha256'],
                                          seed=926603, config=CFG, excluded=frozenset())
        self.assertEqual((m, tasks, publics), (arguments['manifest'], arguments['tasks'], arguments['publics']))
        result = r.check_native_bindings(self.root, **arguments)
        self.assertEqual((result['cases_bound'], result['arm_choices_bound']), (9, 45))
        self.assertIs(result['stored_trace_semantics_checked'], False)

    def test_changed_dataset_bytes_rejected(self):
        arguments = native_fixture(self.root)
        for name in ('train.json', 'validation.json', 'test_public.json', 'test_private.json'):
            with self.subTest(name=name):
                path = self.root/'dataset'/name
                before = path.read_bytes()
                path.write_bytes(before+b' ')
                try:
                    with self.assertRaisesRegex(ValueError, 'REVIEW_DATASET_BYTES_MISMATCH'):
                        r.check_dataset(self.root, pin=arguments['gate']['manifest_sha256'],
                                        seed=926603, config=CFG, excluded=frozenset())
                finally: path.write_bytes(before)

    def test_cold_dataset_report_must_match_saved_construction(self):
        arguments = native_fixture(self.root)
        path = self.root/'native/cold_dataset_validation.json'
        report = checks.read(path)
        report['native_outcomes_checked'] = True
        put(path, report)
        with self.assertRaisesRegex(ValueError, 'RECORDED_COLD_DATASET_MISMATCH'):
            r.check_dataset(self.root, pin=arguments['gate']['manifest_sha256'], seed=926603,
                            config=CFG, excluded=frozenset())

    def test_native_binding_mutations_rejected(self):
        arguments = native_fixture(self.root)
        native = self.root/'native'
        edits = [
            ('seal_digest', 'predictions_seal.json', lambda x: x.update(sha256='0'*64)),
            ('seal_parent', 'predictions_seal.json', lambda x: x.update(parent_gate_sha256='0'*64)),
            ('opening_hash', 'private_opening_receipt.json', lambda x: x.update(private_sha256='0'*64)),
            ('opening_time', 'private_opening_receipt.json', lambda x: x.update(opened_utc='2020-01-01T00:00:01+00:00')),
            ('parent_gate', 'training_parent_gate.json', lambda x: x.update(completed=False)),
            ('case_copy', 'evaluation/case_0000/case_receipt.json', lambda x: x.update(task_id='different')),
            ('reference_action', 'evaluation/case_0000/reference_result.json', lambda x: x.update(selected_action=None)),
            ('reference_public', 'evaluation/case_0000/reference_result.json', lambda x: x.update(public_digest='0'*64)),
            ('reference_verdict', 'evaluation/case_0000/reference_verdict.json', lambda x: x.update(task_correct=False)),
            ('arm_action', 'evaluation/case_0000/cas_trained/case_receipt.json', lambda x: x.update(action={})),
            ('arm_verdict', 'evaluation/case_0000/cas_trained/verification.json', lambda x: x.update(task_correct=True)),
            ('rejected_action', 'evaluation/case_0000/cas_trained/execution_result.json', lambda x: x.update(action={})),
            ('executed_action', 'evaluation/case_0000/rule/execution_result.json', lambda x: x.update(selected_action=None)),
            ('executed_public', 'evaluation/case_0000/rule/execution_result.json', lambda x: x.update(public_digest='0'*64)),
        ]
        for label, name, edit in edits:
            with self.subTest(mutation=label):
                path = native/name
                before = path.read_bytes()
                changed = d.decode(before)
                edit(changed)
                put(path, changed)
                try:
                    with self.assertRaises(ValueError): r.check_native_bindings(self.root, **arguments)
                finally: path.write_bytes(before)

    def test_native_neural_choices_preserved_even_if_native_seal_is_consistent(self):
        arguments = native_fixture(self.root)
        native = self.root/'native'
        rows = [d.decode(line) for line in (native/'predictions.jsonl').read_bytes().splitlines()]
        rows[0]['actions']['cas_trained'] = arguments['tasks'][0]['target']
        raw = b''.join(c.canonical(row)+b'\n' for row in rows)
        (native/'predictions.jsonl').write_bytes(raw)
        seal = checks.read(native/'predictions_seal.json')
        seal['sha256'] = sha256(raw).hexdigest()
        put(native/'predictions_seal.json', seal)
        put(native/'native_receipt.json', {'seal': seal})
        opening = checks.read(native/'private_opening_receipt.json')
        opening['prediction_sha256'] = seal['sha256']
        put(native/'private_opening_receipt.json', opening)
        with self.assertRaisesRegex(ValueError, 'NATIVE_NEURAL_ACTION_MAPPING'):
            r.check_native_bindings(self.root, **arguments)

    def test_failed_native_process_and_wrong_command_rejected(self):
        arguments = native_fixture(self.root)
        path = self.root/'processes/evaluate/process_receipt.json'
        before = path.read_bytes()
        for field, value in (('returncode', 1), ('command', ['wrong']), ('timed_out', True)):
            with self.subTest(field=field):
                record = d.decode(before)
                record[field] = value
                put(path, record)
                with self.assertRaisesRegex(ValueError, 'SUCCESSFUL_TRAINING_PROCESS_EXIT_REQUIRED'):
                    r.check_native_bindings(self.root, **arguments)
        path.write_bytes(before)

    def test_import_guard_and_no_current_result_read(self):
        for name in ('torch', 'casformer', 'cas_cjt', 'boto3', 'botocore', 'jax', 'tensorflow'):
            with self.subTest(module=name):
                self.assertNotIn(name, sys.modules)
                with self.assertRaisesRegex(ValueError, 'LOCAL_NEURAL_OR_PROVIDER_IMPORT_REFUSED'):
                    r.Guard().find_spec(name)
        with self.assertRaisesRegex(AssertionError, 'CURRENT_CAMPAIGN_RESULT_READ_FORBIDDEN'):
            r.PACKET.open('rb')


if __name__ == '__main__':
    unittest.main(verbosity=2)
