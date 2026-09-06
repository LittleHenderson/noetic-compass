"""Synthetic receipt checks only. No dataset generation, neural work, or provider calls."""
import ast
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from aws import prototype_remote_v7 as r

JOB='cas-meta2-20260906000000-12345678'
EXPERIMENT={'profile':'prototype_training_v7','entrypoint':'cas_meta2.contrast_v7.campaign',
            'spec_path':r.PILOT+'/EXPERIMENT_PROTOTYPE_V7.json','spec_sha256':'1'*64}


def enabled(monkeypatch):
    monkeypatch.setattr(r.sys,'platform','linux')
    for name,value in {'CAS_META2_AWS_JOB_ID':JOB,'CAS_META1_AWS_JOB_ID':JOB,
        'CAS_META2_RUN_PROTOTYPE_TRAINING':'1','CAS_META2_RUN_GPU_TESTS':'1'}.items():monkeypatch.setenv(name,value)


@pytest.mark.parametrize('fault',['linux','job','meta1','enable','gpu','time','booltime'])
def test_remote_requires_explicit_fixed_aws_job_before_any_source_read(monkeypatch,fault):
    enabled(monkeypatch);seconds=6900
    if fault=='linux':monkeypatch.setattr(r.sys,'platform','win32')
    if fault=='job':monkeypatch.setenv('CAS_META2_AWS_JOB_ID','different')
    if fault=='meta1':monkeypatch.setenv('CAS_META1_AWS_JOB_ID','different')
    if fault=='enable':monkeypatch.delenv('CAS_META2_RUN_PROTOTYPE_TRAINING')
    if fault=='gpu':monkeypatch.delenv('CAS_META2_RUN_GPU_TESTS')
    if fault=='time':seconds=6600
    if fault=='booltime':seconds=True
    monkeypatch.setattr(r,'file_hash',Mock(side_effect=AssertionError('No source reads')))
    with pytest.raises(ValueError,match='V7_REMOTE_'):r.verify_sources(SimpleNamespace(job=JOB,max_wall_seconds=seconds))
    assert not r.file_hash.called


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value));return path


def evidence(tmp_path):
    native={'schema':'cas-meta2-prototype-native-evaluation/7','completed':True,'cases':72,'reference_cases':72,
            'arm_verdicts':360,'learning_accepted':False,'results':{'rule':{'task_correct':72}},'groups':{}}
    values={'campaign_receipt.json':{'schema':'cas-meta2-prototype-campaign/7','completed':True,'job':JOB,
        'experiment':EXPERIMENT,'training_performed':True,'native_evaluation_completed':True,
        'learning_accepted':False,'release_accepted':False,'native':native},
        'dataset_assembly_receipt.json':{'completed':True,'optimizer_steps_per_family':11200,
            'actual_splits':{'train':{'tasks':896,'depths':{'1':128,'2':384,'3':384}},
                'validation':{'tasks':96,'depths':{'1':32,'2':32,'3':32}},'test':{'tasks':72,'depths':{'3':48,'4':24}}}},
        'training/training_receipt.json':{'schema':'cas-meta2-contrast-training/7','completed':True,
            'completed_epochs':200,'optimizer_steps':{'cas':11200,'generic':11200},'learning_accepted':False},
        'native/native_receipt.json':native,
        'gpu_tmp/saved/v7_smoke/gpu_smoke_receipt.json':{'schema':'cas-meta2-prototype-gpu-preflight/7',
            'status':'V7_KNOWN_FIXTURE_CUDA_FULL_PIPELINE_SMOKE_PASSED','completed':True,'job':JOB,
            'native_evaluation_completed':True,'learning_accepted':False,'task_generation':False,
            'optimizer_steps':{'cas':22,'generic':22},'native_receipt':{'cases':9,'reference_cases':9,
                'arm_verdicts':45,'results':{'rule':{'task_correct':9}}}},
        'training_gate.json':{},'training/neural_predictions.jsonl':{},'training/neural_predictions_seal.json':{},
        'native/evaluation_results.json':{'cases':[],'results':native['results'],'groups':native['groups']},
        'payload_sha256.json':{'synthetic_sealed_index':True}}
    for name,value in values.items():write(tmp_path/name,value)
    compact={key:native[key] for key in ('results','groups','cases','reference_cases','arm_verdicts')}
    compact.update(native_receipt_sha256=r.file_hash(tmp_path/'native/native_receipt.json'),
        evaluation_results_sha256=r.file_hash(tmp_path/'native/evaluation_results.json'))
    values['campaign_receipt.json']['native']=compact
    write(tmp_path/'campaign_receipt.json',values['campaign_receipt.json'])
    return values


def test_complete_synthetic_receipts_report_related_variants_not_independent_structures(tmp_path):
    evidence(tmp_path)
    result=r.completed_evidence(tmp_path,job=JOB,experiment=EXPERIMENT)
    assert result['train_examples']==896 and result['test_variants']==72 and result['matched_test_triplets']==24
    assert result['native_arm_verdicts']==360 and result['known_fixture_smoke_arm_verdicts']==45
    assert len(result['files_sha256'])==10


