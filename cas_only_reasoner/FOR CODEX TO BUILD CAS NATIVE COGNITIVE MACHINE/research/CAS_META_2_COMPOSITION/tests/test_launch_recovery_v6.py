"""Pure recovery-launcher contracts: fake inputs, no real ledger/provider/model work."""
import argparse
import ast
from contextlib import contextmanager, ExitStack, redirect_stdout
from copy import deepcopy
from decimal import Decimal
import importlib.abc
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class NoModelsOrProviders(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch', 'casformer', 'cas_cjt', 'tensorflow',
                                     'jax', 'cupy', 'boto3', 'botocore'}:
            raise AssertionError('REAL_MODEL_OR_PROVIDER_IMPORT_FORBIDDEN:' + fullname)


@contextmanager
def pure_scope():
    hooks, paths = list(sys.meta_path), list(sys.path)
    sys.meta_path.insert(0, NoModelsOrProviders())
    try:
        yield
    finally:
        sys.meta_path[:] = hooks
        sys.path[:] = paths


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


with pure_scope():
    launch = load('pure_recovery_launcher_tested', ROOT/'aws/launch_recovery_v6.py')
p = launch.profiles


def manifest():
    """Synthetic shape only; it is not an admitted source archive."""
    mapping = {p.PILOT+'/'+name: 'a'*64 for name in p.RECOVERY_LOCAL_FILES}
    for index in range(557-len(mapping)):
        mapping[p.PILOT+'/fake_source_'+str(index)+'.py'] = 'a'*64
    mapping[p.ADMISSION_PATH] = p.ADMISSION_SHA256
    mapping[p.SPEC_PATH] = 'b'*64
    return {
        'schema_version': 2, 'source_sha': 'c'*40, 'baseline_sha': launch.ACCEPTED_BASELINE,
        'pilot_dir': p.PILOT, 'meta1_dir': 'research/CAS_META_1_LEARNED_SELECTION',
        'meta_runtime_dir': 'research/CASFORMER_v0_3_META_LOGIC_WIP',
        'dependency_lock': p.PILOT+'/requirements-gpu.txt', 'wheel_paths': [],
        'files_sha256': mapping,
        'experiment': {'profile': 'contrast_recovery_v6', 'entrypoint': p.ENTRYPOINT,
                       'spec_path': p.SPEC_PATH, 'spec_sha256': 'b'*64},
        'recovery': p.recovery_record(mapping),
        'external_packet': {'sha256': p.PACKET_SHA256, 'bytes': p.PACKET_BYTES},
    }


