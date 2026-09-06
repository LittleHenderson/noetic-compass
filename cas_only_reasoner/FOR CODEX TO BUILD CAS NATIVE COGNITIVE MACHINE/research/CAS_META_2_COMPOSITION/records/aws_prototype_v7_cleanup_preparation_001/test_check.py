"""Synthetic provider responses only. No credentials, clients or real calls."""
from copy import deepcopy
from datetime import datetime,timezone
from decimal import Decimal
import importlib.util
from io import BytesIO
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

path=Path(__file__).with_name('check.py')
loader=importlib.util.spec_from_file_location('v7_cleanup_check_under_test',path)
c=importlib.util.module_from_spec(loader);loader.loader.exec_module(c)
START=datetime(2026,9,6,9,40,18,tzinfo=timezone.utc)
END=datetime(2026,9,6,10,40,20,tzinfo=timezone.utc)


def meta():
    return {'ResponseMetadata':{'RequestId':'synthetic-request-id',
        'HTTPHeaders':{'date':'Sun, 06 Sep 2026 10:40:20 GMT'}}}


class FakeError(Exception):
    def __init__(self,code):self.response={**meta(),'Error':{'Code':code}}


def launch():
    plan={'account_id':c.ACCOUNT,'region':c.REGION,'instance_type':'g7.2xlarge','instance_count':1,
        'runtime_seconds_max':7800,'compute_seconds_max':7200,'per_launch_reserved_cap_usd':'7.00',
        'owner_task_cap_usd':'400.00','on_demand_hourly_usd_max':'2.52','ancillary_reserved_usd':'1.00',
        'automatic_retries':0}
    price={'product':{'attributes':{'instanceType':'g7.2xlarge','regionCode':c.REGION,
        'operatingSystem':'Linux','tenancy':'Shared','marketoption':'OnDemand'}},
        'terms':{'OnDemand':{'synthetic':{'priceDimensions':{'synthetic':{'unit':'Hrs',
            'pricePerUnit':{'USD':'2.5200000000'}}}}}}}
    return {'job':c.JOB,'source_sha':c.SOURCE,'archive_sha256':c.ARCHIVE,'run_instances_client_token':c.JOB,
        'smoke_only':False,'status':'AWS_JOB_FINISHED','provider_launch_time':START.isoformat(),
        'resources':{'instance':c.INSTANCE,'security_group':c.GROUP,'bucket':c.BUCKET,'schedule':c.JOB,
            'instance_profile':c.JOB+'-worker',c.JOB+'-worker':'arn:aws:iam::'+c.ACCOUNT+':role/'+c.JOB+'-worker',
            c.JOB+'-timer':'arn:aws:iam::'+c.ACCOUNT+':role/'+c.JOB+'-timer'},'plan':plan,
        'task_budget_reservation':{'reservation':{'job':c.JOB,'source_sha':c.SOURCE,'archive_sha256':c.ARCHIVE,
            'reserved_usd':'7.00','status':'RESERVED_NO_AUTOMATIC_REFUND','plan':deepcopy(plan)}},
        'official_price_response':[json.dumps(price)],'result':{'job':c.JOB,'returncode':0,'sha256':'a'*64,'bytes':100}}


def clients(receipt):
    instances={**meta(),'Reservations':[{'OwnerId':c.ACCOUNT,'Instances':[{
        'InstanceId':c.INSTANCE,'ClientToken':c.JOB,'Tags':[{'Key':'cas_meta_job','Value':c.JOB}],
        'InstanceType':'g7.2xlarge','LaunchTime':START,'State':{'Name':'terminated'},
        'StateTransitionReason':'User initiated (2026-09-06 10:40:00 GMT)'}]}]}
    complete={**meta(),'Body':BytesIO(json.dumps(receipt['result']).encode()),
        'LastModified':datetime(2026,9,6,10,39,18,tzinfo=timezone.utc)}
    return {'sts':SimpleNamespace(get_caller_identity=Mock(return_value={**meta(),'Account':c.ACCOUNT})),
        'ec2':SimpleNamespace(describe_instances=Mock(return_value=instances),
            describe_volumes=Mock(return_value={**meta(),'Volumes':[]}),
            describe_security_groups=Mock(side_effect=FakeError('InvalidGroup.NotFound'))),
        'iam':SimpleNamespace(get_instance_profile=Mock(side_effect=FakeError('NoSuchEntity')),
            get_role=Mock(side_effect=FakeError('NoSuchEntity'))),
        'scheduler':SimpleNamespace(get_schedule=Mock(side_effect=FakeError('ResourceNotFoundException'))),
        's3':SimpleNamespace(get_object=Mock(return_value=complete))}


def test_exact_seven_identities_and_only_nine_read_calls():
    value=launch();api=clients(value);result=c.observe(api,value,now=END)
    assert result['cleanup_passed'] is True and result['passed_checks']==7
    assert tuple(row['check'] for row in result['checks'])==c.CHECKS
    assert all(row['provider_http_date']=='Sun, 06 Sep 2026 10:40:20 GMT' for row in result['checks'])
    api['ec2'].describe_instances.assert_called_once_with(InstanceIds=[c.INSTANCE])
    api['ec2'].describe_volumes.assert_called_once_with(Filters=[{'Name':'tag:cas_meta_job','Values':[c.JOB]}])
    api['ec2'].describe_security_groups.assert_called_once_with(GroupIds=[c.GROUP])
    api['iam'].get_instance_profile.assert_called_once_with(InstanceProfileName=c.JOB+'-worker')
    assert api['iam'].get_role.call_args_list[0].kwargs=={'RoleName':c.JOB+'-worker'}
    assert api['iam'].get_role.call_args_list[1].kwargs=={'RoleName':c.JOB+'-timer'}
    api['scheduler'].get_schedule.assert_called_once_with(Name=c.JOB,GroupName='default')
    api['s3'].get_object.assert_called_once_with(Bucket=c.BUCKET,Key='results/complete.json',ExpectedBucketOwner=c.ACCOUNT)
    assert sum(method.call_count for client in api.values() for method in vars(client).values())==9
    assert result['reservation_changed'] is False and result['automatic_refund'] is False
    assert result['completion_object']['matches_final_launch_result'] is True


