"""Remove only this job's temporary AWS resources after receipt collection."""
import datetime
import hashlib
import json
from pathlib import Path

import boto3

HERE = Path(__file__).resolve().parent
job = json.loads((HERE / 'AWS_JOB.json').read_bytes())
summary = json.loads((HERE / 'TEST_ACCOUNTING.json').read_bytes())
if summary['compatibility_status'] != 'PASS' or summary['historical_prediction_checks'] != 6768:
    raise SystemExit('COLLECT_COMPLETE_RECEIPTS_FIRST')
if job['instance_id'] != 'i-00787ea718c2631ea' or job['bucket'] != 'cas-helm-checker-20260923-807562639912-9eeab1e7':
    raise SystemExit('UNEXPECTED_RESOURCE_IDENTITY')
ec = boto3.client('ec2', region_name=job['region'])
s3 = boto3.client('s3', region_name=job['region'])
instance = ec.describe_instances(InstanceIds=[job['instance_id']])['Reservations'][0]['Instances'][0]
if not any(t['Key'] == 'Name' and t['Value'] == 'cas-helm-stage2-checker-20260923' for t in instance['Tags']):
    raise SystemExit('INSTANCE_TAG_MISMATCH')
remote = s3.head_object(Bucket=job['bucket'], Key='job/run001-results.tar.gz')
archive = (HERE / 'run001-results.tar.gz').read_bytes()
if len(archive) != remote['ContentLength'] or hashlib.md5(archive).hexdigest() != remote['ETag'].strip('"'):
    raise SystemExit('DOWNLOADED_ARCHIVE_MISMATCH')
objects = s3.list_objects_v2(Bucket=job['bucket'])
keys = [r['Key'] for r in objects.get('Contents', [])]
allowed = {'job/input_bundle.tar.gz', 'job/run001-progress.json', 'job/run001-results.tar.gz'}
if objects.get('IsTruncated') or not set(keys) <= allowed:
    raise SystemExit('UNEXPECTED_BUCKET_CONTENTS_PRESERVE')
receipt = {'requested_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'instance_id': job['instance_id'], 'bucket': job['bucket'],
           'archive_sha256': hashlib.sha256(archive).hexdigest(),
           'archive_matches_s3_etag': True, 'deleted_keys': keys,
           'volume_ids': [v['Ebs']['VolumeId'] for v in instance.get('BlockDeviceMappings', [])],
           'launch_time': str(instance['LaunchTime'])}
receipt['termination'] = ec.terminate_instances(InstanceIds=[job['instance_id']])
if keys:
    receipt['objects_deleted'] = s3.delete_objects(Bucket=job['bucket'], Delete={'Objects': [{'Key': k} for k in keys]})
    if receipt['objects_deleted'].get('Errors'):
        raise SystemExit('S3_DELETE_ERROR')
receipt['bucket_deleted'] = s3.delete_bucket(Bucket=job['bucket'])
(HERE / 'AWS_CLEANUP.json').write_text(json.dumps(receipt, indent=2, default=str)+'\n', encoding='utf-8')
print(json.dumps({'termination_requested': job['instance_id'], 'temporary_bucket_deleted': job['bucket']}))
