"""Pure check that the proposed diagnostic uses exactly the recounted probe."""
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_local_v3 import NoNeuralOrProviderImports
sys.meta_path.insert(0, NoNeuralOrProviderImports())
from cas_meta2.fit_diagnostic_v5 import read_training, TRAIN_SHA

training = ROOT / 'records/decoder_dataset_reconstruction_v4_001/dataset/train.json'
previous = ROOT / 'records/training_probe_diagnosis_v5_001/receipt.json'
previous_raw = previous.read_bytes()
record = json.loads(previous_raw)
assert record['completed'] is True and record['recounted_files'] == 28
all_train, selected = read_training(training)
assert [task['task_id'] for task in selected] == record['task_ids']
assert len(all_train) == 3072 and len(selected) == 24
source = ROOT / 'cas_meta2/fit_diagnostic_v5.py'
receipt = {'schema': 'cas-meta2-fit-input-check/0.1', 'completed': True,
    'training_sha256': TRAIN_SHA, 'training_examples': len(all_train),
    'fit_examples': len(selected), 'task_ids': [t['task_id'] for t in selected],
    'prior_probe_receipt_sha256': sha256(previous_raw).hexdigest(),
    'diagnostic_source_sha256': sha256(source.read_bytes()).hexdigest(),
    'script_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
    'neural_execution': False, 'provider_calls': 0,
    'boundary': 'Known training input identity only; no fit result or new learning.'}
with (HERE / 'receipt.json').open('x', encoding='utf-8') as stream:
    json.dump(receipt, stream, sort_keys=True, indent=2)
    stream.write('\n')
print(json.dumps({'completed': True, 'fit_examples': len(selected), 'matches_prior_probe': True}))
