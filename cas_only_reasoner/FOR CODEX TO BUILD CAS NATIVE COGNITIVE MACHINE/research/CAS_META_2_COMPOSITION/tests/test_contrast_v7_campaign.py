"""Synthetic-only v7 orchestration tests. Never generate a registered dataset."""
import ast
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from cas_meta2.contrast_v7 import campaign as q
from tools import experiment_profiles_prototype_v7 as p

ROOT = Path(__file__).resolve().parents[1]
SPEC = p.FIXED_SPEC


def metadata():
    excluded = frozenset(f'{i:064x}' for i in range(8837))
    expected = q.expected_splits(SPEC)
    heldout = {name: sha256(name.encode()).hexdigest() for name in
               ('validation.json','test_public.json','test_private.json')}
    base = {'splits': {**expected, 'train': {'tasks':640,'depths':{'1':128,'2':256,'3':256}}},
            'sha256': heldout}
    merged = {'schema':'cas-meta2-prototype-training-integration/7', 'dataset_id':'fixture',
        'splits':expected, 'training_append_count':256, 'pair_members_kept_together':True,
        'base':{'manifest_sha256':'1'*64, 'seed':SPEC['curriculum_seed'], 'config':SPEC['curriculum'],
                'exclusion_count':8837, 'exclusions_sha256':q.d.digest(p.canonical(sorted(excluded)))},
        'prototype':{'tasks':256,'pairs':128,'depths':{'2':128,'3':128},
            'tasks_sha256':SPEC['original_tasks_sha256'], 'allowed_split':'train',
            'fresh_evaluation':False, 'original_provenance_preserved':True},
        'heldout_bytes_unchanged':heldout, 'sha256':{**heldout,'train.json':'a'*64}}
    cold = {'schema':'cas-meta2-prototype-integration-validation/7','completed':True,
        'manifest_sha256':'2'*64,'dataset_id':'fixture','splits':expected,'prototype_tasks':256,
        'prototype_pairs':128,'heldout_bytes_unchanged':heldout,'tokenizer_fit_examples':896,
        'parent_reads_private_test_targets':True,'training_performed':False}
    exported = {'schema':'cas-meta2-public-training-bundle/7','dataset_id':'fixture','manifest_sha256':'2'*64,
        'splits':expected,'base_train_examples':640,'imported_train_examples':256,'tokenizer_fit_examples':896,
        'private_labels_read_by_loader':False,'test_programs_parsed_by_loader':False,
        'parent_validation_replayed_by_loader':False,'parent_validation':cold,'training_performed':False,
        'loaded_sha256':{name: pin for name,pin in merged['sha256'].items() if name!='test_private.json'}}
    return base, merged, cold, exported, excluded


def verify(values):
    base, merged, cold, exported, excluded = values
    return q.validate_assembly_records(base,merged,cold,exported,spec=SPEC,
                                      base_pin='1'*64,merged_pin='2'*64,excluded=excluded)


