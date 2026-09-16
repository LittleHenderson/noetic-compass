"""Apply non-expiring cleanup to two named evidence buckets, then verify.

Completed evidence is retained indefinitely. Only abandoned multipart uploads
are eligible for automatic abort after seven days. Never deletes objects or
touches the stopped instance/volume. Requires explicit --apply.
"""
import argparse
import datetime
import json
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

ACCOUNT = '807562639912'
BUCKETS = tuple('cas-meta2-rdcjt-' + suffix + '-' + ACCOUNT for suffix in
                ('20260913183000-d27a44e4', '20260913184000-d27a44e4'))
RULE = {'ID': 'retain-evidence-abort-incomplete-after-7-days', 'Status': 'Enabled',
        'Filter': {'Prefix': ''}, 'AbortIncompleteMultipartUpload': {'DaysAfterInitiation': 7}}


def apply(output):
    config = Config(connect_timeout=5, read_timeout=15, retries={'total_max_attempts': 1})
    session = boto3.Session(profile_name='default', region_name='us-west-2')
    assert session.client('sts', config=config).get_caller_identity()['Account'] == ACCOUNT
    s3 = session.client('s3', config=config)
    report = {'schema': 'cas-rdcjt-retention/1', 'observed_utc': datetime.datetime.now(
        datetime.timezone.utc).isoformat(), 'owner_instruction_raw':
        'I give you approval for it all ....GO!', 'evidence_kind': 'owner_instruction_in_session',
        'completed_object_expiration': 'NONE', 'buckets': [], 'stopped_resource_review': None}
    output = Path(output)
    if output.exists():
        raise ValueError('NEW_OUTPUT_REQUIRED')
    output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')

    def inventory(bucket):
        rows = []
        for page in s3.get_paginator('list_objects_v2').paginate(Bucket=bucket):
            rows.extend({'key': x['Key'], 'bytes': x['Size'], 'etag': x['ETag']}
                        for x in page.get('Contents', []))
        return sorted(rows, key=lambda x: x['key'])

    for bucket in BUCKETS:
        try:
            before_rules = s3.get_bucket_lifecycle_configuration(Bucket=bucket).get('Rules', [])
        except ClientError as error:
            if error.response['Error']['Code'] != 'NoSuchLifecycleConfiguration':
                raise
            before_rules = []
        # Do not silently replace a conflicting existing rule.
        prior = [r for r in before_rules if r.get('ID') == RULE['ID']]
        if prior and prior != [RULE]:
            raise ValueError('EXISTING_RULE_CONFLICT')
        before = inventory(bucket)
        row = {'bucket': bucket, 'before_rules': before_rules, 'before_objects': before,
               'status': 'PREPARED'}
        report['buckets'].append(row)
        save()
        desired = before_rules if prior else before_rules + [RULE]
        s3.put_bucket_lifecycle_configuration(Bucket=bucket, LifecycleConfiguration={'Rules': desired})
        after_rules = s3.get_bucket_lifecycle_configuration(Bucket=bucket)['Rules']
        after = inventory(bucket)
        row.update(after_rules=after_rules, after_objects=after,
                   objects_unchanged=before == after, status='VERIFIED' if RULE in after_rules and before == after else 'FAILED')
        save()
        if row['status'] != 'VERIFIED':
            raise ValueError('RETENTION_VERIFICATION_FAILED')
    ec2 = session.client('ec2', config=config)
    instance = ec2.describe_instances(InstanceIds=['i-0c3028734c8885542'])['Reservations'][0]['Instances'][0]
    volume = ec2.describe_volumes(VolumeIds=['vol-01cc880a770c10854'])['Volumes'][0]
    report['stopped_resource_review'] = {
        'instance_id': instance['InstanceId'], 'state': instance['State']['Name'],
        'instance_type': instance['InstanceType'], 'instance_tags': instance.get('Tags', []),
        'volume_id': volume['VolumeId'], 'volume_state': volume['State'], 'size_gib': volume['Size'],
        'volume_tags': volume.get('Tags', []),
        'decision': 'RETAINED: disk contents and recoverability are not established; completed evidence must not be deleted.',
        'billing': 'Storage remains allocated; actual invoice not queried.'}
    save()
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if not args.apply:
        print(json.dumps({'status': 'PLAN_ONLY', 'buckets': BUCKETS, 'rule': RULE}))
    else:
        result = apply(args.output)
        print(json.dumps({'buckets': [{'bucket': x['bucket'], 'status': x['status'],
            'objects_unchanged': x['objects_unchanged']} for x in result['buckets']],
            'stopped_resource_decision': result['stopped_resource_review']['decision']}))
