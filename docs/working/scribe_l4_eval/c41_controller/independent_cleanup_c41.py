"""Independent, READ-ONLY cleanup check for job helm-claude-scribe-l4-score-20261019-c41 (one attempt).

Separate process and code path from aws_control_c41.py. Inventories the instance from the controller receipts AND by
tag/client-token discovery, the volumes from the receipts AND by tag, and the whole shared prefix (all versions,
delete markers, multipart uploads). Writes VERIFIED only if everything is gone. No AWS write call exists here.
Usage: python -B independent_cleanup_c41.py <attempt>"""
import datetime, hashlib, json, sys
from pathlib import Path
import boto3

OWNER = '807562639912'; REGION = 'us-west-2'; BUCKET = 'helm-primary-pointer-807562639912-20261001-v4'
PREFIX = 'bridge-control-20260822/helm-pointer-saturation-20261001-v4/'
JOB = 'helm-claude-scribe-l4-score-20261019-c41'
HERE = Path(__file__).resolve().parent
a = int(sys.argv[1]); TAG = 'aws-c41-a%d' % a; TOKEN = JOB + '-a%d' % a
s = boto3.Session(profile_name='default', region_name=REGION)
assert s.client('sts').get_caller_identity()['Account'] == OWNER
ec = s.client('ec2'); s3 = s.client('s3')
receipts = {n: HERE / (TAG + n) for n in ('-launch-intent.json', '-control.json', '-cleanup.json', '-status.json')}
rsha = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in receipts.values() if p.exists()}
control = json.loads(receipts['-control.json'].read_bytes())
iid = control['instance']
vols = set(control.get('volumes', []))
if receipts['-cleanup.json'].exists():
    vols |= set(json.loads(receipts['-cleanup.json'].read_bytes()).get('volumes', []))
by_id = [i for r in ec.describe_instances(InstanceIds=[iid])['Reservations'] for i in r['Instances']]
found = {}
for f in ({'Name': 'tag:Name', 'Values': [JOB]}, {'Name': 'client-token', 'Values': [TOKEN]}):
    for r in ec.describe_instances(Filters=[f])['Reservations']:
        for i in r['Instances']:
            found[i['InstanceId']] = i['State']['Name']
tag_vols = {v['VolumeId']: v['State'] for v in ec.describe_volumes(Filters=[{'Name': 'tag:Name', 'Values': [JOB]}])['Volumes']}
vol_obs = {}
for v in sorted(vols):
    try:
        st3 = ec.describe_volumes(VolumeIds=[v])['Volumes'][0]['State']
        vol_obs[v] = 'ABSENT' if st3 == 'deleted' else st3
    except ec.exceptions.ClientError as e:
        vol_obs[v] = 'ABSENT' if e.response['Error']['Code'] == 'InvalidVolume.NotFound' else 'ERROR:' + e.response['Error']['Code']
page = s3.list_object_versions(Bucket=BUCKET, Prefix=PREFIX, ExpectedBucketOwner=OWNER, MaxKeys=200)
mp = s3.list_multipart_uploads(Bucket=BUCKET, Prefix=PREFIX, ExpectedBucketOwner=OWNER).get('Uploads', [])
out = {'schema': 'claude.c41.independent-cleanup/1', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'job': JOB, 'attempt': a, 'account': OWNER, 'region': REGION, 'remote_actions': 'READ_ONLY',
       'instance': iid, 'instance_state': by_id[0]['State']['Name'] if by_id else 'ABSENT',
       'instance_state_reason': by_id[0].get('StateTransitionReason') if by_id else None,
       'instances_found_by_tag_or_token': found, 'all_job_volumes': sorted(vols), 'volume_observations': vol_obs,
       'tag_discovered_volumes': tag_vols, 'bucket': BUCKET, 'prefix': PREFIX,
       'prefix_versions_remaining': [v['Key'] for v in page.get('Versions', [])],
       'prefix_delete_markers_remaining': [v['Key'] for v in page.get('DeleteMarkers', [])],
       'multipart_uploads_remaining': len(mp), 'receipt_sha256': rsha}
out['compute_cleanup_verified'] = (out['instance_state'] in ('terminated', 'ABSENT') and all(v == 'terminated' for v in found.values())
                                   and bool(vols) and all(v == 'ABSENT' for v in vol_obs.values())
                                   and all(st == 'deleted' for st in tag_vols.values()))
out['prefix_cleanup_verified'] = not out['prefix_versions_remaining'] and not out['prefix_delete_markers_remaining'] and not mp
out['cleanup_verified'] = out['compute_cleanup_verified'] and out['prefix_cleanup_verified']
out['status'] = 'VERIFIED' if out['cleanup_verified'] else 'NOT_VERIFIED'
p = HERE / (TAG + '-independent-cleanup.json')
with open(p, 'x', encoding='utf-8', newline='\n') as fh:
    json.dump(out, fh, indent=2, default=str)
print(json.dumps(out, indent=2, default=str))
