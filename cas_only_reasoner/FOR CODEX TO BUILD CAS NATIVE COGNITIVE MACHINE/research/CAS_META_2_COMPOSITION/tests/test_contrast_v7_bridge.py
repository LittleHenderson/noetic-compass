"""Pure checks for the versioned training bridge. No neural execution."""
import ast
import copy
import importlib.abc
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class NoNeuralOrProvider(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch', 'tensorflow', 'jax', 'cupy',
                                     'casformer', 'cas_cjt', 'boto3', 'botocore'}:
            raise RuntimeError('NEURAL_OR_PROVIDER_IMPORT_FORBIDDEN:' + fullname)


sys.meta_path.insert(0, NoNeuralOrProvider())
from cas_meta2.contrast_v7 import data, train, checks, parent, evaluation


def function(version, module, name):
    path = ROOT/'cas_meta2'/version/(module+'.py')
    tree = ast.parse(path.read_text(encoding='utf-8'))
    return next(node for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == name)


class RemoveVersionedPlumbing(ast.NodeTransformer):
    """Only the explicit loader pin and schema version may differ in the loops."""
    def visit_FunctionDef(self, node):
        node = self.generic_visit(node)
        pairs = [(arg, default) for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults)
                 if arg.arg != 'expected_loader_sha256']
        node.args.kwonlyargs = [arg for arg, _ in pairs]
        node.args.kw_defaults = [default for _, default in pairs]
        return node

    def visit_Call(self, node):
        node = self.generic_visit(node)
        node.keywords = [item for item in node.keywords if item.arg != 'expected_loader_sha256']
        return node

    def visit_Dict(self, node):
        node = self.generic_visit(node)
        pairs = [(key, value) for key, value in zip(node.keys, node.values)
                 if not isinstance(key, ast.Constant) or key.value != 'loader_sha256']
        node.keys = [key for key, _ in pairs]
        node.values = [value for _, value in pairs]
        return node

    def visit_BoolOp(self, node):
        node = self.generic_visit(node)
        node.values = [value for value in node.values
                       if 'loader_sha256' not in ast.dump(value)]
        return node

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            node.value = node.value.replace('cas-meta2-contrast-neural-seal/7',
                                            'cas-meta2-contrast-neural-seal/6')
            node.value = node.value.replace('cas-meta2-training-parent-gate/7',
                                            'cas-meta2-training-parent-gate/6')
            node.value = node.value.replace('cas-meta2-contrast-evaluation-seal/7',
                                            'cas-meta2-contrast-evaluation-seal/6')
        return node


class BridgeTests(unittest.TestCase):
    def test_training_loop_is_unchanged_except_explicit_loader_plumbing(self):
        before = function('contrast_v6', 'train', 'run')
        after = RemoveVersionedPlumbing().visit(copy.deepcopy(function('contrast_v7', 'train', 'run')))
        self.assertEqual(ast.dump(before), ast.dump(after))

    def test_parent_training_check_is_unchanged_except_explicit_loader_plumbing(self):
        before = function('contrast_v6', 'checks', 'check_training')
        after = RemoveVersionedPlumbing().visit(copy.deepcopy(function('contrast_v7', 'checks', 'check_training')))
        self.assertEqual(ast.dump(before), ast.dump(after))

    def test_selection_and_prediction_helpers_unchanged(self):
        for name in ('TrainingConfig', 'measured_epoch', 'check_validation_counts',
                     'prediction_rows', 'write_new'):
            with self.subTest(name=name):
                self.assertEqual(ast.dump(function('contrast_v6', 'train', name)),
                                 ast.dump(function('contrast_v7', 'train', name)))

    def test_rule_seal_and_private_opening_sequence_unchanged(self):
        before = function('contrast_v6', 'evaluation', 'prepare')
        after = RemoveVersionedPlumbing().visit(
            copy.deepcopy(function('contrast_v7', 'evaluation', 'prepare')))
        self.assertEqual(ast.dump(before), ast.dump(after))

    def test_native_grouping_and_worker_unchanged(self):
        for name in ('grouped_results', 'worker_init'):
            with self.subTest(name=name):
                self.assertEqual(ast.dump(function('contrast_v6', 'evaluation', name)),
                                 ast.dump(function('contrast_v7', 'evaluation', name)))

    def test_module_imports_are_pure(self):
        self.assertFalse({'torch', 'tensorflow', 'jax', 'cupy', 'casformer',
                          'cas_cjt', 'boto3', 'botocore'}.intersection(sys.modules))

    def test_training_rejects_laptop_before_data_or_model(self):
        with patch.object(train.sys, 'platform', 'win32'):
            with self.assertRaisesRegex(ValueError, 'CONTRAST_AWS_LINUX_REQUIRED'):
                train.run('absent', 'absent', job='not-a-job',
                          expected_manifest_sha256='0'*64, expected_loader_sha256='0'*64,
                          curriculum_seed=1, excluded=frozenset())

    def test_loader_requires_external_pin_before_read(self):
        with patch.object(data, 'read', side_effect=AssertionError('must not read')):
            for value in (None, '', 7, 'A'*64, '0'*63):
                with self.subTest(value=value):
                    with self.assertRaisesRegex(ValueError, 'EXTERNAL_V7_LOADER_PIN_REQUIRED'):
                        data.public_loader(value)

    def test_wrong_loader_pin_rejects_before_import(self):
        with patch.object(data, 'read', return_value=b'raise RuntimeError("not imported")'), \
             patch.object(data.importlib.util, 'spec_from_file_location',
                          side_effect=AssertionError('must not import')):
            with self.assertRaisesRegex(ValueError, 'V7_PUBLIC_LOADER_BYTES_CHANGED'):
                data.public_loader('0'*64)

    def test_json_rejects_overflow_and_duplicate_fields(self):
        for value in (b'{"x":1e400}', b'{"x":NaN}', b'{"x":1,"x":2}'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    data.decode(value)

    def test_loader_pin_is_required_in_all_public_training_paths(self):
        node = function('contrast_v7', 'train', 'run')
        loads = [item for item in ast.walk(node) if isinstance(item, ast.Call)
                 and isinstance(item.func, ast.Attribute) and item.func.attr == 'load_training_bundle']
        self.assertEqual(len(loads), 2)
        for call in loads:
            self.assertIn('expected_loader_sha256', [item.arg for item in call.keywords])
        gate = function('contrast_v7', 'checks', 'check_training')
        loads = [item for item in ast.walk(gate) if isinstance(item, ast.Call)
                 and isinstance(item.func, ast.Attribute) and item.func.attr == 'load_training_bundle']
        self.assertEqual(len(loads), 1)
        self.assertIn('expected_loader_sha256', [item.arg for item in loads[0].keywords])

    def test_new_task_count_implies_new_step_count(self):
        config = train.TrainingConfig().checked()
        self.assertEqual(640+256, 896)
        self.assertEqual(math.ceil(896/config.batch_size), 56)
        self.assertEqual(config.epochs*math.ceil(896/config.batch_size), 11200)


if __name__ == '__main__':
    unittest.main(verbosity=2)
