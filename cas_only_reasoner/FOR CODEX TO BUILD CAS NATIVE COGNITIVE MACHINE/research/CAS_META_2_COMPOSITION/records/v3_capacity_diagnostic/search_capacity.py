"""Training-only formal-graph capacity search; not a new experiment dataset.

No public wording, observation tags, validation split, or test split is generated.
Only the two completed, already-exposed historical datasets are read for exclusion.
The search records hashes, not future task targets. No neural/provider imports.
"""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import random
import sys
import time
import zipfile


class NoNeuralImports:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch', 'tensorflow', 'jax', 'cupy', 'boto3', 'cas_cjt'}:
            raise RuntimeError('NEURAL_OR_PROVIDER_IMPORT_FORBIDDEN:' + fullname)


sys.meta_path.insert(0, NoNeuralImports())
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from cas_meta2.curriculum import graph_signature
from cas_meta2.curriculum_v2 import _construct, _target_stats, CurriculumV2Error


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def main():
    directory = Path(__file__).resolve().parent
    out = directory / 'capacity_receipt.json'
    signatures_path = directory / 'diagnostic_graph_signatures.json'
    if out.exists() or signatures_path.exists():
        raise SystemExit('REFUSING_EXISTING_DIAGNOSTIC_OUTPUT')
    start = time.monotonic()
    excluded, historical = set(), {}
    for record in ('aws_full_002', 'aws_learning_v2_001'):
        path = ROOT / 'records' / record / 'cloud_artifacts.zip'
        historical[record] = {'packet_sha256': sha256(path.read_bytes()).hexdigest(), 'members': {}}
        with zipfile.ZipFile(path) as archive:
            for filename in ('train.json', 'validation.json', 'test_private.json'):
                member = 'cloud_job/campaign/dataset/' + filename
                raw = archive.read(member)
                tasks = json.loads(raw)
                historical[record]['members'][member] = {'sha256': sha256(raw).hexdigest(), 'count': len(tasks)}
                excluded.update(graph_signature(task['target']['program']) for task in tasks)
    report = {'schema': 'cas-meta2-training-graph-capacity-diagnostic/0.1',
              'status': 'DIAGNOSTIC_INCOMPLETE', 'diagnostic_seed': 910284113,
              'new_dataset_created': False, 'future_holdouts_created_or_opened': False,
              'public_wording_or_observation_tags_generated': False,
              'neural_or_provider_calls': False, 'historical_exclusions': historical,
              'excluded_graph_count': len(excluded),
              'excluded_graph_signatures_sha256': sha256(canonical(sorted(excluded))).hexdigest(),
              'requested_training_capacity': {'1': 1024, '2': 1024, '3': 1024},
              'maximum_attempts_per_depth': 100000, 'maximum_search_seconds': 60,
              'source_sha256': {name: sha256((ROOT / 'cas_meta2' / name).read_bytes()).hexdigest()
                                 for name in ('curriculum_v2.py', 'curriculum.py', 'ir.py', 'codec.py')},
              'script_sha256': sha256(Path(__file__).read_bytes()).hexdigest(), 'by_depth': {}}
    rng, seen, new_signatures = random.Random(report['diagnostic_seed']), set(excluded), {}
    deadline = time.monotonic() + report['maximum_search_seconds']
    for depth in (1, 2, 3):
        accepted, reasons, attempted, maximum = [], Counter(), 0, Counter()
        while len(accepted) < 1024 and attempted < 100000 and time.monotonic() < deadline:
            attempted += 1
            try:
                program = _construct(rng, depth, len(accepted))
            except CurriculumV2Error as exc:
                reasons[str(exc)] += 1
                continue
            signature = graph_signature(program)
            if signature in seen:
                reasons['OLD_GRAPH' if signature in excluded else 'DIAGNOSTIC_DUPLICATE'] += 1
                continue
            stats = _target_stats({'binding': 0, 'program': program})
            assert stats['max_call_depth'] == depth
            seen.add(signature)
            accepted.append(signature)
            for key in ('procedure_count', 'instruction_count', 'expanded_run_count', 'action_tokens'):
                maximum[key] = max(maximum[key], stats[key])
        new_signatures[str(depth)] = accepted
        report['by_depth'][str(depth)] = {'accepted_unique_graphs': len(accepted), 'attempts': attempted,
                                         'rejections': dict(reasons), 'maxima': dict(maximum)}
    report['status'] = ('CAPACITY_DEMONSTRATED_TRAINING_ONLY'
                        if all(len(v) == 1024 for v in new_signatures.values())
                        else 'CAPACITY_NOT_DEMONSTRATED_WITHIN_BOUNDS')
    payload = canonical(new_signatures) + b'\n'
    with signatures_path.open('xb') as stream:
        stream.write(payload)
    report['diagnostic_graph_signatures_file'] = signatures_path.name
    report['diagnostic_graph_signatures_file_sha256'] = sha256(payload).hexdigest()
    report['wall_seconds'] = time.monotonic() - start
    report['boundary'] = ('Pure capacity evidence only. These diagnostic graphs are now exposed; '
                          'exclude them from future validation/test. No proof of training, learning, '
                          'complete wording/input capacity, or native task success.')
    with out.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'status': report['status'], 'by_depth': report['by_depth'],
                      'excluded_graph_count': len(excluded), 'wall_seconds': report['wall_seconds'],
                      'receipt_sha256': sha256(out.read_bytes()).hexdigest()}, indent=2))


if __name__ == '__main__':
    main()
