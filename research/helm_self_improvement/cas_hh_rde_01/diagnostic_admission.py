"""Single parity reservation inside the owner-issued, separate USD12 pilot.

This mechanism records the actual owner directive and package, not a signature.
It never debits CONT19, growth, seed18 or Q1. Future phases need fresh admission.
"""
from decimal import Decimal
from pathlib import Path
import hashlib
import json
import os

SCHEMA='helm.hh-rde.aws.freeze/1'
PARENT='5b37699d52e530a9ecd3563e235f0884630225da2fbe27489767a196c0f7a109'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def require(ok,code):
    if not ok:raise ValueError(code)

def reserve(ledger,authorization,directive,source):
    ledger,authorization,directive=map(Path,(ledger,authorization,directive))
    a=json.loads(authorization.read_bytes())
    require(a['task']=='CAS-HH-RDE-01' and a['owner_issuance_sha256']==sha(directive.read_bytes()),'OWNER_ISSUANCE_BINDING')
    require(a['campaign_total_usd']=='12.00' and a['parity_setup_usd']=='2.00'
            and a['protected_cleanup_usd']=='2.00' and a['other_campaign_funds_used']=='0.00','FINITE_DIAGNOSTIC_AUTHORITY')
    require(a['equivalent_prior_diagnostic_reservations']==[],'RECONCILE_EXISTING_DIAGNOSTIC_RESERVATIONS_FIRST')
    require(ledger.name=='CAS-HH-RDE-01-PILOT','CANONICAL_PILOT_LEDGER_REQUIRED')
    ledger.mkdir(exist_ok=False)
    row={'schema':'helm.hh-rde.reservation/1','campaign':'CAS-HH-RDE-01-PILOT','job_id':a['job_id'],
         'source_commit':source,'reserved_usd':'2.00','bucket':'parity_setup','campaign_total_usd':'12.00',
         'protected_cleanup_usd':'2.00','remaining_unadmitted_discovery_usd':'6.00',
         'remaining_unadmitted_confirmation_usd':'2.00','automatic_retries':0,
         'other_campaign_funds_used':'0.00','actual_bill_usd':None,
         'authorization_sha256':sha(authorization.read_bytes()),'owner_issuance_sha256':sha(directive.read_bytes()),
         'status':'PROSPECTIVE_RESERVATION_NOT_PROVIDER_BILL'}
    with (ledger/'parity_01.json').open('x',encoding='utf8') as f:
        json.dump(row,f,indent=2);f.flush();os.fsync(f.fileno())
    return ledger/'parity_01.json'

def validate_freeze(p,directory):
    d=Path(directory)
    corrective=p.get('phase')=='parity_corrective_setup'
    exact={'schema':SCHEMA,'phase':'parity_corrective_setup' if corrective else 'parity_setup','runner':'Codex','jobs':1,'retry_count':0,
           'maximum_all_services_usd':'2.00','campaign_total_cap_usd':'12.00',
           'hard_wall_seconds':1800,'operator_seconds':1500,'scheduler_after_seconds':1800,
           'instance_type':'g7.2xlarge','root_gib':75,'region':'us-west-2','account_id':'807562639912',
           'expected_tests':62 if corrective else 21,'expected_status':'PASS_HH_RDE_PARITY_RELOAD','parent_sha256':PARENT,
           'max_packet_forwards':6,'max_optimizer_updates':0,'max_raw_capture_bytes':16777216,
           'max_inputs':2,'max_checkpoints':1,'max_conditions':3,'automatic_retries':0}
    for key,value in exact.items():require(p.get(key)==value,'DIAGNOSTIC_FREEZE_FIELD:'+key)
    for name in ('authorization','reservation'):
        require(sha((d/(name+'.json')).read_bytes())==p[name+'_sha256'],'DIAGNOSTIC_'+name.upper()+'_HASH')
    a=json.loads((d/'authorization.json').read_bytes());r=json.loads((d/'reservation.json').read_bytes())
    require(a['job_id']==r['job_id']==p['job_id'] and r['source_commit']==p['source_commit'],'JOB_SOURCE_BINDING')
    require(a['owner_issuance_sha256']==r['owner_issuance_sha256']==p['owner_directive_sha256'],'OWNER_BINDING')
    require(r['authorization_sha256']==p['authorization_sha256'] and r['reserved_usd']=='2.00'
            and r['campaign_total_usd']=='12.00' and r['protected_cleanup_usd']=='2.00'
            and r['other_campaign_funds_used']=='0.00','NO_HISTORICAL_FUNDS_OR_RESERVE_BORROWING')
    if corrective:
        require(r['model_job_slot']==2 and r['maximum_model_jobs']==2
                and r['allocation_usd']=={'original_preparation':'2.00','corrected_preparation':'2.00',
                    'discovery':'4.00','confirmation_readout':'2.00','protected_cleanup':'2.00'},'CORRECTIVE_REALLOCATION')
        original=Path(r['original_reservation_path'])
        require(sha(original.read_bytes())==r['original_reservation_sha256'],'ORIGINAL_RESERVATION_CHANGED')
        canonical=original.parent/'parity_02_corrective.json'
        require(canonical.read_bytes()==(d/'reservation.json').read_bytes(),'CANONICAL_CORRECTIVE_SLOT_BINDING')
    costs=p['prospective_costs']
    require(Decimal(costs['compute_max_usd'])+Decimal(costs['other_services_allowance_usd'])<=Decimal('2.00'),'ALL_SERVICES_BOUND')
    require(Decimal(costs['compute_hourly_usd'])*Decimal(p['hard_wall_seconds'])/3600<=Decimal(costs['compute_max_usd']),'PRICE_WALL_BOUND')


