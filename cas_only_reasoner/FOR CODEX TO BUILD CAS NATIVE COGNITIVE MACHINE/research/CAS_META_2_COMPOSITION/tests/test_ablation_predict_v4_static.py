"""Pure coordinator guards; actual checkpoint loading requires AWS CUDA."""
import ast
from pathlib import Path
import sys
import pytest
from cas_meta2 import ablation_predict_v4 as candidate

pytestmark = pytest.mark.not_gpu
JOB = 'cas-meta2-20260906000000-12345678'


def test_unapproved_call_stops_before_archive_or_neural_import(monkeypatch):
    monkeypatch.delenv('CAS_META2_RUN_DECODER_ABLATION', raising=False)
    with pytest.raises(RuntimeError, match='EXPLICIT_AWS'):
        candidate.run('absent.zip', 'absent_output', job=JOB)
    assert 'torch' not in sys.modules


def test_nonlinux_stops_before_neural_import(monkeypatch):
    monkeypatch.setenv('CAS_META2_RUN_DECODER_ABLATION', '1')
    monkeypatch.setenv('CAS_META2_AWS_JOB_ID', JOB)
    monkeypatch.setattr(sys, 'platform', 'win32')
    with pytest.raises(RuntimeError, match='AWS_LINUX'):
        candidate.run('absent.zip', 'absent_output', job=JOB)
    assert 'torch' not in sys.modules


@pytest.mark.parametrize('seconds', [0, 901, True, 1.5])
def test_invalid_deadline(monkeypatch, seconds):
    monkeypatch.setenv('CAS_META2_RUN_DECODER_ABLATION', '1')
    monkeypatch.setenv('CAS_META2_AWS_JOB_ID', JOB)
    with pytest.raises(ValueError, match='TIME_BOUND'):
        candidate.require_request(JOB, seconds)


def test_no_output_overwrite(tmp_path):
    with pytest.raises(ValueError, match='NEW_OUTPUT'):
        candidate.new_directory(tmp_path)
    path = tmp_path / 'new'
    assert candidate.new_directory(path) == path
    candidate.write_new(path / 'bytes', b'original')
    with pytest.raises(FileExistsError): candidate.write_new(path / 'bytes', b'replacement')
    assert (path / 'bytes').read_bytes() == b'original'


def test_full_prediction_mapping_and_denominators():
    publics = [{'index': index} for index in range(72)]
    actions = {arm: [{'value': index} for index in range(72)] for arm in candidate.ARMS}
    rows = candidate.prediction_rows(publics, actions)
    assert len(rows) == 72 and rows[71]['case_index'] == 71
    assert rows[71]['actions']['cas_trained'] == {'value': 71}
    for invalid in [{}, {**actions, 'extra': []}, {**actions, 'cas_trained': []}]:
        with pytest.raises(ValueError, match='FULL_ARM_COVERAGE'):
            candidate.prediction_rows(publics, invalid)


def test_no_training_or_private_target_parser():
    source = Path(candidate.__file__).read_text()
    tree = ast.parse(source)
    calls = {node.func.attr for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
    assert not calls & {'backward', 'step', 'train', 'load', 'save'}
    assert 'test_private.json' not in source
