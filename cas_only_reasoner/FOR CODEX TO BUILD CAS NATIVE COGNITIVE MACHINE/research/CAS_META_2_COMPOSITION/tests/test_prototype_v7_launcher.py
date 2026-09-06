"""Synthetic and read-only launcher checks; never call a provider."""
import ast
from copy import deepcopy
from decimal import Decimal
from datetime import datetime,timezone
import os
import pathlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from aws import launch_prototype_v7 as l

ROOT=Path(__file__).resolve().parents[1]


def plan():return l.json.loads(l.PLAN_FILE.read_text())


def test_fixed_plan_fits_seven_dollar_reservation_and_has_no_launch_authority():
    value=plan();l.validate_approval('400.00',value)
    assert type(value['launch_enabled']) is bool
    assert value['runtime_seconds_max']==7800 and value['compute_seconds_max']==7200
    assert value['parent_max_seconds']==6900
    assert sum(value[k] for k in ('gpu_gate_max_seconds','dataset_max_seconds','training_max_seconds','native_max_seconds'))==6630
    assert l.budget.validate_plan(value,'7.00')==Decimal('6.46')


@pytest.mark.parametrize('field,value',[('gpu_gate_max_seconds',900),('dataset_max_seconds',300),
    ('training_max_seconds',3600),('native_max_seconds',3000),('parent_max_seconds',6600),
    ('runtime_seconds_max',7300),('compute_seconds_max',6700),('per_launch_reserved_cap_usd','8.00'),
    ('instance_type','g4dn.xlarge'),('automatic_retries',1),('launch_enabled','true')])
def test_resource_and_phase_plan_cannot_silently_expand(field,value):
    proposal=plan();proposal[field]=value
    with pytest.raises(l.LaunchRefused):l.validate_approval('400.00',proposal)


@pytest.mark.parametrize('function',['execute','_execute_locked'])
def test_preparation_block_precedes_lock_budget_and_provider_import(monkeypatch,function):
    lock=Mock(side_effect=AssertionError('No lock'));ledger=Mock(side_effect=AssertionError('No ledger'))
    monkeypatch.setattr(l,'campaign_execution_lock',lock);monkeypatch.setattr(l.budget,'read_ledger',ledger)
    value=plan();value['launch_enabled']=False
    with pytest.raises(l.LaunchRefused,match='V7_LAUNCH_PREPARATION_ONLY'):
        getattr(l,function)(SimpleNamespace(smoke_only=False,approved_cap_usd='400.00'),value,{})
    assert not lock.called and not ledger.called


def test_plan_mode_has_no_provider_or_reservation(monkeypatch,capsys):
    monkeypatch.setattr(l,'execute',Mock(side_effect=AssertionError('No execution')))
    assert l.main([])==0
    value=l.json.loads(capsys.readouterr().out)
    assert value['aws_actions_performed'] is False and value['archive_verified'] is False
    assert not l.execute.called


def test_remote_program_uses_only_original_four_gpu_tests_then_new_coordinator(monkeypatch):
    record={'entrypoint':'cas_meta2.contrast_v7.campaign','profile':'prototype_training_v7'}
    monkeypatch.setattr(l,'experiment_record',lambda _:record)
    source=l.remote_program({'manifest':{},'smoke_only':False})
    compile(source,'<remote-v7>','exec')
    assert 'tests/test_execution_contract.py' in source and "'tests':4" in source
    assert 'tests/test_policy_gpu.py' not in source and 'policy_expected_tests' not in source
    assert 'aws/prototype_remote_v7.py' in source and "'--max-wall-seconds','6900'" in source
    assert '--launch-manifest-sha256' in source and 'CAS_META2_RUN_PROTOTYPE_TRAINING' in source
    assert 'CAS_META2_RUN_CONTRAST_TRAINING' not in source
    assert 'V7_INSUFFICIENT_FULL_REGISTERED_PARENT_TIME' in source
    assert 'V7_SUCCESS_WITHOUT_BOUND_COORDINATOR_RECEIPT' in source
    assert source.index('compute_started = time.time()')<source.index('probe = "import torch')
    assert "compute_started+CONFIG['compute_seconds_max']" in source
    assert 'if int(compute_deadline-time.time()) < 6900:' in source
    assert source.count('deadline=min(deadline,compute_deadline+120)')==2


def test_source_budget_lock_cleanup_and_evidence_helpers_match_frozen_launcher_ast():
    old=ast.parse((ROOT/'aws/launch_contrast_v6.py').read_text())
    new=ast.parse(Path(l.__file__).read_text())
    names=('reserve_budget','campaign_execution_lock','terminate_owned_instance','confirm_deleted_volumes',
           'remove_owned_auxiliary_resources','verify_downloaded_packet','build_evidence_bundle','verify_schedule')
    for name in names:
        a=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name==name)
        b=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name==name)
        assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False),name


def test_source_readiness_is_checked_before_budget_and_provider_import():
    source=Path(l.__file__).read_text();tree=ast.parse(source)
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='verify_launcher_identity')
    assert 'profiles.require_execution_ready(spec)' in ast.unparse(function)
    assert 'profiles.validate_launch_manifest(manifest, committed.__getitem__)' in ast.unparse(function)
    paid=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_execute_locked')
    body=ast.unparse(paid)
    assert body.index('verify_launcher_identity(manifest)')<body.index('budget.read_ledger()')<body.index('import boto3')


