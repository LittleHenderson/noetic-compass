"""Offline diagnosis of saved rejected outputs; no token replacement or model call."""
from collections import Counter
from copy import deepcopy
from datetime import datetime,timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
SOURCE='42f9164754312f12850d9b8789c062fa7fb8069f'
ARCHIVE='f9bed05bd582e0796e2c4e78ff0f5174e5e1b6a3f447e5c3eab56ad002d473f9'
PACKET='f28603b7aab07d7d75a06cfa52fb5b802689b8896001fa9f572971c9140c9799'
PARTIAL='bc700054e18dad6de9e2516f441adccdfac0a9ace25a39fd0fce6a0879d37f4f'
EXTRACTION='9bf40771df6dd7f67189d402d6bcfd8e05bd8cd997b71a6825fff21da105ae98'
COMMON='bb13cd57b88beafefd1546f504ee38b8595855430dfc55e5d66ecba8bf4684c7'
ARMS=('cas_untrained','cas_trained','generic_untrained','generic_trained')

def require(ok,why):
    if not ok:raise ValueError(why)

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(raw):return sha256(raw).hexdigest()

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module

def state_view(state):
    machine=state._machine
    current=machine.procedures.get(machine.current,{})
    return {'role':state.role,'current_procedure':machine.current,'last_declared_procedure':machine.last_name,
        'completed_steps_in_current_procedure':len(current.get('steps',[])),
        'instruction_count':machine.instructions,'declared_procedures':list(machine.procedures),
        'pending_forward_calls':sorted(machine.pending_names()),'available_variables':sorted(machine.available),
        'current_scope':current.get('allowed_cjts'),'in_progress_step':deepcopy(machine.step)}

def call_exclusions(state,grammar,codec):
    machine=state._machine;pending=machine.pending_names();scope=set(machine.procedures[machine.current]['allowed_cjts'])
    result={}
    for name in codec.PROCEDURE_NAMES:
        reasons=[]
        if machine.reaches(name,machine.current):reasons.append('WOULD_FORM_CALL_CYCLE')
        if name in machine.procedures:
            if not set(machine.procedures[name]['allowed_cjts'])<=scope:reasons.append('CHILD_SCOPE_EXCEEDS_PARENT')
        else:
            if grammar._ORDER[name]<=grammar._ORDER[machine.last_name]:reasons.append('UNDECLARED_NAME_PASSED_CANONICAL_ORDER')
            if len(machine.procedures)+len(pending|{name})>min(16,state.limits.max_procedures):
                reasons.append('PROCEDURE_CAPACITY_EXHAUSTED')
        result[name]=reasons
    return result

