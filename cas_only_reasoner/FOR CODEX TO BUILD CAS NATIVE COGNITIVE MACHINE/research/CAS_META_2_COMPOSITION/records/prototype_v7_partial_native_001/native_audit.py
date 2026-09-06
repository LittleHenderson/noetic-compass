"""Partial-only audit of saved v7 native results; never a complete-run gate."""
from copy import deepcopy

UNFINISHED = 'UNFINISHED_AT_DEADLINE'
NOT_STARTED = 'NOT_STARTED_BEFORE_DEADLINE'


def audit_arm(packet, task, action, row, path, ref, identity, engine, validator, partial, c):
    index, arm = row['case_index'], row['arm']
    c.require(type(index) is int and 0 <= index < 72 and arm in c.ARMS
        and row['action'] == action and row == packet.json(path+'/case_receipt.json'), 'PARTIAL_ARM_ATTRIBUTION')
    c.require(c.remote_member(row['evidence_directory']) == path, 'PARTIAL_ARM_DIRECTORY')
    c.require(type(row['wall_seconds']) in (int,float) and 0 <= row['wall_seconds'] < float('inf'), 'PARTIAL_ARM_TIME')
    result, verdict = packet.json(path+'/execution_result.json'), packet.json(path+'/verification.json')
    c.require(row['verification'] == verdict and result['status'] == row['execution_status'], 'PARTIAL_ARM_VERDICT_COPY')
    status = row['execution_status']; reason = engine.admission_error(deepcopy(action), deepcopy(task['public']))
    summary = {'case_index':index,'arm':arm,'action':deepcopy(action),'execution_status':status,
        'model_rejection':status=='REJECTED','partial_work':None,'evidence_path':path,
        'outcome_available':True,'complete_trace':False}
    database = None
    if status == 'EXECUTED':
        c.require(reason is None and row['model_rejection'] is False and row['failure'] is None
            and row['partial_work'] is None and result['runtime_identity'] == identity,
            'PARTIAL_EXECUTED_IDENTITY')
        c.require(path+'/native/failure.json' not in packet.inventory, 'PARTIAL_EXECUTED_HAS_FAILURE')
        actual = engine._native(packet,result,path+'/native',task['public'],action)
        derived = engine.candidate_verdict(task,action,actual,ref)
        engine.compare_verdict(verdict,derived)
        database = path+'/native/native.db'
        summary.update(verification=derived, rows=actual['rows'], complete_trace=True,
            composition_events=packet.json(path+'/native/composition_events.json'), return_node=actual['return_node'])
    elif status == 'REJECTED':
        c.require(reason is not None and row['model_rejection'] is True and row['failure'] == reason
            and row['partial_work'] is None and result == {'status':'REJECTED','action':action,
            'failure':reason,'reserved_policy_units':0,'native_runs':0}, 'PARTIAL_REJECTION_IDENTITY')
        c.require(not any(n.startswith(path+'/native/') for n in packet.inventory), 'PARTIAL_REJECTION_NATIVE_WRITES')
        expected = {**{k:False for k in c.FIELDS},'repair_success':None,'repair_required':False,
            'failure':'PREDICTED_PROGRAM_REJECTED'}
        c.require(verdict == expected, 'PARTIAL_REJECTION_VERDICT')
        summary.update(verification={**expected,'native_runs':0,'reserved_policy_units':0},rows=[],composition_events=None)
    elif status == c.FAILURE:
        error = {'type':'RuntimeContractError','module':'cas_cjt.runtime','message':c.MESSAGE}
        c.require(reason is None and row['model_rejection'] is False and row['failure'] == error
            and result == {'status':c.FAILURE,'selected_action':action,'failure':error,
                'execution_started':True,'execution_completed':False,'partial_work':row['partial_work']},
            'PARTIAL_KNOWN_POST_START_ERROR')
        expected = {'task_correct':False,'procedure_correct':None,'binding_correct':None,
            'dependency_correct':None,'actual_output_correct':False,'trace_valid':False,
            'repair_required':True,'repair_success':False,'failure':c.FAILURE}
        c.require(verdict == expected, 'PARTIAL_KNOWN_POST_START_VERDICT')
        checked = partial.audit_prefix(packet,path+'/native',task['public'],action,identity,engine,validator,c)
        observed = row['partial_work']
        c.require(type(observed) is dict and all(observed.get(k)==checked[k]
            and type(observed.get(k)) is type(checked[k]) for k in ('committed_native_runs',
            'committed_reserved_policy_units','failed_tick_compute','compute_complete','database_sha256','evidence_sha256'))
            and observed.get('sqlite_integrity_checked') is True and observed.get('payload_hashes_checked') is True
            and observed.get('stored_trace_semantics_checked') is False
            and observed.get('full_execution_trace_available') is False, 'PARTIAL_KNOWN_PREFIX_RECEIPT')
        database = path+'/native/native.db'
        summary.update(verification=expected,partial_work=checked,rows=checked['rows'],
            composition_events=None,next_sealed_run=checked['next_sealed_run'])
    else:
        c.require(False, 'PARTIAL_UNSUPPORTED_COMPLETED_STATUS')
    return summary, database


