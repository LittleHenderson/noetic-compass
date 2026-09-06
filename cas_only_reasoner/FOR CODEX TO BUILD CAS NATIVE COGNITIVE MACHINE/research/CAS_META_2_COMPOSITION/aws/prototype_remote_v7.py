"""Source-bound AWS-only v7 coordinator. The campaign owns all phase deadlines.

This wrapper verifies saved evidence, not task answers or model tensors. Neither
a source package nor a GPU smoke pass accepts learning or permits promotion.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
PILOT = 'research/CAS_META_2_COMPOSITION'


def require(value,reason):
    if not value: raise ValueError(reason)


def require_request(job,max_seconds):
    require(sys.platform=='linux' and type(max_seconds) is int and max_seconds==6900,
        'V7_REMOTE_LINUX_FIXED_PARENT_TIME_REQUIRED')
    require(type(job) is str and re.fullmatch('cas-meta2-[0-9]{14}-[a-f0-9]{8}',job)
        and os.environ.get('CAS_META2_AWS_JOB_ID')==job and os.environ.get('CAS_META1_AWS_JOB_ID')==job
        and os.environ.get('CAS_META2_RUN_PROTOTYPE_TRAINING')=='1'
        and os.environ.get('CAS_META2_RUN_GPU_TESTS')=='1','V7_REMOTE_EXPLICIT_JOB_REQUIRED')


def regular(path):
    path=Path(path).absolute()
    require(path.is_file() and not any(p.is_symlink() or getattr(p,'is_junction',lambda:False)()
        for p in (path,*path.parents)),'V7_REMOTE_LINK_OR_MISSING_FILE')
    return path


def file_hash(path):
    with regular(path).open('rb') as stream:
        return __import__('hashlib').file_digest(stream,'sha256').hexdigest()


def read(path):
    path=regular(path)
    require(path.stat().st_size<=16*1024**2,'V7_REMOTE_JSON_SIZE_BOUND')
    def pairs(items):
        value={}
        for key,item in items:
            require(key not in value,'V7_REMOTE_DUPLICATE_JSON_FIELD');value[key]=item
        return value
    value=json.loads(path.read_bytes(),object_pairs_hook=pairs,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('V7_REMOTE_NONFINITE_JSON')))
    json.dumps(value,allow_nan=False)
    return value


def verify_sources(args):
    require_request(args.job,args.max_wall_seconds)
    package=ROOT.parents[1]
    require(Path(args.launch_manifest).absolute()==package/'launch_manifest.json'
        and type(args.launch_manifest_sha256) is str and re.fullmatch('[a-f0-9]{64}',args.launch_manifest_sha256)
        and file_hash(args.launch_manifest)==args.launch_manifest_sha256,'V7_REMOTE_EXTERNAL_MANIFEST_PIN_REQUIRED')
    manifest=read(args.launch_manifest)
    require(manifest.get('source_sha')==os.environ.get('CAS_META2_SOURCE_SHA')
        and re.fullmatch('[a-f0-9]{40}',manifest.get('source_sha',''))
        and manifest.get('schema_version')==2 and manifest.get('pilot_dir')==PILOT,'V7_REMOTE_SOURCE_IDENTITY')
    mapping=manifest['files_sha256'];aliases=set();total=0
    require(type(mapping) is dict and mapping,'V7_REMOTE_SOURCE_MAP_REQUIRED')
    for name,pin in mapping.items():
        require(type(name) is str and not name.startswith('/') and ':' not in name and '\\' not in name
            and all(part not in ('','.','..') for part in name.split('/'))
            and name.casefold() not in aliases,'V7_REMOTE_UNSAFE_SOURCE_PATH')
        aliases.add(name.casefold())
        path=regular(package/name);total+=path.stat().st_size
        require(total<=512*1024**2 and type(pin) is str and re.fullmatch('[a-f0-9]{64}',pin)
            and file_hash(path)==pin,'V7_REMOTE_SOURCE_BYTES_CHANGED:'+name)
    require(PILOT+'/aws/prototype_remote_v7.py' in mapping
        and PILOT+'/tools/experiment_profiles_prototype_v7.py' in mapping,'V7_REMOTE_SELF_AND_PROFILE_REQUIRED')
    # All source bytes, including this helper, are checked before project imports.
    profile_path=ROOT/'tools/experiment_profiles_prototype_v7.py'
    spec=importlib.util.spec_from_file_location('cas_meta2_v7_remote_profile',profile_path)
    profile=importlib.util.module_from_spec(spec);spec.loader.exec_module(profile)
    experiment=profile.validate_launch_manifest(manifest,lambda name:regular(package/name).read_bytes())
    registered=profile.validate_prototype_spec(regular(package/experiment['spec_path']).read_bytes())
    profile.require_execution_ready(registered)
    require(os.environ.get('CAS_META2_EXPERIMENT_PROFILE')==experiment['profile']
        and os.environ.get('CAS_META2_EXPERIMENT_ENTRYPOINT')==experiment['entrypoint']
        and os.environ.get('CAS_META2_EXPERIMENT_SPEC_SHA256')==experiment['spec_sha256'],
        'V7_REMOTE_EXPERIMENT_ENVIRONMENT_MISMATCH')
    return manifest,registered


def completed_evidence(output,*,job,experiment):
    output=Path(output)
    campaign=read(output/'campaign_receipt.json')
    require(campaign.get('schema')=='cas-meta2-prototype-campaign/7'
        and campaign.get('completed') is True and campaign.get('training_performed') is True
        and campaign.get('native_evaluation_completed') is True and campaign.get('learning_accepted') is False
        and campaign.get('release_accepted') is False and campaign.get('job')==job
        and campaign.get('experiment')==experiment,'V7_REMOTE_CAMPAIGN_COMPLETION_INVALID')
    assembly=read(output/'dataset_assembly_receipt.json')
    expected={'train':{'tasks':896,'depths':{'1':128,'2':384,'3':384}},
        'validation':{'tasks':96,'depths':{'1':32,'2':32,'3':32}},'test':{'tasks':72,'depths':{'3':48,'4':24}}}
    require(assembly.get('completed') is True and assembly.get('actual_splits')==expected
        and assembly.get('optimizer_steps_per_family')==11200,'V7_REMOTE_ASSEMBLED_COUNTS_INVALID')
    trained=read(output/'training/training_receipt.json')
    require(trained.get('schema')=='cas-meta2-contrast-training/7' and trained.get('completed') is True
        and trained.get('completed_epochs')==200 and trained.get('optimizer_steps')=={'cas':11200,'generic':11200}
        and trained.get('learning_accepted') is False,'V7_REMOTE_TRAINING_COUNTS_INVALID')
    native=read(output/'native/native_receipt.json')
    compact={key:native[key] for key in ('results','groups','cases','reference_cases','arm_verdicts')}
    compact.update(native_receipt_sha256=file_hash(output/'native/native_receipt.json'),
        evaluation_results_sha256=file_hash(output/'native/evaluation_results.json'))
    require(native.get('schema')=='cas-meta2-prototype-native-evaluation/7' and native.get('completed') is True
        and native.get('cases')==native.get('reference_cases')==72 and native.get('arm_verdicts')==360
        and native.get('learning_accepted') is False and campaign.get('native')==compact,
        'V7_REMOTE_NATIVE_DENOMINATORS_INVALID')
    smokes=list(output.rglob('gpu_smoke_receipt.json'))
    require(len(smokes)==1,'V7_REMOTE_EXACT_ONE_ACTUAL_SMOKE_RECEIPT_REQUIRED')
    smoke=read(smokes[0])
    require(smoke.get('schema')=='cas-meta2-prototype-gpu-preflight/7'
        and smoke.get('status')=='V7_KNOWN_FIXTURE_CUDA_FULL_PIPELINE_SMOKE_PASSED'
        and smoke.get('completed') is True and smoke.get('job')==job
        and smoke.get('native_evaluation_completed') is True and smoke.get('learning_accepted') is False
        and smoke.get('task_generation') is False and smoke.get('optimizer_steps')=={'cas':22,'generic':22}
        and smoke['native_receipt'].get('cases')==smoke['native_receipt'].get('reference_cases')==9
        and smoke['native_receipt'].get('arm_verdicts')==45
        and smoke['native_receipt']['results']['rule']['task_correct']==9,
        'V7_REMOTE_FULL_PIPELINE_SMOKE_REQUIRED')
    required=('campaign_receipt.json','payload_sha256.json','dataset_assembly_receipt.json','training_gate.json',
        'training/training_receipt.json','training/neural_predictions.jsonl','training/neural_predictions_seal.json',
        'native/native_receipt.json','native/evaluation_results.json')
    hashes={name:file_hash(output/name) for name in required}
    hashes[smokes[0].relative_to(output).as_posix()]=file_hash(smokes[0])
    return {'files_sha256':hashes,'train_examples':896,'validation_examples':96,'test_variants':72,
        'matched_test_triplets':24,'optimizer_steps_per_family':11200,'native_arm_verdicts':360,
        'known_fixture_smoke_reference_cases':9,'known_fixture_smoke_arm_verdicts':45}


def run(args):
    manifest,spec=verify_sources(args)
    output=Path(args.output).absolute()
    coordinator_path=output.parent/'prototype_coordinator_receipt.json'
    require('..' not in output.parts and output.resolve().is_relative_to(ROOT/'runs')
        and output.resolve()!=ROOT/'runs' and not output.exists() and not coordinator_path.exists()
        and not any(p.is_symlink() or getattr(p,'is_junction',lambda:False)() for p in (output,*output.parents)),
        'V7_REMOTE_NEW_OUTPUT_INSIDE_RUNS_REQUIRED')
    from cas_meta2.contrast_v7 import campaign
    started=time.monotonic()
    receipt={'schema':'cas-meta2-prototype-coordinator/7','job':args.job,'experiment':manifest['experiment'],
        'completed':False,'learning_accepted':False,'source_and_inputs_rechecked':False,
        'started_utc':datetime.now(timezone.utc).isoformat()}
    try:
        campaign.run(output,job=args.job,max_seconds=args.max_wall_seconds)
        checked=completed_evidence(output,job=args.job,experiment=manifest['experiment'])
        final,_=verify_sources(args)
        require(final==manifest and time.monotonic()-started<=args.max_wall_seconds,'V7_REMOTE_FINAL_SOURCE_OR_TIME_CHANGED')
        receipt.update(completed=True,source_and_inputs_rechecked=True,evidence=checked,
            source_sha=manifest['source_sha'],launch_manifest_sha256=args.launch_manifest_sha256)
    except BaseException as error:
        receipt['failure']={'type':type(error).__name__,'message':str(error),'traceback':traceback.format_exc()}
        raise
    finally:
        receipt['wall_seconds']=time.monotonic()-started
        receipt['finished_utc']=datetime.now(timezone.utc).isoformat()
        if output.is_dir():
            # The campaign has already sealed its own payload index. This
            # separate outer receipt belongs to the cloud collection instead.
            with coordinator_path.open('x',encoding='utf-8') as stream:
                json.dump(receipt,stream,sort_keys=True,indent=2,allow_nan=False);stream.write('\n')
    return receipt


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--job',required=True)
    parser.add_argument('--max-wall-seconds',required=True,type=int)
    parser.add_argument('--launch-manifest',required=True,type=Path)
    parser.add_argument('--launch-manifest-sha256',required=True)
    run(parser.parse_args(argv));return 0


if __name__=='__main__':
    raise SystemExit(main())
