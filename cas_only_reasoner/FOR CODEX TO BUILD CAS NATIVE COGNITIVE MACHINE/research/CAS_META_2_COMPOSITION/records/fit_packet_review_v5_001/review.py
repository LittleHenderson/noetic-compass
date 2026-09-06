"""Source-bound offline review of one completed fit packet; never load tensors."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.abc
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = '6a71e01c3689a1debe56eed842f101dfa4990556'
SOURCE_HASH = '17cdaaf25a9d07439598bf24ab9105193da1a15614fe9b41a2ba037a49849d4b'
JOB = 'cas-meta2-20260906054131-feae01a9'
SOURCE_ZIP = ROOT / 'records/aws_fit_v5_source_002/source.zip'
PACKET = ROOT / 'records/aws_fit_v5_001/cloud_artifacts.zip'
BASE = 'cloud_job/campaign/'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        require(fullname.split('.')[0] not in {'torch','casformer','cas_cjt','tensorflow',
                'jax','cupy','boto3','botocore'}, 'LOCAL_NEURAL_OR_PROVIDER_IMPORT_REFUSED')


def digest(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() or getattr(p, 'is_junction', lambda:False)()
                    for p in (path, *path.parents)), 'LINK_REFUSED')
    value = sha256()
    with path.open('rb') as stream:
        for raw in iter(lambda:stream.read(1024*1024), b''):
            value.update(raw)
    return value.hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def review(expected_hash):
    require(len(expected_hash) == 64 and all(c in '0123456789abcdef' for c in expected_hash), 'EXACT_PACKET_HASH_REQUIRED')
    require(digest(PACKET) == expected_hash and digest(SOURCE_ZIP) == SOURCE_HASH, 'EXTERNAL_ARCHIVE_HASH_MISMATCH')
    repo = Path(subprocess.check_output(['git','rev-parse','--show-toplevel'], cwd=ROOT, text=True).strip())
    preimport = ('aws/launch_fit_v5.py','aws/budget.py','tools/experiment_profiles_fit_v5.py',
                 'tools/build_launch_bundle_fit_v5.py','aws/launch_plan.json','requirements-gpu.txt')
    for relative in preimport:
        path = ROOT / relative
        raw = subprocess.check_output(['git','show',SOURCE + ':' + path.relative_to(repo).as_posix()], cwd=repo)
        require(digest(path) == sha256(raw).hexdigest(), 'PREIMPORT_SOURCE_MISMATCH')
    launch = load('fit_review_launch', ROOT / 'aws/launch_fit_v5.py')
    plan = json.loads(launch.PLAN_FILE.read_bytes())
    manifest = launch.validate_archive(SOURCE_ZIP, SOURCE_HASH, SOURCE, plan)
    identity = launch.verify_launcher_identity(manifest)
    helper = load('fit_review_archive', ROOT / 'tools/inspect_cloud_packet.py')
    xml = load('fit_review_xml', ROOT / 'tools/inspect_ablation_packet_v5.py')
    extraction = ROOT / 'records/aws_fit_v5_001_review_extracted'
    require(not extraction.exists(), 'NEW_EXTRACTION_REQUIRED')
    with zipfile.ZipFile(PACKET) as archive:
        infos, expanded = helper._safe_infos(archive)
        inventory = []
        for name, info in sorted(infos.items()):
            if info.is_dir():
                continue
            state, count = sha256(), 0
            with archive.open(info) as stream:
                for raw in iter(lambda:stream.read(1024*1024), b''):
                    count += len(raw)
                    require(count <= info.file_size, 'MEMBER_SIZE_EXCEEDED')
                    state.update(raw)
            require(count == info.file_size, 'MEMBER_SIZE_MISMATCH')
            inventory.append({'path':name,'bytes':count,'sha256':state.hexdigest()})
        packet = helper.Packet(archive, infos, inventory)
        collection, full_index = helper._collection(packet, JOB, SOURCE, SOURCE_HASH)
        require(full_index and collection['returncode'] == 0 and collection['partial_evidence'] is False
                and collection.get('experiment') == manifest['experiment'], 'COMPLETE_BOUND_FIT_PACKET_REQUIRED')
        campaign = packet.json(BASE + 'campaign_receipt.json')
        require(campaign.get('schema') == 'cas-meta2-fit-campaign/0.1'
                and campaign.get('job') == JOB and campaign.get('experiment') == manifest['experiment']
                and campaign.get('completed') is True and campaign.get('training_performed') is True,
                'COMPLETED_FIT_CAMPAIGN_REQUIRED')
        for key in ('native_evaluation_completed','fresh_held_out_claim_permitted','learning_accepted','release_accepted'):
            require(campaign.get(key) is False, 'FIT_CLAIM_BOUNDARY_CHANGED:' + key)
        require(campaign['baseline_before'] == campaign['baseline_after'], 'BASELINE_CHANGED')
        require(campaign['baseline_before']['source'] == {'baseline_sha':manifest['baseline_sha'], 'files_verified':316},
                'BASELINE_COUNT_OR_SOURCE_CHANGED')
        require({v['wheel_sha256'] for v in campaign['baseline_before']['installed_wheels'].values()}
                == {manifest['files_sha256'][p] for p in manifest['wheel_paths']}, 'FROZEN_WHEELS_CHANGED')
        for relative, checksum in campaign['source_sha256'].items():
            require(manifest['files_sha256']['research/CAS_META_2_COMPOSITION/' + relative] == checksum,
                    'CAMPAIGN_SOURCE_MISMATCH')
        from cas_meta2.campaign_v3 import _source_identity
        require(campaign['source_sha256'] == _source_identity(), 'COMPLETE_CAMPAIGN_SOURCE_MAP_REQUIRED')
        payload = packet.json(BASE + 'payload_sha256.json')
        require(payload == {r['path'].removeprefix(BASE):r['sha256'] for r in inventory
                            if r['path'].startswith(BASE) and r['path'] != BASE + 'payload_sha256.json'},
                'FULL_PAYLOAD_INDEX_MISMATCH')
        gpu = {'native':xml.xml_passes(packet,'cloud_job/gpu_contract_tests.xml',4),
               'policy':xml.xml_passes(packet,'cloud_job/gpu_policy_tests.xml',27),
               'fit':xml.xml_passes(packet,BASE + 'gpu_tests.xml',2)}
        runtime = packet.json('cloud_job/runtime.json')
        require(runtime.get('cuda_matmul_passed') is True and runtime.get('torch') == '2.11.0+cu128'
                and runtime.get('cuda') == '12.8' and 'RTX PRO 4500' in runtime.get('gpu',''), 'CUDA_ENVIRONMENT_MISMATCH')
        extracted = helper._extract(packet, extraction)
    from cas_meta2.fit_diagnostic_v5 import read_training
    from cas_meta2.fit_campaign_v5 import check_fit
    _, tasks = read_training(ROOT / 'records/decoder_dataset_reconstruction_v4_001/dataset/train.json')
    recount = check_fit(extraction / 'cloud_job/campaign', JOB, [t['task_id'] for t in tasks])
    require(recount == campaign['fit'], 'PARENT_FIT_RECOUNT_MISMATCH')
    require(digest(PACKET) == expected_hash and digest(SOURCE_ZIP) == SOURCE_HASH, 'ARCHIVE_CHANGED_DURING_REVIEW')
    for relative, checksum in manifest['files_sha256'].items():
        require(digest(ROOT.parent.parent / relative) == checksum, 'SOURCE_CHANGED_DURING_REVIEW')
    worker = json.loads((extraction / 'cloud_job/campaign/fit/fit_receipt.json').read_bytes())
    return {'schema':'cas-meta2-offline-fit-review/0.1','status':'RECORDED_FIT_RECOUNT_PASSED',
            'source_sha':SOURCE,'source_archive_sha256':SOURCE_HASH,'packet_sha256':expected_hash,
            'job':JOB,'source_files_verified':len(identity),'full_index_verified':full_index,
            'expanded_bytes':expanded,'extraction':extracted,'gpu_tests':gpu,'runtime':runtime,
            'recount':recount,'history':worker['history'],'optimizer_steps':worker['optimizer_steps'],
            'inventory':inventory,'script_sha256':digest(Path(__file__)),
            'utc':datetime.now(timezone.utc).isoformat(), 'neural_execution':False,'provider_calls':False,
            'learning_accepted':False,'fresh_held_out_evaluation':False,
            'boundary':'Offline byte checks and repeated frozen generation-score checks. No checkpoint loading, independent neural replay, teacher-forced-logit recount, native answer verification, or skill promotion.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    sys.meta_path.insert(0, Guard())
    sys.path.insert(0, str(ROOT))
    output = HERE / 'receipt.json'
    require(not output.exists(), 'NEW_REVIEW_RECEIPT_REQUIRED')
    result = review(args.sha256)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({k:result[k] for k in ('status','source_files_verified','optimizer_steps','recount')},indent=2))