def missing_arm(index, arm, action, path, packet, c):
    c.require(type(index) is int and index == 45 and arm in ('generic_trained','rule'), 'PARTIAL_UNEXPECTED_MISSING_ARM')
    actual = {n.removeprefix(path+'/') for n in packet.inventory if n.startswith(path+'/')}
    expected = {'native/native.db','native/native.db-wal','native/native.db-shm'} if arm=='generic_trained' else set()
    c.require(actual == expected, 'PARTIAL_MISSING_ARM_FILES_CHANGED')
    status = UNFINISHED if arm=='generic_trained' else NOT_STARTED
    return {'case_index':index,'arm':arm,'action':deepcopy(action),'execution_status':status,
        'model_rejection':False,'partial_work':None,'verification':{**{k:None for k in c.FIELDS},
            'repair_required':None,'repair_success':None},'rows':[],'composition_events':None,
        'complete_trace':False,'outcome_available':False,'evidence_path':path,
        'retained_files':{n:packet.inventory[path+'/'+n] for n in sorted(actual)},
        'compute_complete':False,'unrecorded_work':None,
        'boundary':'No result or verifier receipt exists. Not a rejection, not the known RuntimeContractError, and not a measured false outcome.'}


def audit(packet, context, engine, validator, helpers, c, identity_check, progress):
    tasks, predictions = context['tasks'], context['predictions']
    helpers['outcomes'].groups(tasks,c)
    c.require(len(predictions)==72, 'PARTIAL_PREDICTION_COUNT')
    record = packet.json(c.NATIVE+'evaluation_partial.json')
    c.require(record['completed'] is False and record['automatic_retry'] is False
        and record['expected']==72 and record['partial_files_retained'] is True
        and type(record['cases']) is list and len(record['cases'])==71, 'PARTIAL_EXACT_INCOMPLETE_RECORD')
    completed = {}
    for case in record['cases']:
        index = case.get('case_index')
        c.require(type(index) is int and index not in completed, 'PARTIAL_DUPLICATE_CASE')
        completed[index] = case
    c.require(set(completed)==set(range(72))-{45}, 'PARTIAL_COMPLETED_CASE_SET')
    c.require(all(c.NATIVE+name not in packet.inventory for name in ('evaluation_results.json','native_receipt.json')),
        'PARTIAL_HAS_CONTRADICTORY_SUCCESS_RECEIPT')
    audited, expected_databases, workers = [], set(), set()
    identity = context['runtime_identity']
    for index,(task,prediction) in enumerate(zip(tasks,predictions,strict=True)):
        progress('case_'+str(index))
        folder = c.NATIVE+f'evaluation/case_{index:04d}/'
        case = completed.get(index)
        if case is not None:
            c.require(case==packet.json(folder+'case_receipt.json') and case['task_id']==task['task_id']
                and set(case['arms'])==set(c.ARMS), 'PARTIAL_COMPLETE_CASE_COPY')
            worker = packet.json(folder+'worker_identity.json'); identity_check(worker); workers.add(worker['pid'])
        else:
            c.require(folder+'case_receipt.json' not in packet.inventory
                and folder+'worker_identity.json' not in packet.inventory, 'PARTIAL_45_FINAL_RECEIPT_PRESENT')
        reference = packet.json(folder+'reference_result.json')
        c.require(reference['runtime_identity']==reference['runtime_identity_after']==identity, 'PARTIAL_REFERENCE_MODEL_IDENTITY')
        ref = engine._native(packet,reference,folder+'reference',task['public'],task['target'],reference=True)
        verdict = engine.reference_verdict(task,ref)
        engine.compare_verdict(packet.json(folder+'reference_verdict.json'),verdict)
        c.require(verdict['task_correct'] is True, 'PARTIAL_REFERENCE_NOT_CORRECT')
        if case is not None:
            c.require(case['reference_verification']==packet.json(folder+'reference_verdict.json'), 'PARTIAL_REFERENCE_COPY')
        expected_databases.add(folder+'reference/native.db')
        arms = {}
        for arm in c.ARMS:
            path = folder+arm; action = prediction['actions'][arm]
            if index==45 and arm in ('generic_trained','rule'):
                arms[arm]=missing_arm(index,arm,action,path,packet,c)
                if arm=='generic_trained': expected_databases.add(path+'/native/native.db')
                continue
            row = packet.json(path+'/case_receipt.json')
            c.require(type(row['case_index']) is int and row['case_index']==index and row['arm']==arm,
                'PARTIAL_ROW_INDEX_OR_ARM')
            if case is not None: c.require(row==case['arms'][arm], 'PARTIAL_OUTER_ARM_COPY')
            arms[arm], db = audit_arm(packet,task,action,row,path,ref,identity,engine,validator,helpers['partial'],c)
            if db is not None: expected_databases.add(db)
        if index != 45:
            c.require(arms['rule']['action']==task['target'] and arms['rule']['verification']['task_correct'] is True,
                'PARTIAL_CORRECT_COMPLETED_RULE')
        else:
            c.require(arms['rule']['action']==task['target'], 'PARTIAL_UNSTARTED_RULE_CHOICE')
        audited.append({'case_index':index,'task_id':task['task_id'],'arms':arms,'reference':ref,
            'reference_verification':verdict,'reference_composition_events':packet.json(folder+'reference/composition_events.json'),
            'worker_final_identity_available':index!=45})
    actual = {n for n in packet.inventory if n.startswith(c.NATIVE+'evaluation/') and n.endswith('/native.db')}
    c.require(actual==expected_databases, 'PARTIAL_UNACCOUNTED_DATABASE')
    c.require(len(workers)==8, 'PARTIAL_COMPLETED_WORKER_COUNT')
    return {'cases':audited,'references_checked':72,'completed_case_receipts':71,'saved_arm_outcomes_checked':358,
        'missing_arm_outcomes':2,'registered_arm_denominator':360,'registered_cases_per_arm':72,
        'native_databases_in_inventory':len(expected_databases),'timeout_wal_database_semantics_checked_here':False,
        'runtime_identity':identity,'worker_pids':sorted(workers),'missing_final_worker_identity_cases':[45]}
