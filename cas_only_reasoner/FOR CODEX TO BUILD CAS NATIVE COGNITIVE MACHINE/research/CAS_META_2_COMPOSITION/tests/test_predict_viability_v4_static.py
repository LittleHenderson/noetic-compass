"""Pure request guards; no claim of GPU decoder parity or performance."""
import ast
from pathlib import Path
import sys
import pytest
from cas_meta2 import predict_viability_v4 as candidate

pytestmark = pytest.mark.not_gpu
JOB = 'cas-meta2-20260906000000-12345678'


def test_import_is_pure_and_model_not_touched_without_authority(monkeypatch):
    monkeypatch.delenv('CAS_META2_RUN_DECODER_ABLATION', raising=False)
    with pytest.raises(RuntimeError, match='EXPLICIT_AWS_DECODER_ABLATION_REQUIRED'):
        candidate.predict_public(None, None, [], job=JOB, grammar_mode='v3')
    assert 'torch' not in sys.modules


@pytest.mark.parametrize('device', ['cpu', 'mps', 'cuda:bad', None])
def test_cpu_or_invalid_device_is_rejected_before_neural_import(device, monkeypatch):
    monkeypatch.setenv('CAS_META2_AWS_JOB_ID', JOB)
    monkeypatch.setenv('CAS_META2_RUN_DECODER_ABLATION', '1')
    with pytest.raises(RuntimeError, match='DECODER_CUDA_REQUIRED'):
        candidate.require_context(JOB, device, 'v3', 30)


@pytest.mark.parametrize('mode,seconds', [('unknown', 30), ('v3', 0), ('viability_v4', 901), ('v3', True)])
def test_unregistered_mode_and_unbounded_runtime_rejected(mode, seconds, monkeypatch):
    monkeypatch.setenv('CAS_META2_AWS_JOB_ID', JOB)
    monkeypatch.setenv('CAS_META2_RUN_DECODER_ABLATION', '1')
    with pytest.raises(ValueError): candidate.require_context(JOB, 'cuda', mode, seconds)


def test_invalid_batch_is_refused_before_neural_import(monkeypatch):
    monkeypatch.setenv('CAS_META2_AWS_JOB_ID', JOB)
    monkeypatch.setenv('CAS_META2_RUN_DECODER_ABLATION', '1')
    with pytest.raises(ValueError, match='DECODER_BATCH_BOUND_INVALID'):
        candidate.predict_public(None,None,[],job=JOB,grammar_mode='viability_v4')
    assert 'torch' not in sys.modules


def test_no_training_or_semantic_parser_calls():
    tree = ast.parse(Path(candidate.__file__).read_text())
    names = {node.attr for node in ast.walk(tree) if isinstance(node,ast.Attribute)}
    names |= {node.id for node in ast.walk(tree) if isinstance(node,ast.Name)}
    assert not names & {'backward','optimizer','parse_problem','verify_task','reference_task','load_state_dict','save'}
