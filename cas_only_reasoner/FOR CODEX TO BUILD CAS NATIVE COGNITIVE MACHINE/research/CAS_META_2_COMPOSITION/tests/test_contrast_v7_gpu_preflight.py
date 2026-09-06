"""Pure tests only: saved source bytes and synthetic process records, no tasks generated."""
import ast
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from cas_meta2.contrast_v7 import gpu_preflight as q

ROOT = Path(__file__).resolve().parents[1]
JOB = 'cas-meta2-20260906064703-c0d74ffa'


def enabled(monkeypatch):
    monkeypatch.setattr(q.sys, 'platform', 'linux')
    monkeypatch.setenv('CAS_META2_RUN_PROTOTYPE_TRAINING', '1')
    monkeypatch.setenv('CAS_META2_RUN_GPU_TESTS', '1')
    monkeypatch.setenv('CAS_META2_AWS_JOB_ID', JOB)


def test_module_import_is_pure_in_a_fresh_process():
    script = ('import sys; from cas_meta2.contrast_v7 import gpu_preflight as q; '
              'assert not q.FORBIDDEN.intersection(n.split(".")[0] for n in sys.modules); '
              'assert "cas_meta2.contrast_v7.parent" not in sys.modules; '
              'assert "cas_meta2.contrast_v7.train" not in sys.modules; print("PURE_IMPORT")')
    result = subprocess.run([sys.executable, '-B', '-c', script], cwd=ROOT,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'PURE_IMPORT'


@pytest.mark.parametrize('fault', ['platform', 'training', 'gpu', 'job', 'syntax', 'type'])
def test_aws_guards_reject_before_any_runtime_helpers(monkeypatch,tmp_path,fault):
    enabled(monkeypatch)
    job = JOB
    if fault == 'platform': monkeypatch.setattr(q.sys,'platform','win32')
    if fault == 'training': monkeypatch.delenv('CAS_META2_RUN_PROTOTYPE_TRAINING')
    if fault == 'gpu': monkeypatch.delenv('CAS_META2_RUN_GPU_TESTS')
    if fault == 'job': monkeypatch.setenv('CAS_META2_AWS_JOB_ID',JOB+'0')
    if fault == 'syntax': job = 'ordinary-job'
    if fault == 'type': job = None
    helper = Mock(side_effect=AssertionError('No runtime helper before guards'))
    monkeypatch.setattr(q,'runtime_helpers',helper)
    with pytest.raises(ValueError,match='V7_GPU_'):
        q.run_smoke(tmp_path/'output',job=job)
    assert not helper.called


def test_known_fixture_and_loader_are_real_externally_pinned_bytes():
    before=set(sys.modules)
    value=q.fixture_identity()
    assert value['seed']==926603 and value['fixture_files_sha256']==q.FIXTURE_PINS
    assert value['source_pins_sha256']==q.PINS_SHA256
    assert value['public_loader_sha256']==q.LOADER_SHA256
    assert not q.FORBIDDEN.intersection(n.split('.')[0] for n in set(sys.modules)-before)


@pytest.mark.parametrize('name',list(q.FIXTURE_PINS))
def test_saved_fixture_mismatch_is_rejected_before_loader(monkeypatch,name):
    original=q.file_hash
    monkeypatch.setattr(q,'file_hash',lambda path:'0'*64 if Path(path)==q.ROOT/q.FIXTURE/name else original(path))
    with pytest.raises(ValueError,match='V7_GPU_FIXTURE_BYTES_CHANGED:'+name):
        q.fixture_identity()


def test_parent_pin_mismatch_is_rejected(monkeypatch):
    original=q.file_hash
    monkeypatch.setattr(q,'file_hash',lambda path:'0'*64 if Path(path)==q.ROOT/q.PINS_PATH else original(path))
    with pytest.raises(ValueError,match='V7_GPU_PARENT_SOURCE_PINS_CHANGED'):
        q.fixture_identity()


@pytest.mark.parametrize('relative',['.', 'runs', 'outside/result', 'runs/../outside'])
def test_output_must_be_strictly_inside_runs(monkeypatch,tmp_path,relative):
    monkeypatch.setattr(q,'ROOT',tmp_path)
    with pytest.raises(ValueError,match='V7_GPU_RUN_OUTPUT_REQUIRED'):
        q.run_path(tmp_path/relative)


def test_output_new_and_link_rules(monkeypatch,tmp_path):
    monkeypatch.setattr(q,'ROOT',tmp_path)
    path=tmp_path/'runs'/'test';path.mkdir(parents=True)
    assert q.run_path(path)==path
    with pytest.raises(ValueError,match='V7_GPU_RUN_OUTPUT_REQUIRED'):
        q.run_path(path,new=True)
    monkeypatch.setattr(Path,'is_symlink',lambda path:path.name=='test')
    with pytest.raises(ValueError,match='V7_GPU_LINK_REFUSED'):
        q.run_path(path)


def test_json_is_strict_and_write_is_new_only(tmp_path):
    path=tmp_path/'record.json'
    q.write(path,{'completed':True})
    assert q.read(path)=={'completed':True}
    with pytest.raises(FileExistsError): q.write(path,{})


@pytest.mark.parametrize('raw',[b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":1e999}'])
def test_ambiguous_or_nonfinite_json_rejected(tmp_path,raw):
    path=tmp_path/'record.json';path.write_bytes(raw)
    with pytest.raises(ValueError): q.read(path)


def test_pytest_command_uses_bound_basetemp_and_only_new_gpu_test(monkeypatch,tmp_path):
    monkeypatch.setattr(q,'ROOT',tmp_path)
    output=tmp_path/'runs'/'gate'
    command=q.pytest_command(output)
    assert command[:5]==[sys.executable,'-B','-m','pytest','-q']
    assert command[command.index('--basetemp')+1]==str(output/'gpu_tmp')
    assert command[command.index('--junitxml')+1]==str(output/'gpu_test.xml')
    assert 'cas_meta2.pytest_no_aliases_v4' in command and 'no:cacheprovider' in command
    assert [name for name in command if name.startswith('tests/')]==['tests/test_contrast_v7_train_gpu.py']
    (output/'gpu_tmp').mkdir(parents=True)
    with pytest.raises(ValueError,match='V7_GPU_NEW_PYTEST_BASETEMP_REQUIRED'): q.pytest_command(output)


def test_source_has_no_generation_or_old_worker_fallback():
    tree=ast.parse(Path(q.__file__).read_text())
    imports=[node for node in ast.walk(tree) if isinstance(node,ast.ImportFrom)]
    assert not any(alias.name in {'evaluation','_case_worker'} for node in imports for alias in node.names)
    assert any(alias.name=='native_evaluation' for node in imports for alias in node.names)
    assert not any(isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
        and isinstance(node.func.value,ast.Name) and node.func.value.id in {'c','curriculum'}
        and node.func.attr in {'generate','write'} for node in ast.walk(tree))
    module_imports=[node for node in tree.body if isinstance(node,(ast.Import,ast.ImportFrom))]
    assert not any(node.module and 'parent' in node.module for node in module_imports if isinstance(node,ast.ImportFrom))
    assert q.CONFIG=={'train_flat':32,'train_pairs_per_cell':8,'validation_flat':8,'validation_pairs_per_cell':2,'test_triplets':3}


def test_gpu_test_guard_precedes_all_project_imports_and_checks_job():
    tree=ast.parse((ROOT/'tests/test_contrast_v7_train_gpu.py').read_text())
    guard=next(i for i,node in enumerate(tree.body) if isinstance(node,ast.If))
    project=next(i for i,node in enumerate(tree.body) if isinstance(node,ast.ImportFrom) and node.module.startswith('cas_meta2'))
    assert guard<project
    body=ast.unparse(tree.body[guard])
    assert 'linux' in body and 'CAS_META2_RUN_PROTOTYPE_TRAINING' in body and 'CAS_META2_RUN_GPU_TESTS' in body
    assert 'q.require_request(JOB)' in ast.unparse(tree)


def test_checkpoint_function_checks_actual_exits_before_torch_import():
    tree=ast.parse(Path(q.__file__).read_text())
    fn=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='cuda_checkpoint_changes')
    imported=next(i for i,node in enumerate(fn.body) if isinstance(node,ast.Import) and node.names[0].name=='torch')
    prior=ast.unparse(ast.Module(body=fn.body[:imported],type_ignores=[]))
    assert 'require_request(job)' in prior and 'clean_coordinator()' in prior and 'exited_children(' in prior
    source=ast.unparse(fn)
    assert 'weights_only=True' in source and 'map_location=device' in source and "device.type == 'cuda'" in source


def test_unfinished_native_gate_rejects_before_imports(monkeypatch,tmp_path):
    enabled(monkeypatch)
    monkeypatch.setattr(q,'NATIVE_GATE_READY',False)
    helper=Mock(side_effect=AssertionError('No imports'))
    monkeypatch.setattr(q,'clean_coordinator',helper)
    with pytest.raises(ValueError,match='NATIVE_GATE_PENDING'): q.native_fixture(tmp_path,job=JOB)
    assert not helper.called


def process(pid,start,end):
    return {'pid':pid,'started_utc':f'2020-01-01T00:00:{start:02d}+00:00',
            'finished_utc':f'2020-01-01T00:00:{end:02d}+00:00'}


@pytest.mark.parametrize('fault',['overlap','same_pid','coordinator_pid'])
def test_child_exit_order_rejections(fault,tmp_path):
    prep,trained=process(11,0,1),process(12,2,3)
    if fault=='overlap': prep['finished_utc']=trained['finished_utc']
    if fault=='same_pid': trained['pid']=prep['pid']
    if fault=='coordinator_pid': trained['pid']=os.getpid()
    checks=SimpleNamespace(process_exit=Mock(side_effect=[prep,trained]),timestamp=datetime.fromisoformat)
    with pytest.raises(ValueError,match='CHILD_EXIT_ORDER'): q.exited_children(tmp_path,job=JOB,checks=checks)


def native_receipt():
    arms=('cas_untrained','cas_trained','generic_untrained','generic_trained','rule')
    return {'schema':'cas-meta2-prototype-native-evaluation/7','completed':True,'cases':9,'reference_cases':9,
        'arm_verdicts':45,'learning_accepted':False,
        'results':{arm:{'total':9,'task_correct':9 if arm=='rule' else 0,'all_cases_in_denominator':True,
                       'compute_complete':arm=='rule','post_admission_runtime_failures':0 if arm=='rule' else 1} for arm in arms},
        'groups':{group:{arm:{'total':count} for arm in arms} for group,count in
            (('depth_3',6),('depth_4',3),('same_depth',3),('wording_shift',3),('deeper_calls',3))}}


def test_native_smoke_keeps_failed_tick_unknown_and_actual_group_names():
    receipt=native_receipt()
    assert q.check_native_smoke(receipt)==receipt
    assert receipt['results']['cas_trained']['compute_complete'] is False


@pytest.mark.parametrize('fault',['cases','arms','rule','groups','unknown_compute','acceptance'])
def test_native_smoke_does_not_accept_partial_or_relabelled_results(fault):
    value=native_receipt()
    if fault=='cases': value['cases']=8
    if fault=='arms': value['arm_verdicts']=44
    if fault=='rule': value['results']['rule']['task_correct']=8
    if fault=='groups': value['groups']['depth_3']['cas_trained']['total']=9
    if fault=='unknown_compute': value['results']['cas_trained']['compute_complete']=True
    if fault=='acceptance': value['learning_accepted']=True
    with pytest.raises(ValueError,match='V7_GPU_NATIVE_'): q.check_native_smoke(value)


def mock_workflow(monkeypatch,tmp_path):
    enabled(monkeypatch)
    monkeypatch.setattr(q,'ROOT',tmp_path)
    monkeypatch.setattr(q,'clean_coordinator',Mock())
    fixture={'seed':q.SEED,'source_pins_sha256':q.PINS_SHA256,'public_loader_sha256':q.LOADER_SHA256}
    monkeypatch.setattr(q,'fixture_identity',lambda:fixture)
    monkeypatch.setattr(q,'file_hash',lambda path:sha256(str(path).encode()).hexdigest())
    source={'source.py':'1'*64};baseline={'accepted':'baseline'};events=[]
    def run_process(command,directory,deadline,environment):
        events.append(command[command.index('--phase')+1])
    receipts={'prepare_process':process(11,0,1),'training_process':process(12,2,3),'native_process':process(13,4,5)}
    def exit_record(path,*,expected_command):
        phase=expected_command[expected_command.index('--phase')+1]
        events.append(phase+'_exit_checked')
        return receipts[path.parent.name]
    gate={'completed':True,'private_test_labels_opened':False}
    receipt={'completed':True,'completed_epochs':1,'optimizer_steps':{'cas':22,'generic':22},
        'seal':{'test_examples':9,'prediction_count':36,'private_labels_read':False},'learning_accepted':False}
    def check_training(*args,**kwargs):
        events.append('training_checked')
        assert kwargs['expected_source']==source and kwargs['expected_baseline']==baseline
        assert kwargs['excluded']==frozenset() and kwargs['expected_loader_sha256']==q.LOADER_SHA256
        assert kwargs['config'].epochs==1 and kwargs['config'].max_seconds==900
        return gate
    checks=SimpleNamespace(process_exit=exit_record,timestamp=datetime.fromisoformat,
        check_training=check_training,read=lambda path:receipt)
    c=SimpleNamespace(Config=lambda **kwargs:SimpleNamespace(**kwargs))
    t=SimpleNamespace(source_identity=lambda:source,TrainingConfig=lambda **kwargs:SimpleNamespace(**kwargs))
    monkeypatch.setattr(q,'runtime_helpers',lambda:(c,t,checks,None,run_process,lambda:baseline))
    def assembly(*args,**kwargs):
        events.append('assembly_checked');return {'manifest_sha256':'2'*64}
    monkeypatch.setattr(q,'check_assembly',assembly)
    def checkpoints(*args,**kwargs):
        events.append('cuda_checkpoint_load')
        return {family:{'changed_count':1,'all_loaded_on_cuda':True} for family in ('cas','generic')}
    monkeypatch.setattr(q,'cuda_checkpoint_changes',checkpoints)
    original_read=q.read
    monkeypatch.setattr(q,'read',lambda path:native_receipt() if path.name=='native_receipt.json' else original_read(path))
    return tmp_path/'runs'/'mock_smoke',events,receipt


def test_mocked_training_workflow_waits_before_cuda_and_does_not_claim_native(monkeypatch,tmp_path):
    output,events,receipt=mock_workflow(monkeypatch,tmp_path)
    value=q.run_smoke(output,job=JOB)
    assert events==['prepare','prepare_exit_checked','assembly_checked','train','train_exit_checked',
                    'training_checked','cuda_checkpoint_load']
    assert value['native_evaluation_completed'] is False and value['native_receipt'] is None
    assert value['optimizer_steps']=={'cas':22,'generic':22}
    assert value['learning_accepted'] is False and value['task_generation'] is False
    assert q.read(output/'gpu_smoke_receipt.json')==value


def test_mocked_optional_native_is_a_third_child_after_checkpoint_load(monkeypatch,tmp_path):
    output,events,_=mock_workflow(monkeypatch,tmp_path)
    monkeypatch.setattr(q,'NATIVE_GATE_READY',True)
    value=q.run_smoke(output,job=JOB,include_native=True)
    assert events.index('cuda_checkpoint_load')<events.index('native')<events.index('native_exit_checked')
    assert value['native_evaluation_completed'] is True and value['native_receipt']['arm_verdicts']==45
    assert value['native_receipt_sha256'] and value['native_process_receipt_sha256']


def test_mocked_failed_training_recount_never_loads_checkpoints(monkeypatch,tmp_path):
    output,events,receipt=mock_workflow(monkeypatch,tmp_path)
    receipt['optimizer_steps']['cas']=21
    with pytest.raises(ValueError,match='ONE_EPOCH_RECOUNT'): q.run_smoke(output,job=JOB)
    assert 'cuda_checkpoint_load' not in events
    assert not(output/'gpu_smoke_receipt.json').exists()


def test_mocked_native_request_cannot_close_pending_gate(monkeypatch,tmp_path):
    output,events,_=mock_workflow(monkeypatch,tmp_path)
    monkeypatch.setattr(q,'NATIVE_GATE_READY',False)
    with pytest.raises(ValueError,match='NATIVE_GATE_PENDING'): q.run_smoke(output,job=JOB,include_native=True)
    assert not events and not output.exists()


def test_mocked_assembly_copies_saved_bytes_and_exports_only_eight_files(monkeypatch,tmp_path):
    enabled(monkeypatch)
    monkeypatch.setattr(q,'ROOT',tmp_path)
    monkeypatch.setattr(q,'clean_coordinator',Mock())
    monkeypatch.setattr(q,'fixture_identity',lambda:{'synthetic':True})
    source={'source.py':'1'*64}
    c=SimpleNamespace(Config=lambda **kwargs:SimpleNamespace(checked=lambda:SimpleNamespace(**kwargs)))
    t=SimpleNamespace(source_identity=lambda:source)
    monkeypatch.setattr(q,'runtime_helpers',lambda:(c,t,None,None,None,None))
    fixture=tmp_path/q.FIXTURE;fixture.mkdir(parents=True)
    pins={}
    for name in q.FIXTURE_PINS:
        raw=json.dumps({'synthetic_saved_bytes':name}).encode();(fixture/name).write_bytes(raw)
        pins[name]=sha256(raw).hexdigest()
    monkeypatch.setattr(q,'FIXTURE_PINS',pins)
    cold={'completed':True,'splits':q.EXPECTED_SPLITS,'prototype_tasks':256,'prototype_pairs':128,'tokenizer_fit_examples':352}
    def merge(base,dataset,**kwargs):
        assert base.name=='base_dataset' and dataset.name=='dataset' and base.parent==dataset.parent
        assert kwargs['expected_sha256']==pins['manifest.json'] and kwargs['excluded']==frozenset()
        assert all((base/name).read_bytes()==(fixture/name).read_bytes() for name in pins)
        dataset.mkdir();q.write(dataset/'manifest.json',{'synthetic_merged':True});return cold
    def export(dataset,out,**kwargs):
        out.mkdir()
        for name in q.PUBLIC_FILES:q.write(out/name,{'synthetic_export':name})
        return {'parent_validation':cold,'splits':q.EXPECTED_SPLITS,'base_train_examples':96,
            'imported_train_examples':256,'private_labels_read_by_loader':False,'test_programs_parsed_by_loader':False}
    parent=SimpleNamespace(merge=merge,validate_bundle=lambda *args,**kwargs:cold,export_training_bundle=export)
    import cas_meta2.contrast_v7 as package
    monkeypatch.setattr(package,'parent',parent,raising=False)
    output=tmp_path/'runs'/'prepare';output.mkdir(parents=True)
    value=q.prepare_fixture(output,job=JOB)
    assert value['splits']==q.EXPECTED_SPLITS and value['task_generation'] is False
    assert value['parent_process_must_exit_before_training'] is True
    assert set(value['public_export_files_sha256'])==q.PUBLIC_FILES
    assert not(output/'trainer_input/test_private.json').exists()