def test_real_campaign_compact_summary_contract_not_full_receipt(monkeypatch,tmp_path):
    values=evidence(tmp_path)
    from cas_meta2.contrast_v7 import campaign as q,native_evaluation as native
    write(tmp_path/'dataset/test_private.json',[{'synthetic_index':index} for index in range(72)])
    monkeypatch.setattr(native,'aggregate_cases',lambda rows,count:values['native/native_receipt.json']['results'])
    monkeypatch.setattr(native,'grouped_results',lambda rows,tasks:values['native/native_receipt.json']['groups'])
    compact=q.check_native_output(tmp_path,72)
    assert set(compact)=={'results','groups','cases','reference_cases','arm_verdicts',
        'native_receipt_sha256','evaluation_results_sha256'}
    values['campaign_receipt.json']['native']=compact
    write(tmp_path/'campaign_receipt.json',values['campaign_receipt.json'])
    assert r.completed_evidence(tmp_path,job=JOB,experiment=EXPERIMENT)['native_arm_verdicts']==360
    compact['evaluation_results_sha256']='0'*64
    write(tmp_path/'campaign_receipt.json',values['campaign_receipt.json'])
    with pytest.raises(ValueError,match='NATIVE_DENOMINATORS'):r.completed_evidence(tmp_path,job=JOB,experiment=EXPERIMENT)


def test_outer_coordinator_does_not_change_sealed_campaign_index(monkeypatch,tmp_path):
    from cas_meta2.contrast_v7 import campaign as q
    monkeypatch.setattr(r,'ROOT',tmp_path)
    manifest={'experiment':EXPERIMENT,'source_sha':'a'*40}
    monkeypatch.setattr(r,'verify_sources',lambda args:(manifest,{}))
    sealed={}
    def fake_campaign(output,**kwargs):
        evidence(output)
        sealed.update({p.relative_to(output).as_posix():r.file_hash(p) for p in output.rglob('*') if p.is_file()})
    monkeypatch.setattr(q,'run',fake_campaign)
    output=tmp_path/'runs/cloud_job/campaign'
    args=SimpleNamespace(output=output,job=JOB,max_wall_seconds=6900,launch_manifest_sha256='b'*64)
    result=r.run(args)
    assert result['completed'] is True
    assert (output.parent/'prototype_coordinator_receipt.json').is_file()
    assert not(output/'coordinator_receipt.json').exists()
    assert {p.relative_to(output).as_posix():r.file_hash(p) for p in output.rglob('*') if p.is_file()}==sealed


@pytest.mark.parametrize('fault',['partial','oldsteps','traincount','nativepartial','no_smoke','twosmoke',
    'training_only_smoke','wrong_smoke_job','smoke_partial','rule_failure','smoke_generation','promotion'])
def test_remote_never_accepts_partial_old_or_training_only_evidence(tmp_path,fault):
    values=evidence(tmp_path);smoke='gpu_tmp/saved/v7_smoke/gpu_smoke_receipt.json'
    if fault=='partial':values['campaign_receipt.json']['completed']=False
    if fault=='oldsteps':values['training/training_receipt.json']['optimizer_steps']['cas']=8000
    if fault=='traincount':values['dataset_assembly_receipt.json']['actual_splits']['train']['tasks']=640
    if fault=='nativepartial':values['native/native_receipt.json']['cases']=71
    if fault=='no_smoke':(tmp_path/smoke).unlink();values.pop(smoke)
    if fault=='twosmoke':write(tmp_path/'extra/gpu_smoke_receipt.json',values[smoke])
    if fault=='training_only_smoke':values[smoke]['native_evaluation_completed']=False
    if fault=='wrong_smoke_job':values[smoke]['job']='different'
    if fault=='smoke_partial':values[smoke]['native_receipt']['arm_verdicts']=44
    if fault=='rule_failure':values[smoke]['native_receipt']['results']['rule']['task_correct']=8
    if fault=='smoke_generation':values[smoke]['task_generation']=True
    if fault=='promotion':values['campaign_receipt.json']['learning_accepted']=True
    for name,value in values.items():write(tmp_path/name,value)
    with pytest.raises(ValueError,match='V7_REMOTE_'):r.completed_evidence(tmp_path,job=JOB,experiment=EXPERIMENT)


def test_remote_rejects_duplicate_json_keys(tmp_path):
    path=tmp_path/'record.json';path.write_text('{"completed":false,"completed":true}')
    with pytest.raises(ValueError,match='DUPLICATE_JSON'):r.read(path)


def test_remote_source_verification_precedes_campaign_import():
    tree=ast.parse(Path(r.__file__).read_text())
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run')
    body=ast.unparse(fn)
    assert body.index('verify_sources(args)')<body.index('from cas_meta2.contrast_v7 import campaign')
    verify=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='verify_sources')
    body=ast.unparse(verify)
    assert body.index('file_hash(path) == pin')<body.index('spec.loader.exec_module(profile)')
    assert body.index('profile.validate_launch_manifest')<body.index('profile.require_execution_ready')


def test_external_manifest_mismatch_stops_before_profile_import(monkeypatch,tmp_path):
    enabled(monkeypatch);root=tmp_path/'research/CAS_META_2_COMPOSITION';root.mkdir(parents=True)
    monkeypatch.setattr(r,'ROOT',root)
    path=write(tmp_path/'launch_manifest.json',{})
    monkeypatch.setattr(r.importlib.util,'spec_from_file_location',Mock(side_effect=AssertionError('No imports')))
    args=SimpleNamespace(job=JOB,max_wall_seconds=6900,launch_manifest=path,launch_manifest_sha256='0'*64)
    with pytest.raises(ValueError,match='EXTERNAL_MANIFEST_PIN'):r.verify_sources(args)
    assert not r.importlib.util.spec_from_file_location.called
