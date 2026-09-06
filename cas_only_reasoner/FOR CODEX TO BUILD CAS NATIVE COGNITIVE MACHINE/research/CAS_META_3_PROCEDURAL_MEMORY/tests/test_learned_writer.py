"""Real data-only writer process using synthetic learning evidence."""
from hashlib import sha256
import json
import os
from uuid import uuid4

import pytest

from cas_meta3 import learned_writer as writer
from cas_meta3 import learning_evidence as evidence
from cas_meta3.learned_store import RAW_FIELDS
from test_learned_handoff import fixture


def materialize():
    root = writer.ROOT / 'records' / 'writer_test_inputs' / uuid4().hex
    root.mkdir(parents=True)
    candidate, inputs = fixture()
    inputs['permitted_cjts'] = sorted(inputs['permitted_cjts'])
    files = {}
    for name in RAW_FIELDS:
        path = root / (name + '.json')
        path.write_bytes(inputs.pop(name))
        files[name] = str(path)
    request = dict(schema=writer.SCHEMA, package=candidate, trust=inputs,
                   evidence_files=files, source_identity=writer.source_identity(),
                   store_path=str(root / 'saved' / 'candidate.sqlite'),
                   receipt_path=str(root / 'saved' / 'writer.json'))
    return root, request


def seal(root, request):
    raw = evidence.canonical(request)
    path = root / 'request.json'
    path.write_bytes(raw)
    return path, sha256(raw).hexdigest()


def test_real_child_exit_and_saved_bytes():
    root, request = materialize()
    path, digest = seal(root, request)
    result = writer.run_writer(path, digest, root / 'process')
    assert result['writer_exit_verified'] is True
    assert result['pid'] != os.getpid()
    assert result['returncode'] == 0
    assert result['reader_started'] is False
    assert result['qualification_status'] == 'UNQUALIFIED'
    saved = json.loads((root / 'saved' / 'writer.json').read_bytes())
    assert saved['native_execution_performed'] is False
    assert saved['learning_performed'] is False
    assert result['store_sha256'] == sha256((root / 'saved' / 'candidate.sqlite').read_bytes()).hexdigest()
    with pytest.raises(writer.WriterError, match='NEW_WRITER_OUTPUTS_REQUIRED'):
        writer.run_writer(path, digest, root / 'again')


@pytest.mark.parametrize('change', ['source', 'digest', 'scope', 'trust'])
def test_bad_request_rejected_before_child(change):
    root, request = materialize()
    if change == 'source':
        request['source_identity'] = {}
    elif change == 'scope':
        request['store_path'] = str(writer.ROOT / 'outside.sqlite')
    elif change == 'trust':
        request['trust'].pop('expected_inspection_sha256')
    path, digest = seal(root, request)
    if change == 'digest':
        digest = '0' * 64
    with pytest.raises(writer.WriterError):
        writer.run_writer(path, digest, root / 'process')
    assert not (root / 'process').exists()


def test_child_failure_preserves_actual_exit_receipt():
    root, request = materialize()
    request['trust']['expected_inspection_sha256'] = '0' * 64
    path, digest = seal(root, request)
    with pytest.raises(writer.WriterError, match='WRITER_EXIT_NOT_VERIFIED'):
        writer.run_writer(path, digest, root / 'process')
    result = json.loads((root / 'process' / 'process_receipt.json').read_bytes())
    assert result['returncode'] != 0
    assert result['writer_exit_verified'] is False
    assert result['automatic_retries'] == 0
    assert not (root / 'saved' / 'candidate.sqlite').exists()


@pytest.mark.parametrize('name', ['torch', 'tensorflow', 'jax', 'casformer', 'cas_cjt', 'cupy', 'boto3'])
def test_writer_import_guard(name):
    with pytest.raises(RuntimeError, match='WRITER_NEURAL_OR_PROVIDER_IMPORT_FORBIDDEN'):
        writer.NoNeuralImports().find_spec(name)
