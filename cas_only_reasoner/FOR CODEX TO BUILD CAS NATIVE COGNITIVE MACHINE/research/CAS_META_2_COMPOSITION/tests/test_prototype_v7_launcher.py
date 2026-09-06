"""Synthetic and read-only launcher checks; never call a provider."""
import ast
from copy import deepcopy
from decimal import Decimal
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
    assert value['runtime_seconds_max']==7200 and value['compute_seconds_max']==6600
    assert value['parent_max_seconds']==6300
    assert sum(value[k] for k in ('gpu_gate_max_seconds','dataset_max_seconds','training_max_seconds','native_max_seconds'))==6180
    assert l.budget.validate_plan(value,'7.00')==Decimal('6.04')


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
    assert 'aws/prototype_remote_v7.py' in source and "'--max-wall-seconds','6300'" in source
    assert '--launch-manifest-sha256' in source and 'CAS_META2_RUN_PROTOTYPE_TRAINING' in source
    assert 'CAS_META2_RUN_CONTRAST_TRAINING' not in source
    assert 'V7_INSUFFICIENT_FULL_REGISTERED_PARENT_TIME' in source
    assert 'V7_SUCCESS_WITHOUT_BOUND_COORDINATOR_RECEIPT' in source
    assert source.index('compute_started = time.time()')<source.index('probe = "import torch')
    assert "compute_started+CONFIG['compute_seconds_max']" in source
    assert 'if int(compute_deadline-time.time()) < 6300:' in source
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
