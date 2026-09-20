"""Narrow per-arm containment. No native, neural, provider, or data imports."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import time

ARMS = ('cas_untrained', 'cas_trained', 'generic_untrained', 'generic_trained', 'rule')
MESSAGE = 'repair cannot open without a durable distinct ^6 round trip'
FAILURE = 'POST_ADMISSION_RUNTIME_FAILURE'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(canonical(value)+b'\n')


def evaluate_case(index, task, actions, case_directory, ops):
    """Operations are injected for pure tests; the runtime supplies frozen ones.

    Only a candidate execute_task exception of the exact registered class and
    message is contained. Reference/admission/verifier/identity/I/O failures are
    outside that catch. No action is repaired, regenerated, or resealed.
    """
    require(type(index) is int and 0 <= index < 72, 'RECOVERY_CASE_INDEX')
    require(type(actions) is dict and set(actions) == set(ARMS), 'RECOVERY_ARM_COVERAGE')
    before = canonical({'task': task, 'actions': actions})
    case_directory = Path(case_directory)
    require(not case_directory.exists(), 'RECOVERY_NEW_CASE_REQUIRED')
    case_directory.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    ops.assert_identity()
    reference = ops.reference_task(deepcopy(task), case_directory/'reference')
    write_new(case_directory/'reference_result.json', reference)
    reference_verdict = ops.verify_reference_task(deepcopy(task), deepcopy(reference))
    write_new(case_directory/'reference_verdict.json', reference_verdict)
    require(reference.get('status') == 'EXECUTED' and reference_verdict.get('task_correct') is True,
            'RECOVERY_REFERENCE_FAILURE')
    reference_seconds = time.monotonic()-started
    rows = {}
    for arm in ARMS:
        ops.assert_identity()
        action = deepcopy(actions[arm])
        directory = case_directory/arm
        arm_started = time.monotonic()
        rejected = ops.admission_error(deepcopy(action), deepcopy(task['public']))
        partial, failure = None, None
        if rejected is not None:
            result = {'status': 'REJECTED', 'action': action, 'failure': rejected,
                      'reserved_policy_units': 0, 'native_runs': 0}
            verdict = ops.verify_task(deepcopy(task), deepcopy(result), deepcopy(reference))
            require(verdict.get('task_correct') is not True, 'RECOVERY_REJECTION_REPORTED_CORRECT')
        else:
            # Do not broaden this try to encompass any verifier or audit check.
            try:
                result = ops.execute_task(deepcopy(task['public']), deepcopy(action), directory/'native')
            except Exception as error:
                if type(error) is not ops.runtime_contract_error or str(error) != MESSAGE:
                    raise
                # The frozen execute_task closes/checks its backend in finally.
                # Independently recheck identities before accepting containment.
                ops.assert_identity()
                partial = ops.partial_work(directory/'native')
                require(type(partial) is dict and partial.get('compute_complete') is False
                        and partial.get('failed_tick_compute') is None
                        and all(type(partial.get(k)) is int and partial[k] >= 0 for k in
                                ('committed_native_runs', 'committed_reserved_policy_units')),
                        'RECOVERY_PARTIAL_WORK_INVALID')
                failure = {'type': type(error).__name__, 'module': type(error).__module__, 'message': str(error)}
                result = {'status': FAILURE, 'selected_action': action, 'failure': failure,
                          'execution_started': True, 'execution_completed': False,
                          'partial_work': partial}
                # Frozen verify_task labels every non-EXECUTED result REJECTED;
                # it must not be called for this post-start execution failure.
                verdict = {'task_correct': False, 'procedure_correct': None, 'binding_correct': None,
                    'dependency_correct': None, 'actual_output_correct': False, 'trace_valid': False,
                    'repair_required': True, 'repair_success': False, 'failure': FAILURE}
            else:
                require(result.get('status') == 'EXECUTED', 'RECOVERY_UNRECOGNIZED_NATIVE_RESULT')
                verdict = ops.verify_task(deepcopy(task), deepcopy(result), deepcopy(reference))
        ops.assert_identity()
        write_new(directory/'execution_result.json', result)
        write_new(directory/'verification.json', verdict)
        row = {'case_index': index, 'arm': arm, 'action': action,
            'execution_status': result['status'], 'failure': failure or result.get('failure'),
            'verification': verdict, 'model_rejection': rejected is not None,
            'wall_seconds': time.monotonic()-arm_started, 'evidence_directory': str(directory),
            'partial_work': partial}
        write_new(directory/'case_receipt.json', row)
        rows[arm] = row
    require(canonical({'task': task, 'actions': actions}) == before, 'RECOVERY_INPUT_MUTATION')
    receipt = {'case_index': index, 'task_id': task['task_id'], 'arms': rows,
        'reference_verification': reference_verdict, 'reference_wall_seconds': reference_seconds,
        'case_wall_seconds': time.monotonic()-started}
    write_new(case_directory/'case_receipt.json', receipt)
    return receipt


def aggregate_cases(cases, total_expected=72):
    require(type(total_expected) is int and total_expected == 72, 'RECOVERY_FIXED_DENOMINATOR')
    require(type(cases) is list and len(cases) == 72 and all(type(c.get('case_index')) is int for c in cases)
            and sorted(c['case_index'] for c in cases) == list(range(72)), 'RECOVERY_CASE_COVERAGE')
    for case in cases:
        require(type(case.get('arms')) is dict and set(case['arms']) == set(ARMS), 'RECOVERY_ARM_COVERAGE')
        for arm, row in case['arms'].items():
            require(row['arm'] == arm and type(row['case_index']) is int
                    and row['case_index'] == case['case_index'], 'RECOVERY_ARM_ATTRIBUTION')
            require(row['execution_status'] in ('EXECUTED', 'REJECTED', FAILURE), 'RECOVERY_STATUS_UNKNOWN')
            require(row['model_rejection'] is (row['execution_status'] == 'REJECTED'), 'RECOVERY_REJECTION_ATTRIBUTION')
            if row['execution_status'] == FAILURE:
                require(row['verification'].get('task_correct') is False and row.get('partial_work') is not None,
                        'RECOVERY_RUNTIME_FAILURE_REPORTED_SUCCESS')
                partial = row['partial_work']
                require(type(partial) is dict and partial.get('compute_complete') is False
                        and partial.get('failed_tick_compute') is None
                        and all(type(partial.get(k)) is int and partial[k] >= 0 for k in
                                ('committed_native_runs', 'committed_reserved_policy_units')),
                        'RECOVERY_PARTIAL_WORK_INVALID')
    results = {}
    fields = ('task_correct', 'procedure_correct', 'binding_correct', 'dependency_correct',
              'actual_output_correct', 'trace_valid')
    for arm in ARMS:
        rows = [case['arms'][arm] for case in cases]
        failures = [row for row in rows if row['execution_status'] == FAILURE]
        counts = {key: sum(row['verification'].get(key) is True for row in rows) for key in fields}
        results[arm] = {'total': 72, **counts, 'task_accuracy': counts['task_correct']/72,
            'model_rejections': sum(row['model_rejection'] is True for row in rows),
            'post_admission_runtime_failures': len(failures),
            'native_executed': sum(row['execution_status'] == 'EXECUTED' for row in rows),
            'committed_native_runs_lower_bound': sum(
                row['partial_work']['committed_native_runs'] if row['partial_work'] is not None
                else row['verification'].get('native_runs', 0) for row in rows),
            'reserved_policy_units_lower_bound': sum(
                row['partial_work']['committed_reserved_policy_units'] if row['partial_work'] is not None
                else row['verification'].get('reserved_policy_units', 0) for row in rows),
            'compute_complete': not failures, 'all_cases_in_denominator': True,
            'boundary': 'Verified successes out of all 72 fixed cases. Runtime failures are not admission rejections; '
                        'their uncommitted failed-tick compute and unverified component metrics remain unknown.'}
    return results
