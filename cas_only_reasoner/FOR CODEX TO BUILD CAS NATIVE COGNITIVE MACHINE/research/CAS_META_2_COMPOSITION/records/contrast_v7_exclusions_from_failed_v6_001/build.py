"""Append exposures from the failed v6 experiment. Never generate tasks or claim success."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HELPER_COMMIT = '80e44f20a3f2c66a62754212729ce6e11ff9c8fe'
HELPER_HASH = '2d8e2a8afbfbc475ae37b278050eddb467cef4d7825f273590a52d72f2dc6da8'
AUDIT_HASH = '68b3051902428b71b8c85a3295a52d362f8d321e15f14ff5a2347721157b4435'
REVIEW = ROOT/'records/contrast_failure_review_v6_001/run_002/failure_review_receipt.json'
REVIEW_HASH = 'd479c90f711d417f2f585b87a0b746e250db8db12029df1586a4fbabf3b82420'
PACKET = ROOT/'records/aws_contrast_v6_001/cloud_artifacts.zip'
PACKET_HASH = 'db52b01670c9864da7eeecac25c36446986c6b0b625f6d1b6310bbfdcad55def'
SOURCE = 'acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0'
SOURCE_ZIP = ROOT/'records/aws_contrast_v6_source_001'
SOURCE_HASH = '3153318664641ea3affdbef306929c3113bb937cd04113bce41d02f736e0f1f1'
JOB = 'cas-meta2-20260906064703-c0d74ffa'
EXTRACTED = ROOT/'records/aws_contrast_v6_001_failure_extracted'
BASE = 'cloud_job/campaign/'
PRIOR = ROOT/'records/contrast_v6_exclusions_001/inventory.json'
PRIOR_HASH = '1a8f7f39bee35f14ef002dfe90f2c6760cbe5c70436c7606fad32ee03f4c1256'
PROTOTYPE = ROOT/'records/contrast_curriculum_v6_probe_001/tasks.json'
PROTOTYPE_HASH = 'ed6bb0978d34b549917e1ea1b846091f103577936f846bc01db152b19ddbac46'


def require(value, code):
    if not value:
        raise ValueError(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def decode(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, 'DUPLICATE_JSON_FIELD')
            value[key] = item
        return value
    result = json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))
    canonical(result)
    return result


def regular(path):
    path = Path(path).absolute()
    require(path.is_file() and not any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)()
            for p in (path, *path.parents)), 'NONREGULAR_INPUT')
    return path


def file_hash(path):
    with regular(path).open('rb') as stream:
        return __import__('hashlib').file_digest(stream, 'sha256').hexdigest()


def verify_bytes(raw, expected, code):
    require(type(expected) is str and re.fullmatch('[a-f0-9]{64}', expected)
            and sha256(raw).hexdigest() == expected, code)
    return raw


def read_json(path, pin):
    path = regular(path)
    require(path.stat().st_size <= 32*1024**2, 'JSON_SIZE_BOUND')
    raw = path.read_bytes()
    require(len(raw) <= 32*1024**2, 'JSON_SIZE_BOUND')
    return decode(verify_bytes(raw, pin, 'PINNED_JSON_CHANGED'))


def admit(review):
    require(review.get('schema') == 'cas-meta2-contrast-failure-review/6'
        and review.get('status') == 'FAILED_RUN_TRAINING_RECOUNT_PASSED'
        and all(review.get(k) is True for k in ('audit_completed', 'training_recount_passed',
                                               'source_and_extraction_rechecked_at_end', 'collection_full_index_verified'))
        and all(review.get(k) is False for k in ('campaign_completed', 'native_evaluation_completed',
                                                 'neural_execution', 'provider_calls', 'learning_accepted', 'release_accepted'))
        and review.get('source_sha') == SOURCE and review.get('source_archive_sha256') == SOURCE_HASH
        and review.get('packet_sha256') == PACKET_HASH and review.get('job') == JOB
        and review.get('source_files_verified') == 538 and review.get('protected_files_verified') == 316,
        'PINNED_FAILED_REVIEW_REQUIRED')
    collection = review['collection']
    require(type(collection.get('returncode')) is int and collection['returncode'] != 0
        and collection.get('partial_evidence') is False
        and type(collection.get('omitted_full_file_count')) is int
        and collection['omitted_full_file_count'] == 0, 'FAILED_COMPLETE_COLLECTION_REQUIRED')
    require(Path(review['extraction']['path']).resolve() == EXTRACTED.resolve()
            and review['extraction']['all_member_bytes_verified_after_write'] is True
            and review['extraction']['files_verified'] == review['member_files'] == len(review['inventory']),
            'EXTRACTION_IDENTITY_CHANGED')


def load_committed(name, path, expected, repo):
    raw = subprocess.check_output(['git', 'cat-file', 'blob',
        HELPER_COMMIT+':'+path.relative_to(repo).as_posix()], cwd=repo)
    verify_bytes(raw, expected, 'COMMITTED_HELPER_PIN_CHANGED')
    require(file_hash(path) == expected, 'LOCAL_HELPER_SOURCE_CHANGED')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def recount(tasks, expected, graph_signature, validate_program):
    require(type(tasks) is list and len(tasks) == expected['tasks'], 'DATASET_SPLIT_COUNT_CHANGED')
    require(len({t['task_id'] for t in tasks}) == len(tasks), 'DUPLICATE_TASK_ID')
    depths, depth_graphs, all_graphs = Counter(), {}, set()
    for task in tasks:
        program = task['target']['program']
        depth = str(validate_program(program)['max_call_depth'])
        signature = graph_signature(program)
        require(task['provenance']['graph_signature'] == signature
                and str(task['provenance']['depth']) == depth, 'TASK_GRAPH_PROVENANCE_CHANGED')
        depths[depth] += 1
        depth_graphs.setdefault(depth, set()).add(signature)
        all_graphs.add(signature)
    require(dict(depths) == expected['depths'], 'DATASET_DEPTH_COUNTS_CHANGED')
    return all_graphs, {'tasks': len(tasks), 'depths': dict(depths), 'unique_graphs': len(all_graphs),
                        'unique_graphs_by_depth': {d: len(s) for d, s in sorted(depth_graphs.items())}}


def retained_prototype(prior, combined, graphs):
    require(len(graphs) == 256 and prior['origins']['contrast_prototype_seed_926601'] ==
        {'count': 256, 'graph_signatures': sorted(graphs)}, 'PROTOTYPE_PRIOR_ORIGIN_CHANGED')
    require(graphs <= set(prior['graph_signatures']) <= set(combined['graph_signatures']),
            'KNOWN_EXPOSURE_REMOVED')
    require(prior['origins']['contrast_prototype_seed_926601'] ==
            combined['origins']['contrast_prototype_seed_926601'], 'PROTOTYPE_ORIGIN_CHANGED')


def build(output):
    script_pin = file_hash(__file__)
    review = read_json(REVIEW, REVIEW_HASH)
    admit(review)
    require(file_hash(PACKET) == PACKET_HASH and file_hash(SOURCE_ZIP) == SOURCE_HASH, 'ARCHIVE_PIN_CHANGED')
    require(PACKET.stat().st_size == review['packet_bytes'], 'PACKET_SIZE_CHANGED')
    repo = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=ROOT, text=True).strip())
    require(subprocess.check_output(['git', 'rev-parse', HELPER_COMMIT+'^{commit}'], cwd=repo,
                                   text=True).strip() == HELPER_COMMIT, 'EXACT_HELPER_COMMIT_REQUIRED')
    helper_path = ROOT/'records/contrast_v7_exclusions_001/build.py'
    helper = load_committed('_failed_exposure_union', helper_path, HELPER_HASH, repo)
    audit_path = ROOT/'records/contrast_stored_audit_v6_001/audit.py'
    audit = load_committed('_failed_exposure_source', audit_path, AUDIT_HASH, repo)
    require(not audit.FORBIDDEN.intersection(n.split('.')[0] for n in sys.modules), 'PRELOADED_FORBIDDEN_MODULE')
    sys.meta_path.insert(0, audit.Guard())
    sys.path.insert(0, str(ROOT))
    manifest, archive_helper = audit.load_bound_source(SOURCE_ZIP, SOURCE_HASH, SOURCE)
    require(manifest == review['source_manifest'], 'FROZEN_SOURCE_MANIFEST_CHANGED')
    files = audit.Files(EXTRACTED, review['inventory'], archive_helper)
    from cas_meta2.curriculum import graph_signature
    from cas_meta2.ir import validate_program

    source_files = {}
    def member(name):
        path = BASE+'dataset/'+name
        value = files.json(path)
        source_files[path] = files.inventory[path]['sha256']
        return value
    dataset = member('manifest.json')
    require(dataset == review['dataset_manifest'] and source_files[BASE+'dataset/manifest.json'] ==
        review['training_gate']['manifest_sha256'] == review['binding_checks']['dataset_manifest_sha256'],
        'REVIEW_DATASET_MANIFEST_CHANGED')
    prior = read_json(PRIOR, PRIOR_HASH)
    require(prior['schema'] == 'cas-meta2-known-exposures/6' and prior['count'] == 8053,
            'PRIOR_INVENTORY_IDENTITY_CHANGED')
    additions, splits = {}, {}
    for split, filename in (('train', 'train.json'), ('validation', 'validation.json'), ('test', 'test_private.json')):
        tasks = member(filename)
        require(source_files[BASE+'dataset/'+filename] == dataset['sha256'][filename], 'DATASET_BYTES_CHANGED')
        graphs, recounted = recount(tasks, dataset['splits'][split], graph_signature, validate_program)
        additions['contrast_failed_v6_'+split] = graphs
        splits[split] = {**recounted, 'source_path': BASE+'dataset/'+filename,
                         'source_sha256': source_files[BASE+'dataset/'+filename]}
    prototypes = read_json(PROTOTYPE, PROTOTYPE_HASH)
    require(type(prototypes) is list and len(prototypes) == 256, 'PROTOTYPE_TASK_COUNT_CHANGED')
    prototype_graphs = {graph_signature(t['target']['program']) for t in prototypes}
    record = helper.combine(prior, additions)
    retained_prototype(prior, record, prototype_graphs)
    new_graphs = set().union(*additions.values())
    require(new_graphs <= set(record['graph_signatures']), 'FAILED_EXPOSURE_MISSING')
    record.update(
        previous_inventory_sha256=PRIOR_HASH, previous_count=8053,
        failed_experiment={'job': JOB, 'source_sha': SOURCE, 'source_archive_sha256': SOURCE_HASH,
            'packet_sha256': PACKET_HASH, 'review_sha256': REVIEW_HASH,
            'dataset_id': dataset['dataset_id'], 'manifest_sha256': source_files[BASE+'dataset/manifest.json'],
            'seed': dataset['seed'], 'splits': splits, 'campaign_completed': False,
            'native_evaluation_completed': False, 'collection_returncode': review['collection']['returncode']},
        generated_exposures_from_failed_experiment=True,
        added_unique=record['count']-prior['count'], generated_unique_graphs=len(new_graphs),
        original_prototype={'tasks_sha256': PROTOTYPE_HASH, 'tasks': 256, 'unique_graphs': 256,
            'all_preserved_in_fresh_exclusions': True, 'training_only_exact_byte_import_exception': True},
        source_sha256=source_files, source_files_verified=len(manifest['files_sha256']),
        protected_files_verified=manifest['protected_baseline_files'],
        helper_source={'commit': HELPER_COMMIT, 'combine_sha256': HELPER_HASH, 'source_audit_sha256': AUDIT_HASH},
        script_sha256=script_pin, utc=datetime.now(timezone.utc).isoformat(),
        neural_execution=False, provider_execution=False, graph_generation=False,
        native_success_claim=False, learning_accepted=False,
        boundary='Known generated exposures from a FAILED experiment, not native success or new evaluation. '
                 'Exclude the complete union from all fresh curriculum partitions. The literal original 256 '
                 'may be appended only through the separate exact-byte training-only import. Never remove '
                 'their signatures from this exclusion inventory.')
    require(file_hash(REVIEW) == REVIEW_HASH and file_hash(PRIOR) == PRIOR_HASH
        and file_hash(PROTOTYPE) == PROTOTYPE_HASH and file_hash(PACKET) == PACKET_HASH
        and file_hash(SOURCE_ZIP) == SOURCE_HASH, 'INPUT_CHANGED_DURING_BUILD')
    audit.check_source(manifest)
    files.verify_all()
    require(file_hash(helper_path) == HELPER_HASH and file_hash(audit_path) == AUDIT_HASH
            and file_hash(__file__) == script_pin, 'BUILDER_SOURCE_CHANGED')
    require(not audit.FORBIDDEN.intersection(n.split('.')[0] for n in sys.modules), 'FORBIDDEN_MODULE_IMPORTED')
    output = Path(output).absolute()
    require(output.parent == HERE and output.name == 'inventory.json' and not output.exists(),
            'NEW_OWNED_INVENTORY_REQUIRED')
    with output.open('xb') as stream:
        stream.write(canonical(record)+b'\n')
    pin = file_hash(output)
    require(read_json(output, pin) == record, 'OUTPUT_READBACK_CHANGED')
    return {'schema': 'cas-meta2-failed-exposure-build/7', 'completed': True,
        'inventory_sha256': pin, 'inventory_path': str(output), 'count': record['count'],
        'previous_count': 8053, 'added_unique': record['added_unique'],
        'generated_unique_graphs': len(new_graphs), 'actual_splits': splits,
        'all_prior_exposures_preserved': True, 'all_original_256_preserved': True,
        'review_sha256': REVIEW_HASH, 'packet_sha256': PACKET_HASH, 'prior_inventory_sha256': PRIOR_HASH,
        'source_sha': SOURCE, 'source_archive_sha256': SOURCE_HASH,
        'source_and_extraction_rechecked_at_end': True, 'source_files_verified': 538,
        'protected_files_verified': 316, 'helper_source': record['helper_source'],
        'script_sha256': script_pin, 'neural_execution': False, 'provider_execution': False,
        'graph_generation': False, 'native_success_claim': False, 'learning_accepted': False,
        'boundary': record['boundary']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE/'inventory.json')
    args = parser.parse_args()
    require(not (HERE/'receipt.json').exists(), 'NEW_EXECUTION_RECEIPT_REQUIRED')
    start = datetime.now(timezone.utc).isoformat()
    result = build(args.output)
    result.update(command=[sys.executable, *sys.argv], cwd=str(Path.cwd()), python=sys.version,
                  started_utc=start, finished_utc=datetime.now(timezone.utc).isoformat(), returncode=0)
    with (HERE/'receipt.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

