"""Prospective, single-attempt accounting for the separately authorized growth15 check."""
from decimal import Decimal
import hashlib,json,os
from pathlib import Path
SCHEMA='helm.growth15.aws.freeze/1'
def sha(b): return hashlib.sha256(b).hexdigest()
def check(ok,reason):
    if not ok: raise ValueError(reason)
def reserve(directory,authority,directive,source):
    directory,authority,directive=map(Path,(directory,authority,directive))
    a=json.loads(authority.read_bytes())
    check(a['schema']=='helm.growth15.authorization/1' and a['all_services_cap_usd']=='3.00' and a['execution_ceiling_usd']=='2.00' and a['protected_cleanup_usd']=='1.00','FINITE_GROWTH_AUTHORITY')
    check(a['owner_directive_sha256']==sha(directive.read_bytes()) and a['historical_funds_reused'] is False and a['automatic_retry'] is False,'AUTHORITY_BINDING')
    check(directory.name=='growth15_ledger_v1','SEPARATE_LEDGER_REQUIRED')
    directory.mkdir(exist_ok=True)
    check(not list(directory.glob('*.json')),'SINGLE_ALLOCATION_ALREADY_RESERVED')
    r={'schema':'helm.growth15.reservation/1','job_id':a['job_id'],'source_commit':source,'reserved_usd':'2.00','campaign_cap_usd':'3.00','protected_cleanup_usd':'1.00','authorization_sha256':sha(authority.read_bytes()),'owner_directive_sha256':sha(directive.read_bytes()),'historical_funds_reused':False,'automatic_retry':False,'status':'PROSPECTIVE_NOT_ACTUAL_BILL'}
    with (directory/'numerical.json').open('x',encoding='utf8') as f:
        json.dump(r,f,indent=2);f.flush();os.fsync(f.fileno())
    return directory/'numerical.json'
def validate_freeze(p,d):
    d=Path(d)
    expected={'schema':SCHEMA,'phase':'growth15','runner':'Codex','jobs':1,'retry_count':0,'instance_type':'g7.2xlarge','root_gib':75,'region':'us-west-2','account_id':'807562639912','maximum_all_services_usd':'2.00','campaign_total_cap_usd':'3.00','hard_wall_seconds':1800,'operator_seconds':1500,'scheduler_after_seconds':1800,'expected_tests':15,'expected_status':'PASS_GROWTH15_NUMERICAL','growth_source_commit':'c70e1a048d5130e5268b4a6556265aa53225b6c1','package_definition_commit':'a6fe92393dcce5309a4c08e558970d74a89c8447'}
    for k,v in expected.items(): check(p.get(k)==v,'GROWTH_FREEZE_FIELD:'+k)
    for name in ['authorization','reservation']:
        check(sha((d/(name+'.json')).read_bytes())==p[name+'_sha256'],'GROWTH_'+name.upper()+'_HASH')
    a=json.loads((d/'authorization.json').read_bytes());r=json.loads((d/'reservation.json').read_bytes())
    check(a['job_id']==r['job_id']==p['job_id'] and r['source_commit']==p['source_commit'],'GROWTH_JOB_SOURCE_BINDING')
    check(a['owner_directive_sha256']==r['owner_directive_sha256']==p['owner_directive_sha256'],'GROWTH_OWNER_BINDING')
    check(r['authorization_sha256']==p['authorization_sha256'] and r['reserved_usd']=='2.00' and r['protected_cleanup_usd']=='1.00' and r['campaign_cap_usd']=='3.00' and r['historical_funds_reused'] is False,'GROWTH_RESERVE_PROTECTION')
    check(Decimal(p['prospective_costs']['compute_max_usd'])+Decimal(p['prospective_costs']['other_services_allowance_usd'])<=Decimal(r['reserved_usd']),'GROWTH_COST_BOUND')

