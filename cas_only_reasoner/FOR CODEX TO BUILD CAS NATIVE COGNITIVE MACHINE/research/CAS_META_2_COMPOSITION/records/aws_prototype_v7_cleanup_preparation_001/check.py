"""Plan by default. Future exact-job observations are read-only and never refund."""
import argparse
from datetime import datetime,timedelta,timezone
from decimal import Decimal,ROUND_CEILING
from email.utils import parsedate_to_datetime
from hashlib import sha256
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
JOB='cas-meta2-20260906094002-39762c47'
SOURCE='42f9164754312f12850d9b8789c062fa7fb8069f'
ARCHIVE='f9bed05bd582e0796e2c4e78ff0f5174e5e1b6a3f447e5c3eab56ad002d473f9'
ACCOUNT='807562639912'
REGION='us-west-2'
INSTANCE='i-0cba54498bb3a3745'
GROUP='sg-0afb9d8c6c74b706e'
BUCKET=JOB+'-'+ACCOUNT
OUTPUT_DIR=ROOT/'records/aws_prototype_v7_001'
LAUNCH=OUTPUT_DIR/'launch_receipt.json'
LEDGER=ROOT/'records/budget/campaign_ledger.json'
RATE=Decimal('2.52')
RESERVATION=Decimal('7.00')
ALLOWANCE=Decimal('1.00')
CHECKS=('instance_terminated','job_volumes_absent','security_group_absent','worker_profile_absent',
        'worker_role_absent','timer_role_absent','schedule_absent')


def need(value,reason):
    if not value:raise ValueError(reason)


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def decode(raw):
    need(type(raw) is bytes and 0<len(raw)<=16*1024**2,'LOCAL_JSON_BOUND')
    def pairs(items):
        result={}
        for key,value in items:
            need(key not in result,'DUPLICATE_JSON_FIELD');result[key]=value
        return result
    value=json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('NONFINITE_JSON')))
    canonical(value);return value


def timestamp(value):
    result=value if isinstance(value,datetime) else datetime.fromisoformat(value)
    need(result.tzinfo is not None and result.utcoffset() is not None,'TIMEZONE_REQUIRED')
    return result.astimezone(timezone.utc)


def regular(path):
    path=Path(path).absolute()
    need(path.is_file() and not any(p.is_symlink() or getattr(p,'is_junction',lambda:False)()
        for p in (path,*path.parents)),'LOCAL_FILE_MISSING_OR_LINK')
    return path


def file_hash(path):return sha256(regular(path).read_bytes()).hexdigest()


def validate_launch(launch,*,terminal=True):
    need(launch['job']==JOB and launch['source_sha']==SOURCE and launch['archive_sha256']==ARCHIVE
        and launch['run_instances_client_token']==JOB and launch['smoke_only'] is False,'LAUNCH_IDENTITY')
    resources=launch['resources']
    expected={'instance':INSTANCE,'security_group':GROUP,'bucket':BUCKET,'schedule':JOB,
        'instance_profile':JOB+'-worker',JOB+'-worker':'arn:aws:iam::'+ACCOUNT+':role/'+JOB+'-worker',
        JOB+'-timer':'arn:aws:iam::'+ACCOUNT+':role/'+JOB+'-timer'}
    need(resources==expected,'EXACT_LAUNCH_RESOURCES')
    plan=launch['plan']
    need(all(plan.get(k)==v for k,v in {'account_id':ACCOUNT,'region':REGION,'instance_type':'g7.2xlarge',
        'instance_count':1,'runtime_seconds_max':7800,'compute_seconds_max':7200,
        'per_launch_reserved_cap_usd':'7.00','owner_task_cap_usd':'400.00',
        'on_demand_hourly_usd_max':'2.52','ancillary_reserved_usd':'1.00','automatic_retries':0}.items()),
        'RECORDED_PLAN_CHANGED')
    reserve=launch['task_budget_reservation']['reservation']
    need(reserve['job']==JOB and reserve['source_sha']==SOURCE and reserve['archive_sha256']==ARCHIVE
        and reserve['reserved_usd']=='7.00' and reserve['status']=='RESERVED_NO_AUTOMATIC_REFUND'
        and reserve['plan']==plan,'RESERVATION_BINDING')
    rates=[]
    for encoded in launch['official_price_response']:
        product=decode(encoded.encode())
        attributes=product['product']['attributes']
        need(all(attributes.get(k)==v for k,v in {'instanceType':'g7.2xlarge','regionCode':REGION,
            'operatingSystem':'Linux','tenancy':'Shared','marketoption':'OnDemand'}.items()),'RECORDED_PRICE_PRODUCT')
        rates += [Decimal(p['pricePerUnit']['USD']) for term in product['terms']['OnDemand'].values()
                  for p in term['priceDimensions'].values() if p['unit']=='Hrs']
    need(rates==[RATE],'RECORDED_PRICE_RATE')
    if terminal:
        need(launch['status'] in ('AWS_JOB_FINISHED','AWS_JOB_FAILED','AWS_JOB_BLOCKED_OR_FAILED'),
            'WAIT_FOR_FINAL_LAUNCH_RECEIPT')
    return timestamp(launch['provider_launch_time'])


