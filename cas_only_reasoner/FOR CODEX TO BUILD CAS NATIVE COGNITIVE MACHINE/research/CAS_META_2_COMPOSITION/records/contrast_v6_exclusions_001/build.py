"""Freeze known development exposures; never label these graphs fresh holdouts."""
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from tools.validate_local_v3 import NoNeuralOrProviderImports
sys.meta_path.insert(0, NoNeuralOrProviderImports())
from cas_meta2 import curriculum_v3 as frozen
from cas_meta2.curriculum import graph_signature
from cas_meta2.contrast_v6 import curriculum as candidate


def main():
    output = HERE / 'inventory.json'
    if output.exists():
        raise ValueError('NEW_INVENTORY_REQUIRED')
    sources = {}

    def read(relative, expected=None):
        raw = (ROOT / relative).read_bytes()
        digest = sha256(raw).hexdigest()
        if expected is not None and digest != expected:
            raise ValueError('EXPOSURE_SOURCE_CHANGED:' + relative)
        sources[relative] = digest
        return json.loads(raw)

    probe = read('records/contrast_curriculum_v6_probe_001/receipt.json',
                 '88de2f5ca5b991bf7d5f64d58a334bda85629ea6d63b17bd76e0e208062d2363')
    origins = {
        'prior_registered_exclusions': set(frozen.exclusion_inventory()[0]),
        'prior_registered_development': set(frozen.registered_development_exclusions()),
    }
    for name in ('exclusions_v3.json', 'development_exclusions_v3.json'):
        read('cas_meta2/' + name, probe['source_sha256'][name])
    for name, digest in probe['prior_data_sha256'].items():
        tasks = read('records/decoder_dataset_reconstruction_v4_001/dataset/' + name, digest)
        origins['old_v3_' + name] = {graph_signature(t['target']['program']) for t in tasks}
    prior = set().union(*origins.values())
    if len(prior) != probe['prior_excluded_graphs']:
        raise ValueError('PRIOR_INVENTORY_COUNT_CHANGED')
    tasks = read('records/contrast_curriculum_v6_probe_001/tasks.json', probe['tasks_sha256'])
    prototype = {graph_signature(t['target']['program']) for t in tasks}
    if prototype != set(probe['exposed_graph_signatures']) or prototype & prior:
        raise ValueError('PROTOTYPE_INVENTORY_CHANGED')
    origins['contrast_prototype_seed_926601'] = prototype
    config = candidate.Config(train_flat=32, train_pairs_per_cell=8,
                              validation_flat=8, validation_pairs_per_cell=2, test_triplets=3)
    sample = candidate.generate(seed=926603, config=config, excluded=frozenset())
    for split, tasks in sample['splits'].items():
        origins['contrast_unit_fixture_926603_' + split] = {
            graph_signature(t['target']['program']) for t in tasks}
    for relative in ('cas_meta2/contrast_v6/curriculum.py', 'tests/test_contrast_v6_curriculum.py'):
        sources[relative] = sha256((ROOT / relative).read_bytes()).hexdigest()
    union = set().union(*origins.values())
    record = {
        'schema': 'cas-meta2-known-exposures/6',
        'count': len(union), 'graph_signatures': sorted(union),
        'origins': {name: {'count': len(values), 'graph_signatures': sorted(values)}
                    for name, values in origins.items()},
        'source_sha256': sources,
        'fixture': {'seed': 926603, 'config': asdict(config), 'dataset_id': sample['dataset_id']},
        'script_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
        'neural_execution': False, 'provider_execution': False,
        'boundary': 'Known recorded exposures, including diagnostic test partitions. '
                    'Exclude this full union from future registered partitions. '
                    'Additional development exposures must be appended in a new version. '
                    'This inventory alone does not establish fresh evaluation or learning.',
    }
    with output.open('xb') as stream:
        stream.write(candidate.canonical(record) + b'\n')
    cold = json.loads(output.read_bytes())
    assert set(cold['graph_signatures']) == set().union(
        *(set(v['graph_signatures']) for v in cold['origins'].values()))
    assert cold['count'] == len(cold['graph_signatures'])
    print(json.dumps({'count': len(union), 'origin_counts': {k: len(v) for k, v in origins.items()},
                      'sha256': sha256(output.read_bytes()).hexdigest(), 'neural_execution': False}))


if __name__ == '__main__':
    main()
