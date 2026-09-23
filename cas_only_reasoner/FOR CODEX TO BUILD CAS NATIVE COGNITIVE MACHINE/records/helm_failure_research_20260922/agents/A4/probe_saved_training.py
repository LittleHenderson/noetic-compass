"""A4 bounded stdlib-only record examination. Does not import any project code."""
import collections
import hashlib
import json
import math
import pathlib
import sys
import time
import zipfile

START = time.monotonic()
OUT = pathlib.Path(__file__).resolve().parent
MANIFEST = OUT.parents[1] / 'SOURCE_AND_EVIDENCE_MANIFEST.json'
M = json.loads(MANIFEST.read_text(encoding='utf-8'))
PINS = {a['path']: a for s in M['subjects'] for a in s['artifacts']}
READS = {}

def read(path):
    if time.monotonic()-START > 115:
        raise RuntimeError('A4_115_SECOND_STOP')
    path = pathlib.Path(path)
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    pin = PINS.get(str(path))
    if pin:
        assert pin['sha256_raw'] == digest and pin['bytes'] == len(raw), str(path)
    READS[str(path)] = {'bytes': len(raw), 'sha256': digest, 'manifest_bound': bool(pin)}
    return raw

def js(path):
    return json.loads(read(path))

def jl(path):
    return [json.loads(x) for x in read(path).splitlines()]

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def stats(values):
    return {'count':len(values), 'min':min(values), 'max':max(values), 'mean':sum(values)/len(values)}