def metadata(response):
    meta=response['ResponseMetadata'];headers=meta['HTTPHeaders']
    date=next(value for key,value in headers.items() if key.lower()=='date')
    need(type(meta['RequestId']) is str and meta['RequestId'] and type(date) is str and date,
        'PROVIDER_RESPONSE_ID_AND_DATE_REQUIRED')
    parsed=parsedate_to_datetime(date)
    return {'request_id':meta['RequestId'],'provider_http_date':date,
        'provider_response_utc':timestamp(parsed).isoformat()}


def error_record(error):
    response=getattr(error,'response',{})
    result={'error_type':type(error).__name__,'code':response.get('Error',{}).get('Code','UNAVAILABLE')}
    try:result.update(metadata(response))
    except (KeyError,ValueError,StopIteration,TypeError):result['provider_timestamp_unavailable']=True
    return result


def observed_cost(launch_time,instance_check,completion):
    # HTTP Date has one-second precision. Adding one second gives an upper
    # observation endpoint; it is not the actual time termination completed.
    if instance_check.get('passed') is not True:
        return {'available':False,'reason':'TERMINATION_NOT_CONFIRMED','is_invoice':False}
    end=timestamp(instance_check['provider_response_utc'])+timedelta(seconds=1)
    need(end>=launch_time,'PROVIDER_CLOCK_ORDER')
    def estimate(endpoint):
        seconds=Decimal(str((endpoint-launch_time).total_seconds()))
        need(seconds>=0,'NEGATIVE_ELAPSED_TIME')
        rounded=max(Decimal(60),seconds.to_integral_value(rounding=ROUND_CEILING))
        return {'elapsed_seconds':str(seconds),'rounded_compute_seconds':str(rounded),
            'compute_only_usd_estimate':str(rounded*RATE/Decimal(3600))}
    observation=estimate(end)
    complete=None
    if completion.get('available'):
        completion_time=timestamp(completion['provider_last_modified_utc'])
        need(launch_time<=completion_time<=end,'COMPLETION_PROVIDER_CLOCK_ORDER')
        complete=estimate(completion_time)
    with_allowance=Decimal(observation['compute_only_usd_estimate'])+ALLOWANCE
    return {'available':True,'provider_launch_utc':launch_time.isoformat(),
        'termination_observation_upper_utc':end.isoformat(),'actual_termination_timestamp_known':False,
        'launch_to_termination_observation':observation,'launch_to_completion_object':complete,
        'hourly_rate_usd':str(RATE),'rate_source':'externally pinned final launch receipt official_price_response',
        'planned_maximum_with_fixed_allowance_usd':'6.46','observed_compute_plus_fixed_allowance_usd':str(with_allowance),
        'fixed_ancillary_planning_allowance_usd':'1.00','reservation_usd':'7.00',
        'reservation_covers_observed_compute_plus_allowance':with_allowance<=RESERVATION,
        'excluded':'EBS, public IPv4, S3 requests/retention, transfer, taxes and other fees are not measured here. '
            'The $1 is only the previously reserved planning allowance, not verified non-compute charges.',
        'is_invoice':False,'actual_total_cost_established':False,'automatic_refund':False}


