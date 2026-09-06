"""Append the completed v6 dataset to known exposures. Never generate tasks."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import importlib.abc
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRIOR = ROOT/'records/contrast_v6_exclusions_001/inventory.json'
PRIOR_HASH = '1a8f7f39bee35f14ef002dfe90f2c6760cbe5c70436c7606fad32ee03f4c1256'
SOURCE = 'acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0'
JOB = 'cas-meta2-20260906064703-c0d74ffa'
SOURCE_ARCHIVE = '3153318664641ea3affdbef306929c3113bb937cd04113bce41d02f736e0f1f1'
EXTRACTED = ROOT/'records/aws_contrast_v6_001_review_extracted'
BASE = 'cloud_job/campaign/'


def require(value, code):
    if not value:
        raise ValueError(code)


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        require(fullname.split('.')[0] not in
                {'torch', 'casformer', 'cas_cjt', 'tensorflow', 'jax', 'cupy', 'boto3', 'botocore'},
                'NEURAL_OR_PROVIDER_IMPORT_REFUSED')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def read(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)()
                    for p in (path, *path.parents)), 'LINK_INPUT_REFUSED')
    require(path.is_file() and path.stat().st_size <= 32*1024**2, 'INPUT_SIZE_BOUND')
    raw = path.read_bytes()
    require(len(raw) <= 32*1024**2, 'INPUT_SIZE_BOUND')
    return raw


def digest(raw):
    return sha256(raw).hexdigest()


def decode(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            require(key not in result, 'DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))
    canonical(value)
    return value


def graph_set(values):
    require(type(values) is list and values == sorted(set(values))
            and all(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) for value in values),
            'GRAPH_SIGNATURE_SET_INVALID')
    return set(values)


def combine(previous, additions):
    prior = graph_set(previous['graph_signatures'])
    require(type(previous['count']) is int and previous['count'] == len(prior),
            'PRIOR_COUNT_INVALID')
    origins = previous['origins'].copy()
    require(type(additions) is dict and not set(origins).intersection(additions), 'ORIGIN_COLLISION')
    for name, values in additions.items():
        require(type(name) is str and name, 'ORIGIN_NAME_INVALID')
        checked = graph_set(sorted(values))
        origins[name] = {'count': len(checked), 'graph_signatures': sorted(checked)}
    union = set()
    for record in origins.values():
        values = graph_set(record['graph_signatures'])
        require(type(record['count']) is int and record['count'] == len(values), 'ORIGIN_COUNT_INVALID')
        union.update(values)
    require(prior <= union, 'PRIOR_EXPOSURE_REMOVED')
    return {'schema': 'cas-meta2-known-exposures/7', 'count': len(union),
            'graph_signatures': sorted(union), 'origins': origins}


def build(review_path, *, review_sha256, packet_sha256, output):
    for pin in (review_sha256, packet_sha256):
        require(type(pin) is str and re.fullmatch('[0-9a-f]{64}', pin), 'EXTERNAL_HASH_REQUIRED')
    review_raw = read(review_path)
    require(digest(review_raw) == review_sha256, 'REVIEW_RECEIPT_CHANGED')
    review = decode(review_raw)
    require(review.get('schema') == 'cas-meta2-offline-contrast-review/6'
            and review.get('status') == 'RECORDED_CONTRAST_RECOUNT_PASSED'
            and review.get('source_sha') == SOURCE and review.get('job') == JOB
            and review.get('source_archive_sha256') == SOURCE_ARCHIVE
            and review.get('packet_sha256') == packet_sha256
            and review.get('source_and_extraction_rechecked_at_end') is True,
            'COMPLETED_BOUND_V6_REVIEW_REQUIRED')
    rows = review['inventory']
    require(type(rows) is list and len(rows) == review['member_files'], 'INVENTORY_COUNT_CHANGED')
    inventory = {row['path']: row for row in rows}
    require(len(inventory) == len(rows), 'DUPLICATE_INVENTORY_MEMBER')
    sources = review['source_manifest']['files_sha256']
    # Check all reviewed local source bytes before importing program helpers.
    for name, expected in sources.items():
        require(name.startswith('research/') and '..' not in name.split('/')
                and '\\' not in name and ':' not in name, 'SOURCE_PATH_INVALID')
        require(digest(read(ROOT.parent.parent/name)) == expected, 'SOURCE_CHANGED:'+name)
    sys.meta_path.insert(0, Guard())
    sys.path.insert(0, str(ROOT))
    from cas_meta2.curriculum import graph_signature
    from cas_meta2.ir import validate_program

    source_files = {}
    def member(relative):
        name = BASE+relative
        raw = read(EXTRACTED/name)
        row = inventory[name]
        require(len(raw) == row['bytes'] and digest(raw) == row['sha256'],
                'REVIEWED_MEMBER_CHANGED:'+name)
        source_files[name] = row['sha256']
        return decode(raw)

    manifest = member('dataset/manifest.json')
    prior_raw = read(PRIOR)
    require(digest(prior_raw) == PRIOR_HASH, 'FROZEN_PRIOR_EXPOSURES_CHANGED')
    prior = decode(prior_raw)
    require(prior['count'] == 8053 and prior['schema'] == 'cas-meta2-known-exposures/6',
            'PRIOR_INVENTORY_IDENTITY_CHANGED')
    additions, actual_splits = {}, {}
    for split, filename in (('train', 'train.json'), ('validation', 'validation.json'),
                            ('test', 'test_private.json')):
        tasks = member('dataset/'+filename)
        require(source_files[BASE+'dataset/'+filename] == manifest['sha256'][filename],
                'DATASET_MANIFEST_BINDING_CHANGED')
        require(type(tasks) is list and len(tasks) == manifest['splits'][split]['tasks'],
                'DATASET_SPLIT_COUNT_CHANGED')
        depths = Counter(str(validate_program(t['target']['program'])['max_call_depth']) for t in tasks)
        require(dict(depths) == manifest['splits'][split]['depths'], 'DATASET_DEPTH_COUNTS_CHANGED')
        graphs = {graph_signature(task['target']['program']) for task in tasks}
        additions['contrast_registered_v6_'+split] = graphs
        actual_splits[split] = {'tasks': len(tasks), 'depths': dict(depths), 'unique_graphs': len(graphs)}
    record = combine(prior, additions)
    record.update(previous_inventory_sha256=PRIOR_HASH,
        completed_experiment={'job': JOB, 'source_sha': SOURCE,
            'source_archive_sha256': SOURCE_ARCHIVE, 'packet_sha256': packet_sha256,
            'review_sha256': review_sha256, 'dataset_id': manifest['dataset_id'],
            'manifest_sha256': source_files[BASE+'dataset/manifest.json'],
            'seed': manifest['seed'], 'splits': actual_splits},
        source_sha256=source_files, script_sha256=digest(read(__file__)),
        utc=datetime.now(timezone.utc).isoformat(), neural_execution=False, provider_execution=False,
        boundary='Known exposures, not new evaluation tasks. Keep this full union excluded from fresh '
                 'validation and test. The original256 may enter training only through the exact-byte '
                 'training import; never subtract its graphs from this inventory.')
    require(digest(read(review_path)) == review_sha256 and digest(read(PRIOR)) == PRIOR_HASH,
            'BOUND_INPUT_CHANGED')
    for name, expected in source_files.items():
        require(digest(read(EXTRACTED/name)) == expected, 'DATASET_CHANGED_DURING_BUILD')
    output = Path(output).absolute()
    require(output.parent.resolve() == HERE.resolve() and not output.exists(), 'NEW_LOCAL_INVENTORY_REQUIRED')
    with output.open('xb') as stream:
        stream.write(canonical(record)+b'\n')
    require(decode(read(output)) == record, 'OUTPUT_RECOUNT_FAILED')
    return {'count': record['count'], 'added_unique': record['count']-prior['count'],
            'actual_splits': actual_splits, 'sha256': digest(read(output)), 'neural_execution': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', required=True, type=Path)
    parser.add_argument('--review-sha256', required=True)
    parser.add_argument('--packet-sha256', required=True)
    parser.add_argument('--output', type=Path, default=HERE/'inventory.json')
    args = parser.parse_args()
    print(json.dumps(build(args.review, review_sha256=args.review_sha256,
                           packet_sha256=args.packet_sha256, output=args.output), indent=2))
