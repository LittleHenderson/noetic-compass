"""Option B GPU job b1, single attempt. Local runtime is AWS control/transport only; never run. Derived from the op11 C1 controller."""
import base64, ctypes, gzip, json, os, re, shutil, sys, time, zipfile
from pathlib import Path
from controller_common import *

PART_SIZE=64*1024**2
OUTPUT_KEY=PREFIX+'pointer-saturation-deliverable.zip'
# b1, review round 1: the launcher and the watchdog must stay alive on the laptop for up to 180 minutes. If one of them dies,
# the host is ended and the records of a paid run can be lost. So the launch needs this much free physical memory before the claim.
# 2,000,000,000 bytes is PROPOSED by the review; it is not a measured need.
LOCAL_MEMORY_RESERVE_BYTES=2000000000
def free_physical_memory():
    """Bytes of physical memory that are free right now. Windows only (GlobalMemoryStatusEx). Reads one number; changes nothing."""
    class Status(ctypes.Structure):
        _fields_=[('dwLength',ctypes.c_ulong),('dwMemoryLoad',ctypes.c_ulong)]+[(name,ctypes.c_ulonglong) for name in ('ullTotalPhys','ullAvailPhys','ullTotalPageFile','ullAvailPageFile','ullTotalVirtual','ullAvailVirtual','ullAvailExtendedVirtual')]
    status=Status();status.dwLength=ctypes.sizeof(Status)
    require(ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))!=0,'LOCAL_MEMORY_READING_FAILED')
    return int(status.ullAvailPhys)
# b1 clock, seconds after launch (plan section 19.3): setup must end 1800, all model work stops 8100, forced shutdown 10500,
# hard limit 10800. Below they are plain numbers on purpose: the build-time text check compares them with the guest.
require(CLOCK_SECONDS==[1800,8100,10500,10800] and ARCHIVE_CAP_BYTES==100000000,'CLOCK_OR_ARCHIVE_CONTRACT')

def multipart_inventory(t,intent=None):
    result=t.call('list_multipart_uploads',Prefix=PREFIX,MaxUploads=10)
    require(not result.get('IsTruncated'),'MULTIPART_LIST_TRUNCATED')
    rows=result.get('Uploads',[])
    require(len(rows)<=1,'MULTIPART_DUPLICATE_UPLOAD_SCOPE')
    for row in rows:
        require(row['Key']==OUTPUT_KEY,'UNKNOWN_MULTIPART_KEY_NO_ABORT')
        if intent is not None:
            require((ROOT/'MULTIPART_CREATE_INTENT.json').exists(),'NO_MULTIPART_CREATE_AUTHORITY')
            stamp=row['Initiated'].timestamp()
            require(intent['launch_unix']-5<=stamp<=intent['termination_unix'],'UNKNOWN_MULTIPART_CLOCK_NO_ABORT')
            if (ROOT/'MULTIPART_UPLOAD.json').exists():require(row['UploadId']==read('MULTIPART_UPLOAD.json')['upload_id'],'UNKNOWN_UPLOAD_ID_NO_ABORT')
    return rows

def create_multipart(t,intent):
    require(not (ROOT/'MULTIPART_CREATE_INTENT.json').exists(),'CREATE_ALREADY_CONSUMED')
    save('MULTIPART_CREATE_INTENT.json',{'job':JOB,'key':OUTPUT_KEY,'original_clock':intent['launch_unix'],'utc':utc(),'once':True})
    result=t.call('create_multipart_upload',Key=OUTPUT_KEY,ContentType='application/zip',once='multipart_create')
    require(result.get('Bucket')==BUCKET and result.get('Key')==OUTPUT_KEY and isinstance(result.get('UploadId'),str),'MULTIPART_CREATE_SCOPE')
    save('MULTIPART_UPLOAD.json',{'job':JOB,'key':OUTPUT_KEY,'upload_id':result['UploadId'],'utc':utc(),'part_size':PART_SIZE,'maximum_parts':269})
    return result['UploadId']

