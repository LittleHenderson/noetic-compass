"""Supplementary diagnostics on a completed, independently stored-audited packet."""
import argparse
from collections import Counter, defaultdict
from hashlib import file_digest, sha256
import importlib.util
import json
from pathlib import Path
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = 'acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0'
JOB = 'cas-meta2-20260906064703-c0d74ffa'
PACKET = ROOT/'records/aws_contrast_v6_001/cloud_artifacts.zip'
AUDIT = ROOT/'records/contrast_stored_audit_v6_001/run_001/stored_audit_receipt.json'
BASE = 'cloud_job/campaign/'
ARMS = ('cas_untrained', 'cas_trained', 'generic_untrained', 'generic_trained', 'rule')


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)()
                    for p in (path, *path.parents)), 'LINK_REFUSED')
    with path.open('rb') as stream:
        return file_digest(stream, 'sha256').hexdigest()


def decode(raw):
    require(len(raw) <= 64*1024**2, 'JSON_SIZE_CEILING')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))
    json.dumps(value, allow_nan=False)
    return value


def named_site_metrics(action, target):
    """Literal named-site diagnostic, not the frozen semantic correctness score."""
    expected = target['program']['procedures']
    candidate_program = action.get('program') if type(action) is dict else None
    candidate = candidate_program.get('procedures', {}) if type(candidate_program) is dict else {}
    if type(candidate) is not dict:
        candidate = {}
    counts = Counter()
    errors = []
    counts['observation_binding_expected'] = 1
    counts['observation_binding_correct'] = int(type(action) is dict and
        type(action.get('binding')) is int and action['binding'] == target['binding'])
    for name, procedure in expected.items():
        actual = candidate.get(name, {})
        actual_steps = actual.get('steps', []) if type(actual) is dict else []
        if type(actual_steps) is not list:
            actual_steps = []
        for index, step in enumerate(procedure['steps']):
            actual_step = actual_steps[index] if index < len(actual_steps) else None
            if type(actual_step) is not dict:
                actual_step = {}
            same_kind = actual_step.get('kind') == step['kind']
            counts['named_input_sites_expected'] += 1
            input_match = same_kind and actual_step.get('input') == step['input']
            counts['named_input_sites_correct'] += int(input_match)
            if not input_match:
                errors.append({'procedure': name, 'step': index, 'field': 'input',
                    'expected': step['input'], 'actual': actual_step.get('input'),
                    'kind_matches': same_kind})
            if step['kind'] == 'CALL':
                counts['named_child_sites_expected'] += 1
                child_match = same_kind and actual_step.get('procedure') == step['procedure']
                counts['named_child_sites_correct'] += int(child_match)
                if not child_match:
                    errors.append({'procedure': name, 'step': index, 'field': 'child',
                        'expected': step['procedure'], 'actual': actual_step.get('procedure'),
                        'kind_matches': same_kind})
    for key in ('named_input_sites_correct', 'named_child_sites_correct', 'named_child_sites_expected'):
        counts.setdefault(key, 0)
    return {'counts': dict(counts), 'errors': errors}


