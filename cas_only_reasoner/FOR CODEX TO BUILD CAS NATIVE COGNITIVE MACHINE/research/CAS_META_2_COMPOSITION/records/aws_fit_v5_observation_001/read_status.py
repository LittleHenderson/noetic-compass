"""Read-only observation of the single fit job. Never launch or restart."""
from datetime import datetime, timezone
import json
from pathlib import Path
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

JOB = 'cas-meta2-20260906054131-feae01a9'
INSTANCE = 'i-074882aa701bc4cd0'
BUCKET = JOB + '-807562639912'
HERE = Path(__file__).resolve().parent
output = HERE / ('status_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.json')
session = boto3.Session(profile_name='default', region_name='us-west-2')
config = Config(connect_timeout=10, read_timeout=30, retries={'max_attempts':0})
if session.client('sts', config=config).get_caller_identity()['Account'] != '807562639912':
    raise RuntimeError('AWS_ACCOUNT_MISMATCH')
response = session.client('ec2', config=config).describe_instances(InstanceIds=[INSTANCE])
instance = response['Reservations'][0]['Instances'][0]
if (instance['InstanceId'] != INSTANCE or instance.get('ClientToken') != JOB
        or {t['Key']:t['Value'] for t in instance.get('Tags', [])}.get('cas_meta_job') != JOB):
    raise RuntimeError('JOB_INSTANCE_IDENTITY_MISMATCH')
record = {'schema':'cas-meta2-live-fit-observation/0.1', 'job':JOB,
          'utc':datetime.now(timezone.utc).isoformat(), 'instance_response':response,
          'state':instance['State']['Name'], 'provider_mutations':0}
try:
    record['schedule_response'] = session.client('scheduler', config=config).get_schedule(Name=JOB)
except ClientError as error:
    record['schedule_error'] = error.response['Error']['Code']
s3 = session.client('s3', config=config)
tags = s3.get_bucket_tagging(Bucket=BUCKET)['TagSet']
if {t['Key']:t['Value'] for t in tags}.get('cas_meta_job') != JOB:
    raise RuntimeError('BUCKET_JOB_MISMATCH')
for key in ('results/bootstrap.log', 'results/complete.json'):
    try:
        head = s3.head_object(Bucket=BUCKET, Key=key)
        if head['ContentLength'] > 1048576:
            raise RuntimeError('STATUS_OBJECT_SIZE_CEILING')
        raw = s3.get_object(Bucket=BUCKET, Key=key)['Body'].read(1048577)
        if len(raw) > 1048576:
            raise RuntimeError('STATUS_OBJECT_SIZE_CEILING')
        record[key] = {'head':head, 'text':raw.decode('utf-8', errors='replace')}
    except ClientError as error:
        record[key] = {'error':error.response['Error']['Code']}
with output.open('x', encoding='utf-8') as stream:
    json.dump(record, stream, default=str, indent=2, sort_keys=True)
    stream.write('\n')
print(json.dumps({'state':record['state'],
    'schedule':record.get('schedule_response', {}).get('ScheduleExpression'),
    'schedule_state':record.get('schedule_response', {}).get('State'),
    'progress':record['results/bootstrap.log'].get('text', '')[-6000:],
    'complete':record['results/complete.json'], 'receipt':str(output)}, default=str))
