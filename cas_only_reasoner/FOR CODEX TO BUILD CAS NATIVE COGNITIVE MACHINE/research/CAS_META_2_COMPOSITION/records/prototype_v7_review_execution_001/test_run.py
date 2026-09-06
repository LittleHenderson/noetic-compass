"""Synthetic wrapper tests only: fake audit child and fake Git authentication.

Files below a temporary child of this test directory are small artificial bytes.
No actual packet, source archive, reviewer, dataset, provider or model is opened
or executed. Real hashing, path refusal, receipt checks and output capture run.
"""
from contextlib import contextmanager, redirect_stdout, redirect_stderr
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
            raise AssertionError('TEST_NEURAL_PROVIDER_IMPORT:' + fullname)


@contextmanager
def pure_scope():
    hooks, paths = list(sys.meta_path), list(sys.path)
    sys.meta_path.insert(0, Guard())
    try:
        yield
    finally:
        sys.meta_path[:], sys.path[:] = hooks, paths


def load():
    spec = importlib.util.spec_from_file_location('_synthetic_review_capture', HERE/'run.py')
    subject = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(subject)
    return subject


class Fixture:
    def __init__(self, test, s):
        self.s = s
        temporary = tempfile.TemporaryDirectory(prefix='_synthetic_capture_', dir=HERE)
        test.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.capture = self.root/'capture'; self.capture.mkdir()
        self.review = self.root/'review'; self.review.mkdir()
        self.packet, self.archive = self.root/'packet.zip', self.root/'archive.zip'
        self.packet.write_bytes(b'synthetic packet bytes; no ZIP or data')
        self.archive.write_bytes(b'synthetic source bytes; no code archive')
        self.output = self.capture/'execution_001'
        self.review_output, self.extracted = self.review/'run_001', self.review/'extracted_001'
        self.checks = self.review/'checks_004/checks_receipt.json'; self.checks.parent.mkdir()
        self.mapping = {}
        for name in s.REVIEWER_FILES:
            raw = ('# synthetic reviewer byte stand-in: ' + name + '\n').encode()
            (self.review/name).write_bytes(raw)
            self.mapping[name] = sha256(raw).hexdigest()
        self.prep = {'completed': True, 'source_unchanged': True, 'actual_packet_review': False,
            'synthetic_tests': True, 'source_sha': s.SOURCE, 'source_archive_sha256': s.file_hash(self.archive),
            'source_files_verified': 603, 'protected_files_verified': 316,
            'commands': [{'returncode': 0} for _ in range(4)], 'reviewer_files_sha256': self.mapping}
        self.checks.write_bytes(s.canonical(self.prep))
        for key, value in {'ROOT': self.root, 'HERE': self.capture, 'REVIEW': self.review,
            'PACKET': self.packet, 'ARCHIVE': self.archive, 'CHECKS': self.checks,
            'ARCHIVE_SHA256': s.file_hash(self.archive), 'CHECKS_SHA256': s.file_hash(self.checks)}.items():
            test.enterContext(patch.object(s, key, value))
        self.git = test.enterContext(patch.object(s, 'git_bound_bytes'))
        self.pin = s.file_hash(self.packet)
        self.child_returncode = 0
        self.make_success = True
        self.change_result = lambda result: None
        self.after_wait = lambda: None
        self.omit_summary = False
        self.calls = []
        self.popen = test.enterContext(patch.object(s.subprocess, 'Popen', side_effect=self.fake_popen))

    def fake_popen(self, command, *, cwd, stdout, stderr):
        self.calls.append({'command': command, 'cwd': cwd})
        stdout.write(b'SYNTHETIC AUDIT STDOUT ONLY\n')
        stderr.write(b'SYNTHETIC AUDIT STDERR ONLY\n')
        fixture = self
        class Child:
            pid = 12345
            returncode = None
            def wait(self, timeout=None):
                fixture.review_output.mkdir()
                if fixture.make_success:
                    result = {'status': s.PASS, 'completed': True, 'errors': [], 'job': s.JOB,
                        'source_sha': s.SOURCE, 'source_archive_sha256': s.ARCHIVE_SHA256,
                        'packet_sha256': fixture.pin, 'reviewer_files_sha256': fixture.mapping,
                        'test_fixture_only': True}
                    fixture.change_result(result)
                    s.write_new(fixture.review_output/'prototype_stored_review.json', result)
                    if not fixture.omit_summary:
                        (fixture.review_output/'SUMMARY.md').write_text('Synthetic test only.\n', encoding='utf-8')
                elif fixture.child_returncode:
                    s.write_new(fixture.review_output/'review_failure.json', {'completed': False, 'synthetic': True})
                fixture.after_wait()
                self.returncode = fixture.child_returncode
                return self.returncode
            def poll(self):
                return self.returncode
        s = self.s
        return Child()

    def run(self, **kwargs):
        args = dict(packet=self.packet, packet_sha256=self.pin, output=self.output,
                    review_output=self.review_output, extracted=self.extracted)
        args.update(kwargs)
        with redirect_stdout(io.StringIO()):
            return self.s.execute(**args)

    def receipt(self):
        return self.s.decode((self.output/'process_receipt.json').read_bytes())


