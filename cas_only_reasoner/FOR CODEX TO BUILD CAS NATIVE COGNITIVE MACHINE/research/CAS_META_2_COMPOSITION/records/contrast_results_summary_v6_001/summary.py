"""Bound final contrast-v6 result report. Standard library only; no neural work."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sys
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = 'cloud_job/campaign/'
ARMS = ('cas_untrained', 'cas_trained', 'generic_untrained', 'generic_trained', 'rule')
FIELDS = ('task_correct', 'procedure_correct', 'binding_correct', 'dependency_correct', 'actual_output_correct', 'trace_valid')
EXCLUSIONS = ROOT/'records/contrast_v6_exclusions_001/inventory.json'
EXCLUSIONS_SHA = '1a8f7f39bee35f14ef002dfe90f2c6760cbe5c70436c7606fad32ee03f4c1256'
HISTORY = {
    'familiar_fit': (ROOT/'records/fit_packet_review_v5_001/receipt.json',
        '8da83bbd2f931c9a1735cb255104a88560bab221b37db8354447c3888bcaf0b4'),
    'earlier_composition': (ROOT/'records/aws_ablation_v4_stored_audit_002/stored_audit_receipt.json',
        '3dc89119685d6c83ee33bc65019f8ea98ad58f6307613d77d1e95ba8e2502580')}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(path):
    path = Path(path).absolute()
    require(path.is_file() and not any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)()
            for p in (path, *path.parents)), 'REGULAR_UNLINKED_INPUT_REQUIRED')
    state = sha256()
    with path.open('rb') as stream:
        for raw in iter(lambda: stream.read(1024**2), b''):
            state.update(raw)
    return state.hexdigest()


def decode(raw):
    require(len(raw) <= 64*1024**2, 'JSON_SIZE_CEILING')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    result = json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))
    canonical(result)
    return result


def checked(path, checksum):
    require(type(checksum) is str and re.fullmatch('[a-f0-9]{64}', checksum), 'EXTERNAL_SHA256_REQUIRED')
    require(digest(path) == checksum, 'EXTERNAL_HASH_MISMATCH')
    require(Path(path).stat().st_size <= 64*1024**2, 'JSON_SIZE_CEILING')
    return decode(Path(path).read_bytes())


def identities(review, audit, diagnostics, *, packet_sha, source_sha, source_hash, job, review_sha, audit_sha):
    require(type(source_sha) is str and re.fullmatch('[a-f0-9]{40}', source_sha)
            and type(source_hash) is str and re.fullmatch('[a-f0-9]{64}', source_hash)
            and type(packet_sha) is str and re.fullmatch('[a-f0-9]{64}', packet_sha)
            and type(job) is str and re.fullmatch('cas-meta2-[0-9]{14}-[a-f0-9]{8}', job), 'EXACT_IDENTITIES_REQUIRED')
    for item in (review, audit, diagnostics):
        require(item.get('packet_sha256') == packet_sha and item.get('source_sha') == source_sha
                and item.get('job') == job and item.get('learning_accepted') is False, 'RECEIPT_IDENTITY_OR_CLAIM_MISMATCH')
    require(review.get('schema') == 'cas-meta2-offline-contrast-review/6'
            and review.get('status') == 'RECORDED_CONTRAST_RECOUNT_PASSED'
            and review.get('neural_execution') is False and review.get('provider_calls') is False
            and review.get('source_and_extraction_rechecked_at_end') is True
            and review.get('source_archive_sha256') == source_hash, 'COMPLETED_BYTE_REVIEW_REQUIRED')
    require(audit.get('schema') == 'cas-meta2-contrast-stored-audit/6'
            and audit.get('status') == 'STORED_CONTRAST_AUDIT_PASSED'
            and audit.get('completed') is True and audit.get('errors') == []
            and audit.get('review_receipt_sha256') == review_sha
            and audit.get('source_archive_sha256') == source_hash
            and audit.get('neural_execution_performed') is False, 'COMPLETED_BOUND_STORED_AUDIT_REQUIRED')
    require(diagnostics.get('schema') == 'cas-meta2-contrast-error-report/6'
            and diagnostics.get('stored_audit_sha256') == audit_sha
            and diagnostics.get('neural_execution') is False, 'BOUND_DIAGNOSTIC_REPORT_REQUIRED')


class Packet:
    """Read only reviewed member bytes from the externally bound ZIP."""
    def __init__(self, archive, review):
        self.archive = archive
        rows = review['inventory']
        self.rows = {row['path']: row for row in rows}
        names = [info.filename for info in archive.infolist() if not info.is_dir()]
        require(len(names) == len(set(names)) == len(rows) == len(self.rows)
                and set(names) == set(self.rows), 'PACKET_INVENTORY_COVERAGE')
        self.read_hashes = {}

    def read(self, name):
        require(name in self.rows, 'UNREVIEWED_PACKET_MEMBER')
        row, info = self.rows[name], self.archive.getinfo(name)
        require(type(row['bytes']) is int and 0 <= row['bytes'] == info.file_size <= 64*1024**2, 'MEMBER_SIZE_CEILING')
        raw = self.archive.read(info)
        require(len(raw) == row['bytes'] and sha256(raw).hexdigest() == row['sha256'], 'PACKET_MEMBER_HASH_CHANGED')
        self.read_hashes[name] = row['sha256']
        return decode(raw)


def split_counts(manifest, splits, excluded):
    require(set(splits) == {'train', 'validation', 'test'}, 'SPLIT_COVERAGE')
    prototype = excluded['origins']['contrast_prototype_seed_926601']
    require(excluded['schema'] == 'cas-meta2-known-exposures/6' and excluded['count'] == 8053
            and prototype['count'] == len(set(prototype['graph_signatures'])) == 256, 'EXCLUSION_INVENTORY_INVALID')
    excluded_graphs = set(excluded['graph_signatures'])
    require(len(excluded['graph_signatures']) == len(excluded_graphs) == 8053, 'EXCLUSION_UNION_COUNT_INVALID')
    require(set(prototype['graph_signatures']) <= excluded_graphs, 'OLD_256_NOT_EXCLUDED')
    counts, known = {}, set()
    for split, tasks in splits.items():
        require(type(tasks) is list and tasks, 'SPLIT_TASKS_REQUIRED')
        depths, groups = Counter(), set()
        for task in tasks:
            require(task['task_id'] not in known and task['provenance']['evaluation_group'] == split
                    and type(task['provenance']['depth']) is int, 'SPLIT_TASK_IDENTITY')
            known.add(task['task_id'])
            depths[str(task['provenance']['depth'])] += 1
            groups.add(task['contrast_group'])
            require(task['provenance']['graph_signature'] not in excluded_graphs, 'EXPOSED_GRAPH_IN_CURRENT_V6')
        counts[split] = {'tasks': len(tasks), 'depths': dict(sorted(depths.items())), 'groups': len(groups)}
        require(counts[split] == manifest['splits'][split], 'ASSEMBLED_SPLIT_MANIFEST_MISMATCH')
    require(counts['train']['tasks'] == 640 and counts['train']['depths'] == {'1': 128, '2': 256, '3': 256}
            and counts['validation']['tasks'] == 96 and counts['validation']['depths'] == {'1': 32, '2': 32, '3': 32}
            and counts['test']['tasks'] == 72 and counts['test']['depths'] == {'3': 48, '4': 24}
            and counts['test']['groups'] == 24, 'REGISTERED_SPLIT_COUNTS_CHANGED')
    return {'assembled': counts, 'old_literal_256_graph_overlap': 0,
        'old_literal_256_used_as_training_examples': False, 'known_excluded_graphs': 8053,
        'test_design': '24 matched triplets: same_depth, wording_shift, deeper_calls; not 72 independent structures',
        'familiar_known_program_test_evaluation_in_v6': False}


def outcomes(tasks, audit, diagnostics):
    cases, rows = audit['outcomes']['cases'], diagnostics['cases']
    require(len(tasks) == len(cases) == 72 and len(rows) == 360, 'ALL_360_OUTCOMES_REQUIRED')
    mapped, groups, supplementary = {}, defaultdict(lambda: defaultdict(Counter)), defaultdict(Counter)
    for row in rows:
        key = (row['case_index'], row['arm'])
        require(type(key[0]) is int and 0 <= key[0] < 72 and key[1] in ARMS and key not in mapped, 'DIAGNOSTIC_CASE_COVERAGE')
        mapped[key] = row
    for index, (task, case) in enumerate(zip(tasks, cases, strict=True)):
        require(type(case['case_index']) is int and case['case_index'] == index and case['task_id'] == task['task_id']
                and set(case['arms']) == set(ARMS), 'AUDIT_CASE_MAPPING')
        depth, condition = task['provenance']['depth'], task['contrast_side']
        require(depth == (4 if condition == 'deeper_calls' else 3)
                and condition in ('same_depth', 'wording_shift', 'deeper_calls'), 'TEST_CONDITION_DEPTH')
        for arm, actual in case['arms'].items():
            require(all(type(actual[k]) is bool for k in (*FIELDS, 'model_rejection'))
                    and all(type(actual[k]) is int and actual[k] >= 0 for k in ('native_runs', 'reserved_policy_units')),
                    'AUDIT_VERDICT_TYPES')
            diag = mapped[index, arm]
            require(diag['task_id'] == task['task_id'] and diag['depth'] == depth and diag['condition'] == condition
                    and type(diag['task_correct']) is bool and diag['task_correct'] == actual['task_correct']
                    and diag['execution_status'] == ('REJECTED' if actual['model_rejection'] else 'EXECUTED'), 'DIAGNOSTIC_AUDIT_MAPPING')
            for name in ('all', 'depth_'+str(depth), condition):
                group = groups[name][arm]
                group['attempted'] += 1
                group.update({k: int(actual[k]) for k in (*FIELDS, 'model_rejection', 'native_runs', 'reserved_policy_units')})
            for name in (arm+'/all', arm+'/depth/'+str(depth), arm+'/condition/'+condition):
                total = supplementary[name]
                total.update(attempted=1, correct=int(actual['task_correct']))
                site = diag['named_site_diagnostic']['counts']
                for prefix in ('observation_binding', 'named_input_sites', 'named_child_sites'):
                    correct, expected = site[prefix+'_correct'], site[prefix+'_expected']
                    require(type(correct) is int and type(expected) is int and 0 <= correct <= expected,
                            'NAMED_SITE_COUNT_INVALID')
                    total.update({prefix+'_correct': correct, prefix+'_expected': expected})
                if not actual['task_correct']:
                    boundary = diag['first_observed_boundary']
                    require(boundary in ('pre_execution_rejection', 'recorded_trajectory_divergence',
                                         'unresolved_no_difference_in_selected_fields'), 'UNKNOWN_DIAGNOSTIC_BOUNDARY')
                    require((boundary == 'pre_execution_rejection') is actual['model_rejection'], 'REJECTION_BOUNDARY_MISMATCH')
                    total[boundary] += 1
                    difference = diag.get('first_observed_difference')
                    if difference:
                        require(boundary == 'recorded_trajectory_divergence', 'WRONG_DIVERGENCE_BOUNDARY')
                        for category in difference['categories']:
                            require(type(category) is str and 0 < len(category) <= 128, 'INVALID_DIVERGENCE_CATEGORY')
                            total['first_difference/'+category] += 1
    require(dict(supplementary) == diagnostics['summaries'], 'DIAGNOSTIC_SUMMARY_RECOUNT_MISMATCH')
    expected = {'all': audit['outcomes']['metrics'], **audit['outcomes']['groups']}
    require(set(expected) == set(groups), 'AUDIT_GROUP_COVERAGE')
    for name, arms in groups.items():
        for arm, group in arms.items():
            saved = expected[name][arm]
            require(saved['total'] == group['attempted'] and all(saved[k] == group[k] for k in
                (*FIELDS, 'model_rejection', 'native_runs', 'reserved_policy_units')), 'AUDIT_GROUP_RECOUNT_MISMATCH')
    return {'native_task_outcomes': {name: dict(arms) for name, arms in groups.items()},
        'diagnostics': dict(supplementary), 'cases_bound': 72, 'arm_choices_bound': 360,
        'diagnostic_boundary': 'Literal procedure-name/step-site comparisons can penalize semantically equivalent renaming; missing sites count wrong. First recorded divergence is not the earliest neural decision or a causal root cause. Categories can overlap. Rejected programs have no executed trajectory.'}


def learning(training, registration, review, inventory):
    gate = review['training_gate']
    require(training.get('schema') == 'cas-meta2-contrast-training/6' and training.get('completed') is True
            and training['history'] == review['history'] and training['optimizer_steps'] == review['optimizer_steps']
            and training['checkpoints'] == gate['checkpoints'] and training['learning_accepted'] is False
            and registration['private_labels_read'] is False and registration['probe_used_for_selection'] is False,
            'TRAINING_REVIEW_MAPPING')
    selected, curves = {}, {'cas': [], 'generic': []}
    for family in ('cas', 'generic'):
        require(training['optimizer_steps'][family] == 8000 and training['completed_epochs'] == 200, 'TRAINING_COMPLETION_CHANGED')
        record = training['checkpoints'][family]['selected']
        require(record['family'] == family and type(record['epoch']) is int and 1 <= record['epoch'] <= 200
                and inventory[BASE+'training/'+record['path']]['sha256'] == record['sha256'], 'SELECTED_CHECKPOINT_IDENTITY')
        selected[family] = record
        for row in training['history']:
            score = row['families'][family]['validation']
            metrics = score['generation']
            require(metrics['overall']['total'] == 96 and set(metrics['by_depth']) == {'1', '2', '3'}
                    and all(metrics['by_depth'][d]['total'] == 32 for d in ('1', '2', '3')), 'VALIDATION_CURVE_DENOMINATORS')
            require(all(type(metrics['by_depth'][d]['joint_correct']) is int
                        and 0 <= metrics['by_depth'][d]['joint_correct'] <= 32 for d in ('1', '2', '3'))
                    and type(metrics['overall']['joint_correct']) is int
                    and metrics['overall']['joint_correct'] == sum(metrics['by_depth'][d]['joint_correct'] for d in ('1', '2', '3')),
                    'VALIDATION_CURVE_COUNTS')
            curves[family].append({'epoch': row['epoch'], 'selected': row['families'][family]['selected'],
                'optimizer_steps': row['optimizer_steps'][family], 'token_cross_entropy': score['token_cross_entropy'],
                'generated_program_binding': metrics})
    return {'selected_checkpoints': selected, 'validation_action_curves': curves,
        'selection_rule': registration['selection_rule'], 'parameter_matching': registration['parameter_matching'],
        'validation_only_selection': True, 'probe_used_for_selection': False,
        'boundary': 'Validation curves score freely generated program/binding choices, not native full-task execution. Checkpoints were selected only on validation. Test outcomes come from initial versus selected checkpoints; the last epoch is not substituted.'}


def money(ledger, launch, *, source_sha, source_hash, job, packet_sha):
    result = {'reservation': None, 'cost_estimate': None, 'aws_invoice': None,
              'boundary': 'Reservations are spending limits, not charges. Estimates are not AWS invoices; no automatic refund.'}
    if ledger is not None:
        require(ledger.get('schema') == 'cas-meta-campaign-budget/2' and ledger.get('owner_task_cap_usd') == '400.00', 'BUDGET_SCHEMA')
        rows = ledger['reservations']
        require(len({r['job'] for r in rows}) == len(rows), 'DUPLICATE_BUDGET_JOB')
        require(all(Decimal(r['reserved_usd']).is_finite() and Decimal(r['reserved_usd']) > 0
                    and r['status'] == 'RESERVED_NO_AUTOMATIC_REFUND' for r in rows), 'BUDGET_RESERVATION_INVALID')
        total = sum((Decimal(r['reserved_usd']) for r in rows), Decimal(0))
        require(total.is_finite() and 0 <= total <= 400 and total == Decimal(ledger['total_reserved_usd'])
                and Decimal(ledger['remaining_unreserved_usd']) == 400-total, 'BUDGET_TOTAL_MISMATCH')
        selected = [r for r in rows if r['job'] == job]
        require(len(selected) == 1 and selected[0]['source_sha'] == source_sha and selected[0]['archive_sha256'] == source_hash
                and selected[0]['status'] == 'RESERVED_NO_AUTOMATIC_REFUND', 'JOB_RESERVATION_MISMATCH')
        result['reservation'] = {'job_reserved_usd': selected[0]['reserved_usd'], 'total_reserved_usd': str(total),
            'cap_usd': '400.00', 'remaining_unreserved_usd': str(400-total), 'ledger_revision': ledger['revision'],
            'recorded_utc': ledger['updated_utc']}
    if launch is not None:
        require(launch['job'] == job and launch['source_sha'] == source_sha and launch['archive_sha256'] == source_hash
                and launch['result']['sha256'] == packet_sha, 'LAUNCH_COST_IDENTITY_MISMATCH')
        if launch.get('cost_estimate') is not None:
            estimate = launch['cost_estimate']
            amount = Decimal(estimate['compute_ebs_ipv4_usd_estimate'])
            seconds = estimate['instance_wall_clock_seconds_upper_observation']
            require(amount.is_finite() and amount >= 0 and type(seconds) in (int, float) and math.isfinite(seconds)
                    and seconds >= 0 and type(estimate['excluded']) is str, 'COST_ESTIMATE_INVALID')
            result['cost_estimate'] = estimate
        result['recorded_termination_confirmed'] = launch.get('termination_confirmed') is True
        result['recorded_cleanup_errors'] = launch.get('cleanup_errors')
    return result


def historical():
    fit, old = (checked(*HISTORY[name]) for name in ('familiar_fit', 'earlier_composition'))
    require(fit['status'] == 'RECORDED_FIT_RECOUNT_PASSED' and fit['fresh_held_out_evaluation'] is False
            and all(fit['recount']['final_generation'][f]['overall']['joint_correct'] == 24
                    and fit['recount']['final_generation'][f]['overall']['total'] == 24 for f in ('cas', 'generic')), 'HISTORICAL_FIT_CHANGED')
    require(old['status'] == 'STORED_COMPARISON_AUDIT_PASSED' and old['completed'] is True and old['errors'] == []
            and all(old['modes'][mode]['metrics'][arm]['task_correct'] == score
                for mode in ('v3', 'viability_v4') for arm, score in [('cas_trained', 0), ('generic_trained', 12), ('rule', 72)]),
            'HISTORICAL_NEGATIVE_CHANGED')
    return {'familiar_fit': {'cas': '24/24', 'generic': '24/24', 'native_full_task_metric': False,
        'meaning': 'Familiar-example program/binding fit, not fresh generalization or native task correctness.'},
        'earlier_composition': {'cas_trained': '0/72', 'generic_trained': '12/72', 'rule': '72/72',
        'meaning': 'Earlier retrospective native task outcomes, retained unchanged; not pooled with current v6.'},
        'references': {k: {'path': str(p), 'sha256': h} for k, (p, h) in HISTORY.items()}}


def markdown(result):
    out = ['# CASformer contrast v6: verified results', '',
        'These are native task outcomes from the initial and validation-selected checkpoints. No model is automatically accepted.', '',
        '## Actual assembled data', '', '| Split | Attempts | By depth |', '| --- | ---: | --- |']
    for split, row in result['dataset']['assembled'].items():
        out.append(f"| {split} | {row['tasks']} | "+', '.join(f"depth {d}: {n}" for d, n in row['depths'].items())+' |')
    out += ['', 'The test has 24 matched triplets, not 72 independent structures. The old literal 256 prototype tasks are excluded from every current split. V6 has no separate familiar-known-program test evaluation.', '',
        '## Native full-task correctness', '', '| Group | CAS before → after | Generic before → after | Rule |', '| --- | ---: | ---: | ---: |']
    native = result['outcomes']['native_task_outcomes']
    def fraction(row, field='task_correct'):
        return f"{row[field]}/{row['attempted']}"
    for name in ('all', 'depth_3', 'depth_4', 'same_depth', 'wording_shift', 'deeper_calls'):
        arms = native[name]
        out.append(f"| {name} | {fraction(arms['cas_untrained'])} → {fraction(arms['cas_trained'])} | "
                   f"{fraction(arms['generic_untrained'])} → {fraction(arms['generic_trained'])} | {fraction(arms['rule'])} |")
    out += ['', 'Every attempted task stays in the denominator, including rejected programs. A valid trace is not a correct answer.', '',
        '## Selection and validation', '', result['learning']['boundary'], '']
    for family, checkpoint in result['learning']['selected_checkpoints'].items():
        out.append(f"- {family}: selected epoch {checkpoint['epoch']}; SHA-256 `{checkpoint['sha256']}`.")
    out += ['', '| Epoch | CAS validation program+binding | Generic validation program+binding |', '| --- | ---: | ---: |']
    curves = result['learning']['validation_action_curves']
    for cas, generic in zip(curves['cas'], curves['generic'], strict=True):
        c, g = cas['generated_program_binding']['overall'], generic['generated_program_binding']['overall']
        out.append(f"| {cas['epoch']} | {c['joint_correct']}/{c['total']} | {g['joint_correct']}/{g['total']} |")
    out += ['', 'The JSON companion retains every per-depth validation curve. These rows are action scores, not native task learning curves.', '',
        '## Binding and first recorded errors', '', '| Arm | Native binding | Literal observation binding | Literal input sites | Literal child sites |', '| --- | ---: | ---: | ---: | ---: |']
    for arm in ARMS:
        diag = result['outcomes']['diagnostics'][arm+'/all']
        def site(prefix):
            return f"{diag[prefix+'_correct']}/{diag[prefix+'_expected']}"
        out.append(f"| {arm} | {fraction(native['all'][arm], 'binding_correct')} | {site('observation_binding')} | {site('named_input_sites')} | {site('named_child_sites')} |")
    out += ['', result['outcomes']['diagnostic_boundary'], '']
    for arm in ARMS:
        diag = result['outcomes']['diagnostics'][arm+'/all']
        parts = [f"{k}: {v}" for k, v in sorted(diag.items()) if k.startswith('first_difference/') or
                 k in ('pre_execution_rejection', 'recorded_trajectory_divergence', 'unresolved_no_difference_in_selected_fields')]
        out.append(f"- {arm}: "+('; '.join(parts) if parts else 'no incorrect task')+'.')
    compute = result['compute']
    out += ['', '## GPU, compute, and budget', '',
        f"GPU: {compute['runtime']['gpu']}; PyTorch {compute['runtime']['torch']}; CUDA {compute['runtime']['cuda']}. "
        f"Campaign wall time: {compute['campaign_wall_seconds']:.3f}s; training worker: {compute['training_wall_seconds']:.3f}s; native evaluation: {compute['native_wall_seconds']:.3f}s.",
        f"Recorded training-step seconds: CAS {compute['training_step_seconds']['cas']:.3f}s; generic {compute['training_step_seconds']['generic']:.3f}s. "
        f"Optimizer steps: {compute['optimizer_steps']}. These intervals overlap or nest and must not be added as a bill.", '']
    budget = result['budget']
    if budget['reservation']:
        r = budget['reservation']
        out.append(f"Reserved: ${r['job_reserved_usd']} for this job; ${r['total_reserved_usd']} of ${r['cap_usd']} total; ${r['remaining_unreserved_usd']} unreserved at ledger revision {r['ledger_revision']}.")
    else:
        out.append('Budget reservation: not supplied to this report; not assumed zero.')
    if budget['cost_estimate']:
        e = budget['cost_estimate']
        out.append(f"Compute/disk/IP estimate: ${e['compute_ebs_ipv4_usd_estimate']}. Exclusions: {e['excluded']}.")
    else:
        out.append('Cost estimate: not supplied to this report; not assumed zero.')
    out += ['AWS invoice: not available in this report. No automatic refund.', '',
        '## Earlier evidence stays separate', '',
        '- Familiar fit: CAS and generic each reached 24/24 on known examples. This was program/binding fit, not native task correctness or generalization.',
        '- Earlier composition: CAS 0/72, generic 12/72, rule 72/72. The negative result is unchanged and is not pooled with v6.', '']
    for name, reference in result['historical']['references'].items():
        out.append(f"- [{name}](<{reference['path']}>), SHA-256 `{reference['sha256']}`.")
    out += ['', f"Source `{result['source_sha']}`; job `{result['job']}`; packet SHA-256 `{result['packet_sha256']}`.",
        'The accepted executor, verifier, permissions, and baseline weights stay unchanged. No CAS-specific advantage, general reasoning, production readiness, or complete CNCM claim is made.', '']
    return '\n'.join(out)


def generate(*, review, review_sha256, audit, audit_sha256, diagnostics, diagnostics_sha256,
             packet, packet_sha256, source_sha, source_sha256, job, output,
             ledger=None, ledger_sha256=None, launch=None, launch_sha256=None):
    inputs = {str(Path(p).absolute()): h for p, h in [(review, review_sha256), (audit, audit_sha256),
        (diagnostics, diagnostics_sha256), (packet, packet_sha256), (EXCLUSIONS, EXCLUSIONS_SHA)]}
    rv, av, dv = checked(review, review_sha256), checked(audit, audit_sha256), checked(diagnostics, diagnostics_sha256)
    identities(rv, av, dv, packet_sha=packet_sha256, source_sha=source_sha, source_hash=source_sha256,
               job=job, review_sha=review_sha256, audit_sha=audit_sha256)
    require(digest(packet) == packet_sha256, 'PACKET_SHA256_MISMATCH')
    excluded = checked(EXCLUSIONS, EXCLUSIONS_SHA)
    budget_values = {}
    for name, path, checksum in (('ledger', ledger, ledger_sha256), ('launch', launch, launch_sha256)):
        require((path is None) is (checksum is None), 'OPTIONAL_RECEIPT_HASH_REQUIRED')
        budget_values[name] = checked(path, checksum) if path else None
        if path:
            inputs[str(Path(path).absolute())] = checksum
    with zipfile.ZipFile(packet) as archive:
        reader = Packet(archive, rv)
        manifest = reader.read(BASE+'dataset/manifest.json')
        splits = {name: reader.read(BASE+'dataset/'+file) for name, file in
            [('train', 'train.json'), ('validation', 'validation.json'), ('test', 'test_private.json')]}
        for name, file in [('train', 'train.json'), ('validation', 'validation.json'), ('test', 'test_private.json')]:
            require(reader.read_hashes[BASE+'dataset/'+file] == manifest['sha256'][file], 'DATASET_MEMBER_MANIFEST_MISMATCH')
        training, registration = reader.read(BASE+'training/training_receipt.json'), reader.read(BASE+'training/registration.json')
        campaign, native = reader.read(BASE+'campaign_receipt.json'), reader.read(BASE+'native/native_receipt.json')
        require(reader.read_hashes[BASE+'training/training_receipt.json'] == rv['training_gate']['training_receipt_sha256']
                and reader.read_hashes[BASE+'training/registration.json'] == rv['training_gate']['registration_sha256'], 'TRAINING_INPUT_BINDING')
        require(campaign['completed'] is True and campaign['job'] == job and native['completed'] is True
                and training['job'] == job and registration['job'] == job, 'COMPLETED_PACKET_REQUIRED')
        require(campaign['baseline_before']['source'] == {
            'baseline_sha': '0917267b1354e5d036263eaa6ba9a7197eafb776', 'files_verified': 316}, 'ACCEPTED_BASELINE_IDENTITY_CHANGED')
        result = {'schema': 'cas-meta2-contrast-final-summary/6', 'completed': True, 'status': 'BOUND_RESULTS_SUMMARY_CREATED',
            'job': job, 'source_sha': source_sha, 'source_archive_sha256': source_sha256, 'packet_sha256': packet_sha256,
            'dataset': split_counts(manifest, splits, excluded), 'outcomes': outcomes(splits['test'], av, dv),
            'learning': learning(training, registration, rv, reader.rows),
            'compute': {'runtime': rv['runtime'], 'training_environment': registration['environment'],
                'training_step_seconds': training['training_step_seconds'], 'prediction_seconds': training['prediction_seconds'],
                'optimizer_steps': training['optimizer_steps'], 'training_wall_seconds': training['wall_seconds'],
                'campaign_wall_seconds': campaign['wall_seconds'], 'native_wall_seconds': native['wall_seconds'],
                'boundary': 'Recorded synchronized step/worker timings, not profiler GPU-active seconds or a provider invoice.'},
            'budget': money(**budget_values, source_sha=source_sha, source_hash=source_sha256, job=job, packet_sha=packet_sha256),
            'historical': historical(), 'input_member_sha256': reader.read_hashes,
            'baseline': campaign['baseline_before']['source'], 'neural_execution': False, 'provider_calls': False,
            'checkpoint_loading': False, 'learning_accepted': False, 'automatic_promotion': False,
            'created_utc': datetime.now(timezone.utc).isoformat(), 'script_sha256': digest(__file__)}
    inputs.update({str(p): h for p, h in HISTORY.values()})
    require(all(digest(p) == h for p, h in inputs.items()), 'SUMMARY_INPUT_CHANGED')
    result['external_inputs_sha256'] = inputs
    path = Path(output).absolute()
    require(not path.exists() and path.resolve().is_relative_to(HERE.resolve())
            and not any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)() for p in (path, *path.parents)), 'NEW_SCOPED_OUTPUT_REQUIRED')
    text = markdown(result)
    path.mkdir(parents=True, exist_ok=False)
    with (path/'summary.json').open('xb') as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode()+b'\n')
    with (path/'RESULTS.md').open('x', encoding='utf-8') as stream:
        stream.write(text)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('review', 'review-sha256', 'audit', 'audit-sha256', 'diagnostics', 'diagnostics-sha256',
                 'packet', 'packet-sha256', 'source-sha', 'source-sha256', 'job', 'output'):
        parser.add_argument('--'+name, required=True)
    for name in ('ledger', 'ledger-sha256', 'launch', 'launch-sha256'):
        parser.add_argument('--'+name)
    result = generate(**vars(parser.parse_args()))
    print(json.dumps({k: result[k] for k in ('status', 'completed', 'job', 'packet_sha256')}))
