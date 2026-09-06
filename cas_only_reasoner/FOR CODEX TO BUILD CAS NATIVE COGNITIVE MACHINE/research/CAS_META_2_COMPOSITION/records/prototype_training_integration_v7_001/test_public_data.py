"""Known-fixture public-loader tests; no new graphs, models, AWS, or live results."""
from contextlib import ExitStack
from copy import deepcopy
from hashlib import sha256
import importlib.abc
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class TestGuard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch', 'casformer', 'cas_cjt', 'jax', 'cupy', 'tensorflow', 'boto3', 'botocore'}:
            raise AssertionError('NEURAL_OR_PROVIDER_IMPORT_FORBIDDEN_IN_TEST')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


sys.meta_path.insert(0, TestGuard())
p = module('v7_public_inputs_tested', HERE/'public_data.py')
a = module('v7_parent_for_public_tests', HERE/'adapter.py')
FIXTURE = ROOT/'records/contrast_v6_bundle_probe_001/dataset'
BASE_PIN = '36e57983fd43ac9650e5946d5fd04ca0888e9013131fc450f8d9f8f3c84131a1'


def put(path, value):
    path.write_bytes(p.canonical(value)+b'\n')


def blocked(*args, **kwargs):
    raise AssertionError('PRIVATE_PARSER_PARENT_OR_PROVIDER_PATH_CALLED')


class PublicDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_temp = tempfile.TemporaryDirectory(prefix='public_data_known_fixture_', dir=HERE)
        cls.fixture_root = Path(cls.fixture_temp.name)
        cls.ctx = a.Context()
        cls.cfg = cls.ctx.c.Config(**p.DIAGNOSTIC)
        cls.merged = cls.fixture_root/'parent_bundle'
        cls.parent_receipt = a.merge(FIXTURE, cls.merged, expected_sha256=BASE_PIN,
            seed=926603, config=cls.cfg, excluded=frozenset(), ctx=cls.ctx)
        cls.pin = p.digest(p.read(cls.merged/'manifest.json'))
        cls.loader_pin = p.digest(p.read(HERE/'public_data.py'))
        cls.options = dict(expected_sha256=cls.pin, seed=926603, config=cls.cfg,
                           excluded=frozenset(), expected_loader_sha256=cls.loader_pin)
        cls.public = cls.fixture_root/'public_bundle'
        cls.export_receipt = p.export_training_bundle(cls.merged, cls.public, **cls.options, parent_ctx=cls.ctx)

    @classmethod
    def tearDownClass(cls):
        cls.fixture_temp.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='public_data_case_', dir=HERE)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root/'public_bundle'
        shutil.copytree(self.public, self.bundle)
        self.options = dict(type(self).options)

    def reload(self):
        return p.load_training_bundle(self.bundle, **self.options)

    def update_manifest(self, name=None, value=None, edit=None):
        """Synthetic corruption with a newly supplied digest tests deeper checks."""
        m = p.decode(p.read(self.bundle/'manifest.json'))
        if name:
            put(self.bundle/name, value)
            m['sha256'][name] = p.digest(p.read(self.bundle/name))
        if edit:
            edit(m)
        put(self.bundle/'manifest.json', m)
        self.options['expected_sha256'] = p.digest(p.read(self.bundle/'manifest.json'))

    def test_import_has_no_context_hooks_helper_loading_or_reads(self):
        paths, hooks = list(sys.path), list(sys.meta_path)
        with patch.object(Path, 'open', blocked), patch.object(subprocess, 'run', blocked):
            imported = module('v7_public_inputs_import_only', HERE/'public_data.py')
        self.assertEqual(imported.SCHEMA, p.SCHEMA)
        self.assertEqual(sys.path, paths)
        self.assertEqual(sys.meta_path, hooks)

    def test_export_admits_parent_then_excludes_private_file(self):
        self.assertEqual({path.name for path in self.bundle.iterdir()}, {*p.PUBLIC_FILES, 'manifest.json'})
        self.assertFalse((self.bundle/'test_private.json').exists())
        self.assertTrue(self.export_receipt['parent_validation']['completed'])
        self.assertTrue(self.export_receipt['parent_reads_private_test_targets'])
        self.assertFalse(self.export_receipt['private_labels_read_by_loader'])
        self.assertFalse(self.export_receipt['training_performed'])

    def test_loader_and_reload_never_touch_private_parser_parent_git_or_generation(self):
        original_open = Path.open
        opened = []
        def guarded_open(path, *args, **kwargs):
            if path.name == 'test_private.json':
                raise AssertionError('PRIVATE_TEST_FILE_OPENED')
            if path.absolute().is_relative_to((ROOT/'records/aws_contrast_v6_001').absolute()):
                raise AssertionError('LIVE_RESULT_OPENED')
            opened.append(str(path))
            return original_open(path, *args, **kwargs)
        hooks, paths = list(sys.meta_path), list(sys.path)
        with ExitStack() as stack:
            stack.enter_context(patch.object(Path, 'open', guarded_open))
            stack.enter_context(patch.object(subprocess, 'run', blocked))
            stack.enter_context(patch.object(subprocess, 'check_output', blocked))
            for name in ('validate_bundle', 'materialize', 'original', 'check_original_records', 'source_identity', 'Context'):
                stack.enter_context(patch.object(a, name, blocked))
            for name in ('cas_meta2.curriculum', 'cas_meta2.curriculum_v2', 'cas_meta2.curriculum_v3',
                         'cas_meta2.contrast_v6.curriculum'):
                helper = sys.modules[name]
                stack.enter_context(patch.object(helper, 'parse_problem', blocked))
                if hasattr(helper, 'generate'):
                    stack.enter_context(patch.object(helper, 'generate', blocked))
            stack.enter_context(patch.object(self.ctx.c, 'validate', blocked))
            first, second = self.reload(), self.reload()
        self.assertEqual(first['receipt'], second['receipt'])
        self.assertEqual(sys.meta_path, hooks)
        self.assertEqual(sys.path, paths)
        self.assertTrue(opened)
        self.assertEqual(set(first), {'train', 'validation', 'test_public', 'tokenizer', 'manifest', 'receipt'})
        self.assertFalse(first['receipt']['test_programs_parsed_by_loader'])
        self.assertFalse(first['receipt']['parent_validation_replayed_by_loader'])

    def test_loader_does_not_install_cuda_blockers_or_reject_preloaded_neural_module(self):
        self.assertNotIn('torch', sys.modules)
        before = list(sys.meta_path)
        # Placeholder only: no import, tensors, model, or CUDA work occurs.
        with patch.dict(sys.modules, {'torch': types.ModuleType('synthetic_torch_placeholder')}):
            loaded = self.reload()
        self.assertEqual(len(loaded['train']), 352)
        self.assertEqual(sys.meta_path, before)

    def test_cold_subprocess_load_has_no_parent_git_parser_or_private_path(self):
        code = '''import importlib.abc, importlib.util, json, subprocess, sys
from pathlib import Path
class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch','casformer','cas_cjt','jax','tensorflow','cupy','boto3','botocore','adapter'}:
            raise AssertionError('COLD_FORBIDDEN_IMPORT:'+fullname)
sys.meta_path.insert(0, Guard())
def blocked(*args, **kwargs):
    raise AssertionError('COLD_SUBPROCESS_OR_GIT_CALLED')
subprocess.run = subprocess.check_output = subprocess.Popen = blocked
original_open = Path.open
def opened(path, *args, **kwargs):
    if path.name == 'test_private.json':
        raise AssertionError('COLD_PRIVATE_OPEN')
    return original_open(path, *args, **kwargs)
Path.open = opened
def profile(frame, event, arg):
    if event == 'call' and frame.f_code.co_name in {'parse_problem','validate_bundle','materialize','original','check_original_records','generate','token_and_counts','source_identity'}:
        raise AssertionError('COLD_PARENT_PARSER_GENERATOR_CALLED:'+frame.f_code.co_name)
sys.setprofile(profile)
spec = importlib.util.spec_from_file_location('cold_public_loader', sys.argv[1])
loader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loader)
paths, hooks = list(sys.path), list(sys.meta_path)
result = loader.load_training_bundle(sys.argv[2], expected_sha256=sys.argv[3], seed=926603,
    config=loader.DIAGNOSTIC, excluded=frozenset(), expected_loader_sha256=sys.argv[4])
assert paths == sys.path and hooks == sys.meta_path
assert not any('adapter' == name or 'parent' in name for name in sys.modules if name.startswith('v7'))
print(json.dumps({'train':len(result['train']), 'validation':len(result['validation']),
    'test_public':len(result['test_public']), 'receipt':result['receipt']}))
'''
        child = subprocess.run([sys.executable, '-B', '-c', code, str(HERE/'public_data.py'),
            str(self.bundle), self.pin, self.loader_pin], cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(child.returncode, 0, child.stderr)
        result = json.loads(child.stdout)
        self.assertEqual((result['train'], result['validation'], result['test_public']), (352, 24, 9))
        self.assertFalse(result['receipt']['private_labels_read_by_loader'])
        self.assertFalse(result['receipt']['private_test_graph_separation_replayed'])

    def test_actual_exact_records_counts_and_train_only_tokenizer(self):
        fitted = []
        tokenizer_class = self.ctx.c.LosslessPublicTokenizer
        fit = tokenizer_class.fit_train
        def tracked(publics, **kwargs):
            fitted.append(deepcopy(publics))
            return fit(publics, **kwargs)
        with patch.object(tokenizer_class, 'fit_train', tracked):
            loaded = self.reload()
        train = loaded['train']
        originals = p.decode(p.read(ROOT/p.PROTOTYPE/'tasks.json'))
        base = p.decode(p.read(self.bundle/'base_train.json'))
        self.assertEqual(train, base+originals)
        self.assertEqual(fitted, [[task['public'] for task in train]])
        self.assertEqual(loaded['receipt']['splits'], {
            'train': {'tasks': 352, 'depths': {'1': 32, '2': 160, '3': 160}},
            'validation': {'tasks': 24, 'depths': {'1': 8, '2': 8, '3': 8}},
            'test': {'tasks': 9, 'depths': {'3': 6, '4': 3}}})
        self.assertEqual(loaded['receipt']['imported_train_examples'], 256)
        self.assertEqual(loaded['tokenizer'].to_dict()['fitted_examples'], 352)

    def test_counts_for_proposed896_shape_without_generation(self):
        expected = p.expected_counts(926604, p.REGISTERED_SHAPE)
        self.assertEqual(expected['train'], {'tasks': 896, 'depths': {'1': 128, '2': 384, '3': 384}})
        self.assertEqual((expected['train']['tasks']//16)*200, 11200)
        with self.assertRaisesRegex(ValueError, 'BASE_SEED_REFUSED'):
            p.expected_counts(2026092601, p.REGISTERED_SHAPE)
        for config in (dict(p.DIAGNOSTIC, train_flat=0), dict(p.DIAGNOSTIC, train_flat=True)):
            with self.subTest(config=config):
                with self.assertRaises(ValueError): p.expected_counts(926603, config)

    def test_external_manifest_and_loader_pins_required(self):
        for name in ('expected_sha256', 'expected_loader_sha256'):
            for value in ('', '0'*64, None):
                with self.subTest(name=name, value=value):
                    changed = {**self.options, name: value}
                    with self.assertRaises(ValueError): p.load_training_bundle(self.bundle, **changed)

    def test_extra_private_file_rejected_without_opening_it(self):
        (self.bundle/'test_private.json').write_bytes(b'DO NOT OPEN')
        original = Path.open
        def no_private(path, *args, **kwargs):
            if path.name == 'test_private.json': raise AssertionError('PRIVATE_FILE_OPENED')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', no_private):
            with self.assertRaisesRegex(ValueError, 'DIRECTORY_CONTENTS'): self.reload()

    def test_changed_public_files_refused_by_external_manifest(self):
        for name in p.PUBLIC_FILES:
            with self.subTest(name=name):
                path = self.bundle/name
                before = path.read_bytes()
                path.write_bytes(before+b' ')
                try:
                    with self.assertRaisesRegex(ValueError, 'FILE_DIGEST'): self.reload()
                finally: path.write_bytes(before)

    def test_import_map_and_exact_append_cannot_be_rewritten(self):
        for mutation in ('map', 'drop', 'reorder', 'public', 'provenance', 'extra_record_field'):
            with self.subTest(mutation=mutation):
                local = self.root/mutation
                shutil.copytree(self.public, local)
                original_bundle, original_options = self.bundle, self.options
                self.bundle, self.options = local, dict(type(self).options)
                try:
                    if mutation == 'map':
                        value = p.decode(p.read(local/'training_imports.json'))
                        value['records'][0]['train_index'] = 0
                        self.update_manifest('training_imports.json', value)
                    else:
                        value = p.decode(p.read(local/'train.json'))
                        if mutation == 'drop': value.pop()
                        elif mutation == 'reorder': value[-1], value[-2] = value[-2], value[-1]
                        elif mutation == 'public': value[96]['public']['problem'] += ' changed'
                        elif mutation == 'provenance': value[96]['provenance']['evaluation_group'] = 'train'
                        else: value[96]['contrast_group'] = 'invented'
                        self.update_manifest('train.json', value)
                    with self.assertRaises(ValueError): self.reload()
                finally: self.bundle, self.options = original_bundle, original_options

    def test_resealed_base_train_still_bound_to_retained_base_manifest(self):
        value = p.decode(p.read(self.bundle/'base_train.json'))
        value[0]['public']['problem'] += ' changed'
        self.update_manifest('base_train.json', value)
        with self.assertRaisesRegex(ValueError, 'BASE_TRAIN_CHANGED'): self.reload()

    def test_manifest_counts_and_private_metadata_must_match(self):
        for name in ('count', 'private_hash', 'allowed_split'):
            with self.subTest(name=name):
                before = (self.bundle/'manifest.json').read_bytes()
                options = dict(self.options)
                if name == 'count': edit = lambda m: m['splits']['train'].update(tasks=353)
                elif name == 'private_hash': edit = lambda m: m['sha256'].update({'test_private.json': '0'*64})
                else: edit = lambda m: m['prototype'].update(allowed_split='test')
                self.update_manifest(edit=edit)
                try:
                    with self.assertRaises(ValueError): self.reload()
                finally:
                    (self.bundle/'manifest.json').write_bytes(before)
                    self.options = options

    def test_serialized_tokenizer_is_recomputed_from_train_only(self):
        value = p.decode(p.read(self.bundle/'tokenizer.json'))
        value['fitted_examples'] = 351
        self.update_manifest('tokenizer.json', value)
        with self.assertRaisesRegex(ValueError, 'TRAIN_ONLY_TOKENIZER'): self.reload()

    def test_helper_byte_change_is_rejected_before_helper_import(self):
        original = p.read
        def changed(path):
            raw = original(path)
            return raw+b'changed' if str(path).replace('\\', '/').endswith('cas_meta2/codec.py') else raw
        with patch.object(p, 'read', changed), patch.object(p, '_helpers', blocked):
            with self.assertRaisesRegex(ValueError, 'HELPER_BYTES_CHANGED'): self.reload()

    def test_bad_parent_private_bytes_block_export(self):
        source = self.root/'bad_parent'
        shutil.copytree(self.merged, source)
        path = source/'test_private.json'
        path.write_bytes(path.read_bytes()+b' ')
        output = self.root/'must_not_export'
        with self.assertRaises(ValueError):
            p.export_training_bundle(source, output, **self.options, parent_ctx=self.ctx)
        self.assertFalse(output.exists())

    def test_export_refuses_existing_output(self):
        before = (self.bundle/'manifest.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'NEW_PUBLIC_EXPORT_REQUIRED'):
            p.export_training_bundle(self.merged, self.bundle, **self.options, parent_ctx=self.ctx)
        self.assertEqual(before, (self.bundle/'manifest.json').read_bytes())

    def test_json_duplicate_and_overflow_rejected(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e400}'):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError): p.decode(raw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
