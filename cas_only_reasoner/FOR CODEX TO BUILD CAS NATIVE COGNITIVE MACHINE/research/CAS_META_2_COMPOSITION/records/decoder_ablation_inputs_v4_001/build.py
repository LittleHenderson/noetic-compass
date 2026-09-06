"""Create a retrospective decoder input artifact without loading any model."""
from hashlib import sha256
import json
from pathlib import Path
import zipfile

OUTPUT = Path(__file__).resolve().parent
ROOT = OUTPUT.parents[1]
PACKET_SHA = 'ebb76793a3897d70563be8cd2a857b0e24c82c4e412d3db66d80ac76345acaf2'
INSPECTION_SHA = '86fc7177a29b12836904174413f85f6f03f37ce31ac6a79e8469fa6f8b3fdfb7'
packet = ROOT / 'records/aws_learning_v3_001/cloud_artifacts.zip'
inspection_path = ROOT / 'records/aws_learning_v3_inspection_002/inspection_receipt.json'
raw = inspection_path.read_bytes()
assert sha256(raw).hexdigest() == INSPECTION_SHA
inspection = json.loads(raw)
assert inspection['packet_sha256'] == PACKET_SHA
assert inspection['archive_safety_and_all_included_bytes_checked'] is True
assert inspection['status'] == 'CAS_META_2_V3_PACKET_PARTIAL_EVIDENCE'
assert sha256(packet.read_bytes()).hexdigest() == PACKET_SHA
index_raw = Path(inspection['full_member_index']).read_bytes()
assert sha256(index_raw).hexdigest() == inspection['full_member_index_sha256']
index = {r['path']: r for r in json.loads(index_raw)['entries']}
names = ['candidate_' + family + '_' + state + '.pt'
         for family in ('cas','generic') for state in ('initial','best')]
names += ['tokenizer.json','checkpoints.json','training_receipt.json',
          'predictions.jsonl','predictions_seal.json','dataset/test_public.json',
          'dataset/test_private.json','dataset/dataset_manifest.json']
base = 'cloud_job/campaign/'
destination = OUTPUT / 'inputs.zip'
assert not destination.exists() and not (OUTPUT / 'receipt.json').exists()
members = {}
with zipfile.ZipFile(packet) as source, zipfile.ZipFile(destination,'x',zipfile.ZIP_DEFLATED) as target:
    for name in names:
        key = base + name
        entry = index[key]
        assert entry['bytes'] <= 16 * 1024**2
        data = source.read(key)
        assert len(data) == entry['bytes'] and sha256(data).hexdigest() == entry['sha256']
        target.writestr(name,data)
        members[name] = {'bytes':len(data),'sha256':entry['sha256'],'original_member':key}
    checkpoints = json.loads(source.read(base + 'checkpoints.json'))
    locations = {}
    for family in ('cas','generic'):
        for state, suffix in (('initial','initial'),('selected','best')):
            record = checkpoints[family][state]
            name = 'candidate_' + family + '_' + suffix + '.pt'
            assert members[name]['sha256'] == record['sha256'] and members[name]['bytes'] == record['bytes']
            locations[family + '_' + state] = {'member':name,'epoch':record['epoch'],
                'optimizer_steps':record['optimizer_steps'],'sha256':record['sha256']}
    publics = json.loads(source.read(base + 'dataset/test_public.json'))
    private = json.loads(source.read(base + 'dataset/test_private.json'))
    assert len(publics) == len(private) == 72
    assert all(public == task['public'] for public, task in zip(publics,private))
    manifest = {'schema':'cas-meta2-decoder-ablation-inputs/0.1',
        'source_packet_sha256':PACKET_SHA,'inspection_sha256':INSPECTION_SHA,
        'learning_source_sha':'ec9d161908ab4ed8a4fb300ca31cb089ac0c3b70',
        'purpose':'RETROSPECTIVE_DECODER_DIAGNOSTIC','task_count':72,
        'previously_exposed_test_data':True,'fresh_held_out_claim_permitted':False,
        'source_release_accepted':False,'model_deserialization_performed':False,
        'training_permitted':False,'members':members,'checkpoint_locations':locations,
        'prediction_rule':'Load public observations only into predictors. Seal all new predictions before the evaluation process opens private targets.'}
    manifest_raw = json.dumps(manifest,sort_keys=True,indent=2).encode() + b'\n'
    target.writestr('input_manifest.json',manifest_raw)
with zipfile.ZipFile(destination) as check:
    assert set(check.namelist()) == set(names) | {'input_manifest.json'}
    for name,row in members.items():
        assert sha256(check.read(name)).hexdigest() == row['sha256']
receipt = {'schema':'cas-meta2-decoder-ablation-input-build/0.1','archive':str(destination),
    'archive_sha256':sha256(destination.read_bytes()).hexdigest(),'archive_bytes':destination.stat().st_size,
    'input_manifest_sha256':sha256(manifest_raw).hexdigest(),'manifest':manifest,
    'builder_sha256':sha256(Path(__file__).read_bytes()).hexdigest(),
    'all_copied_bytes_rechecked':True,'neural_execution_performed':False,
    'provider_calls':0,'gpu_launched':False}
with (OUTPUT/'receipt.json').open('x',encoding='utf-8') as f:
    json.dump(receipt,f,indent=2,sort_keys=True); f.write('\n')
print(json.dumps({k:receipt[k] for k in ('archive_sha256','archive_bytes','all_copied_bytes_rechecked','gpu_launched')}))
