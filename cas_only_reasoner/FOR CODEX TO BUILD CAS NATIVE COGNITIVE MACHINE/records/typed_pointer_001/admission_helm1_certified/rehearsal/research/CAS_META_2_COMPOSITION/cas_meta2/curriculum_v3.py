"""Fresh, source-bound learning curriculum over the unchanged CAS-META-2 IR.

Formal structure comes first, wording second, independent checking third.
This module performs no neural/native execution. Registered seed 20260919 is
reserved for the future launch; local tests use explicitly diagnostic seeds.
The existing public language expresses no scope declaration, so every target
retains the explicit fixed ABC scope. General grammar scope support is separate.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import random
import re
import struct

from . import curriculum_v2 as frozen
from .codec import ACTION_VOCABULARY, PROCEDURE_NAMES, action_to_tokens, validate_public
from .curriculum import TAGS, check_public, graph_signature, parse_problem, permitted_view
from .ir import validate_program


SCHEMA = 'cas-meta2-curriculum/3'
MANIFEST_SCHEMA = 'cas-meta2-dataset-manifest/3'
DEFAULT_SEED = 20260919
DEFAULT_COUNTS = {'train': 3072, 'validation': 96, 'test': 72}
GROUPS = ('same_depth', 'wording_shift', 'deeper_calls')
MAX_EXPANDED_RUNS = 15
MAX_ACTION_TOKENS = 256
EXCLUSION_ASSET_SHA256 = '2e11f0e0e5a8cb8bc32907f81cc4c8a02c59f8623ce8f9b5937c59d421050f48'
EXCLUSION_UNION_SHA256 = '0b7ac0ab3854964e2b18770f7aea7001d3f8d18e2defa0e7a37ec4015ee69671'
DEVELOPMENT_EXCLUSION_ASSET_SHA256 = '4642f5c1c5a9fc078343cdc5fb99c042ec6ee3c7e2e2c971ee5965776ab71913'
DEVELOPMENT_EXCLUSION_LIST_SHA256 = 'ef6a490b911be2a0a8676db010d74e6fe214703674afe897803bf6b712a386af'
DEVELOPMENT_EXPOSURE_SOURCE_SHA256 = '18cab097a20c17e4681d288089f0df376ec4cc24d34f71a40f58131b4bea69fb'
HEX = re.compile(r'[0-9a-f]{64}\Z')
_ROOT = Path(__file__).resolve().parent
_FROZEN_SHA256 = {
    'curriculum.py': 'c89a03e2f0c381ec4e9c2f8750fd5f5bf6d4b7836ca790d02e256c1cc334e384',
    'curriculum_v2.py': 'a62e7acb23024a6f195e33af57a3a19cb513b5e7181a9a00370332ee37f1c5bd',
    'codec.py': 'c6ca7f489f91e4b43225b7ffc4d496490f038c18842266b6d5da05570ca29030',
    'ir.py': '02f3ce65ef9c3b54901a38abab2d4f9f272268e7c195f7001fb119bf1d384637',
}


class CurriculumV3Error(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise CurriculumV3Error(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def digest(value):
    return sha256(canonical(value)).hexdigest()


def dependency_receipt():
    """Bind only local source bytes, not an asserted Git or runtime identity."""
    hashes = {name: sha256((_ROOT / name).read_bytes()).hexdigest() for name in _FROZEN_SHA256}
    require(hashes == _FROZEN_SHA256, 'V3_FROZEN_CURRICULUM_DEPENDENCY_CHANGED')
    require(Path(frozen.__file__).resolve() == (_ROOT / 'curriculum_v2.py').resolve(),
            'V3_FROZEN_CURRICULUM_MODULE_PATH_MISMATCH')
    development = registered_development_exclusions()
    return {'frozen_source_sha256': hashes,
            'curriculum_v3_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
            'exclusions_asset_sha256': EXCLUSION_ASSET_SHA256,
            'development_exclusions_asset_sha256': DEVELOPMENT_EXCLUSION_ASSET_SHA256,
            'development_exclusions_count': len(development),
            'development_exclusions_sha256': DEVELOPMENT_EXCLUSION_LIST_SHA256,
            'development_exposure_source_sha256': DEVELOPMENT_EXPOSURE_SOURCE_SHA256}


def exclusion_inventory():
    """Read the portable, byte-pinned 4,312-graph inventory; no old gold files."""
    raw = (_ROOT / 'exclusions_v3.json').read_bytes()
    require(sha256(raw).hexdigest() == EXCLUSION_ASSET_SHA256, 'V3_EXCLUSION_ASSET_DIGEST_MISMATCH')
    asset = json.loads(raw)
    require(asset.get('schema') == 'cas-meta2-graph-exclusions/3'
            and set(asset.get('origins', {})) == {'aws_full_002', 'aws_learning_v2_001', 'capacity_diagnostic'},
            'V3_EXCLUSION_ASSET_SCHEMA_INVALID')
    expected = {'aws_full_002': 376, 'aws_learning_v2_001': 864, 'capacity_diagnostic': 3072}
    union, origins = set(), {}
    for name, origin in asset['origins'].items():
        values = origin.get('graph_signatures')
        require(type(values) is list and all(type(v) is str and HEX.fullmatch(v) for v in values)
                and values == sorted(set(values)) and len(values) == expected[name]
                and origin.get('unique_graph_count') == len(values)
                and origin.get('graph_signatures_sha256') == digest(values), 'V3_EXCLUSION_ORIGIN_INVALID')
        origins[name] = {key: value for key, value in origin.items() if key != 'graph_signatures'}
        union.update(values)
    overlap = sum(expected.values()) - len(union)
    require(len(union) == asset.get('union_count') == 4312
            and digest(sorted(union)) == asset.get('union_sha256') == EXCLUSION_UNION_SHA256
            and asset.get('cross_origin_overlap_count') == overlap == 0, 'V3_EXCLUSION_UNION_INVALID')
    return frozenset(union), {'asset_sha256': EXCLUSION_ASSET_SHA256, 'base_count': len(union),
                             'base_sha256': EXCLUSION_UNION_SHA256,
                             'cross_origin_overlap_count': overlap, 'origins': origins}


def registered_development_exclusions():
    """Load exposed diagnostic graphs for explicit registered-run exclusion.

    This reads only pinned portable assets, not diagnostic records or targets.
    It does not implicitly change tiny development fixtures. Registered callers
    must pass this set as ``excluded_graph_signatures`` to construction and audit.
    """
    raw = (_ROOT / 'development_exclusions_v3.json').read_bytes()
    require(sha256(raw).hexdigest() == DEVELOPMENT_EXCLUSION_ASSET_SHA256,
            'V3_DEVELOPMENT_EXCLUSION_ASSET_DIGEST_MISMATCH')
    asset = json.loads(raw)
    require(type(asset) is dict and set(asset) == {
        'schema', 'boundary', 'count', 'diagnostic_seeds', 'graph_signatures',
        'graph_signatures_sha256', 'source_exposure_file_sha256',
        'base_overlap_count', 'new_beyond_base_count'}
        and asset['schema'] == 'cas-meta2-development-exclusions/3'
        and asset['diagnostic_seeds'] == [914701, 914702, 914703]
        and asset['source_exposure_file_sha256'] == DEVELOPMENT_EXPOSURE_SOURCE_SHA256,
        'V3_DEVELOPMENT_EXCLUSION_ASSET_SCHEMA_INVALID')
    values = asset['graph_signatures']
    require(type(values) is list and all(type(value) is str and HEX.fullmatch(value) for value in values)
            and values == sorted(set(values)) and type(asset['count']) is int
            and len(values) == asset['count'] == 177
            and digest(values) == asset['graph_signatures_sha256'] == DEVELOPMENT_EXCLUSION_LIST_SHA256,
            'V3_DEVELOPMENT_EXCLUSION_INVENTORY_INVALID')
    base, _ = exclusion_inventory()
    values = frozenset(values)
    require(type(asset['base_overlap_count']) is int and type(asset['new_beyond_base_count']) is int
            and len(values & base) == asset['base_overlap_count'] == 1
            and len(values - base) == asset['new_beyond_base_count'] == 176,
            'V3_DEVELOPMENT_EXCLUSION_OVERLAP_INVALID')
    return values


def _exclusions(extra):
    require(extra is None or type(extra) in (set, frozenset), 'V3_EXCLUSIONS_MUST_BE_SET')
    extra = set() if extra is None else set(extra)
    require(all(type(v) is str and HEX.fullmatch(v) for v in extra), 'V3_INVALID_EXCLUDED_GRAPH_SIGNATURE')
    base, receipt = exclusion_inventory()
    combined = set(base) | extra
    return combined, {**receipt, 'provided_additional_count': len(extra),
                      'new_additional_count': len(extra - base), 'additional_sha256': digest(sorted(extra)),
                      'count': len(combined), 'sha256': digest(sorted(combined))}


def _counts(counts):
    require(counts is None or type(counts) is dict, 'V3_INVALID_COUNTS')
    result = dict(DEFAULT_COUNTS if counts is None else counts)
    require(set(result) == set(DEFAULT_COUNTS) and all(type(n) is int for n in result.values())
            and 48 <= result['train'] <= 3072 and 6 <= result['validation'] <= 96
            and 6 <= result['test'] <= 72 and all(n % 3 == 0 for n in result.values()), 'V3_INVALID_COUNTS')
    return result


def dataset_identity(seed, counts=None, excluded_graph_signatures=None):
    counts = _counts(counts)
    require(type(seed) is int and 0 <= seed < 2**63, 'V3_INVALID_SEED')
    if seed == DEFAULT_SEED:
        require(counts == DEFAULT_COUNTS, 'V3_REGISTERED_COUNTS_REQUIRED')
    combined, exclusions = _exclusions(excluded_graph_signatures)
    if seed == DEFAULT_SEED:
        require(registered_development_exclusions() <= combined,
                'V3_REGISTERED_DEVELOPMENT_EXCLUSIONS_REQUIRED')
    return digest({'schema': SCHEMA, 'seed': seed, 'counts': counts,
                   'source': dependency_receipt(), 'exclusions': exclusions})


def render_problem(program, tag, combination, *, definition_order=None):
    """Render an explicit presentation order without changing the program."""
    names = list(program['procedures']) if definition_order is None else definition_order
    require(type(names) in (tuple, list) and all(type(name) is str for name in names)
            and len(names) == len(set(names)) and set(names) == set(program['procedures']),
            'V3_INVALID_DEFINITION_ORDER')
    detached = deepcopy(program)
    detached['procedures'] = {name: detached['procedures'][name] for name in names}
    return frozen.render_problem(detached, tag, combination)


def _public_check(public):
    check_public(public)
    validate_public(public)
    observations = public['observations']
    require(len({row['tag'] for row in observations}) == 3, 'V3_AMBIGUOUS_OBSERVATION_TAGS')
    require(all(abs(value) <= 2 for row in observations for value in row['values']), 'V3_OBSERVATION_BOUND_EXCEEDED')
    payloads = [struct.pack('<8f', *row['values']) for row in observations]
    require(len(set(payloads)) == 3, 'V3_AMBIGUOUS_FLOAT32_OBSERVATIONS')
    return payloads


def _observations(rng, seen):
    tags, result = rng.sample(TAGS, 3), []
    for slot, tag in enumerate(tags):
        for _ in range(1000):
            values = [round(base / 10 + rng.uniform(-0.0004, 0.0004), 7) for base in range(1, 9)]
            payload = struct.pack('<8f', *values)
            if payload not in seen:
                seen.add(payload)
                result.append({'slot': slot, 'tag': tag, 'values': values})
                break
        else:
            raise CurriculumV3Error('V3_OBSERVATION_GENERATION_EXHAUSTED')
    return result


def _task(program, observations, binding, combination, task_id, group, order, triplet=None):
    tag = next(row['tag'] for row in observations if row['slot'] == binding)
    public = {'problem': render_problem(program, tag, combination, definition_order=order),
              'observations': deepcopy(observations)}
    target = {'program': deepcopy(program), 'binding': binding}
    require(canonical(parse_problem(public)) == canonical(target), 'V3_RENDERED_MEANING_MISMATCH')
    return {'task_id': task_id, 'public': public, 'target': target,
            'provenance': {'graph_signature': graph_signature(program),
                           'depth': validate_program(program)['max_call_depth'],
                           'evaluation_group': group, 'triplet_id': triplet,
                           'wording_combination': list(combination), 'definition_order': list(order)}}


def generate_dataset(seed=DEFAULT_SEED, counts=None, excluded_graph_signatures=None):
    """Construct all partitions in memory; callers must enforce gold withholding.

    Tests must pass a nonregistered diagnostic seed explicitly. No policy is
    invoked here. The public manifest contains no held-out binding/token counts.
    """
    counts = _counts(counts)
    identity = dataset_identity(seed, counts, excluded_graph_signatures)
    excluded, _ = _exclusions(excluded_graph_signatures)
    rng, graphs, inputs, splits = random.Random(seed), set(excluded), set(), {}
    for split, remainder, group in (('train', 0, 'training'), ('validation', 2, 'validation')):
        tasks, combinations = [], frozen.wording_combinations(remainder)
        depths = [depth for depth in (1, 2, 3) for _ in range(counts[split] // 3)]
        for index, depth in enumerate(depths):
            for _ in range(10000):
                try:
                    program = frozen._construct(rng, depth, index)
                except frozen.CurriculumV2Error as exc:
                    if str(exc) == 'V2_NATIVE_RUN_CEILING':
                        continue
                    raise
                signature = graph_signature(program)
                if signature not in graphs:
                    graphs.add(signature)
                    break
            else:
                raise CurriculumV3Error('V3_GRAPH_GENERATION_EXHAUSTED')
            observations = _observations(rng, inputs)
            order = list(program['procedures'])
            rng.shuffle(order)
            task_id = f'meta2-v3-{identity[:16]}-{split}-{index:05d}'
            tasks.append(_task(program, observations, index % 3, combinations[index % len(combinations)],
                               task_id, group, order))
        rng.shuffle(tasks)
        splits[split] = tasks
    testing = []
    known, shifted = frozen.wording_combinations(0), frozen.wording_combinations(1)
    for index in range(counts['test'] // 3):
        for _ in range(10000):
            try:
                shallow, deep = frozen._paired_programs(rng, index)
            except frozen.CurriculumV2Error as exc:
                if str(exc) == 'V2_NATIVE_RUN_CEILING':
                    continue
                raise
            signatures = {graph_signature(shallow), graph_signature(deep)}
            if len(signatures) == 2 and not signatures & graphs:
                graphs.update(signatures)
                break
        else:
            raise CurriculumV3Error('V3_PAIRED_GRAPH_GENERATION_EXHAUSTED')
        observations, triplet = _observations(rng, inputs), f'triplet-{index:04d}'
        order = list(shallow['procedures'])
        rng.shuffle(order)
        for group, program, combination in (
                ('same_depth', shallow, known[index % len(known)]),
                ('wording_shift', shallow, shifted[index % len(shifted)]),
                ('deeper_calls', deep, known[index % len(known)])):
            task_id = f'meta2-v3-{identity[:16]}-test-{triplet}-{group}'
            testing.append(_task(program, observations, index % 3, combination, task_id, group, order, triplet))
    rng.shuffle(testing)
    splits['test'] = testing
    result = {'schema': SCHEMA, 'seed': seed, 'dataset_id': identity, 'splits': splits}
    result['manifest'] = validate_dataset(result, excluded_graph_signatures)
    return result


def validate_dataset(dataset, excluded_graph_signatures=None):
    """Recheck detached or cold-reloaded data, including actual public meaning.

    Independent parsing reconstructs presentation order from public declarations;
    JSON object insertion order is never treated as part of program meaning.
    This full-data function belongs after prediction sealing during test audit.
    """
    require(type(dataset) is dict and {'schema', 'seed', 'dataset_id', 'splits'} <= set(dataset)
            <= {'schema', 'seed', 'dataset_id', 'splits', 'manifest'}
            and dataset['schema'] == SCHEMA and type(dataset['splits']) is dict
            and set(dataset['splits']) == set(DEFAULT_COUNTS), 'V3_INVALID_DATASET')
    splits = dataset['splits']
    require(all(type(tasks) is list for tasks in splits.values()), 'V3_INVALID_PARTITION')
    counts = _counts({split: len(tasks) for split, tasks in splits.items()})
    identity = dataset_identity(dataset['seed'], counts, excluded_graph_signatures)
    require(dataset['dataset_id'] == identity, 'V3_DATASET_IDENTITY_MISMATCH')
    excluded, exclusion_receipt = _exclusions(excluded_graph_signatures)
    ids, graph_owners, input_owners, report, triplets, token_counts = set(), {}, {}, {}, {}, {}
    for split in ('train', 'validation', 'test'):
        depth_counts, groups, bindings = Counter(), Counter(), [0, 0, 0]
        split_ids = set()
        token_counts[split] = Counter()
        max_runs, max_tokens, max_chars, shuffled = 0, 0, 0, 0
        for task in splits[split]:
            require(type(task) is dict and set(task) == {'task_id', 'public', 'target', 'provenance'}, 'V3_INVALID_TASK_FIELDS')
            require(type(task['task_id']) is str and task['task_id'] not in ids
                    and task['task_id'].startswith(f'meta2-v3-{identity[:16]}-{split}-'), 'V3_INVALID_OR_DUPLICATE_TASK_ID')
            ids.add(task['task_id'])
            split_ids.add(task['task_id'])
            public, target, provenance = task['public'], task['target'], task['provenance']
            payloads = _public_check(public)
            stats = frozen._target_stats(target)
            token_counts[split].update(action_to_tokens(target, max_length=MAX_ACTION_TOKENS))
            signature = graph_signature(target['program'])
            require(signature not in excluded, 'V3_EXPOSED_GRAPH_REUSED')
            require(type(provenance) is dict and set(provenance) == {
                'graph_signature', 'depth', 'evaluation_group', 'triplet_id', 'wording_combination', 'definition_order'},
                'V3_INVALID_PROVENANCE')
            group, triplet, combination = (provenance['evaluation_group'], provenance['triplet_id'], provenance['wording_combination'])
            require(provenance['graph_signature'] == signature and type(provenance['depth']) is int
                    and provenance['depth'] == stats['max_call_depth'], 'V3_GRAPH_OR_DEPTH_MISMATCH')
            if split == 'test':
                require(group in GROUPS and type(triplet) is str and re.fullmatch(r'triplet-\d{4}', triplet), 'V3_INVALID_TEST_GROUP')
                require(stats['max_call_depth'] == (4 if group == 'deeper_calls' else 3), 'V3_TEST_DEPTH_MISMATCH')
                require(group not in triplets.setdefault(triplet, {}), 'V3_DUPLICATE_TRIPLET_GROUP')
                triplets[triplet][group] = task
                remainder = 1 if group == 'wording_shift' else 0
            else:
                require(group == ('training' if split == 'train' else 'validation') and triplet is None,
                        'V3_INVALID_DEVELOPMENT_GROUP')
                remainder = 0 if split == 'train' else 2
            require(type(combination) is list and all(type(v) is int for v in combination)
                    and tuple(combination) in frozen.wording_combinations(remainder), 'V3_WORDING_PARTITION_MISMATCH')
            parsed = parse_problem(public)
            require(canonical(parsed) == canonical(target), 'V3_PUBLIC_MEANING_MISMATCH')
            order = list(parsed['program']['procedures'])
            require(provenance['definition_order'] == order, 'V3_PUBLIC_DEFINITION_ORDER_MISMATCH')
            tag = next(row['tag'] for row in public['observations'] if row['slot'] == target['binding'])
            require(public['problem'] == render_problem(target['program'], tag, combination, definition_order=order),
                    'V3_ACTUAL_WORDING_MISMATCH')
            shuffled += order != sorted(order, key=lambda name: (name != 'main', name))
            owner = (split, triplet, group)
            if signature in graph_owners:
                prior = graph_owners[signature]
                require(split == prior[0] == 'test' and triplet == prior[1]
                        and {group, prior[2]} == {'same_depth', 'wording_shift'}, 'V3_GRAPH_OVERLAP_NOT_PERMITTED')
            else:
                graph_owners[signature] = owner
            for payload, observation in zip(payloads, public['observations'], strict=True):
                if payload in input_owners:
                    prior = input_owners[payload]
                    require(split == prior[0] == 'test' and triplet == prior[1] and observation == prior[2],
                            'V3_INPUT_OVERLAP_NOT_PERMITTED')
                else:
                    input_owners[payload] = (split, triplet, observation)
            depth_counts[stats['max_call_depth']] += 1
            groups[group] += 1
            bindings[target['binding']] += 1
            max_runs, max_tokens = max(max_runs, stats['expanded_run_count']), max(max_tokens, stats['action_tokens'])
            max_chars = max(max_chars, len(public['problem']))
        if split == 'test':
            expected_ids = {f'meta2-v3-{identity[:16]}-test-triplet-{index:04d}-{group}'
                            for index in range(counts['test'] // 3) for group in GROUPS}
        else:
            expected_ids = {f'meta2-v3-{identity[:16]}-{split}-{index:05d}' for index in range(counts[split])}
        require(split_ids == expected_ids, 'V3_SOURCE_BOUND_TASK_ID_COVERAGE_MISMATCH')
        report[split] = {'count': len(splits[split]), 'sha256': digest(splits[split]),
                         'depth_counts': {str(key): value for key, value in sorted(depth_counts.items())},
                         'evaluation_groups': dict(sorted(groups.items())), 'max_public_characters': max_chars}
        if split == 'train':
            report[split].update(binding_counts=bindings, max_expanded_runs=max_runs,
                                 max_action_tokens=max_tokens, shuffled_definition_programs=shuffled)
    require(all(report[split]['depth_counts'] == {str(depth): counts[split] // 3 for depth in (1, 2, 3)}
                for split in ('train', 'validation')), 'V3_DEVELOPMENT_DEPTH_COUNTS_MISMATCH')
    require(len(triplets) == counts['test'] // 3 and report['test']['evaluation_groups']
            == {group: counts['test'] // 3 for group in GROUPS}, 'V3_TRIPLET_COUNTS_MISMATCH')
    for triplet in triplets.values():
        require(set(triplet) == set(GROUPS), 'V3_TRIPLET_INCOMPLETE')
        same, wording, deep = (triplet[group] for group in GROUPS)
        require(canonical(same['target']) == canonical(wording['target'])
                and same['public']['observations'] == wording['public']['observations'] == deep['public']['observations']
                and same['target']['binding'] == deep['target']['binding'], 'V3_PAIRED_INPUT_OR_TARGET_MISMATCH')
        require(same['provenance']['wording_combination'] == deep['provenance']['wording_combination']
                and same['provenance']['definition_order'] == wording['provenance']['definition_order'] == deep['provenance']['definition_order']
                and same['public']['problem'] != wording['public']['problem'], 'V3_PAIRED_WORDING_MISMATCH')
        frozen._validate_pair(same['target']['program'], deep['target']['program'])
    coverage = frozen._coverage(splits['train'])
    missing = {split: sorted(set(token_counts[split]) - set(token_counts['train'])) for split in ('validation', 'test')}
    require(not any(missing.values()), 'V3_UNSEEN_POSITIVE_TARGET_TOKEN')
    missing_sentences = [role + ':' + str(family) for role, values in coverage['sentence_primitives'].items()
                         for family in range(3) if values.get(str(family), 0) <= 0]
    require(not missing_sentences, 'V3_SENTENCE_PRIMITIVE_TRAINING_GAP')
    require(all(coverage['procedure_declarations'].get(name, 0) > 0
                and coverage['procedure_call_targets'].get(name, 0) > 0 for name in PROCEDURE_NAMES[1:]),
            'V3_PROCEDURE_IDENTITY_TRAINING_GAP')
    require(coverage['programs_with_child_calls'] == counts['train'] // 3
            and all(coverage['instructions'].get(name, 0) > 0 for name in ('RUN', 'CALL', 'RETURN'))
            and all(coverage[key] > 0 for key in ('earlier_value_inputs', 'earlier_value_returns', 'repeated_callee_uses'))
            and report['train']['shuffled_definition_programs'] > 0, 'V3_CONTROL_PRIMITIVE_TRAINING_GAP')
    return {'schema': MANIFEST_SCHEMA, 'seed': dataset['seed'], 'dataset_id': identity,
            'source': dependency_receipt(), 'counts': counts, 'splits': report,
            'registered_validation_depth_counts': {str(depth): counts['validation'] // 3 for depth in (1, 2, 3)},
            'evaluation_group_counts': {group: counts['test'] // 3 for group in GROUPS}, 'triplets': len(triplets),
            'training_coverage': coverage, 'exclusions': exclusion_receipt,
            'positive_target_token_coverage': {'training_counts': dict(sorted(token_counts['train'].items())),
                'validation_tokens_covered': True, 'test_tokens_covered': True,
                'missing_validation_tokens': [], 'missing_test_tokens': []},
            'missing_training_sentence_primitives': [], 'graph_sets_disjoint_across_splits': True,
            'input_instances_disjoint_across_splits': True,
            'duplicate_exceptions': {'test_graph_reuse': 'Only same_depth/wording_shift within one triplet.',
                                     'test_input_reuse': 'Only the three members of one matched triplet.'},
            'wording_partitions': {'train_and_same_depth': 0, 'test_wording_shift': 1, 'validation': 2,
                                   'rule': 'Sum of four existing sentence-family IDs modulo 3.'},
            'presentation_order': 'Explicit provenance, reconstructed independently from public declarations; JSON key order is irrelevant.',
            'scope_boundary': 'Every target has fixed ABC scope; existing public syntax cannot express varying permission scopes.',
            'every_procedure_has_native_run': True, 'deeper_pairs_preserve_native_work': True,
            'max_expanded_runs': MAX_EXPANDED_RUNS, 'max_action_tokens': MAX_ACTION_TOKENS,
            'native_outcomes_checked': False, 'training_or_neural_execution_performed': False,
            'boundary': 'Pure construction and checked public meaning only. Native task/output correctness requires the unchanged AWS executor after prediction sealing.'}


def validate_manifest(manifest, expected_counts=None, *, expected_seed=None, excluded_graph_signatures=None):
    """Public metadata only; callers separately verify file hashes and gold seals."""
    counts = _counts(expected_counts)
    fields = {'schema', 'seed', 'dataset_id', 'source', 'counts', 'splits', 'registered_validation_depth_counts',
              'evaluation_group_counts', 'triplets', 'training_coverage', 'exclusions', 'positive_target_token_coverage',
              'missing_training_sentence_primitives', 'graph_sets_disjoint_across_splits', 'input_instances_disjoint_across_splits',
              'duplicate_exceptions', 'wording_partitions', 'presentation_order', 'scope_boundary',
              'every_procedure_has_native_run', 'deeper_pairs_preserve_native_work', 'max_expanded_runs', 'max_action_tokens',
              'native_outcomes_checked', 'training_or_neural_execution_performed', 'boundary', 'sha256'}
    require(type(manifest) is dict and manifest.get('schema') == MANIFEST_SCHEMA
            and set(manifest) == fields and manifest.get('counts') == counts
            and type(manifest.get('seed')) is int, 'V3_INVALID_PUBLIC_MANIFEST')
    if expected_seed is not None:
        require(type(expected_seed) is int and manifest['seed'] == expected_seed, 'V3_MANIFEST_SEED_MISMATCH')
    identity = dataset_identity(manifest['seed'], counts, excluded_graph_signatures)
    _, exclusions = _exclusions(excluded_graph_signatures)
    require(manifest.get('dataset_id') == identity and manifest.get('source') == dependency_receipt()
            and manifest.get('exclusions') == exclusions, 'V3_MANIFEST_SOURCE_OR_EXCLUSIONS_MISMATCH')
    hashes = manifest.get('sha256', {})
    require(type(hashes) is dict and set(hashes) == {'train.json', 'validation.json', 'test_public.json', 'test_private.json'}
            and all(type(v) is str and HEX.fullmatch(v) for v in hashes.values()), 'V3_INVALID_PARTITION_HASHES')
    require(manifest.get('registered_validation_depth_counts') == {str(d): counts['validation'] // 3 for d in (1, 2, 3)}
            and manifest.get('evaluation_group_counts') == {group: counts['test'] // 3 for group in GROUPS}
            and manifest.get('triplets') == counts['test'] // 3
            and all(manifest.get(key) is True for key in ('graph_sets_disjoint_across_splits',
                'input_instances_disjoint_across_splits', 'every_procedure_has_native_run', 'deeper_pairs_preserve_native_work')),
            'V3_MANIFEST_COVERAGE_MISMATCH')
    require(type(manifest.get('splits')) is dict and set(manifest['splits']) == set(counts)
            and all(manifest['splits'][split].get('count') == count for split, count in counts.items()), 'V3_MANIFEST_SPLIT_COUNTS_MISMATCH')
    common = {'count', 'sha256', 'depth_counts', 'evaluation_groups', 'max_public_characters'}
    train_fields = common | {'binding_counts', 'max_expanded_runs', 'max_action_tokens', 'shuffled_definition_programs'}
    require(set(manifest['splits']['train']) == train_fields
            and all(set(manifest['splits'][split]) == common for split in ('validation', 'test')),
            'V3_PUBLIC_SPLIT_METADATA_FIELDS_INVALID')
    require(all(type(row.get('sha256')) is str and HEX.fullmatch(row['sha256'])
                and type(row.get('max_public_characters')) is int and 0 < row['max_public_characters'] <= 8192
                for row in manifest['splits'].values()), 'V3_PUBLIC_SPLIT_METADATA_INVALID')
    for split in ('train', 'validation'):
        require(manifest['splits'][split].get('depth_counts') == {str(d): counts[split] // 3 for d in (1, 2, 3)},
                'V3_MANIFEST_DEPTH_COUNTS_MISMATCH')
    require(manifest['splits']['test'].get('depth_counts') == {'3': 2 * counts['test'] // 3, '4': counts['test'] // 3}
            and manifest['splits']['test'].get('evaluation_groups') == {group: counts['test'] // 3 for group in GROUPS}
            and manifest['splits']['train'].get('evaluation_groups') == {'training': counts['train']}
            and manifest['splits']['validation'].get('evaluation_groups') == {'validation': counts['validation']},
            'V3_MANIFEST_GROUP_COUNTS_MISMATCH')
    tokens = manifest.get('positive_target_token_coverage', {})
    require(type(tokens) is dict and set(tokens) == {'training_counts', 'validation_tokens_covered',
            'test_tokens_covered', 'missing_validation_tokens', 'missing_test_tokens'}
            and tokens.get('validation_tokens_covered') is True and tokens.get('test_tokens_covered') is True
            and tokens.get('missing_validation_tokens') == tokens.get('missing_test_tokens') == []
            and manifest.get('missing_training_sentence_primitives') == [], 'V3_MANIFEST_TOKEN_COVERAGE_INVALID')
    training_tokens = tokens['training_counts']
    require(type(training_tokens) is dict and training_tokens and set(training_tokens) <= set(ACTION_VOCABULARY)
            and all(type(value) is int and value > 0 for value in training_tokens.values()), 'V3_TRAINING_TOKEN_COUNTS_INVALID')
    coverage = manifest.get('training_coverage', {})
    coverage_fields = {'procedure_declarations', 'procedure_call_targets', 'instructions', 'calls_from_child_procedures',
                       'programs_with_child_calls', 'earlier_value_inputs', 'earlier_value_returns', 'repeated_callee_uses', 'sentence_primitives'}
    require(type(coverage) is dict and set(coverage) == coverage_fields, 'V3_TRAINING_COVERAGE_FIELDS_INVALID')
    require(all(coverage.get('procedure_declarations', {}).get(name, 0) > 0
                and coverage.get('procedure_call_targets', {}).get(name, 0) > 0 for name in PROCEDURE_NAMES[1:])
            and coverage.get('programs_with_child_calls') == counts['train'] // 3,
            'V3_MANIFEST_TRAINING_COVERAGE_MISSING')
    require(all(coverage.get('sentence_primitives', {}).get(role, {}).get(str(family), 0) > 0
                for role in ('start', 'declaration', 'RUN', 'CALL', 'RETURN') for family in range(3)),
            'V3_MANIFEST_SENTENCE_COVERAGE_MISSING')
    require(manifest.get('native_outcomes_checked') is False
            and manifest.get('training_or_neural_execution_performed') is False, 'V3_CONSTRUCTION_CANNOT_CLAIM_NATIVE_RESULTS')
    return {'schema': MANIFEST_SCHEMA, 'dataset_id': identity, 'counts': counts, 'sha256': dict(hashes),
            'private_partition_opened': False, 'boundary': 'Public manifest consistency only; no private file read or task execution.'}


def write_dataset(output, seed=DEFAULT_SEED, counts=None, excluded_graph_signatures=None):
    dataset = generate_dataset(seed, counts, excluded_graph_signatures)
    path = Path(output)
    require(not path.exists(), 'V3_DATASET_OUTPUT_MUST_BE_NEW')
    path.mkdir(parents=True, exist_ok=False)
    files = {'train.json': dataset['splits']['train'], 'validation.json': dataset['splits']['validation'],
             'test_public.json': [permitted_view(task) for task in dataset['splits']['test']],
             'test_private.json': dataset['splits']['test']}
    hashes = {}
    for name, value in files.items():
        payload = canonical(value) + b'\n'
        with (path / name).open('xb') as stream:
            stream.write(payload)
        hashes[name] = sha256(payload).hexdigest()
    # Prove the actual cold JSON reload passes before reporting construction.
    cold = {'schema': SCHEMA, 'seed': seed, 'dataset_id': dataset['dataset_id'],
            'splits': {split: json.loads((path / name).read_bytes()) for split, name in (
                ('train', 'train.json'), ('validation', 'validation.json'), ('test', 'test_private.json'))}}
    checked = validate_dataset(cold, excluded_graph_signatures)
    require(canonical(checked) == canonical(dataset['manifest']), 'V3_COLD_RELOAD_VALIDATION_CHANGED')
    manifest = {**checked, 'sha256': hashes}
    validate_manifest(manifest, dataset['manifest']['counts'], expected_seed=seed,
                      excluded_graph_signatures=excluded_graph_signatures)
    with (path / 'dataset_manifest.json').open('xb') as stream:
        stream.write(canonical(manifest) + b'\n')
    return manifest
