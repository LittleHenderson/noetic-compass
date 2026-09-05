"""Pure tiny diagnostic curricula only; seed 20260919 is never constructed."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import random

import pytest

from cas_meta2 import curriculum_v3 as v3
from cas_meta2.codec import action_to_tokens
from cas_meta2.curriculum import graph_signature, parse_problem

pytestmark = pytest.mark.not_gpu
SMALL = {'train': 48, 'validation': 6, 'test': 6}
DIAGNOSTIC_SEEDS = (914701, 914702, 914703)
_EXPOSED = set()


def _record(dataset):
    for tasks in dataset['splits'].values():
        for task in tasks:
            try:
                _EXPOSED.add(graph_signature(task['target']['program']))
            except (ValueError, KeyError, TypeError):
                pass


def diagnostic_exposures():
    return {'schema': 'cas-meta2-local-diagnostic-exposures/0.1',
            'seeds': list(DIAGNOSTIC_SEEDS), 'registered_seed_constructed': False,
            'graph_signatures': sorted(_EXPOSED),
            'boundary': 'Tiny local fixtures and mutations are exposed; exclude these hashes from future experiment partitions.'}


@pytest.fixture(scope='module')
def original():
    result = v3.generate_dataset(seed=DIAGNOSTIC_SEEDS[0], counts=SMALL)
    _record(result)
    return result


@pytest.fixture
def dataset(original):
    return deepcopy(original)


def check(data, extra=None):
    _record(data)
    return v3.validate_dataset(data, extra)


def reword(task):
    target = task['target']
    tag = next(o['tag'] for o in task['public']['observations'] if o['slot'] == target['binding'])
    task['provenance']['graph_signature'] = graph_signature(target['program'])
    task['public']['problem'] = v3.render_problem(target['program'], tag, task['provenance']['wording_combination'],
                                                  definition_order=task['provenance']['definition_order'])


def test_registered_defaults_only_no_generation():
    assert v3.DEFAULT_SEED == 20260919
    assert v3.DEFAULT_COUNTS == {'train': 3072, 'validation': 96, 'test': 72}
    assert v3.GROUPS == ('same_depth', 'wording_shift', 'deeper_calls')


def test_registered_seed_refuses_smaller_unregistered_counts_before_construction(monkeypatch):
    monkeypatch.setattr(v3.frozen, '_construct', lambda *a: pytest.fail('Registered target constructor was called'))
    with pytest.raises(v3.CurriculumV3Error, match='REGISTERED_COUNTS_REQUIRED'):
        v3.generate_dataset(seed=v3.DEFAULT_SEED, counts=SMALL)


@pytest.mark.parametrize('extra', [None, frozenset()])
def test_registered_seed_requires_development_exclusions_before_construction(monkeypatch, extra):
    monkeypatch.setattr(v3.frozen, '_construct', lambda *a: pytest.fail('Registered target constructor was called'))
    with pytest.raises(v3.CurriculumV3Error, match='REGISTERED_DEVELOPMENT_EXCLUSIONS_REQUIRED'):
        v3.generate_dataset(seed=v3.DEFAULT_SEED, excluded_graph_signatures=extra)


def test_registered_identity_accepts_complete_exclusions_without_generation(monkeypatch):
    monkeypatch.setattr(v3.frozen, '_construct', lambda *a: pytest.fail('Registered target constructor was called'))
    extra = v3.registered_development_exclusions()
    assert v3.HEX.fullmatch(v3.dataset_identity(v3.DEFAULT_SEED, excluded_graph_signatures=extra))
    base, _ = v3.exclusion_inventory()
    missing = next(iter(extra - base))
    with pytest.raises(v3.CurriculumV3Error, match='REGISTERED_DEVELOPMENT_EXCLUSIONS_REQUIRED'):
        v3.dataset_identity(v3.DEFAULT_SEED, excluded_graph_signatures=extra - {missing})


def test_portable_exclusion_inventory_binds_all_origins():
    values, receipt = v3.exclusion_inventory()
    assert len(values) == receipt['base_count'] == 4312
    assert receipt['cross_origin_overlap_count'] == 0
    assert {name: row['unique_graph_count'] for name, row in receipt['origins'].items()} == {
        'aws_full_002': 376, 'aws_learning_v2_001': 864, 'capacity_diagnostic': 3072}
    assert v3.digest(sorted(values)) == v3.EXCLUSION_UNION_SHA256


def test_asset_byte_tampering_rejected_without_writing(monkeypatch):
    read = Path.read_bytes
    monkeypatch.setattr(Path, 'read_bytes', lambda path: read(path) + b' ' if path.name == 'exclusions_v3.json' else read(path))
    with pytest.raises(v3.CurriculumV3Error, match='EXCLUSION_ASSET_DIGEST_MISMATCH'):
        v3.exclusion_inventory()


def test_development_exclusion_loader_is_pinned_and_explicit():
    values = v3.registered_development_exclusions()
    base, _ = v3.exclusion_inventory()
    assert type(values) is frozenset
    assert len(values) == 177
    assert len(values & base) == 1
    assert len(values | base) == 4488
    assert v3.digest(sorted(values)) == v3.DEVELOPMENT_EXCLUSION_LIST_SHA256
    assert v3._exclusions(None)[1]['count'] == 4312
    combined, receipt = v3._exclusions(values)
    assert len(combined) == receipt['count'] == 4488
    assert receipt['provided_additional_count'] == 177
    assert receipt['new_additional_count'] == 176


def test_development_loader_needs_only_portable_assets(monkeypatch):
    read = Path.read_bytes
    permitted = {'development_exclusions_v3.json', 'exclusions_v3.json'}
    def guarded(path):
        assert path.name in permitted, 'Loader attempted to read records or task targets'
        return read(path)
    monkeypatch.setattr(Path, 'read_bytes', guarded)
    assert len(v3.registered_development_exclusions()) == 177


def test_development_asset_tampering_rejected_without_writing(monkeypatch):
    read = Path.read_bytes
    monkeypatch.setattr(Path, 'read_bytes', lambda path: read(path) + b' '
                        if path.name == 'development_exclusions_v3.json' else read(path))
    with pytest.raises(v3.CurriculumV3Error, match='DEVELOPMENT_EXCLUSION_ASSET_DIGEST_MISMATCH'):
        v3.registered_development_exclusions()
    with pytest.raises(v3.CurriculumV3Error, match='DEVELOPMENT_EXCLUSION_ASSET_DIGEST_MISMATCH'):
        v3.dependency_receipt()


def test_dependency_receipt_binds_both_exclusion_assets():
    receipt = v3.dependency_receipt()
    assert receipt['exclusions_asset_sha256'] == v3.EXCLUSION_ASSET_SHA256
    assert receipt['development_exclusions_asset_sha256'] == v3.DEVELOPMENT_EXCLUSION_ASSET_SHA256
    assert receipt['development_exclusions_count'] == 177
    assert receipt['development_exclusions_sha256'] == v3.DEVELOPMENT_EXCLUSION_LIST_SHA256
    assert receipt['development_exposure_source_sha256'] == v3.DEVELOPMENT_EXPOSURE_SOURCE_SHA256


def test_frozen_dependency_tampering_rejected_without_writing(monkeypatch):
    read = Path.read_bytes
    monkeypatch.setattr(Path, 'read_bytes', lambda path: read(path) + b' ' if path.name == 'codec.py' else read(path))
    with pytest.raises(v3.CurriculumV3Error, match='FROZEN_CURRICULUM_DEPENDENCY_CHANGED'):
        v3.dependency_receipt()


@pytest.mark.parametrize('extra', [[], {'x'}, {'G' * 64}, {True}, 'a' * 64])
def test_invalid_extra_exclusions_rejected(extra):
    with pytest.raises(v3.CurriculumV3Error):
        v3.dataset_identity(DIAGNOSTIC_SEEDS[0], SMALL, extra)


def test_identity_binds_seed_counts_source_and_exclusions():
    base = v3.dataset_identity(DIAGNOSTIC_SEEDS[0], SMALL)
    assert base != v3.dataset_identity(DIAGNOSTIC_SEEDS[1], SMALL)
    assert base != v3.dataset_identity(DIAGNOSTIC_SEEDS[0], {**SMALL, 'train': 51})
    assert base != v3.dataset_identity(DIAGNOSTIC_SEEDS[0], SMALL, {'a' * 64})


@pytest.mark.parametrize('counts', [None, {}, {'train': 48, 'validation': 6, 'test': True},
                                  {'train': 47, 'validation': 6, 'test': 6},
                                  {'train': 3075, 'validation': 6, 'test': 6},
                                  {'train': 48, 'validation': 7, 'test': 6}])
def test_invalid_count_variants_or_default_seed_are_bounded(counts):
    if counts is None:
        assert v3._counts(None) == v3.DEFAULT_COUNTS
    else:
        with pytest.raises(v3.CurriculumV3Error):
            v3._counts(counts)


def test_diagnostic_generation_is_deterministic(original):
    again = v3.generate_dataset(seed=DIAGNOSTIC_SEEDS[0], counts=SMALL)
    _record(again)
    assert v3.canonical(again) == v3.canonical(original)


def test_balanced_depths_real_controls_and_coverage(original):
    manifest = original['manifest']
    assert manifest['splits']['train']['depth_counts'] == {'1': 16, '2': 16, '3': 16}
    assert manifest['registered_validation_depth_counts'] == {'1': 2, '2': 2, '3': 2}
    assert manifest['evaluation_group_counts'] == {name: 2 for name in v3.GROUPS}
    assert manifest['training_coverage']['programs_with_child_calls'] == 16
    assert all(manifest['training_coverage'][key] > 0 for key in ('earlier_value_inputs', 'earlier_value_returns', 'repeated_callee_uses'))
    assert manifest['splits']['train']['shuffled_definition_programs'] > 0
    assert set(manifest['training_coverage']['procedure_call_targets']) == {f'p{i}' for i in range(16)}
    assert manifest['exclusions']['count'] == 4312


def test_every_public_problem_independently_reconstructs_exact_action(original):
    for tasks in original['splits'].values():
        for task in tasks:
            assert v3.canonical(parse_problem(task['public'])) == v3.canonical(task['target'])
            assert list(parse_problem(task['public'])['program']['procedures']) == task['provenance']['definition_order']
            assert all(p['allowed_cjts'] == ['A', 'B', 'C'] for p in task['target']['program']['procedures'].values())
            assert 'R' not in action_to_tokens(task['target'])


def test_cold_json_reload_passes_without_an_adapter(original):
    cold = json.loads(v3.canonical(original))
    assert v3.canonical(check(cold)) == v3.canonical(original['manifest'])


def test_target_definition_dictionary_order_is_not_semantics(dataset):
    for task in dataset['splits']['train']:
        procedures = task['target']['program']['procedures']
        task['target']['program']['procedures'] = dict(reversed(list(procedures.items())))
    assert check(dataset)['counts'] == SMALL


def test_extra_exclusions_apply_to_every_partition(original):
    old = {t['provenance']['graph_signature'] for tasks in original['splits'].values() for t in tasks}
    result = v3.generate_dataset(seed=DIAGNOSTIC_SEEDS[1], counts=SMALL, excluded_graph_signatures=old)
    _record(result)
    actual = {t['provenance']['graph_signature'] for tasks in result['splits'].values() for t in tasks}
    assert not old & actual
    assert result['manifest']['exclusions']['new_additional_count'] == len(old)
    assert check(result, old)['dataset_id'] == result['dataset_id']
    with pytest.raises(v3.CurriculumV3Error, match='IDENTITY_MISMATCH'):
        check(result)


@pytest.mark.parametrize('mutation', ['target_return', 'binding_bool', 'definition_order', 'depth', 'scope', 'task_id', 'task_suffix', 'dataset_id'])
def test_meaning_and_provenance_mutations_rejected(dataset, mutation):
    task = dataset['splits']['train'][0]
    if mutation == 'target_return':
        task['target']['program']['procedures']['main']['return'] = 'arg'
    elif mutation == 'binding_bool':
        task['target']['binding'] = bool(task['target']['binding'])
    elif mutation == 'definition_order':
        task['provenance']['definition_order'] += ['not_declared']
    elif mutation == 'depth':
        task['provenance']['depth'] += 1
    elif mutation == 'scope':
        task['target']['program']['procedures']['main']['allowed_cjts'] = ['A', 'B']
    elif mutation == 'task_id':
        task['task_id'] = 'different-source-train-00000'
    elif mutation == 'task_suffix':
        task['task_id'] += '-extra'
    else:
        dataset['dataset_id'] = '0' * 64
    with pytest.raises(ValueError):
        check(dataset)


def test_actual_sentence_change_is_not_hidden_by_provenance(dataset):
    task = next(t for t in dataset['splits']['train'] if 'junction B' in t['public']['problem'])
    task['public']['problem'] = task['public']['problem'].replace('junction B', 'junction C', 1)
    with pytest.raises(ValueError):
        check(dataset)


def test_nonregistered_wording_family_recombination_rejected(dataset):
    task = dataset['splits']['validation'][0]
    task['provenance']['wording_combination'] = list(v3.frozen.wording_combinations(0)[0])
    reword(task)
    with pytest.raises(v3.CurriculumV3Error, match='WORDING_PARTITION_MISMATCH'):
        check(dataset)


def test_duplicate_float32_observation_payloads_rejected(dataset):
    task = dataset['splits']['train'][0]
    task['public']['observations'][1]['values'] = [v + 1e-12 for v in task['public']['observations'][0]['values']]
    with pytest.raises(v3.CurriculumV3Error, match='AMBIGUOUS_FLOAT32'):
        check(dataset)


def test_cross_split_graph_overlap_rejected(dataset):
    source = next(t for t in dataset['splits']['train'] if t['provenance']['depth'] == 1)
    target = next(t for t in dataset['splits']['validation'] if t['provenance']['depth'] == 1)
    target['target'] = deepcopy(source['target'])
    target['provenance']['definition_order'] = deepcopy(source['provenance']['definition_order'])
    reword(target)
    with pytest.raises(v3.CurriculumV3Error, match='GRAPH_OVERLAP_NOT_PERMITTED'):
        check(dataset)


def test_cross_split_input_overlap_rejected(dataset):
    source, target = dataset['splits']['train'][0], dataset['splits']['validation'][0]
    target['public']['observations'] = deepcopy(source['public']['observations'])
    reword(target)
    with pytest.raises(v3.CurriculumV3Error, match='INPUT_OVERLAP_NOT_PERMITTED'):
        check(dataset)


def test_deeper_pair_return_changes_are_not_accepted_as_equivalent(dataset):
    target = next(t for t in dataset['splits']['test'] if t['provenance']['evaluation_group'] == 'deeper_calls')
    program = target['target']['program']
    top = next(step['procedure'] for step in program['procedures']['main']['steps'] if step['kind'] == 'CALL')
    program['procedures'][top]['return'] = program['procedures'][top]['steps'][0]['output']
    reword(target)
    with pytest.raises(ValueError, match='PAIRED_NATIVE_WORK_MISMATCH'):
        check(dataset)


def test_same_graph_cannot_cross_triplets(dataset):
    same = [t for t in dataset['splits']['test'] if t['provenance']['evaluation_group'] == 'same_depth']
    same[1]['target'] = deepcopy(same[0]['target'])
    same[1]['provenance']['definition_order'] = deepcopy(same[0]['provenance']['definition_order'])
    reword(same[1])
    with pytest.raises(ValueError, match='GRAPH_OVERLAP_NOT_PERMITTED'):
        check(dataset)


def test_existing_exposed_graph_is_rejected(dataset):
    exposed = v3.frozen._construct(random.Random(910284113), 1, 0)
    assert graph_signature(exposed) in v3.exclusion_inventory()[0]
    task = next(t for t in dataset['splits']['train'] if t['provenance']['depth'] == 1)
    task['target']['program'] = exposed
    task['provenance']['definition_order'] = list(exposed['procedures'])
    reword(task)
    with pytest.raises(v3.CurriculumV3Error, match='EXPOSED_GRAPH_REUSED'):
        check(dataset)


def test_literal_positive_target_token_coverage_is_enforced(dataset):
    assert 'v31' not in dataset['manifest']['positive_target_token_coverage']['training_counts']
    for task in dataset['splits']['test']:
        main = task['target']['program']['procedures']['main']
        old = main['steps'][0]['output']
        for step in main['steps']:
            for key in ('input', 'output'):
                if step[key] == old:
                    step[key] = 'v31'
        if main['return'] == old:
            main['return'] = 'v31'
        reword(task)
    with pytest.raises(v3.CurriculumV3Error, match='UNSEEN_POSITIVE_TARGET_TOKEN'):
        check(dataset)


@pytest.fixture(scope='module')
def written(tmp_path_factory):
    directory = tmp_path_factory.mktemp('source-bound') / 'new_dataset'
    manifest = v3.write_dataset(directory, seed=DIAGNOSTIC_SEEDS[2], counts=SMALL)
    cold = {'schema': v3.SCHEMA, 'seed': DIAGNOSTIC_SEEDS[2], 'dataset_id': manifest['dataset_id'],
            'splits': {split: json.loads((directory / filename).read_bytes()) for split, filename in (
                ('train', 'train.json'), ('validation', 'validation.json'), ('test', 'test_private.json'))}}
    _record(cold)
    return directory, manifest, cold


def test_written_partition_hashes_and_cold_validation(written):
    directory, manifest, cold = written
    assert set(manifest['sha256']) == {'train.json', 'validation.json', 'test_public.json', 'test_private.json'}
    for filename, value in manifest['sha256'].items():
        assert sha256((directory / filename).read_bytes()).hexdigest() == value
    assert check(cold) == {k: v for k, v in manifest.items() if k != 'sha256'}
    assert v3.validate_manifest(manifest, SMALL, expected_seed=DIAGNOSTIC_SEEDS[2])['private_partition_opened'] is False


def test_public_partition_has_no_private_task_fields(written):
    directory, _, _ = written
    public = json.loads((directory / 'test_public.json').read_bytes())
    assert len(public) == 6
    assert all(set(row) == {'problem', 'observations'} for row in public)


def test_public_manifest_does_not_read_private_files(written, monkeypatch):
    _, manifest, _ = written
    read = Path.read_bytes
    def limited(path):
        if path.name in ('test_private.json', 'train.json', 'validation.json'):
            pytest.fail('Manifest-only validation opened a task partition')
        return read(path)
    monkeypatch.setattr(Path, 'read_bytes', limited)
    v3.validate_manifest(manifest, SMALL)


@pytest.mark.parametrize('mutation', ['depth_count', 'binding_frequency', 'token_frequency', 'token_flag',
                                     'seed', 'source', 'exclusions', 'native_claim', 'extra_root_field', 'extra_coverage', 'nested_token_count'])
def test_manifest_mutations_rejected(written, mutation):
    _, original_manifest, _ = written
    manifest = deepcopy(original_manifest)
    if mutation == 'depth_count':
        manifest['registered_validation_depth_counts']['3'] -= 1
    elif mutation == 'binding_frequency':
        manifest['splits']['test']['binding_counts'] = [2, 2, 2]
    elif mutation == 'token_frequency':
        manifest['positive_target_token_coverage']['test_counts'] = {'CALL': 1}
    elif mutation == 'token_flag':
        manifest['positive_target_token_coverage']['validation_tokens_covered'] = False
    elif mutation == 'seed':
        manifest['seed'] += 1
    elif mutation == 'source':
        manifest['source']['curriculum_v3_sha256'] = '0' * 64
    elif mutation == 'exclusions':
        manifest['exclusions']['count'] -= 1
    elif mutation == 'extra_root_field':
        manifest['private_task_labels'] = ['forbidden']
    elif mutation == 'extra_coverage':
        manifest['training_coverage']['private_task_labels'] = ['forbidden']
    elif mutation == 'nested_token_count':
        manifest['positive_target_token_coverage']['training_counts']['CALL'] = {'hidden': 'labels'}
    else:
        manifest['native_outcomes_checked'] = True
    with pytest.raises(ValueError):
        v3.validate_manifest(manifest, SMALL, expected_seed=DIAGNOSTIC_SEEDS[2])


def test_write_refuses_existing_output(written):
    directory, _, _ = written
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    with pytest.raises(v3.CurriculumV3Error, match='OUTPUT_MUST_BE_NEW'):
        v3.write_dataset(directory, seed=DIAGNOSTIC_SEEDS[2], counts=SMALL)
    assert before == {p.name: p.read_bytes() for p in directory.iterdir()}
