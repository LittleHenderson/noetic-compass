"""Recount preserved training probes without model loading or new evaluation."""
from hashlib import file_digest, sha256
import json
from pathlib import Path
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_local_v3 import NoNeuralOrProviderImports
sys.meta_path.insert(0, NoNeuralOrProviderImports())
from cas_meta2.selection_v3 import depth_generated_metrics


def digest(path):
    with path.open('rb') as stream:
        return file_digest(stream, 'sha256').hexdigest()


packet = ROOT / 'records/aws_learning_v3_001/cloud_artifacts.zip'
packet_sha = 'ebb76793a3897d70563be8cd2a857b0e24c82c4e412d3db66d80ac76345acaf2'
train_path = ROOT / 'records/decoder_dataset_reconstruction_v4_001/dataset/train.json'
train_sha = '579a1bfdda64702b4357f57b75c9c9b6e0710a9262c1da41d5aeec1ca1404359'
assert digest(packet) == packet_sha and digest(train_path) == train_sha
train = json.loads(train_path.read_bytes())
assert len(train) == 3072
by_id = {task['task_id']: task for task in train}
assert len(by_id) == len(train)
source_files = [ROOT / 'cas_meta2' / name for name in
                ('selection_v3.py', 'selection_v2.py', 'codec.py', 'ir.py')]
source_before = {str(path): digest(path) for path in source_files}
record = {'schema': 'cas-meta2-training-probe-diagnosis/0.1',
    'original_partial_packet_sha256': packet_sha, 'training_data_sha256': train_sha,
    'source_sha256': source_before, 'script_sha256': digest(Path(__file__)),
    'checkpoint_loading': False, 'neural_execution': False, 'new_training': False,
    'fresh_evaluation': False, 'learning_accepted': False, 'files': {}, 'curves': {}}
epochs = (0, 1, *range(5, 61, 5))
shared_ids = None
with zipfile.ZipFile(packet) as archive:
    for family in ('cas', 'generic'):
        rows = []
        for epoch in epochs:
            name = f'cloud_job/campaign/train_probe_predictions/{family}_epoch_{epoch:04d}.json'
            assert archive.getinfo(name).file_size < 2 * 1024 * 1024
            raw = archive.read(name)
            probe = json.loads(raw)
            assert probe['epoch'] == epoch and probe['split'] == 'train'
            assert probe['used_for_checkpoint_selection'] is False
            ids = probe['task_ids']
            assert len(ids) == len(set(ids)) == 24 and all(name in by_id for name in ids)
            if shared_ids is None:
                shared_ids = ids
            assert ids == shared_ids
            tasks = [by_id[name] for name in ids]
            actual = depth_generated_metrics(probe['actions'], tasks)
            assert actual == probe['metrics']
            assert all(group['total'] == 8 for group in actual['by_depth'].values())
            record['files'][name] = sha256(raw).hexdigest()
            rows.append({'epoch': epoch, 'joint_correct': actual['overall']['joint_correct'],
                         'total': 24, 'by_depth': {d: {'joint_correct': v['joint_correct'],
                         'total': v['total']} for d, v in actual['by_depth'].items()}})
        record['curves'][family] = rows
assert digest(packet) == packet_sha and digest(train_path) == train_sha
assert all(digest(Path(path)) == value for path, value in source_before.items())
assert digest(Path(__file__)) == record['script_sha256']
record.update(completed=True, recounted_files=len(record['files']), task_ids=shared_ids,
    boundary='Fixed 24-example training probe from an incompletely audited old run. '
             'Recounted with preserved scoring code; not independent neural execution, '
             'not representative full-training accuracy and not native task correctness.')
with (HERE / 'receipt.json').open('x', encoding='utf-8') as stream:
    json.dump(record, stream, sort_keys=True, indent=2)
    stream.write('\n')
print(json.dumps({'completed': True, 'recounted_files': record['recounted_files'],
                  'last_three': {family: rows[-3:] for family, rows in record['curves'].items()}}))
