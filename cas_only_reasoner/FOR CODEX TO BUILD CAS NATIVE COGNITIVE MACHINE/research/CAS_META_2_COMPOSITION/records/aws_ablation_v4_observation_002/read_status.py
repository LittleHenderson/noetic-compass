"""Read-only observation of the one existing comparison job; never restart it."""
from datetime import datetime, timezone
import json
from pathlib import Path
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

JOB = 'cas-meta2-20260906032109-361b34a0'
INSTANCE = 'i-09ed76379ad9536b1'
BUCKET = JOB + '-807562639912'
HERE = Path(__file__).resolve().parent
output = HERE / ('status_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.json')
session = boto3.Session(profile_name='default', region_name='us-west-2')
config = Config(connect_timeout=10, read_timeout=30, retries={'max_attempts': 0})
if session.client('sts', config=config).get_caller_identity()['Account'] != '807562639912':
    raise RuntimeError('AWS_ACCOUNT_MISMATCH')
ec2 = session.client('ec2', config=config)
response = ec2.describe_instances(InstanceIds=[INSTANCE])
instance = response['Reservations'][0]['Instances'][0]
if (instance['InstanceId'] != INSTANCE or instance.get('ClientToken') != JOB
        or {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}.get('cas_meta_job') != JOB):
    raise RuntimeError('JOB_INSTANCE_IDENTITY_MISMATCH')
record = {'schema': 'cas-meta2-live-ablation-observation/0.1', 'job': JOB,
    'utc': datetime.now(timezone.utc).isoformat(), 'instance_response': response,
    'state': instance['State']['Name'], 'provider_mutations': 0}
try:
    record['schedule_response'] = session.client('scheduler', config=config).get_schedule(Name=JOB)
except ClientError as error:
    record['schedule_error'] = error.response['Error']['Code']
s3 = session.client('s3', config=config)
for key, ceiling in [('results/bootstrap.log', 1048576), ('results/complete.json', 1048576)]:
    try:
        head = s3.head_object(Bucket=BUCKET, Key=key)
        if head['ContentLength'] > ceiling:
            raise RuntimeError('STATUS_OBJECT_SIZE_CEILING')
        result = s3.get_object(Bucket=BUCKET, Key=key)
        raw = result['Body'].read(ceiling + 1)
        if len(raw) > ceiling:
            raise RuntimeError('STATUS_OBJECT_SIZE_CEILING')
        record[key] = {'head': head, 'text': raw.decode('utf-8', errors='replace')}
    except ClientError as error:
        record[key] = {'error': error.response['Error']['Code']}
with output.open('x', encoding='utf-8') as stream:
    json.dump(record, stream, default=str, indent=2, sort_keys=True)
    stream.write('\n')
print(json.dumps({'state': record['state'], 'schedule': record.get('schedule_response', {}).get('ScheduleExpression'),
    'schedule_state': record.get('schedule_response', {}).get('State'),
    'progress': record['results/bootstrap.log'].get('text', '')[-8000:],
    'complete': record['results/complete.json'], 'receipt': str(output)}, default=str))
