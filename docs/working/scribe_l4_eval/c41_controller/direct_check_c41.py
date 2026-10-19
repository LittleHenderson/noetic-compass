"""Third, direct READ-ONLY look for job c41: the instance by id, any live instance carrying the project tag, any volume
carrying the job tag, the shared prefix (versions, delete markers) and multipart uploads. Usage: python -B direct_check_c41.py <attempt>"""
import datetime, json, sys
from pathlib import Path
import boto3

JOB = 'helm-claude-scribe-l4-score-20261019-c41'
BUCKET = 'helm-primary-pointer-807562639912-20261001-v4'; PREFIX = 'bridge-control-20260822/helm-pointer-saturation-20261001-v4/'
HERE = Path(__file__).resolve().parent
a = int(sys.argv[1]); TAG = 'aws-c41-a%d' % a
s = boto3.Session(profile_name='default', region_name='us-west-2')
assert s.client('sts').get_caller_identity()['Account'] == '807562639912'
ec = s.client('ec2'); s3 = s.client('s3')
iid = json.loads((HERE / (TAG + '-control.json')).read_bytes())['instance']
inst = [{'id': i['InstanceId'], 'state': i['State']['Name'], 'launch_time': i['LaunchTime'].isoformat(),
         'state_transition_reason': i.get('StateTransitionReason'), 'type': i['InstanceType']}
        for r in ec.describe_instances(InstanceIds=[iid])['Reservations'] for i in r['Instances']]
live = [i['InstanceId'] for r in ec.describe_instances(Filters=[{'Name': 'tag:Project', 'Values': ['HELM-pointer-saturation']},
        {'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped', 'shutting-down']}])['Reservations'] for i in r['Instances']]
vols = [v['VolumeId'] for v in ec.describe_volumes(Filters=[{'Name': 'tag:Name', 'Values': [JOB]}])['Volumes'] if v['State'] != 'deleted']
page = s3.list_object_versions(Bucket=BUCKET, Prefix=PREFIX, ExpectedBucketOwner='807562639912', MaxKeys=200)
mp = s3.list_multipart_uploads(Bucket=BUCKET, Prefix=PREFIX, ExpectedBucketOwner='807562639912').get('Uploads', [])
out = {'schema': 'claude.direct-read-only-observation/1', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'job': JOB, 'attempt': a, 'remote_actions': 'READ_ONLY', 'instance': inst, 'live_instances_with_project_tag': live,
       'volumes_remaining': vols, 'prefix_versions': [v['Key'] for v in page.get('Versions', [])],
       'prefix_delete_markers': [v['Key'] for v in page.get('DeleteMarkers', [])], 'multipart_uploads': [u['Key'] for u in mp]}
with open(HERE / (TAG + '-direct-observation.json'), 'x', encoding='utf-8', newline='\n') as fh:
    json.dump(out, fh, indent=2)
print(json.dumps(out, indent=2))
