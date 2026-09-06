"""Pure synthetic metadata/CLI tests, not a stored-packet authentication audit.

The in-memory Packet represents already authenticated bytes. Collection-index
authentication and the old four-test GPU gate are explicitly stubbed; tests
verify their exact inputs, result handling and exception propagation. No actual
packet, dataset, model, checkpoint, provider or Git history is opened here.
CLI runs are mocked after argument/output validation and write only temporary
test receipts below this records directory.
"""
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from copy import deepcopy
from hashlib import sha256
import importlib.abc
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
FORBIDDEN = {'torch', 'casformer', 'cas_cjt', 'cas_meta', 'tensorflow', 'jax', 'cupy', 'boto3', 'botocore'}


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in FORBIDDEN:
            raise AssertionError('TEST_MODEL_PROVIDER_IMPORT:' + fullname)


@contextmanager
def pure_scope():
    hooks, paths = list(sys.meta_path), list(sys.path)
    sys.meta_path.insert(0, Guard())
    try:
        yield
    finally:
        sys.meta_path[:], sys.path[:] = hooks, paths


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class FakePacket:
    """An authenticated-byte stand-in; does not claim ZIP authentication."""
    def __init__(self, c):
        self.c, self.values, self.inventory, self.hash_checks = c, {}, {}, []

    def put(self, name, value):
        raw = value if type(value) is bytes else self.c.canonical(value) + b'\n'
        self.values[name] = raw
        self.inventory[name] = {'path': name, 'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}
        return self.inventory[name]['sha256']

    def json(self, name):
        return self.c.decode(self.values[name])

    def same_hash(self, name, pin):
        self.hash_checks.append((name, pin))
        self.c.require(name in self.inventory and self.inventory[name]['sha256'] == pin,
                       'TEST_MEMBER_BINDING:' + name)

    def change(self, name, change):
        value = self.json(name)
        change(value)
        self.put(name, value)


class Fixture:
    def __init__(self, subject, c):
        self.subject, self.c, self.packet = subject, c, FakePacket(c)
        self.job = 'cas-meta2-20000101000000-1234abcd'
        self.source, self.archive_pin, self.launch_pin = 'a'*40, 'b'*64, 'c'*64
        self.manifest = {'experiment': {'profile': 'prototype_v7', 'entrypoint': 'cas_meta2.contrast_v7',
            'spec_path': c.PILOT + '/EXPERIMENT_PROTOTYPE_V7.json', 'spec_sha256': 'd'*64}}
        self.collection = {'returncode': 0, 'partial_evidence': False, 'smoke_only': False,
                           'experiment': self.manifest['experiment']}
        self.index_verified, self.calls = True, []
        self.gate = {'passed': 4, 'tests': ['synthetic-contract-'+str(i) for i in range(4)]}
        self.helper = SimpleNamespace(_collection=self.collection_stub, _gpu_gate=self.gate_stub)
        self.smoke_name = 'gpu_tmp/synthetic/v7_smoke/gpu_smoke_receipt.json'
        self.required = {'campaign_receipt.json', 'payload_sha256.json', 'dataset_assembly_receipt.json',
            'training_gate.json', 'training/training_receipt.json', 'training/neural_predictions.jsonl',
            'training/neural_predictions_seal.json', 'native/native_receipt.json', 'native/evaluation_results.json'}
        p = self.packet
        p.put('cloud_job/job.json', {'job': self.job, 'source_sha': self.source,
            'archive_sha256': self.archive_pin, 'baseline_sha': c.BASELINE, 'returncode': 0,
            'smoke_only': False, 'experiment': self.manifest['experiment']})
        self.command = ['/opt/cas-meta2/venv/bin/python', '-B',
            '/opt/cas-meta2/package/' + c.PILOT + '/aws/prototype_remote_v7.py', '--output',
            '/opt/cas-meta2/package/' + c.PILOT + '/runs/' + c.BASE.rstrip('/'),
            '--job', self.job, '--max-wall-seconds', '6900', '--launch-manifest',
            '/opt/cas-meta2/package/launch_manifest.json', '--launch-manifest-sha256', self.launch_pin]
        p.put('cloud_job/command.json', self.command)
        campaign = {'schema': 'cas-meta2-prototype-campaign/7', 'job': self.job,
            'experiment': self.manifest['experiment'], 'completed': True, 'training_performed': True,
            'training_attempted': True, 'native_evaluation_completed': True, 'learning_accepted': False,
            'release_accepted': False, 'automatic_retry': False, 'stage': 'completed',
            'processes': {name: {'synthetic_process': name} for name in ('gpu_gate', 'dataset', 'training', 'evaluate')}}
        p.put(c.BASE + 'campaign_receipt.json', campaign)
        p.put(c.BASE + 'campaign_status.json', {'job': self.job, 'stage': 'completed', 'completed': True})
        for name in self.required - {'campaign_receipt.json', 'payload_sha256.json'}:
            p.put(c.BASE + name, {'synthetic_member_only': name})
        p.put(c.BASE + self.smoke_name, {'synthetic_member_only': 'smoke'})
        p.put(c.BASE + 'extra/raw.log', b'full payload index must also cover this raw log\n')
        self.coordinator = {'schema': 'cas-meta2-prototype-coordinator/7', 'completed': True, 'job': self.job,
            'experiment': self.manifest['experiment'], 'learning_accepted': False,
            'source_and_inputs_rechecked': True, 'source_sha': self.source,
            'launch_manifest_sha256': self.launch_pin, 'evidence': {'train_examples': 896,
            'validation_examples': 96, 'test_variants': 72, 'matched_test_triplets': 24,
            'optimizer_steps_per_family': 11200, 'native_arm_verdicts': 360,
            'known_fixture_smoke_reference_cases': 9, 'known_fixture_smoke_arm_verdicts': 45}}
        self.contract = ['/opt/cas-meta2/venv/bin/python', '-m', 'pytest', '-m', 'gpu',
            'tests/test_execution_contract.py', '-q', '--junitxml',
            '/opt/cas-meta2/package/' + c.PILOT + '/runs/cloud_job/gpu_contract_tests.xml', '-p', 'no:cacheprovider']
        p.put('cloud_job/gpu_contract_command.json', self.contract)
        p.put('cloud_job/runtime.json', {'synthetic_environment_only': True})
        self.reseal_documentary_records()

    def collection_stub(self, packet, job, source, archive_pin):
        # Actual collection authentication is independently tested elsewhere.
        self.calls.append(('collection', packet, job, source, archive_pin))
        return deepcopy(self.collection), self.index_verified

    def gate_stub(self, packet, family):
        # No GPU gate or test execution occurs in this synthetic test.
        self.calls.append(('contract', packet, family))
        return deepcopy(self.gate)

    def reseal_documentary_records(self):
        p, base = self.packet, self.c.BASE
        p.put(base + 'payload_sha256.json', {name.removeprefix(base): row['sha256']
            for name, row in p.inventory.items() if name.startswith(base) and name != base + 'payload_sha256.json'})
        self.coordinator['evidence']['files_sha256'] = {
            name: p.inventory[base + name]['sha256'] for name in self.required | {self.smoke_name}}
        p.put('cloud_job/prototype_coordinator_receipt.json', self.coordinator)

    def check(self):
        return self.subject.metadata(self.packet, self.manifest, self.source, self.archive_pin,
                                     self.launch_pin, self.job, self.helper, self.c)


class GuardedTestCase(unittest.TestCase):
    def setUp(self):
        scope = pure_scope()
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        self.subject = load(HERE / 'review.py', '_synthetic_v7_review_' + self._testMethodName)
        self.c = load(HERE / 'common.py', '_synthetic_v7_common_' + self._testMethodName)


class MetadataTests(GuardedTestCase):
    def fixture(self):
        return Fixture(self.subject, self.c)

    def test_positive_metadata_preserves_bound_records_and_exact_helper_inputs(self):
        f = self.fixture()
        result = f.check()
        self.assertEqual(set(result), {'collection', 'campaign', 'coordinator', 'contract_gpu_gate', 'runtime'})
        self.assertEqual(result['contract_gpu_gate'], f.gate)
        self.assertEqual(f.calls, [('collection', f.packet, f.job, f.source, f.archive_pin),
                                  ('contract', f.packet, 'contract')])
        self.assertEqual({name for name, _ in f.packet.hash_checks},
                         {self.c.BASE + name for name in f.required | {f.smoke_name}})
        self.assertEqual(result['coordinator']['evidence']['test_variants'], 72)
        self.assertEqual(result['coordinator']['evidence']['native_arm_verdicts'], 360)
        self.assertEqual(result['coordinator']['evidence']['known_fixture_smoke_arm_verdicts'], 45)

    def test_invalid_external_job_rejected_before_collection(self):
        for job in ('', 'cas-meta2-20000101000000-1234abcg', 'cas-meta2-20000101000000-1234abcd/extra', None, 7):
            with self.subTest(job=job):
                f = self.fixture(); f.job = job
                with self.assertRaisesRegex(ValueError, 'V7_EXTERNAL_JOB_REQUIRED'):
                    f.check()
                self.assertEqual(f.calls, [])

    def test_unverified_full_collection_index_rejected(self):
        for value in (False, None, 1):
            with self.subTest(index=value):
                f = self.fixture(); f.index_verified = value
                with self.assertRaisesRegex(ValueError, 'V7_COMPLETE_COLLECTION_REQUIRED'):
                    f.check()

    def test_partial_failed_or_smoke_collection_rejected(self):
        for field, value in (('returncode', 1), ('partial_evidence', True), ('smoke_only', True),
                             ('experiment', {'wrong': True})):
            with self.subTest(field=field):
                f = self.fixture(); f.collection[field] = value
                with self.assertRaisesRegex(ValueError, 'V7_COMPLETE_COLLECTION_REQUIRED'):
                    f.check()

    def test_external_job_source_archive_and_baseline_must_match_remote(self):
        changes = {'job': 'cas-meta2-20000101000000-deadbeef', 'source_sha': 'e'*40,
            'archive_sha256': 'e'*64, 'baseline_sha': 'e'*40, 'returncode': 1,
            'smoke_only': True, 'experiment': {'wrong': True}}
        for field, value in changes.items():
            with self.subTest(field=field):
                f = self.fixture(); f.packet.change('cloud_job/job.json', lambda row: row.update({field: value}))
                with self.assertRaisesRegex(ValueError, 'V7_JOB_IDENTITY'):
                    f.check()

    def test_boolean_returncode_is_not_integer_exit(self):
        f = self.fixture(); f.packet.change('cloud_job/job.json', lambda row: row.update(returncode=False))
        with self.assertRaisesRegex(ValueError, 'V7_JOB_IDENTITY'):
            f.check()

    def test_coordinator_command_is_exact_including_manifest_pin(self):
        for index in (0, 2, 4, 6, 8, 10, 12):
            with self.subTest(argument=index):
                f = self.fixture(); command = list(f.command); command[index] += '_wrong'
                f.packet.put('cloud_job/command.json', command)
                with self.assertRaisesRegex(ValueError, 'V7_COORDINATOR_COMMAND'):
                    f.check()
        f = self.fixture(); f.packet.put('cloud_job/command.json', f.command + ['--extra'])
        with self.assertRaisesRegex(ValueError, 'V7_COORDINATOR_COMMAND'):
            f.check()

    def test_campaign_completion_flags_are_exact_booleans(self):
        for field in ('completed', 'training_performed', 'training_attempted', 'native_evaluation_completed',
                      'learning_accepted', 'release_accepted', 'automatic_retry'):
            for value in (None, 1, 'true'):
                with self.subTest(field=field, value=value):
                    f = self.fixture()
                    f.packet.change(self.c.BASE + 'campaign_receipt.json', lambda row: row.update({field: value}))
                    f.reseal_documentary_records()
                    with self.assertRaisesRegex(ValueError, 'V7_COMPLETE_CAMPAIGN_REQUIRED'):
                        f.check()

    def test_campaign_job_experiment_schema_stage_must_match(self):
        for field in ('job', 'experiment', 'schema', 'stage'):
            with self.subTest(field=field):
                f = self.fixture()
                f.packet.change(self.c.BASE + 'campaign_receipt.json', lambda row: row.update({field: 'wrong'}))
                f.reseal_documentary_records()
                with self.assertRaisesRegex(ValueError, 'V7_COMPLETE_CAMPAIGN_REQUIRED'):
                    f.check()

    def test_campaign_failure_or_finalization_error_never_complete(self):
        for field in ('failure', 'finalization_error'):
            with self.subTest(field=field):
                f = self.fixture()
                f.packet.change(self.c.BASE + 'campaign_receipt.json', lambda row: row.update({field: None}))
                f.reseal_documentary_records()
                with self.assertRaisesRegex(ValueError, 'V7_COMPLETE_CAMPAIGN_REQUIRED'):
                    f.check()

    def test_campaign_process_coverage_cannot_omit_or_add_phase(self):
        for change in (lambda row: row['processes'].pop('evaluate'),
                       lambda row: row['processes'].update(retry={'synthetic': True})):
            with self.subTest(change=change):
                f = self.fixture(); f.packet.change(self.c.BASE + 'campaign_receipt.json', change)
                f.reseal_documentary_records()
                with self.assertRaisesRegex(ValueError, 'V7_COMPLETE_CAMPAIGN_REQUIRED'):
                    f.check()

    def test_final_status_copy_cannot_disagree(self):
        f = self.fixture()
        f.packet.change(self.c.BASE + 'campaign_status.json', lambda row: row.update(stage='training'))
        f.reseal_documentary_records()
        with self.assertRaisesRegex(ValueError, 'V7_FINAL_STATUS_COPY'):
            f.check()

    def test_full_payload_index_rejects_missing_extra_and_wrong_hash(self):
        for change in (lambda row: row.pop('extra/raw.log'), lambda row: row.update(invented='e'*64),
                       lambda row: row.update({'extra/raw.log': 'e'*64})):
            with self.subTest(change=change):
                f = self.fixture(); f.packet.change(self.c.BASE + 'payload_sha256.json', change)
                with self.assertRaisesRegex(ValueError, 'V7_FULL_PAYLOAD_INDEX'):
                    f.check()

    def test_new_unindexed_campaign_member_is_not_silently_ignored(self):
        f = self.fixture(); f.packet.put(self.c.BASE + 'unexpected.log', b'new bytes')
        with self.assertRaisesRegex(ValueError, 'V7_FULL_PAYLOAD_INDEX'):
            f.check()

    def test_index_cannot_include_itself(self):
        f = self.fixture()
        f.packet.change(self.c.BASE + 'payload_sha256.json', lambda row: row.update({'payload_sha256.json': 'e'*64}))
        with self.assertRaisesRegex(ValueError, 'V7_FULL_PAYLOAD_INDEX'):
            f.check()

    def test_coordinator_identity_and_completion_must_match(self):
        changes = {'schema': 'wrong', 'completed': False, 'job': 'wrong', 'experiment': {'wrong': True},
            'learning_accepted': True, 'source_and_inputs_rechecked': False, 'source_sha': 'e'*40,
            'launch_manifest_sha256': 'e'*64, 'failure': None}
        for field, value in changes.items():
            with self.subTest(field=field):
                f = self.fixture(); f.coordinator[field] = value; f.reseal_documentary_records()
                with self.assertRaisesRegex(ValueError, 'V7_COMPLETE_COORDINATOR_REQUIRED'):
                    f.check()

    def test_coordinator_boolean_completion_does_not_accept_integer(self):
        f = self.fixture(); f.coordinator['completed'] = 1; f.reseal_documentary_records()
        with self.assertRaisesRegex(ValueError, 'V7_COMPLETE_COORDINATOR_REQUIRED'):
            f.check()

    def test_declared_main_and_smoke_counts_have_exact_separate_denominators(self):
        fields = ('train_examples', 'validation_examples', 'test_variants', 'matched_test_triplets',
            'optimizer_steps_per_family', 'native_arm_verdicts', 'known_fixture_smoke_reference_cases',
            'known_fixture_smoke_arm_verdicts')
        for field in fields:
            for value in (0, True, '72'):
                with self.subTest(field=field, value=value):
                    f = self.fixture(); f.coordinator['evidence'][field] = value; f.reseal_documentary_records()
                    with self.assertRaisesRegex(ValueError, 'V7_COORDINATOR_COUNTS'):
                        f.check()

    def test_coordinator_hash_coverage_is_exact(self):
        for change in (lambda row: row['evidence']['files_sha256'].pop('native/native_receipt.json'),
                       lambda row: row['evidence']['files_sha256'].update({'extra/raw.log': 'e'*64})):
            with self.subTest(change=change):
                f = self.fixture(); f.packet.change('cloud_job/prototype_coordinator_receipt.json', change)
                with self.assertRaisesRegex(ValueError, 'V7_COORDINATOR_HASH_COVERAGE'):
                    f.check()

    def test_coordinator_hashes_checked_against_each_member(self):
        f = self.fixture()
        f.packet.change('cloud_job/prototype_coordinator_receipt.json',
            lambda row: row['evidence']['files_sha256'].update({'native/native_receipt.json': 'e'*64}))
        with self.assertRaisesRegex(ValueError, 'TEST_MEMBER_BINDING:.*native/native_receipt'):
            f.check()

    def test_more_than_one_smoke_receipt_rejected(self):
        f = self.fixture(); f.packet.put(self.c.BASE + 'gpu_tmp/second/gpu_smoke_receipt.json', {})
        f.reseal_documentary_records()
        with self.assertRaisesRegex(ValueError, 'V7_COORDINATOR_HASH_COVERAGE'):
            f.check()

    def test_no_smoke_receipt_rejected(self):
        f = self.fixture(); name = self.c.BASE + f.smoke_name
        del f.packet.values[name]; del f.packet.inventory[name]
        f.packet.put(self.c.BASE + 'payload_sha256.json', {key.removeprefix(self.c.BASE): row['sha256']
            for key, row in f.packet.inventory.items() if key.startswith(self.c.BASE)
            and key != self.c.BASE + 'payload_sha256.json'})
        with self.assertRaisesRegex(ValueError, 'V7_COORDINATOR_HASH_COVERAGE'):
            f.check()

    def test_old_four_gpu_contract_gate_gets_exact_command(self):
        for index in (0, 5, 8, 10):
            with self.subTest(argument=index):
                f = self.fixture(); command = list(f.contract); command[index] += '_wrong'
                f.packet.put('cloud_job/gpu_contract_command.json', command)
                with self.assertRaisesRegex(ValueError, 'V7_EXACT_CONTRACT_GPU_COMMAND'):
                    f.check()
                self.assertEqual(f.calls[-1], ('contract', f.packet, 'contract'))

    def test_collection_and_old_gate_failures_are_fatal(self):
        def reject(*args):
            raise RuntimeError('synthetic independent helper rejection')
        for name in ('_collection', '_gpu_gate'):
            with self.subTest(helper=name):
                f = self.fixture(); setattr(f.helper, name, reject)
                with self.assertRaisesRegex(RuntimeError, 'independent helper rejection'):
                    f.check()


class CLITests(GuardedTestCase):
    def setUp(self):
        super().setUp()
        self.temporary = tempfile.TemporaryDirectory(prefix='_synthetic_review_cli_', dir=HERE)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def args(self, output=None):
        values = {'packet': self.root/'not-read-packet.zip', 'packet-sha256': 'a'*64,
            'extracted': self.root/'not-read-extraction', 'source-archive': self.root/'not-read-source.zip',
            'source-archive-sha256': 'b'*64, 'source-sha': 'c'*40,
            'job': 'cas-meta2-20000101000000-1234abcd', 'output': output or self.root/'new_output'}
        return [word for name, value in values.items() for word in ('--'+name, str(value))]

    def test_all_external_pin_and_path_arguments_are_required(self):
        argv = self.args()
        for index in range(0, len(argv), 2):
            with self.subTest(missing=argv[index]), patch.object(self.subject, 'module') as import_common, \
                    patch.object(self.subject, 'run') as audit, redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    self.subject.main(argv[:index] + argv[index+2:])
                self.assertEqual(error.exception.code, 2)
                import_common.assert_not_called(); audit.assert_not_called()
        self.assertFalse((self.root/'new_output').exists())

    def test_abbreviated_external_pin_flag_not_accepted(self):
        argv = self.args(); argv[argv.index('--packet-sha256')] = '--packet-sha'
        with patch.object(self.subject, 'run') as audit, redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                self.subject.main(argv)
            self.assertEqual(error.exception.code, 2); audit.assert_not_called()

    def test_existing_output_rejected_before_any_audit(self):
        output = self.root/'existing'; output.mkdir()
        with patch.object(self.subject, 'run') as audit:
            with self.assertRaisesRegex(ValueError, 'V7_NEW_LOCAL_OUTPUT_REQUIRED'):
                self.subject.main(self.args(output))
            audit.assert_not_called()
        self.assertEqual(list(output.iterdir()), [])

    def test_output_outside_owned_records_directory_rejected_before_audit(self):
        output = HERE.parent/('outside-' + self.root.name)
        self.assertFalse(output.exists())
        with patch.object(self.subject, 'run') as audit:
            with self.assertRaisesRegex(ValueError, 'V7_NEW_LOCAL_OUTPUT_REQUIRED'):
                self.subject.main(self.args(output))
            audit.assert_not_called()
        self.assertFalse(output.exists())

    def test_cli_forwards_external_inputs_without_inventing_pins(self):
        output = self.root/'new_output'
        synthetic = {'status': 'SYNTHETIC_TEST_ONLY_NOT_A_REAL_AUDIT', 'completed': True,
                     'reviewer_files_sha256': {'summary.py': self.c.file_hash(HERE/'summary.py')}}
        renderer = SimpleNamespace(build=lambda result: 'Synthetic CLI test only. No audit was run.\n')
        with patch.object(self.subject, 'run', return_value=synthetic) as audit, \
                patch.object(self.subject, 'module', return_value=self.c), \
                patch.object(self.c, 'load', return_value=renderer) as load_renderer, \
                redirect_stdout(io.StringIO()) as text:
            self.assertEqual(self.subject.main(self.args(output) + ['--create-extraction']), 0)
        load_renderer.assert_called_once_with('_v7_human_summary', HERE/'summary.py')
        audit.assert_called_once_with(packet_path=self.root/'not-read-packet.zip', packet_sha256='a'*64,
            extracted=self.root/'not-read-extraction', source_archive=self.root/'not-read-source.zip',
            source_archive_sha256='b'*64, source_sha='c'*40, job='cas-meta2-20000101000000-1234abcd',
            create_extraction=True)
        receipt = output/'prototype_stored_review.json'
        self.assertEqual(self.c.decode(receipt.read_bytes()), synthetic)
        printed = json.loads(text.getvalue())
        self.assertEqual(printed['sha256'], self.c.file_hash(receipt))
        self.assertEqual((printed['cases'], printed['arm_verdicts']), (72, 360))
        self.assertEqual((output/'SUMMARY.md').read_text(encoding='utf-8'),
                         'Synthetic CLI test only. No audit was run.\n')
        # These constants describe the real CLI contract, not synthetic native execution.

    def test_cli_records_external_pin_failure_without_partial_success(self):
        output = self.root/'failed_output'
        with patch.object(self.subject, 'run', side_effect=ValueError('synthetic external pin mismatch')) as audit:
            with self.assertRaisesRegex(ValueError, 'synthetic external pin mismatch'):
                self.subject.main(self.args(output))
        audit.assert_called_once()
        failure = self.c.decode((output/'review_failure.json').read_bytes())
        self.assertIs(failure['completed'], False)
        self.assertIs(failure['no_partial_success_claim'], True)
        self.assertEqual(failure['status'], 'PROTOTYPE_V7_STORED_REVIEW_FAILED')
        self.assertEqual((failure['source_sha'], failure['source_archive_sha256'], failure['packet_sha256']),
                         ('c'*40, 'b'*64, 'a'*64))
        self.assertEqual(failure['errors'][0]['type'], 'ValueError')
        self.assertIn('synthetic external pin mismatch', failure['errors'][0]['traceback'])
        self.assertFalse((output/'prototype_stored_review.json').exists())


class SummaryTests(GuardedTestCase):
    def test_summary_refuses_incomplete_or_nonpassed_result(self):
        renderer = load(HERE/'summary.py', '_synthetic_v7_real_summary')
        for result in ({}, {'status': 'PROTOTYPE_V7_STORED_REVIEW_FAILED', 'completed': False},
                       {'status': 'PROTOTYPE_V7_STORED_REVIEW_PASSED', 'completed': False},
                       {'status': 'PROTOTYPE_V7_STORED_REVIEW_PASSED', 'completed': 1},
                       {'status': 'SYNTHETIC_TEST_ONLY', 'completed': True}):
            with self.subTest(result=result):
                with self.assertRaisesRegex(ValueError, 'V7_COMPLETED_REVIEW_REQUIRED_FOR_REPORT'):
                    renderer.build(result)


class IsolationTests(unittest.TestCase):
    def test_import_scope_restores_hooks_and_paths(self):
        hooks, paths = list(sys.meta_path), list(sys.path)
        before = {name for name in sys.modules if name.split('.')[0] in FORBIDDEN}
        with pure_scope():
            load(HERE/'review.py', '_synthetic_v7_review_isolation')
            load(HERE/'common.py', '_synthetic_v7_common_isolation')
            with self.assertRaisesRegex(AssertionError, 'TEST_MODEL_PROVIDER_IMPORT'):
                sys.meta_path[0].find_spec('torch.synthetic')
        self.assertEqual(sys.meta_path, hooks); self.assertEqual(sys.path, paths)
        self.assertEqual({name for name in sys.modules if name.split('.')[0] in FORBIDDEN}, before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
