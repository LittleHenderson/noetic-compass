"""Synthetic semantic tests; Packet authentication and training replay are mocked.

No real packet, fixture graphs, CUDA, model, checkpoint deserialization or provider
is used. Real pure process/baseline/environment and aggregate helpers are used.
"""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
import importlib.abc
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FORBIDDEN = {'torch', 'casformer', 'cas_cjt', 'tensorflow', 'jax', 'cupy', 'boto3', 'botocore'}


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in FORBIDDEN:
            raise AssertionError('TEST_MODEL_PROVIDER_IMPORT:' + fullname)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def pure_scope():
    hooks, paths = list(sys.meta_path), list(sys.path)
    sys.meta_path.insert(0, Guard())
    sys.path.insert(0, str(ROOT))
    try:
        yield
    finally:
        sys.meta_path[:], sys.path[:] = hooks, paths


def require(value, reason):
    if not value:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return sha256(canonical(value)).hexdigest()


class Packet:
    """In-memory authenticated-Packet stand-in, not a cryptographic ZIP test."""
    def __init__(self):
        self.values, self.inventory, self.touched = {}, {}, []

    def put(self, name, value, pin=None):
        raw = value if type(value) is bytes else canonical(value) + b'\n'
        self.values[name] = raw
        self.inventory[name] = {'bytes': len(raw), 'sha256': pin or sha256(raw).hexdigest()}
        return self.inventory[name]['sha256']

    def json(self, name):
        return json.loads(self.values[name])

    def raw(self, name, limit=64*1024**2):
        assert len(self.values[name]) <= limit
        return self.values[name]

    def path(self, name):
        assert name in self.inventory
        self.touched.append(name)
        return Path('/authenticated') / name

    def same_hash(self, name, expected):
        require(self.inventory[name]['sha256'] == expected, 'TEST_PACKET_HASH:' + name)

    def update(self, name, change):
        value = self.json(name)
        change(value)
        self.put(name, value)