def diagnose_ids(ids,max_length,grammar,viability,codec):
    result={'saved_token_count':len(ids) if type(ids) is list else None,'registered_max_action_length':max_length,
        'token_source':'saved_token_ids','first_invalid_token':None,'first_detected_noncompletable_choice':None,
        'detected_noncompletable_choices':[],'first_empty_mask':None,'neural_cause':None}
    if type(ids) is not list or any(type(i) is not int or not 0<=i<len(codec.ACTION_VOCABULARY) for i in ids):
        result.update(structural_class='MALFORMED_TOKEN_IDS',terminal_cause='ACTION_TOKEN_ID_INVALID')
        return result
    tokens=[codec.ACTION_VOCABULARY[i] for i in ids];result['saved_tokens']=tokens
    state=grammar.GrammarState(max_length=max_length)
    for index,token in enumerate(tokens):
        allowed=state.allowed_tokens();view=state_view(state)
        if token not in allowed:
            result['first_invalid_token']={'token_index_zero_based':index,'token_id':ids[index],'token':token,
                'state_before':view,'allowed_tokens':list(allowed)}
            result.update(structural_class='MALFORMED_OR_DISALLOWED_TOKEN',terminal_cause='TOKEN_NOT_ALLOWED')
            break
        viability_allowed=viability._allowed(state)
        if token not in viability_allowed:
            if token=='PROC' and state.role=='procedure_or_eos' and state._machine.procedures and not state._machine.pending_names():
                cause='PROC_WITH_NO_PENDING_FORWARD_CALL'
            elif token=='CALL' and state.role=='step_kind_or_return':cause='CALL_WITH_NO_LEGAL_TARGET'
            else:raise ValueError('UNEXPECTED_FROZEN_VIABILITY_DISAGREEMENT')
            witness={'token_index_zero_based':index,'token_id':ids[index],'token':token,'cause':cause,
                'state_before':view,'allowed_by_actual_v3_grammar':True,
                'boundary':'First detected structural impossibility among these two proved checks, not a neural-cause claim.'}
            result['detected_noncompletable_choices'].append(witness)
            if result['first_detected_noncompletable_choice'] is None:result['first_detected_noncompletable_choice']=witness
        state=state.advance(token)
        if state.dead_end and result['first_empty_mask'] is None:
            result['first_empty_mask']={'prefix_token_count':index+1,'after_token_index_zero_based':index,
                'after_token':token,'state':state_view(state)}
    else:
        raw_allowed=sorted(grammar._raw_allowed(state._machine,state.limits))
        result.update(all_saved_tokens_allowed_by_actual_v3=True,terminal_state=state_view(state),
            terminal_allowed_tokens=list(state.allowed_tokens()),terminal_raw_allowed_without_token_budget=raw_allowed,
            terminal_completion_error=state.completion_error(),has_eos=codec.EOS_ID in ids)
        if state.complete:
            try:
                action=state.to_action()
                result.update(structural_class='COMPLETE_VALID_TOKEN_SEQUENCE',terminal_cause=None,
                    decoded_action_sha256=codec.canonical_sha256(action))
            except Exception as error:
                result.update(structural_class='COMPLETE_TOKEN_SEQUENCE_SEMANTIC_REJECTION',
                    terminal_cause=str(error),completion_error_type=type(error).__name__)
        elif state.dead_end:
            if len(tokens)>=max_length or (len(tokens)==max_length-1 and raw_allowed and '[EOS]' not in raw_allowed):
                result.update(structural_class='TOKEN_BUDGET_EXHAUSTION_OR_EOS_RESERVATION',
                    terminal_cause='FULL_TOKEN_BUDGET' if len(tokens)>=max_length else 'LAST_POSITION_REQUIRES_EOS')
            else:
                role=state.role
                result.update(structural_class='GRAMMAR_STATE_DEAD_END',terminal_cause={
                    'call_target':'NO_LEGAL_CALL_TARGET','procedure_name':'NO_LEGAL_DECLARATION_NAME',
                    'procedure_or_eos':'NO_DECLARATION_OR_VALID_COMPLETION','allowed_cjt':'EMPTY_COMMON_CJT_SCOPE',
                    'step_kind_or_return':'NO_INSTRUCTION_OR_RETURN_CONTINUATION'}.get(role,'EMPTY_ALLOWED_SET:'+role))
                if role=='call_target':result['callee_exclusions']=call_exclusions(state,grammar,codec)
        else:
            result.update(structural_class='INCOMPLETE_PREFIX_WITH_AVAILABLE_CONTINUATION',terminal_cause='PREFIX_STOPPED_WITH_LEGAL_CONTINUATIONS')
    try:
        codec.ids_to_action(ids,max_length=max_length)
        result['whole_stream_codec_error']=None
    except Exception as error:
        result['whole_stream_codec_error']={'type':type(error).__name__,'message':str(error)}
    result['literal_invalid_token_detected']=result['first_invalid_token'] is not None
    result['boundary']='Replay of saved tokens only. No completion is generated. Incomplete-prefix codec errors do not imply a malformed emitted token.'
    return result

