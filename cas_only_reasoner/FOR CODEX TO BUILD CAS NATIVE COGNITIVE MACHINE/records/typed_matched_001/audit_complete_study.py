"""Independent final file, pairing, work and rational-endpoint audit.

Reads completed receipts only. No model, checker, provider or final-panel import.
"""
from collections import Counter
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import runpy

ROOT=Path(__file__).resolve().parents[2]
RECORDS=ROOT/'records/typed_matched_001'
SEEDS=(20260917,20260918,20260919)
ARMS=('ALT_COMPONENT_WHOLE','MIXED_SAME_ITEMS')
CURSORS=(0,40,80,120,160)
STATE_KEYS=tuple(k+'_state_identity' for k in ('model','optimizer','encoder','rng'))


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()


def digest(value): return sha256(canonical(value)).hexdigest()
def read(path): return json.loads(Path(path).read_bytes())
def rational(value): return {'numerator':value.numerator,'denominator':value.denominator,'value':float(value)}


def family_accuracy(rows, families):
    assert len(families)==6
    assert len([k for f in families for k in f['record_ids']])==len(rows)==59
    assert {k for f in families for k in f['record_ids']}==set(rows)
    result=Fraction()
    for f in families:
        part=[rows[k] for k in f['record_ids'] if rows[k]['kind']=='parts']
        reach=[rows[k] for k in f['record_ids'] if rows[k]['kind']=='reach']
        assert len(part)==1 and len(reach)==len(f['record_ids'])-1 and reach
        result+=(Fraction(sum(r['correct'] for r in part))+Fraction(sum(r['correct'] for r in reach),len(reach)))/2
    return result/6


def check_scores(artifacts, phase):
    raw=(artifacts/(phase+'_predictions.json')).read_bytes()
    seal=json.loads(raw); score=read(artifacts/(phase+'_scoring.json'))
    assert seal['phase']==score['phase']==phase
    assert score['public_seal']=={'name':phase+'_predictions.json','bytes':len(raw),'sha256':sha256(raw).hexdigest()}
    predictions=seal['predictions']; rows=score['rows']
    assert [r['record_id'] for r in predictions]==[r['record_id'] for r in rows]
    assert len({r['record_id'] for r in rows})==len(rows)
    for p,r in zip(predictions,rows):
        assert r['prediction_id']==p['prediction_id']=='typed-prediction-'+digest({k:v for k,v in p.items() if k!='prediction_id'})
        assert r['answer_digest']==digest(p['answer']) and r['kind']==p['answer']['kind']
        assert type(r['correct']) is bool
        assert r['check_digest']==digest({k:v for k,v in r.items() if k not in ('record_id','prediction_id','check_digest')})
    assert score['total']==len(rows) and score['correct']==sum(r['correct'] for r in rows)
    return {r['record_id']:r for r in rows}


