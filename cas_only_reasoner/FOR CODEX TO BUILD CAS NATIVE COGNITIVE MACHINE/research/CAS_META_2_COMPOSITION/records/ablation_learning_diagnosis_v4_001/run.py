"""Pure analysis of preserved training metadata and the already-exposed dataset."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_local_v3 import NoNeuralOrProviderImports
sys.meta_path.insert(0, NoNeuralOrProviderImports())
from cas_meta2.ablation_inputs_v4 import read_prediction_inputs
from cas_meta2.ablation_campaign_v4 import check_dataset
from cas_meta2.ir import validate_program

output = HERE / 'receipt.json'
if output.exists():
    raise RuntimeError('NEW_DIAGNOSIS_RECEIPT_REQUIRED')
archive = ROOT / 'records/decoder_ablation_inputs_v4_001/inputs.zip'
raw = read_prediction_inputs(archive, ['training_receipt.json'])['training_receipt.json']
training = json.loads(raw)
data = ROOT / 'records/decoder_dataset_reconstruction_v4_001/dataset'
hashes = check_dataset(data)
structure = {}
for split, filename in [('train', 'train.json'), ('validation', 'validation.json'), ('test', 'test_private.json')]:
    tasks = json.loads((data / filename).read_bytes())
    strata, procedures, depths = Counter(), Counter(), Counter()
    for task in tasks:
        stats = validate_program(task['target']['program'])
        depth, count = stats['max_call_depth'], stats['procedure_count']
        if depth != task['provenance']['depth']:
            raise RuntimeError('RECORDED_DEPTH_DIFFERS_FROM_PROGRAM')
        strata[(depth, count)] += 1
        procedures[count] += 1
        depths[depth] += 1
    structure[split] = {'tasks': len(tasks),
        'depth_counts': dict(sorted(depths.items())), 'procedure_counts': dict(sorted(procedures.items())),
        'depth_and_procedure_counts': [{'depth': d, 'procedures': p, 'tasks': n}
                                     for (d, p), n in sorted(strata.items())]}
models = {}
for family in ('cas', 'generic'):
    selected = training['checkpoints'][family]['selected']
    validation = selected['validation']
    models[family] = {'selected_epoch': selected['epoch'], 'checkpoint_sha256': selected['sha256'],
        'teacher_forced_token_accuracy': validation['teacher_forced_token_accuracy'],
        'token_cross_entropy': validation['token_cross_entropy'],
        'generated_program_and_binding_by_depth': {
            depth: {key: values[key] for key in ('total', 'joint_correct', 'program_correct',
                                                'binding_correct', 'valid_programs')}
            for depth, values in validation['generation']['by_depth'].items()},
        'generated_overall': validation['generation']['overall'],
        'optimizer_steps': training['optimizer_steps'][family],
        'active_parameters': training['active_parameters'][family]['trainable_parameters']}
record = {'schema': 'cas-meta2-preserved-learning-diagnosis/0.1', 'completed': True,
    'training_receipt_sha256': sha256(raw).hexdigest(), 'dataset_sha256': hashes,
    'models': models, 'structure': structure,
    'script_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
    'validator_sha256': sha256((ROOT / 'cas_meta2/ir.py').read_bytes()).hexdigest(),
    'neural_execution_performed': False, 'training_performed': False,
    'native_evaluation_performed': False, 'learning_accepted': False,
    'boundary': 'Preserved metadata from an incompletely audited training run and structural counts of an already-exposed test set. Not a fresh evaluation or a causal diagnosis.'}
with output.open('x', encoding='utf-8') as stream:
    json.dump(record, stream, sort_keys=True, indent=2)
    stream.write('\n')
print(json.dumps(record))
