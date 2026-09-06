"""Pure sealing and ordering tests, with simulated processes, not AWS claims."""
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import pytest
from cas_meta2 import ablation_campaign_v4 as candidate
from cas_meta2.ablation_predict_v4 import prediction_rows, write_json

pytestmark = pytest.mark.not_gpu
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'records/decoder_dataset_reconstruction_v4_001/dataset'
ARCHIVE = ROOT / 'records/decoder_ablation_inputs_v4_001/inputs.zip'
JOB = 'cas-meta2-20260906000000-12345678'


def saved_prediction(output):
    (output / 'processes/prediction').mkdir(parents=True)
    write_json(output / 'processes/prediction/process_receipt.json',
               {'completed': True, 'returncode': 0, 'timed_out': False, 'pid': 123})
    publics = json.loads((output / 'dataset/test_public.json').read_bytes())
    rows = prediction_rows(publics, {arm: [{'status': 'REJECTED'}] * 72 for arm in candidate.ARMS})
    raw = b''.join(json.dumps(row, sort_keys=True).encode() + b'\n' for row in rows)
    seals = {}
    for mode in candidate.MODES:
        directory = output / 'prediction' / mode
        directory.mkdir(parents=True)
        (directory / 'predictions.jsonl').write_bytes(raw)
        seal = {'schema': 'cas-meta2-prediction-seal/1', 'arms': list(candidate.ARMS),
            'test_examples': 72, 'prediction_count': 360, 'test_private_labels_loaded': False,
            'test_public_sha256': candidate.PUBLIC_SHA, 'test_private_sha256': candidate.PRIVATE_SHA,
            'sha256': sha256(raw).hexdigest()}
        write_json(directory / 'predictions_seal.json', seal)
        seals[mode] = seal
    write_json(output / 'prediction/prediction_receipt.json', {
        'schema': 'cas-meta2-retrospective-prediction/0.1', 'completed': True, 'job': JOB,
        'training_performed': False, 'native_evaluation_completed': False,
        'fresh_held_out_claim_permitted': False, 'seals': seals})


@pytest.fixture
def saved(tmp_path):
    shutil.copytree(DATA, tmp_path / 'dataset')
    saved_prediction(tmp_path)
    return tmp_path


def test_unchanged_dataset_reconstruction_matches():
    assert candidate.check_dataset(DATA) == candidate.DATA_HASHES


def test_both_complete_seals_and_exit_required(saved):
    result = candidate.check_prediction_exit(saved, JOB)
    assert result['prediction_pid'] == 123 and set(result['seals']) == set(candidate.MODES)
    assert 'torch' not in sys.modules


@pytest.mark.parametrize('field,value', [('completed', False), ('returncode', 1),
    ('returncode', False), ('timed_out', True), ('pid', 0)])
def test_failed_exit_blocks_even_with_complete_seals(saved, field, value):
    path = saved / 'processes/prediction/process_receipt.json'
    record = json.loads(path.read_bytes())
    record[field] = value
    path.write_text(json.dumps(record))
    with pytest.raises(RuntimeError, match='SUCCESSFUL_PREDICTION_EXIT'):
        candidate.check_prediction_exit(saved, JOB)


def test_changed_second_mode_blocks(saved):
    (saved / 'prediction/viability_v4/predictions.jsonl').write_bytes(b'{}\n')
    with pytest.raises(RuntimeError, match='BOTH_COMPLETE_SEALS'):
        candidate.check_prediction_exit(saved, JOB)


def test_wrong_job_blocks(saved):
    with pytest.raises(RuntimeError, match='RECEIPT_INVALID'):
        candidate.check_prediction_exit(saved, JOB + 'wrong')


def test_unauthorized_parent_stops_before_neural_import(monkeypatch):
    monkeypatch.delenv('CAS_META2_RUN_DECODER_ABLATION', raising=False)
    with pytest.raises(RuntimeError, match='EXPLICIT_AWS'):
        candidate.run('missing', 'missing', job=JOB)
    assert 'torch' not in sys.modules


@pytest.mark.parametrize('fail_prediction,fail_index', [(False, False), (True, False), (False, True)])
def test_simulated_parent_order_and_failures(tmp_path, monkeypatch, fail_prediction, fail_index):
    from cas_meta2 import campaign_v3 as frozen
    calls = []
    output = tmp_path / 'campaign'
    monkeypatch.setattr(candidate, 'require_request', lambda *args: None)
    monkeypatch.setattr(candidate.signal, 'SIGALRM', 14, raising=False)
    monkeypatch.setattr(candidate.signal, 'getsignal', lambda *args: None)
    monkeypatch.setattr(candidate.signal, 'signal', lambda *args: None)
    monkeypatch.setattr(candidate.signal, 'setitimer', lambda *args: None, raising=False)
    monkeypatch.setattr(candidate.signal, 'ITIMER_REAL', 0, raising=False)
    def new_output(path):
        path.mkdir()
        return path
    monkeypatch.setattr(frozen, '_new_output', new_output)
    monkeypatch.setattr(frozen, '_source_identity', lambda: {'mock': 'unchanged'})
    monkeypatch.setattr(frozen, '_baseline_identity', lambda: {'mock': 'unchanged'})
    def construct(output, seed, deadline):
        assert seed == 20260919
        calls.append('dataset')
        shutil.copytree(DATA, output / 'dataset')
        return output / 'dataset'
    monkeypatch.setattr(frozen, '_construct_data', construct)
    monkeypatch.setattr(frozen, '_xml_receipt', lambda *args: {'simulated': True})
    def process(command, directory, deadline, environment=None):
        name = directory.name
        calls.append(name)
        if name == 'prediction':
            saved_prediction(output)
            if fail_prediction:
                raise RuntimeError('simulated child failure after files were written')
        if name.startswith('evaluate_'):
            assert (output / 'prediction_gate.json').is_file()
            mode = name.removeprefix('evaluate_')
            write_json(output / 'prediction' / mode / 'native_receipt.json',
                       {'cases': 72, 'arm_verdicts': 360, 'simulated': True})
        return {'completed': True, 'returncode': 0, 'simulated': True}
    monkeypatch.setattr(frozen, '_run_process', process)
    def index(output):
        if fail_index: raise RuntimeError('simulated unsafe output link')
        return 'simulated'
    monkeypatch.setattr(frozen, '_final_payload_index', index)
    if fail_index:
        with pytest.raises(RuntimeError, match='unsafe output link'):
            candidate.run(ARCHIVE, output, job=JOB)
        result = json.loads((output / 'campaign_receipt.json').read_bytes())
        assert result['completed'] is False and result['stage'] == 'final_evidence'
    else:
        result = candidate.run(ARCHIVE, output, job=JOB)
        assert result['completed'] is not fail_prediction
    if fail_prediction:
        assert not any(name.startswith('evaluate_') for name in calls)
        assert not (output / 'prediction_gate.json').exists()
    else:
        assert calls == ['dataset', 'runtime', 'gpu_contracts', 'prediction',
                         'evaluate_v3', 'evaluate_viability_v4']
