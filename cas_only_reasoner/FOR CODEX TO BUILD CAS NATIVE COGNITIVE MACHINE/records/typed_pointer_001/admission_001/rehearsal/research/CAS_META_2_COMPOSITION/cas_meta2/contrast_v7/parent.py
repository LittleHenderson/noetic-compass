"""Portable, pure parent admission for the exact original256 training append.

A source-bound experiment supplies a pin-file hash and public-loader hash.
Runtime uses those verified bytes, not local Git availability. This code is
parent/evaluator-only; never call it inside a neural trainer. The frozen
prototype validators install neural-import guards in this pure process.
"""
from pathlib import Path
import sys

from . import data as d

ROOT = Path(__file__).resolve().parents[2]


class Context:
    def __init__(self, pins, *, expected_pins_sha256, expected_loader_sha256):
        self.pins = d.no_links(pins)
        self.pin_hash = expected_pins_sha256
        self.loader_hash = expected_loader_sha256
        self.root = ROOT
        self.loader = d.public_loader(expected_loader_sha256)
        raw = d.read(self.pins)
        d.require(d.digest(raw) == expected_pins_sha256, 'V7_PARENT_SOURCE_PINS_CHANGED')
        self.source = d.decode(raw)
        self.loader.verify_source(self.source, expected_loader_sha256=expected_loader_sha256, root=ROOT)
        d.require(not any(name.split('.')[0] in
                         {'torch', 'casformer', 'cas_cjt', 'tensorflow', 'jax', 'cupy',
                          'boto3', 'botocore'} for name in sys.modules),
                  'V7_PURE_PARENT_PROCESS_REQUIRED')
        self.adapter = self.loader_module(ROOT/d.INTEGRATION/'adapter.py', 'cas_meta2_v7_parent_adapter')
        self.c, self.d, _ = self.loader._helpers(ROOT)
        self.builder = self.loader_module(ROOT/'records/contrast_curriculum_v6_probe_001/build.py',
                                          'cas_meta2_v7_frozen_prototype_builder')
        self.verifier = self.loader_module(ROOT/'records/contrast_curriculum_v6_probe_001/verify.py',
                                           'cas_meta2_v7_frozen_prototype_verifier')
        self.assert_unchanged()

    @staticmethod
    def loader_module(path, name):
        # Context verifies every path's bytes before this helper is called.
        import importlib.util
        spec = importlib.util.spec_from_file_location(name, path)
        d.require(spec is not None and spec.loader is not None, 'V7_PARENT_MODULE_SPEC_REQUIRED')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def assert_unchanged(self):
        d.require(d.digest(d.read(self.pins)) == self.pin_hash, 'V7_PARENT_SOURCE_PINS_CHANGED')
        self.loader.verify_source(self.source, expected_loader_sha256=self.loader_hash, root=ROOT)


def validate_bundle(path, *, expected_sha256, seed, config, excluded,
                    pins, expected_pins_sha256, expected_loader_sha256):
    context = Context(pins, expected_pins_sha256=expected_pins_sha256,
                      expected_loader_sha256=expected_loader_sha256)
    return context.adapter.validate_bundle(path, expected_sha256=expected_sha256,
        seed=seed, config=config, excluded=excluded, ctx=context)


def merge(source, output, *, expected_sha256, seed, config, excluded,
          pins, expected_pins_sha256, expected_loader_sha256):
    context = Context(pins, expected_pins_sha256=expected_pins_sha256,
                      expected_loader_sha256=expected_loader_sha256)
    a = context.adapter
    a.reject_reserved(seed)
    source = a.directory(source, ('manifest.json', 'train.json', *a.HELDOUT))
    output = a.no_links(output)
    d.require(source.name == 'base_dataset' and output.name == 'dataset'
              and source.parent.resolve() == output.parent.resolve()
              and not output.exists(), 'V7_NEW_SIBLING_DATASET_REQUIRED')
    manifest_raw = a.read(source/'manifest.json')
    context.d.checked_manifest(manifest_raw, expected_sha256=expected_sha256,
        seed=seed, config=config, excluded=excluded)
    raw = {'manifest.json': manifest_raw,
           **{name: a.read(source/name) for name in ('train.json', *a.HELDOUT)}}
    contents, manifest = a.materialize(raw, expected_sha256=expected_sha256,
        seed=seed, config=config, excluded=excluded, ctx=context)
    context.assert_unchanged()
    output.mkdir(parents=False, exist_ok=False)
    for name, value in {**contents, 'manifest.json': a.canonical(manifest)+b'\n'}.items():
        with (output/name).open('xb') as stream:
            stream.write(value)
    result = a.validate_bundle(output, expected_sha256=a.digest(a.read(output/'manifest.json')),
                               seed=seed, config=config, excluded=excluded, ctx=context)
    d.require(all(a.read(source/name) == value for name, value in raw.items()),
              'V7_BASE_DATA_CHANGED_DURING_MERGE')
    return result


def export_training_bundle(source, output, *, expected_sha256, seed, config, excluded,
                           pins, expected_pins_sha256, expected_loader_sha256):
    context = Context(pins, expected_pins_sha256=expected_pins_sha256,
                      expected_loader_sha256=expected_loader_sha256)
    return context.loader.export_training_bundle(source, output,
        expected_sha256=expected_sha256, seed=seed, config=config, excluded=excluded,
        expected_loader_sha256=expected_loader_sha256, parent_ctx=context)
