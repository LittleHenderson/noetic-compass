"""Read-only ledger/source/provider audit. Never launches, reserves, or loads models."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import importlib.abc, json, sys
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent
HOME=OUT.parents[2]
ROOT=HOME/'research/CAS_META_2_COMPOSITION'
sys.path.insert(0,str(ROOT))
class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'torch','numpy','cas_cjt','casformer','transformers','safetensors'}:
            raise RuntimeError('AUDIT_MODEL_IMPORT_FORBIDDEN:'+fullname)
sys.meta_path.insert(0,Deny())
from aws import budget, graph_training_curriculum_launch as shared
from aws import graph_training_candidate_launch as lifecycle
def now():return datetime.now(timezone.utc).isoformat()
def pin(p):
    p=Path(p);raw=p.read_bytes();return {'path':str(p),'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
def write(name,value):
    with (OUT/name).open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2,sort_keys=True,default=str);f.write('\n')
    print(name,sha256((OUT/name).read_bytes()).hexdigest(),flush=True)
terminal=json.loads((ROOT/'records/ordered_encoder_001/budget_terminal.json').read_bytes())
canonical=Path(terminal['canonical_spending_ledger'])
ledger,lock,history=budget.paths(canonical)
assert not lock.exists(),'CANONICAL_LEDGER_LOCK_PRESENT'
before=pin(ledger);hist_before=[pin(p) for p in sorted(history.iterdir())]
# read_locked itself performs only reads. No lock file is created by this audit.
# Check for concurrent changes around the full history validation.
state=budget.read_locked(ledger,history)
hist_after=[pin(p) for p in sorted(history.iterdir())];after=pin(ledger)
assert before==after and hist_before==hist_after and not lock.exists(),'LEDGER_CHANGED_DURING_READ'
local_ledger=ROOT/'records/budget/campaign_ledger.json'
bound={k:{'path':v['path'],'sha256':v['sha256'],'verified_actual_sha256':sha256(Path(v['path']).read_bytes()).hexdigest()} for k,v in state.items() if k in ('predecessor','approval','amendment')}
write('budget.json',{'schema':'cas.learning-smoke-budget-readonly/0.1','observed_utc':now(),
 'canonical_ledger':before,'publication_copy':pin(local_ledger),'publication_copy_matches_canonical':local_ledger.read_bytes()==ledger.read_bytes(),
 'history_count':len(hist_before),'history_pins':hist_before,'revision':state['revision'],'reservations':len(state['reservations']),
 'owner_task_cap_usd':state['owner_task_cap_usd'],'total_reserved_usd':state['total_reserved_usd'],
 'remaining_unreserved_usd':state['remaining_unreserved_usd'],'last_reservations':state['reservations'][-4:],
 'authorization_bindings':bound,'read_locked_passed':True,'stable_before_after':True,'lock_files_created':0,
 'reservations_created':0,'refunds':0,'scope':'Validated stable read without acquiring a mutable lock; launch must revalidate atomically through the canonical budget wrapper. Internal reservation bounds, not an invoice.'})
prereqs=[]
for rel,expected in shared.WHEELS.items():
    p=HOME/rel; row={'relative_path':rel,'expected_sha256':expected,'exists':p.is_file()}
    if p.is_file():row.update(pin(p));row['matches_expected']=row['sha256']==expected
    prereqs.append(row)
source_paths=['aws/budget.py','aws/graph_training_curriculum_launch.py','aws/graph_training_candidate_launch.py','aws/ordered_encoder_launch.py','aws/graph6_contrast_launch.py','aws/run_evidence.py','requirements-gpu.txt']
source=[pin(ROOT/r) for r in source_paths]
raw_neural=HOME/'research/CAS_CJT_TRANSFORMER_v0_2/cas_cjt/neural.py'
write('local.json',{'schema':'cas.learning-smoke-local-prerequisites/0.1','observed_utc':now(),'resource_plan':shared.RESOURCE_PLAN,
 'wheel_prerequisites':prereqs,'raw_neural_source':pin(raw_neural) if raw_neural.is_file() else {'path':str(raw_neural),'exists':False},
 'source_pins':source,'previous_authority':pin(ROOT/'records/ordered_encoder_001/OWNER_AUTHORIZATION_001.json'),
 'reuse':'CandidateProvider lifecycle and shared committed-member packaging/evidence transport. OrderedEncoderProvider is zero-update-only and must not be reused as training authorization.',
 'new_request_or_reservation_written':False})
import boto3
from botocore.config import Config
config=Config(connect_timeout=5,read_timeout=10,retries={'max_attempts':0})
session=boto3.Session(profile_name='default',region_name='us-west-2')
clients={n:session.client(n,config=config,region_name='us-east-1' if n=='pricing' else 'us-west-2') for n in ('sts','ec2','pricing','iam','scheduler','service-quotas')}
identity=clients['sts'].get_caller_identity();assert identity['Account']=='807562639912','AWS_ACCOUNT_MISMATCH'
observations={'schema':'cas.learning-smoke-provider-readonly/0.1','observed_start_utc':now(),'account':identity['Account'],'region':'us-west-2','profile':'default',
 'identity_http_status':identity.get('ResponseMetadata',{}).get('HTTPStatusCode'),'identity_request_id':identity.get('ResponseMetadata',{}).get('RequestId'),
 'calls':{},'mutations':0,'capacity_claim':'Instance-type offering and quota are not a capacity guarantee; no RunInstances or dry-run was called.'}
ec2=clients['ec2'];oldjob='cas-meta2-orderedencoder-20260916064137-e47349be'
pricefilters={'instanceType':'g7.2xlarge','location':'US West (Oregon)','operatingSystem':'Linux','tenancy':'Shared','preInstalledSw':'NA','capacitystatus':'Used','marketoption':'OnDemand','operation':'RunInstances'}
calls={
 'active_tagged':('ec2.describe_instances',lambda:ec2.describe_instances(Filters=[{'Name':'tag-key','Values':['cas_meta_job']},{'Name':'instance-state-name','Values':['pending','running','stopping','stopped','shutting-down']}]),lambda d:{'instances':[{'id':i['InstanceId'],'state':i['State']['Name'],'type':i['InstanceType'],'launch_time':i.get('LaunchTime'),'job':[t['Value'] for t in i.get('Tags',[]) if t['Key']=='cas_meta_job']} for r in d.get('Reservations',[]) for i in r.get('Instances',[])],'next_token':d.get('NextToken')}),
 'active_all':('ec2.describe_instances',lambda:ec2.describe_instances(Filters=[{'Name':'instance-state-name','Values':['pending','running','stopping','shutting-down']}]),lambda d:{'instances':[{'id':i['InstanceId'],'state':i['State']['Name'],'type':i['InstanceType'],'job':[t['Value'] for t in i.get('Tags',[]) if t['Key']=='cas_meta_job']} for r in d.get('Reservations',[]) for i in r.get('Instances',[])],'next_token':d.get('NextToken')}),
 'previous_instance':('ec2.describe_instances',lambda:ec2.describe_instances(InstanceIds=['i-06659e476be997d48']),lambda d:{'instances':[{'id':i['InstanceId'],'state':i['State']['Name'],'type':i['InstanceType'],'transition':i.get('StateTransitionReason')} for r in d.get('Reservations',[]) for i in r.get('Instances',[])]}),
 'ami':('ec2.describe_images',lambda:ec2.describe_images(ImageIds=['ami-0fbbd0facbc9e3cff']),lambda d:{'images':[{k:i.get(k) for k in ('ImageId','Name','State','Architecture','CreationDate','OwnerId')} for i in d.get('Images',[])]}),
 'instance_type':('ec2.describe_instance_types',lambda:ec2.describe_instance_types(InstanceTypes=['g7.2xlarge']),lambda d:{'types':[{k:i.get(k) for k in ('InstanceType','GpuInfo','VCpuInfo','MemoryInfo','ProcessorInfo')} for i in d.get('InstanceTypes',[])]}),
 'pricing':('pricing.get_products',lambda:clients['pricing'].get_products(ServiceCode='AmazonEC2',Filters=[{'Type':'TERM_MATCH','Field':k,'Value':v} for k,v in pricefilters.items()]),lambda d:{'products':[json.loads(x) for x in d.get('PriceList',[])],'next_token':d.get('NextToken')}),
 'offerings':('ec2.describe_instance_type_offerings',lambda:ec2.describe_instance_type_offerings(LocationType='availability-zone',Filters=[{'Name':'instance-type','Values':['g7.2xlarge']}]),lambda d:{'offerings':d.get('InstanceTypeOfferings',[]),'next_token':d.get('NextToken')}),
 'default_subnets':('ec2.describe_subnets',lambda:ec2.describe_subnets(Filters=[{'Name':'default-for-az','Values':['true']}]),lambda d:{'subnets':[{k:s.get(k) for k in ('SubnetId','VpcId','AvailabilityZone','State','AvailableIpAddressCount','MapPublicIpOnLaunch')} for s in d.get('Subnets',[])],'next_token':d.get('NextToken')}),
 'old_security_group':('ec2.describe_security_groups',lambda:ec2.describe_security_groups(Filters=[{'Name':'group-name','Values':[oldjob]}]),lambda d:{'groups':[{'id':s['GroupId'],'name':s['GroupName']} for s in d.get('SecurityGroups',[])]}),
 'old_worker_role':('iam.get_role',lambda:clients['iam'].get_role(RoleName=oldjob+'-worker'),lambda d:{'name':d.get('Role',{}).get('RoleName')}),
 'old_instance_profile':('iam.get_instance_profile',lambda:clients['iam'].get_instance_profile(InstanceProfileName=oldjob+'-worker'),lambda d:{'name':d.get('InstanceProfile',{}).get('InstanceProfileName')}),
 'old_schedule':('scheduler.get_schedule',lambda:clients['scheduler'].get_schedule(Name=oldjob,GroupName='default'),lambda d:{'name':d.get('Name'),'state':d.get('State')}),
}
def run_call(name,parts):
    api,fn,project=parts;record={'api':api,'queried_utc':now()}
    try:
        data=fn();meta=data.get('ResponseMetadata',{});record.update({'http_status':meta.get('HTTPStatusCode'),'request_id':meta.get('RequestId'),'observed':project(data)})
    except Exception as e:
        data=getattr(e,'response',{});meta=data.get('ResponseMetadata',{});record.update({'http_status':meta.get('HTTPStatusCode'),'request_id':meta.get('RequestId'),'error_type':type(e).__name__,'error_code':data.get('Error',{}).get('Code')})
    return name,record
with ThreadPoolExecutor(max_workers=6) as pool:
    futures=[pool.submit(run_call,n,c) for n,c in calls.items()]
    for f in as_completed(futures):
        n,r=f.result();observations['calls'][n]=r;print('read',n,r.get('http_status'),r.get('error_code'),flush=True)
# Quotas are paginated; retain only relevant GPU quotas, never credentials.
qrows=[];token=None;qmeta=[]
while True:
    try:
        data=clients['service-quotas'].list_service_quotas(ServiceCode='ec2',**({'NextToken':token} if token else {}))
        qmeta.append({k:data.get('ResponseMetadata',{}).get(k) for k in ('RequestId','HTTPStatusCode')})
        for q in data.get('Quotas',[]):
            if ('On-Demand' in q.get('QuotaName','') and (' G ' in q['QuotaName'] or 'G and VT' in q['QuotaName'])):
                qrows.append({k:q.get(k) for k in ('QuotaCode','QuotaName','Value','Unit','Adjustable')})
        token=data.get('NextToken')
        if not token:break
    except Exception as e:
        observations['quota_error']={'type':type(e).__name__,'code':getattr(e,'response',{}).get('Error',{}).get('Code')};break
observations['gpu_quotas']={'rows':qrows,'pages':qmeta}
observations['observed_end_utc']=now();write('provider.json',observations)
assert pin(ledger)==before,'CANONICAL_LEDGER_CHANGED_AFTER_PROVIDER_AUDIT'
write('finish.json',{'observed_utc':now(),'canonical_ledger_unchanged':True,'script':pin(__file__),'new_reservations':0,'provider_mutations':0,'model_loads':0})
