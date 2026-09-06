"""Pure byte checks against the real preserved input artifact; no model load."""
import json
from pathlib import Path
import sys
import zipfile
import pytest
from cas_meta2 import ablation_inputs_v4 as candidate

pytestmark = pytest.mark.not_gpu
ARCHIVE = Path(__file__).resolve().parents[1] / 'records/decoder_ablation_inputs_v4_001/inputs.zip'


def test_real_public_read_never_opens_private_or_old_predictions(monkeypatch):
    reads = []
    original = zipfile.ZipFile.read
    def tracked(self, name, *args, **kwargs):
        reads.append(name)
        return original(self, name, *args, **kwargs)
    monkeypatch.setattr(zipfile.ZipFile, 'read', tracked)
    result = candidate.read_prediction_inputs(ARCHIVE, ['dataset/test_public.json', 'checkpoints.json'])
    assert len(json.loads(result['dataset/test_public.json'])) == 72
    assert reads == ['input_manifest.json', 'dataset/test_public.json', 'checkpoints.json']
    assert 'torch' not in sys.modules


@pytest.mark.parametrize('names', [[], ['dataset/test_private.json'], ['predictions.jsonl'],
                                  ['../secret'], ['tokenizer.json', 'tokenizer.json']])
def test_forbidden_names_rejected_before_file_open(names):
    with pytest.raises(ValueError, match='PREDICTION_MEMBER_FORBIDDEN'):
        candidate.read_prediction_inputs('nonexistent.zip', names)


def test_wrong_size_rejected(tmp_path):
    path = tmp_path / 'wrong.zip'
    path.write_bytes(b'wrong')
    with pytest.raises(ValueError, match='ARCHIVE_SIZE_MISMATCH'):
        candidate.read_prediction_inputs(path, ['tokenizer.json'])


def test_same_size_changed_bytes_rejected(tmp_path):
    path = tmp_path / 'changed.zip'
    data = bytearray(ARCHIVE.read_bytes())
    data[-1] ^= 1
    path.write_bytes(data)
    with pytest.raises(ValueError, match='ARCHIVE_DIGEST_MISMATCH'):
        candidate.read_prediction_inputs(path, ['tokenizer.json'])


def test_all_four_checkpoints_are_read_as_bytes_only():
    result = candidate.read_prediction_inputs(ARCHIVE, sorted(candidate.CHECKPOINTS))
    assert set(result) == candidate.CHECKPOINTS
    assert all(isinstance(raw, bytes) and raw for raw in result.values())
    assert 'torch' not in sys.modules


def test_strict_json_rejects_duplicate_and_nonfinite():
    for raw in [b'{"a":1,"a":2}', b'{"a":NaN}']:
        with pytest.raises(ValueError): candidate._json(raw)