class WrapperTests(unittest.TestCase):
    def setUp(self):
        scope = pure_scope(); scope.__enter__(); self.addCleanup(scope.__exit__, None, None, None)
        self.s = load(); self.f = Fixture(self, self.s)

    def test_synthetic_pass_captures_exact_command_pid_exit_times_and_hashes(self):
        f, s = self.f, self.s
        self.assertEqual(f.run(), 0)
        r = f.receipt()
        self.assertTrue(r['completed']); self.assertTrue(r['independent_review_passed'])
        self.assertEqual((r['pid'], r['returncode'], r['wrapper_returncode']), (12345, 0, 0))
        self.assertTrue(r['child_started']); self.assertGreaterEqual(r['wall_seconds'], 0)
        self.assertLessEqual(r['started_utc'], r['child_finished_utc'])
        self.assertLessEqual(r['child_finished_utc'], r['finished_utc'])
        expected = s.command(f.packet, f.pin, f.extracted, f.review_output)
        self.assertEqual(r['command'], expected); self.assertEqual(f.calls, [{'command': expected, 'cwd': f.root}])
        self.assertEqual(r['prepared_before'], r['prepared_after'])
        self.assertEqual(r['prepared_before']['reviewer_git_files_verified'], 11)
        self.assertEqual(f.git.call_count, 2)
        for name in ('stdout', 'stderr'):
            self.assertEqual(r[name+'_sha256'], s.file_hash(f.output/(name+'.txt')))
        e = s.decode((f.output/'execution_result.json').read_bytes())
        self.assertEqual(e['process_receipt_sha256'], s.file_hash(f.output/'process_receipt.json'))
        self.assertEqual(e['review_receipt_sha256'], s.file_hash(f.review_output/'prototype_stored_review.json'))
        self.assertEqual(s.decode((f.output/'process_started.json').read_bytes())['pid'], 12345)

    def test_wrong_or_missing_external_packet_pin_does_not_start_child(self):
        for pin in ('', None, 'ABC'*22, 'g'*64):
            with self.subTest(pin=pin):
                with self.assertRaisesRegex(ValueError, 'EXECUTION_EXTERNAL_PACKET_HASH_REQUIRED'):
                    self.f.run(packet_sha256=pin)
        self.f.popen.assert_not_called(); self.assertFalse(self.f.output.exists())

    def test_different_packet_path_is_refused_before_read_or_launch(self):
        with self.assertRaisesRegex(ValueError, 'EXECUTION_FIXED_PACKET_PATH_REQUIRED'):
            self.f.run(packet=self.f.root/'another.zip')
        self.f.popen.assert_not_called(); self.assertFalse(self.f.output.exists())

    def test_existing_capture_cannot_be_reused(self):
        self.f.output.mkdir()
        with self.assertRaisesRegex(ValueError, 'EXECUTION_NEW_CONTAINED_CHILD_REQUIRED'):
            self.f.run()
        self.f.popen.assert_not_called(); self.assertEqual(list(self.f.output.iterdir()), [])

    def test_existing_review_output_or_extraction_refused(self):
        for key in ('review_output', 'extracted'):
            with self.subTest(key=key):
                existing = self.f.review/('existing_'+key); existing.mkdir()
                with self.assertRaisesRegex(ValueError, 'EXECUTION_NEW_CONTAINED_CHILD_REQUIRED'):
                    self.f.run(**{key: existing})
        self.f.popen.assert_not_called(); self.assertFalse(self.f.output.exists())

    def test_outside_or_root_capture_refused(self):
        for output in (self.f.root/'outside', self.f.capture, self.f.capture/'missing'/'nested'):
            with self.subTest(output=output):
                with self.assertRaisesRegex(ValueError, 'EXECUTION_NEW_CONTAINED_CHILD_REQUIRED'):
                    self.f.run(output=output)
        self.f.popen.assert_not_called()

    def test_same_review_and_extraction_target_refused(self):
        with self.assertRaisesRegex(ValueError, 'EXECUTION_OUTPUT_EXTRACTION_MUST_DIFFER'):
            self.f.run(extracted=self.f.review_output)
        self.f.popen.assert_not_called()

    def test_packet_hash_mismatch_is_retained_as_failed_preflight(self):
        self.assertEqual(self.f.run(packet_sha256='e'*64), 1)
        r = self.f.receipt()
        self.assertFalse(r['completed']); self.assertFalse(r['child_started']); self.assertIsNone(r['pid'])
        self.assertIsNone(r['returncode']); self.assertIn('EXECUTION_HASH_MISMATCH', r['errors'][0]['message'])
        self.f.popen.assert_not_called()

    def test_prepared_reviewer_byte_change_refused_before_child(self):
        (self.f.review/'gpu.py').write_bytes(b'changed synthetic reviewer')
        self.assertEqual(self.f.run(), 1)
        self.assertFalse(self.f.receipt()['child_started']); self.f.popen.assert_not_called()

    def test_extra_reviewer_python_file_refused(self):
        (self.f.review/'extra.py').write_bytes(b'# unexpected')
        self.assertEqual(self.f.run(), 1)
        self.assertIn('EXECUTION_EXACT_TEN_REVIEWER_FILES_REQUIRED', self.f.receipt()['errors'][0]['message'])
        self.f.popen.assert_not_called()

    def test_checks_receipt_hash_and_git_binding_are_required(self):
        self.f.git.side_effect = ValueError('synthetic Git blob mismatch')
        self.assertEqual(self.f.run(), 1)
        self.assertIn('synthetic Git blob mismatch', self.f.receipt()['errors'][0]['message'])
        self.f.popen.assert_not_called()

    def test_changed_checks_receipt_refused(self):
        self.f.checks.write_bytes(b'{}')
        self.assertEqual(self.f.run(), 1)
        self.assertIn('EXECUTION_HASH_MISMATCH', self.f.receipt()['errors'][0]['message'])
        self.f.popen.assert_not_called()

    def test_failed_preparation_command_not_admitted_even_with_new_test_pin(self):
        self.f.prep['commands'][2]['returncode'] = 1
        self.f.checks.write_bytes(self.s.canonical(self.f.prep))
        with patch.object(self.s, 'CHECKS_SHA256', self.s.file_hash(self.f.checks)):
            self.assertEqual(self.f.run(), 1)
        self.assertIn('EXECUTION_PREPARATION_RECEIPT_INVALID', self.f.receipt()['errors'][0]['message'])
        self.f.popen.assert_not_called()

    def test_nonzero_child_with_pass_file_still_fails(self):
        self.f.child_returncode = 7
        self.assertEqual(self.f.run(), 1)
        r = self.f.receipt()
        self.assertEqual(r['returncode'], 7); self.assertFalse(r['independent_review_passed'])
        self.assertIn('prototype_stored_review.json', r['observed_review_artifacts'])

    def test_nonzero_child_failure_file_is_preserved_and_hashed(self):
        self.f.child_returncode = 9; self.f.make_success = False
        self.assertEqual(self.f.run(), 1)
        r = self.f.receipt()
        self.assertEqual(r['returncode'], 9)
        self.assertEqual(r['observed_review_artifacts']['review_failure.json'],
                         self.s.file_hash(self.f.review_output/'review_failure.json'))
        self.assertNotIn('review_receipt', r)

    def test_zero_exit_without_review_receipt_is_not_pass(self):
        self.f.make_success = False
        self.assertEqual(self.f.run(), 1)
        r = self.f.receipt()
        self.assertEqual(r['returncode'], 0); self.assertEqual(r['wrapper_returncode'], 1)
        self.assertFalse(r['independent_review_passed'])

    def test_zero_exit_with_failed_review_status_is_not_pass(self):
        self.f.change_result = lambda r: r.update(status='PROTOTYPE_V7_STORED_REVIEW_FAILED', completed=False)
        self.assertEqual(self.f.run(), 1)
        self.assertIn('EXECUTION_COMPLETED_REVIEW_IDENTITY_MISMATCH', self.f.receipt()['errors'][0]['message'])

    def test_zero_exit_with_wrong_job_source_or_packet_identity_is_not_pass(self):
        self.f.change_result = lambda r: r.update(job='wrong', source_sha='e'*40, packet_sha256='f'*64)
        self.assertEqual(self.f.run(), 1)
        self.assertFalse(self.f.receipt()['completed'])

    def test_zero_exit_with_missing_summary_is_not_pass(self):
        self.f.omit_summary = True
        self.assertEqual(self.f.run(), 1)
        self.assertFalse(self.f.receipt()['completed'])

    def test_prepared_source_change_after_exit_cannot_pass(self):
        self.f.after_wait = lambda: (self.f.review/'review.py').write_bytes(b'changed after child')
        self.assertEqual(self.f.run(), 1)
        r = self.f.receipt()
        self.assertEqual(r['returncode'], 0); self.assertFalse(r['completed'])
        self.assertIn('EXECUTION_HASH_MISMATCH', r['errors'][0]['message'])

    def test_packet_change_after_exit_cannot_pass(self):
        self.f.after_wait = lambda: self.f.packet.write_bytes(b'changed after child')
        self.assertEqual(self.f.run(), 1)
        self.assertFalse(self.f.receipt()['completed'])

    def test_spawn_error_retains_command_and_raw_empty_streams(self):
        self.f.popen.side_effect = OSError('synthetic spawn failure')
        self.assertEqual(self.f.run(), 1)
        r = self.f.receipt()
        self.assertIsNone(r['pid']); self.assertFalse(r['child_started']); self.assertIsNone(r['returncode'])
        self.assertEqual(r['errors'][0]['type'], 'OSError')
        self.assertEqual((self.f.output/'stdout.txt').read_bytes(), b'')
        self.assertTrue((self.f.output/'command.json').is_file())

    def test_all_cli_args_required_no_automatic_packet_hash(self):
        args = ['--packet', str(self.f.packet), '--packet-sha256', self.f.pin, '--output', str(self.f.output),
                '--review-output', str(self.f.review_output), '--extracted', str(self.f.extracted)]
        with patch.object(self.s, 'execute') as execute:
            for index in range(0, len(args), 2):
                with self.subTest(missing=args[index]), redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as error:
                        self.s.main(args[:index]+args[index+2:])
                    self.assertEqual(error.exception.code, 2)
            execute.assert_not_called()


