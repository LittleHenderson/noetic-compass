"""Independent read-only provider cleanup observation for the completed corrected v4 comparison."""
from datetime import datetime, timezone
import json
from pathlib import Path
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

JOB = 'cas-meta2-20260906032109-361b34a0'
session = boto3.Session(profile_name='default', region_name='us-west-2')
cfg = Config(connect_timeout=10,read_timeout=20,retries={'max_attempts':0})
if session.client('sts',config=cfg).get_caller_identity()['Account'] != '807562639912':
    raise RuntimeError('AWS_ACCOUNT_MISMATCH')
ec2, iam, timer = (session.client(name,config=cfg) for name in ('ec2','iam','scheduler'))
checks = []
def absent(label, operation, expected, **kwargs):
    try:
        response = operation(**kwargs)
        checks.append({'check':label,'passed':False,'reason':'RESOURCE_STILL_EXISTS',
                       'request_id':response['ResponseMetadata']['RequestId']})
    except ClientError as error:
        checks.append({'check':label,'passed':error.response['Error']['Code']==expected,
                       'code':error.response['Error']['Code'],
                       'request_id':error.response['ResponseMetadata']['RequestId']})
r=ec2.describe_instances(InstanceIds=['i-09ed76379ad9536b1'])
i=r['Reservations'][0]['Instances'][0]
if (i.get('ClientToken') != JOB or {t['Key']:t['Value'] for t in i.get('Tags',[])}.get('cas_meta_job') != JOB):
    raise RuntimeError('AWS_INSTANCE_IDENTITY_MISMATCH')
checks.append({'check':'instance_terminated','passed':i['State']['Name']=='terminated',
    'state':i['State']['Name'],'request_id':r['ResponseMetadata']['RequestId']})
r=ec2.describe_volumes(Filters=[{'Name':'tag:cas_meta_job','Values':[JOB]}])
checks.append({'check':'job_volumes_absent','passed':not r['Volumes'],
    'volume_ids':[v['VolumeId'] for v in r['Volumes']], 'request_id':r['ResponseMetadata']['RequestId']})
absent('security_group_absent',ec2.describe_security_groups,'InvalidGroup.NotFound',GroupIds=['sg-0b5751b497b3c8e41'])
absent('worker_profile_absent',iam.get_instance_profile,'NoSuchEntity',InstanceProfileName=JOB+'-worker')
for suffix in ('worker','timer'):
    absent(suffix+'_role_absent',iam.get_role,'NoSuchEntity',RoleName=JOB+'-'+suffix)
absent('schedule_absent',timer.get_schedule,'ResourceNotFoundException',Name=JOB)
record={'schema':'cas-meta2-v4-cleanup-observation/0.1','utc':datetime.now(timezone.utc).isoformat(),
        'job':JOB,'checks':checks,'passed':all(c['passed'] for c in checks),
        'boundary':'Read-only instance, disk and auxiliary-resource check. S3 evidence bucket is retained under its separate expiry policy; not an invoice.'}
with Path(__file__).with_name('cleanup_receipt.json').open('x',encoding='utf-8') as f:
    json.dump(record,f,sort_keys=True,indent=2); f.write('\n')
print(json.dumps(record,indent=2))