def test_preimport_check_lists_new_executable_sources():
    tree=ast.parse(Path(l.__file__).read_text())
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='verify_cli_source_before_helper_import')
    source=ast.unparse(fn)
    for name in ('aws/launch_prototype_v7.py','aws/prototype_remote_v7.py','tools/experiment_profiles_prototype_v7.py',
                 'tools/build_launch_bundle_prototype_v7.py','aws/launch_prototype_v7_plan.json','aws/budget.py'):
        assert name in source


def progress_helper(monkeypatch,tmp_path):
    """Compile only the generated progress helper; never run remote bootstrap."""
    monkeypatch.setattr(l,'experiment_record',lambda _:{'entrypoint':'cas_meta2.contrast_v7.campaign'})
    source=l.remote_program({'manifest':{},'smoke_only':False})
    tree=ast.parse(source)
    function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='publish_progress')
    module=ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[]))
    process=SimpleNamespace(run=Mock(),DEVNULL=-3)
    output=tmp_path/'cloud_job';output.mkdir()
    context={'json':l.json,'datetime':datetime,'timezone':timezone,'os':SimpleNamespace(environ={}),
        'pathlib':pathlib,'subprocess':process,'root':tmp_path,'out':output,
        'CONFIG':{'job':'cas-meta2-20000101000000-1234abcd','bucket':'owned-bucket','region':'us-west-2'}}
    exec(compile(module,'<pure-v7-progress-helper>','exec'),context)
    return context['publish_progress'],output,process


def progress_files(output,*,large=False):
    files={output/'campaign/campaign_status.json':b'{"stage":"training","train":896,"validation":96,"test":72}',
        output/'campaign/processes/training/stdout.txt':b'{"epoch":10,"optimizer_steps":{"cas":560,"generic":560}}',
        output/'campaign/native/progress.json':b'{"completed":12,"expected":72}',
        output/'campaign.log':b'ACTUAL_ASSEMBLED_COUNTS=896/96/72'}
    for path,raw in files.items():
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes((b'x'*100000 if large else b'')+raw)
    return files


def test_progress_reads_only_actual_public_v7_paths_and_uses_one_existing_object(monkeypatch,tmp_path):
    publish,output,process=progress_helper(monkeypatch,tmp_path)
    files=progress_files(output)
    old=output/'campaign/progress.json';old.write_bytes(b'OBSOLETE_PROGRESS_MUST_NOT_BE_READ')
    private=output/'campaign/test_private.json';private.write_bytes(b'PRIVATE_TARGET_MUST_NOT_BE_READ')
    opened=[];original=Path.open
    def checked_open(path,mode='r',*args,**kwargs):
        if mode=='rb':
            opened.append(path)
            assert path in files,'Unexpected progress read: '+str(path)
        return original(path,mode,*args,**kwargs)
    with monkeypatch.context() as scope:
        scope.setattr(Path,'open',checked_open)
        publish(output/'campaign.log',{'state':'RUNNING','elapsed_seconds':10,'artifact_bytes':1234})
    content=(tmp_path/'live-progress.log').read_bytes()
    assert set(opened)==set(files) and all(raw in content for raw in files.values())
    assert b'PRIVATE_TARGET' not in content and b'OBSOLETE_PROGRESS' not in content
    assert process.run.call_count==1
    args,kwargs=process.run.call_args
    assert args[0]==['aws','s3','cp',str(tmp_path/'live-progress.log'),
        's3://owned-bucket/results/bootstrap.log','--region','us-west-2',
        '--cli-connect-timeout','5','--cli-read-timeout','5']
    assert kwargs['timeout']==5 and kwargs['check'] is False
    assert kwargs['env']=={'AWS_MAX_ATTEMPTS':'1','AWS_PAGER':''}


def test_progress_limits_long_logs_and_large_status_without_hiding_latest_metrics(monkeypatch,tmp_path):
    publish,output,process=progress_helper(monkeypatch,tmp_path)
    files=progress_files(output,large=True)
    publish(output/'campaign.log',{'state':'RUNNING','padding':'z'*100000})
    content=(tmp_path/'live-progress.log').read_bytes()
    assert len(content)<=65536 and all(raw in content for raw in files.values())
    assert l.json.loads(content.splitlines()[0])['oversized_status_omitted'] is True
    assert process.run.call_count==1


def test_progress_missing_files_are_best_effort_and_unregistered_log_is_not_read(monkeypatch,tmp_path):
    publish,output,process=progress_helper(monkeypatch,tmp_path)
    private=output/'test_private.json';private.write_bytes(b'PRIVATE_TARGET_SENTINEL')
    publish(private,{'state':'STARTING'})
    content=(tmp_path/'live-progress.log').read_bytes()
    assert b'PRIVATE_TARGET_SENTINEL' not in content
    assert l.json.loads(content.splitlines()[0])['stage_log'] is None
    assert len(content)<=65536 and process.run.call_count==1


def test_progress_refuses_symlink_inputs_without_reading_targets(monkeypatch,tmp_path):
    publish,output,process=progress_helper(monkeypatch,tmp_path)
    files=progress_files(output)
    target=output/'campaign/processes/training/stdout.txt'
    original=Path.is_symlink
    monkeypatch.setattr(Path,'is_symlink',lambda path:True if path==target else original(path))
    publish(output/'campaign.log',{'state':'RUNNING'})
    assert files[target] not in (tmp_path/'live-progress.log').read_bytes()
    assert process.run.call_count==1


def test_progress_upload_failure_has_no_retry_or_new_object(monkeypatch,tmp_path):
    publish,output,process=progress_helper(monkeypatch,tmp_path)
    progress_files(output)
    process.run.side_effect=TimeoutError('Synthetic upload timeout')
    assert publish(output/'campaign.log',{'state':'RUNNING'}) is None
    assert process.run.call_count==1
