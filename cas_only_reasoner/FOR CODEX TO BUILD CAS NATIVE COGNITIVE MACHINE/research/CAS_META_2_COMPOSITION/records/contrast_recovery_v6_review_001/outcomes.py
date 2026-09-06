"""Independent fixed-denominator replay; never calls native execution."""
import math
import sqlite3


def groups(tasks,c):
    c.require(type(tasks) is list and len(tasks)==72,'OUTCOME_72_TASKS_REQUIRED')
    result={'all':list(range(72)),**{k:[] for k in
        ('depth_3','depth_4','same_depth','wording_shift','deeper_calls')}}
    for i,t in enumerate(tasks):
        depth,side=t['provenance']['depth'],t['contrast_side']
        c.require(type(depth) is int and side in ('same_depth','wording_shift','deeper_calls')
            and depth==(4 if side=='deeper_calls' else 3)
            and t['provenance']['evaluation_group']=='test','OUTCOME_TASK_GROUP_IDENTITY')
        result['depth_'+str(depth)].append(i);result[side].append(i)
    c.require({k:len(v) for k,v in result.items()}=={'all':72,'depth_3':48,'depth_4':24,
        'same_depth':24,'wording_shift':24,'deeper_calls':24},'OUTCOME_GROUP_COUNTS')
    return result


def recount(cases,c,indices=None):
    c.require(type(cases) is list and len(cases)==72 and all(type(x.get('case_index')) is int for x in cases)
        and [x['case_index'] for x in cases]==list(range(72)),'OUTCOME_EXACT_72_ORDERED_CASES')
    for case in cases:
        c.require(set(case['arms'])==set(c.ARMS),'OUTCOME_FIVE_ARM_COVERAGE')
        for arm,row in case['arms'].items():
            c.require(type(row['case_index']) is int and row['case_index']==case['case_index']
                and row['arm']==arm and row['execution_status'] in ('EXECUTED','REJECTED',c.FAILURE)
                and row['model_rejection'] is (row['execution_status']=='REJECTED'),'OUTCOME_ARM_ATTRIBUTION')
            p=row['partial_work']
            if row['execution_status']==c.FAILURE:
                c.require(type(p) is dict and p['compute_complete'] is False and p['failed_tick_compute'] is None
                    and all(type(p[k]) is int and p[k]>=0 for k in
                        ('committed_native_runs','committed_reserved_policy_units')),'OUTCOME_PARTIAL_COMPUTE')
                c.require(row['verification']['task_correct'] is False,'OUTCOME_FAILED_TASK_SUCCESS')
            else:
                c.require(p is None and all(type(row['verification'][k]) is bool for k in c.FIELDS),
                          'OUTCOME_COMPLETED_METRIC_TYPE')
                c.require(all(type(row['verification'].get(k,0)) is int and row['verification'].get(k,0)>=0
                              for k in ('native_runs','reserved_policy_units')),'OUTCOME_COMPUTE_INTEGER')
    selected=list(range(72)) if indices is None else indices
    c.require(type(selected) is list and selected and len(set(selected))==len(selected)
        and all(type(i) is int and 0<=i<72 for i in selected),'OUTCOME_GROUP_INDICES')
    results={}
    for arm in c.ARMS:
        rows=[cases[i]['arms'][arm] for i in selected]
        failures=[r for r in rows if r['execution_status']==c.FAILURE]
        counts={k:sum(r['verification'][k] is True for r in rows) for k in c.FIELDS}
        results[arm]={'total':len(rows),**counts,'task_accuracy':counts['task_correct']/len(rows),
            'model_rejections':sum(r['execution_status']=='REJECTED' for r in rows),
            'post_admission_runtime_failures':len(failures),
            'native_executed':sum(r['execution_status']=='EXECUTED' for r in rows),
            'committed_native_runs_lower_bound':sum(r['partial_work']['committed_native_runs']
                if r['partial_work'] is not None else r['verification'].get('native_runs',0) for r in rows),
            'reserved_policy_units_lower_bound':sum(r['partial_work']['committed_reserved_policy_units']
                if r['partial_work'] is not None else r['verification'].get('reserved_policy_units',0) for r in rows),
            'compute_complete':not failures,'all_cases_in_denominator':True}
    return results


def compare_aggregate(saved,derived,c):
    c.require(type(saved) is dict and set(saved)==set(c.ARMS),'OUTCOME_AGGREGATE_ARMS')
    for arm,row in derived.items():
        for key,value in row.items():
            actual=saved[arm].get(key)
            c.require(type(actual) is type(value) and actual==value,'OUTCOME_AGGREGATE_MISMATCH:'+arm+':'+key)