def test_cost_uses_provider_dates_and_does_not_claim_invoice_or_termination_time():
    value=launch();result=c.observe(clients(value),value,now=END)['cost']
    assert result['launch_to_termination_observation']['elapsed_seconds']=='3603.0'
    assert Decimal(result['launch_to_termination_observation']['compute_only_usd_estimate'])==Decimal('2.5221')
    assert result['launch_to_completion_object']['elapsed_seconds']=='3540.0'
    assert result['actual_termination_timestamp_known'] is False
    assert result['is_invoice'] is False and result['actual_total_cost_established'] is False
    assert result['reservation_covers_observed_compute_plus_allowance'] is True


@pytest.mark.parametrize('field,value',[('instance','i-wrong'),('security_group','sg-wrong'),
    ('bucket','wrong'),('schedule','wrong'),('instance_profile','wrong')])
def test_foreign_recorded_resources_stop_before_any_provider_call(field,value):
    record=launch();record['resources'][field]=value;api=clients(record)
    with pytest.raises(ValueError,match='EXACT_LAUNCH_RESOURCES'):c.observe(api,record)
    assert not api['sts'].get_caller_identity.called


def test_incomplete_launch_receipt_stops_before_provider_calls():
    record=launch();record['status']='STARTING';api=clients(record)
    with pytest.raises(ValueError,match='WAIT_FOR_FINAL'):c.observe(api,record)
    assert not api['sts'].get_caller_identity.called


def test_wrong_account_stops_all_resource_reads():
    record=launch();api=clients(record);api['sts'].get_caller_identity.return_value['Account']='wrong'
    with pytest.raises(ValueError,match='AWS_ACCOUNT_MISMATCH'):c.observe(api,record)
    assert not api['ec2'].describe_instances.called


@pytest.mark.parametrize('fault',['running','foreign_token','foreign_tag','foreign_instance','foreign_owner',
    'launch_time','volume','pagination','access_denied','resource_exists','missing_provider_date'])
def test_cleanup_cannot_report_success_with_live_unknown_or_wrong_resources(fault):
    record=launch();api=clients(record)
    reservation=api['ec2'].describe_instances.return_value['Reservations'][0];item=reservation['Instances'][0]
    if fault=='running':item['State']['Name']='running'
    if fault=='foreign_token':item['ClientToken']='other'
    if fault=='foreign_tag':item['Tags'][0]['Value']='other'
    if fault=='foreign_instance':item['InstanceId']='other'
    if fault=='foreign_owner':reservation['OwnerId']='other'
    if fault=='launch_time':item['LaunchTime']=END
    if fault=='volume':api['ec2'].describe_volumes.return_value['Volumes']=[{'VolumeId':'vol-existing'}]
    if fault=='pagination':api['ec2'].describe_volumes.return_value['NextToken']='more'
    if fault=='access_denied':api['iam'].get_role.side_effect=FakeError('AccessDenied')
    if fault=='resource_exists':api['scheduler'].get_schedule.side_effect=None;api['scheduler'].get_schedule.return_value=meta()
    if fault=='missing_provider_date':api['ec2'].describe_instances.return_value['ResponseMetadata']['HTTPHeaders']={}
    result=c.observe(api,record,now=END)
    assert result['cleanup_passed'] is False and result['passed_checks']<7 and len(result['checks'])==7


def test_missing_completion_retains_cleanup_but_does_not_invent_completion_time():
    record=launch();api=clients(record);api['s3'].get_object.side_effect=FakeError('NoSuchKey')
    result=c.observe(api,record,now=END)
    assert result['cleanup_passed'] is True and result['completion_object']['available'] is False
    assert result['cost']['launch_to_completion_object'] is None


def test_wrong_completion_bytes_are_not_a_bound_completion_receipt():
    record=launch();api=clients(record);api['s3'].get_object.return_value['Body']=BytesIO(b'{"job":"other"}')
    result=c.observe(api,record,now=END)
    assert result['completion_object']['available'] is False
    assert result['cost']['launch_to_completion_object'] is None


def test_plan_default_never_constructs_a_client(monkeypatch,capsys):
    factory=Mock(side_effect=AssertionError('No real clients'))
    monkeypatch.setattr(c,'make_clients',factory)
    assert c.main([])==0
    assert json.loads(capsys.readouterr().out)['aws_calls_performed'] is False
    assert not factory.called


def test_observation_without_external_receipt_pin_never_constructs_client(monkeypatch):
    factory=Mock(side_effect=AssertionError('No real clients'));monkeypatch.setattr(c,'make_clients',factory)
    with pytest.raises(ValueError,match='EXTERNAL_FINAL'):c.main(['--observe-aws'])
    assert not factory.called