def top_functions(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    return {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}


def named_calls(node, name):
    return [item for item in ast.walk(node) if isinstance(item, ast.Call) and
            ((isinstance(item.func, ast.Name) and item.func.id == name) or
             (isinstance(item.func, ast.Attribute) and item.func.attr == name))]


class RecoveryLaunchTests(unittest.TestCase):
    def setUp(self):
        scope = pure_scope()
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        self.tmp = tempfile.TemporaryDirectory(prefix='recovery-launch-test-', dir=ROOT/'records')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.assertEqual(self.base.parent, (ROOT/'records').resolve())
        self.plan = json.loads(launch.PLAN_FILE.read_bytes())
        self.manifest = manifest()
        self.args = argparse.Namespace(smoke_only=False, approved_cap_usd='400.00',
            archive=str(self.base/'nonexistent-source.zip'), sha256='a'*64, source_sha='c'*40,
            prior_packet=str(self.base/'nonexistent-prior.zip'), profile='FAKE_NO_PROVIDER',
            subnet_id='subnet-012345', receipt_dir=str(self.base/'new-output'))
        self.functions = top_functions(ROOT/'aws/launch_recovery_v6.py')

    def config(self):
        return {**self.plan, 'job': 'cas-meta2-synthetic-test', 'bucket': 'synthetic-only',
                'archive_sha256': 'a'*64, 'manifest': self.manifest,
                'prior_packet': self.manifest['external_packet'], 'smoke_only': False}

    def never(self, *args, **kwargs):
        raise AssertionError('BUDGET_PROVIDER_OR_UNEXPECTED_PATH_REACHED')

    def test_scoped_import_and_test_guards_leave_no_hook_leak(self):
        hooks, paths = list(sys.meta_path), list(sys.path)
        with pure_scope():
            loaded = load('recovery_launcher_scope_probe', ROOT/'aws/launch_recovery_v6.py')
            self.assertTrue(callable(loaded.remote_program))
        self.assertEqual(sys.meta_path, hooks)
        self.assertEqual(sys.path, paths)
        with self.assertRaisesRegex(ValueError, 'scope probe'):
            with pure_scope():
                raise ValueError('scope probe')
        self.assertEqual(sys.meta_path, hooks)

    def test_plan_is_explicit_one_hour_four_dollars_and_no_training(self):
        with patch.object(launch.budget, 'read_ledger', self.never), \
             patch.object(launch.budget, 'reserve_budget', self.never):
            launch.validate_approval('400.00', self.plan)
            self.assertEqual(launch.budget.validate_plan(self.plan, '4.00'), Decimal('3.52'))
        self.assertEqual(self.plan['per_launch_reserved_cap_usd'], '4.00')
        self.assertEqual(self.plan['runtime_seconds_max'], 3600)
        self.assertEqual(self.plan['compute_seconds_max'], 3300)
        self.assertEqual(self.plan['automatic_retries'], 0)
        self.assertIs(self.plan['training_performed'], False)
        self.assertIs(self.plan['fresh_test'], False)
        self.assertIs(self.plan['predictions_reused_unchanged'], True)

    def test_plan_changes_and_nonfinite_caps_are_refused_without_ledger(self):
        with patch.object(launch.budget, 'read_ledger', self.never), \
             patch.object(launch.budget, 'reserve_budget', self.never):
            for cap in (None, '', '4.00', '399.00', 'NaN', 'Infinity'):
                with self.subTest(cap=cap), self.assertRaises(launch.LaunchRefused):
                    launch.validate_approval(cap, self.plan)
            for key, value in (('runtime_seconds_max', 3601), ('per_launch_reserved_cap_usd', '5.00'),
                               ('automatic_retries', 1), ('instance_type', 'g4dn.xlarge'),
                               ('instance_count', True), ('local_neural_execution', True)):
                bad = {**self.plan, key: value}
                with self.subTest(key=key), self.assertRaises(launch.LaunchRefused):
                    launch.validate_approval('400.00', bad)

    def test_plan_only_does_not_reserve_or_execute(self):
        with patch.object(launch, 'execute', self.never), \
             patch.object(launch.budget, 'read_ledger', self.never), \
             patch.object(launch.budget, 'reserve_budget', self.never), redirect_stdout(io.StringIO()) as out:
            self.assertEqual(launch.main([]), 0)
        self.assertIs(json.loads(out.getvalue())['aws_actions_performed'], False)

    def test_synthetic_recovery_manifest_has_exact_profile(self):
        self.assertEqual(launch.experiment_record(self.manifest), self.manifest['experiment'])
        for name in ('contrast_learning_v6', 'learning_v3', None):
            bad = deepcopy(self.manifest)
            bad['experiment']['profile'] = name
            with self.subTest(profile=name), self.assertRaises(launch.LaunchRefused):
                launch.experiment_record(bad)

    def test_remote_source_compiles_without_being_executed(self):
        text = launch.remote_program(self.config())
        compile(ast.parse(text), '<remote-code-not-executed>', 'exec')
        self.assertIn("'aws/recovery_remote_v6.py'", text)
        self.assertIn("'--enable-native-evaluation'", text)
        self.assertIn("'--admission-sha256'", text)
        self.assertIn("'--recovery-manifest-sha256'", text)
        self.assertIn("'cases') != 72", text)
        self.assertIn("'arm_verdicts') != 360", text)

    def test_remote_never_calls_training_generation_or_old_campaign(self):
        text = launch.remote_program(self.config())
        tree = ast.parse(text)
        constants = {node.value for node in ast.walk(tree)
                     if isinstance(node, ast.Constant) and isinstance(node.value, str)}
        for forbidden in ('cas_meta2.campaign_v3', 'cas_meta2.contrast_v6.campaign',
                          'cas_meta2.contrast_v7.campaign', '--epochs', '--training-file'):
            self.assertNotIn(forbidden, constants)
        for forbidden in ('generate_dataset', 'generate_predictions', 'train_policy',
                          'seal_predictions', 'reseal_predictions'):
            self.assertFalse(named_calls(tree, forbidden))
        self.assertIn("env.pop('CAS_META2_RUN_CONTRAST_TRAINING',None)", text)
        self.assertIn("env['CAS_META2_RUN_CONTRAST_RECOVERY'] = '1'", text)
        self.assertIn("'training_performed') is not False", text)
        self.assertIn("'predictions_reused_unchanged') is not True", text)

    def test_remote_prior_packet_pin_and_deadline_precede_recovery(self):
        text = launch.remote_program(self.config())
        self.assertIn("s3_get('input/prior_packet.zip',prior_packet)", text)
        self.assertIn("prior_packet.stat().st_size != CONFIG['prior_packet']['bytes']", text)
        self.assertIn("sha(prior_packet) != CONFIG['prior_packet']['sha256']", text)
        self.assertLess(text.index('PRIOR_PACKET_IDENTITY_MISMATCH'), text.index("'--enable-native-evaluation'"))
        self.assertLess(text.index('CLOUD_DEADLINE_NOT_CONFIRMED'), text.index("'-m','pip','install'"))
        self.assertIn('effective_seconds = min(3000,', text)
        self.assertIn('INSUFFICIENT_RECOVERY_TIME_AFTER_GPU_GATE', text)

    def test_smoke_and_missing_recovery_mode_are_refused(self):
        for value in (True, None, 0):
            with self.subTest(value=value), self.assertRaisesRegex(
                    launch.LaunchRefused, 'RECOVERY_HAS_NO_TRAINING_OR_SMOKE_MODE'):
                launch.remote_program({**self.config(), 'smoke_only': value})
        self.args.smoke_only = True
        with patch.object(launch, 'campaign_execution_lock', self.never), \
             patch.object(launch.budget, 'read_ledger', self.never), \
             self.assertRaises(launch.LaunchRefused):
            launch.execute(self.args, self.plan, self.manifest)

    def test_invalid_archive_rejects_before_source_budget_and_execute(self):
        archive = self.base/'invalid.zip'
        archive.write_bytes(b'inert invalid archive')
        with patch.object(launch, 'verify_launcher_identity', self.never), \
             patch.object(launch, 'execute', self.never), \
             patch.object(launch.budget, 'read_ledger', self.never), redirect_stdout(io.StringIO()) as out:
            code = launch.main(['--execute', '--archive', str(archive),
                '--sha256', '0'*64, '--source-sha', 'c'*40, '--prior-packet', self.args.prior_packet,
                '--receipt-dir', self.args.receipt_dir, '--approved-cap-usd', '400.00'])
        self.assertEqual(code, 2)
        self.assertIn('ARCHIVE_SHA_MISMATCH', out.getvalue())

    def test_source_failure_precedes_packet_lock_and_budget(self):
        with patch.object(launch, 'verify_launcher_identity',
                          side_effect=launch.LaunchRefused('SOURCE_PROBE')), \
             patch.object(launch, 'validate_prior_packet', self.never), \
             patch.object(launch, 'campaign_execution_lock', self.never), \
             patch.object(launch.budget, 'read_ledger', self.never), \
             self.assertRaisesRegex(launch.LaunchRefused, 'SOURCE_PROBE'):
            launch.execute(self.args, self.plan, self.manifest)

    def test_invalid_prior_packet_rejects_before_lock_or_budget(self):
        tiny = self.base/'tiny-prior.zip'
        tiny.write_bytes(b'not the registered packet')
        self.args.prior_packet = str(tiny)
        with patch.object(launch, 'verify_launcher_identity', return_value={}), \
             patch.object(launch, 'campaign_execution_lock', self.never), \
             patch.object(launch.budget, 'read_ledger', self.never), \
             patch.object(launch, 'digest', self.never), \
             self.assertRaisesRegex(launch.LaunchRefused, 'PRIOR_PACKET_IDENTITY_MISMATCH'):
            launch.execute(self.args, self.plan, self.manifest)

    def test_exact_packet_pin_is_not_taken_from_caller_manifest(self):
        fake = SimpleNamespace(is_file=lambda: True, is_symlink=lambda: False,
                               parents=[], stat=lambda: SimpleNamespace(st_size=p.PACKET_BYTES))
        with patch.object(launch, 'digest', return_value=p.PACKET_SHA256):
            self.assertEqual(launch.validate_prior_packet(fake, self.manifest),
                             {'sha256': p.PACKET_SHA256, 'bytes': p.PACKET_BYTES})
            for change in ({'sha256': 'f'*64}, {'bytes': p.PACKET_BYTES+1},
                           {'bytes': float(p.PACKET_BYTES)}):
                bad = deepcopy(self.manifest)
                bad['external_packet'].update(change)
                with self.subTest(change=change), self.assertRaisesRegex(
                        launch.LaunchRefused, 'PRIOR_PACKET_MANIFEST_BINDING_MISMATCH'):
                    launch.validate_prior_packet(fake, bad)

    def test_locked_stage_rechecks_identity_and_packet_before_budget(self):
        for function in ('verify_launcher_identity', 'validate_prior_packet'):
            with self.subTest(function=function), ExitStack() as stack:
                stack.enter_context(patch.object(launch, 'verify_launcher_identity', return_value={}))
                stack.enter_context(patch.object(launch, 'validate_prior_packet', return_value={}))
                stack.enter_context(patch.object(launch, function,
                    side_effect=launch.LaunchRefused('RECHECK_PROBE')))
                stack.enter_context(patch.object(launch.budget, 'read_ledger', self.never))
                with self.assertRaisesRegex(launch.LaunchRefused, 'RECHECK_PROBE'):
                    launch._execute_locked(self.args, self.plan, self.manifest)

    def test_exhausted_budget_rejects_before_provider_import(self):
        with patch.object(launch, 'verify_launcher_identity', return_value={}), \
             patch.object(launch, 'validate_prior_packet', return_value={}), \
             patch.object(launch.budget, 'read_ledger', return_value={'remaining_unreserved_usd': '3.99'}), \
             patch.object(launch, 'reserve_budget', self.never), \
             self.assertRaisesRegex(launch.LaunchRefused, 'CAMPAIGN_BUDGET_EXHAUSTED'):
            launch._execute_locked(self.args, self.plan, self.manifest)

    def test_invalid_local_launch_arguments_never_construct_provider_session(self):
        boto = ModuleType('boto3')
        boto.Session = self.never
        botocore = ModuleType('botocore')
        botocore.__path__ = []
        config = ModuleType('botocore.config')
        config.Config = lambda **kwargs: SimpleNamespace(**kwargs)
        exceptions = ModuleType('botocore.exceptions')
        exceptions.ClientError = type('SyntheticClientError', (Exception,), {})
        # These are inert test modules, not imports of provider libraries.
        fake_modules = {'boto3': boto, 'botocore': botocore,
                        'botocore.config': config, 'botocore.exceptions': exceptions}
        for key, value, message in (('subnet_id', '', 'EXPLICIT_SUBNET_REQUIRED'),
                                   ('receipt_dir', str(ROOT), 'NEW_RECEIPT_DIRECTORY_INSIDE_PILOT_REQUIRED')):
            args = deepcopy(self.args)
            setattr(args, key, value)
            with self.subTest(key=key), patch.dict(sys.modules, fake_modules), \
                 patch.object(launch, 'verify_launcher_identity', return_value={}), \
                 patch.object(launch, 'validate_prior_packet', return_value={}), \
                 patch.object(launch.budget, 'read_ledger', return_value={'remaining_unreserved_usd': '4.00'}), \
                 patch.object(launch, 'reserve_budget', self.never), \
                 self.assertRaisesRegex(launch.LaunchRefused, message):
                launch._execute_locked(args, self.plan, self.manifest)

    def test_identity_uses_recovery_spec_validator(self):
        calls = {item.func.attr for item in ast.walk(self.functions['verify_launcher_identity'])
                 if isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute)
                 and isinstance(item.func.value, ast.Name) and item.func.value.id == 'profiles'}
        self.assertIn('validate_recovery_spec', calls)
        self.assertNotIn('validate_contrast_spec', calls)

    def test_source_archive_packet_checks_precede_reservation_and_provider(self):
        execute = self.functions['execute']
        self.assertLess(named_calls(execute, 'verify_launcher_identity')[0].lineno,
                        named_calls(execute, 'validate_prior_packet')[0].lineno)
        self.assertLess(named_calls(execute, 'validate_prior_packet')[0].lineno,
                        named_calls(execute, 'campaign_execution_lock')[0].lineno)
        locked = self.functions['_execute_locked']
        provider_line = min(node.lineno for node in ast.walk(locked)
                            if isinstance(node, ast.Import) and any(alias.name == 'boto3' for alias in node.names))
        for name in ('verify_launcher_identity', 'validate_prior_packet', 'read_ledger'):
            self.assertLess(named_calls(locked, name)[0].lineno, provider_line)
        self.assertLess(named_calls(locked, 'reserve_budget')[0].lineno,
                        named_calls(locked, 'create_bucket')[0].lineno)
        main = self.functions['main']
        self.assertLess(named_calls(main, 'validate_archive')[0].lineno,
                        named_calls(main, 'execute')[0].lineno)

    def test_prior_packet_has_dedicated_get_upload_and_cleanup_keys(self):
        source = ast.get_source_segment((ROOT/'aws/launch_recovery_v6.py').read_text(),
                                        self.functions['_execute_locked'])
        self.assertIn('("payload.zip","permit.json","remote.py","prior_packet.zip")', source)
        self.assertIn('s3.upload_file(str(Path(args.prior_packet).resolve()),bucket,"input/prior_packet.zip")', source)
        self.assertIn('("payload.zip","remote.py","permit.json","prior_packet.zip")', source)
        self.assertLess(source.index('if artifact_verified:'), source.index('s3.delete_objects'))
        self.assertIn('check_tag(s3.get_bucket_tagging', source)
        self.assertNotIn('"s3:*"', source)

    def test_unchanged_ownership_budget_cleanup_and_archive_safety_helpers(self):
        old = top_functions(ROOT/'aws/launch_contrast_v6.py')
        names = ('reserve_budget', 'validate_archive', 'check_tag', 'verify_downloaded_packet',
                 'confirm_deleted_volumes', 'remove_owned_auxiliary_resources', 'reconcile_instance',
                 'verify_schedule', 'terminate_owned_instance', 'build_evidence_bundle',
                 'sample_artifact_bytes', 'user_data', 'campaign_execution_lock', 'safe_relative', 'digest')
        for name in names:
            with self.subTest(function=name):
                self.assertEqual(ast.dump(old[name]), ast.dump(self.functions[name]))
        self.assertEqual(launch.EXECUTION_LOCK_FILE, ROOT/'records/aws_campaign_execution_v3.lock')

    def test_prior_packet_is_external_not_embedded_source_input(self):
        self.assertIs(self.manifest['recovery']['packet_in_source_archive'], False)
        self.assertFalse(any('prior_packet.zip' in name or 'cloud_artifacts.zip' in name
                             for name in self.manifest['files_sha256']))
        self.assertEqual(self.manifest['external_packet']['bytes'], 74958249)


if __name__ == '__main__':
    unittest.main(verbosity=2)