def _seconds(value,c):
    c.require(type(value) in (int,float) and math.isfinite(value) and value>=0,'OUTCOME_INVALID_TIME')


def audit(packet,context,engine,validator,partial,identity_check,c):
    tasks,predictions=context['tasks'],context['predictions']
    grouped=groups(tasks,c)
    stored=packet.json(c.NATIVE+'evaluation_results.json')
    cases=stored['cases']
    c.require(type(cases) is list and len(cases)==len(predictions)==72,'OUTCOME_COMPLETE_72_REQUIRED')
    audited=[];fixed_identity=context['runtime_identity'];expected_databases=set()
    for index,(task,prediction,case) in enumerate(zip(tasks,predictions,cases,strict=True)):
        folder=c.NATIVE+f'evaluation/case_{index:04d}/'
        c.require(type(case['case_index']) is int and case['case_index']==index and case['task_id']==task['task_id']
            and set(case['arms'])==set(c.ARMS) and case==packet.json(folder+'case_receipt.json'),
            'OUTCOME_CASE_MAPPING_OR_COPY')
        identity_check(packet.json(folder+'worker_identity.json'))
        reference=packet.json(folder+'reference_result.json')
        c.require(reference['runtime_identity']==reference['runtime_identity_after'],'OUTCOME_REFERENCE_IDENTITY_CHANGED')
        c.require(reference['runtime_identity']==fixed_identity,'OUTCOME_REFERENCE_FIXED_MODEL_CHANGED')
        ref=engine._native(packet,reference,folder+'reference',task['public'],task['target'],reference=True)
        expected_databases.add(folder+'reference/native.db')
        ref_verdict=engine.reference_verdict(task,ref)
        engine.compare_verdict(packet.json(folder+'reference_verdict.json'),ref_verdict)
        c.require(case['reference_verification']==packet.json(folder+'reference_verdict.json'),
                  'OUTCOME_REFERENCE_VERDICT_COPY')
        _seconds(case['reference_wall_seconds'],c);_seconds(case['case_wall_seconds'],c)
        arms={}
        for arm in c.ARMS:
            row=case['arms'][arm];path=folder+arm
            action=prediction['actions'][arm]
            c.require(row==packet.json(path+'/case_receipt.json') and row['arm']==arm
                and type(row['case_index']) is int and row['case_index']==index and row['action']==action,
                'OUTCOME_ARM_RECEIPT_OR_SEAL')
            c.require(c.remote_member(row['evidence_directory'])==path,'OUTCOME_DIRECTORY_ATTRIBUTION')
            _seconds(row['wall_seconds'],c)
            result=packet.json(path+'/execution_result.json');verdict=packet.json(path+'/verification.json')
            c.require(row['verification']==verdict and result['status']==row['execution_status'],
                      'OUTCOME_RESULT_VERDICT_COPY')
            status=row['execution_status'];reason=engine.admission_error(action,task['public'])
            summary={'case_index':index,'arm':arm,'action':action,'execution_status':status,
                     'model_rejection':status=='REJECTED','partial_work':None}
            if status=='EXECUTED':
                c.require(reason is None and row['model_rejection'] is False and row['failure'] is None
                    and row['partial_work'] is None and result['runtime_identity']==fixed_identity,
                    'OUTCOME_EXECUTED_IDENTITY_OR_CLASSIFICATION')
                c.require(path+'/native/failure.json' not in packet.inventory,'OUTCOME_SUCCESS_WITH_FAILURE_FILE')
                actual=engine._native(packet,result,path+'/native',task['public'],action)
                derived=engine.candidate_verdict(task,action,actual,ref)
                engine.compare_verdict(verdict,derived)
                expected_databases.add(path+'/native/native.db')
                summary.update(verification=derived,rows=actual['rows'],
                    composition_events=packet.json(path+'/native/composition_events.json'),
                    complete_trace=True,return_node=actual['return_node'])
            elif status=='REJECTED':
                c.require(reason is not None and row['model_rejection'] is True and row['failure']==reason
                    and row['partial_work'] is None and result=={'status':'REJECTED','action':action,
                        'failure':reason,'reserved_policy_units':0,'native_runs':0},'OUTCOME_REJECTION_IDENTITY')
                c.require(not any(n.startswith(path+'/native/') for n in packet.inventory),
                          'OUTCOME_REJECTION_HAS_NATIVE_WRITES')
                expected={**{k:False for k in c.FIELDS},'repair_success':None,'repair_required':False,
                          'failure':'PREDICTED_PROGRAM_REJECTED'}
                c.require(verdict==expected,'OUTCOME_REJECTION_VERDICT')
                summary.update(verification={**expected,'native_runs':0,'reserved_policy_units':0},
                               rows=[],composition_events=None,complete_trace=False)
            elif status==c.FAILURE:
                error={'type':'RuntimeContractError','module':'cas_cjt.runtime','message':c.MESSAGE}
                c.require(reason is None and row['model_rejection'] is False and row['failure']==error
                    and result=={'status':c.FAILURE,'selected_action':action,'failure':error,
                        'execution_started':True,'execution_completed':False,'partial_work':row['partial_work']},
                    'OUTCOME_POST_START_FAILURE_IDENTITY')
                expected={'task_correct':False,'procedure_correct':None,'binding_correct':None,
                    'dependency_correct':None,'actual_output_correct':False,'trace_valid':False,
                    'repair_required':True,'repair_success':False,'failure':c.FAILURE}
                c.require(verdict==expected,'OUTCOME_POST_START_FAILURE_VERDICT')
                checked=partial.audit_prefix(packet,path+'/native',task['public'],action,fixed_identity,engine,validator,c)
                p=row['partial_work']
                c.require(type(p) is dict and all(p.get(k)==checked[k] and type(p.get(k)) is type(checked[k]) for k in
                    ('committed_native_runs','committed_reserved_policy_units','failed_tick_compute','compute_complete',
                     'database_sha256','evidence_sha256')) and p.get('sqlite_integrity_checked') is True
                    and p.get('payload_hashes_checked') is True and p.get('stored_trace_semantics_checked') is False
                    and p.get('full_execution_trace_available') is False,'OUTCOME_PARTIAL_RECEIPT_MISMATCH')
                expected_databases.add(path+'/native/native.db')
                summary.update(verification=expected,partial_work=checked,rows=checked['rows'],
                    composition_events=None,complete_trace=False,next_sealed_run=checked['next_sealed_run'])
            else:c.require(False,'OUTCOME_UNSUPPORTED_STATUS')
            arms[arm]=summary
        c.require(arms['rule']['action']==task['target'] and arms['rule']['verification']['task_correct'] is True,
                  'OUTCOME_CORRECT_RULE_REQUIRED')
        audited.append({'case_index':index,'task_id':task['task_id'],'arms':arms,'reference':ref,
                        'reference_verification':ref_verdict})
    actual={n for n in packet.inventory if n.startswith(c.NATIVE+'evaluation/') and n.endswith('/native.db')}
    c.require(actual==expected_databases,'OUTCOME_UNACCOUNTED_DATABASE_OR_CASE')
    expected_case_names={f'case_{i:04d}' for i in range(72)}
    for name in packet.inventory:
        if name.startswith(c.NATIVE+'evaluation/'):
            parts=name.removeprefix(c.NATIVE+'evaluation/').split('/')
            c.require(len(parts)>=2 and parts[0] in expected_case_names and parts[1] in
                {*c.ARMS,'reference','reference_result.json','reference_verdict.json','case_receipt.json','worker_identity.json'},
                'OUTCOME_UNEXPECTED_CASE_FILE')
    c.require(not any(n.startswith(c.NATIVE) and n.endswith(('worker_failure.json','recovery_failure.json',
                        'evaluation_partial.json')) for n in packet.inventory),'OUTCOME_INCOMPLETE_RECOVERY_FILES')
    result=recount(audited,c)
    compare_aggregate(stored['results'],result,c)
    return {'cases':audited,'results':result,'groups':{name:recount(audited,c,indices)
            for name,indices in grouped.items()},'references_checked':72,'arms_checked':360,
            'native_databases_checked':len(expected_databases),'runtime_identity':fixed_identity}


def exports(packet,validator,c):
    counts={}
    for name in packet.inventory:
        if not name.endswith('/native_traces.json'):continue
        con=sqlite3.connect(packet.path(name.removesuffix('native_traces.json')+'native.db').as_uri()+
                            '?mode=ro&immutable=1',uri=True)
        try:stored=[c.decode(row[0]) for row in con.execute('SELECT payload_json FROM trace_events ORDER BY sequence')]
        finally:con.close()
        c.require(packet.json(name)==stored,'OUTCOME_TRACE_EXPORT_MISMATCH')
        for trace in stored:validator.validate(trace)
        counts[name]=len(stored)
    c.require(counts,'OUTCOME_NO_TRACE_EXPORTS')
    return {'exports':len(counts),'stored_traces':sum(counts.values()),'per_export':counts}
