"""Post-run, pure-data diagnosis. No model loading, inference, or execution.

Reads completed saved records only. This is not an acceptance auditor. Exact
prefix comparisons use stored targets after the experiment has finished; they
must never be fed back to the evaluated checkpoint or used as new holdouts.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import statistics
import sys
import zipfile


class NoNeuralImports:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch', 'tensorflow', 'jax', 'cupy', 'boto3', 'cas_cjt'}:
            raise RuntimeError('NEURAL_OR_PROVIDER_IMPORT_FORBIDDEN:' + fullname)


sys.meta_path.insert(0, NoNeuralImports())
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from cas_meta2.codec import ACTION_VOCABULARY, action_to_tokens


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def tokens(action):
    if 'token_ids' in action:
        return [ACTION_VOCABULARY[n] for n in action['token_ids']]
    return action_to_tokens(action)


def gold_roles(action):
    roles = ['bos', 'observation_binding']
    for name, p in sorted(action['program']['procedures'].items(), key=lambda x: (x[0] != 'main', x[0])):
        roles += ['proc_marker', 'procedure_name', 'allow_marker']
        roles += ['allowed_cjt'] * len(p['allowed_cjts'])
        roles += ['endallow_marker']
        for step in p['steps']:
            roles += ['step_kind', 'call_target' if step['kind'] == 'CALL' else 'run_cjt',
                      'step_input', 'step_output']
        roles += ['return_marker', 'return_value', 'endproc_marker']
    roles += ['eos']
    assert len(roles) == len(action_to_tokens(action))
    return roles


def parse_blocks(sequence):
    """Diagnostic syntax walk only: preserves duplicates; never admits an action."""
    blocks = []
    i = 2
    try:
        while sequence[i] != '[EOS]':
            assert sequence[i] == 'PROC' and sequence[i + 2] == 'ALLOW'
            name = sequence[i + 1]
            i += 3
            while sequence[i] != 'ENDALLOW':
                i += 1
            i += 1
            steps = []
            while sequence[i] in ('RUN', 'CALL'):
                steps.append(tuple(sequence[i:i + 4]))
                assert len(steps[-1]) == 4
                i += 4
            assert sequence[i] == 'RETURN' and sequence[i + 2] == 'ENDPROC'
            blocks.append({'name': name, 'steps': steps, 'return': sequence[i + 1]})
            i += 3
        assert i == len(sequence) - 1
        return blocks
    except (IndexError, AssertionError):
        return None


def differences(action, target):
    actual, expected = tokens(action), tokens(target)
    prefix = next((i for i, pair in enumerate(zip(actual, expected)) if pair[0] != pair[1]),
                  min(len(actual), len(expected)))
    exact = actual == expected
    result = {'exact': exact, 'predicted_tokens': len(actual), 'target_tokens': len(expected),
              'matching_prefix': prefix,
              'first_error_role': None if exact else gold_roles(target)[prefix] if prefix < len(expected) else 'trailing_data',
              'binding_token_correct': len(actual) > 1 and actual[1] == expected[1]}
    blocks, wanted = parse_blocks(actual), parse_blocks(expected)
    result['syntax_walk_complete'] = blocks is not None
    if blocks is None:
        return result
    names = [b['name'] for b in blocks]
    result['duplicate_declarations'] = len(names) != len(set(names))
    result['missing_call_targets'] = sorted({s[1] for b in blocks for s in b['steps']
                                             if s[0] == 'CALL'} - set(names))
    result['exact_declared_name_sequence'] = names == [b['name'] for b in wanted]
    result['exact_declared_name_set'] = set(names) == {b['name'] for b in wanted}
    result['number_of_blocks_correct'] = len(blocks) == len(wanted)
    result['exact_block_content_by_name'] = []
    result['field_differences'] = []
    if len(names) == len(set(names)):
        mapping = {b['name']: b for b in blocks}
        for want in wanted:
            have = mapping.get(want['name'])
            if have is None:
                result['field_differences'].append('missing_procedure')
                continue
            result['exact_block_content_by_name'].append(have == want)
            if have['return'] != want['return']:
                result['field_differences'].append('return_value')
            if len(have['steps']) != len(want['steps']):
                result['field_differences'].append('step_count')
            for a, b in zip(have['steps'], want['steps']):
                for j, role in enumerate(('step_kind', 'step_target', 'step_input', 'step_output')):
                    if a[j] != b[j]:
                        result['field_differences'].append(role)
    return result


def summarize(actions, tasks):
    rows = [differences(action, task['target']) for action, task in zip(actions, tasks, strict=True)]
    result = {'count': len(rows), 'exact_action': sum(r['exact'] for r in rows),
              'first_error_roles': dict(Counter(r['first_error_role'] for r in rows if not r['exact'])),
              'reported_generation_reasons': dict(Counter(a.get('reason', 'DECODED_ACTION') for a in actions)),
              'median_matching_prefix': statistics.median(r['matching_prefix'] for r in rows),
              'predicted_length_range': [min(r['predicted_tokens'] for r in rows), max(r['predicted_tokens'] for r in rows)],
              'target_length_range': [min(r['target_tokens'] for r in rows), max(r['target_tokens'] for r in rows)],
              'field_differences_among_unique_declarations': dict(Counter(k for r in rows for k in r.get('field_differences', [])))}
    for key in ('binding_token_correct', 'syntax_walk_complete', 'duplicate_declarations',
                'exact_declared_name_sequence', 'exact_declared_name_set', 'number_of_blocks_correct'):
        result[key] = sum(bool(r.get(key)) for r in rows)
    result['missing_call_targets'] = sum(bool(r.get('missing_call_targets')) for r in rows)
    return result, rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('REFUSING_EXISTING_OUTPUT')
    if args.output.resolve().parent != Path(__file__).resolve().parent:
        raise SystemExit('OUTPUT_MUST_STAY_IN_THIS_DIAGNOSIS_DIRECTORY')
    members = {}
    with zipfile.ZipFile(args.packet) as z:
        def read(name, lines=False):
            path = 'cloud_job/campaign/' + name
            raw = z.read(path)
            members[path] = {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}
            return [json.loads(line) for line in raw.splitlines()] if lines else json.loads(raw)
        campaign = read('campaign_receipt.json')
        if campaign.get('completed') is not True:
            raise SystemExit('CAMPAIGN_NOT_FINISHED')
        training = read('training_receipt.json')
        seal = read('predictions_seal.json')
        predictions = read('predictions.jsonl', True)
        evaluation = read('evaluation_results.json')
        validation = read('dataset/validation.json')
        test = read('dataset/test_private.json')
        history = read('training_history.json')
        preflight = read('gpu_preflight_v2.json')
        external = {}
        for label, relative in (
            ('inspection', 'records/aws_learning_v2_001_inspection/inspection_receipt.json'),
            ('stored_audit', 'records/aws_learning_v2_001_stored_audit/stored_audit_receipt.json'),
        ):
            path = ROOT / relative
            raw = path.read_bytes()
            data = json.loads(raw)
            external[label] = {'path': relative, 'sha256': sha256(raw).hexdigest(),
                               'status': data['status'], 'issues': data.get('issues'),
                               'errors': data.get('errors'),
                               'completed': data.get('completed'),
                               'completed_run_evidence_verified': data.get('completed_run_evidence_verified')}
            if label == 'inspection':
                source_sha = data['source_sha']
                index = Path(data['full_member_index'])
                assert sha256(index.read_bytes()).hexdigest() == data['full_member_index_sha256']
                external[label]['full_member_index_sha256'] = data['full_member_index_sha256']
        assert source_sha == '410bce98307a5644db51928459b73391c7066b72'
        assert seal['sha256'] == members['cloud_job/campaign/predictions.jsonl']['sha256']
        assert seal['test_private_sha256'] == members['cloud_job/campaign/dataset/test_private.json']['sha256']
        assert len(predictions) == len(test) == len(evaluation['cases']) == seal['test_examples']
        assert seal['prediction_count'] == len(predictions) * len(seal['arms'])
        assert all(p['case_index'] == i for i, p in enumerate(predictions))
        assert all(p['actions'] == {a: evaluation['cases'][i]['arms'][a]['action'] for a in seal['arms']}
                   for i, p in enumerate(predictions))
        assert all(p['public_sha256'] == sha256(canonical(t['public'])).hexdigest()
                   for p, t in zip(predictions, test, strict=True))
        report = {'schema': 'cas-meta2-postrun-diagnosis/0.1',
                  'status': 'DIAGNOSTIC_ONLY_NOT_RELEASE_ACCEPTANCE',
                  'packet_sha256': sha256(args.packet.read_bytes()).hexdigest(),
                  'script_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
                  'no_models_loaded_or_executed': True,
                  'no_new_test_cases_generated': True,
                  'predictions_seal_and_public_alignment_checked': True,
                  'pure_codec_sha256': sha256((ROOT / 'cas_meta2/codec.py').read_bytes()).hexdigest(),
                  'frozen_source_sha': source_sha,
                  'external_gate_receipts': external,
                  'gpu_preflight_memory': {k: v for k, v in preflight.items()
                                            if k.startswith('cuda_') or k in ('status', 'completed')},
                  'test_target_access': 'POST_COMPLETION_DIAGNOSIS_ONLY',
                  'prediction_seal': seal, 'test': {}, 'validation_by_epoch': {}, 'admitted_test_cases': {}}
        for family in ('cas', 'generic'):
            arm = family + '_trained'
            actions = [p['actions'][arm] for p in predictions]
            report['test'][arm], rows = summarize(actions, test)
            admitted = []
            reasons = Counter()
            for i, (case, task, row) in enumerate(zip(evaluation['cases'], test, rows, strict=True)):
                result = case['arms'][arm]
                reasons[result['execution_status'] + ':' + str((result.get('failure') or {}).get('message'))] += 1
                if result['execution_status'] == 'EXECUTED':
                    admitted.append({'case_index': i, 'task_id': task['task_id'],
                                     'provenance': task['provenance'], 'comparison': row,
                                     'verification': result['verification']})
            report['test'][arm]['execution_reasons'] = dict(reasons)
            report['admitted_test_cases'][arm] = admitted
            progression = []
            for h in history:
                info = h['families'][family]
                v = info['validation']
                if 'generation' not in v:
                    continue
                epoch = h['epoch']
                saved = read(f'validation_predictions/{family}_epoch_{epoch:04d}.json')
                actions = saved['actions']
                summaries = {}
                for depth in (1, 2, 3):
                    chosen = [i for i, t in enumerate(validation) if t['provenance']['depth'] == depth]
                    summaries[str(depth)], _ = summarize([actions[i] for i in chosen], [validation[i] for i in chosen])
                progression.append({'epoch': epoch, 'selected': info['selected'],
                                    'training_token_cross_entropy': info['training_token_cross_entropy'],
                                    'validation': v, 'by_depth': summaries})
            report['validation_by_epoch'][family] = progression
        report['selected_checkpoint_epoch'] = {f: training['checkpoints'][f]['selected']['epoch']
                                                for f in ('cas', 'generic')}
        report['member_hashes'] = members
        report['input_index_sha256'] = sha256(canonical(members)).hexdigest()
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        print(json.dumps({'output': str(args.output), 'sha256': sha256(args.output.read_bytes()).hexdigest(),
                          'members': len(members), 'test': report['test']}, indent=2))


if __name__ == '__main__':
    main()
