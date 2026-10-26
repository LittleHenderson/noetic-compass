"""Fresh read-only OP11 closure checks; no launch, termination or object writes."""
import sys
from controller_common import *
def main():
    ec,_,_,t=clients();intent=read('LAUNCH_INTENT.json');i=discover(ec,intent);volumes=scoped_volumes(ec)
    os.environ['OP11_CONTROL_DEADLINE_UNIX']=str(intent['termination_unix'])
    listed=t.list_objects_v2(Bucket=BUCKET,Prefix=PREFIX,MaxKeys=10)
    require(not listed.get('IsTruncated'),'OBJECT_CLOSURE_TRUNCATED')
    objects=listed.get('Contents',[])
    mp=t.call('list_multipart_uploads',Prefix=PREFIX,MaxUploads=10)
    require(not mp.get('IsTruncated'),'MULTIPART_CLOSURE_TRUNCATED')
    uploads=mp.get('Uploads',[])
    preserved=False
    if (ROOT/'DOWNLOAD.json').exists():
        d=read('DOWNLOAD.json');actual=sha(ROOT/'deliverable.zip');preserved=d['transport_complete'] is True and actual==d['sha256']
        require(actual==read('ARTIFACT_REOPEN_VERIFICATION.json')['archive_sha256'],'REOPEN_PIN')
    complete=preserved and read('DOWNLOAD.json')['complete_required_evidence'] is True
    host_ok=bool(i and i['State']['Name']=='terminated')
    no_host_before_ec2=not i and not (ROOT/'EC2_LAUNCH_ATTEMPT.json').exists()
    cloud_ok=(host_ok or no_host_before_ec2) and not volumes and not objects and not uploads
    status=('VERIFIED_COMPLETE' if complete else 'CLOUD_CLEANUP_VERIFIED_EVIDENCE_INCOMPLETE') if cloud_ok else 'NOT_VERIFIED_COMPLETE'
    save('INDEPENDENT_CLEANUP.json',{'job':JOB,'utc':utc(),'status':status,'observation_after_original_deadline':time.time()>intent['termination_unix'],'instance':i['InstanceId'] if i else None,'host_state':i['State']['Name'] if i else None,'no_paid_host_attempted':no_host_before_ec2,'volumes':[v['VolumeId'] for v in volumes],'remaining_keys':[v['Key'] for v in objects],'multipart_uploads':[{'key':v['Key'],'upload_id':v['UploadId']} for v in uploads],'local_artifact_preserved':preserved,'complete_required_evidence':complete,'billing':'PENDING_ALL_HOLDS_RETAINED'})
    return 0 if cloud_ok else 2
if __name__=='__main__':sys.exit(main())
