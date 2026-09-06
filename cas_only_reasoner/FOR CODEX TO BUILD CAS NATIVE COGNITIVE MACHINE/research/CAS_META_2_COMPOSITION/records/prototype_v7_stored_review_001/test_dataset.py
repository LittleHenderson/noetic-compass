"""Small synthetic v7 review tests: no tasks, tensors, providers or runtime execution."""
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import importlib.util
from pathlib import Path,PurePosixPath
from types import SimpleNamespace
import zipfile

import pytest

HERE=Path(__file__).resolve().parent


def load(name):
    spec=importlib.util.spec_from_file_location('_test_v7_review_'+name,HERE/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


c=load('common')
d=load('dataset')
JOB='cas-meta2-20260906000000-12345678'
PIN='a'*64
PYTHON='/opt/cas-meta2/venv/bin/python'
REMOTE='/opt/cas-meta2/package/'+c.PILOT


def spec():
    return {'public_loader_sha256':'b'*64,'source_pins_path':'records/source_pins.json',
        'source_pins_sha256':'c'*64,'exclusion_inventory_path':'records/exclusions.json',
        'exclusion_inventory_sha256':'d'*64,'curriculum_seed':12345}


def choices():
    # Deliberately not valid CAS programs or generated curriculum records.
    publics=[{'synthetic_index':i,'permitted_observation':i+100} for i in range(72)]
    tasks=[{'synthetic_case':i} for i in range(72)]
    def rule(public):return {'synthetic_rule':public['synthetic_index']}
    rows=[{'case_index':i,'public_sha256':c.digest(public),
        'actions':{**{arm:{'opaque_choice':i,'arm':arm} for arm in c.ARMS[:-1]},'rule':rule(public)}}
        for i,public in enumerate(publics)]
    neural=[{**row,'actions':{arm:deepcopy(row['actions'][arm]) for arm in c.ARMS[:-1]}} for row in rows]
    return neural,rows,tasks,publics,rule


def bind(data):
    neural,rows,tasks,publics,rule=data
    return d.bind_choices(neural,rows,tasks,publics,canonical=c.digest,parse=rule,c=c)


def test_72_choices_bind_four_neural_arms_plus_public_only_rule():
    data=choices();calls=[];actual=data[-1]
    data=(*data[:-1],lambda public:(calls.append(public),actual(public))[1])
    assert bind(data) is None
    assert calls==data[3] and len(calls)==72


@pytest.mark.parametrize('part',range(4))
@pytest.mark.parametrize('count',[0,71,73])
def test_any_missing_or_extra_case_rejects_before_attribution(part,count):
    data=list(choices());items=data[part]
    data[part]=items[:count] if count<=72 else items+[deepcopy(items[-1])]
    with pytest.raises(ValueError,match='EXACT_72'):bind(data)


@pytest.mark.parametrize('fault',['reorder','duplicate','case_index','bool_index','public_pin','extra_field',
    'missing_arm','extra_arm','neural_choice','neural_public','neural_extra','rule'])
def test_relabelled_or_mismatched_predictions_are_rejected(fault):
    data=choices();neural,rows,tasks,publics,_=data
    if fault=='reorder':rows[7],rows[8]=rows[8],rows[7]
    if fault=='duplicate':rows[8]=deepcopy(rows[7])
    if fault=='case_index':rows[7]['case_index']=8
    if fault=='bool_index':rows[1]['case_index']=True
    if fault=='public_pin':rows[7]['public_sha256']='f'*64
    if fault=='extra_field':rows[7]['target']='not allowed'
    if fault=='missing_arm':rows[7]['actions'].pop('generic_untrained')
    if fault=='extra_arm':rows[7]['actions']['new_arm']={}
    if fault=='neural_choice':neural[7]['actions']['cas_trained']={'opaque_choice':'changed'}
    if fault=='neural_public':neural[7]['public_sha256']='e'*64
    if fault=='neural_extra':neural[7]['extra']=0
    if fault=='rule':rows[7]['actions']['rule']={'synthetic_rule':'gold leaked'}
    with pytest.raises(ValueError,match='SEALED_CHOICE_ATTRIBUTION|RULE_NOT_PUBLIC_DERIVED'):bind(data)


def test_command_lists_equal_frozen_campaign_templates(monkeypatch):
    with c.pure_guard():
        from cas_meta2.contrast_v7 import campaign
        monkeypatch.setattr(campaign,'Path',PurePosixPath)
        monkeypatch.setattr(campaign,'ROOT',PurePosixPath(REMOTE))
        monkeypatch.setattr(campaign.sys,'executable',PYTHON)
        monkeypatch.setattr(campaign,'require_assembly',lambda output,settings:{'manifest_sha256':PIN})
        expected=d.commands(c.BASE,JOB,spec(),PIN,c)
        output=PurePosixPath(REMOTE+'/runs/'+c.BASE.rstrip('/'))
        assert expected['training']==campaign.training_command(output,JOB,spec())
        for name in ('dataset','evaluate'):
            assert expected[name]==campaign.dataset_command(output,JOB,name)
        assert '--execute' not in sum(expected.values(),[])


@dataclass
class Config:
    synthetic_count:int=9


class FakePacket:
    def __init__(self,documents):
        self.documents=documents;self.reads=[]
        self.inventory={name:{'sha256':c.digest(value)} for name,value in documents.items()}
    def json(self,name):
        self.reads.append(name);return deepcopy(self.documents[name])


def cold_fixture():
    cfg=Config();settings=spec();source={'synthetic_source.py':'e'*64};excluded=frozenset({'f'*64,'0'*64})
    request={'job':JOB,'private_data':REMOTE+'/runs/'+c.BASE+'dataset','expected_sha256':PIN,
        'seed':settings['curriculum_seed'],'config':{'synthetic_count':9},'excluded':sorted(excluded),
        'pins':REMOTE+'/'+settings['source_pins_path'],'expected_pins_sha256':settings['source_pins_sha256'],
        'expected_loader_sha256':settings['public_loader_sha256'],'source_sha256':source}
    report={'completed':True,'synthetic_report':True}
    packet=FakePacket({c.NATIVE+'cold_validation_request.json':request,
        c.NATIVE+'cold_dataset_validation.json':report})
    parent={'pid':100,'started_utc':'2026-09-06T00:00:00+00:00','finished_utc':'2026-09-06T00:00:20+00:00'}
    child={'pid':101,'started_utc':'2026-09-06T00:00:03+00:00','finished_utc':'2026-09-06T00:00:10+00:00'}
    calls=[]
    def process(current,name,command,common):
        assert current is packet and common is c
        assert packet.reads==[c.NATIVE+'cold_validation_request.json']
        calls.append((name,command));return child
    evidence=SimpleNamespace(process=process,timestamp=lambda value,common:datetime.fromisoformat(value))
    options=dict(native_base=c.NATIVE,parent_report=report,job=JOB,spec=settings,cfg=cfg,
        excluded=excluded,source=source,manifest_pin=PIN,process=parent,c=c,evidence=evidence)
    return packet,options,child,calls


def test_cold_child_exact_request_pin_command_and_exit_precede_report():
    packet,options,child,calls=cold_fixture()
    assert d.cold_child(packet,**options)==child
    out=REMOTE+'/runs/'+c.NATIVE.rstrip('/')
    expected=[PYTHON,'-B','-c',
        'import sys;from cas_meta2.contrast_v7.native_evaluation import validate_private_child;'
        'validate_private_child(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4])',
        out+'/cold_validation_request.json',packet.inventory[c.NATIVE+'cold_validation_request.json']['sha256'],
        out+'/cold_dataset_validation.json',JOB]
    assert calls==[(c.NATIVE+'cold_validation_process/process_receipt.json',expected)]
    assert packet.reads==[c.NATIVE+'cold_validation_request.json',c.NATIVE+'cold_dataset_validation.json']


@pytest.mark.parametrize('field,value',[('job','wrong'),('private_data','wrong'),('expected_sha256','0'*64),
    ('seed',777),('config',{}),('excluded',[]),('pins','wrong'),('expected_pins_sha256','0'*64),
    ('expected_loader_sha256','0'*64),('source_sha256',{})])
def test_cold_child_request_changes_stop_before_process_or_report(field,value):
    packet,options,child,calls=cold_fixture()
    packet.documents[c.NATIVE+'cold_validation_request.json'][field]=value
    with pytest.raises(ValueError,match='COLD_REQUEST_ATTRIBUTION'):d.cold_child(packet,**options)
    assert calls==[] and packet.reads==[c.NATIVE+'cold_validation_request.json']


@pytest.mark.parametrize('fault',['same_pid','before_parent','after_parent','reversed','zero_duration'])
def test_cold_child_invalid_exit_order_stops_before_report(fault):
    packet,options,child,calls=cold_fixture()
    if fault=='same_pid':child['pid']=100
    if fault=='before_parent':child['started_utc']='2026-09-05T23:59:59+00:00'
    if fault=='after_parent':child['finished_utc']='2026-09-06T00:00:21+00:00'
    if fault=='reversed':child['finished_utc']='2026-09-06T00:00:01+00:00'
    if fault=='zero_duration':child['finished_utc']=child['started_utc']
    with pytest.raises(ValueError,match='COLD_EXIT_ORDER'):d.cold_child(packet,**options)
    assert len(calls)==1 and packet.reads==[c.NATIVE+'cold_validation_request.json']


def test_cold_child_failed_process_prevents_report_read():
    packet,options,child,calls=cold_fixture()
    def fail(*args):raise ValueError('synthetic process failure')
    options['evidence'].process=fail
    with pytest.raises(ValueError,match='synthetic process failure'):d.cold_child(packet,**options)
    assert packet.reads==[c.NATIVE+'cold_validation_request.json']


def test_cold_child_report_must_equal_independent_parent_recount():
    packet,options,child,calls=cold_fixture()
    packet.documents[c.NATIVE+'cold_dataset_validation.json']={'completed':True,'synthetic_report':False}
    with pytest.raises(ValueError,match='COLD_RECOUNT_COPY'):d.cold_child(packet,**options)


@pytest.mark.parametrize('name',['../escape','/absolute','C:/root','a\\b','a//b','a/./b','a/../b'])
def test_common_refuses_unsafe_member_names(name):
    with pytest.raises(ValueError,match='UNSAFE_MEMBER'):c.safe_name(name)


@pytest.mark.parametrize('raw',[b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":1e999}'])
def test_common_json_rejects_ambiguous_or_nonfinite_records(raw):
    with pytest.raises(ValueError):c.decode(raw)


def test_common_packet_checks_extracted_bytes_and_refuses_later_changes(monkeypatch,tmp_path):
    monkeypatch.setattr(c,'HERE',tmp_path)
    archive=tmp_path/'synthetic.zip'
    with zipfile.ZipFile(archive,'w') as stream:stream.writestr('cloud_job/public_receipt.json',b'{"synthetic":true}')
    packet=c.Packet(archive,sha256(archive.read_bytes()).hexdigest(),tmp_path/'extracted',create=True)
    assert packet.json('cloud_job/public_receipt.json')=={'synthetic':True}
    (packet.root/'cloud_job/public_receipt.json').write_bytes(b'{"synthetic":false}')
    with pytest.raises(ValueError,match='EXTRACTED_BYTES_CHANGED'):packet.verify_all()
