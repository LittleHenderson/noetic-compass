"""Recount the delivered diagnosis from retained rows; never loads a model."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cas_meta2.graph_teaching import contrast_probe, contrast_readout as r


def summarize(directory):
    directory = Path(directory)
    request = json.loads((directory.parent / 'REQUEST_001.json').read_bytes())
    raw = (directory / 'curriculum_result.json').read_bytes()
    assert r.digest(raw) == (directory / 'curriculum_result.json.sha256').read_text().strip()
    terminal = json.loads(raw)
    assert terminal['schema'] == r.RESULT_SCHEMA and terminal['status'] == 'CONTRAST_READOUT_DELIVERED'
    assert terminal['job'] == request['job'] and terminal['optimizer_updates'] == 0
    for entry in terminal['artifacts']:
        data = (directory / 'checkpoints' / entry['name']).read_bytes()
        assert len(data) == entry['bytes'] and r.digest(data) == entry['sha256']
    report = json.loads((directory / 'checkpoints/contrast_readout.json').read_bytes())
    expected = {(i['condition'], i['seed']): i for i in r.input_inventory(ROOT)}
    seen, per_learner, totals, lengths = set(), [], Counter(), Counter()
    for row in report['learners']:
        key = row['condition'], row['seed']
        assert key not in seen
        seen.add(key)
        item = expected[key]
        probe = row['probe']
        assert row['checkpoint_sha256'] == item['sha256']
        assert row['parameter_digest'] == item['expected_parameter_digest']
        assert probe['parameter_digest_before'] == probe['parameter_digest_after'] == row['parameter_digest']
        assert probe['weights_unchanged'] is True and probe['optimizer_steps_taken'] == 0
        assert row['practice_reproduced'] is True
        assert sum(x['correct'] for x in row['practice']) == item['practice_correct']
        summary = contrast_probe.summarise(probe['per_case'])
        assert summary == probe['summary']
        original = summary['accuracy']['original']
        assert original['attempted'] == original['correct'] == item['practice_correct']
        per_learner.append({'condition': key[0], 'seed': key[1], **summary})
        for variant, counts in summary['accuracy'].items():
            for field in ('correct', 'attempted'):
                totals[variant + '_' + field] += counts[field]
        for name, count in summary['answer_changes'].items():
            totals[name] += count
        for entry in probe['list_length_probe']:
            lengths['permutations'] += 1
            lengths['correct'] += int(entry['correct'])
            lengths['chosen_slot_' + str(entry['chosen_slot'])] += 1
            lengths['chosen_shortest'] += int(entry['chosen_length'] == min(entry['option_lengths']))
            lengths['chosen_longest'] += int(entry['chosen_length'] == max(entry['option_lengths']))
    assert seen == set(expected)
    collection = json.loads((directory / 'receiver_receipt.json').read_bytes())
    assert collection['collection'] == 'COMPLETE_VERIFIED'
    return {'schema': 'cas-graph6-contrast-recount/1', 'status': 'VERIFIED',
        'job': request['job'], 'source_sha': request['source_sha'], 'learners': per_learner,
        'totals': dict(totals), 'length_reading': dict(lengths),
        'optimizer_updates': 0, 'all_practice_scores_reproduced': True,
        'all_weights_unchanged': True, 'collection': collection['collection'],
        'elapsed_inference_seconds': report['elapsed_seconds'],
        'boundary': 'Conditional on each learner originally answering correctly. Retrospective diagnosis only; renaming sensitivity and rewiring failures do not identify a causal shortcut. Length observations do not prove length bias.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    report = summarize(args.receipt)
    r.write_json(args.output, report)
    print(json.dumps({key: report[key] for key in ('status', 'totals', 'length_reading', 'elapsed_inference_seconds')}))
