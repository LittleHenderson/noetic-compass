"""Read only this study's lifecycle files, EC2 states and newest progress record."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'research/CAS_META_2_COMPOSITION')]
from aws import typed_matched_launch as launch

def observe():
    study=json.loads((ROOT/'records/typed_matched_001/admission_001/study.json').read_bytes())
    clients=launch.lifecycle._clients('default')
    observations=[]
    for job in study['jobs']:
        receipt=Path(job['receipt_dir'])
        row={'job':job['job'],'condition':job['condition'],'model_seed':job['model_seed']}
        if (receipt/'result.json').is_file():
            result=json.loads((receipt/'result.json').read_bytes())
            row.update(status=result['status'],completed_deliverable=result['completed_deliverable'],cleanup_complete=result['cleanup']['complete'])
            analysis=receipt/'matched_analysis.json'
            if analysis.is_file():
                values=json.loads(analysis.read_bytes()); row.update(speed_auc=values['speed_auc'],transfer=values['transfer'],retention_status=values['retention']['status'])
        elif receipt.is_dir():
            row['status']='PROVIDER_LIFECYCLE_IN_PROGRESS'
            if (receipt/'launch.json').is_file():
                launched=json.loads((receipt/'launch.json').read_bytes()); row['launch']=launched
            instances=clients['ec2'].describe_instances(Filters=[{'Name':'tag:cas_meta_job','Values':[job['job']]}])
            row['instances']=[{'instance_id':v['InstanceId'],'state':v['State']['Name']} for r in instances.get('Reservations',[]) for v in r.get('Instances',[])]
            bucket=json.loads(Path(job['authority']['path']).read_bytes())['worker_config']['bucket']
            keys=[]
            try:
                for page in clients['s3'].get_paginator('list_objects_v2').paginate(Bucket=bucket,Prefix='results/evidence/typed_progress_',ExpectedBucketOwner='807562639912'):
                    keys.extend(v['Key'] for v in page.get('Contents',[]))
                if keys:
                    key=max(keys); obj=clients['s3'].get_object(Bucket=bucket,Key=key,ExpectedBucketOwner='807562639912')
                    raw=obj['Body'].read(65537); assert len(raw)<=65536
                    row['latest_progress']=json.loads(raw)
            except launch.lifecycle._client_error() as error:
                row['progress_read_error']=error.response.get('Error',{}).get('Code')
        else: row['status']='NOT_STARTED'
        observations.append(row)
    result={'observed_utc':datetime.now(timezone.utc).isoformat(),'provider_mutations':0,'jobs':observations}
    directory=ROOT/'records/typed_matched_001/live_observations'; directory.mkdir(exist_ok=True)
    path=directory/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%f')+'.json')
    path.open('xb').write(launch.canonical(result))
    print(json.dumps(result),flush=True)

if __name__=='__main__': observe()
