"""Read-only live re-check of the last slot user c41 (custom controller) before c42 takes the shared prefix: its
instance terminated, its volume absent, no live instance tagged with its job, the shared prefix empty (all versions and
delete markers), no multipart uploads. Usage: python -B recheck_c41_live_c42.py <out.json>"""
import datetime, json, sys
import boto3

REGION = 'us-west-2'; BUCKET = 'helm-primary-pointer-807562639912-20261001-v4'
PREFIX = 'bridge-control-20260822/helm-pointer-saturation-20261001-v4/'
JOB = 'helm-claude-scribe-l4-score-20261019-c41'; INSTANCE = 'i-085092855ef75f1b8'; VOLUME = 'vol-09ed9ed5cfe971512'
s = boto3.Session(region_name=REGION)
assert s.client('sts').get_caller_identity()['Account'] == '807562639912'
ec, s3 = s.client('ec2'), s.client('s3')
inst = [i['State']['Name'] for r in ec.describe_instances(InstanceIds=[INSTANCE])['Reservations'] for i in r['Instances']] \
    if True else []
active = ['pending', 'running', 'shutting-down', 'stopped', 'stopping']
tagged = [i['InstanceId'] for r in ec.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': [JOB]}, {'Name': 'instance-state-name', 'Values': active}])['Reservations'] for i in r['Instances']]
vols = ec.describe_volumes(Filters=[{'Name': 'volume-id', 'Values': [VOLUME]}])['Volumes']
page = s3.list_object_versions(Bucket=BUCKET, Prefix=PREFIX, ExpectedBucketOwner='807562639912')
mp = s3.list_multipart_uploads(Bucket=BUCKET, Prefix=PREFIX, ExpectedBucketOwner='807562639912').get('Uploads', [])
out = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'remote_actions': 'READ_ONLY', 'job': JOB,
       'instance': INSTANCE, 'instance_states': inst, 'live_tagged_instances': tagged, 'volume_rows': len(vols),
       'prefix_versions': len(page.get('Versions', [])), 'prefix_delete_markers': len(page.get('DeleteMarkers', [])),
       'multipart_uploads': len(mp)}
out['verdict'] = 'C41_CLEAN_SLOT_FREE' if inst in ([], ['terminated']) and not tagged and not vols and not out['prefix_versions'] \
    and not out['prefix_delete_markers'] and not mp else 'NOT_CLEAN'
with open(sys.argv[1], 'x', encoding='utf-8', newline='\n') as f:
    json.dump(out, f, indent=1)
print(json.dumps(out, indent=1))
