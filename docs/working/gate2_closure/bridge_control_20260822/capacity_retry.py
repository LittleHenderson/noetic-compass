# -*- coding: utf-8 -*-
import boto3, base64, json, pathlib, time, datetime
SP = pathlib.Path(__file__).resolve().parent
s = boto3.Session(region_name='us-west-2')
ec2, iam = s.client('ec2'), s.client('iam')
subs = ec2.describe_subnets(Filters=[{'Name':'vpc-id','Values':['vpc-0df2f8cc1b9f23838']}])['Subnets']
sg = ec2.describe_security_groups(Filters=[{'Name':'group-name','Values':['cas-aws-gpu-standby-v1']}])['SecurityGroups'][0]['GroupId']
ud = base64.b64encode((SP / 'bootstrap_userdata.sh').read_text(encoding='utf-8').encode()).decode()
DEADLINE = time.time() + 2 * 3600
attempt = 0
print('capacity-retry start', flush=True)
while time.time() < DEADLINE:
    attempt += 1
    for az in ['us-west-2a','us-west-2c','us-west-2b','us-west-2d']:
        cand = [x for x in subs if x['AvailabilityZone'] == az]
        if not cand: continue
        sub = sorted(cand, key=lambda x: x['DefaultForAz'], reverse=True)[0]
        try:
            r = ec2.run_instances(
                ImageId='ami-039f004668b2adc12', InstanceType='g6e.xlarge', MinCount=1, MaxCount=1,
                IamInstanceProfile={'Name':'cas-aws-gpu-standby-v1-us-west-2'},
                SecurityGroupIds=[sg], SubnetId=sub['SubnetId'], UserData=ud,
                DisableApiTermination=True,
                BlockDeviceMappings=[{'DeviceName':'/dev/sda1','Ebs':{'DeleteOnTermination':True,'Encrypted':True,'VolumeSize':100,'VolumeType':'gp3'}}],
                TagSpecifications=[{'ResourceType':'instance','Tags':[{'Key':'Name','Value':'cas-bridge-control-20260822'}]}],
            )
            iid = r['Instances'][0]['InstanceId']
            policy = {'Version':'2012-10-17','Statement':[
                {'Effect':'Allow','Action':['s3:GetObject','s3:PutObject'],'Resource':['arn:aws:s3:::cas-harness-runpod-92754088/bridge-control-20260822/*']},
                {'Effect':'Allow','Action':['ec2:DescribeInstances','ec2:ModifyInstanceAttribute','ec2:TerminateInstances'],'Resource':[f'arn:aws:ec2:us-west-2:807562639912:instance/{iid}']}]}
            iam.put_role_policy(RoleName='cas-aws-gpu-standby-v1-us-west-2', PolicyName='bridge-control-20260822', PolicyDocument=json.dumps(policy))
            (SP / 'launch_state.json').write_text(json.dumps({'instance_id': iid, 'launched_at': time.time(), 'subnet': sub['SubnetId'], 'az': az}, indent=2))
            print('LAUNCHED', iid, az, flush=True)
            raise SystemExit(0)
        except Exception as e:
            msg = str(e)[:70]
            print(f"[{datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%SZ')}] attempt {attempt} az {az}: {msg}", flush=True)
            time.sleep(3)
    time.sleep(600)
print('CAPACITY_TIMEOUT after 2h', flush=True)
raise SystemExit(2)
