"""Read-only provider receipts for the single CAS-META-1 recovery job 002."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ACCOUNT = '807562639912'
REGION = 'us-west-2'
JOB = 'cas-meta1-20260905115219-33ee1c8f'
INSTANCE = 'i-04ac8e28d607c2e53'
VOLUMES = ['vol-0c4fe87a14872b103']  # Observed on the owned running instance, 2026-09-05 12:01:09 UTC.
SECURITY_GROUP = 'sg-09495a2dbccdfc648'
BUCKET = JOB+'-'+ACCOUNT


def require(condition, message):
    if not condition:
        raise ValueError(message)


def hashed(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def owned(path):
    path = Path(path).resolve()
    require(path.is_relative_to(ROOT/'records') and path != ROOT/'records', 'OWNED_RECORDS_SUBDIRECTORY_REQUIRED')
    return path


def check_instance(response):
    instances = [item for reservation in response['Reservations'] for item in reservation['Instances']]
    require(len(instances) == 1, 'EXACTLY_ONE_OWNED_INSTANCE_REQUIRED')
    instance = instances[0]
    require(instance['InstanceId'] == INSTANCE and instance.get('ClientToken') == JOB
            and {item['Key']:item['Value'] for item in instance.get('Tags', [])}.get('cas_meta_job') == JOB,
            'INSTANCE_TAG_OR_CLIENT_TOKEN_MISMATCH')
    return instance


def collect(run_dir, output, snapshot=None, profile='default'):
    run_dir, output = owned(run_dir), owned(output)
    require(run_dir == (ROOT/'records'/'aws_run_002').resolve(), 'ONLY_JOB_002_RUN_DIRECTORY_ALLOWED')
    require(not output.exists() and not output.is_relative_to(run_dir), 'NEW_SEPARATE_OUTPUT_REQUIRED')
    launch_path = run_dir/'launch_receipt.json'
    launch = read(launch_path)
    require(launch.get('job') == JOB and launch.get('resources', {}).get('instance') == INSTANCE
            and launch['resources'].get('security_group') == SECURITY_GROUP
            and launch['resources'].get('bucket') == BUCKET
            and launch['resources'].get('instance_profile') == JOB+'-worker', 'LAUNCH_RESOURCE_IDENTITY_MISMATCH')
    prior = None
    if snapshot is not None:
        snapshot = owned(snapshot)
        require(not output.is_relative_to(snapshot), 'OUTPUT_MUST_NOT_OVERLAP_EARLY_SNAPSHOT')
        prior_path = snapshot/'provider_state_receipt.json'
        prior = read(prior_path)
        require(prior.get('job') == JOB and prior.get('instance_id') == INSTANCE
                and prior.get('account') == ACCOUNT and prior.get('volume_ids') == VOLUMES, 'EARLY_SNAPSHOT_IDENTITY_MISMATCH')
        for name, digest in prior['raw_response_sha256'].items():
            path = (snapshot/name).resolve()
            require(path.is_relative_to(snapshot) and hashed(path) == digest, 'EARLY_RAW_RESPONSE_CHANGED')
        early = check_instance(read(snapshot/'raw'/'instance.json')['response'])
        require(sorted(item['Ebs']['VolumeId'] for item in early.get('BlockDeviceMappings', []) if 'Ebs' in item) == VOLUMES,
                'EARLY_ATTACHED_VOLUME_BINDING_MISSING')
    output.mkdir(parents=True, exist_ok=False)
    (output/'raw').mkdir()
    receipt = {'schema':'cas-meta1-provider-cleanup/1','status':'PROVIDER_STATE_INCOMPLETE',
        'utc_started':datetime.now(timezone.utc).isoformat(),'job':JOB,'account':ACCOUNT,'region':REGION,
        'instance_id':INSTANCE,'volume_ids':VOLUMES,'security_group':SECURITY_GROUP,
        'command_argv':[sys.executable,*sys.argv],'helper_sha256':hashed(__file__),
        'launch_receipt_sha256':hashed(launch_path),'early_snapshot_receipt_sha256':hashed(prior_path) if prior is not None else None,
        'aws_mutations_performed':False,'raw_response_sha256':{},'checks':{},'requests':[]}
    try:
        import boto3
        from botocore.config import Config
        from botocore.exceptions import ClientError
        config = Config(connect_timeout=5, read_timeout=10, retries={'max_attempts':0})
        session = boto3.Session(profile_name=profile, region_name=REGION)
        def request(label, client, method, *, absent=(), **arguments):
            try:
                response = getattr(client, method)(**arguments)
                result = {'absent':False,'response':response}
            except ClientError as exc:
                response = exc.response
                result = {'absent':response.get('Error', {}).get('Code') in absent,'response':response}
                if not result['absent']:
                    result['unexpected_error'] = True
            target = output/'raw'/(label+'.json')
            with target.open('x', encoding='utf-8') as stream:
                json.dump(result, stream, indent=2, sort_keys=True, default=str)
            receipt['raw_response_sha256']['raw/'+target.name] = hashed(target)
            receipt['requests'].append({'label':label,'method':method,'arguments':arguments,
                'request_id':response.get('ResponseMetadata', {}).get('RequestId'),'absent':result['absent']})
            require(not result.get('unexpected_error'), 'PROVIDER_READ_FAILED:'+label+':'+str(response.get('Error')))
            return result
        identity = request('identity', session.client('sts', config=config), 'get_caller_identity')['response']
        require(identity['Account'] == ACCOUNT, 'AWS_ACCOUNT_MISMATCH')
        ec2, iam = session.client('ec2', config=config), session.client('iam', config=config)
        instance = check_instance(request('instance', ec2, 'describe_instances', InstanceIds=[INSTANCE])['response'])
        receipt['instance_state'] = instance['State']['Name']
        attached = sorted(item['Ebs']['VolumeId'] for item in instance.get('BlockDeviceMappings', []) if 'Ebs' in item)
        if prior is None:
            require(attached == VOLUMES, 'EARLY_ATTACHED_VOLUME_BINDING_MISSING')
        receipt['observed_attached_volume_ids'] = attached
        checks = receipt['checks']
        checks['instance_terminated'] = instance['State']['Name'] == 'terminated'
        volumes = request('volumes', ec2, 'describe_volumes', VolumeIds=VOLUMES, absent=('InvalidVolume.NotFound',))
        checks['volumes_absent'] = volumes['absent']
        if not volumes['absent']:
            require(all({tag['Key']:tag['Value'] for tag in volume.get('Tags', [])}.get('cas_meta_job') == JOB
                        for volume in volumes['response']['Volumes']), 'VOLUME_JOB_TAG_MISMATCH')
        checks['security_group_absent'] = request('security_group', ec2, 'describe_security_groups',
            GroupIds=[SECURITY_GROUP], absent=('InvalidGroup.NotFound',))['absent']
        checks['instance_profile_absent'] = request('instance_profile', iam, 'get_instance_profile',
            InstanceProfileName=JOB+'-worker', absent=('NoSuchEntity',))['absent']
        for suffix in ('worker','timer'):
            checks[suffix+'_role_absent'] = request(suffix+'_role', iam, 'get_role',
                RoleName=JOB+'-'+suffix, absent=('NoSuchEntity',))['absent']
        checks['schedule_absent'] = request('schedule', session.client('scheduler', config=config), 'get_schedule',
            Name=JOB, absent=('ResourceNotFoundException',))['absent']
        s3 = session.client('s3', config=config)
        lifecycle = request('s3_lifecycle', s3, 'get_bucket_lifecycle_configuration', Bucket=BUCKET)['response']
        rules = lifecycle.get('Rules', [])
        checks['s3_seven_day_retention'] = len(rules) == 1 and any(rule.get('Status') == 'Enabled' and rule.get('Expiration') == {'Days':7}
            and (rule.get('Filter') == {'Prefix':''} or rule.get('Prefix') == '') for rule in rules)
        objects = request('s3_results', s3, 'list_objects_v2', Bucket=BUCKET, Prefix='results/', MaxKeys=10)['response']
        receipt['retained_result_objects'] = [{'key':item['Key'],'bytes':item['Size'],'last_modified':item['LastModified']}
                                              for item in objects.get('Contents', [])]
        receipt['results_listing_truncated'] = objects.get('IsTruncated', False)
        receipt['status'] = ('PROVIDER_CLEANUP_VERIFIED' if all(checks.values()) and prior is not None
                             else 'PROVIDER_STATE_CAPTURED_CLEANUP_PENDING')
    except BaseException as exc:
        receipt['error'] = {'type':type(exc).__name__,'message':str(exc)}
        raise
    finally:
        receipt['utc_finished'] = datetime.now(timezone.utc).isoformat()
        with (output/'provider_state_receipt.json').open('x', encoding='utf-8') as stream:
            json.dump(receipt, stream, indent=2, sort_keys=True, default=str)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--snapshot', type=Path)
    parser.add_argument('--profile', default='default')
    args = parser.parse_args(argv)
    try:
        receipt = collect(args.run_dir, args.output, args.snapshot, args.profile)
        print(json.dumps({'status':receipt['status'],'instance_state':receipt['instance_state'],
                          'volume_ids':receipt['volume_ids'],'checks':receipt['checks'],'output':str(args.output)}))
        return 0 if receipt['status'] == 'PROVIDER_CLEANUP_VERIFIED' or args.snapshot is None else 1
    except Exception as exc:
        print(json.dumps({'status':'PROVIDER_STATE_INCOMPLETE','type':type(exc).__name__,'message':str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
