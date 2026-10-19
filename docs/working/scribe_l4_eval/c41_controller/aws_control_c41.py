"""AWS control/transport for job helm-claude-scribe-l4-score-20261019-c41 (SCORE_SCRIBE_L4_SEALED_98).

Modelled on the c40 controller (aws_control.py): same account, region, subnet, security group, standing instance
profile, standing never-versioned bucket and four-key prefix; durable launch intent before the only run_instances;
client-token discovery; one SSM dispatch; download + sha check; terminate; prefix purge with verify. Differences:
one t3.medium (plan section 4), Amazon Linux 2023 (resolved from the public SSM parameter and pinned in the
preflight), CPU-only torch installed on the host, 30-minute life (force cutoff 28 min, OS shutdown +30 min).
No local project execution; no scoring here.

Usage: python -B aws_control_c41.py <preflight|launch|watch|cleanup|status|console> <attempt 1|2>
"""
import datetime, hashlib, json, os, sys, time
from pathlib import Path
import boto3
from botocore.config import Config

OWNER = '807562639912'; REGION = 'us-west-2'; BUCKET = 'helm-primary-pointer-807562639912-20261001-v4'
PREFIX = 'bridge-control-20260822/helm-pointer-saturation-20261001-v4/'
KEYS = {PREFIX + n for n in ('input.zip', 'progress.json', 'transport-result.json', 'pointer-saturation-deliverable.zip')}
JOB = 'helm-claude-scribe-l4-score-20261019-c41'
PROJECT = 'HELM-pointer-saturation'
TYPE = 't3.medium'
SUBNET = 'subnet-02deacfa16bdaa4f4'; SG = 'sg-0562c483e0364cdab'; PROFILE = 'cas-aws-gpu-standby-v1-us-west-2'
AMI_PARAM = '/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64'
CAP_USD = 0.10
FORCE_MIN = 28; OS_SHUTDOWN_MIN = 30
HERE = Path(__file__).resolve().parent
OP = HERE.parent
PAYLOAD = Path(r'C:\Users\wakil\Documents\Codex\2026-10-19\scribe_l4_score\payload_c41\c41-payload.zip')
PAYLOAD_SHA = '5a4f6981028745dac31bfb3c0c45d022eccc7e2a77ba22dcda419ef345957d03'
PREV_CLEANUP = OP / 'controller_claude_r1w5_c40' / 'aws-claude-r1w5-c40-independent-cleanup.json'
PREV_CLEANUP_SHA = '3d131b6d4697319670eaae66f9b75bf210a56d251396aa050ee9b54af35da9da'
STORAGE_ADMISSION = OP / 'controller_claude_r1w5_c40' / 'STORAGE_ADMISSION.json'
LEASE = OP / 'CLAUDE_SCRIBE_L4_C41_TRANSPORT_LEASE.json'
POINTER = Path(r'C:\Users\wakil\Documents\Codex\AWS_COMBINED_ALLOCATION_CURRENT.json')

mode = sys.argv[1]
attempt = int(sys.argv[2])
assert mode in ('preflight', 'launch', 'watch', 'cleanup', 'status', 'console') and attempt in (1, 2)
TOKEN = JOB + '-a%d' % attempt
TAG = 'aws-c41-a%d' % attempt
os.chdir(HERE)
INTENT = HERE / (TAG + '-launch-intent.json'); STATE = HERE / (TAG + '-control.json')
CLEAN = HERE / (TAG + '-cleanup.json'); STATUS = HERE / (TAG + '-status.json')
PRE = HERE / (TAG + '-preflight.json'); WATCH = HERE / (TAG + '-watch.json')
CLAIM = OP / ('CLAUDE_SCRIBE_L4_C41_A%d_SINGLE_LAUNCH_CLAIM.json' % attempt)


