"""Public-only compute accounting, independent of measured scores or model code.

This adds evidence validation, not a new experimental endpoint. Run without
arguments to save planned work; pass a collected artifacts directory to audit
its counters after completion. Never imports numerical packages or a checker.
"""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'research/CAS_META_2_COMPOSITION')]
from cas_meta2.typed_teaching import matched_contract as c, source


def slots(packet):
    world=next(w for w in packet['source']['worlds'] if w['world_id']==packet['source']['focus_world_id'])
    n=len(world['nodes']); kind=packet['record']['query']['kind']
    return {'role_set':6,'definition':3,'context':n+1,'analogy':1,
        'correspondence':n+1,'parts':n,'edge_account':n*n,'reach':1}[kind]


def counts(presentations, slot_count, passes, batches=0):
    return {'core_forward_attempts':passes,'core_forward_calls':passes,'sample_core_passes':passes,
        'slot_forwards':slot_count,'prediction_calls':presentations,'staged_batches':batches,
        'backward_attempts':batches,'backward_calls':batches,'optimizer_step_attempts':batches,
        'optimizer_updates':batches,'private_loss_plan_calls':presentations if batches else 0}


def sum_counts(values):
    values=list(values)
    assert values and all(v.keys()==values[0].keys() for v in values)
    return {k:sum(v[k] for v in values) for k in values[0]}


def planned():
    frozen,_,dev=c.load_material(ROOT)
    packets=dict(c.public_packets(frozen)); probes=dict(c.retention_packets(frozen)); development=c.development_packets(dev)
    representative={}
    for key,p in packets.items(): representative.setdefault(p['record']['query']['kind'],key)
    representative={kind:representative[kind] for kind in sorted(representative)}
    def evaluate(selected):
        n=sum(slots(p) for p in selected)
        return counts(len(selected),n,n*8)
    result={}
    for condition in c.CONDITIONS:
        batches,stats=c.schedule(frozen,condition)
        def training(groups):
            return counts(sum(len(b['record_ids']) for b in groups),
                sum(slots(packets[k]) for b in groups for k in b['record_ids']),
                sum(slots(packets[k])*b['depth'] for b in groups for k in b['record_ids']),len(groups))
        phases={'initial':evaluate(list(packets.values())), 'final':evaluate(list(packets.values())),
            'retention_before':evaluate(list(probes.values())), 'retention_after':evaluate(list(probes.values())),
            'main_training':training(batches),'interference_training':training(c.interference_batches(frozen)),
            'initial_reload':evaluate([packets[k] for k in representative.values()]),
            'final_reload':evaluate([packets[k] for k in representative.values()]),
            'retained_reload':evaluate([probes[k] for k in list(probes)[:8]])}
        for cursor in (0,40,80,120,160): phases['development_%03d'%cursor]=evaluate(list(development.values()))
        replay=sum_counts([training(batches[-1:]),phases['final_reload']])
        for i in (1,2): phases['replay_'+str(i)]=replay
        result[condition]={'phases':phases,'totals':sum_counts(phases.values()),'schedule_digest':stats['batches_digest']}
    a,m=(result[condition] for condition in c.CONDITIONS)
    assert a['phases']==m['phases'] and a['totals']==m['totals']
    assert a['totals']['optimizer_updates']==a['totals']['backward_calls']==178
    assert a['phases']['main_training']['prediction_calls']==1152
    assert a['phases']['main_training']['core_forward_calls']==17178
    return {'schema':'cncm.typed-matched-independent-work-plan/0.1','planned':result,
        'planning_only':True,'models_executed':0,'targets_constructed':0,'same_counted_work':True,
        'boundary':'Counted mathematical operations, not equal elapsed time or actual cloud charges.'}


def audit(directory, plan):
    directory=Path(directory).resolve(strict=True)
    report=json.loads((directory/'worker_report.json').read_bytes())
    expected=plan['planned'][report['condition']]
    actual=report['global_actual_work']
    measured={row['phase']:row['delta'] for row in actual['phases']}
    assert len(measured)==len(actual['phases']) and measured==expected['phases']
    assert actual['totals']==sum_counts(measured.values())==expected['totals']
    initial=json.loads((directory/'initial_checkpoint.json').read_bytes())['metadata']
    assert all(v==0 for v in initial['counters'].values())
    return {'schema':'cncm.typed-matched-independent-work-audit/0.1','job':report['job'],
        'status':'EXACT_DECLARED_WORK_OBSERVED','totals':actual['totals'],'worker_report_sha256':
        sha256((directory/'worker_report.json').read_bytes()).hexdigest(),'numeric_work_performed_by_audit':False}


if __name__=='__main__':
    result=planned()
    if len(sys.argv)==2: result=audit(sys.argv[1],result)
    else:
        path=ROOT/'records/typed_matched_001/independent_work_plan_001.json'
        with path.open('xb') as f: f.write(c.canonical(result))
    print(json.dumps(result),flush=True)
