"""Read-only monitoring for the one caller-bound typed-course job."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import json,re
import boto3
from botocore.config import Config

base=Path(__file__).resolve().parent
launch=json.loads((base/'receipt_001/launch.json').read_bytes())
job,iid,bucket=launch['job'],launch['instance_id'],launch['bucket']
assert job=='cas-meta2-typedcourse-20260917020901-85736789' and iid=='i-0b7a980f8110e686a'
now=datetime.now(timezone.utc)
out=base/('monitoring_'+now.strftime('%Y%m%dT%H%M%S%fZ'))
out.mkdir()
session=boto3.Session(profile_name='default',region_name='us-west-2')
config=Config(connect_timeout=5,read_timeout=10,retries={'max_attempts':0})
ec2=session.client('ec2',config=config)
s3=session.client('s3',config=config)
artifacts=[]
def save_raw(name,raw):
    with (out/name).open('xb') as f:f.write(raw)
    pin={'path':name,'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    artifacts.append(pin)
    return pin
def save(name,value):
    return save_raw(name,(json.dumps(value,sort_keys=True,separators=(',',':'),default=lambda v:v.isoformat() if hasattr(v,'isoformat') else str(v))+'\n').encode())
summary={'job':job,'instance_id':iid,'bucket':bucket,'observed_at_utc':now.isoformat(),'provider_mutations':0,'operations':[]}
def call(client,operation,**args):
    response=getattr(client,operation)(**args)
    summary['operations'].append({'operation':operation,'request_id':response.get('ResponseMetadata',{}).get('RequestId')})
    return response
try:
    r=call(ec2,'describe_instances',InstanceIds=[iid])
    values=[v for row in r['Reservations'] for v in row['Instances']]
    assert len(values)==1 and values[0]['InstanceId']==iid
    v=values[0]
    summary['instance_state']=v['State']['Name']
    save('instance.json',{k:v.get(k) for k in ['InstanceId','State','InstanceType','LaunchTime','ClientToken','Tags']})
except Exception as e:
    summary['instance_error']={'type':type(e).__name__,'message':str(e)[:500]}
try:
    r=call(s3,'list_objects_v2',Bucket=bucket,Prefix='results/',MaxKeys=1000)
    assert not r.get('IsTruncated'),'MONITOR_LIST_TRUNCATED'
    contents=r.get('Contents',[])
    save('objects.json',{'IsTruncated':False,'Contents':contents})
    keys=[v['Key'] for v in contents]
    updates=sorted(k for k in keys if re.fullmatch(r'results/artifacts/update_\d{3}\.json',k))
    batches=sorted(k for k in keys if re.fullmatch(r'results/artifacts/batch_\d{3}\.json',k))
    summary.update(result_object_count=len(keys),update_receipt_count=len(updates),batch_seal_count=len(batches),
       last_update=updates[-1] if updates else None,terminal_marker_present='results/result.json' in keys,
       evidence_keys=sorted(k for k in keys if k.startswith('results/evidence/')),
       checkpoint_keys=sorted(k for k in keys if k.endswith('.pt')))
    wanted=[]
    if updates:wanted.append(updates[-1])
    for key in ['results/result.json','results/failure.json','results/artifacts/worker_report.json']:
        if key in keys:wanted.append(key)
    for key in wanted:
        r=call(s3,'get_object',Bucket=bucket,Key=key)
        raw=r['Body'].read(1024*1024+1)
        assert len(raw)<=1024*1024,'MONITOR_OBJECT_BOUND'
        save_raw(key.replace('/','__'),raw)
        d=json.loads(raw)
        if key in updates:
            summary['latest_update']={k:d.get(k) for k in ['cursor_committed','model_revision','gradient_squared_norm','raw_batch_loss','counters']}
        else:
            summary[key]={k:d.get(k) for k in ['status','phase','failure','completed_main_updates','elapsed_seconds','summary']}
except Exception as e:
    summary['s3_error']={'type':type(e).__name__,'message':str(e)[:500]}
try:
    r=call(ec2,'get_console_output',InstanceId=iid,Latest=True)
    value=r.get('Output') or ''
    raw=value if isinstance(value,bytes) else value.encode('utf-8')
    save_raw('console_sdk_output.bin',raw)
    save_raw('console_decoded.log',raw)
    text=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]','',raw.decode('utf-8',errors='replace'))
    safe=[]
    for line in text.splitlines()[-12:]:
        if re.search(r'(?i)(authorization|access.?key|secret|token=|password|credential|X-Amz-|BEGIN .*PRIVATE KEY)',line):
            safe.append('[credential-related line withheld from chat]')
        else:safe.append(line[:700])
    summary.update(console_timestamp=r.get('Timestamp'),console_tail=safe,console_sha256=sha256(raw).hexdigest())
except Exception as e:
    summary['console_error']={'type':type(e).__name__,'message':str(e)[:500]}
summary['artifacts']=list(artifacts)
save('receipt.json',summary)
print(json.dumps({'path':str(out),'summary':{k:v for k,v in summary.items() if k not in ('artifacts','operations')}},default=str))
