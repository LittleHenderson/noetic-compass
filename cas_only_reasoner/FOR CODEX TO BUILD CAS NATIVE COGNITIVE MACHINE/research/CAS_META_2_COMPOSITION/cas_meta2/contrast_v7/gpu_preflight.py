"""AWS-only v7 smoke workflow over a saved fixture; imports remain pure.

The portable parent runs in its own process and exits before training starts.
Its permanent neural-import hooks cannot leak into the trainer or coordinator.
Native coverage is unavailable until its source-bound readiness flag is closed.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'cas-meta2-prototype-gpu-preflight/7'
SEED = 926603
CONFIG = {'train_flat':32,'train_pairs_per_cell':8,'validation_flat':8,'validation_pairs_per_cell':2,'test_triplets':3}
EXPECTED_SPLITS = {'train':{'tasks':352,'depths':{'1':32,'2':160,'3':160}},
                   'validation':{'tasks':24,'depths':{'1':8,'2':8,'3':8}},
                   'test':{'tasks':9,'depths':{'3':6,'4':3}}}
PINS_PATH = 'records/contrast_v7_bridge_checks_001/source_pins.json'
PINS_SHA256 = '9d66a81fbdc0e4041cd09d460c821f3cf68e244610ed49831324b5accf74084d'
LOADER_SHA256 = '5db831d685b2343a16b93cbc3d3c16e53978ebf0e3cf9da8fefd7d10692708b0'
FIXTURE = 'records/contrast_v6_bundle_probe_001/dataset'
FIXTURE_PINS = {
    'manifest.json':'36e57983fd43ac9650e5946d5fd04ca0888e9013131fc450f8d9f8f3c84131a1',
    'train.json':'e9032b27ac10364120e7eb7a8844eb43da40985a42cc6ab0629c88f874ae8a17',
    'validation.json':'26869a0c61007185e9fb76445297b2b231ff107ff15ad9a37fd7288bc855549d',
    'test_public.json':'cfec9cdbd9519887b9b08b7349d0bc264d1b327bb1efc89d9325eb7a57535e6a',
    'test_private.json':'8c62b9d591fd5f1ad6c8d2ed598315f91b9183d2e480709a0f12241ba0b49fff',
}
PUBLIC_FILES = {'train.json','validation.json','test_public.json','base_train.json',
                'base_manifest.json','training_imports.json','tokenizer.json','manifest.json'}
GPU_TEST = 'test_saved_fixture_exact_append_and_matched_cuda_training_exit'
NATIVE_GATE_READY = False
FORBIDDEN = {'torch','casformer','cas_cjt','tensorflow','jax','cupy','boto3','botocore'}


def require(value, code):
    if not value:
        raise ValueError(code)


def require_request(job):
    require(sys.platform == 'linux'
        and os.environ.get('CAS_META2_RUN_PROTOTYPE_TRAINING') == '1'
        and os.environ.get('CAS_META2_RUN_GPU_TESTS') == '1', 'V7_GPU_AWS_LINUX_EXPLICIT_ENABLE_REQUIRED')
    require(type(job) is str and re.fullmatch(r'cas-meta2-\d{14}-[a-f0-9]{8}', job)
        and os.environ.get('CAS_META2_AWS_JOB_ID') == job, 'V7_GPU_MATCHED_AWS_JOB_REQUIRED')


def no_links(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() or getattr(p,'is_junction',lambda:False)() for p in (path,*path.parents)),
            'V7_GPU_LINK_REFUSED')
    return path


def run_path(path, *, new=False):
    path = no_links(path)
    require('..' not in path.parts and path.resolve().is_relative_to((ROOT/'runs').resolve())
            and path.resolve() != (ROOT/'runs').resolve() and (not new or not path.exists()),
            'V7_GPU_RUN_OUTPUT_REQUIRED')
    return path


def file_hash(path):
    with no_links(path).open('rb') as stream:
        return __import__('hashlib').file_digest(stream,'sha256').hexdigest()


def read(path):
    path = no_links(path)
    require(path.is_file() and path.stat().st_size <= 32*1024**2, 'V7_GPU_JSON_SIZE_BOUND')
    raw = path.read_bytes()
    def pairs(items):
        value={}
        for name,item in items:
            require(name not in value,'V7_GPU_DUPLICATE_JSON_FIELD')
            value[name]=item
        return value
    value=json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('V7_GPU_NONFINITE_JSON')))
    json.dumps(value,allow_nan=False)
    return value


def write(path,value):
    with no_links(path).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,sort_keys=True,allow_nan=False)
        stream.write('\n')


def fixture_identity():
    """Parent-only check of all saved fixture bytes, including private targets."""
    for name,pin in FIXTURE_PINS.items():
        require(file_hash(ROOT/FIXTURE/name)==pin,'V7_GPU_FIXTURE_BYTES_CHANGED:'+name)
    return public_fixture_identity()


def public_fixture_identity():
    """Trainer admission checks public bytes and pinned metadata, never targets."""
    for name,pin in FIXTURE_PINS.items():
        if name != 'test_private.json':
            require(file_hash(ROOT/FIXTURE/name)==pin,'V7_GPU_FIXTURE_BYTES_CHANGED:'+name)
    manifest=read(ROOT/FIXTURE/'manifest.json')
    require(manifest['seed']==SEED and manifest['config']==CONFIG
        and manifest['sha256']=={n:p for n,p in FIXTURE_PINS.items() if n!='manifest.json'},
        'V7_GPU_KNOWN_FIXTURE_IDENTITY')
    require(file_hash(ROOT/PINS_PATH)==PINS_SHA256,'V7_GPU_PARENT_SOURCE_PINS_CHANGED')
    from . import data
    loader=data.public_loader(LOADER_SHA256)
    loader.verify_source(read(ROOT/PINS_PATH),expected_loader_sha256=LOADER_SHA256,root=ROOT)
    return {'seed':SEED,'fixture_files_sha256':dict(FIXTURE_PINS),'source_pins_sha256':PINS_SHA256,
            'public_loader_sha256':LOADER_SHA256}


def runtime_helpers():
    # All are pure imports; this helper is only called after AWS admission.
    from ..contrast_v6 import curriculum
    from . import train,checks,data
    from ..campaign_v3 import _run_process,_baseline_identity
    return curriculum,train,checks,data,_run_process,_baseline_identity


def clean_coordinator():
    require(not FORBIDDEN.intersection(name.split('.')[0] for name in sys.modules),
            'V7_GPU_NEURAL_IMPORT_BEFORE_PARENT_EXIT')
    require('cas_meta2.contrast_v7.parent' not in sys.modules,'V7_GPU_PARENT_IMPORTED_IN_COORDINATOR')


def phase_command(output,job,phase):
    require(phase in ('prepare','train','native'),'V7_GPU_PHASE_REQUIRED')
    return [sys.executable,'-B','-m','cas_meta2.contrast_v7.gpu_preflight',
            '--phase',phase,'--output',str(output),'--job',job]


def prepare_fixture(output,*,job):
    require_request(job)
    clean_coordinator()
    output=run_path(output)
    require(output.is_dir() and all(not(output/name).exists() for name in
        ('base_dataset','dataset','trainer_input','assembly_receipt.json')),'V7_GPU_NEW_ASSEMBLY_REQUIRED')
    identity=fixture_identity()
    c,t,checks,data,_,_=runtime_helpers()
    before=t.source_identity()
    # Import the hook-installing parent only in this disposable pure child.
    from . import parent
    cfg=c.Config(**CONFIG).checked()
    base=output/'base_dataset';base.mkdir()
    for name,pin in FIXTURE_PINS.items():
        raw=(ROOT/FIXTURE/name).read_bytes()
        require(sha256(raw).hexdigest()==pin,'V7_GPU_FIXTURE_COPY_CHANGED')
        with (base/name).open('xb') as stream:
            stream.write(raw)
    opts={'seed':SEED,'config':cfg,'excluded':frozenset(),'pins':ROOT/PINS_PATH,
          'expected_pins_sha256':PINS_SHA256,'expected_loader_sha256':LOADER_SHA256}
    merged=parent.merge(base,output/'dataset',expected_sha256=FIXTURE_PINS['manifest.json'],**opts)
    pin=file_hash(output/'dataset/manifest.json')
    cold=parent.validate_bundle(output/'dataset',expected_sha256=pin,**opts)
    require(merged==cold and cold['completed'] is True and cold['splits']==EXPECTED_SPLITS
        and cold['prototype_tasks']==256 and cold['prototype_pairs']==128
        and cold['tokenizer_fit_examples']==352,'V7_GPU_MERGED_FIXTURE_COUNTS')
    exported=parent.export_training_bundle(output/'dataset',output/'trainer_input',expected_sha256=pin,**opts)
    require(exported['parent_validation']==cold and exported['splits']==EXPECTED_SPLITS
        and exported['base_train_examples']==96 and exported['imported_train_examples']==256
        and exported['private_labels_read_by_loader'] is False and exported['test_programs_parsed_by_loader'] is False
        and {p.name for p in (output/'trainer_input').iterdir()}==PUBLIC_FILES
        and not(output/'trainer_input/test_private.json').exists(),'V7_GPU_PUBLIC_EXPORT_BOUNDARY')
    require(fixture_identity()==identity and t.source_identity()==before,'V7_GPU_ASSEMBLY_SOURCE_CHANGED')
    require(not FORBIDDEN.intersection(name.split('.')[0] for name in sys.modules),'V7_GPU_NEURAL_IMPORT_IN_PARENT')
    result={'schema':SCHEMA,'phase':'prepare','completed':True,'job':job,'pid':os.getpid(),
        'source_sha256':before,'manifest_sha256':pin,'fixture':identity,'splits':EXPECTED_SPLITS,
        'parent_validation':cold,'public_export':exported,
        'public_export_files_sha256':{name:file_hash(output/'trainer_input'/name) for name in sorted(PUBLIC_FILES)},
        'neural_execution':False,'task_generation':False,'native_evaluation_completed':False,
        'parent_process_must_exit_before_training':True}
    write(output/'assembly_receipt.json',result)
    return result


def check_assembly(output,*,job,process,source,checks,data):
    value=read(output/'assembly_receipt.json')
    require(value['schema']==SCHEMA and value['phase']=='prepare' and value['completed'] is True
        and value['job']==job and value['pid']==process['pid'] and value['source_sha256']==source
        and value['fixture']==public_fixture_identity() and value['splits']==EXPECTED_SPLITS
        and value['neural_execution'] is False and value['task_generation'] is False
        and value['parent_process_must_exit_before_training'] is True,'V7_GPU_ASSEMBLY_RECEIPT')
    require(value['manifest_sha256']==file_hash(output/'dataset/manifest.json')
        and set(value['public_export_files_sha256'])==PUBLIC_FILES
        and {p.name for p in (output/'trainer_input').iterdir()}==PUBLIC_FILES
        and all(file_hash(output/'trainer_input'/name)==pin
                for name,pin in value['public_export_files_sha256'].items()),'V7_GPU_EXPORT_BYTES_CHANGED')
    from ..contrast_v6 import curriculum as c
    loaded=data.load_training_bundle(output/'trainer_input',expected_sha256=value['manifest_sha256'],
        seed=SEED,config=c.Config(**CONFIG),excluded=frozenset(),expected_loader_sha256=LOADER_SHA256)
    require(loaded['receipt']['splits']==EXPECTED_SPLITS and len(loaded['train'])==352
        and len(loaded['validation'])==24 and len(loaded['test_public'])==9
        and loaded['receipt']['private_labels_read_by_loader'] is False,'V7_GPU_PUBLIC_LOADER_COUNTS')
    return value


def train_fixture(output,*,job):
    require_request(job)
    clean_coordinator()
    output=run_path(output)
    c,t,checks,data,_,_=runtime_helpers()
    # Require the externally parent-recorded preparation exit before this child
    # can read the public bundle or perform any neural imports.
    prep=checks.process_exit(output/'prepare_process/process_receipt.json',
                            expected_command=phase_command(output,job,'prepare'))
    require(prep['pid']!=os.getpid(),'V7_GPU_PREPARE_MUST_BE_SEPARATE_PROCESS')
    source=t.source_identity()
    assembled=check_assembly(output,job=job,process=prep,source=source,checks=checks,data=data)
    require(checks.timestamp(prep['finished_utc'])<=datetime.now(timezone.utc),'V7_GPU_PREPARE_EXIT_REQUIRED')
    return t.run(output/'trainer_input',output/'training',job=job,
        expected_manifest_sha256=assembled['manifest_sha256'],expected_loader_sha256=LOADER_SHA256,
        curriculum_seed=SEED,curriculum_config=c.Config(**CONFIG),excluded=frozenset(),
        config=t.TrainingConfig(epochs=1,max_seconds=900))


def exited_children(output,*,job,checks):
    prep=checks.process_exit(output/'prepare_process/process_receipt.json',
        expected_command=phase_command(output,job,'prepare'))
    trained=checks.process_exit(output/'training_process/process_receipt.json',
        expected_command=phase_command(output,job,'train'))
    require(checks.timestamp(prep['finished_utc'])<=checks.timestamp(trained['started_utc'])
        and len({prep['pid'],trained['pid'],os.getpid()})==3,'V7_GPU_CHILD_EXIT_ORDER')
    return prep,trained


def cuda_checkpoint_changes(output,*,job,receipt,source,manifest_pin):
    require_request(job)
    clean_coordinator()
    from . import checks
    exited_children(output,job=job,checks=checks)
    # Both actual child exits are checked here BEFORE this function's import.
    import torch
    require(torch.cuda.is_available(),'V7_GPU_CUDA_REQUIRED')
    device=torch.device('cuda')
    require('T4' not in torch.cuda.get_device_name(device).upper(),'T4_NOT_AUTHORIZED')
    changed={}
    for family in ('cas','generic'):
        states=[]
        for kind,epoch in (('initial',0),('final',1)):
            record=receipt['checkpoints'][family][kind]
            relative=Path(record['path'])
            require(not relative.is_absolute() and '..' not in relative.parts
                and not relative.drive,'V7_GPU_CHECKPOINT_PATH_ESCAPE')
            path=output/'training'/relative
            require(file_hash(path)==record['sha256'] and path.stat().st_size==record['bytes'],
                    'V7_GPU_CHECKPOINT_BYTES_CHANGED')
            state=torch.load(path,map_location=device,weights_only=True)
            require(state['schema']=='cas-meta2-contrast-training/7' and state['family']==family
                and state['epoch']==epoch and state['optimizer_steps']==22*epoch and state['accepted'] is False
                and state['source_sha256']==source and state['manifest_sha256']==manifest_pin,
                'V7_GPU_CHECKPOINT_IDENTITY')
            tensors=state['state_dict']
            require(tensors and all(torch.is_tensor(v) and v.device.type=='cuda' for v in tensors.values()),
                    'V7_GPU_CHECKPOINT_NOT_ALL_CUDA')
            states.append(tensors)
        require(set(states[0])==set(states[1]),'V7_GPU_CHECKPOINT_KEYS_CHANGED')
        names=sorted(name for name in states[0] if not torch.equal(states[0][name],states[1][name]))
        require(names,'V7_GPU_NO_LEARNED_PARAMETER_CHANGE')
        changed[family]={'changed_state_tensors':names,'changed_count':len(names),'all_loaded_on_cuda':True}
    return changed


def native_fixture(output,*,job):
    require_request(job)
    require(NATIVE_GATE_READY is True,'V7_GPU_NATIVE_GATE_PENDING_RECOVERY_CONFIRMATION')
    clean_coordinator()
    output=run_path(output)
    c,t,checks,data,_,baseline_identity=runtime_helpers()
    prep,process=exited_children(output,job=job,checks=checks)
    source,baseline=t.source_identity(),baseline_identity()
    assembled=check_assembly(output,job=job,process=prep,source=source,checks=checks,data=data)
    checkpoint=read(output/'checkpoint_verification.json')
    require(checkpoint['completed'] is True and checkpoint['job']==job
        and checkpoint['source_sha256']==source and checkpoint['baseline']==baseline
        and checkpoint['training_process_receipt_sha256']==file_hash(output/'training_process/process_receipt.json')
        and checkpoint['training_receipt_sha256']==file_hash(output/'training/training_receipt.json')
        and checkpoint['manifest_sha256']==assembled['manifest_sha256']
        and all(checkpoint['changed_weights'][family]['all_loaded_on_cuda'] is True
            and checkpoint['changed_weights'][family]['changed_count']>0 for family in ('cas','generic')),
        'V7_GPU_CHECKPOINT_VERIFICATION_REQUIRED')
    # The new native child is pure until its private-data parent has finished;
    # evaluator workers are fresh spawned children, not this hook-bearing parent.
    from . import native_evaluation
    return native_evaluation.evaluate(output/'dataset',output/'training',
        output/'training_process/process_receipt.json',output/'trainer_input',output/'native_evaluation',
        expected_command=phase_command(output,job,'train'),job=job,
        expected_manifest_sha256=assembled['manifest_sha256'],expected_loader_sha256=LOADER_SHA256,
        curriculum_seed=SEED,curriculum_config=c.Config(**CONFIG),excluded=frozenset(),
        config=t.TrainingConfig(epochs=1,max_seconds=900),expected_source=source,expected_baseline=baseline,
        pins=ROOT/PINS_PATH,expected_pins_sha256=PINS_SHA256,max_seconds=600)


def check_native_smoke(receipt):
    arms={'cas_untrained','cas_trained','generic_untrained','generic_trained','rule'}
    require(receipt['schema']=='cas-meta2-prototype-native-evaluation/7'
        and receipt['completed'] is True and receipt['cases']==receipt['reference_cases']==9
        and receipt['arm_verdicts']==45 and receipt['learning_accepted'] is False
        and set(receipt['results'])==arms
        and all(receipt['results'][arm]['total']==9
            and receipt['results'][arm]['all_cases_in_denominator'] is True
            and receipt['results'][arm]['compute_complete'] is
                (receipt['results'][arm]['post_admission_runtime_failures']==0) for arm in arms)
        and receipt['results']['rule']['task_correct']==9,'V7_GPU_NATIVE_FULL_CASE_COVERAGE')
    for group,total in (('depth_3',6),('depth_4',3),('same_depth',3),('wording_shift',3),('deeper_calls',3)):
        require(set(receipt['groups'][group])==arms and all(
            receipt['groups'][group][arm]['total']==total for arm in arms),'V7_GPU_NATIVE_GROUP_DENOMINATORS')
    return receipt


def run_smoke(output,*,job,max_seconds=900,include_native=False):
    require_request(job)
    clean_coordinator()
    require(type(include_native) is bool and (not include_native or NATIVE_GATE_READY is True),
        'V7_GPU_NATIVE_GATE_PENDING_RECOVERY_CONFIRMATION')
    require(type(max_seconds) is int and max_seconds==900,'V7_GPU_SMOKE_900_SECOND_BOUND')
    output=run_path(output,new=True);output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();deadline=started+max_seconds
    c,t,checks,data,run_process,baseline_identity=runtime_helpers()
    source,baseline=t.source_identity(),baseline_identity()
    identity=fixture_identity()
    prep_command=phase_command(output,job,'prepare')
    run_process(prep_command,output/'prepare_process',min(deadline,time.monotonic()+240),environment=dict(os.environ))
    prep=checks.process_exit(output/'prepare_process/process_receipt.json',expected_command=prep_command)
    clean_coordinator()
    assembled=check_assembly(output,job=job,process=prep,source=source,checks=checks,data=data)
    command=phase_command(output,job,'train')
    run_process(command,output/'training_process',deadline,environment=dict(os.environ))
    process=checks.process_exit(output/'training_process/process_receipt.json',expected_command=command)
    require(checks.timestamp(prep['finished_utc'])<=checks.timestamp(process['started_utc'])
        and prep['pid']!=process['pid'],'V7_GPU_CHILD_EXIT_ORDER')
    gate=checks.check_training(output/'training',output/'training_process/process_receipt.json',
        output/'trainer_input',expected_command=command,job=job,
        expected_manifest_sha256=assembled['manifest_sha256'],expected_loader_sha256=LOADER_SHA256,
        curriculum_seed=SEED,curriculum_config=c.Config(**CONFIG),excluded=frozenset(),
        config=t.TrainingConfig(epochs=1,max_seconds=900),expected_source=source,expected_baseline=baseline)
    receipt=checks.read(output/'training/training_receipt.json')
    require(gate['completed'] is True and receipt['completed'] is True
        and receipt['completed_epochs']==1 and receipt['optimizer_steps']=={'cas':22,'generic':22}
        and receipt['seal']['test_examples']==9 and receipt['seal']['prediction_count']==36
        and receipt['seal']['private_labels_read'] is False and receipt['learning_accepted'] is False,
        'V7_GPU_ONE_EPOCH_RECOUNT')
    clean_coordinator()
    changed=cuda_checkpoint_changes(output,job=job,receipt=receipt,source=source,
                                     manifest_pin=assembled['manifest_sha256'])
    write(output/'checkpoint_verification.json',{'schema':SCHEMA,'completed':True,'job':job,
        'source_sha256':source,'baseline':baseline,'manifest_sha256':assembled['manifest_sha256'],
        'training_process_receipt_sha256':file_hash(output/'training_process/process_receipt.json'),
        'training_receipt_sha256':file_hash(output/'training/training_receipt.json'),'changed_weights':changed})
    native=None
    if include_native:
        command=phase_command(output,job,'native')
        run_process(command,output/'native_process',deadline,environment=dict(os.environ))
        process_native=checks.process_exit(output/'native_process/process_receipt.json',expected_command=command)
        require(checks.timestamp(process['finished_utc'])<=checks.timestamp(process_native['started_utc'])
            and len({prep['pid'],process['pid'],process_native['pid'],os.getpid()})==4,'V7_GPU_NATIVE_EXIT_ORDER')
        native=check_native_smoke(read(output/'native_evaluation/native_receipt.json'))
    require(time.monotonic()<=deadline and t.source_identity()==source and baseline_identity()==baseline
        and fixture_identity()==identity,'V7_GPU_SMOKE_BOUND_STATE_CHANGED')
    result={'schema':SCHEMA,'status':('V7_KNOWN_FIXTURE_CUDA_FULL_PIPELINE_SMOKE_PASSED' if include_native
        else 'V7_KNOWN_FIXTURE_CUDA_TRAINING_SMOKE_PASSED'),'completed':True,'job':job,
        'fixture':identity,'splits':EXPECTED_SPLITS,'source_sha256':source,'baseline':baseline,
        'assembly_receipt_sha256':file_hash(output/'assembly_receipt.json'),
        'prepare_process_receipt_sha256':file_hash(output/'prepare_process/process_receipt.json'),
        'training_process_receipt_sha256':file_hash(output/'training_process/process_receipt.json'),
        'prepare_pid':prep['pid'],'training_pid':process['pid'],'prepare_exit_before_training':True,
        'training_gate':gate,'optimizer_steps':receipt['optimizer_steps'],'changed_weights':changed,
        'wall_seconds':time.monotonic()-started,'neural_execution':True,'task_generation':False,
        'learning_accepted':False,'native_evaluation_completed':include_native,'native_receipt':native,
        'native_receipt_sha256':file_hash(output/'native_evaluation/native_receipt.json') if include_native else None,
        'native_process_receipt_sha256':file_hash(output/'native_process/process_receipt.json') if include_native else None,
        'native_integration_status':'COMPLETED_KNOWN_FIXTURE_ONLY' if include_native else 'PENDING_VALIDATED_V7_NATIVE_EVALUATOR',
        'boundary':'Actual known-fixture CUDA assembly/training smoke; native coverage is reported separately. '
                   'Not a learning experiment, fresh evaluation or permission to launch production training.'}
    write(output/'gpu_smoke_receipt.json',result)
    return result


def pytest_command(output):
    output=run_path(output)
    require(not(output/'gpu_tmp').exists(),'V7_GPU_NEW_PYTEST_BASETEMP_REQUIRED')
    return [sys.executable,'-B','-m','pytest','-q','-m','gpu','-p','cas_meta2.pytest_no_aliases_v4',
        '-p','no:cacheprovider','tests/test_contrast_v7_train_gpu.py','--basetemp',str(output/'gpu_tmp'),
        '--junitxml',str(output/'gpu_test.xml')]


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=('prepare','train','native'),required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--job',required=True)
    args=parser.parse_args()
    require_request(args.job)
    function={'prepare':prepare_fixture,'train':train_fixture,'native':native_fixture}[args.phase]
    result=function(args.output,job=args.job)
    print(json.dumps({'schema':SCHEMA,'phase':args.phase,'completed':result['completed'],'job':args.job}))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