def observe(clients,launch,*,now=None):
    start=validate_launch(launch);now=now or datetime.now(timezone.utc)
    identity=clients['sts'].get_caller_identity()
    need(identity['Account']==ACCOUNT,'AWS_ACCOUNT_MISMATCH')
    account_evidence=metadata(identity);checks=[]
    def check(label,call,evaluate,**kwargs):
        try:
            response=call(**kwargs);details=evaluate(response)
            checks.append({'check':label,**metadata(response),**details})
        except Exception as error:
            checks.append({'check':label,'passed':False,**error_record(error)})
    def instance(response):
        need(not response.get('NextToken') and len(response['Reservations'])==1,'INSTANCE_RESERVATION_COUNT')
        reservation=response['Reservations'][0]
        need(reservation['OwnerId']==ACCOUNT and len(reservation['Instances'])==1,'INSTANCE_OWNER_OR_COUNT')
        item=reservation['Instances'][0]
        need(item['InstanceId']==INSTANCE and item['ClientToken']==JOB
            and {x['Key']:x['Value'] for x in item['Tags']}.get('cas_meta_job')==JOB
            and item['InstanceType']=='g7.2xlarge' and timestamp(item['LaunchTime'])==start,'INSTANCE_IDENTITY')
        return {'passed':item['State']['Name']=='terminated','state':item['State']['Name'],
            'instance_id':INSTANCE,'provider_launch_utc':timestamp(item['LaunchTime']).isoformat(),
            'state_transition_reason':item.get('StateTransitionReason'),
            'state_transition_reason_is_not_used_as_termination_time':True}
    check('instance_terminated',clients['ec2'].describe_instances,instance,InstanceIds=[INSTANCE])
    check('job_volumes_absent',clients['ec2'].describe_volumes,
        lambda r:{'passed':not r['Volumes'] and not r.get('NextToken'),
            'volume_ids':[v['VolumeId'] for v in r['Volumes']],'pagination_token_present':bool(r.get('NextToken'))},
        Filters=[{'Name':'tag:cas_meta_job','Values':[JOB]}])
    def absent(label,operation,code,**kwargs):
        try:
            response=operation(**kwargs)
            checks.append({'check':label,'passed':False,'reason':'RESOURCE_STILL_EXISTS',**metadata(response)})
        except Exception as error:
            detail=error_record(error)
            checks.append({'check':label,'passed':detail['code']==code and 'provider_response_utc' in detail,**detail})
    absent('security_group_absent',clients['ec2'].describe_security_groups,'InvalidGroup.NotFound',GroupIds=[GROUP])
    absent('worker_profile_absent',clients['iam'].get_instance_profile,'NoSuchEntity',InstanceProfileName=JOB+'-worker')
    for suffix in ('worker','timer'):
        absent(suffix+'_role_absent',clients['iam'].get_role,'NoSuchEntity',RoleName=JOB+'-'+suffix)
    absent('schedule_absent',clients['scheduler'].get_schedule,'ResourceNotFoundException',Name=JOB,GroupName='default')
    completion={'available':False}
    try:
        response=clients['s3'].get_object(Bucket=BUCKET,Key='results/complete.json',ExpectedBucketOwner=ACCOUNT)
        body=response['Body']
        try:payload=body.read(131073)
        finally:body.close()
        need(len(payload)<=131072 and decode(payload)==launch.get('result')
            and decode(payload).get('job')==JOB,'COMPLETION_OBJECT_BINDING')
        completion={'available':True,'bucket':BUCKET,'key':'results/complete.json',**metadata(response),
            'provider_last_modified_utc':timestamp(response['LastModified']).isoformat(),
            'bytes':len(payload),'sha256':sha256(payload).hexdigest(),'matches_final_launch_result':True,
            'timestamp_meaning':'S3 completion object last modification, not GPU computation end'}
    except Exception as error:completion.update(error_record(error))
    need(tuple(row['check'] for row in checks)==CHECKS,'SEVEN_CLEANUP_CHECKS_REQUIRED')
    cost=observed_cost(start,checks[0],completion)
    return {'schema':'cas-meta2-v7-cleanup-and-cost-observation/1','job':JOB,'source_sha':SOURCE,
        'utc':timestamp(now).isoformat(),'account_id':ACCOUNT,'region':REGION,'account_evidence':account_evidence,
        'resources':launch['resources'],
        'checks':checks,'cleanup_passed':all(row['passed'] for row in checks),'passed_checks':sum(row['passed'] for row in checks),
        'completion_object':completion,'cost':cost,'provider_calls_are_read_only':True,
        'resource_mutation_performed':False,'reservation_changed':False,'automatic_refund':False,
        'boundary':'Seven exact cleanup identities observed. The retained S3 bucket is intentionally not deleted. '
            'No training, launch, termination, retry or refund is performed; cost figures are estimates, not invoices.'}


