"""Retrospective structural error inventory; no model loading or execution."""
from collections import Counter
from hashlib import file_digest, sha256
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / 'records/aws_ablation_v4_002/cloud_artifacts.zip'
EXPECTED = 'c0fbc413ce94a3b192a5b634bfc246dae96d94f3fe01943caacbff83a4e74708'
BASE = 'cloud_job/campaign/'


def digest(path):
    with path.open('rb') as stream:
        return file_digest(stream, 'sha256').hexdigest()


def differences(actual, expected, path=()):
    """Literal JSON structure differences, not semantic equivalence."""
    if type(actual) is not type(expected):
        return [{'path': list(path), 'kind': 'type', 'actual': actual, 'expected': expected}]
    if isinstance(expected, dict):
        result = []
        for key in sorted(set(actual) | set(expected)):
            if key not in actual:
                result.append({'path': list(path + (key,)), 'kind': 'missing', 'expected': expected[key]})
            elif key not in expected:
                result.append({'path': list(path + (key,)), 'kind': 'extra', 'actual': actual[key]})
            else:
                result.extend(differences(actual[key], expected[key], path + (key,)))
        return result
    if isinstance(expected, list):
        result = []
        if len(actual) != len(expected):
            result.append({'path': list(path), 'kind': 'length', 'actual': len(actual), 'expected': len(expected)})
        for index in range(min(len(actual), len(expected))):
            result.extend(differences(actual[index], expected[index], path + (index,)))
        return result
    return [] if actual == expected else [{'path': list(path), 'kind': 'value', 'actual': actual, 'expected': expected}]


def category(item):
    path = item['path']
    if len(path) == 2 and path[0] == 'procedures':
        return 'procedure_' + item['kind']
    if path and path[-1] == 'steps' and item['kind'] == 'length':
        return 'step_count'
    if 'steps' in path:
        return 'step_' + str(path[-1])
    return 'program_' + str(path[-1] if path else 'root')


def main():
    assert differences({'x': 1}, {'x': 1}) == []
    assert differences({'x': []}, {'x': [1]})[0]['kind'] == 'length'
    assert differences({'x': 1}, {'x': True})[0]['kind'] == 'type'
    assert differences({}, {'x': 1})[0]['kind'] == 'missing'
    assert differences({'x': 1}, {})[0]['kind'] == 'extra'
    assert category({'path': ['procedures', 'p2'], 'kind': 'missing'}) == 'procedure_missing'
    assert category({'path': ['procedures', 'p2', 'steps'], 'kind': 'length'}) == 'step_count'
    assert digest(PACKET) == EXPECTED
    code_sha = digest(Path(__file__))
    record = {'schema': 'cas-meta2-retrospective-program-errors/0.1',
              'packet_sha256': EXPECTED, 'script_sha256': code_sha,
              'self_checks': 7, 'neural_execution': False, 'training': False,
              'fresh_evaluation': False, 'semantic_audit': False, 'inputs': {}, 'modes': {}}
    with zipfile.ZipFile(PACKET) as archive:
        def read(name):
            raw = archive.read(BASE + name)
            record['inputs'][name] = sha256(raw).hexdigest()
            return json.loads(raw)
        tasks = read('dataset/test_private.json')
        assert len(tasks) == 72
        for mode in ('v3', 'viability_v4'):
            cases = read('prediction/' + mode + '/evaluation_results.json')['cases']
            assert len(cases) == len(tasks)
            summaries = {}
            for arm in ('cas_trained', 'generic_trained'):
                rows, failures, categories = [], Counter(), Counter()
                for task, case in zip(tasks, cases):
                    assert task['task_id'] == case['task_id']
                    action = case['arms'][arm]['action']
                    program = action.get('program')
                    if program is None:
                        failures[action.get('reason', 'NO_PROGRAM')] += 1
                        continue
                    mismatch = differences(program, task['target']['program'])
                    tags = sorted({category(item) for item in mismatch})
                    categories.update(tags)
                    rows.append({'task_id': task['task_id'], 'categories': tags,
                                 'binding_correct': action['binding'] == task['target']['binding'],
                                 'differences': mismatch})
                summaries[arm] = {'total': 72, 'program_present': len(rows),
                    'exact_program_matches': sum(not row['differences'] for row in rows),
                    'generation_failures': dict(failures),
                    'cases_with_difference_category': dict(sorted(categories.items())), 'cases': rows}
            record['modes'][mode] = summaries
    assert digest(PACKET) == EXPECTED and digest(Path(__file__)) == code_sha
    record['boundary'] = ('Literal JSON differences on already-exposed cases, with overlapping categories. '
                          'Not semantic equivalence, independent execution, causal diagnosis, or new learning.')
    with Path(__file__).with_name('receipt.json').open('x', encoding='utf-8') as stream:
        json.dump(record, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print(json.dumps({mode: {arm: {k: v for k, v in summary.items() if k != 'cases'}
          for arm, summary in arms.items()} for mode, arms in record['modes'].items()}, indent=2))


if __name__ == '__main__':
    main()
