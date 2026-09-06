"""First observed divergence in already-audited saved trajectories; no models."""
from collections import Counter, defaultdict
from hashlib import file_digest, sha256
import json
from pathlib import Path
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PACKET = ROOT / 'records/aws_ablation_v4_002/cloud_artifacts.zip'
PACKET_SHA = 'c0fbc413ce94a3b192a5b634bfc246dae96d94f3fe01943caacbff83a4e74708'
AUDIT = ROOT / 'records/aws_ablation_v4_stored_audit_002/stored_audit_receipt.json'
AUDIT_SHA = '3dc89119685d6c83ee33bc65019f8ea98ad58f6307613d77d1e95ba8e2502580'
FIELDS = ('kind', 'address', 'procedure', 'input_name', 'output_name',
          'return_name', 'return_to', 'pc', 'child_address', 'cjt_id')


def digest(path):
    with path.open('rb') as stream:
        return file_digest(stream, 'sha256').hexdigest()


def normalize(events):
    """Replace run-specific Effect IDs by the address of their recorded producer."""
    producers, rows = {}, []
    for event in events:
        if event['kind'] == 'CHARGE':
            continue
        row = {key: event[key] for key in FIELDS if key in event}
        for name in ('input_reference', 'reference', 'output_reference'):
            if name not in event:
                continue
            ref = event[name]
            if ref['kind'] == 'effect':
                if name == 'output_reference':
                    producers[ref['effect_id']] = event['address']
                if ref['effect_id'] not in producers:
                    raise ValueError('UNRESOLVED_RECORDED_EFFECT')
                row[name] = {'kind': 'effect', 'producer': producers[ref['effect_id']],
                             'payload_sha256': ref['payload_sha256']}
            else:
                row[name] = ref
        rows.append({'seq': event['seq'], 'event': row})
    return rows


def first_difference(actual, expected):
    for i in range(max(len(actual), len(expected))):
        a = actual[i] if i < len(actual) else None
        e = expected[i] if i < len(expected) else None
        if a is not None and e is not None and a['event'] == e['event']:
            continue
        tags = []
        if a is None:
            tags = ['trajectory_ended_early']
        elif e is None:
            tags = ['extra_recorded_transition']
        else:
            av, ev = a['event'], e['event']
            changed = {k for k in set(av) | set(ev) if av.get(k) != ev.get(k)}
            if 'kind' in changed:
                tags.append('early_return' if av['kind'] == 'RETURN' else 'operation_kind_difference')
            if 'procedure' in changed:
                tags.append('wrong_child_called' if ev.get('address') != 'entry' else 'wrong_entry_procedure')
            if 'cjt_id' in changed:
                tags.append('wrong_cjt_selected')
            if changed & {'input_name', 'input_reference'}:
                tags.append('input_binding_difference')
            if changed & {'return_name', 'reference'}:
                tags.append('returned_value_difference')
            if 'return_to' in changed:
                tags.append('return_continuation_difference')
            if changed & {'pc', 'child_address', 'address'}:
                tags.append('resume_position_difference' if av['kind'] == 'RESUME' else 'control_position_difference')
            if changed & {'output_name', 'output_reference'}:
                tags.append('output_binding_or_value_difference')
            if not tags:
                tags.append('unclassified_recorded_difference')
        return {'position_without_charge_events': i, 'categories': tags,
                'candidate': a, 'successful_rule': e}
    return None


def self_checks():
    row = lambda **kw: {'seq': 1, 'event': kw}
    assert first_difference([row(kind='ENTER')], [row(kind='ENTER')]) is None
    checks = [({'kind':'ENTER','procedure':'bad','address':'entry/0'},
               {'kind':'ENTER','procedure':'good','address':'entry/0'}, 'wrong_child_called'),
              ({'kind':'SUSPEND','input_name':'v0'}, {'kind':'SUSPEND','input_name':'v1'}, 'input_binding_difference'),
              ({'kind':'RETURN','return_name':'v0'}, {'kind':'RETURN','return_name':'v1'}, 'returned_value_difference'),
              ({'kind':'RESUME','pc':1}, {'kind':'RESUME','pc':2}, 'resume_position_difference'),
              ({'kind':'RETURN'}, {'kind':'NATIVE'}, 'early_return'),
              ({'kind':'NATIVE','cjt_id':'A'}, {'kind':'NATIVE','cjt_id':'B'}, 'wrong_cjt_selected')]
    for a, e, tag in checks:
        assert tag in first_difference([row(**a)], [row(**e)])['categories']
    assert first_difference([], [row(kind='ENTER')])['categories'] == ['trajectory_ended_early']
    assert first_difference([row(kind='ENTER')], [])['categories'] == ['extra_recorded_transition']
    def events(identity):
        ref = {'kind':'effect','effect_id':identity,'payload_sha256':'a'*64}
        return [{'seq':0,'kind':'NATIVE','address':'entry/0','output_reference':ref},
                {'seq':1,'kind':'RETURN','address':'entry','reference':ref}]
    assert normalize(events('one')) == normalize(events('two'))
    assert first_difference([row(kind='RETURN', return_to={'pc':1})],
                            [row(kind='RETURN', return_to={'pc':2})])['categories'] == ['return_continuation_difference']
    return 11


