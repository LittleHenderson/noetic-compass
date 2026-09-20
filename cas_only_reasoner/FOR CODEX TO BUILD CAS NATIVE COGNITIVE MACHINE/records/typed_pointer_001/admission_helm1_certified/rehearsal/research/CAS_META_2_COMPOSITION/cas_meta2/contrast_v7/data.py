"""Thin runtime bridge to the separately source-pinned public-only loader.

The caller supplies the loader hash from its registered experiment. Never derive
that trust anchor from the file being loaded. The exporter/parent validator are
not imported or invoked through this module. No private-label read path is added.
"""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re

from ..contrast_v6.data import no_links, read, directory
from ..contrast_v6.curriculum import require

ROOT = Path(__file__).resolve().parents[2]
INTEGRATION = 'records/prototype_training_integration_v7_001'


def digest(raw):
    return sha256(raw).hexdigest()


def decode(raw):
    from ..contrast_v6.data import decode as frozen_decode
    value = frozen_decode(raw)
    # Reject finite-looking numeric literals that overflow to infinity.
    json.dumps(value, allow_nan=False)
    return value


def integration_source_identity():
    """Record helper bytes; the external loader pin remains separately required."""
    names = (INTEGRATION+'/adapter.py', INTEGRATION+'/public_data.py',
             'records/contrast_curriculum_v6_probe_001/tasks.json',
             'records/contrast_curriculum_v6_probe_001/receipt.json',
             'records/contrast_curriculum_v6_probe_001/build.py',
             'records/contrast_curriculum_v6_probe_001/verify.py',
             'records/contrast_v6_exclusions_001/inventory.json')
    return {name: digest(read(ROOT/name)) for name in names}


def public_loader(expected_loader_sha256):
    require(type(expected_loader_sha256) is str
            and re.fullmatch('[0-9a-f]{64}', expected_loader_sha256),
            'EXTERNAL_V7_LOADER_PIN_REQUIRED')
    path = no_links(ROOT/INTEGRATION/'public_data.py')
    require(digest(read(path)) == expected_loader_sha256, 'V7_PUBLIC_LOADER_BYTES_CHANGED')
    spec = importlib.util.spec_from_file_location('cas_meta2_v7_public_input_loader', path)
    require(spec is not None and spec.loader is not None, 'V7_PUBLIC_LOADER_SPEC_REQUIRED')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(digest(read(path)) == expected_loader_sha256, 'V7_PUBLIC_LOADER_BYTES_CHANGED')
    return module


def load_training_bundle(path, *, expected_sha256, seed, config, excluded,
                         expected_loader_sha256):
    loader = public_loader(expected_loader_sha256)
    result = loader.load_training_bundle(path, expected_sha256=expected_sha256,
        seed=seed, config=config, excluded=excluded,
        expected_loader_sha256=expected_loader_sha256, root=ROOT)
    require(type(result) is dict and set(result) ==
            {'train', 'validation', 'test_public', 'tokenizer', 'manifest', 'receipt'},
            'V7_PUBLIC_LOADER_RETURN_CONTRACT_CHANGED')
    require(result['receipt'].get('private_labels_read_by_loader') is False
            and result['receipt'].get('test_programs_parsed_by_loader') is False,
            'V7_PUBLIC_LOADER_BOUNDARY_CHANGED')
    return result