def run():
    study_path=RECORDS/'admission_001/study.json'; assert sha256(study_path.read_bytes()).hexdigest()=='154dee19e678aa3520b47528100642d73303c836230abcb7db6bc02d242a5099'
    study=read(study_path); assert len(study['jobs'])==6
    expected_work=read(RECORDS/'independent_work_plan_001.json')
    work_audit=runpy.run_path(str(RECORDS/'independent_work_audit.py'))['audit']
    results=[]; actual_by_key={}; initial_by_key={}; correction_by_key={}; targets_by_key={}; curves={}
    for job in study['jobs']:
        root=Path(job['receipt_dir']); collected=root/'collected'; artifacts=collected/'results/artifacts'
        for name in ('request','authority','owner'):
            pin=job[name]; raw=Path(pin['path']).read_bytes()
            assert len(raw)==pin['bytes'] and sha256(raw).hexdigest()==pin['sha256']
        authority=read(job['authority']['path']); lifecycle=read(root/'result.json'); report=read(artifacts/'worker_report.json')
        analysis=read(root/'matched_analysis.json'); index=read(root/'collected_inventory.json')
        assert lifecycle['completed_deliverable'] is True and lifecycle['cleanup']['complete'] is True
        assert lifecycle['stages']['missing_required_objects']==[] and lifecycle['evidence_contract']['required_count']==397
        assert report['status']=='COMPLETE_TYPED_MATCHED_DEVELOPMENT_ARM' and report['job']==job['job']
        assert report['source_sha']==study['source_sha']==authority['source_sha']
        assert report['design']==authority['worker_config']['design'] and report['inputs']==authority['worker_config']['inputs']
        assert read(collected/'input/config.json')==authority['worker_config']
        assert sha256((collected/'input/source.zip').read_bytes()).hexdigest()==study['package_archive_sha256']
        assert index['failures']==[] and index['file_count']==len(index['files'])==584
        assert len({p['relative_path'] for p in index['files']})==584
        for pin in index['files']:
            path=collected/pin['relative_path']; assert path.resolve().is_relative_to(collected.resolve()) and not path.is_symlink()
            raw=path.read_bytes(); assert len(raw)==pin['bytes'] and sha256(raw).hexdigest()==pin['sha256'],pin['relative_path']
        envelope_raw=(collected/'results/result.json').read_bytes()
        assert sha256(envelope_raw).hexdigest()==(collected/'results/result.json.sha256').read_text().strip()
        manifest=read(artifacts/'manifest.json'); assert manifest['artifacts']==json.loads(envelope_raw)['artifacts'] and len(manifest['artifacts'])==394
        allowed={p['path']:p for p in report['inputs']}; loaded=read(artifacts/'loaded_sources.json')
        for stage in ('before','after'):
            assert len({r['module'] for r in loaded[stage]['modules']})==len(loaded[stage]['modules'])
            for row in loaded[stage]['modules']:
                assert row['execution']=='COMPILED_FROM_VERIFIED_SOURCE_BYTES' and {k:row[k] for k in ('path','bytes','sha256')}==allowed[row['path']]
        installed=read(artifacts/'installed_sources.json')
        assert installed['before']['source_files']==installed['after']['source_files']
        assert all(installed[s]['status']=='INSTALLED_AND_LOADED_SOURCES_MATCH_PINNED_WHEELS' for s in ('before','after'))
        replay=read(artifacts/'replay_report.json'); assert len(replay['reloads'])==3 and len(replay['replays'])==2
        for entry in replay['reloads']:
            metadata=read(artifacts/(entry['phase']+'_checkpoint.json'))['metadata']
            assert entry['exact_state']=={k:metadata[k] for k in STATE_KEYS}
            phase='retention_after' if entry['phase']=='retained' else entry['phase']
            expected={p['record_id']:p for p in read(artifacts/(phase+'_predictions.json'))['predictions']}
            assert all(p==expected[p['record_id']] for p in read(artifacts/(entry['phase']+'_reload_predictions.json'))['predictions'])
        final=read(artifacts/'final_checkpoint.json')['metadata']
        for entry in replay['replays']:
            prefix='replay_'+str(entry['branch']); assert entry['exact_state']=={k:final[k] for k in STATE_KEYS}
            assert (artifacts/(prefix+'_batch.json')).read_bytes()==(artifacts/'main_159_batch.json').read_bytes()
            assert (artifacts/(prefix+'_update.json')).read_bytes()==(artifacts/'main_159_update.json').read_bytes()
        work=work_audit(artifacts,expected_work)
        phases=('initial','final','retention_before','retention_after')+tuple('development_%03d'%v for v in CURSORS)
        scores={phase:check_scores(artifacts,phase) for phase in phases}
        protocol=read(artifacts/'protocol_material.json'); key=(job['model_seed'],job['condition'])
        assert key not in actual_by_key
        assert digest(protocol['schedule']['batches'])==report['design']['schedule']['batches_digest']
        assert digest(protocol['interference_batches'])==report['design']['interference_batches_digest']
        correction=[]
        for prefix,groups in (('main',protocol['schedule']['batches']),('interference',protocol['interference_batches'])):
            for i,batch in enumerate(groups):
                name=prefix+'_%03d_'%i; raw=(artifacts/(name+'batch.json')).read_bytes(); seal=json.loads(raw); update=read(artifacts/(name+'update.json'))
                assert update['public_seal_sha256']==sha256(raw).hexdigest() and update['batch_id']==seal['batch_id']
                assert [r['record_id'] for r in seal['predictions']]==batch['record_ids'] and seal['occurrence_ids']==batch['occurrence_ids']
                assert [r['record_id'] for r in update['correction_identities']]==batch['record_ids']
                for row in update['correction_identities']:
                    assert row['target_digest']==scores['initial'][row['record_id']]['target_digest']
                    correction.append((row['record_id'],batch['depth'],row['target_digest']))
        initial=read(artifacts/'initial_checkpoint.json')['metadata']; assert initial['cursor']==0 and all(v==0 for v in initial['counters'].values())
        initial_by_key[key]={k:initial[k] for k in STATE_KEYS}; correction_by_key[key]=sorted(correction)
        targets_by_key[key]={phase:sorted((k,v['target_digest']) for k,v in rows.items()) for phase,rows in scores.items()}
        curve={n:family_accuracy(scores['development_%03d'%n],protocol['development']['families']) for n in CURSORS}
        auc=(curve[0]+2*curve[40]+2*curve[80]+2*curve[120]+curve[160])/8
        assert abs(float(auc)-analysis['speed_auc'])<1e-15 and abs(float(curve[160])-analysis['transfer'])<1e-15
        curves[key]=(auc,curve[160]); actual_by_key[key]=report['global_actual_work']['totals']
        before=scores['retention_before']; after=scores['retention_after']; assert before.keys()==after.keys()
        correct_before=sum(v['correct'] for v in before.values()); correct_after=sum(v['correct'] for v in after.values())
        eligible=2*correct_before>=len(before); assert eligible==analysis['retention']['eligible']
        raw_pre=sum(v['correct'] for v in scores['initial'].values()); raw_post=sum(v['correct'] for v in scores['final'].values())
        assert raw_pre==analysis['exposed']['before']['correct'] and raw_post==analysis['exposed']['after']['correct']
        results.append({'job':job['job'],'model_seed':key[0],'condition':key[1],'source_sha':report['source_sha'],
            'collected_files_verified':584,'artifacts_verified':394,'required_objects_verified':397,
            'loaded_modules_verified':len(loaded['after']['modules']),'worker_seconds':report['elapsed_seconds'],
            'work_totals':work['totals'],'family_balanced_curve':{str(k):rational(v) for k,v in curve.items()},
            'speed_auc':rational(auc),'transfer':rational(curve[160]),'raw_development_final_correct':sum(v['correct'] for v in scores['development_160'].values()),
            'exposed_before':raw_pre,'exposed_after':raw_post,'retention_before':correct_before,'retention_after':correct_after,'retention_eligible':eligible,
            'initial_state':initial_by_key[key],'lifecycle_result_sha256':sha256((root/'result.json').read_bytes()).hexdigest()})
    assert set(actual_by_key)=={(s,c) for s in SEEDS for c in ARMS}
    pairs=[]
    for seed in SEEDS:
        a,m=((seed,c) for c in ARMS)
        assert initial_by_key[a]==initial_by_key[m] and correction_by_key[a]==correction_by_key[m]
        assert actual_by_key[a]==actual_by_key[m] and targets_by_key[a]==targets_by_key[m]
        pairs.append({'model_seed':seed,'speed_auc_difference':rational(curves[a][0]-curves[m][0]),'transfer_difference':rational(curves[a][1]-curves[m][1])})
    assert len({initial_by_key[s,ARMS[0]]['model_state_identity'] for s in SEEDS})==3
    mean_auc=sum((curves[s,ARMS[0]][0]-curves[s,ARMS[1]][0] for s in SEEDS),Fraction())/3
    mean_transfer=sum((curves[s,ARMS[0]][1]-curves[s,ARMS[1]][1] for s in SEEDS),Fraction())/3
    saved=read(RECORDS/'admission_001/paired_result.json')
    assert abs(saved['mean_speed_auc_difference']-float(mean_auc))<1e-15 and abs(saved['mean_transfer_difference']-float(mean_transfer))<1e-15
    assert all(p['retention_status']=='RETENTION_UNASSESSED' for p in saved['pairs']) and saved['mean_retained_fraction_difference'] is None
    result={'schema':'cncm.typed-matched-independent-complete-audit/0.1','status':'PASS','arms':results,'pairs':pairs,
        'complete_arms':6,'paired_initializations_verified':3,'distinct_initial_models':3,'files_verified':3504,'artifacts_verified':2364,
        'required_objects_verified':2382,'checkpoint_reloads_verified':18,'exact_last_update_replays_verified':12,
        'mean_speed_auc_difference':rational(mean_auc),'mean_transfer_difference':rational(mean_transfer),
        'paired_retention_eligible':0,'local_numeric_execution':False,'boundary':saved['boundary']}
    path=RECORDS/'independent_complete_audit_001.json'; path.open('xb').write((json.dumps(result,sort_keys=True)+'\n').encode())
    print(json.dumps({k:v for k,v in result.items() if k not in ('arms','pairs')}))


if __name__=='__main__': run()