def frozen_differences():
    path = ROOT/'records/first_transition_review_v5_001/run.py'
    repo = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=ROOT, text=True).strip())
    raw = subprocess.check_output(['git', 'cat-file', 'blob',
        SOURCE+':'+path.relative_to(repo).as_posix()], cwd=repo)
    require(digest(path) == sha256(raw).hexdigest(), 'FROZEN_DIAGNOSTIC_SOURCE_CHANGED')
    spec = importlib.util.spec_from_file_location('frozen_transition_diagnostics', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(module.self_checks() == 11, 'FROZEN_DIAGNOSTIC_SELF_CHECK_FAILED')
    return module, sha256(raw).hexdigest()


def report(packet_sha, audit_sha):
    require(all(type(x) is str and len(x) == 64 and all(c in '0123456789abcdef' for c in x)
                for x in (packet_sha, audit_sha)), 'EXTERNAL_SHA256_REQUIRED')
    require(digest(PACKET) == packet_sha and digest(AUDIT) == audit_sha, 'EXTERNAL_DIGEST_MISMATCH')
    audit = decode(AUDIT.read_bytes())
    require(audit.get('schema') == 'cas-meta2-contrast-stored-audit/6'
            and audit.get('status') == 'STORED_CONTRAST_AUDIT_PASSED'
            and audit.get('completed') is True and audit.get('errors') == []
            and audit.get('job') == JOB and audit.get('source_sha') == SOURCE
            and audit.get('packet_sha256') == packet_sha, 'SUCCESSFUL_BOUND_STORED_AUDIT_REQUIRED')
    old, old_sha = frozen_differences()
    rows, summaries, inputs = [], defaultdict(Counter), {}
    with zipfile.ZipFile(PACKET) as archive:
        def read(name):
            info = archive.getinfo(name)
            require(info.file_size <= 64*1024**2, 'MEMBER_SIZE_CEILING')
            raw = archive.read(name)
            inputs[name] = sha256(raw).hexdigest()
            return decode(raw)
        tasks = read(BASE+'dataset/test_private.json')
        cases = read(BASE+'native/evaluation_results.json')['cases']
        audited = audit['outcomes']['cases']
        require(len(tasks) == len(cases) == len(audited) == 72, 'CASE_COVERAGE_CHANGED')
        for index, (task, case, checked) in enumerate(zip(tasks, cases, audited, strict=True)):
            require(task['task_id'] == case['task_id'] == checked['task_id']
                    and checked['case_index'] == index and set(case['arms']) == set(ARMS), 'CASE_MAPPING_CHANGED')
            rule = case['arms']['rule']
            require(rule['verification']['task_correct'] is True and rule['action'] == task['target'],
                    'CORRECT_RULE_REFERENCE_REQUIRED')
            prefix = BASE+f'native/evaluation/case_{index:04d}/'
            gold = old.normalize(read(prefix+'rule/native/composition_events.json'))
            for arm in ARMS:
                result = case['arms'][arm]
                correct = result['verification']['task_correct']
                require(type(correct) is bool and correct == checked['arms'][arm]['task_correct'],
                        'AUDITED_TASK_VERDICT_CHANGED')
                row = {'case_index': index, 'task_id': task['task_id'], 'arm': arm,
                    'depth': task['provenance']['depth'], 'condition': task['contrast_side'],
                    'task_correct': correct, 'execution_status': result['execution_status'],
                    'named_site_diagnostic': named_site_metrics(result['action'], task['target'])}
                if not correct:
                    if result['execution_status'] == 'REJECTED':
                        row.update(first_observed_boundary='pre_execution_rejection',
                                   generation_reason=(result['action'].get('reason')
                                       if type(result['action']) is dict else None), failure=result.get('failure'))
                    else:
                        require(result['execution_status'] == 'EXECUTED', 'UNKNOWN_EXECUTION_STATUS')
                        events = old.normalize(read(prefix+arm+'/native/composition_events.json'))
                        difference = old.first_difference(events, gold)
                        row.update(first_observed_difference=difference,
                            first_observed_boundary='recorded_trajectory_divergence' if difference else
                            'unresolved_no_difference_in_selected_fields')
                keys = (arm+'/all', arm+'/depth/'+str(row['depth']), arm+'/condition/'+row['condition'])
                for key in keys:
                    summaries[key]['attempted'] += 1
                    summaries[key]['correct'] += int(correct)
                    summaries[key].update(row['named_site_diagnostic']['counts'])
                    if not correct:
                        summaries[key][row['first_observed_boundary']] += 1
                        difference = row.get('first_observed_difference')
                        if difference:
                            for category in difference['categories']:
                                summaries[key]['first_difference/'+category] += 1
                rows.append(row)
    require(digest(PACKET) == packet_sha and digest(AUDIT) == audit_sha, 'INPUT_CHANGED_DURING_REPORT')
    return {'schema': 'cas-meta2-contrast-error-report/6', 'job': JOB, 'source_sha': SOURCE,
        'packet_sha256': packet_sha, 'stored_audit_sha256': audit_sha, 'script_sha256': digest(__file__),
        'frozen_diagnostic_sha256': old_sha, 'input_members_sha256': inputs, 'cases': rows,
        'summaries': dict(sorted(summaries.items())), 'neural_execution': False,
        'learning_accepted': False,
        'boundary': 'Task correctness comes from the unchanged verifier and completed stored audit. '
                    'Named-site input/child scores compare literal procedure names and step positions from the problem; '
                    'they are supplementary and can penalize semantically equivalent renaming. Missing sites count wrong. '
                    'First recorded divergence is not proof of the earliest neural decision or causal root cause. '
                    'Rejected programs have no executed trajectory. First-divergence categories can overlap. '
                    'Test tasks comprise 24 related triplets, not 72 independent program structures.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--packet-sha256', required=True)
    parser.add_argument('--audit-sha256', required=True)
    args = parser.parse_args()
    output = HERE/'receipt.json'
    require(not output.exists(), 'NEW_REPORT_RECEIPT_REQUIRED')
    result = report(args.packet_sha256, args.audit_sha256)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'case_rows': len(result['cases']), 'summaries': result['summaries']}, indent=2))