def ensure_multipart_completed(t,terminal):
    mp=terminal['multipart'];saved=read('MULTIPART_UPLOAD.json')
    require(terminal['status']=='MULTIPART_PARTS_READY_NOT_COMPLETED' and mp['upload_id']==saved['upload_id'],'TERMINAL_MULTIPART_SCOPE')
    require(mp['part_size']==PART_SIZE and mp['whole_archive_sha256']==terminal['output_sha256'],'MULTIPART_ARCHIVE_BINDING')
    rows=mp['parts'];require(1<=len(rows)<=269 and mp['part_count']==len(rows),'PART_COUNT')
    total=0;completed=[]
    for number,row in enumerate(rows,1):
        require(row['part_number']==number and type(row['bytes']) is int and 0<row['bytes']<=PART_SIZE,'PART_SEQUENCE_OR_BYTES')
        if number<len(rows):require(row['bytes']==PART_SIZE,'NONFINAL_PART_SIZE')
        require(re.fullmatch(r'"[0-9a-f]{32}"',row['etag']) and re.fullmatch(r'[0-9a-f]{64}',row['sha256']),'PART_HASH_SHAPE')
        total+=row['bytes'];completed.append({'PartNumber':number,'ETag':row['etag']})
    require(total==terminal['output_bytes'] and 0<total<=ARCHIVE_CAP_BYTES,'EXACT_MULTIPART_TOTAL_CAP')
    terminal_hash=hashlib.sha256(json.dumps(terminal,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if not (ROOT/'MULTIPART_COMPLETE_ATTEMPT.json').exists():
        actual=t.call('list_parts',Key=OUTPUT_KEY,UploadId=mp['upload_id'],MaxParts=300)
        require(not actual.get('IsTruncated'),'PARTS_TRUNCATED')
        observed=actual.get('Parts',[])
        require([(v['PartNumber'],v['Size'],v['ETag']) for v in observed]==[(v['part_number'],v['bytes'],v['etag']) for v in rows],'ACTUAL_PARTS_DIFFER')
        save('MULTIPART_COMPLETE_ATTEMPT.json',{'job':JOB,'upload_id':mp['upload_id'],'terminal_sha256':terminal_hash,'parts':rows,'total_bytes':total,'utc':utc(),'no_retry':True})
        try:
            result=t.call('complete_multipart_upload',Key=OUTPUT_KEY,UploadId=mp['upload_id'],MultipartUpload={'Parts':completed},once='multipart_complete')
            require(result.get('Key')==OUTPUT_KEY and result.get('Bucket')==BUCKET and (result.get('VersionId') or 'null')=='null','COMPLETION_SCOPE')
            save('MULTIPART_COMPLETE_RESPONSE.json',{'job':JOB,'upload_id':mp['upload_id'],'etag':result.get('ETag'),'utc':utc()})
        except Exception as e:preserve_error('multipart_completion_no_retry',e)
    else:require(read('MULTIPART_COMPLETE_ATTEMPT.json')['terminal_sha256']==terminal_hash,'TERMINAL_CHANGED_AFTER_COMPLETION_ATTEMPT')
    head=t.head(OUTPUT_KEY,version_id='null')
    require(head['ContentLength']==total and (head.get('VersionId') or 'null')=='null','COMPLETED_OBJECT_LENGTH')
    save('MULTIPART_COMPLETION_OBSERVED.json',{'job':JOB,'upload_id':mp['upload_id'],'bytes':total,'terminal_sha256':terminal_hash,'utc':utc(),'exactly_one_completion_attempt':True})

def abort_multipart(t,intent):
    rows=multipart_inventory(t,intent)
    for row in rows:
        upload_id=row['UploadId'];token=hashlib.sha256(upload_id.encode()).hexdigest()[:24]
        for attempt in range(2):
            try:t.call('abort_multipart_upload',Key=OUTPUT_KEY,UploadId=upload_id,once='abort_'+token+'_'+str(attempt))
            except Exception as e:
                if (getattr(e,'response',None) or {}).get('Error',{}).get('Code')!='NoSuchUpload':preserve_error('multipart_abort',e)
            try:
                parts=t.call('list_parts',Key=OUTPUT_KEY,UploadId=upload_id,MaxParts=300)
                require(not parts.get('IsTruncated'),'ABORT_PARTS_TRUNCATED')
            except Exception as e:
                if (getattr(e,'response',None) or {}).get('Error',{}).get('Code')=='NoSuchUpload':break
                raise
            time.sleep(2)
    remaining=multipart_inventory(t,intent)
    require(not remaining,'MULTIPART_CLEANUP_INCOMPLETE')
    save('MULTIPART_CLEANUP.json',{'job':JOB,'utc':utc(),'remaining_uploads':0,'previous_upload_count':len(rows),'incomplete_parts_aborted_and_absence_verified':True})

def private_preflight(t):
    require(t.get_bucket_location(Bucket=BUCKET)['LocationConstraint']==REGION,'BUCKET_REGION')
    require(t.get_bucket_request_payment(Bucket=BUCKET)['Payer']=='BucketOwner','REQUESTER_PAYS')
    require(t.get_bucket_accelerate_configuration(Bucket=BUCKET).get('Status')!='Enabled','ACCELERATION')
    require(not t.control('get_bucket_versioning',Bucket=BUCKET).get('Status'),'NEVER_VERSIONED')
    public=t.control('get_public_access_block',Bucket=BUCKET)['PublicAccessBlockConfiguration']
    require(all(public.values()),'PUBLIC_BLOCK')
    require(t.control('get_bucket_policy_status',Bucket=BUCKET)['PolicyStatus']['IsPublic'] is False,'PRIVATE_BUCKET')
    lifecycle=t.control('get_bucket_lifecycle_configuration',Bucket=BUCKET)['Rules']
    require(any(v.get('Status')=='Enabled' and v.get('Expiration',{}).get('Days')==7 and
        (v.get('Filter',{}).get('Prefix')==PREFIX or v.get('Prefix')==PREFIX) for v in lifecycle),'SEVEN_DAY_PREFIX_EXPIRY')
    require(not t.list_objects_v2(Bucket=BUCKET,Prefix=PREFIX,MaxKeys=10).get('Contents'),'TRANSPORT_PREFIX_BUSY')
    require(not multipart_inventory(t),'TRANSPORT_MULTIPART_BUSY')

def reopen(path,complete):
    """Hash every member in bounded chunks. Never executes or extracts evidence."""
    count=0;unpacked=0;inventory=[]
    with zipfile.ZipFile(path) as z:
        names=[i.filename for i in z.infolist()];require(len(set(names))==len(names),'DUPLICATE_MEMBERS')
        require(len(names)<=100000,'ARCHIVE_MEMBER_CAP')
        for i in z.infolist():
            name=Path(i.filename.replace('\\','/'));require(not name.is_absolute() and '..' not in name.parts and ':' not in i.filename,'ARCHIVE_PATH')
            require(not i.flag_bits&1,'ENCRYPTED_ARCHIVE')
            unpacked+=i.file_size;require(unpacked<=ARCHIVE_CAP_BYTES,'EXPANSION_CAP')
            h=hashlib.sha256();length=0
            with z.open(i) as f:
                for b in iter(lambda:f.read(1024*1024),b''):
                    require(time.time()<float(os.environ.get('OP11_CONTROL_DEADLINE_UNIX','inf')),'REOPEN_ABSOLUTE_DEADLINE')
                    length+=len(b);h.update(b)
            require(length==i.file_size,'MEMBER_LENGTH');inventory.append({'path':i.filename,'bytes':length,'sha256':h.hexdigest()});count+=1
        require('controller/GUEST_RESULT.json' in names,'GUEST_RESULT_REQUIRED')
        if complete:
            manifest_info=z.getinfo('controller/REQUIRED_EVIDENCE_INVENTORY.json');require(manifest_info.file_size<=32*1024**2,'INVENTORY_CAP')
            expected=json.loads(z.read(manifest_info))['members']
            actual=[v for v in inventory if v['path']!='controller/REQUIRED_EVIDENCE_INVENTORY.json']
            require(sorted(expected,key=lambda v:v['path'])==sorted(actual,key=lambda v:v['path']),'COMPLETE_EVIDENCE_INVENTORY_CLOSURE')
        else:require('controller/RETRIEVAL_INCOMPLETE.json' in names,'INCOMPLETE_FAILURE_RECEIPT_REQUIRED')
    save('ARTIFACT_REOPEN_VERIFICATION.json',{'job':JOB,'status':'REOPEN_HASH_VERIFIED','archive_sha256':sha(path),'members':inventory,'total_bytes':unpacked,'member_count':count})

def retrieve(t,instance):
    intent=read('LAUNCH_INTENT.json')
    old_deadline=os.environ.get('OP11_CONTROL_DEADLINE_UNIX')
    os.environ['OP11_CONTROL_DEADLINE_UNIX']=str(min(float(old_deadline or 'inf'),intent['termination_unix']-300))
    try:return retrieve_with_deadline(t,instance)
    finally:
        if old_deadline is None:os.environ.pop('OP11_CONTROL_DEADLINE_UNIX',None)
        else:os.environ['OP11_CONTROL_DEADLINE_UNIX']=old_deadline

def retrieve_with_deadline(t,instance):
    key=PREFIX+'transport-result.json'
    try:raw=t.get_bytes(key,limit=64*1024)
    except Exception as e:
        if (getattr(e,'response',None) or {}).get('Error',{}).get('Code') in ('404','NoSuchKey'):return False
        raise
    terminal=json.loads(raw);require(terminal['job']==JOB and terminal['instance']==instance,'TERMINAL_SCOPE')
    require(terminal['output_key']==PREFIX+'pointer-saturation-deliverable.zip' and terminal['payload_manifest_sha256']==sha(ROOT/'CONTRACT.json'),'TERMINAL_SOURCE')
    save('REMOTE_TERMINAL.json',terminal)
    if terminal['status']=='TRANSPORT_INCOMPLETE_CONTROLLER_MUST_ABORT':
        save('REMOTE_TRANSPORT_INCOMPLETE.json',{'job':JOB,'instance':instance,'terminal_sha256':hashlib.sha256(raw).hexdigest(),'scientific_archive_retrieved':False,'utc':utc()})
        return False
    require(0<terminal['output_bytes']<=ARCHIVE_CAP_BYTES,'OUTPUT_CAP')
    if (ROOT/'DOWNLOAD.json').exists():
        saved=read('DOWNLOAD.json');require(sha(ROOT/'deliverable.zip')==saved['sha256'],'PRESERVATION_CHANGED');return True
    ensure_multipart_completed(t,terminal)
    receipt=t.get_file(terminal['output_key'],ROOT/'deliverable.zip',max_bytes=ARCHIVE_CAP_BYTES,
        expected_bytes=terminal['output_bytes'],expected_sha256=terminal['output_sha256'],version_id='null',once='final_get')
    require(isinstance(terminal['complete_required_evidence'],bool),'TERMINAL_COMPLETENESS_REQUIRED')
    reopen(ROOT/'deliverable.zip',terminal['complete_required_evidence']);save('DOWNLOAD.json',{'job':JOB,'instance':instance,**receipt,'transport_complete':True,'complete_required_evidence':terminal['complete_required_evidence']})
    return True

def cleanup(ec,t,intent,instance=None):
    os.environ['OP11_CONTROL_DEADLINE_UNIX']=str(intent['termination_unix']-60)
    if instance:
        try:terminate(ec,instance)
        except Exception as e:preserve_error('terminate_known_instance',e)
    found=discover(ec,intent)
    if found:
        instance=found['InstanceId']
        if found['State']['Name']!='terminated':terminate(ec,instance)
    # No prefix purge until the full required archive reopens locally.
    preserved=False;errored=False
    if instance:
        try:preserved=retrieve(t,instance)
        except Exception as e:errored=True;preserve_error('retrieve_during_cleanup',e)
    # Leave three minutes for scoped object disposition and independent verification.
    end=intent['termination_unix']-180
    while time.time()<end:
        found=discover(ec,intent);vols=scoped_volumes(ec)
        for v in vols:
            require(v['VolumeType']=='gp3' and v['Size']==100,'VOLUME_SCOPE')
            if v['State']=='available':ec.delete_volume(VolumeId=v['VolumeId'])
        if (not found or found['State']['Name']=='terminated') and not vols:break
        time.sleep(10)
    # Recheck after termination polling: never abort while an uploader may live.
    found=discover(ec,intent)
    uploader_stopped=bool(found and found['State']['Name']=='terminated') or (not found and not (ROOT/'EC2_LAUNCH_ATTEMPT.json').exists())
    if not uploader_stopped:
        save('CLEANUP_BLOCKED_UPLOADER_LIVE_OR_UNKNOWN.json',{'job':JOB,'utc':utc(),'instance':instance,'state':found['State']['Name'] if found else 'UNKNOWN_AFTER_EC2_ATTEMPT','multipart_absence_not_claimed':True})
    require(uploader_stopped,'UPLOADER_NOT_VERIFIED_STOPPED_NO_MULTIPART_ABORT')
    # The authorized route remains never-versioned. Verify actual null versions before deletion.
    # C1: the host is already terminated here. If retrieval errored and completion was never observed, the uploaded
    # parts may be the only copy of the results: keep them, record the blocker and stop as not verified.
    if errored and not (ROOT/'MULTIPART_COMPLETION_OBSERVED.json').exists():
        save('CLEANUP_BLOCKED_PARTS_RETAINED.json',{'job':JOB,'utc':utc(),'instance':instance,'multipart_not_aborted':True,'host_terminated':True})
        raise RuntimeError('RETRIEVAL_ERRORED_MULTIPART_NOT_ABORTED')
    abort_multipart(t,intent)
    require(not t.control('get_bucket_versioning',Bucket=BUCKET).get('Status'),'CLEANUP_NEVER_VERSIONED_REQUIRED')
    versions=t.list_object_versions(Bucket=BUCKET,Prefix=PREFIX,MaxKeys=10)
    require(not versions.get('IsTruncated') and not versions.get('DeleteMarkers'),'UNEXPECTED_VERSION_STATE_NO_DELETE')
    objects=versions.get('Versions',[])
    require(all(v['Key'] in {PREFIX+k for k in KEYS} and v.get('VersionId')=='null' and v.get('IsLatest') is True for v in objects),'UNKNOWN_OBJECT_OR_VERSION_NO_DELETE')
    require(len({v['Key'] for v in objects})==len(objects),'DUPLICATE_VERSION_NO_DELETE')
    save('CLEANUP_VERSION_INVENTORY.json',{'job':JOB,'utc':utc(),'preserved':preserved,'objects':[{'key':v['Key'],'version_id':v['VersionId']} for v in objects]})
    small_preserved=set()
    if not preserved:
        for v in objects:
            if v['Key'] in (PREFIX+'progress.json',PREFIX+'transport-result.json'):
                raw=t.get_bytes(v['Key'],limit=64*1024,version_id='null')
                value=json.loads(raw);require(value['job']==JOB,'SMALL_CLEANUP_SCOPE')
                save('PRESERVED_'+v['Key'].rsplit('/',1)[-1],{'value':value,'original_sha256':hashlib.sha256(raw).hexdigest(),'original_bytes':len(raw),'utc':utc()})
                small_preserved.add(v['Key'])
    for v in objects:
        if preserved or v['Key']==PREFIX+'input.zip' or v['Key'] in small_preserved:t.delete_object(Bucket=BUCKET,Key=v['Key'],VersionId=v['VersionId'])
    remaining=t.list_objects_v2(Bucket=BUCKET,Prefix=PREFIX,MaxKeys=10).get('Contents',[])
    save('CLEANUP.json',{'job':JOB,'utc':utc(),'instance':instance,'host_terminated':not found or found['State']['Name']=='terminated','volumes_remaining':[v['VolumeId'] for v in scoped_volumes(ec)],'prefix_empty':not remaining,'multipart_uploads_remaining':0,'preserved':preserved,'retained_output_keys':[v['Key'] for v in remaining],'retained_until_existing_expiry':bool(remaining),'small_control_objects_preserved_locally':sorted(small_preserved),'all_in_final_bill':'PENDING_NO_HOLD_RELEASE'})

def read_watch():
    # The watcher replaces this file every few seconds; a read can collide with the replace on Windows.
    for attempt in range(8):
        try:return read('WATCH.json')
        except (OSError,ValueError):
            if attempt==7:raise
            time.sleep(0.25)
def tolerate(error,calm,stage):
    # C1: a transient failure of a read-only poll skips one tick; never more than fifteen in a row.
    response=getattr(error,'response',None) or {}
    status=response.get('ResponseMetadata',{}).get('HTTPStatusCode',0);code=response.get('Error',{}).get('Code','')
    soft=(not response and type(error).__name__ in ('EndpointConnectionError','ConnectTimeoutError','ReadTimeoutError','ConnectionClosedError','ConnectionError','SSLError','HTTPClientError','ResponseStreamingError','IncompleteReadError')) or status>=500 or code in ('RequestLimitExceeded','Throttling','ThrottlingException','RequestTimeout','RequestTimeoutException','SlowDown','InternalError','ServiceUnavailable')
    calm[0]+=1
    if not soft or calm[0]>15:return False
    save('TRANSIENT_POLL_'+str(time.time_ns())+'.json',{'job':JOB,'utc':utc(),'stage':stage,'type':type(error).__name__,'aws_code':code or None,'http_status':status or None,'in_a_row':calm[0],'action':'SKIPPED_ONE_TICK'})
    return True
def launch():
    a,price=authority();ec,ssm,raw,t=clients()
    require(not (ROOT/'LAUNCH_INTENT.json').exists() and not (ROOT/'SINGLE_ATTEMPT_CLAIM.json').exists(),'SINGLE_ATTEMPT_CONSUMED')
    watch=read_watch();require(watch['job']==JOB and watch['status']=='READY' and 0<=time.time()-watch['heartbeat_unix']<20,'WATCH_REQUIRED')
    private_preflight(t);no_live_conflict(ec)
    worker=(ROOT/'worker_v02.py').read_bytes();require(len(worker)<=131072,'WORKER_EXPANSION_CAP')
    encoded_worker=base64.b64encode(gzip.compress(worker,mtime=0)).decode()
    require(shutil.disk_usage(ROOT).free>=24000000000,'LOCAL_STREAMING_CUSTODY_DISK_RESERVE')
    # b1, review round 1: free memory gate, beside the disk gate and before the claim. A miss here costs nothing.
    free_memory=free_physical_memory();require(free_memory>=LOCAL_MEMORY_RESERVE_BYTES,'LOCAL_MEMORY_RESERVE: %d bytes of physical memory are free; %d are needed. Close programs and start again.'%(free_memory,LOCAL_MEMORY_RESERVE_BYTES))
    save('LOCAL_MEMORY_GATE.json',{'job':JOB,'utc':utc(),'free_physical_memory_bytes':free_memory,'required_bytes':LOCAL_MEMORY_RESERVE_BYTES,'checked_before_claim':True})
    def urls(upload_id,expires=10800):
        return {'input_url':raw.generate_presigned_url('get_object',Params={'Bucket':BUCKET,'Key':PREFIX+'input.zip'},ExpiresIn=expires),
            'put_urls':{k:raw.generate_presigned_url('put_object',Params={'Bucket':BUCKET,'Key':PREFIX+k},ExpiresIn=expires) for k in ('progress.json','transport-result.json')},
            'multipart':{'upload_id':upload_id,'part_size':PART_SIZE,'part_urls':{str(n):raw.generate_presigned_url('upload_part',Params={'Bucket':BUCKET,'Key':OUTPUT_KEY,'UploadId':upload_id,'PartNumber':n},ExpiresIn=expires) for n in range(1,270)}}}
    trial=urls('0'*2048);require(len(base64.b64encode(gzip.compress(json.dumps(trial).encode(),mtime=0)))+len(encoded_worker)+16384<60000,'SSM_SIZE_BEFORE_STAGING')
    save('SSM_SOURCE_BOUND.json',{'compressed_worker_base64_bytes':len(encoded_worker),'overhead_reserved':16384,'limit':60000,'checked_before_paid_host':True})
    with (ROOT/'SINGLE_ATTEMPT_CLAIM.json').open('x') as f:json.dump({'job':JOB,'utc':utc(),'attempt':1},f);f.flush();os.fsync(f.fileno())
    started=time.time();os.environ['OP11_CONTROL_DEADLINE_UNIX']=str(started+10740)
    intent={'job':JOB,'client_token':JOB,'launch_unix':started,'setup_cutoff_unix':started+1800,'work_cutoff_unix':started+8100,'force_cutoff_unix':started+10500,'termination_unix':started+10800,'input_sha256':a['input_zip_sha256'],'payload_manifest_sha256':a['payload_manifest_sha256']}
    save('LAUNCH_INTENT.json',intent)
    try:
        os.environ['OP11_CONTROL_DEADLINE_UNIX']=str(intent['setup_cutoff_unix']-600)
        staged=t.put_file(PREFIX+'input.zip',ROOT/'input.zip',max_bytes=INPUT_CAP_BYTES,once='input_put')
        require(staged['sha256']==a['input_zip_sha256'] and staged['bytes']==a['input_zip_bytes'],'STAGED_INPUT_IDENTITY')
        save('INPUT_UPLOAD.json',{'job':JOB,'sha256':staged['sha256'],'bytes':staged['bytes'],'utc':utc()})
        os.environ['OP11_CONTROL_DEADLINE_UNIX']=str(intent['termination_unix']-60)
        watch=read_watch();require(watch['job']==JOB and watch['status'] in ('READY','DISCOVERING_SCOPED_LAUNCH') and 0<=time.time()-watch['heartbeat_unix']<20,'WATCH_EXPIRED_DURING_STAGING')
        if watch['status']=='DISCOVERING_SCOPED_LAUNCH':require(watch['intent_sha256']==sha(ROOT/'LAUNCH_INTENT.json'),'WATCH_INTENT_MISMATCH')
        require(time.time()<intent['setup_cutoff_unix']-600,'STAGING_MUST_LEAVE_TEN_MINUTES_SETUP')
        upload_id=create_multipart(t,intent)
        signed=urls(upload_id,max(1,int(intent['termination_unix']-time.time())))
        require(len(json.dumps(signed).encode())+16384<1048576,'ACTUAL_CONFIG_EXPANSION_CAP')
        require(len(base64.b64encode(gzip.compress(json.dumps(signed).encode(),mtime=0)))+len(encoded_worker)+16384<60000,'EXACT_SIGNED_SSM_SIZE_BEFORE_PAID_HOST')
    except BaseException as e:
        preserve_error('no_host_staging_or_poststage',e)
        cleanup(ec,t,intent,None)
        raise
    # Absolute original clock, independently enforced by systemd and AWS watcher.
    # A persistent service recalculates the original absolute cutoff after reboot.
    userdata='''#!/bin/bash
set -eu
umask 077
cat > /usr/local/sbin/helm-op11-deadline <<'HELM_DEADLINE'
#!/bin/bash
set -eu
remaining=$(( CUTOFF_EPOCH - $(date +%s) ))
if [ "$remaining" -gt 0 ]; then sleep "$remaining"; fi
/sbin/shutdown -h now
HELM_DEADLINE
chmod 700 /usr/local/sbin/helm-op11-deadline
cat > /etc/systemd/system/helm-op11-host-deadline.service <<'HELM_UNIT'
[Unit]
Description=HELM original absolute host termination deadline
[Service]
Type=simple
ExecStart=/usr/local/sbin/helm-op11-deadline
Restart=on-failure
RestartSec=1
[Install]
WantedBy=multi-user.target
HELM_UNIT
systemctl daemon-reload
systemctl enable --now helm-op11-host-deadline.service
'''.replace('CUTOFF_EPOCH',str(int(started+10500)))
    instance=None
    try:
        save('EC2_LAUNCH_ATTEMPT.json',{'job':JOB,'client_token':JOB,'utc':utc(),'original_clock':started,'once':True})
        response=ec.run_instances(ImageId=AMI,InstanceType=INSTANCE_TYPE,MinCount=1,MaxCount=1,ClientToken=JOB,
            SubnetId='subnet-02deacfa16bdaa4f4',SecurityGroupIds=['sg-0562c483e0364cdab'],IamInstanceProfile={'Name':'cas-aws-gpu-standby-v1-us-west-2'},
            InstanceInitiatedShutdownBehavior='terminate',MetadataOptions={'HttpTokens':'required'},
            BlockDeviceMappings=[{'DeviceName':'/dev/sda1','Ebs':{'VolumeSize':100,'VolumeType':'gp3','DeleteOnTermination':True}}],
            TagSpecifications=[{'ResourceType':k,'Tags':[{'Key':'Name','Value':JOB},{'Key':'Project','Value':'HELM-pointer-saturation'}]} for k in ('instance','volume')],UserData=userdata)
        instance=response['Instances'][0]['InstanceId'];save('CONTROL.json',{**intent,'instance':instance})
        print(json.dumps({'event':'ACTUAL_LAUNCH_CONFIRMED','job':JOB,'instance':instance,'launch_unix':started,'deadline_unix':started+10800}),flush=True)
        while time.time()<started+1800:
            w=read_watch()
            if w.get('instance')==instance and w.get('status')=='ARMED' and 0<=time.time()-w['heartbeat_unix']<20:break
            time.sleep(5)
        require(w.get('instance')==instance and w.get('status')=='ARMED' and w.get('intent_sha256')==sha(ROOT/'LAUNCH_INTENT.json'),'WATCH_NOT_ARMED')
        config={**intent,**signed,'instance':instance,'input_bytes':a['input_zip_bytes'],'output_key':PREFIX+'pointer-saturation-deliverable.zip','external_watch_pid':w['pid']}
        config_bytes=json.dumps(config).encode();require(len(config_bytes)<=1048576,'CONFIG_EXPANSION_CAP')
        encoded_config=base64.b64encode(gzip.compress(config_bytes,mtime=0)).decode()
        # Source decode is control bootstrap, not a test or model entry point.
        bootstrap="set -eu\numask 077\nmkdir -p /opt/helm-op11-worker\ncd /opt/helm-op11-worker\n/usr/bin/python3 - <<'PY'\nimport base64,gzip,hashlib,pathlib\nfor name,data,expected in [('guest.json','"+encoded_config+"','"+hashlib.sha256(config_bytes).hexdigest()+"'),('worker_v02.py','"+encoded_worker+"','"+hashlib.sha256(worker).hexdigest()+"')]:\n b=gzip.decompress(base64.b64decode(data));assert len(b)<=(131072 if name=='worker_v02.py' else 1048576) and hashlib.sha256(b).hexdigest()==expected;pathlib.Path(name).write_bytes(b)\nPY\nremaining=$(( "+str(int(started+10500))+" - $(date +%s) ))\ntest \"$remaining\" -gt 0\nsystemctl is-active --quiet helm-op11-host-deadline.service\nsystemd-run --unit helm-op11-work --collect --wait --pipe -p MemoryMax=28G -p MemorySwapMax=0 -p TasksMax=128 -p CPUQuota=800% -p KillMode=control-group -p TimeoutStopSec=5 -p RuntimeMaxSec=\"${remaining}s\" /opt/pytorch/bin/python -B /opt/helm-op11-worker/worker_v02.py\n"
        require(len(bootstrap.encode())<60000,'SSM_SIZE')
        dispatched=False;downloaded=False;seen={};calm=[0]
        while time.time()<intent['force_cutoff_unix']:
            before=calm[0]
            try:i=discover(ec,intent)
            except Exception as e:
                if isinstance(e,RuntimeError) or not tolerate(e,calm,'discover'):raise
                time.sleep(30);continue
            require(i is not None,'INSTANCE_DISAPPEARED')
            if not dispatched and time.time()<started+1800:
                try:online=ssm.describe_instance_information(Filters=[{'Key':'InstanceIds','Values':[instance]}]).get('InstanceInformationList',[])
                except Exception as e:
                    if not tolerate(e,calm,'ssm_online'):raise
                    online=[]
                if any(x.get('PingStatus')=='Online' for x in online):
                    w=read_watch();require(w.get('instance')==instance and w.get('status')=='ARMED' and 0<=time.time()-w['heartbeat_unix']<90,'WATCH_AT_DISPATCH')
                    dispatched=True;save('DISPATCH_INTENT.json',{'job':JOB,'instance':instance,'utc':utc(),'worker_sha256':sha(ROOT/'worker_v02.py'),'no_retry':True})
                    command=ssm.send_command(InstanceIds=[instance],DocumentName='AWS-RunShellScript',TimeoutSeconds=60,Parameters={'commands':[bootstrap],'executionTimeout':[str(max(1,int(started+10500-time.time())))]})['Command']['CommandId']
                    save('COMMAND.json',{'job':JOB,'instance':instance,'command_id':command,'utc':utc()})
            if not dispatched and time.time()>=started+1800:raise RuntimeError('SSM_NOT_READY_THIRTY_MINUTES')
            w=read_watch();require(0<=time.time()-w['heartbeat_unix']<180,'WATCH_HEARTBEAT_LOST')
            try:downloaded=retrieve(t,instance)
            except Exception as e:
                if isinstance(e,RuntimeError) or not tolerate(e,calm,'retrieve'):raise
                downloaded=False
            if downloaded or i['State']['Name']=='terminated':break
            try:
                progress=json.loads(t.get_bytes(PREFIX+'progress.json',limit=64*1024));require(progress['job']==JOB and progress['instance']==instance,'PROGRESS_SCOPE');save('LATEST_PROGRESS.json',progress);seen=progress
            except Exception as e:
                if (getattr(e,'response',None) or {}).get('Error',{}).get('Code') in ('404','NoSuchKey'):progress=seen
                elif isinstance(e,RuntimeError) or not tolerate(e,calm,'progress'):raise
                else:progress=seen
            if time.time()>=intent['setup_cutoff_unix']:require(progress.get('setup_complete') is True,'SETUP_CUTOFF')
            if dispatched:
                try:invocation=ssm.get_command_invocation(CommandId=command,InstanceId=instance)
                except Exception as e:
                    if (getattr(e,'response',None) or {}).get('Error',{}).get('Code')!='InvocationDoesNotExist' and not tolerate(e,calm,'ssm_invocation'):raise
                    invocation={'Status':'Pending'}
                if invocation['Status'] in ('Failed','Cancelled','TimedOut','Success'):
                    save('SSM_TERMINAL.json',{k:invocation.get(k) for k in ('Status','ResponseCode','StandardOutputContent','StandardErrorContent','ExecutionStartDateTime','ExecutionEndDateTime')})
                    require(retrieve(t,instance),'GUEST_EXIT_WITHOUT_TERMINAL');break
            if calm[0]==before:calm[0]=0
            save('STATUS.json',{'job':JOB,'instance':instance,'utc':utc(),'dispatch':dispatched,'downloaded':downloaded,'phase':progress.get('stage'),'setup_complete':progress.get('setup_complete'),'transient_polls_in_a_row':calm[0]})
            time.sleep(120)
    except BaseException as error:preserve_error('launch_or_monitor',error);raise
    finally:cleanup(ec,t,intent,instance)

SUBNET='subnet-02deacfa16bdaa4f4';SECURITY_GROUP='sg-0562c483e0364cdab'
def readiness():
    """Read-only checks before the claim. No host, no upload, no storage write, no invoice call. Writes local receipts only.
    b1: takes the place of read_only_readiness_c1.py and read_only_storage_network_prices_v02.py of the op11 controller."""
    require(not (ROOT/'LAUNCH_INTENT.json').exists() and not (ROOT/'SINGLE_ATTEMPT_CLAIM.json').exists(),'SINGLE_ATTEMPT_CONSUMED')
    r={'job':JOB,'utc':utc(),'actions':'EXISTING_AUTHORIZED_AWS_READ_ONLY','paid_compute_launched':False,'storage_uploads':0,'new_credentials':False,'security_changes':False,'local_project_execution':False,'invoice_apis':'NOT_CALLED','s3_read_requests':0}
    try:
        cfg=Config(connect_timeout=8,read_timeout=20,retries={'total_max_attempts':1})
        session=boto3.Session(profile_name='default',region_name=REGION)
        identity=session.client('sts',config=cfg).get_caller_identity()
        require(identity['Arn']==f'arn:aws:iam::{ACCOUNT}:user/cas-g5-operator','IDENTITY');r['identity_arn']=identity['Arn']
        ec=session.client('ec2',config=cfg)
        # The most recent job on the shared four-key slot: a VERIFIED record in the launch gate's form, and the ledger's last job.
        prior=read('PRIOR_INDEPENDENT_CLEANUP.json')
        require(prior['job']!=JOB and prior['schema']=='pointer.saturation.independent-cleanup/1' and prior['bucket']==BUCKET and prior['prefix']==PREFIX and prior['status']=='VERIFIED' and prior['cleanup_verified'] is True and prior['compute_cleanup_verified'] is True and prior['prefix_cleanup_verified'] is True and prior['instance_state']=='terminated' and not prior['active_own_job_instances'] and not prior['prefix_versions_remaining'],'PRIOR_VERIFIED_CLOSURE')
        pointer=json.loads(LEDGER_POINTER.read_text(encoding='utf-8-sig'))
        require(pointer.get('last_jobs')==[prior['job']],'PRIOR_CLEANUP_IS_NOT_FOR_THE_LAST_JOB_ON_THE_LEDGER')
        free=cents(pointer['ceiling_usd'])-cents(pointer['combined_allocation_usd']);require(free>=cents(CAP_USD),'CAP_EXCEEDS_UNRESERVED_FUNDS')
        r.update(prior_slot_job=prior['job'],prior_cleanup_sha256=sha(ROOT/'PRIOR_INDEPENDENT_CLEANUP.json'),ledger_unreserved_cents=free,ledger_pointer_sha256=sha(LEDGER_POINTER))
        no_live_conflict(ec)
        vols=ec.describe_volumes(Filters=[{'Name':'tag:Name','Values':[JOB,prior['job']]}])
        require(not vols.get('NextToken') and not vols['Volumes'],'SCOPED_VOLUME_CONFLICT')
        seen=ec.describe_instances(Filters=[{'Name':'instance-id','Values':[prior['instance']]}])
        states=[i['State']['Name'] for g in seen['Reservations'] for i in g['Instances']]
        require(not seen.get('NextToken') and states in ([],['terminated']),'PRIOR_NOT_TERMINATED')
        r.update(prior_job_states=states,prior_job_closure='PINNED_VERIFIED_TERMINATION_AND_FRESH_NO_LIVE_CONFLICT; old ID may be absent from current listings',no_live_conflict=True)
        images=ec.describe_images(ImageIds=[AMI])['Images']
        require(len(images)==1 and images[0]['State']=='available' and images[0]['Architecture']=='x86_64' and images[0].get('Platform')!='windows' and not images[0].get('ProductCodes'),'EXISTING_IMAGE')
        disks=[d['Ebs'] for d in images[0]['BlockDeviceMappings'] if 'Ebs' in d]
        require(len(disks)==1 and disks[0]['VolumeSize']<=100,'IMAGE_DISK_BOUND')
        r['image']={'id':images[0]['ImageId'],'name':images[0].get('Name'),'root_gib':disks[0]['VolumeSize']}
        subnet=ec.describe_subnets(SubnetIds=[SUBNET])['Subnets'][0];group=ec.describe_security_groups(GroupIds=[SECURITY_GROUP])['SecurityGroups'][0]
        require(subnet['State']=='available' and subnet['MapPublicIpOnLaunch'] and subnet['VpcId']==group['VpcId'],'EXISTING_NETWORK')
        shape=ec.describe_instance_types(InstanceTypes=[INSTANCE_TYPE])['InstanceTypes'][0]
        require(shape['MemoryInfo']['SizeInMiB']>=32768 and shape['VCpuInfo']['DefaultVCpus']==8 and shape.get('GpuInfo',{}).get('TotalGpuMemoryInMiB',0)>=22000,'GPU_MEMORY_CPU_SHAPE')
        offering=ec.describe_instance_type_offerings(LocationType='availability-zone',Filters=[{'Name':'location','Values':[subnet['AvailabilityZone']]},{'Name':'instance-type','Values':[INSTANCE_TYPE]}])
        require(offering.get('InstanceTypeOfferings') and not offering.get('NextToken'),'EXISTING_AZ_GPU_OFFERING')
        r.update(existing_network={'subnet':SUBNET,'security_group':SECURITY_GROUP,'vpc':subnet['VpcId'],'zone':subnet['AvailabilityZone']},capacity_guaranteed=False)
        s3=session.client('s3',config=cfg);route={}
        for name,operation in (('location','get_bucket_location'),('request_payment','get_bucket_request_payment'),('acceleration','get_bucket_accelerate_configuration'),('versioning','get_bucket_versioning'),('public_access','get_public_access_block'),('policy_status','get_bucket_policy_status'),('lifecycle','get_bucket_lifecycle_configuration')):
            r['s3_read_requests']+=1;route[name]=getattr(s3,operation)(Bucket=BUCKET,ExpectedBucketOwner=ACCOUNT)
        r['s3_read_requests']+=1;objects=s3.list_objects_v2(Bucket=BUCKET,Prefix=PREFIX,MaxKeys=10,ExpectedBucketOwner=ACCOUNT)
        r['s3_read_requests']+=1;uploads=s3.list_multipart_uploads(Bucket=BUCKET,Prefix=PREFIX,MaxUploads=10,ExpectedBucketOwner=ACCOUNT)
        require(not uploads.get('Uploads') and not uploads.get('IsTruncated'),'MULTIPART_PREFIX_BUSY')
        require(route['location']['LocationConstraint']==REGION,'BUCKET_REGION')
        require(route['request_payment']['Payer']=='BucketOwner','BUCKET_PAYER')
        require(not route['versioning'].get('Status'),'NEVER_VERSIONED_ROUTE_REQUIRED')
        require(route['acceleration'].get('Status')!='Enabled','ACCELERATION_COST')
        require(not objects.get('Contents') and not objects.get('IsTruncated'),'PREFIX_BUSY')
        require(route['policy_status']['PolicyStatus']['IsPublic'] is False and all(route['public_access']['PublicAccessBlockConfiguration'].values()),'PRIVATE_ROUTE')
        require(any(v['Status']=='Enabled' and v.get('Filter',{}).get('Prefix')==PREFIX and v.get('Expiration',{}).get('Days')==7 for v in route['lifecycle']['Rules']),'SEVEN_DAY_EXPIRY')
        save('PRIVATE_ROUTE_RECEIPT.json',{'job':JOB,'status':'VERIFIED_EXISTING_PRIVATE_ROUTE_NO_ACTIVE_JOB_OR_MULTIPART','observed_utc':utc(),'bucket':BUCKET,'prefix':PREFIX,'region':REGION,'never_versioned':True,'expiry_days':7,'security_changes':False,'existing_authorized_route':True,'no_live_conflict':True,'no_multipart_uploads':True,'storage_route_created':False,'invoice_apis':'NOT_CALLED'})
        pricing=session.client('pricing',region_name='us-east-1',config=cfg)
        def products(service,fields):
            reply=pricing.get_products(ServiceCode=service,Filters=[{'Type':'TERM_MATCH','Field':k,'Value':v} for k,v in fields.items()],MaxResults=100)
            require(not reply.get('NextToken'),'PRICE_PAGINATION:'+service);rows=[]
            for raw in reply.get('PriceList',[]):
                j=json.loads(raw);rows.append({'sku':j['product']['sku'],'dimensions':[{'unit':d['unit'],'usd':d['pricePerUnit']['USD']} for term in j.get('terms',{}).get('OnDemand',{}).values() for d in term.get('priceDimensions',{}).values()]})
            return rows
        def top(name,rows,unit=None):
            values=[float(d['usd']) for j in rows for d in j['dimensions'] if unit is None or d['unit']==unit]
            require(values,'PRICE_MISSING:'+name);return max(values)
        compute=products('AmazonEC2',{'regionCode':REGION,'instanceType':INSTANCE_TYPE,'operatingSystem':'Linux','tenancy':'Shared','preInstalledSw':'NA','capacitystatus':'Used'})
        hourly=top('compute',compute,'Hrs');require(hourly<=1.22,'LINUX_PRICE_BOUND')
        queries={'gp3':('AmazonEC2',{'usagetype':'USW2-EBS:VolumeUsage.gp3'}),'ipv4':('AmazonVPC',{'usagetype':'USW2-PublicIPv4:InUseAddress'}),'s3storage':('AmazonS3',{'usagetype':'USW2-TimedStorage-ByteHrs','storageClass':'General Purpose'}),'s3put':('AmazonS3',{'usagetype':'USW2-Requests-Tier1'}),'s3get':('AmazonS3',{'usagetype':'USW2-Requests-Tier2'}),'transferout':('AWSDataTransfer',{'fromLocation':'US West (Oregon)','toLocation':'External','transferType':'AWS Outbound'})}
        quotes={name:products(service,fields) for name,(service,fields) in queries.items()}
        save('STORAGE_NETWORK_LIVE_PRICES.json',{'job':JOB,'utc':utc(),'actions':'PRICING_READ_ONLY','invoice_apis':'NOT_CALLED','status':'COMPLETE','compute':compute,'queries':quotes})
        rate={name:top(name,rows) for name,rows in quotes.items()}
        b=COST_BOUNDS;hours=b['hard_hours']
        components={'compute':hourly*hours,'root_disk':b['root_gib']/672*hours*rate['gp3'],'ipv4':hours*rate['ipv4'],'s3_storage':b['storage_decimal_gb']*b['storage_days']/28*rate['s3storage'],
            'requests':b['tier1_requests']*rate['s3put']+b['tier2_requests']*rate['s3get'],'network':b['network_decimal_gb']*rate['transferout'],'tax_adjustment_contingency':b['tax_adjustment_contingency_usd']}
        total=sum(components.values());require(total<=CAP_USD,'ALL_SERVICES_CAP')
        save('FRESH_PRICE_RECEIPT.json',{'job':JOB,'utc':utc(),'observed_unix':time.time(),'linux_hourly_usd':hourly,'projected_all_in_usd':total,'components':components,'rates':rate,'credits_assumed':False,'actual_bill':'PENDING','hard_minutes':HARD_MINUTES,'maximum_all_services_usd':CAP_USD,'cost_bounds':dict(b),'tax_contingency_not_invoice_guarantee':True,'storage_network_receipt_sha256':sha(ROOT/'STORAGE_NETWORK_LIVE_PRICES.json')})
        r.update(status='READ_ONLY_READY',projected_all_in_usd=total,hourly_usd=hourly)
    except Exception as exc:
        response=getattr(exc,'response',None) or {}
        r.update(status='FAILED_NO_BYPASS',error_type=type(exc).__name__,aws_code=response.get('Error',{}).get('Code'),reason=str(exc)[:500] if isinstance(exc,(RuntimeError,KeyError)) else 'Request arguments omitted')
    save('READINESS_RECEIPT.json',r)
    print(json.dumps({k:r.get(k) for k in ('status','reason','aws_code','projected_all_in_usd','hourly_usd','s3_read_requests','prior_slot_job','ledger_unreserved_cents')}),flush=True)
    return 0 if r['status']=='READ_ONLY_READY' else 2
def hashes():
    """Laptop only. No AWS call. Writes nothing. Prints the hashes and sizes the operator copies into AUTHORITY_B1.json."""
    rows={'controller_review':ROOT/'INDEPENDENT_REVIEW.json','source_pins':ROOT/'SOURCE_PINS.json','private_route_receipt':ROOT/'PRIVATE_ROUTE_RECEIPT.json','fresh_price_receipt':ROOT/'FRESH_PRICE_RECEIPT.json','prior_cleanup_receipt':ROOT/'PRIOR_INDEPENDENT_CLEANUP.json',
        'payload_manifest':ROOT/'CONTRACT.json','input_zip':ROOT/'input.zip','exclusive_lease':HOP/LEASE_NAME,'ledger_pointer':LEDGER_POINTER,'seal_file':CAS/'optionb'/'SEAL_OPTIONB.jsonl','precheck_receipt':ROOT/'PRECHECK_RECEIPT.json','owner_status_table':CAS/STATUS_TABLE}
    out={name:({'path':str(path),'sha256':sha(path),'bytes':path.stat().st_size} if path.is_file() else {'path':str(path),'missing':True}) for name,path in rows.items()}
    if LEDGER_POINTER.is_file():
        p=json.loads(LEDGER_POINTER.read_text(encoding='utf-8-sig'));free=cents(p['ceiling_usd'])-cents(p['combined_allocation_usd'])
        out['ledger_reading']={'combined_allocation_usd':p['combined_allocation_usd'],'ceiling_usd':p['ceiling_usd'],'unreserved_usd':free/100,'unreserved_after_hold_usd':(free-cents(CAP_USD))/100,'last_jobs':p.get('last_jobs'),'cap_fits':free>=cents(CAP_USD)}
    print(json.dumps(out,indent=1),flush=True)
def main():
    mode=sys.argv[1];require(mode in ('readiness','hashes','launch','cleanup'),'EXPLICIT_MODE')
    if mode=='readiness':sys.exit(readiness())
    elif mode=='hashes':hashes()
    elif mode=='launch':launch()
    else:
        ec,_,_,t=clients();cleanup(ec,t,read('LAUNCH_INTENT.json'))
if __name__=='__main__':main()