def main():
    checks = self_checks()
    assert digest(PACKET) == PACKET_SHA and digest(AUDIT) == AUDIT_SHA
    audit = json.loads(AUDIT.read_bytes())
    assert audit['completed'] is True and audit['errors'] == []
    inputs, rows, summaries = {}, [], {}
    with zipfile.ZipFile(PACKET) as archive:
        def read(name):
            raw = archive.read(name)
            inputs[name] = sha256(raw).hexdigest()
            return json.loads(raw)
        base = 'cloud_job/campaign/'
        tasks = read(base + 'dataset/test_private.json')
        for mode in ('v3', 'viability_v4'):
            cases = read(base + 'prediction/' + mode + '/evaluation_results.json')['cases']
            assert len(tasks) == len(cases) == 72
            counts = defaultdict(Counter)
            for task, case in zip(tasks, cases):
                assert task['task_id'] == case['task_id']
                rule = case['arms']['rule']
                assert rule['verification']['task_correct'] is True
                index = rule['case_index']
                prefix = base + f'prediction/{mode}/evaluation/case_{index:04d}/'
                gold_events = normalize(read(prefix + 'rule/native/composition_events.json'))
                assert rule['action'] == task['target']
                for arm, result in case['arms'].items():
                    verdict = result['verification']
                    correct = verdict['task_correct']
                    assert type(correct) is bool
                    row = {'mode':mode, 'arm':arm, 'task_id':task['task_id'],
                           'depth':task['provenance']['depth'],
                           'family':task['provenance']['evaluation_group'],
                           'task_correct':correct, 'execution_status':result['execution_status']}
                    keys = [arm + '/all', arm + '/depth/' + str(row['depth']), arm + '/family/' + row['family']]
                    for key in keys:
                        counts[key]['attempted'] += 1
                        counts[key]['correct'] += int(correct)
                    if not correct:
                        if result['execution_status'] == 'REJECTED':
                            row['first_observed_boundary'] = 'pre_execution_rejection'
                            row['generation_reason'] = result['action'].get('reason')
                            row['failure'] = result.get('failure')
                        elif result['execution_status'] == 'EXECUTED':
                            events = normalize(read(prefix + arm + '/native/composition_events.json'))
                            row['first_observed_difference'] = first_difference(events, gold_events)
                            row['first_observed_boundary'] = ('recorded_trajectory_divergence' if row['first_observed_difference']
                                                              else 'unresolved_no_difference_in_selected_fields')
                        else:
                            row['first_observed_boundary'] = 'unclassified_execution_status'
                        for key in keys:
                            counts[key][row['first_observed_boundary']] += 1
                    rows.append(row)
            summaries[mode] = dict(sorted(counts.items()))
    assert digest(PACKET) == PACKET_SHA and digest(AUDIT) == AUDIT_SHA
    report = {'schema':'cas-meta2-first-observed-transition/0.1', 'self_checks':checks,
              'packet_sha256':PACKET_SHA, 'stored_audit_sha256':AUDIT_SHA,
              'script_sha256':digest(Path(__file__)), 'inputs_sha256':inputs,
              'summaries':summaries, 'cases':rows, 'neural_execution':False,
              'training':False, 'fresh_held_out_evaluation':False,
              'boundary':'First recorded difference from a task-correct rule trajectory on exposed tasks. '
                         'Not proof of the earliest neural decision, causal root cause, or exhaustive semantic equivalence. '
                         'Charge events excluded. Rejected generations have no executed transition. '
                         'Multiple categories may describe one first divergent event; categories are not forced into one cause.'}
    with (HERE / 'receipt.json').open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'self_checks':checks,'case_rows':len(rows),'summaries':summaries},indent=2))


if __name__ == '__main__':
    main()