def test_saved_update_integrity(root, protocol):
    """One input case per subject; 1,470 main and 16 interference rows in each."""
    result, task_totals, kinds, order = [], collections.defaultdict(list), {}, []
    for phase in [f'pass_{p:02}' for p in range(1,11)] + ['interference']:
        rows = jl(root/f'{phase}_updates.jsonl')
        batches = jl(root/f'{phase}_batches.jsonl')
        assert len(rows) == len(batches) == (16 if phase == 'interference' else 147)
        clipping = []; grad_counts = collections.Counter(); finite_count = 0
        rates=set(); schedules=set(); ids=[]; kind_counts=collections.Counter()
        for u,b in zip(rows,batches):
            assert u['batch_id'] == b['batch_id']
            assert u['public_seal_sha256'] == hashlib.sha256((json.dumps(b,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n').encode()).hexdigest()
            predictions=b['predictions']; byid={p['record_id']:p for p in predictions}
            assert len(predictions)==len(u['tasks'])==8
            if phase!='interference':
                assert len({p['answer']['kind'] for p in predictions})==8
            ids.append([t['record_id'] for t in u['tasks']])
            for t in u['tasks']:
                kind=byid[t['record_id']]['answer']['kind']; kinds[t['record_id']]=kind
                kind_counts[kind]+=1
                assert math.isclose(t['raw_task_loss'],sum(f['raw_loss'] for f in t['fields'])/len(t['fields']),rel_tol=1e-6,abs_tol=1e-6)
                task_totals[(phase,kind)].append(t['raw_task_loss'])
            assert math.isclose(u['raw_batch_loss'],sum(t['raw_task_loss'] for t in u['tasks'])/len(u['tasks']),rel_tol=1e-12)
            numeric=[u[k] for k in ('raw_batch_loss','normalized_batch_loss','gradient_squared_norm')]
            assert all(math.isfinite(x) for x in numeric)
            finite_count+=1; grad_counts[(u['gradient_parameter_count'],u['gradient_parameter_total'])]+=1
            if 'learning_rate_this_step' in u: rates.add(u['learning_rate_this_step']); schedules.add(u['learning_rate_schedule'])
            if 'gradient_was_clipped' in u:
                assert u['gradient_was_clipped'] == (u['gradient_norm_before_clip'] > u['gradient_clip_norm'])
                assert math.isclose(u['gradient_norm_before_clip']**2,u['gradient_squared_norm'],rel_tol=2e-5)
                clipping.append(u['gradient_was_clipped'])
        if phase!='interference':
            assert set(kind_counts.values())=={147} and len(kind_counts)==8
            order.append(ids)
        result.append({'phase':phase,'rows':len(rows),'finite_rows':finite_count,'loss':stats([u['raw_batch_loss'] for u in rows]),
            'grad_squared':stats([u['gradient_squared_norm'] for u in rows]),'clip_count':sum(clipping),'clip_record_rows':len(clipping),
            'recorded_rates':sorted(rates),'recorded_schedules':sorted(schedules),'gradient_counts':{str(k):v for k,v in grad_counts.items()},
            'record_order_digest':digest(ids),'task_counts':dict(kind_counts),
            'mean_loss_by_kind':{k:sum(v)/len(v) for (p,k),v in task_totals.items() if p==phase}})
    assert all(o==order[0] for o in order)
    assert order[0]==[b['record_ids'] for b in protocol['schedule']['batches'][:147]]
    return {'phases':result,'same_order_all_ten_passes':True,'first_pass_record_order_digest':digest(order[0]),'unique_training_records':len({r for b in order[0] for r in b})}

def test_saved_transitions(root, protocol):
    """Saved checker rows, not a new execution of the semantic checker."""
    panels={}; predictions={}; held=set(protocol['held_back_record_ids'])
    for p in (0,1,2,4,6,8,10):
        stem=f'course_p{p:02}' if p in (0,1,10) else f'heldback_p{p:02}'
        score=js(root/f'{stem}_scoring.json'); pred=js(root/f'{stem}_predictions.json')
        assert sum(r['correct'] for r in score['rows'])==score['correct']
        panels[p]={r['record_id']:r for r in score['rows'] if r['record_id'] in held}
        predictions[p]={r['record_id']:r for r in pred['predictions'] if r['record_id'] in held}
        assert set(panels[p])==held
    lost=[i for i,r in panels[0].items() if r['correct'] and not panels[10][i]['correct']]
    details=[]
    for i in lost:
        details.append({'record_id':i,'query_id':panels[0][i]['query_id'],'kind':panels[0][i]['kind'],
          'chronology':[{'pass':p,'correct':panels[p][i]['correct'],'answer':predictions[p][i]['answer'],
              'scores':predictions[p][i]['scores']} for p in panels]})
    retention={phase:js(root/f'retention_{phase}_scoring.json') for phase in ('before','after')}
    for score in retention.values():
        assert sum(r['correct'] for r in score['rows'])==score['correct']
    before={r['record_id']:r for r in retention['before']['rows']}; after={r['record_id']:r for r in retention['after']['rows']}
    lost_ret=[{'record_id':i,'query_id':r['query_id'],'kind':r['kind'],'held_world':i in protocol['retention_held_world_record_ids']} for i,r in before.items() if r['correct'] and not after[i]['correct']]
    gained_ret=[i for i,r in before.items() if not r['correct'] and after[i]['correct']]
    return {'held_records':len(held),'held_correct_by_pass':{p:sum(r['correct'] for r in rows.values()) for p,rows in panels.items()},
      'lost_initial_held_count':len(lost),'lost_initial_held':details,
      'retention':{'before':retention['before']['correct'],'after':retention['after']['correct'],'total':len(before),
                   'lost_count':len(lost_ret),'gained_count':len(gained_ret),'lost':lost_ret,'gained':gained_ret}}

def test_checkpoint_sidecars(root):
    """Saved sidecars only. Checkpoint tensor files are never deserialized."""
    result={}
    for name,cursor in [('initial',0),('pass_01',147),('prelast',1469),('final',1470),('retained',1486)]:
        d=js(root/f'{name}_checkpoint.json'); md=d['metadata']; assert md['cursor']==cursor
        result[name]={'cursor':md['cursor'],'checkpoint_sha256':d['sha256'],'model_state_identity':md['model_state_identity'],
            'encoder_state_identity':md['encoder_state_identity'],'rng_state_identity':md['rng_state_identity'],
            'learnable_names':md['learnable_names'],'scope':md['run_identity']['scope'],
            'limits':md['run_identity']['limits'],'optimizer_config':md['run_identity']['optimizer_config']}
    assert len({v['encoder_state_identity'] for v in result.values()})==1
    return result

def main():
    summaries=[]
    for s in M['subjects']:
        receipt=pathlib.Path(s['receipt_root']); root=receipt/'checkpoints'
        config=js(receipt/'collected/input/config.json'); protocol=js(root/'protocol_material.json')
        report=js(root/'worker_report.json'); identity=js(root/'model_identity.json'); loaded=js(root/'loaded_sources.json')
        d={'version':s['version'],'seed':s['seed'],'source_commit':s['source_commit'],'receipt_root':s['receipt_root'],
           'config_settings':{k:v for k,v in config['design'].items() if k in ('optimizer_config','schedule','schedule_stratified','initialization','training_loss','reporting_loss','passes')},
           'worker':{k:report[k] for k in ('status','runtime','completed_main_updates','global_updates','checkpoint_reload_verified','retention_scores','pass_summaries','schedule_plan_mode')},
           'identity':identity,'loaded_sources':loaded,
           'update_integrity':test_saved_update_integrity(root,protocol),
           'transitions':test_saved_transitions(root,protocol),'checkpoints':test_checkpoint_sidecars(root),
           'replay_report':js(root/'replay_report.json'),'schedule_plan':js(root/'schedule_plan.json')}
        summaries.append(d)
        print(s['version'],s['seed'],'updates=1470+16','held_lost',d['transitions']['lost_initial_held_count'],
              'retention',d['transitions']['retention']['before'],d['transitions']['retention']['after'])
    (OUT/'SAVED_RECORD_ANALYSIS.json').write_text(json.dumps({'subjects':summaries},indent=2)+'\n',encoding='utf-8',newline='\n')
    (OUT/'READ_FINGERPRINTS.json').write_text(json.dumps(READS,indent=2)+'\n',encoding='utf-8',newline='\n')
    run_path=OUT/'PROBE_RUN.json'
    prior=json.loads(run_path.read_text(encoding='utf-8')) if run_path.exists() else None
    run={'python':sys.version,'executable':sys.executable,'elapsed_seconds':time.monotonic()-START,
         'test_functions':3,'subject_cases_per_function':6,'subject_function_cases':18,'probe_executions':1+(prior['probe_executions'] if prior else 0),
         'main_update_rows':8820,'interference_update_rows':96,'new_model_executions':0,
         'status':'PASS','files_read':len(READS),'unbound_reads':[p for p,v in READS.items() if not v['manifest_bound']]}
    if prior:
        run['previous_executions']=[*prior.get('previous_executions',[]), {k:v for k,v in prior.items() if k!='previous_executions'}]
    run_path.write_text(json.dumps(run,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(run))

if __name__=='__main__':
    main()