def now():
    return datetime.datetime.now(datetime.timezone.utc)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, x):
    p = Path(p); tmp = p.with_name(p.name + '.%d.tmp' % os.getpid())
    with tmp.open('w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(x, indent=2, default=str)); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, p)


def log(event, **kw):
    row = {'utc': now().isoformat(), 'mode': mode, 'attempt': attempt, 'event': event, **kw}
    with (HERE / (TAG + '-events.jsonl')).open('a', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(row, default=str) + '\n'); f.flush(); os.fsync(f.fileno())
    print(json.dumps(row, default=str), flush=True)


cfg = Config(connect_timeout=8, read_timeout=20, retries={'total_max_attempts': 2, 'mode': 'standard'})
s = boto3.Session(profile_name='default', region_name=REGION)
assert s.client('sts', config=cfg).get_caller_identity()['Account'] == OWNER, 'EXACT_ACCOUNT_REQUIRED'
ec = s.client('ec2', config=cfg); ss = s.client('ssm', config=cfg); s3 = s.client('s3', config=cfg)
ACTIVE = ['pending', 'running', 'shutting-down', 'stopped', 'stopping']


def prefix_rows():
    page = s3.list_object_versions(Bucket=BUCKET, Prefix=PREFIX, ExpectedBucketOwner=OWNER, MaxKeys=200)
    assert not page.get('IsTruncated')
    return page.get('Versions', []), page.get('DeleteMarkers', [])


def preflight():
    assert sha(PAYLOAD) == PAYLOAD_SHA, 'PAYLOAD_CHANGED'
    assert sha(PREV_CLEANUP) == PREV_CLEANUP_SHA
    prev = json.loads(PREV_CLEANUP.read_bytes())
    assert prev['status'] == 'VERIFIED' and prev['prefix_cleanup_verified'] is True, 'PREVIOUS_SLOT_NOT_CLEAN'
    live = ec.describe_instances(Filters=[{'Name': 'tag:Project', 'Values': [PROJECT]}, {'Name': 'instance-state-name', 'Values': ACTIVE}])
    assert not live['Reservations'], 'ANOTHER_PROJECT_INSTANCE_IS_LIVE'
    for f in ({'Name': 'tag:Name', 'Values': [JOB]}, {'Name': 'client-token', 'Values': [TOKEN]}):
        assert not ec.describe_instances(Filters=[f, {'Name': 'instance-state-name', 'Values': ACTIVE}])['Reservations']
    versions, markers = prefix_rows()
    assert not versions and not markers, 'PREFIX_NOT_EMPTY_SLOT_BUSY'
    assert not s3.list_multipart_uploads(Bucket=BUCKET, Prefix=PREFIX, ExpectedBucketOwner=OWNER).get('Uploads')
    assert not s3.get_bucket_versioning(Bucket=BUCKET, ExpectedBucketOwner=OWNER).get('Status'), 'NEVER_VERSIONED_REQUIRED'
    lc = s3.get_bucket_lifecycle_configuration(Bucket=BUCKET, ExpectedBucketOwner=OWNER)['Rules']
    assert lc == [{'ID': 'helm-pointer-v4-seven-day-expiry', 'Status': 'Enabled', 'Filter': {'Prefix': PREFIX}, 'Expiration': {'Days': 7}}]
    pab = s3.get_public_access_block(Bucket=BUCKET, ExpectedBucketOwner=OWNER)['PublicAccessBlockConfiguration']
    assert all(pab[k] for k in ('BlockPublicAcls', 'IgnorePublicAcls', 'BlockPublicPolicy', 'RestrictPublicBuckets'))
    policy = json.loads(s3.get_bucket_policy(Bucket=BUCKET, ExpectedBucketOwner=OWNER)['Policy'])
    assert policy == json.loads(STORAGE_ADMISSION.read_bytes())['policy'], 'FOUR_KEY_WORKER_POLICY_CHANGED'
    prof = s.client('iam', config=cfg).get_instance_profile(InstanceProfileName=PROFILE)['InstanceProfile']
    assert [r['RoleName'] for r in prof['Roles']] == [PROFILE]
    sn = ec.describe_subnets(SubnetIds=[SUBNET])['Subnets'][0]
    ec.describe_security_groups(GroupIds=[SG])
    assert ec.describe_instance_type_offerings(LocationType='availability-zone', Filters=[
        {'Name': 'instance-type', 'Values': [TYPE]}, {'Name': 'location', 'Values': [sn['AvailabilityZone']]}])['InstanceTypeOfferings']
    shape = ec.describe_instance_types(InstanceTypes=[TYPE])['InstanceTypes'][0]
    assert shape['VCpuInfo']['DefaultVCpus'] == 2 and shape['MemoryInfo']['SizeInMiB'] == 4096
    ami_id = ss.get_parameter(Name=AMI_PARAM)['Parameter']['Value']
    ami = ec.describe_images(ImageIds=[ami_id])['Images'][0]
    assert ami['State'] == 'available' and ami['Architecture'] == 'x86_64' and ami['Name'].startswith('al2023-ami-')
    assert ami['OwnerId'] == '137112412989', 'AMAZON_OWNED_AMI_REQUIRED'
    pr = s.client('pricing', 'us-east-1', config=cfg).get_products(ServiceCode='AmazonEC2', Filters=[
        {'Type': 'TERM_MATCH', 'Field': k, 'Value': v} for k, v in {'instanceType': TYPE, 'location': 'US West (Oregon)',
        'operatingSystem': 'Linux', 'tenancy': 'Shared', 'preInstalledSw': 'NA', 'capacitystatus': 'Used'}.items()])
    rates = [float(d['pricePerUnit']['USD']) for p in pr['PriceList'] for t in json.loads(p).get('terms', {}).get('OnDemand', {}).values()
             for d in t['priceDimensions'].values() if d['unit'] == 'Hrs']
    assert len(rates) == 1 and rates[0] <= 0.06, rates
    hours = OS_SHUTDOWN_MIN / 60
    comp = {'compute_30min': rates[0] * hours, 'root_gp3_16gb_30min': 16 * 0.08 / 730 * hours,
            'public_ipv4_30min': 0.005 * hours, 't3_unlimited_surplus_worst_2vcpu_30min': 2 * hours * 0.05,
            's3_requests_and_transfer_allowance': 0.005}
    est = sum(comp.values())
    assert est <= CAP_USD, est
    out = {'job': JOB, 'attempt': attempt, 'client_token': TOKEN, 'utc': now().isoformat(), 'account': OWNER, 'region': REGION,
           'instance_type': TYPE, 'hourly_usd': rates[0], 'ami': ami_id, 'ami_name': ami['Name'], 'root_device': ami['RootDeviceName'],
           'subnet': SUBNET, 'availability_zone': sn['AvailabilityZone'], 'security_group': SG, 'instance_profile': PROFILE,
           'bucket': BUCKET, 'prefix': PREFIX, 'prefix_empty': True, 'payload_sha256': PAYLOAD_SHA,
           'previous_slot_cleanup_sha256': PREV_CLEANUP_SHA, 'cap_usd': CAP_USD, 'cautious_upper_usd': round(est, 6),
           'cautious_components_usd': comp, 'force_cutoff_minutes': FORCE_MIN, 'os_shutdown_minutes': OS_SHUTDOWN_MIN,
           'remote_actions': 'READ_ONLY'}
    save(PRE, out); log('PREFLIGHT_OK', cautious_upper_usd=round(est, 6), hourly=rates[0], ami=ami_id)
    return out


def discover(intent):
    rows = ec.describe_instances(Filters=[{'Name': 'tag:Name', 'Values': [JOB]}, {'Name': 'client-token', 'Values': [intent['client_token']]}])
    inst = [i for r in rows['Reservations'] for i in r['Instances']]
    assert len(inst) <= 1, 'MULTIPLE_SCOPED_INSTANCES'
    return inst[0] if inst else None


def own(iid):
    i = ec.describe_instances(InstanceIds=[iid])['Reservations'][0]['Instances'][0]
    tags = {t['Key']: t['Value'] for t in i.get('Tags', [])}
    assert tags.get('Name') == JOB and tags.get('Project') == PROJECT and i.get('ClientToken') == TOKEN
    return i


def terminate(iid, why):
    ec.terminate_instances(InstanceIds=[iid])
    log('TERMINATE_REQUESTED', instance=iid, reason=why)


def head_pin(key):
    h = s3.head_object(Bucket=BUCKET, Key=key, ExpectedBucketOwner=OWNER)
    return h['ContentLength'], h.get('Metadata', {}), h.get('VersionId') or 'null'


def download(iid):
    raw = s3.get_object(Bucket=BUCKET, Key=PREFIX + 'transport-result.json', ExpectedBucketOwner=OWNER)['Body'].read(65536)
    terminal = json.loads(raw)
    assert terminal['job'] == JOB and terminal['instance'] == iid and terminal['payload_sha256'] == PAYLOAD_SHA, 'TERMINAL_IDENTITY'
    (HERE / (TAG + '-transport-result.json')).write_bytes(raw)
    length, meta, ver = head_pin(PREFIX + 'pointer-saturation-deliverable.zip')
    assert length <= 64 * 1024 * 1024 and meta.get('sha256') == terminal['deliverable_sha256'] and meta.get('length') == str(length)
    body = s3.get_object(Bucket=BUCKET, Key=PREFIX + 'pointer-saturation-deliverable.zip', ExpectedBucketOwner=OWNER)['Body'].read(length + 1)
    assert len(body) == length and hashlib.sha256(body).hexdigest() == terminal['deliverable_sha256'], 'DELIVERABLE_SHA_MISMATCH'
    dp = HERE / (TAG + '-deliverable.zip')
    with dp.open('xb') as f:
        f.write(body); f.flush(); os.fsync(f.fileno())
    rec = {'utc': now().isoformat(), 'job': JOB, 'attempt': attempt, 'instance': iid, 'path': str(dp), 'bytes': length,
           'sha256': terminal['deliverable_sha256'], 'version_id': ver, 'terminal_sha256': hashlib.sha256(raw).hexdigest(),
           'terminal_status': terminal.get('status'), 'score_exit': terminal.get('score_exit'), 'transport_complete': True}
    save(HERE / (TAG + '-download.json'), rec); log('DOWNLOADED_AND_VERIFIED', sha256=rec['sha256'], status=rec['terminal_status'])
    return rec


def purge_prefix():
    versions, markers = prefix_rows()
    rows = [(v['Key'], v['VersionId']) for v in versions + markers]
    for k, _ in rows:
        assert k in KEYS, ('FOREIGN_KEY_REFUSED', k)
    for k, v in rows:
        s3.delete_object(Bucket=BUCKET, Key=k, VersionId=v, ExpectedBucketOwner=OWNER)
    versions, markers = prefix_rows()
    mp = s3.list_multipart_uploads(Bucket=BUCKET, Prefix=PREFIX, ExpectedBucketOwner=OWNER).get('Uploads', [])
    return {'deleted_version_count': len(rows), 'deleted_keys': sorted({k for k, _ in rows}),
            'verified_empty': not versions and not markers, 'multipart_uploads': len(mp)}


def cleanup(iid, volumes):
    i = own(iid)
    if i['State']['Name'] != 'terminated':
        terminate(iid, 'cleanup')
    for _ in range(36):
        i = own(iid)
        if i['State']['Name'] == 'terminated':
            break
        time.sleep(5)
    vstates = {}
    for v in volumes:
        try:
            vol = ec.describe_volumes(VolumeIds=[v])['Volumes'][0]
            vstates[v] = 'DELETED' if vol['State'] == 'deleted' else vol['State']
        except ec.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'InvalidVolume.NotFound':
                vstates[v] = 'DELETED'
            else:
                raise
    for _ in range(24):
        if all(x == 'DELETED' for x in vstates.values()):
            break
        time.sleep(5)
        for v in list(vstates):
            try:
                st2 = ec.describe_volumes(VolumeIds=[v])['Volumes'][0]['State']
                vstates[v] = 'DELETED' if st2 == 'deleted' else st2
            except ec.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'InvalidVolume.NotFound':
                    vstates[v] = 'DELETED'
                else:
                    raise
    out = {'utc': now().isoformat(), 'job': JOB, 'attempt': attempt, 'instance': iid, 'state': i['State']['Name'],
           'state_reason': i.get('StateTransitionReason'), 'volumes': volumes, 'volume_states': vstates}
    out['compute_cleanup_verified'] = i['State']['Name'] == 'terminated' and bool(volumes) and all(x == 'DELETED' for x in vstates.values())
    dl = HERE / (TAG + '-download.json')
    out['local_preservation_verified'] = dl.exists() and sha(json.loads(dl.read_bytes())['path']) == json.loads(dl.read_bytes())['sha256']
    if out['compute_cleanup_verified']:
        out['prefix_purge'] = purge_prefix()
        out['storage_cleanup_verified'] = out['prefix_purge']['verified_empty'] and out['prefix_purge']['multipart_uploads'] == 0
    else:
        out['storage_cleanup_verified'] = False
    out['cleanup_verified'] = bool(out['compute_cleanup_verified'] and out['storage_cleanup_verified'])
    out['status'] = ('PRESERVED_AND_PREFIX_PURGE_VERIFIED' if out['cleanup_verified'] and out['local_preservation_verified']
                     else 'CLEAN_NO_DELIVERABLE' if out['cleanup_verified'] else 'CLEANUP_PENDING')
    save(CLEAN, out); log('CLEANUP', status=out['status'])
    return out


def ledger_hold_present():
    cur = json.loads(POINTER.read_bytes())
    return cur['last_jobs'] == [JOB]


if mode == 'preflight':
    preflight()

elif mode == 'watch':
    # Independent watchdog: waits for this attempt's intent, then force-terminates at the force cutoff.
    start = time.monotonic()
    save(WATCH, {'status': 'READY', 'utc': now().isoformat(), 'job': JOB, 'attempt': attempt})
    while not INTENT.exists():
        if time.monotonic() - start > 1200:
            save(WATCH, {'status': 'EXPIRED_NO_INTENT', 'utc': now().isoformat()}); sys.exit(0)
        time.sleep(3)
    intent = json.loads(INTENT.read_bytes()); cut = datetime.datetime.fromisoformat(intent['force_cutoff_utc'])
    end = datetime.datetime.fromisoformat(intent['hard_deadline_utc']) + datetime.timedelta(minutes=5)
    while now() < end:
        try:
            i = discover(intent)
            if i is not None:
                st = i['State']['Name']
                if st == 'terminated':
                    save(WATCH, {'status': 'TERMINATED', 'instance': i['InstanceId'], 'utc': now().isoformat()}); sys.exit(0)
                if now() >= cut:
                    ec.terminate_instances(InstanceIds=[i['InstanceId']]); st = 'WATCHDOG_FORCE_TERMINATION_REQUESTED'
                save(WATCH, {'status': st, 'instance': i['InstanceId'], 'utc': now().isoformat(), 'force_cutoff_utc': cut.isoformat()})
            else:
                save(WATCH, {'status': 'WAITING_FOR_INSTANCE', 'utc': now().isoformat()})
        except Exception as e:
            save(WATCH, {'status': 'WATCH_ERROR', 'error': type(e).__name__ + ':' + str(e)[:300], 'utc': now().isoformat()})
        time.sleep(10)
    save(WATCH, {'status': 'WATCH_WINDOW_ENDED', 'utc': now().isoformat()}); sys.exit(2)

elif mode == 'launch':
    assert LEASE.exists() and json.loads(LEASE.read_bytes())['job'] == JOB, 'LEASE_REQUIRED'
    assert ledger_hold_present(), 'LEDGER_HOLD_REQUIRED'
    assert not INTENT.exists() and not STATE.exists(), 'ATTEMPT_ALREADY_USED'
    if attempt == 2:
        a1 = json.loads((HERE / 'aws-c41-a1-cleanup.json').read_bytes())
        assert a1['cleanup_verified'] is True, 'ATTEMPT1_NOT_CLEAN'
        assert (HERE / 'RETRY_DECISION_C41.json').exists(), 'PLUMBING_RETRY_DECISION_REQUIRED'
    w = json.loads(WATCH.read_bytes()); assert w['status'] == 'READY', 'WATCHDOG_NOT_READY'
    price = preflight()
    with CLAIM.open('x') as f:
        json.dump({'job': JOB, 'attempt': attempt, 'utc': now().isoformat(), 'payload_sha256': PAYLOAD_SHA}, f)
    body = PAYLOAD.read_bytes()
    put = s3.put_object(Bucket=BUCKET, Key=PREFIX + 'input.zip', Body=body, ExpectedBucketOwner=OWNER,
                        Metadata={'sha256': PAYLOAD_SHA, 'length': str(len(body))})
    log('INPUT_UPLOADED', bytes=len(body), etag=put.get('ETag'))
    started = now()
    cut = started + datetime.timedelta(minutes=FORCE_MIN)
    hard = started + datetime.timedelta(minutes=OS_SHUTDOWN_MIN)
    user = '#!/bin/bash\nshutdown -h +%d\n' % OS_SHUTDOWN_MIN
    intent = {**price, 'client_token': TOKEN, 'launch_utc': started.isoformat(), 'force_cutoff_utc': cut.isoformat(),
              'hard_deadline_utc': hard.isoformat(), 'input_key': PREFIX + 'input.zip', 'user_data': user,
              'purpose': 'SCORE_SCRIBE_L4_SEALED_98 per docs/working/scribe_l4_eval/SCORE_SCRIBE_L4_PLAN.md (sha256 18e350f5); '
                         'score the old small English model Scribe L4 (commit 84812689) on the sealed 98 with the plan script '
                         'score_scribe_l4.py (sha256 969c845e); counts only.',
              'source': 'payload c41-payload.zip sha256 ' + PAYLOAD_SHA + ' (manifest ff8eb33f)'}
    save(INTENT, intent)
    try:
        inst = ec.run_instances(ImageId=price['ami'], InstanceType=TYPE, MinCount=1, MaxCount=1, ClientToken=TOKEN,
                                SubnetId=SUBNET, SecurityGroupIds=[SG], IamInstanceProfile={'Name': PROFILE},
                                InstanceInitiatedShutdownBehavior='terminate', MetadataOptions={'HttpTokens': 'required'},
                                BlockDeviceMappings=[{'DeviceName': price['root_device'], 'Ebs': {'VolumeSize': 16, 'VolumeType': 'gp3', 'DeleteOnTermination': True}}],
                                TagSpecifications=[{'ResourceType': k, 'Tags': [{'Key': 'Name', 'Value': JOB}, {'Key': 'Project', 'Value': PROJECT},
                                                                               {'Key': 'Attempt', 'Value': str(attempt)}]} for k in ('instance', 'volume')],
                                UserData=user)['Instances'][0]
    except BaseException:
        time.sleep(5)
        found = discover(intent)
        if found is not None:
            cleanup(found['InstanceId'], [])
        raise
    iid = inst['InstanceId']
    r = {**intent, 'instance': iid, 'volumes': []}
    save(STATE, r); log('LAUNCHED', instance=iid)
    worker = (HERE / 'worker_c41.sh').read_text(encoding='utf-8')
    worker = (worker.replace('__BUCKET__', BUCKET).replace('__PREFIX__', PREFIX).replace('__JOB__', JOB)
              .replace('__INSTANCE__', iid).replace('__PAYLOAD_SHA__', PAYLOAD_SHA))
    assert '__' not in worker.replace('__pycache__', ''), 'WORKER_PLACEHOLDER_LEFT'
    command_id = None; downloaded = None; last = None; volumes = []
    try:
        while now() < hard:
            try:
                i = own(iid); st = i['State']['Name']
                vs = [x['Ebs']['VolumeId'] for x in i.get('BlockDeviceMappings', []) if 'Ebs' in x]
                if vs and vs != volumes:
                    volumes = vs; r['volumes'] = vs; save(STATE, r)
                if st == 'terminated':
                    log('OBSERVED_TERMINATED', reason=i.get('StateTransitionReason')); break
                if now() >= cut:
                    terminate(iid, 'FORCE_CUTOFF'); time.sleep(10); continue
                if command_id is None and st == 'running':
                    info = ss.describe_instance_information(Filters=[{'Key': 'InstanceIds', 'Values': [iid]}]).get('InstanceInformationList', [])
                    if any(x.get('PingStatus') == 'Online' for x in info):
                        remaining = int((cut - now()).total_seconds()) - 60
                        save(HERE / (TAG + '-dispatch-intent.json'), {'utc': now().isoformat(), 'instance': iid, 'worker_sha256': hashlib.sha256(worker.encode()).hexdigest(), 'execution_timeout': remaining})
                        command_id = ss.send_command(InstanceIds=[iid], DocumentName='AWS-RunShellScript', TimeoutSeconds=60,
                                                     Parameters={'commands': [worker], 'executionTimeout': [str(remaining)]})['Command']['CommandId']
                        save(HERE / (TAG + '-command.json'), {'utc': now().isoformat(), 'command_id': command_id, 'instance': iid})
                        log('SSM_DISPATCH', command_id=command_id)
                try:
                    ph = s3.get_object(Bucket=BUCKET, Key=PREFIX + 'progress.json', ExpectedBucketOwner=OWNER)['Body'].read(65536).decode()
                    if ph != last:
                        last = ph; log('REMOTE_PROGRESS', progress=json.loads(ph))
                except s3.exceptions.ClientError as e:
                    if e.response['Error']['Code'] not in ('404', 'NoSuchKey'):
                        raise
                if downloaded is None:
                    try:
                        s3.head_object(Bucket=BUCKET, Key=PREFIX + 'transport-result.json', ExpectedBucketOwner=OWNER)
                        downloaded = download(iid)
                        terminate(iid, 'DELIVERABLE_DOWNLOADED')
                    except s3.exceptions.ClientError as e:
                        if e.response['Error']['Code'] not in ('404', 'NoSuchKey'):
                            raise
                if command_id:
                    try:
                        inv = ss.get_command_invocation(CommandId=command_id, InstanceId=iid)
                        save(HERE / (TAG + '-command-result.json'), {k: inv.get(k) for k in ('Status', 'ResponseCode', 'ExecutionStartDateTime', 'ExecutionEndDateTime', 'StandardOutputContent', 'StandardErrorContent')})
                        if inv['Status'] in ('Failed', 'TimedOut', 'Cancelled') and downloaded is None:
                            time.sleep(15)
                            try:
                                s3.head_object(Bucket=BUCKET, Key=PREFIX + 'transport-result.json', ExpectedBucketOwner=OWNER)
                                downloaded = download(iid)
                            except s3.exceptions.ClientError:
                                pass
                            try:
                                co = ec.get_console_output(InstanceId=iid, Latest=True).get('Output', '')
                                (HERE / (TAG + '-console.txt')).write_text(co or '', encoding='utf-8')
                            except Exception:
                                pass
                            log('REMOTE_COMMAND_TERMINAL', status=inv['Status']); terminate(iid, 'COMMAND_' + inv['Status'])
                    except ss.exceptions.InvocationDoesNotExist:
                        pass
                save(STATUS, {'utc': now().isoformat(), 'instance': iid, 'state': st, 'volumes': volumes, 'downloaded': downloaded is not None})
            except Exception as e:
                log('CONTROL_ERROR', error=type(e).__name__ + ':' + str(e)[:300])
            time.sleep(10)
    finally:
        if not volumes:
            volumes = [v['VolumeId'] for v in ec.describe_volumes(Filters=[{'Name': 'tag:Name', 'Values': [JOB]}, {'Name': 'tag:Attempt', 'Values': [str(attempt)]}])['Volumes']]
            r['volumes'] = volumes; save(STATE, r)
        cleanup(iid, volumes)

else:
    r = json.loads(STATE.read_bytes())
    if mode == 'cleanup':
        cleanup(r['instance'], r['volumes'])
    elif mode == 'status':
        i = own(r['instance']); print(json.dumps({'state': i['State']['Name'], 'reason': i.get('StateTransitionReason')}))
    elif mode == 'console':
        co = ec.get_console_output(InstanceId=r['instance'], Latest=True).get('Output', '')
        (HERE / (TAG + '-console.txt')).write_text(co or '', encoding='utf-8'); print((co or '')[-4000:])