class PureUtilityTests(unittest.TestCase):
    def test_duplicate_or_nonfinite_json_rejected(self):
        s = load()
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                s.decode(raw)

    def test_git_batch_binds_requested_fixed_commit_and_exact_raw_bytes(self):
        s = load(); files = {HERE/'synthetic.py': b'raw\r\nbytes\n'}
        raw = next(iter(files.values()))
        responses = [SimpleNamespace(stdout=(str(HERE)+'\n').encode()),
                     SimpleNamespace(stdout=b'0'*40+b' blob '+str(len(raw)).encode()+b'\n'+raw+b'\n')]
        with patch.object(s.subprocess, 'run', side_effect=responses) as run:
            s.git_bound_bytes(files)
        self.assertEqual(run.call_args_list[1].kwargs['input'],
                         (s.REVIEWER_COMMIT+':synthetic.py\n').encode())
        responses[1] = SimpleNamespace(stdout=b'0'*40+b' blob 1\nx\n')
        with patch.object(s.subprocess, 'run', side_effect=responses), self.assertRaisesRegex(ValueError, 'GIT_BYTES_CHANGED'):
            s.git_bound_bytes(files)

    def test_import_has_no_neural_provider_or_hook_leak(self):
        before = {name for name in sys.modules if name.split('.')[0] in FORBIDDEN}
        hooks, paths = list(sys.meta_path), list(sys.path)
        with pure_scope():
            load()
        self.assertEqual(hooks, sys.meta_path); self.assertEqual(paths, sys.path)
        self.assertEqual(before, {name for name in sys.modules if name.split('.')[0] in FORBIDDEN})


if __name__ == '__main__':
    unittest.main(verbosity=2)
