"""Inspect retained scalar training history; never load a checkpoint."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_local_v3 import NoNeuralOrProviderImports
sys.meta_path.insert(0, NoNeuralOrProviderImports())
from cas_meta2.ablation_inputs_v4 import read_prediction_inputs

def digest(path):
    state = sha256()
    with path.open('rb') as stream:
        for raw in iter(lambda: stream.read(1024 * 1024), b''):
            state.update(raw)
    return state.hexdigest()

output = HERE / 'receipt.json'
if output.exists():
    raise RuntimeError('NEW_CURVE_RECEIPT_REQUIRED')
packet = ROOT / 'records/aws_learning_v3_001/cloud_artifacts.zip'
packet_sha = 'ebb76793a3897d70563be8cd2a857b0e24c82c4e412d3db66d80ac76345acaf2'
if digest(packet) != packet_sha:
    raise RuntimeError('ORIGINAL_PARTIAL_PACKET_CHANGED')
name = 'cloud_job/campaign/training_history.json'
with zipfile.ZipFile(packet) as archive:
    if archive.getinfo(name).file_size > 1024 * 1024:
        raise RuntimeError('HISTORY_SIZE_CEILING')
    raw = archive.read(name)
history = json.loads(raw)
if [row['epoch'] for row in history] != list(range(1, 61)):
    raise RuntimeError('INCOMPLETE_EPOCH_HISTORY')
training = json.loads(read_prediction_inputs(
    ROOT / 'records/decoder_ablation_inputs_v4_001/inputs.zip',
    ['training_receipt.json'])['training_receipt.json'])
curves = {}
for family in ('cas', 'generic'):
    selected = training['checkpoints'][family]['selected']
    if history[-1]['families'][family]['validation'] != selected['validation']:
        raise RuntimeError('FINAL_HISTORY_CHECKPOINT_METADATA_MISMATCH')
    rows, not_checked = [], []
    for epoch in history:
        values = epoch['families'][family]
        validation = values['validation']
        generation = validation.get('generation')
        if generation is None:
            not_checked.append(epoch['epoch'])
            continue
        rows.append({'epoch': epoch['epoch'], 'selected': values['selected'],
            'token_cross_entropy': validation['token_cross_entropy'],
            'joint_correct': generation['overall']['joint_correct'],
            'total': generation['overall']['total'],
            'by_depth': {depth: {'joint_correct': row['joint_correct'], 'total': row['total']}
                         for depth, row in generation['by_depth'].items()}})
    curves[family] = {'checked_generations': rows, 'generation_not_checked_epochs': not_checked}
record = {'schema': 'cas-meta2-preserved-learning-curve/0.1', 'completed': True,
    'original_partial_packet_sha256': packet_sha, 'history_sha256': sha256(raw).hexdigest(),
    'epochs': 60, 'curves': curves, 'final_checkpoint_metadata_matches': True,
    'neural_execution_performed': False, 'training_performed': False,
    'native_evaluation_performed': False, 'learning_accepted': False,
    'script_sha256': digest(Path(__file__)),
    'boundary': 'Retained metadata from an incompletely audited run, not a fresh evaluation. Unchecked generation epochs are missing measurements, not zero scores.'}
with output.open('x', encoding='utf-8') as stream:
    json.dump(record, stream, sort_keys=True, indent=2)
    stream.write('\n')
print(json.dumps({'completed': True, 'history_sha256': record['history_sha256'],
                  'last_three_checked': {family: values['checked_generations'][-3:]
                                         for family, values in curves.items()}}))