def counts(rows):
    reasons=Counter(row['saved_generation_reason'] for row in rows)
    classes=Counter(row['diagnosis']['structural_class'] for row in rows)
    terminal=Counter(str(row['diagnosis'].get('terminal_cause')) for row in rows)
    first=Counter((row['diagnosis'].get('first_detected_noncompletable_choice') or {}).get('cause','NONE_DETECTED') for row in rows)
    return {'rejected':len(rows),'saved_generation_reasons':dict(reasons),'structural_classes':dict(classes),
        'terminal_causes':dict(terminal),'first_detected_noncompletable_choices':dict(first),
        'all_detected_noncompletable_choice_occurrences':dict(Counter(w['cause'] for row in rows
            for w in row['diagnosis'].get('detected_noncompletable_choices',[]))),
        'malformed_or_disallowed_saved_token_rows':sum(row['diagnosis'].get('literal_invalid_token_detected',False) for row in rows),
        'saved_reason_matches_replay':sum(row['saved_reason_matches_replay'] for row in rows)}

def run(output):
    output=Path(output).resolve();require(output.parent==HERE and not output.exists(),'NEW_OUTPUT_REQUIRED');output.mkdir()
    start=time.monotonic();own={p.name:digest(p.read_bytes()) for p in HERE.glob('*.py')}
    common_path=ROOT/'records/prototype_v7_stored_review_001/common.py'
    require(digest(common_path.read_bytes())==COMMON,'FROZEN_COMMON_CHANGED');c=load('_rejection_common',common_path)
    with c.pure_guard():
        manifest,_=c.source_preflight(ROOT/'records/aws_prototype_v7_source_001',ARCHIVE,SOURCE)
        receipt_path=ROOT/'records/prototype_v7_partial_native_001/run_001/partial_native_receipt.json'
        extraction_path=ROOT/'records/prototype_v7_partial_review_001/extraction_receipt.json'
        c.pin(receipt_path,PARTIAL);c.pin(extraction_path,EXTRACTION)
        accepted=c.decode(receipt_path.read_bytes())
        require(accepted['status']=='PARTIAL_NATIVE_EVIDENCE_CHECKED' and accepted['audit_completed'] is True
            and accepted['packet_sha256']==PACKET and accepted['source_sha']==SOURCE,'PARTIAL_RECEIPT_IDENTITY')
        packet=c.Packet(ROOT/'records/aws_prototype_v7_001/cloud_artifacts.zip',PACKET,
            ROOT/'records/prototype_v7_partial_review_001/extracted_001')
        require(packet.inventory==c.decode(extraction_path.read_bytes())['inventory'],'EXTRACTION_BINDING')
        registration=packet.json(c.BASE+'training/registration.json')
        gate=packet.json(c.BASE+'training_gate.json')
        packet.same_hash(c.BASE+'training/registration.json',gate['registration_sha256'])
        max_length=registration['policy_config']['max_action_length'];require(max_length==256,'REGISTERED_TOKEN_BOUND')
        from cas_meta2 import codec,grammar_v3,grammar_viability_v4
        source_files=('codec.py','grammar_v3.py','grammar_viability_v4.py','ir.py','policy_v3.py')
        helpers={name:manifest['files_sha256'][c.PILOT+'/cas_meta2/'+name] for name in source_files}
        for name,pin in helpers.items():c.pin(ROOT/'cas_meta2'/name,pin)
        predictions=[c.decode(line) for line in packet.raw(c.NATIVE+'predictions.jsonl').splitlines()]
        require(len(predictions)==72 and len(accepted['diagnostics']['rows'])==360,'FIXED_ROWS')
        rows=[]
        for row in accepted['diagnostics']['rows']:
            if row['arm'] not in ARMS or row['execution_status']!='REJECTED':continue
            index,arm=row['case_index'],row['arm'];action=row['action']
            require(action==predictions[index]['actions'][arm],'REJECTED_SAVED_ACTION_CHANGED')
            member=c.NATIVE+f'evaluation/case_{index:04d}/'+arm+'/case_receipt.json'
            saved=packet.json(member)
            require(saved['action']==action and saved['execution_status']=='REJECTED' and saved['model_rejection'] is True,
                'REJECTED_EXECUTION_RECEIPT_CHANGED')
            if type(action) is dict and set(action)=={'status','reason','token_ids'} and action['status']=='REJECTED':
                diagnosis=diagnose_ids(action['token_ids'],max_length,grammar_v3,grammar_viability_v4,codec)
                reason=action['reason'];terminal=diagnosis['structural_class']
                matches=(reason=='GENERATION_GRAMMAR_DEAD_END' and diagnosis.get('first_invalid_token') is None
                    and diagnosis.get('first_empty_mask') is not None) or (
                    reason=='GENERATION_LENGTH_EXHAUSTED:NO_SILENT_TRUNCATION'
                    and terminal=='TOKEN_BUDGET_EXHAUSTION_OR_EOS_RESERVATION') or (
                    reason=='TOKEN_NOT_ALLOWED' and diagnosis.get('first_invalid_token') is not None)
            else:
                # Keep complete rejected actions distinct; no guessed emitted token sequence.
                reason='NO_GENERATOR_REJECTION_WRAPPER'
                diagnosis={'structural_class':'COMPLETE_ACTION_NATIVE_ADMISSION_REJECTION','terminal_cause':saved['failure'],
                    'token_source':'not_recorded','neural_cause':None,'first_invalid_token':None,
                    'first_detected_noncompletable_choice':None,'detected_noncompletable_choices':[]}
                matches=True
            rows.append({'case_index':index,'task_id':row['task_id'],'arm':arm,'depth':row['depth'],'condition':row['condition'],
                'action_sha256':codec.canonical_sha256(action),'saved_generation_reason':reason,
                'saved_evaluator_reason':saved['failure'],'saved_reason_matches_replay':bool(matches),
                'evidence_member':member,'evidence_sha256':packet.inventory[member]['sha256'],'diagnosis':diagnosis})
        require(len(rows)==256 and len({(r['case_index'],r['arm']) for r in rows})==256,'EXACT_REJECTED_ROW_COUNT')
        summaries={}
        for group in ('all','depth_3','depth_4','same_depth','wording_shift','deeper_calls'):
            selected=[row for row in rows if group=='all' or group=='depth_'+str(row['depth']) or group==row['condition']]
            summaries[group]={arm:counts([row for row in selected if row['arm']==arm]) for arm in ARMS}
        result={'schema':'cas-meta2-v7-rejection-diagnosis/1','status':'SAVED_REJECTION_DIAGNOSIS_COMPLETED',
            'diagnosis_completed':True,'job':accepted['job'],'source_sha':SOURCE,'source_archive_sha256':ARCHIVE,
            'packet_sha256':PACKET,'partial_native_receipt_sha256':PARTIAL,'extraction_receipt_sha256':EXTRACTION,
            'registration_sha256':packet.inventory[c.BASE+'training/registration.json']['sha256'],
            'registered_max_action_length':max_length,'source_helpers_sha256':helpers,'analysis_files_sha256':own,
            'rows':rows,'summaries':summaries,'all':counts(rows),'all_four_neural_arms_preserved':True,
            'gold_programs_used_for_diagnosis':False,'new_sequences_or_substituted_actions':False,
            'model_or_tensor_loaded':False,'neural_or_native_execution':False,'provider_calls':False,
            'runtime_or_decoder_changed':False,'campaign_completed':False,'learning_accepted':False,
            'boundary':'Actual v3 prefix replay plus two pre-existing pure v4 impossibility checks as diagnostics only. '
                'The first detected structural impossibility is not necessarily the earliest impossible prefix or causal neural decision. '
                'Terminal incomplete codec streams may contain only grammar-allowed tokens. No corrected action, counterfactual generation, '
                'gold repair, task success, or new learning result is supplied.'}
        packet.verify_all();c.check_source_again(manifest);c.pin(receipt_path,PARTIAL);c.pin(extraction_path,EXTRACTION)
        require(own=={p.name:digest(p.read_bytes()) for p in HERE.glob('*.py')},'DIAGNOSIS_CODE_CHANGED')
        result.update(source_and_evidence_unchanged=True,wall_seconds=time.monotonic()-start,utc=datetime.now(timezone.utc).isoformat())
        path=output/'diagnosis.json'
        with path.open('xb') as stream:stream.write(canonical(result).encode()+b'\n')
        print(canonical({'status':result['status'],'path':str(path),'sha256':digest(path.read_bytes()),'all':result['all']}),flush=True)
    return result

if __name__=='__main__':run(sys.argv[1])