def reserve_corrective(ledger, authorization, directive, source):
    """One owner-issued second slot. Preserve the first reservation byte for byte."""
    ledger,authorization,directive=map(Path,(ledger,authorization,directive))
    a=json.loads(authorization.read_bytes());original=ledger/'parity_01.json'
    require(ledger.name=='CAS-HH-RDE-01-PILOT' and original.is_file(),'ORIGINAL_LEDGER_REQUIRED')
    require(a['task']=='CAS-HH-RDE-01_CORRECTIVE_PASSIVE_VALIDATION'
            and a['owner_issuance_sha256']==sha(directive.read_bytes()),'CORRECTIVE_OWNER_BINDING')
    allocation={'original_preparation':'2.00','corrected_preparation':'2.00',
                'discovery':'4.00','confirmation_readout':'2.00','protected_cleanup':'2.00'}
    require(a['allocation_usd']==allocation and a['campaign_total_usd']=='12.00'
            and a['corrective_attempts']==1 and a['maximum_model_jobs']==2,'FINITE_CORRECTIVE_AUTHORITY')
    raw=original.read_bytes();first=json.loads(raw)
    require(sha(raw)==a['original_reservation_sha256'] and first['reserved_usd']=='2.00'
            and first['job_id']=='helm-hh-rde-parity-20260928-a1','PRESERVE_ORIGINAL_RESERVATION')
    require(set(p.name for p in ledger.glob('*.json'))=={'parity_01.json'},'CORRECTIVE_SLOT_ALREADY_RECORDED')
    row={'schema':'helm.hh-rde.corrective-reservation/1','campaign':'CAS-HH-RDE-01-PILOT',
         'job_id':a['job_id'],'source_commit':source,'reserved_usd':'2.00','campaign_total_usd':'12.00',
         'protected_cleanup_usd':'2.00','allocation_usd':allocation,'model_job_slot':2,'maximum_model_jobs':2,
         'original_reservation_path':str(original.resolve()),'original_reservation_sha256':sha(raw),
         'historical_reservation_released':False,'other_campaign_funds_used':'0.00',
         'authorization_sha256':sha(authorization.read_bytes()),'owner_issuance_sha256':sha(directive.read_bytes()),
         'automatic_retries':0,'actual_bill_usd':None,'status':'PROSPECTIVE_RESERVATION_NOT_PROVIDER_BILL'}
    path=ledger/'parity_02_corrective.json'
    with path.open('x',encoding='utf8') as f:
        json.dump(row,f,indent=2);f.flush();os.fsync(f.fileno())
    return path
