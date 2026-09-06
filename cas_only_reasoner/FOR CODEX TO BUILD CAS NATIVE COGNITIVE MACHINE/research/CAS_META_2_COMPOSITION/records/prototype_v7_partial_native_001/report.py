"""Counts and literal diagnostics for a fixed partial packet, not full acceptance."""
from collections import Counter
from copy import deepcopy

UNFINISHED='UNFINISHED_AT_DEADLINE'
NOT_STARTED='NOT_STARTED_BEFORE_DEADLINE'

def summarize(rows,c):
    c.require(type(rows) is list and rows, 'PARTIAL_REPORT_ROWS')
    statuses=Counter(r['execution_status'] for r in rows)
    allowed={'EXECUTED','REJECTED',c.FAILURE,UNFINISHED,NOT_STARTED}
    c.require(set(statuses)<=allowed,'PARTIAL_REPORT_UNKNOWN_STATUS')
    metrics={}
    for field in c.FIELDS:
        values=[r['verification'][field] for r in rows]
        c.require(all(type(v) is bool or v is None for v in values),'PARTIAL_REPORT_METRIC_TYPE')
        metrics[field]={'correct':sum(v is True for v in values),'incorrect':sum(v is False for v in values),
            'unknown':sum(v is None for v in values),'scheduled':len(rows),
            'attempted':len(rows)-statuses[NOT_STARTED]}
    for row in rows:
        status=row['execution_status']
        if status in (UNFINISHED,NOT_STARTED):
            c.require(all(row['verification'][field] is None for field in c.FIELDS)
                and row['model_rejection'] is False,'PARTIAL_REPORT_MISSING_MUST_BE_UNKNOWN')
        if status=='REJECTED':c.require(row['verification']['task_correct'] is False,'PARTIAL_REPORT_REJECTION_SUCCESS')
    sites,boundaries,categories,run_fields=Counter(),Counter(),Counter(),Counter()
    native_runs=units=0
    for row in rows:
        sites.update(row['named_site_diagnostic']['counts'])
        if row.get('first_observed_boundary'):boundaries[row['first_observed_boundary']]+=1
        if row.get('first_observed_difference'):categories.update(row['first_observed_difference']['categories'])
        if row.get('first_committed_run_disagreement'):run_fields.update(row['first_committed_run_disagreement']['changed_fields'])
        part=row.get('partial_work')
        if part is not None:
            for key in ('committed_native_runs','committed_reserved_policy_units'):
                c.require(type(part[key]) is int and part[key]>=0,'PARTIAL_REPORT_COMPUTE_COUNT')
            c.require(part['compute_complete'] is False,'PARTIAL_REPORT_PREFIX_COMPLETE')
            native_runs+=part['committed_native_runs'];units+=part['committed_reserved_policy_units']
        else:
            for key in ('native_runs','reserved_policy_units'):
                c.require(type(row['verification'].get(key,0)) is int and row['verification'].get(key,0)>=0,
                    'PARTIAL_REPORT_COMPUTE_INTEGER')
            native_runs+=row['verification'].get('native_runs',0)
            units+=row['verification'].get('reserved_policy_units',0)
    return {'scheduled':len(rows),'attempted':len(rows)-statuses[NOT_STARTED],
        'outcomes_recorded':len(rows)-statuses[NOT_STARTED]-statuses[UNFINISHED],
        'correct':metrics['task_correct']['correct'],'incorrect':metrics['task_correct']['incorrect'],
        'unknown':metrics['task_correct']['unknown'],'statuses':dict(statuses),'metrics':metrics,
        'named_site_counts':dict(sites),'first_observed_boundaries':dict(boundaries),
        'complete_trace_first_difference_categories':dict(categories),
        'committed_run_first_difference_fields':dict(run_fields),
        'committed_native_runs_lower_bound':native_runs,'reserved_policy_units_lower_bound':units,
        'compute_complete':not (statuses[c.FAILURE] or statuses[UNFINISHED]),
        'not_started_is_not_a_failed_attempt':True,'unknown_is_not_false':True}

