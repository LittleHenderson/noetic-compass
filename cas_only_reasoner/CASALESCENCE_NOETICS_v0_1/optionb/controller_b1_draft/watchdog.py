"""Option B GPU job b1. Separate fail-safe AWS controller process; observes immutable intent. Never run."""
import os,time
from controller_common import *
# b1 clock, seconds after launch: forced shutdown 10500 and hard limit 10800, as in aws_control.py and the guest.
require(CLOCK_SECONDS[2:]==[10500,10800],'CLOCK_CONTRACT')
def main():
    ec,_,_,_=clients();start=time.time();intent=None;instance=None;failures=0
    require(not (ROOT/'LAUNCH_INTENT.json').exists(),'WATCH_MUST_START_BEFORE_INTENT')
    while time.time()-start<900:
        save('WATCH.json',{'job':JOB,'status':'READY','heartbeat_unix':time.time(),'pid':os.getpid()})
        if (ROOT/'LAUNCH_INTENT.json').exists():intent=read('LAUNCH_INTENT.json');break
        time.sleep(5)
    require(intent is not None and intent['job']==JOB,'WATCH_READY_WINDOW_EXPIRED')
    intent_hash=sha(ROOT/'LAUNCH_INTENT.json');deadline=intent['termination_unix']
    require(deadline==intent['launch_unix']+10800 and intent['force_cutoff_unix']==intent['launch_unix']+10500,'DEADLINE_SCOPE')
    while time.time()<deadline:
        try:
            require(sha(ROOT/'LAUNCH_INTENT.json')==intent_hash,'INTENT_MUTATED')
            i=discover(ec,intent)
            if i:
                instance=i['InstanceId']
                if time.time()>=intent['force_cutoff_unix'] and i['State']['Name']!='terminated':terminate(ec,instance)
                for v in scoped_volumes(ec):
                    require(v['VolumeType']=='gp3' and v['Size']==100,'VOLUME_SCOPE')
                    if v['State']=='available':ec.delete_volume(VolumeId=v['VolumeId'])
                status='ARMED' if i['State']['Name']!='terminated' else 'TERMINATED'
                save('WATCH.json',{'job':JOB,'instance':instance,'status':status,'pid':os.getpid(),'heartbeat_unix':time.time(),'intent_sha256':intent_hash,'force_cutoff_unix':intent['force_cutoff_unix'],'termination_unix':deadline})
                if status=='TERMINATED' and not scoped_volumes(ec):return
            else:save('WATCH.json',{'job':JOB,'status':'DISCOVERING_SCOPED_LAUNCH','pid':os.getpid(),'heartbeat_unix':time.time(),'intent_sha256':intent_hash})
        except Exception as e:
            preserve_error('independent_watch',e);failures+=1
            # C1: the host shuts itself down at the original cutoff whatever happens here. Emergency
            # termination now needs the cutoff, a changed intent, or twelve failed observations in a row.
            if instance and (time.time()>=intent['force_cutoff_unix'] or failures>=12 or str(e)=='INTENT_MUTATED'):
                try:terminate(ec,instance)
                except Exception as x:preserve_error('watch_emergency_terminate',x)
            elif instance:
                try:save('WATCH.json',{'job':JOB,'instance':instance,'status':'ARMED','pid':os.getpid(),'heartbeat_unix':time.time(),'intent_sha256':intent_hash,'force_cutoff_unix':intent['force_cutoff_unix'],'termination_unix':deadline,'failed_observations_in_a_row':failures})
                except Exception as x:preserve_error('watch_heartbeat_write',x)
        else:failures=0
        time.sleep(10)
    if instance:terminate(ec,instance)
    save('WATCH_END.json',{'job':JOB,'instance':instance,'utc':utc(),'status':'DEADLINE_REACHED_VERIFY_CLEANUP_REQUIRED'})
if __name__=='__main__':main()
