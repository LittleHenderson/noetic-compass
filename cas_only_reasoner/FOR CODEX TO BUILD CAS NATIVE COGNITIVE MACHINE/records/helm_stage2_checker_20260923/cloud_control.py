"""Single-owner AWS transport for this bounded CPU checker job. No model calls."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import uuid

import boto3
from botocore.config import Config

HERE = Path(__file__).resolve().parent
STATE = HERE / 'AWS_JOB.json'
REGION = 'us-west-2'
CONFIG = Config(connect_timeout=5, read_timeout=30, retries={'max_attempts': 0})
SESSION = boto3.Session(region_name=REGION)


def client(name):
    return SESSION.client(name, config=CONFIG)


def save(state):
    STATE.write_text(json.dumps(state, indent=2, default=str) + '\n', encoding='utf-8')


def launch():
    if STATE.exists():
        raise SystemExit('EXISTING_JOB_NO_AUTOMATIC_RETRY')
    account = SESSION.client('sts', config=CONFIG).get_caller_identity()['Account']
    token = uuid.uuid4().hex
    bucket = 'cas-helm-checker-20260923-' + account + '-' + token[:8]
    state = {'schema': 'helm.stage2-aws-job/1', 'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'region': REGION, 'bucket': bucket, 'prefix': 'job/', 'client_token': token,
             'owner_instruction': 'use aws as there is only 354 mb of 16 gbs locally',
             'instance_type': 't3.large', 'vcpu': 2, 'memory_gib': 8, 'disk_gib': 12,
             'instance_lifetime_seconds': 7200, 'cpu_credits': 'standard', 'worker_memory_gib': 4,
             'budget_usd': 1, 'budget_enforcement': 'resource/time caps; not a billing-enforced dollar cap',
             'rate_usd_hour': '0.0832', 'training_updates': 0, 'gpu': False}
    save(state)
    s3 = client('s3')
    s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={'LocationConstraint': REGION})
    s3.put_public_access_block(Bucket=bucket, PublicAccessBlockConfiguration={
        'BlockPublicAcls': True, 'IgnorePublicAcls': True, 'BlockPublicPolicy': True, 'RestrictPublicBuckets': True})
    s3.put_bucket_encryption(Bucket=bucket, ServerSideEncryptionConfiguration={
        'Rules': [{'ApplyServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}]})
    s3.put_bucket_policy(Bucket=bucket, Policy=json.dumps({'Version': '2012-10-17', 'Statement': [{
        'Effect': 'Allow', 'Principal': {'AWS': f'arn:aws:iam::{account}:role/cas-aws-gpu-standby-v1-us-west-2'},
        'Action': ['s3:GetObject', 's3:PutObject'], 'Resource': f'arn:aws:s3:::{bucket}/job/*'}]}))
    ec = client('ec2')
    ami = client('ssm').get_parameter(Name='/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64')['Parameter']['Value']
    startup = '''#!/bin/bash
set -eu
shutdown -h +120
timeout 600 dnf install -y python3-pip tar gzip awscli
mkdir -p /opt/helm-stage2
printf 'READY\\n' > /opt/helm-stage2/startup-status
'''
    result = ec.run_instances(ImageId=ami, InstanceType='t3.large', MinCount=1, MaxCount=1,
        ClientToken=token, SubnetId='subnet-0eb3ca4bf5ca98f24', SecurityGroupIds=['sg-0562c483e0364cdab'],
        IamInstanceProfile={'Name': 'cas-aws-gpu-standby-v1-us-west-2'},
        InstanceInitiatedShutdownBehavior='terminate', CreditSpecification={'CpuCredits': 'standard'},
        MetadataOptions={'HttpTokens': 'required'}, UserData=startup,
        BlockDeviceMappings=[{'DeviceName': '/dev/xvda', 'Ebs': {
            'VolumeSize': 12, 'VolumeType': 'gp3', 'DeleteOnTermination': True, 'Encrypted': True}}],
        TagSpecifications=[{'ResourceType': 'instance', 'Tags': [
            {'Key': 'Name', 'Value': 'cas-helm-stage2-checker-20260923'},
            {'Key': 'Purpose', 'Value': 'bounded-cpu-checker-validation'},
            {'Key': 'ExpiresAfterSeconds', 'Value': '7200'}]}])
    state.update(instance_id=result['Instances'][0]['InstanceId'], ami=ami,
                 launch_response_request_id=result['ResponseMetadata']['RequestId'])
    save(state)
    print(json.dumps(state))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('action', choices=['launch', 'status', 'send', 'read', 'upload', 'download', 'terminate'])
    ap.add_argument('--file'); ap.add_argument('--name'); ap.add_argument('--command-id')
    args = ap.parse_args()
    if args.action == 'launch':
        launch(); return
    state = json.loads(STATE.read_bytes()); instance = state.get('instance_id')
    if args.action == 'status':
        ec = client('ec2').describe_instances(InstanceIds=[instance])['Reservations'][0]['Instances'][0]
        ss = client('ssm').describe_instance_information(Filters=[{'Key': 'InstanceIds', 'Values': [instance]}])
        print(json.dumps({'instance': instance, 'state': ec['State']['Name'], 'ssm': ss['InstanceInformationList']}, default=str))
    elif args.action == 'send':
        raw = Path(args.file).read_bytes()
        result = client('ssm').send_command(InstanceIds=[instance], DocumentName='AWS-RunShellScript',
            Parameters={'commands': [raw.decode('utf-8')], 'executionTimeout': ['6600']}, TimeoutSeconds=60)
        receipt = {'id': result['Command']['CommandId'], 'script': args.file, 'sha256': hashlib.sha256(raw).hexdigest()}
        state.setdefault('commands', []).append(receipt); save(state); print(json.dumps(receipt))
    elif args.action == 'read':
        result = client('ssm').get_command_invocation(CommandId=args.command_id, InstanceId=instance)
        name = args.name or args.command_id
        (HERE / (name + '.json')).write_text(json.dumps(result, indent=2, default=str) + '\n', encoding='utf-8')
        print(json.dumps({k: result.get(k) for k in ['Status', 'ResponseCode', 'StandardOutputContent', 'StandardErrorContent']}))
    elif args.action == 'upload':
        raw = Path(args.file).read_bytes(); name = args.name or Path(args.file).name
        client('s3').put_object(Bucket=state['bucket'], Key='job/' + name, Body=raw, ServerSideEncryption='AES256')
        print(json.dumps({'key': 'job/' + name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}))
    elif args.action == 'download':
        result = client('s3').get_object(Bucket=state['bucket'], Key='job/' + args.name)
        raw = result['Body'].read(); Path(args.file).write_bytes(raw)
        print(json.dumps({'downloaded': args.name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}))
    elif args.action == 'terminate':
        result = client('ec2').terminate_instances(InstanceIds=[instance]); state['termination_response'] = result
        save(state); print(json.dumps(result, default=str))


if __name__ == '__main__':
    main()