def build(tasks,predictions,cases,helpers,c):
    c.require(len(tasks)==len(predictions)==len(cases)==72,'PARTIAL_REPORT_EXACT_72')
    groups=helpers['outcomes'].groups(tasks,c)
    groups['common_completed_71']=[i for i in range(72) if i!=45]
    rows=[];differences=helpers['differences'];old=helpers['report']
    for index,(task,prediction,case) in enumerate(zip(tasks,predictions,cases,strict=True)):
        c.require(type(case['case_index']) is int and case['case_index']==index and case['task_id']==task['task_id']
            and set(case['arms'])==set(c.ARMS) and set(prediction['actions'])==set(c.ARMS)
            and case['reference_verification']['task_correct'] is True,'PARTIAL_REPORT_CASE_MAPPING')
        # Reference events exist even where the rule arm did not start. This is
        # a private checked reference, never a fabricated rule execution.
        if index==45:
            expected_events=case['reference_composition_events'];expected_runs=case['reference']['rows']
            comparison='independently_checked_private_reference'
        else:
            rule=case['arms']['rule'];c.require(rule['verification']['task_correct'] is True,'PARTIAL_REPORT_RULE_CORRECT')
            expected_events=rule['composition_events'];expected_runs=rule['rows'];comparison='independently_correct_rule'
        gold=differences.normalize(deepcopy(expected_events))
        for arm in c.ARMS:
            item=case['arms'][arm]
            c.require(item['case_index']==index and item['arm']==arm and item['action']==prediction['actions'][arm],
                'PARTIAL_REPORT_ARM_MAPPING')
            status=item['execution_status']
            c.require((status in (UNFINISHED,NOT_STARTED)) == (index==45 and arm in ('generic_trained','rule')),
                'PARTIAL_REPORT_EXACT_UNKNOWN_SLOTS')
            row={**deepcopy(item),'task_id':task['task_id'],'depth':task['provenance']['depth'],
                'condition':task['contrast_side'],'named_site_diagnostic':old.named_site_metrics(item['action'],task['target']),
                'comparison_reference':comparison}
            if status=='REJECTED':
                row['first_observed_boundary']='pre_execution_rejection'
                row['generation_reason']=item['action'].get('reason')
            elif status in (c.FAILURE,UNFINISHED):
                row['first_observed_boundary']='post_admission_runtime_failure' if status==c.FAILURE else 'deadline_unfinished'
                if item.get('partial_work') is not None:
                    diff=old.first_committed_run_difference(item['rows'],expected_runs,c)
                    if diff is not None:
                        diff['comparison_run']=diff.pop('successful_rule')
                        diff['comparison_reference']=comparison
                    row['first_committed_run_disagreement']=diff
                    row['prefix_boundary']='Only available committed RUNs; no missing future event or failed-tick cause is inferred.'
            elif status==NOT_STARTED:row['first_observed_boundary']='not_started_before_deadline'
            elif item['verification']['task_correct'] is False:
                difference=differences.first_difference(differences.normalize(deepcopy(item['composition_events'])),deepcopy(gold))
                row['first_observed_difference']=difference
                row['first_observed_boundary']='recorded_trajectory_divergence' if difference else 'unresolved_no_difference_in_selected_fields'
            rows.append(row)
    summaries={name:{arm:summarize([r for r in rows if r['case_index'] in indices and r['arm']==arm],c)
        for arm in c.ARMS} for name,indices in groups.items()}
    before_after={}
    for group,values in summaries.items():
        before_after[group]={family:{'before':{k:values[family+'_untrained'][k] for k in
            ('scheduled','attempted','outcomes_recorded','correct','incorrect','unknown')},
            'after':{k:values[family+'_trained'][k] for k in
            ('scheduled','attempted','outcomes_recorded','correct','incorrect','unknown')}} for family in ('cas','generic')}
    return {'rows':rows,'summaries':summaries,'before_after':before_after,'scheduled_cases':72,'scheduled_arm_slots':360,
        'boundary':'72 scheduled slots per arm are retained. Rule attempted71; generic trained attempted72 with one unfinished. '
            'Common71 is a separate matched subset, not a replacement denominator. Literal naming/site comparisons can penalize '
            'equivalent renaming. First recorded differences are not proven earliest causal neural decisions. '
            'Related triplets are not72 independent structures.'}