def test_registered_counts_and_seed():
    actual = p.validate_prototype_spec((ROOT/'EXPERIMENT_PROTOTYPE_V7.json').read_bytes())
    cfg, train = q.configurations(actual)
    assert actual['curriculum_seed'] == 2026092701 and cfg.train_flat+8*cfg.train_pairs_per_cell == 640
    assert actual['train_count'] == 896 and actual['train_depths'] == {'1':128,'2':384,'3':384}
    assert actual['optimizer_steps_per_family'] == (896//train.batch_size)*train.epochs == 11200
    assert actual['exclusion_count'] == 8837
    assert actual['test_count'] == 72 and actual['matched_test_triplets'] == 24


@pytest.mark.parametrize('field,value', [
    ('curriculum_seed',2026092601),('train_count',640),('original_train_append_count',255),
    ('exclusion_count',8053),('exclusion_inventory_sha256','0'*64),('public_loader_sha256','0'*64),
    ('source_pins_sha256','0'*64),('execution_enabled',True),('training_permitted',True),
    ('private_test_labels_in_trainer',True),('automatic_promotion',True),('original_tasks_training_only',False),
    ('original_graphs_remain_in_fresh_exclusions',False),('optimizer_steps_per_family',8000),
])
def test_spec_changes_are_not_an_implicit_gate_override(field,value):
    spec = deepcopy(SPEC);spec[field]=value
    with pytest.raises(ValueError,match='SPEC_IDENTITY'):
        p.validate_prototype_spec(p.canonical(spec))


def test_pending_gates_prevent_all_campaign_entrypoints(monkeypatch,tmp_path):
    monkeypatch.setattr(q,'registered_spec',lambda:deepcopy(SPEC))
    monkeypatch.setattr(q.c,'write',Mock(side_effect=AssertionError('No generation')))
    monkeypatch.setattr(q.t,'run',Mock(side_effect=AssertionError('No training')))
    monkeypatch.setattr(q,'parent_module',Mock(side_effect=AssertionError('No parent execution')))
    for call in (lambda:q.run(tmp_path,job='fixture'),lambda:q.run_phase(tmp_path,'fixture','dataset'),
                 lambda:q.run_phase(tmp_path,'fixture','evaluate'),
                 lambda:q.assemble_dataset(tmp_path,job='fixture',spec=SPEC)):
        with pytest.raises(ValueError,match='V7_PREPARATION_ONLY'):
            call()
    assert not q.c.write.called and not q.t.run.called
    assert p.execution_blockers(SPEC)==list(p.PENDING)


def test_only_exception_contained_native_evaluator_is_wired():
    tree=ast.parse((ROOT/'cas_meta2/contrast_v7/campaign.py').read_text())
    imports=[node for node in ast.walk(tree) if isinstance(node,ast.ImportFrom)]
    assert not any(alias.name in {'evaluation','_case_worker'} for node in imports for alias in node.names)
    assert any(alias.name == 'native_evaluation' for node in imports for alias in node.names)
    assert p.execution_blockers(SPEC) == list(p.PENDING)


def test_correct_synthetic_assembly_counts():
    result=verify(metadata())
    assert result['actual_splits']['train']['tasks']==896
    assert result['optimizer_steps_per_family']==11200


@pytest.mark.parametrize('lane', ['base_train','merged_depth','append','base_seed','exclusions','prototype',
                                  'heldout','cold','export_private','export_count','export_pin'])
def test_assembly_rejects_count_identity_and_label_boundary_changes(lane):
    values=metadata();base,merged,cold,exported,_=values
    if lane=='base_train':base['splits']['train']['tasks']=639
    elif lane=='merged_depth':merged['splits']=deepcopy(merged['splits']);merged['splits']['train']['depths']['2']=383
    elif lane=='append':merged['training_append_count']=255
    elif lane=='base_seed':merged['base']['seed']=1
    elif lane=='exclusions':merged['base']['exclusion_count']=8053
    elif lane=='prototype':merged['prototype']['allowed_split']='test'
    elif lane=='heldout':merged['heldout_bytes_unchanged']=dict(merged['heldout_bytes_unchanged']);merged['heldout_bytes_unchanged']['test_private.json']='0'*64
    elif lane=='cold':cold['completed']=False
    elif lane=='export_private':exported['loaded_sha256']['test_private.json']=merged['sha256']['test_private.json']
    elif lane=='export_count':exported['base_train_examples']=896
    else:exported['loaded_sha256']['train.json']='0'*64
    with pytest.raises(ValueError):
        verify(values)


def test_synthetic_data_phase_calls_generate_merge_validate_export_in_order(monkeypatch,tmp_path):
    base,merged,cold,exported,excluded=metadata()
    output=tmp_path/'runs'/'synthetic';output.mkdir(parents=True)
    events=[];saved={}
    monkeypatch.setattr(q,'ROOT',tmp_path)
    monkeypatch.setattr(q.profile,'require_execution_ready',lambda _:None)
    monkeypatch.setattr(q.t,'require_request',lambda *args:None)
    monkeypatch.setattr(q,'check_gpu_phase',lambda *args,**kwargs:{'synthetic':True})
    monkeypatch.setattr(q,'checked_inputs',lambda _:excluded)
    monkeypatch.setattr(q,'source_identity',lambda:{'fixture':'pinned'})
    monkeypatch.setattr(q.c,'write',lambda path,**kw:events.append(('base',path,kw)))
    def merge(a,b,**kw):
        events.append(('merge',a,b,kw));return deepcopy(cold)
    def validate(path,**kw):
        events.append(('validate',path,kw));return deepcopy(cold)
    def export(a,b,**kw):
        events.append(('export',a,b,kw));return deepcopy(exported)
    monkeypatch.setattr(q,'parent_module',lambda:SimpleNamespace(merge=merge,validate_bundle=validate,export_training_bundle=export))
    monkeypatch.setattr(q.checks,'file_hash',lambda path:'1'*64 if 'base_dataset' in path.parts else '2'*64)
    monkeypatch.setattr(q.checks,'read',lambda path:deepcopy(base if 'base_dataset' in path.parts else merged))
    monkeypatch.setattr(q.t,'write_new',lambda path,value:saved.update({path.name:deepcopy(value)}))
    result=q.assemble_dataset(output,job='synthetic-job',spec=SPEC)
    assert [row[0] for row in events]==['base','merge','validate','export']
    assert events[0][1].name=='base_dataset' and events[0][2]['seed']==2026092701
    assert events[1][1].name=='base_dataset' and events[1][2].name=='dataset'
    assert events[-1][2].name=='trainer_input'
    assert events[1][3]['expected_pins_sha256']==SPEC['source_pins_sha256']
    assert events[-1][3]['expected_loader_sha256']==SPEC['public_loader_sha256']
    assert result['actual_splits']['train']['tasks']==896 and result['training_started'] is False
    assert set(saved)=={'curriculum_config.json','training_config.json','experiment.json',
                        'training_bundle_receipt.json','dataset_assembly_receipt.json'}
    assert saved['training_config.json']==SPEC['training']
    assert saved['curriculum_config.json']==SPEC['curriculum']
    assert not (output/'base_dataset').exists()  # Generator was a stub, no actual data created.


def assembly_receipt():
    return {'schema':q.SCHEMA,'completed':True,'actual_splits':q.expected_splits(SPEC),
        'optimizer_steps_per_family':11200,'manifest_sha256':'2'*64,
        'source_pins_sha256':SPEC['source_pins_sha256'],'public_loader_sha256':SPEC['public_loader_sha256'],
        'exclusion_inventory_sha256':SPEC['exclusion_inventory_sha256'],'exclusion_count':8837,
        'original_tasks_sha256':SPEC['original_tasks_sha256'],'original_training_only':True,
        'all_original_graphs_remain_in_fresh_exclusions':True,'training_started':False,'neural_execution':False}


def test_training_command_carries_all_external_pins(monkeypatch,tmp_path):
    monkeypatch.setattr(q.checks,'read',lambda _:assembly_receipt())
    monkeypatch.setattr(q.checks,'file_hash',lambda _:'2'*64)
    command=q.training_command(tmp_path,'fixture',SPEC)
    for flag,value in [('--manifest-sha256','2'*64),('--loader-sha256',SPEC['public_loader_sha256']),
                       ('--exclusions-sha256',SPEC['exclusion_inventory_sha256']),('--curriculum-seed','2026092701')]:
        assert command[command.index(flag)+1]==value
    assert command[3]=='cas_meta2.contrast_v7.train'
    assert not any('parent' in item or 'test_private' in item for item in command)


def test_no_training_command_without_actual_assembly_receipt(monkeypatch,tmp_path):
    value=assembly_receipt();value['actual_splits']={}
    monkeypatch.setattr(q.checks,'read',lambda _:value)
    monkeypatch.setattr(q.checks,'file_hash',lambda _:'2'*64)
    with pytest.raises(ValueError,match='ACTUAL_ASSEMBLY'):
        q.training_command(tmp_path,'fixture',SPEC)


def test_source_pin_map_is_literal_and_profile_is_nonlaunchable():
    raw=(ROOT/SPEC['source_pins_path']).read_bytes()
    mapping=p.pinned_source_map(raw)
    assert len(mapping)==16
    assert mapping[p.PILOT+'/'+SPEC['original_tasks_path']]==SPEC['original_tasks_sha256']
    with pytest.raises(ValueError,match='SOURCE_PINS_CHANGED'):
        p.pinned_source_map(raw+b' ')
    with pytest.raises(ValueError,match='V7_PREPARATION_ONLY'):
        p.require_execution_ready(SPEC)


def test_trainer_has_no_parent_or_private_import_regression():
    tree=ast.parse((ROOT/'cas_meta2/contrast_v7/train.py').read_text())
    imports=[node for node in ast.walk(tree) if isinstance(node,ast.ImportFrom)]
    assert not any(node.module and ('parent' in node.module or 'adapter' in node.module) for node in imports)
    assert not any(alias.name in {'parent','adapter'} for node in imports for alias in node.names)


def test_pure_import_has_no_neural_module():
    import sys
    assert not {'torch','casformer','cas_cjt','boto3'} & set(sys.modules)


def test_actual_registered_inputs_are_pinned_without_generation():
    excluded=q.checked_inputs(SPEC)
    assert len(excluded)==8837
    old=json.loads((ROOT/'records/contrast_v6_exclusions_001/inventory.json').read_bytes())
    assert set(old['graph_signatures'])<=excluded


def test_prepared_data_phase_still_refuses_laptop(monkeypatch,tmp_path):
    monkeypatch.setattr(q.profile,'require_execution_ready',lambda _:None)
    monkeypatch.setattr(q.t.sys,'platform','win32')
    monkeypatch.setattr(q,'checked_inputs',Mock(side_effect=AssertionError('No input work on laptop')))
    with pytest.raises(ValueError,match='CONTRAST_AWS_LINUX_REQUIRED'):
        q.assemble_dataset(tmp_path,job='fixture',spec=SPEC)
    assert not q.checked_inputs.called


def test_training_gate_uses_public_loader_and_unchanged_training_source(monkeypatch,tmp_path):
    value=assembly_receipt();value['source_sha256']={'campaign':'pinned'}
    initial={'source_sha256':{'trainer':'pinned'},'campaign_source_sha256':{'campaign':'pinned'},'baseline':{'fixture':True}}
    monkeypatch.setattr(q.checks,'read',lambda path:initial if path.name=='initial_identity.json' else value)
    monkeypatch.setattr(q.checks,'file_hash',lambda _:'2'*64)
    monkeypatch.setattr(q,'checked_inputs',lambda _:frozenset({'fixture'}))
    monkeypatch.setattr(q,'source_identity',lambda:{'campaign':'pinned'})
    monkeypatch.setattr(q.t,'source_identity',lambda:{'trainer':'pinned'})
    gate=q.gate_arguments(tmp_path,'fixture',SPEC)
    assert gate['expected_loader_sha256']==SPEC['public_loader_sha256']
    assert gate['expected_source']=={'trainer':'pinned'}
    assert gate['expected_baseline']==initial['baseline']
    assert gate['expected_manifest_sha256']=='2'*64
    assert 'pins' not in gate and 'parent' not in gate


def test_profile_record_pins_sources_and_cannot_dispatch():
    pin_raw=(ROOT/SPEC['source_pins_path']).read_bytes()
    names={**p.pinned_source_map(pin_raw),**p.EXTRA_INPUTS}
    members={name:(ROOT.parents[1]/name).read_bytes() for name in names}
    members.update({p.PILOT+'/'+name:b'# inert source fixture\n' for name in p.V7_LOCAL_FILES})
    members[p.SPEC_PATH]=(ROOT/'EXPERIMENT_PROTOTYPE_V7.json').read_bytes()
    record=p.make_record(members)
    manifest={'experiment':record,'files_sha256':{name:sha256(raw).hexdigest() for name,raw in members.items()}}
    assert p.validate_manifest(manifest,members.__getitem__)==record
    with pytest.raises(ValueError,match='V7_PREPARATION_ONLY'):
        p.entrypoint(manifest)
    members[p.SOURCE_PINS_PATH]+=b' '
    with pytest.raises(ValueError,match='SOURCE_PINS_CHANGED'):
        p.make_record(members)