class Fixture:
    def __init__(self, subject, q, native, ev):
        self.subject, self.q, self.native, self.ev = subject, q, native, ev
        self.packet = p = Packet()
        self.job, self.source = 'cas-meta2-20000101000000-1234abcd', {'synthetic.py': 'a'*64}
        self.base = 'cloud_job/campaign/'
        self.smoke = self.base + 'gpu_tmp/test_saved_fixture_exact_app0/v7_smoke/'
        self.nb = self.smoke + 'native_evaluation/'
        self.prefix = '/opt/cas-meta2/package/research/CAS_META_2_COMPOSITION/runs/'
        self.python = '/opt/cas-meta2/venv/bin/python'
        self.baseline = {'source': {'baseline_sha': '0917267b1354e5d036263eaa6ba9a7197eafb776', 'files_verified': 316},
                         'installed_wheels': {'synthetic': {'sha256': 'b'*64, 'path': '/remote/wheel'}}}
        self.environment = {'torch': '2.11.0+cu128', 'cuda_runtime': '12.8', 'cuda_device_name': 'NVIDIA A10G',
            'deterministic_algorithms': True, 'tf32_matmul': False, 'tf32_cudnn': False, 'torch_cpu_threads': 1}
        self.c = SimpleNamespace(BASE=self.base, PILOT='research/CAS_META_2_COMPOSITION', ROOT=ROOT,
            BASELINE=self.baseline['source']['baseline_sha'], RUNTIME=native.RECOVERY_MANIFEST_SHA256,
            require=require, canonical=canonical, digest=digest, decode=json.loads,
            safe_name=lambda name: require(name and '..' not in name.split('/') and '\\' not in name
                and ':' not in name and not name.startswith('/'), 'TEST_UNSAFE_PATH') or name,
            remote_member=lambda name: name.removeprefix(self.prefix))
        self.spec = {'source_pins_sha256': q.PINS_SHA256, 'public_loader_sha256': q.LOADER_SHA256}
        self.calls = []
        self.fixture = {'seed': q.SEED, 'fixture_files_sha256': q.FIXTURE_PINS,
            'source_pins_sha256': q.PINS_SHA256, 'public_loader_sha256': q.LOADER_SHA256}
        p.put(self.base + 'initial_identity.json', {'source_sha256': self.source, 'baseline': self.baseline})
        p.put('cloud_job/runtime.json', {'cuda_matmul_passed': True, 'torch': '2.11.0+cu128',
                                        'cuda': '12.8', 'gpu': 'NVIDIA A10G'})
        command = [self.python, '-B', '-m', 'pytest', '-q', '-m', 'gpu', '-p', 'cas_meta2.pytest_no_aliases_v4',
            '-p', 'no:cacheprovider', 'tests/test_contrast_v7_train_gpu.py', '--basetemp',
            self.prefix + self.base + 'gpu_tmp', '--junitxml', self.prefix + self.base + 'gpu_test.xml']
        self.proc(self.base + 'processes/gpu_gate/', command, 10, 0, 120)
        self.xml = ('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0">'
            '<testcase name="'+q.GPU_TEST+'" classname="tests.test_contrast_v7_train_gpu"/>'
            '</testsuite></testsuites>').encode()
        p.put(self.base + 'gpu_test.xml', self.xml)
        self.commands = {}
        for phase, directory, pid, start, end in (('prepare', 'prepare_process', 11, 10, 20),
                ('train', 'training_process', 12, 30, 50), ('native', 'native_process', 13, 60, 100)):
            cmd = [self.python, '-B', '-m', 'cas_meta2.contrast_v7.gpu_preflight', '--phase', phase,
                   '--output', self.prefix + self.smoke.rstrip('/'), '--job', self.job]
            self.commands[phase] = cmd
            self.proc(self.smoke + directory + '/', cmd, pid, start, end)
        self.public = [{'synthetic_index': i} for i in range(9)]
        self.tasks = [{'task_id': f'synthetic-{i}', 'public': public,
            'provenance': {'depth': 4 if i % 3 == 2 else 3},
            'contrast_side': ('same_depth', 'wording_shift', 'deeper_calls')[i % 3]}
            for i, public in enumerate(self.public)]
        files = {'base_manifest.json': {'synthetic': 'base'}, 'base_train.json': [], 'train.json': [],
            'validation.json': [], 'test_public.json': self.public, 'test_private.json': self.tasks,
            'tokenizer.json': {'synthetic': True}, 'training_imports.json': {'synthetic': True}}
        hashes = {}
        for name, value in files.items():
            hashes[name] = p.put(self.smoke + 'dataset/' + name, value)
        self.manifest = {'splits': q.EXPECTED_SPLITS, 'sha256': hashes}
        p.put(self.smoke + 'dataset/manifest.json', self.manifest, subject.MANIFEST)
        for name, pin in q.FIXTURE_PINS.items():
            p.put(self.smoke + 'base_dataset/' + name, b'synthetic pinned base bytes', pin)
        for name in q.PUBLIC_FILES:
            src = self.smoke + 'dataset/' + name
            p.put(self.smoke + 'trainer_input/' + name, p.values[src], p.inventory[src]['sha256'])
        self.cold = {'completed': True, 'prototype_tasks': 256, 'prototype_pairs': 128,
            'tokenizer_fit_examples': 352, 'splits': q.EXPECTED_SPLITS, 'manifest_sha256': subject.MANIFEST}
        self.export = {'parent_validation': self.cold, 'splits': q.EXPECTED_SPLITS,
            'base_train_examples': 96, 'imported_train_examples': 256,
            'private_labels_read_by_loader': False, 'test_programs_parsed_by_loader': False}
        assembly = {'schema': q.SCHEMA, 'phase': 'prepare', 'completed': True, 'job': self.job, 'pid': 11,
            'source_sha256': self.source, 'manifest_sha256': subject.MANIFEST, 'fixture': self.fixture,
            'splits': q.EXPECTED_SPLITS, 'parent_validation': self.cold, 'public_export': self.export,
            'public_export_files_sha256': {name: p.inventory[self.smoke+'trainer_input/'+name]['sha256'] for name in q.PUBLIC_FILES},
            'neural_execution': False, 'task_generation': False, 'native_evaluation_completed': False,
            'parent_process_must_exit_before_training': True}
        p.put(self.smoke + 'assembly_receipt.json', assembly)
        neural = [{'case_index': i, 'public_sha256': digest(public),
                   'actions': {arm: {'status': 'REJECTED'} for arm in subject.ARMS if arm != 'rule'}}
                  for i, public in enumerate(self.public)]
        self.neural = neural
        self.neural_sha = p.put(self.smoke + 'training/neural_predictions.jsonl',
                               b''.join(canonical(row)+b'\n' for row in neural))
        self.gate = {'completed': True, 'private_test_labels_opened': False,
            'process_receipt_sha256': p.inventory[self.smoke+'training_process/process_receipt.json']['sha256'],
            'predictions_sha256': self.neural_sha}
        checkpoints = {}
        for family in ('cas', 'generic'):
            checkpoints[family] = {}
            for kind, epoch in (('initial', 0), ('selected', 1), ('final', 1)):
                name = f'{family}_{kind}_epoch_{epoch:04d}.pt'
                raw = ('synthetic checkpoint bytes only:' + name).encode()
                pin = p.put(self.smoke+'training/'+name, raw)
                checkpoints[family][kind] = {'path': name, 'family': family, 'epoch': epoch,
                    'optimizer_steps': epoch*22, 'sha256': pin, 'bytes': len(raw)}
        self.training = {'completed_epochs': 1, 'learning_accepted': False,
            'optimizer_steps': {'cas': 22, 'generic': 22}, 'checkpoints': checkpoints,
            'seal': {'test_examples': 9, 'prediction_count': 36, 'private_labels_read': False}}
        p.put(self.smoke + 'training/training_receipt.json', self.training)
        p.put(self.smoke + 'training/registration.json', {'baseline': self.baseline, 'environment': self.environment})
        self.changed = {family: {'changed_state_tensors': ['synthetic.weight'], 'changed_count': 1,
                                'all_loaded_on_cuda': True} for family in ('cas', 'generic')}
        checkpoint = {'schema': q.SCHEMA, 'completed': True, 'job': self.job, 'source_sha256': self.source,
            'baseline': self.baseline, 'manifest_sha256': subject.MANIFEST,
            'training_process_receipt_sha256': p.inventory[self.smoke+'training_process/process_receipt.json']['sha256'],
            'training_receipt_sha256': p.inventory[self.smoke+'training/training_receipt.json']['sha256'],
            'changed_weights': self.changed}
        p.put(self.smoke + 'checkpoint_verification.json', checkpoint)
        preds = [{**row, 'actions': {**row['actions'], 'rule': self.rule(public)}}
                 for row, public in zip(neural, self.public)]
        pred_sha = p.put(self.nb + 'predictions.jsonl', b''.join(canonical(row)+b'\n' for row in preds))
        self.seal = {'schema': 'cas-meta2-contrast-evaluation-seal/7', 'manifest_sha256': subject.MANIFEST,
            'test_examples': 9, 'prediction_count': 45, 'arms': list(subject.ARMS),
            'neural_predictions_sha256': self.neural_sha, 'parent_gate_sha256': digest(self.gate),
            'rule_input': 'public problem and permitted observations only', 'sha256': pred_sha,
            'sealed_utc': self.time(61)}
        p.put(self.nb + 'predictions_seal.json', self.seal)
        p.put(self.nb + 'training_parent_gate.json', self.gate)
        p.put(self.nb + 'private_opening_receipt.json', {'prediction_sha256': pred_sha,
            'training_exit_receipt_sha256': self.gate['process_receipt_sha256'],
            'private_sha256': hashes['test_private.json'], 'opened_utc': self.time(62)})
        request = {'job': self.job, 'private_data': self.prefix+self.smoke+'dataset',
            'expected_sha256': subject.MANIFEST, 'seed': q.SEED, 'config': q.CONFIG, 'excluded': [],
            'pins': '/opt/cas-meta2/package/'+self.c.PILOT+'/'+q.PINS_PATH,
            'expected_pins_sha256': q.PINS_SHA256, 'expected_loader_sha256': q.LOADER_SHA256,
            'source_sha256': self.source}
        pin = p.put(self.nb + 'cold_validation_request.json', request)
        cmd = [self.python, '-B', '-c', subject.COLD_CODE, self.prefix+self.nb+'cold_validation_request.json',
               pin, self.prefix+self.nb+'cold_dataset_validation.json', self.job]
        self.proc(self.nb+'cold_validation_process/', cmd, 14, 70, 80)
        p.put(self.nb+'cold_dataset_validation.json', self.cold)
        cases = []
        helper_identity = native.recovery_identity()
        for i, (task, pred) in enumerate(zip(self.tasks, preds)):
            rows = {}
            for arm in subject.ARMS:
                success = arm == 'rule'
                rows[arm] = {'case_index': i, 'arm': arm, 'action': pred['actions'][arm],
                    'execution_status': 'EXECUTED' if success else 'REJECTED', 'model_rejection': not success,
                    'partial_work': None, 'verification': {field: success for field in
                        ('task_correct','procedure_correct','binding_correct','dependency_correct','actual_output_correct','trace_valid')}}
            cases.append({'case_index': i, 'task_id': task['task_id'], 'arms': rows,
                          'reference_verification': {'task_correct': True}})
            p.put(self.nb+f'evaluation/case_{i:04d}/worker_identity.json', {'pid': 20+i % 2,
                'environment': self.environment, 'source_sha256': self.source, 'baseline': self.baseline,
                'recovery_helpers_sha256': helper_identity})
        results, groups = native.aggregate_cases(cases, 9), native.grouped_results(cases, self.tasks)
        self.native_receipt = {'schema': 'cas-meta2-prototype-native-evaluation/7', 'completed': True,
            'cases': 9, 'reference_cases': 9, 'arm_verdicts': 45, 'workers': 8, 'results': results, 'groups': groups,
            'learning_accepted': False, 'seal': self.seal, 'recovery_helper_manifest_sha256': self.c.RUNTIME}
        p.put(self.nb+'evaluation_results.json', {'cases': cases, 'results': results, 'groups': groups})
        p.put(self.nb+'native_receipt.json', self.native_receipt)
        smoke = {'schema': q.SCHEMA, 'status': 'V7_KNOWN_FIXTURE_CUDA_FULL_PIPELINE_SMOKE_PASSED',
            'completed': True, 'job': self.job, 'neural_execution': True, 'native_evaluation_completed': True,
            'task_generation': False, 'learning_accepted': False, 'prepare_exit_before_training': True,
            'native_integration_status': 'COMPLETED_KNOWN_FIXTURE_ONLY', 'wall_seconds': 90,
            'source_sha256': self.source, 'baseline': self.baseline, 'splits': q.EXPECTED_SPLITS,
            'optimizer_steps': {'cas': 22, 'generic': 22}, 'fixture': self.fixture,
            'prepare_pid': 11, 'training_pid': 12, 'training_gate': self.gate, 'changed_weights': self.changed,
            'native_receipt': self.native_receipt}
        p.put(self.smoke+'gpu_smoke_receipt.json', smoke)
        self.sync()
        def check_training(output, process, bundle, **kwargs):
            self.calls.append('training_recount')
            assert output == p.path(self.smoke+'training/training_receipt.json').parent
            assert bundle == p.path(self.smoke+'trainer_input/manifest.json').parent
            assert kwargs['curriculum_seed'] == 926603 and kwargs['expected_manifest_sha256'] == subject.MANIFEST
            assert kwargs['expected_source'] == self.source and kwargs['expected_baseline'] == self.baseline
            assert kwargs['config'].epochs == 1 and kwargs['config'].max_seconds == 900
            return deepcopy(self.gate)
        def validate_bundle(path, **kwargs):
            self.calls.append('cold_recount')
            assert path == p.path(self.smoke+'dataset/manifest.json').parent
            assert kwargs['seed'] == 926603 and kwargs['excluded'] == frozenset()
            assert kwargs['expected_sha256'] == subject.MANIFEST
            return deepcopy(self.cold)
        self.modules = {'gpu_preflight': q, 'native': native,
            'checks': SimpleNamespace(check_training=check_training),
            'train': SimpleNamespace(TrainingConfig=lambda **kw: SimpleNamespace(**kw)),
            'curriculum': SimpleNamespace(Config=lambda **kw: SimpleNamespace(**kw),
                permitted_view=lambda task: task['public'], parse_problem=self.rule),
            'parent': SimpleNamespace(validate_bundle=validate_bundle)}

    @staticmethod
    def rule(public):
        return {'synthetic_rule': public['synthetic_index']}

    @staticmethod
    def time(seconds):
        return f'2000-01-01T00:{seconds//60:02d}:{seconds%60:02d}+00:00'

    def proc(self, directory, command, pid, start, end):
        row = {'schema': 'cas-meta2-campaign-subprocess/3', 'command': command, 'completed': True,
            'returncode': 0, 'timed_out': False, 'automatic_retry': False, 'new_process_group': True,
            'pid': pid, 'started_utc': self.time(start), 'finished_utc': self.time(end),
            'wall_seconds': end-start, 'cwd': '/opt/cas-meta2/package/research/CAS_META_2_COMPOSITION'}
        for stream in ('stdout', 'stderr'):
            row[stream] = self.prefix+directory+stream+'.txt'
            row[stream+'_sha256'] = self.packet.put(directory+stream+'.txt', b'synthetic process log\n')
        self.packet.put(directory+'process_receipt.json', row)

    def sync(self):
        p = self.packet
        def smoke(row):
            for field, name in (('assembly_receipt_sha256', 'assembly_receipt.json'),
                ('prepare_process_receipt_sha256', 'prepare_process/process_receipt.json'),
                ('training_process_receipt_sha256', 'training_process/process_receipt.json'),
                ('native_process_receipt_sha256', 'native_process/process_receipt.json'),
                ('native_receipt_sha256', 'native_evaluation/native_receipt.json')):
                row[field] = p.inventory[self.smoke+name]['sha256']
        p.update(self.smoke+'gpu_smoke_receipt.json', smoke)

    def run(self):
        return self.subject.audit_smoke(self.packet, job=self.job, source=self.source, baseline=self.baseline,
            spec=self.spec, modules=self.modules, c=self.c, evidence=self.ev)


class SmokeEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with pure_scope():
            cls.subject = load(HERE/'gpu.py', 'independent_gpu_review_test_subject')
            cls.ev = load(ROOT/'records/contrast_recovery_v6_review_001/evidence.py', 'frozen_pure_evidence_for_smoke_test')
            from cas_meta2.contrast_v7 import gpu_preflight, native_evaluation
            cls.q, cls.native = gpu_preflight, native_evaluation

    def setUp(self):
        self.scope = pure_scope()
        self.scope.__enter__()
        self.addCleanup(lambda: self.scope.__exit__(None, None, None))
        self.f = Fixture(self.subject, self.q, self.native, self.ev)

    def rejected(self, mutator, pattern):
        mutator(self.f)
        self.f.sync()
        with self.assertRaisesRegex((ValueError, AssertionError), pattern):
            self.f.run()

    def test_complete_synthetic_smoke_and_explicit_boundaries(self):
        result = self.f.run()
        self.assertTrue(result['completed'])
        self.assertEqual((result['tests'], result['native_cases'], result['native_arm_verdicts']), (1,9,45))
        self.assertEqual(len(result['checkpoint_byte_hashes']), 6)
        self.assertEqual(self.f.calls, ['training_recount', 'cold_recount'])
        self.assertFalse(result['tensor_state_independently_replayed'])
        self.assertFalse(result['native_verifier_or_sqlite_independently_replayed'])
        self.assertFalse(result['fresh_evaluation'])
        self.assertFalse(FORBIDDEN.intersection(name.split('.')[0] for name in sys.modules))

    def test_wrong_gpu_command_rejected(self):
        self.rejected(lambda f: f.packet.update(f.base+'processes/gpu_gate/process_receipt.json',
            lambda r: r['command'].append('--wrong')), 'SMOKE_GPU_COMMAND')

    def test_xml_skip_rejected(self):
        self.rejected(lambda f: f.packet.put(f.base+'gpu_test.xml', f.xml.replace(b'/>', b'><skipped/></testcase>')),
                      'SMOKE_ONE_ACTUAL_GPU_TEST')

    def test_xml_entity_declaration_rejected(self):
        self.rejected(lambda f: f.packet.put(f.base+'gpu_test.xml', b'<!DOCTYPE x>'+f.xml), 'SMOKE_XML_DECLARATION')

    def test_duplicate_smoke_rejected(self):
        self.rejected(lambda f: f.packet.put(f.base+'gpu_tmp/second/gpu_smoke_receipt.json', {}), 'SMOKE_ONE_CURRENT_RECEIPT')

    def test_foreign_job_rejected(self):
        self.rejected(lambda f: f.packet.update(f.smoke+'gpu_smoke_receipt.json', lambda r: r.update(job='other')),
                      'SMOKE_COMPLETED_BOUNDARY')

    def test_changed_source_rejected(self):
        self.rejected(lambda f: f.packet.update(f.smoke+'gpu_smoke_receipt.json', lambda r: r.update(source_sha256={})),
                      'SMOKE_SOURCE')

    def test_bad_native_process_exit_rejected(self):
        self.rejected(lambda f: f.packet.update(f.smoke+'native_process/process_receipt.json', lambda r: r.update(returncode=1)),
                      'EVIDENCE_PROCESS_FAILED_OR_CHANGED')

    def test_overlapping_prepare_and_train_rejected(self):
        self.rejected(lambda f: f.packet.update(f.smoke+'prepare_process/process_receipt.json',
            lambda r: r.update(finished_utc=f.time(35))), 'SMOKE_CHILD_EXIT_ORDER')

    def test_wrong_352_split_rejected(self):
        self.rejected(lambda f: f.packet.update(f.smoke+'assembly_receipt.json',
            lambda r: r['splits']['train'].update(tasks=351)), 'SMOKE_ASSEMBLY_SPLITS')

    def test_private_labels_in_public_export_rejected(self):
        self.rejected(lambda f: f.packet.put(f.smoke+'trainer_input/test_private.json', []), 'SMOKE_DIRECTORY_COVERAGE')

    def test_wrong_training_step_count_rejected(self):
        self.rejected(lambda f: f.packet.update(f.smoke+'training/training_receipt.json',
            lambda r: r['optimizer_steps'].update(cas=21)), 'SMOKE_TRAINING_STEPS')

    def test_checkpoint_substitution_rejected(self):
        self.rejected(lambda f: f.packet.put(f.smoke+'training/cas_initial_epoch_0000.pt', b'substitute'), 'TEST_PACKET_HASH')

    def test_unaccounted_checkpoint_rejected(self):
        self.rejected(lambda f: f.packet.put(f.smoke+'training/extra.pt', b'unaccounted'), 'SMOKE_EXTRA_CHECKPOINT')

    def test_changed_weight_attestation_hash_binding(self):
        self.rejected(lambda f: f.packet.update(f.smoke+'checkpoint_verification.json',
            lambda r: r.update(training_receipt_sha256='0'*64)), 'TEST_PACKET_HASH')

    def test_zero_tensor_change_rejected(self):
        def change(f):
            for name in ('checkpoint_verification.json', 'gpu_smoke_receipt.json'):
                f.packet.update(f.smoke+name, lambda r: r['changed_weights']['cas'].update(changed_count=0))
        self.rejected(change, 'SMOKE_CHANGED_TENSOR_RECORD')

    def test_duplicate_changed_tensor_names_rejected(self):
        def change(f):
            for name in ('checkpoint_verification.json', 'gpu_smoke_receipt.json'):
                f.packet.update(f.smoke+name, lambda r: r['changed_weights']['cas'].update(
                    changed_state_tensors=['x','x'], changed_count=2))
        self.rejected(change, 'SMOKE_CHANGED_TENSOR_RECORD')

    def test_embedded_native_does_not_replace_stored_native(self):
        self.rejected(lambda f: f.packet.update(f.nb+'native_receipt.json', lambda r: r.update(cases=8)),
                      'SMOKE_EMBEDDED_NATIVE_CHANGED')

    def test_private_opening_before_seal_rejected(self):
        self.rejected(lambda f: f.packet.update(f.nb+'private_opening_receipt.json',
            lambda r: r.update(opened_utc=f.time(60))), 'SMOKE_PRIVATE_OPENING_ORDER')

    def test_cold_source_request_rejected(self):
        self.rejected(lambda f: f.packet.update(f.nb+'cold_validation_request.json',
            lambda r: r.update(source_sha256={})), 'SMOKE_COLD_REQUEST')

    def test_cold_same_pid_rejected(self):
        self.rejected(lambda f: f.packet.update(f.nb+'cold_validation_process/process_receipt.json',
            lambda r: r.update(pid=13)), 'SMOKE_COLD_EXIT_ORDER')

    def test_cold_report_mismatch_rejected(self):
        self.rejected(lambda f: f.packet.update(f.nb+'cold_dataset_validation.json',
            lambda r: r.update(prototype_tasks=255)), 'SMOKE_COLD_RECOUNT')

    def test_missing_native_case_rejected(self):
        self.rejected(lambda f: f.packet.update(f.nb+'evaluation_results.json', lambda r: r['cases'].pop()),
                      'SMOKE_STORED_CASE_COUNT')

    def test_wrong_native_case_action_rejected(self):
        self.rejected(lambda f: f.packet.update(f.nb+'evaluation_results.json',
            lambda r: r['cases'][0]['arms']['rule'].update(action={'changed': True})), 'SMOKE_NATIVE_ACTION_CHANGED')

    def test_missing_successful_reference_rejected(self):
        self.rejected(lambda f: f.packet.update(f.nb+'evaluation_results.json',
            lambda r: r['cases'][0]['reference_verification'].update(task_correct=False)), 'SMOKE_REFERENCE_VERIFICATION')

    def test_worker_source_changed_rejected(self):
        self.rejected(lambda f: f.packet.update(f.nb+'evaluation/case_0000/worker_identity.json',
            lambda r: r.update(source_sha256={})), 'SMOKE_WORKER_SOURCE')

    def test_worker_pool_cannot_claim_nine_processes(self):
        def change(f):
            for i in range(9):
                f.packet.update(f.nb+f'evaluation/case_{i:04d}/worker_identity.json',
                                lambda row, i=i: row.update(pid=20+i))
        self.rejected(change, 'SMOKE_WORKER_POOL_BOUND')

    def test_native_parent_cannot_be_its_worker(self):
        self.rejected(lambda f: f.packet.update(f.nb+'evaluation/case_0000/worker_identity.json',
            lambda row: row.update(pid=13)), 'SMOKE_WORKER_PID')

    def test_native_group_denominator_recount(self):
        self.rejected(lambda f: f.packet.update(f.nb+'evaluation_results.json',
            lambda r: r['groups']['depth_3']['rule'].update(total=5)), 'SMOKE_GROUP_RECOUNT')


if __name__ == '__main__':
    unittest.main(verbosity=2)
