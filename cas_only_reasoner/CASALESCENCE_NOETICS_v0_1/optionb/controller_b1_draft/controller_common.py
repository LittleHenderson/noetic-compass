"""Option B GPU job b1. AWS control only; no project imports. Derived from the op11 C1 controller. Never run."""
import datetime, hashlib, json, os, re, time
from pathlib import Path
import boto3
from botocore.config import Config
from bounded_s3 import BudgetedS3
ROOT=Path(__file__).resolve().parent
HOP=Path(r'C:\Users\wakil\Documents\Codex\2026-10-01\task-2\helm_operator_preparation')
CAS=Path(r'C:\Users\wakil\OneDrive\Desktop\tksCAS\cas_only_reasoner\CASALESCENCE_NOETICS_v0_1')
LEDGER_POINTER=Path(r'C:\Users\wakil\Documents\Codex\AWS_COMBINED_ALLOCATION_CURRENT.json')
OPERATOR='claude-code/claude-opus-5-5/session-d2ce92aa-19e8-4dac-8de6-1ffa8931b6b0'
OWNER_APPROVAL=CAS/'OWNER_APPROVAL_ALL_STAGES_20261005T0610Z.json'
OWNER_APPROVAL_SHA='d1c052f56b61a6f30a428d25b4530352d6cd6ddb489163734fe6ea6d23b24325'
OWNER_DIRECTION=CAS/'OWNER_DIRECTION_POINTING_AND_OPTION_B_20261005.json'
OWNER_DIRECTION_SHA='689f4b5622b0f28d60e0146e3b2e41d68c40f9eec7ddf42c06719c42d4f692fc'
JOB='cas-optionb-b1'
ACCOUNT='807562639912'; REGION='us-west-2'
AMI='ami-0dddfa1ffa6b87af7'; INSTANCE_TYPE='g5.2xlarge'
BUCKET='helm-primary-pointer-807562639912-20261001-v4'
PREFIX='bridge-control-20260822/helm-pointer-saturation-20261001-v4/'
KEYS=('input.zip','progress.json','transport-result.json','pointer-saturation-deliverable.zip')
# b1 limits (operator decision D8 and plan section 19). aws_control.py and watchdog.py carry the same four clock numbers as literals.
CAP_USD=5.00; HARD_MINUTES=180; MODEL_CALLS=5000
CLOCK_SECONDS=[1800,8100,10500,10800]
ARCHIVE_CAP_BYTES=100000000; INPUT_CAP_BYTES=1100000000
COST_BOUNDS={'network_decimal_gb':0.2,'storage_decimal_gb':1.2,'storage_days':8,'tier1_requests':2000,'tier2_requests':1000,'root_gib':100,'hard_hours':3,'tax_adjustment_contingency_usd':1.0}
LEASE_NAME='CAS_OPTIONB_B1_TRANSPORT_LEASE.json'
# These two files must stay byte-identical to the op11 C1 controller (reviewed and run on 2026-10-04).
IDENTICAL_SHA={'bounded_s3.py':'2582940278d720da833e3795d7678b4146046d4bb73deec1c76606f252fdee61','independent_cleanup.py':'4d0b816c14fd65dd8773976a42e0872168da03f73960d810b0a1f286bc5c51e5'}
REQUIRED_PINS={'controller_common.py','aws_control.py','bounded_s3.py','watchdog.py','independent_cleanup.py','worker_v02.py','CONTRACT.json','input.zip'}
SEAL_STEPS=('1_PLAN_AND_SOURCES','2_ROLE_NOTES','3A_PRACTICE_QUESTIONS_AND_KEYS','3B_PRACTICE_SET_FIXED','3C_FINAL_QUESTIONS_AND_KEYS','4_ORDINARY_NOTES','5_PROMPT_PARTS_AND_REMOVAL_LOG','6_PROGRAMS','7_PRECHECK')
# Review round 1 (plan section 11.1, FILE_FORMATS.md section 15.2): the two repair lines that may stand between the nine steps. Amendment A5 gave each a window; seal_gate checks both.
REPAIR_STEPS=('6R_PROGRAMS_REPAIRED','TR_TOOLS_REPAIRED'); MAX_PROGRAM_REPAIRS=2
STATUS_TABLE='optionb/OUTCOME_STATUS_TABLE.json'
def require(ok,why):
    if not ok: raise RuntimeError(why)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):
            require(time.time()<float(os.environ.get('OP11_CONTROL_DEADLINE_UNIX','inf')),'CONTROL_DEADLINE');h.update(b)
    return h.hexdigest()