def make_clients(profile):
    # This is the only provider-import path, reached only by explicit future CLI.
    import boto3
    from botocore.config import Config
    session=boto3.Session(profile_name=profile,region_name=REGION)
    config=Config(connect_timeout=5,read_timeout=15,retries={'max_attempts':0})
    return {name:session.client(name,config=config) for name in ('sts','ec2','iam','scheduler','s3')}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False)
    parser.add_argument('--observe-aws',action='store_true')
    parser.add_argument('--launch-receipt-sha256')
    parser.add_argument('--profile',default='default')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args(argv)
    if not args.observe_aws:
        print(json.dumps({'mode':'PREPARATION_ONLY','job':JOB,'source_sha':SOURCE,'checks':CHECKS,
            'aws_calls_performed':False,'launch_receipt':str(LAUNCH),'reservation_usd':'7.00'}));return 0
    need(type(args.launch_receipt_sha256) is str and re.fullmatch('[a-f0-9]{64}',args.launch_receipt_sha256),
        'EXTERNAL_FINAL_LAUNCH_RECEIPT_HASH_REQUIRED')
    need(args.output is not None,'NEW_OUTPUT_REQUIRED')
    output=args.output.absolute()
    need(output.parent.resolve()==OUTPUT_DIR.resolve() and output.suffix=='.json'
        and not output.exists() and not any(p.is_symlink() or getattr(p,'is_junction',lambda:False)()
            for p in (output,*output.parents)),'NEW_JOB_OUTPUT_ONLY')
    need(file_hash(LAUNCH)==args.launch_receipt_sha256,'FINAL_LAUNCH_RECEIPT_CHANGED')
    launch=decode(regular(LAUNCH).read_bytes());validate_launch(launch)
    ledger_before=file_hash(LEDGER)
    result=observe(make_clients(args.profile),launch)
    need(file_hash(LAUNCH)==args.launch_receipt_sha256 and file_hash(LEDGER)==ledger_before,'LOCAL_INPUT_CHANGED_DURING_CHECK')
    result.update(launch_receipt_sha256=args.launch_receipt_sha256,ledger_sha256=ledger_before,ledger_unchanged=True,
        checker_sha256=file_hash(Path(__file__)))
    with output.open('xb') as stream:stream.write(canonical(result)+b'\n')
    print(json.dumps({'cleanup_passed':result['cleanup_passed'],'passed_checks':result['passed_checks'],
        'receipt':str(output),'sha256':file_hash(output),'reservation_changed':False}))
    return 0 if result['cleanup_passed'] else 1


if __name__=='__main__':raise SystemExit(main())
