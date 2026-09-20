"""Separate private curriculum admission from public-only training inputs.

The parent validates private targets, then exports a directory without them.
The training loader checks an externally supplied manifest digest. It never
reads private targets or derives test programs with the symbolic parser.
Directory separation is not an operating-system access-control sandbox.
"""
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import re

from . import curriculum as c
from ..codec import action_to_tokens, validate_action, validate_public
from ..features_v2 import LosslessPublicTokenizer
from ..ir import validate_program

PUBLIC_FILES = ('train.json', 'validation.json', 'test_public.json')
ALL_FILES = (*PUBLIC_FILES, 'test_private.json')
MAX_FILE_BYTES = 32 * 1024 * 1024


def digest(value):
    return sha256(value).hexdigest()


def no_links(path):
    path = Path(path).absolute()
    c.require(not any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)()
                      for p in (path, *path.parents)), 'DATA_LINK_REFUSED')
    return path


def read(path):
    path = no_links(path)
    c.require(path.is_file() and path.stat().st_size <= MAX_FILE_BYTES, 'DATA_FILE_BOUND')
    with path.open('rb') as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    c.require(len(raw) <= MAX_FILE_BYTES, 'DATA_FILE_BOUND')
    return raw


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            c.require(key not in result, 'DUPLICATE_JSON_KEY')
            result[key] = value
        return result

    def constant(value):
        raise ValueError('NONFINITE_JSON_CONSTANT:' + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def expected_splits(config):
    config.checked()
    result = {}
    for split in ('train', 'validation'):
        flat = getattr(config, split + '_flat')
        pairs = getattr(config, split + '_pairs_per_cell')
        result[split] = {'tasks': flat + 8 * pairs,
                         'depths': {'1': flat, '2': 4 * pairs, '3': 4 * pairs},
                         'groups': flat + 4 * pairs}
    n = config.test_triplets
    result['test'] = {'tasks': 3 * n, 'depths': {'3': 2 * n, '4': n}, 'groups': n}
    return result


def checked_manifest(raw, *, expected_sha256, seed, config, excluded):
    c.require(type(expected_sha256) is str and re.fullmatch('[0-9a-f]{64}', expected_sha256)
              and digest(raw) == expected_sha256, 'EXTERNAL_MANIFEST_DIGEST_MISMATCH')
    m = decode(raw)
    fields = {'schema', 'dataset_id', 'splits', 'source', 'cross_split_graph_overlap',
              'cross_split_observation_overlap', 'native_outcomes_checked', 'neural_execution',
              'boundary', 'seed', 'config', 'sha256'}
    c.require(type(m) is dict and set(m) == fields, 'MANIFEST_FIELDS_INVALID')
    c.require(m['schema'] == c.SCHEMA and type(m['seed']) is int and m['seed'] == seed
              and c.canonical(m['config']) == c.canonical(asdict(config))
              and m['dataset_id'] == c.identity(seed, config, excluded), 'MANIFEST_IDENTITY_MISMATCH')
    c.require(c.canonical(m['splits']) == c.canonical(expected_splits(config)), 'MANIFEST_COUNTS_MISMATCH')
    c.require(m['source'] == c.wording.dependency_receipt(), 'MANIFEST_SOURCE_MISMATCH')
    c.require(all(m[k] is False for k in ('cross_split_graph_overlap', 'cross_split_observation_overlap',
                                        'native_outcomes_checked', 'neural_execution')),
              'MANIFEST_CLAIM_MISMATCH')
    c.require(type(m['boundary']) is str and type(m['sha256']) is dict
              and set(m['sha256']) == set(ALL_FILES)
              and all(type(v) is str and re.fullmatch('[0-9a-f]{64}', v) for v in m['sha256'].values()),
              'MANIFEST_FILE_DIGESTS_INVALID')
    return m


def directory(path, names):
    path = no_links(path)
    c.require(path.is_dir() and {p.name for p in path.iterdir()} == set(names), 'DATA_DIRECTORY_CONTENTS_INVALID')
    for name in names:
        c.require(no_links(path / name).is_file(), 'DATA_FILE_REQUIRED')
    return path


def prepare_training_bundle(source, output, *, expected_sha256, seed, config, excluded):
    """Parent-only admission. This function deliberately reads private labels."""
    source = directory(source, (*ALL_FILES, 'manifest.json'))
    output = no_links(output)
    c.require(not output.exists(), 'NEW_TRAINING_BUNDLE_REQUIRED')
    raw_manifest = read(source / 'manifest.json')
    m = checked_manifest(raw_manifest, expected_sha256=expected_sha256, seed=seed, config=config, excluded=excluded)
    raw = {name: read(source / name) for name in ALL_FILES}
    c.require(all(digest(value) == m['sha256'][name] for name, value in raw.items()), 'DATA_FILE_DIGEST_MISMATCH')
    splits = {split: decode(raw[name]) for split, name in
              (('train', 'train.json'), ('validation', 'validation.json'), ('test', 'test_private.json'))}
    report = c.validate({'schema': c.SCHEMA, 'seed': seed, 'config': asdict(config),
                         'dataset_id': m['dataset_id'], 'splits': splits}, excluded=excluded)
    c.require(c.canonical(report) == c.canonical({k: v for k, v in m.items() if k not in {'seed', 'config', 'sha256'}}),
              'COLD_MANIFEST_REPORT_MISMATCH')
    c.require(decode(raw['test_public.json']) == [c.permitted_view(t) for t in splits['test']],
              'PUBLIC_PRIVATE_MAPPING_MISMATCH')
    output.mkdir(parents=True, exist_ok=False)
    for name in PUBLIC_FILES:
        with (output / name).open('xb') as stream:
            stream.write(raw[name])
    with (output / 'manifest.json').open('xb') as stream:
        stream.write(raw_manifest)
    loaded = load_training_bundle(output, expected_sha256=expected_sha256, seed=seed, config=config, excluded=excluded)
    return {**loaded['receipt'], 'parent_private_validation_completed': True,
            'boundary': 'Parent checked private targets; exported only train/validation labels and test public inputs. '
                        'Trainer loader has no private-file read path. Not an OS access-control sandbox.'}


def load_training_bundle(path, *, expected_sha256, seed, config, excluded):
    """Trainer entry: does not open private test files, even to hash them."""
    path = directory(path, (*PUBLIC_FILES, 'manifest.json'))
    m = checked_manifest(read(path / 'manifest.json'), expected_sha256=expected_sha256,
                         seed=seed, config=config, excluded=excluded)
    values = {}
    for name in PUBLIC_FILES:
        raw = read(path / name)
        c.require(digest(raw) == m['sha256'][name], 'DATA_FILE_DIGEST_MISMATCH:' + name)
        values[name] = decode(raw)
        c.require(type(values[name]) is list, 'DATA_LIST_REQUIRED')
    ids = set()
    for split in ('train', 'validation'):
        tasks = values[split + '.json']
        counts = Counter()
        for t in tasks:
            c.require(type(t) is dict and set(t) == {'task_id', 'public', 'target', 'provenance',
                                                    'contrast_group', 'contrast_side'}, 'TRAIN_TASK_FIELDS_INVALID')
            c.require(type(t['task_id']) is str and t['task_id'] not in ids
                      and t['task_id'].startswith(f"meta2-v6-{m['dataset_id'][:16]}-{split}-"), 'TRAIN_TASK_ID_INVALID')
            ids.add(t['task_id'])
            validate_public(t['public'])
            validate_action(t['target'])
            counts[str(validate_program(t['target']['program'])['max_call_depth'])] += 1
        c.require(len(tasks) == m['splits'][split]['tasks'] and dict(counts) == m['splits'][split]['depths'],
                  'ACTUAL_TRAIN_DEPTH_COUNTS_MISMATCH')
    test = values['test_public.json']
    c.require(len(test) == m['splits']['test']['tasks'], 'ACTUAL_TEST_COUNT_MISMATCH')
    for public in test:
        validate_public(public)
    train, validation = values['train.json'], values['validation.json']
    tokenizer = LosslessPublicTokenizer.fit_train([t['public'] for t in train], max_length=1024)
    for public in [t['public'] for t in train + validation] + test:
        tokenizer.encode_public(public)
    train_tokens = {x for t in train for x in action_to_tokens(t['target'], max_length=256)}
    c.require(all(set(action_to_tokens(t['target'], max_length=256)) <= train_tokens for t in validation),
              'UNSEEN_VALIDATION_ACTION_TOKEN')
    return {'train': train, 'validation': validation, 'test_public': test, 'tokenizer': tokenizer,
            'manifest': m, 'receipt': {'schema': 'cas-meta2-training-bundle/6', 'dataset_id': m['dataset_id'],
                'manifest_sha256': expected_sha256, 'loaded_sha256': {name: m['sha256'][name] for name in PUBLIC_FILES},
                'splits': m['splits'], 'tokenizer_sha256': tokenizer.digest,
                'tokenizer_fit_examples': len(train), 'private_labels_read_by_loader': False,
                'test_programs_parsed_by_loader': False, 'neural_execution': False}}