def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8-sig'))
def save(name,value):
    p=ROOT/name;t=p.with_name(p.name+'.'+str(os.getpid())+'.tmp')
    with t.open('w',encoding='utf-8') as f:json.dump(value,f,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(t,p)
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def clients():
    cfg=Config(connect_timeout=8,read_timeout=30,retries={'total_max_attempts':1})
    # C1: the EC2 calls made here are read-only or idempotent (fixed ClientToken, terminate, delete), so they may retry.
    # SSM (one dispatch) and S3 (budgeted single requests) stay single-attempt.
    calm=Config(connect_timeout=8,read_timeout=30,retries={'total_max_attempts':4,'mode':'standard'})
    session=boto3.Session(profile_name='default',region_name=REGION)
    require(session.client('sts',config=calm).get_caller_identity()['Arn']==f'arn:aws:iam::{ACCOUNT}:user/cas-g5-operator','IDENTITY')
    ec=session.client('ec2',config=calm);ssm=session.client('ssm',config=cfg);raw=session.client('s3',config=cfg)
    return ec,ssm,raw,BudgetedS3(raw,ROOT,owner=ACCOUNT,bucket=BUCKET,prefix=PREFIX,region=REGION)
def cents(value):return int(round(float(value)*100))
def pinned(base,ref,why):
    # ref is {'path':..,'sha256':..}; the path is relative to base and may not leave it.
    p=(base/ref['path']).resolve();require(p.is_relative_to(base.resolve()) and p.is_file() and sha(p)==ref['sha256'],why);return p
def ledger_gate(a):
    """The shared ledger is read again at launch (decision D8). The cap must fit inside unreserved funds. Reads one local file."""
    m=a['ledger_reading'];raw=LEDGER_POINTER.read_bytes();p=json.loads(raw.decode('utf-8-sig'))
    require(hashlib.sha256(raw).hexdigest()==m['pointer_sha256'],'LEDGER_CHANGED_SINCE_THE_READING_READ_IT_AGAIN')
    free=cents(p['ceiling_usd'])-cents(p['combined_allocation_usd'])
    require(p['schema']=='helm.aws-combined-allocation.current/1' and cents(p['unreserved_usd'])==free,'LEDGER_POINTER_SHAPE')
    require(cents(m['combined_allocation_usd'])==cents(p['combined_allocation_usd']) and cents(m['ceiling_usd'])==cents(p['ceiling_usd']) and cents(m['unreserved_usd'])==free,'LEDGER_READING_MISMATCH')
    require(free>=cents(CAP_USD),'CAP_EXCEEDS_UNRESERVED_FUNDS')
    require(cents(a['new_hold_usd'])==cents(CAP_USD) and cents(a['unreserved_after_hold_usd'])==free-cents(CAP_USD),'ONE_NEW_HOLD_OF_THE_CAP')
    return p
def seal_gate(a,contract):
    """The seal chain must end with one passed pre-check of the same source.zip (decision D7), and the sealed plan and
    launch floor must agree with this controller. Reads local files only. Formats: optionb/FILE_FORMATS.md sections 11 and 15."""
    s=a['seal'];path=pinned(CAS,{'path':'optionb/SEAL_OPTIONB.jsonl','sha256':s['seal_file_sha256']},'SEAL_FILE_PIN')
    raw=path.read_bytes();require(raw.endswith(b'\n') and b'\r' not in raw,'SEAL_FILE_SHAPE')
    lines=raw[:-1].split(b'\n');rows=[json.loads(x.decode('utf-8')) for x in lines]
    require([r['n'] for r in rows]==list(range(1,len(rows)+1)),'SEAL_LINE_NUMBERS')
    require(all(r['schema']=='casalescence/optionb/seal-step/v1' and r['step'] in SEAL_STEPS+REPAIR_STEPS for r in rows),'SEAL_STEP_NAMES')
    require(rows[0]['step']==SEAL_STEPS[0] and rows[0]['previous_line_sha256'] is None,'SEAL_STARTS_WITH_THE_PLAN')
    for i in range(1,len(rows)):require(rows[i]['previous_line_sha256']==hashlib.sha256(lines[i-1]).hexdigest(),'SEAL_CHAIN_BROKEN')
    # Order rule of FILE_FORMATS.md 15.2: leave the repair lines out; what is left must be the nine steps, in order, each once.
    steps=[r['step'] for r in rows];require([x for x in steps if x not in REPAIR_STEPS]==list(SEAL_STEPS),'SEAL_STEP_ORDER')
    six=steps.index('6_PROGRAMS');seven=steps.index('7_PRECHECK');fixes=[i for i,x in enumerate(steps) if x==REPAIR_STEPS[0]]
    # A program repair stands after step 6 and before step 7, at most twice. So the passed pre-check is always later than the last program repair.
    require(len(fixes)<=MAX_PROGRAM_REPAIRS and all(six<i<seven for i in fixes),'SEAL_PROGRAM_REPAIR_LINES_OUT_OF_PLACE')
    # Amendment A5: a tool repair is allowed only while no final question exists. So a tool-repair line stands after line 1 and before the line 3C.
    final=steps.index('3C_FINAL_QUESTIONS_AND_KEYS');require(all(0<i<final for i,x in enumerate(steps) if x==REPAIR_STEPS[1]),'SEAL_TOOL_REPAIR_LINE_OUTSIDE_ITS_WINDOW')
    # So nothing can follow the pre-check line: it is the last line of the seal file.
    require(seven==len(steps)-1,'SEAL_MUST_END_WITH_ONE_PRECHECK')
    last=rows[seven];v=last['values']
    require(v['selftest_status']=='SELFTEST_PASS','PRECHECK_DID_NOT_PASS')
    require(v['source_zip_sha256']==s['source_zip_sha256']==contract['source']['zip_sha256'],'PRECHECK_AND_GPU_JOB_MUST_USE_THE_SAME_SOURCE_ZIP')
    for name in ('prompt_list_sha256','padding_plan_sha256','selftest_json_sha256'):
        require(isinstance(v[name],str) and re.fullmatch(r'[0-9a-f]{64}',v[name]) is not None and v[name]==s['precheck'][name],'PRECHECK_HASH:'+name)
    # Review round 1 (plan section 19.1): a rehearsal or a test on made-up data is never the sealed pre-check. The receipt of the
    # pre-check job, copied unchanged out of its result archive, must show a passed job on the sealed package with these five values.
    receipt=json.loads(pinned(ROOT,s['precheck_receipt'],'PRECHECK_RECEIPT_PIN').read_text(encoding='utf-8-sig'))
    require(receipt.get('precheck_kind')=='SEALED_PACKAGE' and receipt.get('status')=='PRECHECK_COMPLETE_SELFTEST_PASS' and re.fullmatch(r'cas-optionb-b1-precheck-p[1-4]',str(receipt.get('job'))) is not None
        and receipt.get('seal_step_7_values')=={k:v[k] for k in ('source_zip_sha256','selftest_status','prompt_list_sha256','padding_plan_sha256','selftest_json_sha256')},'SEALED_PRECHECK_IS_NOT_A_PASSED_JOB_ON_THE_SEALED_PACKAGE')
    # The guest hands these two values to Gate 0 from CONTRACT.json. A contract with other values would spend the attempt.
    for name in ('prompt_list_sha256','padding_plan_sha256'):require(contract['precheck'][name]==v[name],'CONTRACT_PRECHECK_BINDING:'+name)
    # The hash in force (FILE_FORMATS.md 15.2): for a path that more than one line lists, the latest line counts.
    sealed={f['path']:f['sha256'] for r in rows for f in r['files']}
    require('optionb/PLAN_CONSTANTS.json' in sealed and 'optionb/removal_log.json' in sealed,'PLAN_OR_REMOVAL_LOG_NOT_SEALED')
    # Plan sections 15.4 and 21 (review round 1): the owner's table of status words is sealed in step 7, before any result exists.
    pinned(CAS,{'path':STATUS_TABLE,'sha256':{f['path']:f['sha256'] for f in last['files']}.get(STATUS_TABLE)},'OWNER_STATUS_TABLE_NOT_SEALED_IN_STEP_7_OR_CHANGED')
    plan=json.loads(pinned(CAS,{'path':'optionb/PLAN_CONSTANTS.json','sha256':sealed['optionb/PLAN_CONSTANTS.json']},'PLAN_CONSTANTS_CHANGED_AFTER_SEAL').read_text(encoding='utf-8'))
    g=plan['aws']['gpu_job']
    require(cents(g['cap_usd'])==cents(CAP_USD) and g['hard_time_limit_minutes']==HARD_MINUTES and g['attempts']==1 and g['call_cap']==MODEL_CALLS and g['archive_cap_bytes']==ARCHIVE_CAP_BYTES and g['image']==AMI and g['instance'].startswith(INSTANCE_TYPE)
        and [g['clock_seconds'][k] for k in ('setup_must_end','work_cutoff','forced_shutdown','hard_limit')]==CLOCK_SECONDS,'CONTROLLER_AND_SEALED_PLAN_DISAGREE')
    removal=json.loads(pinned(CAS,{'path':'optionb/removal_log.json','sha256':sealed['optionb/removal_log.json']},'REMOVAL_LOG_CHANGED_AFTER_SEAL').read_text(encoding='utf-8'))
    floor=plan['launch_floor'];counts=removal['final_counts']
    require(removal['launch_floor_met'] is True and removal['tier'] in ('AS_IT_STANDS','EXPLORATORY'),'LAUNCH_FLOOR_NOT_MET')
    require(counts['final_role_step_tasks']>=floor['final_role_step_tasks_min'] and counts['final_plain_fact_tasks']>=floor['final_plain_fact_tasks_min']
        and counts['practice_role_step_tasks']>=floor['practice_role_step_tasks_min'] and counts['practice_plain_fact_tasks']>=floor['practice_plain_fact_tasks_min'],'LAUNCH_FLOOR_NUMBERS')
def authority():
    a=read('AUTHORITY_B1.json')
    require(a['schema']=='cas.optionb.b1.authority/1' and a['status']=='ADMITTED' and a['job']==JOB and a['execution_owner']==OPERATOR,'SOLE_OPERATOR')
    require(a['owner_approval']=={'path':OWNER_APPROVAL.name,'sha256':OWNER_APPROVAL_SHA} and sha(OWNER_APPROVAL)==OWNER_APPROVAL_SHA,'OWNER_STANDING_APPROVAL')
    require(a['owner_direction']=={'path':OWNER_DIRECTION.name,'sha256':OWNER_DIRECTION_SHA} and sha(OWNER_DIRECTION)==OWNER_DIRECTION_SHA,'OWNER_OPTION_B_DIRECTION')
    # Plan section 22, questions 12 and 13: the GPU job waits for one yes from the owner after the real counts are shown.
    go=json.loads(pinned(CAS,a['owner_go_record'],'OWNER_GO_RECORD_PIN').read_text(encoding='utf-8-sig'))
    require(go.get('applies_to_job')==JOB and go.get('decision')=='GO' and isinstance(go.get('owner_words_verbatim'),str) and go['owner_words_verbatim'].strip()!=''
        and cents(go.get('cap_usd',0))==cents(CAP_USD) and go.get('hard_minutes')==HARD_MINUTES,'OWNER_GO_FOR_THIS_JOB')
    require(cents(a['cap_usd'])==cents(CAP_USD) and a['hard_minutes']==HARD_MINUTES and a['clock_seconds']==CLOCK_SECONDS and a['model_calls_cap']==MODEL_CALLS and a['archive_cap_bytes']==ARCHIVE_CAP_BYTES
        and a['os']=='Linux' and a['paid_attempts_allowed']==1 and a['automatic_retry'] is False and a['new_installs_allowed']=='GUEST_ISOLATED_OVERLAY_OF_ACCEPTED_REQUIREMENTS_ONLY','APPROVED_SCOPE')
    pointer=ledger_gate(a)
    for name,expected in IDENTICAL_SHA.items():require(sha(ROOT/name)==expected,'MUST_STAY_BYTE_IDENTICAL:'+name)
    lease_path=HOP/LEASE_NAME
    require(sha(lease_path)==a['exclusive_lease_sha256'],'LEASE_PIN')
    lease=json.loads(lease_path.read_text(encoding='utf-8-sig'))
    require(lease['status']=='ADMITTED_EXCLUSIVE' and lease['job']==JOB and lease['execution_owner']==a['execution_owner']==OPERATOR and lease['bucket']==BUCKET and lease['prefix']==PREFIX and lease['unique_local_output_prefix']==str(ROOT),'EXCLUSIVE_LEASE')
    for ref in ('controller_review','source_pins','private_route_receipt','fresh_price_receipt','prior_cleanup_receipt'):
        v=a[ref];p=(ROOT/v['path']).resolve();require(p.is_relative_to(ROOT) and sha(p)==v['sha256'],'AUTHORITY_PIN:'+ref)
    # The gate is not loosened: same form and same fields as before. The job name now comes from the authority record
    # and must be the last job the shared ledger carries, so the record is for the most recent job on the storage slot.
    prior=read(a['prior_cleanup_receipt']['path']);require(prior['job']==a['prior_slot_job']!=JOB and prior['schema']=='pointer.saturation.independent-cleanup/1' and prior['bucket']==BUCKET and prior['prefix']==PREFIX and prior['status']=='VERIFIED' and prior['cleanup_verified'] is True and prior['compute_cleanup_verified'] is True and prior['prefix_cleanup_verified'] is True and prior['instance_state']=='terminated' and not prior['active_own_job_instances'] and not prior['prefix_versions_remaining'],'PRIOR_SERIAL_CLEANUP')
    require(pointer.get('last_jobs')==[prior['job']],'PRIOR_CLEANUP_IS_NOT_FOR_THE_LAST_JOB_ON_THE_LEDGER')
    review=read(a['controller_review']['path']);require(review['job']==JOB and review['decision']=='ACCEPT_SOURCE_PENDING_EXTERNAL_ADMISSION' and review['source_pins_sha256']==a['source_pins']['sha256'],'INDEPENDENT_CONTROL_REVIEW')
    pins=read(a['source_pins']['path']);require(pins['job']==JOB and REQUIRED_PINS<={v['path'] for v in pins['files']},'SOURCE_PINS_MUST_LIST_EVERY_PROGRAM')
    for v in pins['files']:
        p=(ROOT/v['path']).resolve();require(p.is_relative_to(ROOT) and sha(p)==v['sha256'],'SOURCE_CHANGED:'+v['path'])
    price=read(a['fresh_price_receipt']['path']);require(price['job']==JOB and 0<=time.time()-price['observed_unix']<=3600,'FRESH_PRICE')
    require(price['projected_all_in_usd']<=CAP_USD and price['linux_hourly_usd']<=1.22 and price['hard_minutes']==HARD_MINUTES,'ALL_SERVICES_CAP')
    require(price['cost_bounds']==COST_BOUNDS,'COST_BINDING')
    require(a['payload_manifest_sha256']==sha(ROOT/'CONTRACT.json'),'CONTRACT_PIN')
    require(a['input_zip_bytes']<=INPUT_CAP_BYTES and sha(ROOT/'input.zip')==a['input_zip_sha256'] and (ROOT/'input.zip').stat().st_size==a['input_zip_bytes'],'INPUT_PIN')
    route=read(a['private_route_receipt']['path']);require(route['job']==JOB and route['bucket']==BUCKET and route['prefix']==PREFIX and route['never_versioned'] is True and route['expiry_days']==7 and route['security_changes'] is False,'PRIVATE_ROUTE')
    contract=read('CONTRACT.json');require(contract['job']==JOB and contract['source']['manifest_sha256']==a['seal']['bundle_manifest_sha256'] and contract['limits']['model_calls']==MODEL_CALLS and contract['limits']['archive_bytes']==ARCHIVE_CAP_BYTES,'REVIEWED_PACKAGE_ONLY')
    seal_gate(a,contract)
    return a,price
def discover(ec,intent):
    response=ec.describe_instances(Filters=[{'Name':'tag:Name','Values':[JOB]},{'Name':'client-token','Values':[intent['client_token']]}])
    require(not response.get('NextToken'),'DISCOVERY_TRUNCATED')
    rows=[i for r in response['Reservations'] for i in r['Instances']];require(len(rows)<=1,'DUPLICATE_SCOPE')
    if not rows:return None
    i=rows[0];require(i['InstanceType']==INSTANCE_TYPE and i.get('Platform')!='windows' and i['ImageId']==AMI,'HOST_SCOPE');return i
def scoped_volumes(ec):
    response=ec.describe_volumes(Filters=[{'Name':'tag:Name','Values':[JOB]}]);require(not response.get('NextToken'),'VOLUME_DISCOVERY_TRUNCATED');return response['Volumes']
def no_live_conflict(ec):
    active=['pending','running','shutting-down','stopping','stopped']
    for tag,value in (('Name',JOB),('Project','HELM-pointer-saturation')):
        response=ec.describe_instances(Filters=[{'Name':'tag:'+tag,'Values':[value]},{'Name':'instance-state-name','Values':active}]);require(not response.get('NextToken'),'CONFLICT_DISCOVERY_TRUNCATED')
        require(not any(r['Instances'] for r in response['Reservations']),'EXISTING_ACTIVE_HOST_CONFLICT')
    require(not scoped_volumes(ec),'EXISTING_SCOPED_DISK_CONFLICT')
def terminate(ec,instance):ec.terminate_instances(InstanceIds=[instance])
def preserve_error(stage,error):
    response=getattr(error,'response',None) or {}
    save('CONTROL_FAILURE_'+str(time.time_ns())+'.json',{'job':JOB,'utc':utc(),'stage':stage,'type':type(error).__name__,'aws_code':response.get('Error',{}).get('Code'),'message':str(error)[:500] if isinstance(error,RuntimeError) else 'Sensitive request arguments/URLs omitted','no_retry':True})
