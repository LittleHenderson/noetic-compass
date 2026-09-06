"""Offline recorded-result review. Never loads tensors or calls a provider."""
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
SOURCE = 'acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0'
SOURCE_HASH = '3153318664641ea3affdbef306929c3113bb937cd04113bce41d02f736e0f1f1'
JOB = 'cas-meta2-20260906064703-c0d74ffa'
SOURCE_ZIP = ROOT/'records/aws_contrast_v6_source_001'
PACKET = ROOT/'records/aws_contrast_v6_001/cloud_artifacts.zip'
BASE = 'cloud_job/campaign/'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        require(fullname.split('.')[0] not in {
            'torch', 'casformer', 'cas_cjt', 'tensorflow', 'jax', 'cupy', 'boto3', 'botocore'
        }, 'LOCAL_NEURAL_OR_PROVIDER_IMPORT_REFUSED')


def digest(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)()
                    for p in (path, *path.parents)), 'LINK_REFUSED')
    result = sha256()
    with path.open('rb') as stream:
        for raw in iter(lambda: stream.read(1024**2), b''):
            result.update(raw)
    return result.hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def review(expected_hash):
    require(len(expected_hash) == 64 and all(c in '0123456789abcdef' for c in expected_hash),
            'EXACT_PACKET_HASH_REQUIRED')
    require(digest(PACKET) == expected_hash and digest(SOURCE_ZIP) == SOURCE_HASH,
            'EXTERNAL_ARCHIVE_HASH_MISMATCH')
    repo = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=ROOT, text=True).strip())
    for relative in ('aws/launch_contrast_v6.py', 'aws/budget.py',
                     'tools/experiment_profiles_contrast_v6.py',
                     'tools/build_launch_bundle_contrast_v6.py',
                     'aws/launch_plan.json', 'requirements-gpu.txt'):
        path = ROOT/relative
        raw = subprocess.check_output(['git', 'cat-file', 'blob',
            SOURCE+':'+path.relative_to(repo).as_posix()], cwd=repo)
        require(digest(path) == sha256(raw).hexdigest(), 'PREIMPORT_SOURCE_MISMATCH:'+relative)
    launch = load('contrast_review_launch', ROOT/'aws/launch_contrast_v6.py')
    manifest = launch.validate_archive(SOURCE_ZIP, SOURCE_HASH, SOURCE,
                                      json.loads(launch.PLAN_FILE.read_bytes()))
    launch.verify_launcher_identity(manifest)
    # Check every helper and input against the frozen package before importing it.
    for relative, checksum in manifest['files_sha256'].items():
        require(digest(ROOT.parent.parent/relative) == checksum, 'LOCAL_SOURCE_MISMATCH:'+relative)
    helper = load('contrast_review_archive', ROOT/'tools/inspect_cloud_packet.py')
    xml = load('contrast_review_xml', ROOT/'tools/inspect_ablation_packet_v5.py')
    extraction = ROOT/'records/aws_contrast_v6_001_review_extracted'
    require(not extraction.exists(), 'NEW_EXTRACTION_REQUIRED')
    with zipfile.ZipFile(PACKET) as archive:
        infos, expanded = helper._safe_infos(archive)
        inventory = []
        for name, info in sorted(infos.items()):
            if info.is_dir():
                continue
            state, count = sha256(), 0
            with archive.open(info) as stream:
                for raw in iter(lambda: stream.read(1024**2), b''):
                    count += len(raw)
                    require(count <= info.file_size, 'MEMBER_SIZE_EXCEEDED')
                    state.update(raw)
            require(count == info.file_size, 'MEMBER_SIZE_MISMATCH')
            inventory.append({'path': name, 'bytes': count, 'sha256': state.hexdigest()})
        packet = helper.Packet(archive, infos, inventory)
        collection, full_index = helper._collection(packet, JOB, SOURCE, SOURCE_HASH)
        require(full_index and collection['returncode'] == 0
                and collection['partial_evidence'] is False
                and collection.get('experiment') == manifest['experiment'], 'COMPLETE_BOUND_PACKET_REQUIRED')
        campaign = packet.json(BASE+'campaign_receipt.json')
        require(campaign.get('schema') == 'cas-meta2-contrast-campaign/6'
                and campaign.get('job') == JOB and campaign.get('experiment') == manifest['experiment']
                and all(campaign.get(key) is True for key in
                        ('completed', 'training_performed', 'native_evaluation_completed'))
                and all(campaign.get(key) is False for key in
                        ('learning_accepted', 'release_accepted', 'automatic_retry')),
                'COMPLETED_CANDIDATE_CAMPAIGN_REQUIRED')
        from cas_meta2.contrast_v6 import train, curriculum, data, checks
        from cas_meta2.contrast_v6.campaign import configurations, check_native_output
        require(campaign['source_sha256'] == train.source_identity(), 'SOURCE_MAPPING_MISMATCH')
        baseline = campaign['baseline_before']
        require(baseline['source'] == {'baseline_sha': manifest['baseline_sha'], 'files_verified': 316},
                'BASELINE_IDENTITY_MISMATCH')
        require({v['wheel_sha256'] for v in baseline['installed_wheels'].values()}
                == {manifest['files_sha256'][p] for p in manifest['wheel_paths']}, 'WHEEL_IDENTITY_MISMATCH')
        payload = packet.json(BASE+'payload_sha256.json')
        require(payload == {r['path'].removeprefix(BASE): r['sha256'] for r in inventory
                            if r['path'].startswith(BASE) and r['path'] != BASE+'payload_sha256.json'},
                'FULL_PAYLOAD_INDEX_MISMATCH')
        gpu = {'native': xml.xml_passes(packet, 'cloud_job/gpu_contract_tests.xml', 4),
               'policy': xml.xml_passes(packet, 'cloud_job/gpu_policy_tests.xml', 27),
               'contrast_pipeline': xml.xml_passes(packet, BASE+'gpu_test.xml', 1)}
        runtime = packet.json('cloud_job/runtime.json')
        require(runtime.get('cuda_matmul_passed') is True and runtime.get('torch') == '2.11.0+cu128'
                and runtime.get('cuda') == '12.8' and 'RTX PRO 4500' in runtime.get('gpu', ''),
                'CUDA_ENVIRONMENT_MISMATCH')
        helper._extract(packet, extraction)
    output = extraction/'cloud_job/campaign'
    spec = checks.read(ROOT/'EXPERIMENT_CONTRAST_V6.json')
    require(checks.read(output/'experiment.json') == spec, 'REGISTERED_EXPERIMENT_MISMATCH')
    cfg, training = configurations(spec)
    excluded = train.registered_exclusions(ROOT/'records/contrast_v6_exclusions_001/inventory.json')
    initial = checks.read(output/'initial_identity.json')
    require(initial == {'source_sha256': campaign['source_sha256'],
                        'baseline': baseline, 'experiment': manifest['experiment']}, 'INITIAL_IDENTITY_MISMATCH')
    pin = checks.file_hash(output/'dataset/manifest.json')
    remote_root = '/opt/cas-meta2/package/'+manifest['pilot_dir']
    remote_output = remote_root+'/runs/cloud_job/campaign'
    command = ['/opt/cas-meta2/venv/bin/python', '-B', '-m', 'cas_meta2.contrast_v6.train',
               '--bundle', remote_output+'/trainer_input', '--output', remote_output+'/training',
               '--job', JOB, '--manifest-sha256', pin, '--curriculum-seed', str(spec['curriculum_seed']),
               '--curriculum-config', remote_output+'/curriculum_config.json',
               '--training-config', remote_output+'/training_config.json',
               '--exclusions', remote_root+'/records/contrast_v6_exclusions_001/inventory.json']
    gate = checks.check_training(output/'training', output/'processes/training/process_receipt.json',
        output/'trainer_input', expected_command=command, job=JOB, expected_manifest_sha256=pin,
        curriculum_seed=spec['curriculum_seed'], curriculum_config=cfg, excluded=excluded,
        config=training, expected_source=campaign['source_sha256'], expected_baseline=baseline)
    require(gate == checks.read(output/'training_gate.json'), 'RECORDED_TRAINING_GATE_MISMATCH')
    native = check_native_output(output, spec['test_count'])
    require(native == campaign['native'], 'NATIVE_SUMMARY_RECOUNT_MISMATCH')
    require(digest(PACKET) == expected_hash and digest(SOURCE_ZIP) == SOURCE_HASH, 'ARCHIVE_CHANGED')
    receipt = checks.read(output/'training/training_receipt.json')
    return {'schema': 'cas-meta2-offline-contrast-review/6',
        'status': 'RECORDED_CONTRAST_RECOUNT_PASSED', 'job': JOB,
        'source_sha': SOURCE, 'source_archive_sha256': SOURCE_HASH, 'packet_sha256': expected_hash,
        'source_files_verified': len(manifest['files_sha256']), 'expanded_bytes': expanded,
        'gpu_tests': gpu, 'runtime': runtime, 'training_gate': gate, 'native_summary': native,
        'history': receipt['history'], 'optimizer_steps': receipt['optimizer_steps'],
        'inventory': inventory, 'script_sha256': digest(__file__),
        'utc': datetime.now(timezone.utc).isoformat(), 'neural_execution': False,
        'provider_calls': False, 'learning_accepted': False,
        'boundary': 'Offline saved-action, selection, checkpoint-byte and summary recount. '
                    'Not independent neural replay or native stored-trace semantic audit.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    sys.meta_path.insert(0, Guard())
    sys.path.insert(0, str(ROOT))
    output = HERE/'receipt.json'
    require(not output.exists(), 'NEW_REVIEW_RECEIPT_REQUIRED')
    result = review(args.sha256)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({k: result[k] for k in
        ('status', 'source_files_verified', 'optimizer_steps', 'native_summary')}, indent=2))
