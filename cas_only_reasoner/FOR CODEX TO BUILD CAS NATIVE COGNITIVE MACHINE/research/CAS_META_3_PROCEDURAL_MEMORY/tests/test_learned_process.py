"""Pure coordinator scope checks. No GPU reader runs in these tests."""
from copy import deepcopy
import pytest
from cas_meta3 import learned_process as process
from cas_meta3 import learned_writer as writer


def requests():
    saved = {'trust': {'expected_digest': 'a' * 64, 'permitted_cjts': ['A']},
             'store_path': str(writer.ROOT / 'records' / 'synthetic' / 'candidate.sqlite')}
    reader = {'job': 'synthetic', 'store_path': saved['store_path'],
        'expected_digest': 'a' * 64, 'trust_inputs': {'permitted_cjts': ['A']},
        'source_public': {}, 'public_cases': [], 'output': 'unused', 'native_output': 'unused'}
    return saved, reader


def test_identical_candidate_and_external_scope():
    saved, reader = requests()
    before = deepcopy((saved, reader))
    process.check_binding(saved, reader)
    assert (saved, reader) == before


@pytest.mark.parametrize('change', ['digest', 'trust', 'store', 'extra', 'missing'])
def test_changed_reader_binding_rejected(change):
    saved, reader = requests()
    if change == 'digest': reader['expected_digest'] = 'b' * 64
    if change == 'trust': reader['trust_inputs']['permitted_cjts'].append('B')
    if change == 'store': reader['store_path'] += '.other'
    if change == 'extra': reader['arbitrary_code'] = 'forbidden'
    if change == 'missing': reader.pop('source_public')
    with pytest.raises(writer.WriterError):
        process.check_binding(saved, reader)


def test_pair_refuses_local_execution_before_source_or_files(monkeypatch):
    monkeypatch.delenv('CAS_META3_RUN_GPU_DEMO', raising=False)
    with pytest.raises(process.reuse.native_support.NativeDemoError, match='META3_EXPLICIT_AWS_GPU_JOB_REQUIRED'):
        process.run_process_pair(writer_request_path='absent', writer_request_sha256='0'*64,
            reader_request={'job': 'absent'}, process_output='absent', expected_source_identity={})
