"""Source-pinned v7 public training inputs; no models or private loader reads.

The exporter is parent-only local preparation and invokes the parent validator.
The loader is independent of that validator: no Context, Git, parser, private
targets, task generation, import guards, or neural/provider imports. A future
registered coordinator must supply both external pins and package these bytes.
"""
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
import importlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INTEGRATION = 'records/prototype_training_integration_v7_001'
PROTOTYPE = 'records/contrast_curriculum_v6_probe_001'
FROZEN_SOURCE = 'acbb266fbcdb6efcd69808f6f0f9b7b1e36b7ed0'
TASKS_SHA256 = 'ed6bb0978d34b549917e1ea1b846091f103577936f846bc01db152b19ddbac46'
SCHEMA = 'cas-meta2-prototype-training-integration/7'
PUBLIC_FILES = ('train.json', 'validation.json', 'test_public.json', 'base_train.json',
                'base_manifest.json', 'training_imports.json', 'tokenizer.json')
PARENT_FILES = (*PUBLIC_FILES, 'test_private.json')
FROZEN_FILES = ('cas_meta2/__init__.py', 'cas_meta2/ir.py', 'cas_meta2/codec.py',
    'cas_meta2/curriculum.py', 'cas_meta2/curriculum_v2.py', 'cas_meta2/curriculum_v3.py',
    'cas_meta2/features_v2.py', 'cas_meta2/exclusions_v3.json', 'cas_meta2/development_exclusions_v3.json',
    'cas_meta2/contrast_v6/__init__.py', 'cas_meta2/contrast_v6/curriculum.py', 'cas_meta2/contrast_v6/data.py',
    *(PROTOTYPE+'/'+name for name in ('tasks.json', 'receipt.json', 'build.py', 'verify.py')))
MAX_BYTES = 32*1024**2
SHA = re.compile('[0-9a-f]{64}\\Z')
DIAGNOSTIC = {'train_flat': 32, 'train_pairs_per_cell': 8, 'validation_flat': 8,
              'validation_pairs_per_cell': 2, 'test_triplets': 3}
REGISTERED_SHAPE = {'train_flat': 128, 'train_pairs_per_cell': 64, 'validation_flat': 32,
                    'validation_pairs_per_cell': 8, 'test_triplets': 24}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(raw):
    return sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'PUBLIC_INPUT_DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('PUBLIC_INPUT_NONFINITE_JSON')))
    canonical(value)
    return value


def no_links(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)() for p in (path, *path.parents)),
            'PUBLIC_INPUT_LINK_REFUSED')
    return path


def read(path):
    path = no_links(path)
    require(path.is_file() and path.stat().st_size <= MAX_BYTES, 'PUBLIC_INPUT_FILE_BOUND')
    with path.open('rb') as stream:
        raw = stream.read(MAX_BYTES+1)
    require(len(raw) <= MAX_BYTES, 'PUBLIC_INPUT_FILE_BOUND')
    return raw


def directory(path):
    path = no_links(path)
    require(path.is_dir() and {p.name for p in path.iterdir()} == {*PUBLIC_FILES, 'manifest.json'},
            'PUBLIC_INPUT_DIRECTORY_CONTENTS')
    return path


def expected_counts(seed, config):
    require(type(seed) is int and 0 <= seed < 2**63 and seed != 2026092601, 'PUBLIC_INPUT_BASE_SEED_REFUSED')
    values = asdict(config) if not isinstance(config, dict) else dict(config)
    require(set(values) == set(DIAGNOSTIC) and all(type(v) is int for v in values.values()), 'PUBLIC_INPUT_CONFIG_FIELDS')
    require((seed == 926603 and values == DIAGNOSTIC) or (seed != 926603 and values == REGISTERED_SHAPE),
            'PUBLIC_INPUT_UNREGISTERED_COUNT_SHAPE')
    flat, pairs = values['train_flat'], values['train_pairs_per_cell']
    vflat, vpairs, triplets = values['validation_flat'], values['validation_pairs_per_cell'], values['test_triplets']
    return {'train': {'tasks': flat+8*pairs+256, 'depths': {'1': flat, '2': 4*pairs+128, '3': 4*pairs+128}},
            'validation': {'tasks': vflat+8*vpairs, 'depths': {'1': vflat, '2': 4*vpairs, '3': 4*vpairs}},
            'test': {'tasks': 3*triplets, 'depths': {'3': 2*triplets, '4': triplets}}}


def verify_source(source, *, expected_loader_sha256, root):
    require(type(expected_loader_sha256) is str and SHA.fullmatch(expected_loader_sha256), 'EXTERNAL_PUBLIC_LOADER_PIN_REQUIRED')
    require(digest(read(Path(__file__))) == expected_loader_sha256, 'PUBLIC_LOADER_BYTES_CHANGED')
    require(type(source) is dict and set(source) == {'frozen_source_sha', 'frozen_files_sha256', 'adapter_sha256', 'adapter_schema'}
            and source['frozen_source_sha'] == FROZEN_SOURCE and source['adapter_schema'] == SCHEMA,
            'PUBLIC_INPUT_SOURCE_IDENTITY')
    mapping = source['frozen_files_sha256']
    require(type(mapping) is dict and set(mapping) == set(FROZEN_FILES)
            and all(type(v) is str and SHA.fullmatch(v) for v in mapping.values())
            and mapping[PROTOTYPE+'/tasks.json'] == TASKS_SHA256, 'PUBLIC_INPUT_SOURCE_CLOSURE')
    require(type(source['adapter_sha256']) is str and SHA.fullmatch(source['adapter_sha256']), 'PUBLIC_INPUT_ADAPTER_PIN')
    for name, expected in {**mapping, INTEGRATION+'/adapter.py': source['adapter_sha256']}.items():
        require(digest(read(Path(root)/name)) == expected, 'PUBLIC_INPUT_HELPER_BYTES_CHANGED:'+name)
    return {'public_loader_sha256': expected_loader_sha256, **source}


def _helpers(root):
    """Import only the directly hash-checked pure modules, with no persistent hooks."""
    names = {'cas_meta2': 'cas_meta2/__init__.py', 'cas_meta2.contrast_v6': 'cas_meta2/contrast_v6/__init__.py'}
    names.update({path[:-3].replace('/', '.'): path for path in FROZEN_FILES
                  if path.startswith('cas_meta2/') and path.endswith('.py') and not path.endswith('__init__.py')})
    for name, path in names.items():
        if name in sys.modules:
            require(getattr(sys.modules[name], '__file__', None) is not None
                    and Path(sys.modules[name].__file__).resolve() == (Path(root)/path).resolve(), 'PUBLIC_INPUT_PRELOADED_HELPER_PATH')
    old_path = list(sys.path)
    try:
        sys.path.insert(0, str(root))
        c = importlib.import_module('cas_meta2.contrast_v6.curriculum')
        d = importlib.import_module('cas_meta2.contrast_v6.data')
        codec = importlib.import_module('cas_meta2.codec')
    finally:
        sys.path[:] = old_path
    return c, d, codec


def _manifest(raw, pin):
    require(type(pin) is str and SHA.fullmatch(pin) and digest(raw) == pin, 'EXTERNAL_PUBLIC_MANIFEST_MISMATCH')
    m = decode(raw)
    fields = {'schema', 'dataset_id', 'source', 'base', 'prototype', 'splits', 'training_append_count',
        'pair_members_kept_together', 'heldout_bytes_unchanged', 'split_safety', 'tokens', 'sha256',
        'neural_execution', 'native_outcomes_checked', 'training_performed', 'parent_reads_private_test_targets', 'boundary'}
    require(type(m) is dict and set(m) == fields and m['schema'] == SCHEMA, 'PUBLIC_INPUT_MANIFEST_FIELDS')
    require(type(m['sha256']) is dict and set(m['sha256']) == set(PARENT_FILES)
            and all(type(v) is str and SHA.fullmatch(v) for v in m['sha256'].values()), 'PUBLIC_INPUT_FILE_PIN_SET')
    require(all(m[key] is False for key in ('neural_execution', 'native_outcomes_checked', 'training_performed'))
            and m['parent_reads_private_test_targets'] is True and m['pair_members_kept_together'] is True
            and type(m['training_append_count']) is int and m['training_append_count'] == 256,
            'PUBLIC_INPUT_PREPARATION_BOUNDARY')
    return m


def _import_map(base_train, originals):
    return {'schema': 'cas-meta2-training-import-map/7', 'destination_split': 'train',
        'source_tasks_sha256': TASKS_SHA256, 'original_task_count': 256, 'original_pair_count': 128,
        'original_order_preserved': True, 'base_prefix_count': len(base_train),
        'records': [{'train_index': len(base_train)+i, 'original_index': i, 'task_id': task['task_id'],
            'original_record_sha256': digest(canonical(task)), 'pair_id': task['contrast']['pair_id'],
            'side': task['contrast']['side'], 'family': task['contrast']['family'],
            'original_provenance_sha256': digest(canonical(task['provenance']))} for i, task in enumerate(originals)]}


def load_training_bundle(path, *, expected_sha256, seed, config, excluded, expected_loader_sha256, root=ROOT):
    """Public-only initial/reload/checker path. Never calls the parent validator."""
    counts = expected_counts(seed, config)
    path, root = directory(path), no_links(root)
    raw_manifest = read(path/'manifest.json')
    m = _manifest(raw_manifest, expected_sha256)
    sources = verify_source(m['source'], expected_loader_sha256=expected_loader_sha256, root=root)
    c, d, codec = _helpers(root)
    cfg = c.Config(**(dict(config) if isinstance(config, dict) else asdict(config))).checked()
    raw = {name: read(path/name) for name in PUBLIC_FILES}
    require(all(digest(value) == m['sha256'][name] for name, value in raw.items()), 'PUBLIC_INPUT_FILE_DIGEST')
    values = {name: decode(value) for name, value in raw.items()}
    base = d.checked_manifest(raw['base_manifest.json'], expected_sha256=m['base']['manifest_sha256'],
                             seed=seed, config=cfg, excluded=excluded)
    require(m['base'] == {'manifest_sha256': digest(raw['base_manifest.json']), 'dataset_id': base['dataset_id'],
        'seed': seed, 'config': asdict(cfg), 'exclusions_sha256': digest(canonical(sorted(excluded))),
        'exclusion_count': len(excluded), 'splits': base['splits']}, 'PUBLIC_INPUT_BASE_IDENTITY')
    require(digest(raw['base_train.json']) == base['sha256']['train.json'], 'PUBLIC_INPUT_BASE_TRAIN_CHANGED')
    for name in ('validation.json', 'test_public.json'):
        require(digest(raw[name]) == base['sha256'][name], 'PUBLIC_INPUT_HELDOUT_BYTES_CHANGED:'+name)
    # The private digest is compared only as opaque metadata. No private path is constructed.
    require(m['heldout_bytes_unchanged'] == {name: base['sha256'][name] for name in
        ('validation.json', 'test_public.json', 'test_private.json')}
        and m['sha256']['test_private.json'] == base['sha256']['test_private.json'], 'PUBLIC_INPUT_PRIVATE_METADATA_CHANGED')
    identity = {'schema': SCHEMA, 'source': m['source'], 'base_manifest_sha256': digest(raw['base_manifest.json']),
                'base_dataset_id': base['dataset_id'], 'prototype_tasks_sha256': TASKS_SHA256}
    require(m['dataset_id'] == digest(canonical(identity)) and canonical(m['splits']) == canonical(counts), 'PUBLIC_INPUT_DATASET_COUNTS_IDENTITY')
    original_raw = read(root/PROTOTYPE/'tasks.json')
    require(digest(original_raw) == TASKS_SHA256, 'PUBLIC_INPUT_ORIGINAL_PIN_CHANGED')
    originals = decode(original_raw)
    prototype_receipt = decode(read(root/PROTOTYPE/'receipt.json'))
    require(type(originals) is list and len(originals) == 256 and prototype_receipt['task_count'] == 256
            and prototype_receipt['pair_count'] == 128, 'PUBLIC_INPUT_ORIGINAL_COUNTS')
    expected_prototype = {'tasks': 256, 'pairs': 128,
        'pair_counts': {'2/step_input': 32, '2/call_target': 32, '3/step_input': 32, '3/call_target': 32},
        'depths': {'2': 128, '3': 128}, 'public_meaning_checked': True, 'source_path': PROTOTYPE+'/tasks.json',
        'tasks_sha256': TASKS_SHA256, 'receipt_sha256': m['source']['frozen_files_sha256'][PROTOTYPE+'/receipt.json'],
        'allowed_split': 'train', 'fresh_evaluation': False, 'original_provenance_preserved': True}
    require(canonical(m['prototype']) == canonical(expected_prototype), 'PUBLIC_INPUT_PROTOTYPE_METADATA')
    require(m['split_safety'] == {'prototype_graph_overlap': False, 'prototype_observation_overlap': False,
        'prototype_task_id_overlap': False, 'policy': 'Exact original records are training-only; no graph-wide exemption.'},
        'PUBLIC_INPUT_PARENT_SPLIT_METADATA')
    train, base_train, validation, publics = (values[name] for name in
        ('train.json', 'base_train.json', 'validation.json', 'test_public.json'))
    require(all(type(value) is list for value in (train, base_train, validation, publics)), 'PUBLIC_INPUT_LIST_REQUIRED')
    require(len(base_train) == base['splits']['train']['tasks']
            and len(train) == counts['train']['tasks'] and len(publics) == counts['test']['tasks'], 'PUBLIC_INPUT_ACTUAL_COUNTS')
    require(canonical(train) == canonical(base_train+originals), 'PUBLIC_INPUT_EXACT_APPEND_REQUIRED')
    require(canonical(values['training_imports.json']) == canonical(_import_map(base_train, originals)), 'PUBLIC_INPUT_IMPORT_MAP_CHANGED')
    ids, actual_counts = set(), {}
    for split, tasks in (('train', base_train), ('validation', validation)):
        depths = Counter()
        for task in tasks:
            require(type(task) is dict and set(task) == {'task_id', 'public', 'target', 'provenance', 'contrast_group', 'contrast_side'},
                    'PUBLIC_INPUT_BASE_RECORD_FIELDS')
            require(task['task_id'] == f"meta2-v6-{base['dataset_id'][:16]}-{split}-{task['contrast_group']}-{task['contrast_side']}"
                    and task['task_id'] not in ids and task['provenance']['evaluation_group'] == split, 'PUBLIC_INPUT_BASE_RECORD_ID')
            ids.add(task['task_id'])
            codec.validate_public(task['public'])
            codec.validate_action(task['target'])
            depth = c.validate_program(task['target']['program'])['max_call_depth']
            require(type(task['provenance']['depth']) is int and task['provenance']['depth'] == depth, 'PUBLIC_INPUT_BASE_RECORD_DEPTH')
            depths[str(depth)] += 1
        require(dict(depths) == base['splits'][split]['depths'] and len(tasks) == base['splits'][split]['tasks'],
                'PUBLIC_INPUT_BASE_DEPTH_COUNTS')
        actual_counts[split] = {'tasks': len(tasks), 'depths': dict(depths)}
    for task in originals:
        require(set(task) == {'task_id', 'public', 'target', 'provenance', 'contrast'}
                and task['task_id'] not in ids, 'PUBLIC_INPUT_ORIGINAL_RECORD_FIELDS')
        ids.add(task['task_id'])
        codec.validate_public(task['public'])
        codec.validate_action(task['target'])
    depths = Counter(str(c.validate_program(t['target']['program'])['max_call_depth']) for t in train)
    actual_counts['train'] = {'tasks': len(train), 'depths': dict(depths)}
    require(actual_counts == {name: counts[name] for name in ('train', 'validation')}, 'PUBLIC_INPUT_MERGED_DEPTH_COUNTS')
    original_graphs = {c.graph_signature(t['target']['program']) for t in originals}
    original_payloads = {struct.pack('<8f', *o['values']) for t in originals for o in t['public']['observations']}
    for task in base_train+validation:
        require(c.graph_signature(task['target']['program']) not in original_graphs, 'PUBLIC_INPUT_PROTOTYPE_GRAPH_OVERLAP')
    for public in [t['public'] for t in base_train+validation]+publics:
        codec.validate_public(public)
        require(not any(struct.pack('<8f', *o['values']) in original_payloads for o in public['observations']),
                'PUBLIC_INPUT_PROTOTYPE_OBSERVATION_OVERLAP')
    tokenizer = c.LosslessPublicTokenizer.fit_train([t['public'] for t in train], max_length=1024)
    require(canonical(tokenizer.to_dict()) == canonical(values['tokenizer.json']), 'PUBLIC_INPUT_TRAIN_ONLY_TOKENIZER')
    tokens = {token for task in train for token in codec.action_to_tokens(task['target'], max_length=256)}
    for task in validation:
        require(set(codec.action_to_tokens(task['target'], max_length=256)) <= tokens, 'PUBLIC_INPUT_VALIDATION_ACTION_TOKEN')
    maxima = {}
    for split, tasks in (('train', train), ('validation', validation)):
        maxima[split] = {'input_tokens': max(len(tokenizer.encode_public(t['public'])['ids']) for t in tasks),
                         'action_tokens': max(len(codec.action_to_tokens(t['target'], max_length=256)) for t in tasks)}
    test_input_max = max(len(tokenizer.encode_public(public)['ids']) for public in publics)
    require(m['tokens']['tokenizer_fit_split'] == 'train_only' and m['tokens']['fit_examples'] == len(train)
            and m['tokens']['tokenizer_sha256'] == tokenizer.digest and m['tokens']['input_token_limit'] == 1024
            and m['tokens']['action_token_limit'] == 256 and m['tokens']['positive_action_token_coverage'] is True
            and m['tokens']['actual_maxima']['test']['input_tokens'] == test_input_max
            and type(m['tokens']['actual_maxima']['test']['action_tokens']) is int
            and 1 <= m['tokens']['actual_maxima']['test']['action_tokens'] <= 256
            and all(m['tokens']['actual_maxima'][key] == value for key, value in maxima.items()),
            'PUBLIC_INPUT_TOKENIZER_METADATA')
    require(verify_source(m['source'], expected_loader_sha256=expected_loader_sha256, root=root) == sources
            and read(path/'manifest.json') == raw_manifest and all(read(path/name) == value for name, value in raw.items()),
            'PUBLIC_INPUT_CHANGED_DURING_LOAD')
    return {'train': train, 'validation': validation, 'test_public': publics, 'tokenizer': tokenizer, 'manifest': m,
        'receipt': {'schema': 'cas-meta2-public-training-bundle/7', 'dataset_id': m['dataset_id'],
            'manifest_sha256': expected_sha256, 'loaded_sha256': {name: m['sha256'][name] for name in PUBLIC_FILES},
            'splits': counts, 'base_train_examples': len(base_train), 'imported_train_examples': 256,
            'tokenizer_sha256': tokenizer.digest, 'tokenizer_fit_examples': len(train), 'source': sources,
            'private_labels_read_by_loader': False, 'test_programs_parsed_by_loader': False,
            'parent_validation_replayed_by_loader': False, 'private_test_depths_recounted': False,
            'private_test_graph_separation_replayed': False, 'neural_execution': False,
            'boundary': 'Exact known training import and public-input checks. Private graph separation/target checks remain parent-admitted, externally pinned facts; no private test parser/read or model execution.'}}


def export_training_bundle(source, output, *, expected_sha256, seed, config, excluded,
                           expected_loader_sha256, parent_ctx=None, root=ROOT):
    """Parent-only preparation; validates private targets then exports no private file."""
    expected_counts(seed, config)
    source, output, root = no_links(source), no_links(output), no_links(root)
    require(output.resolve().is_relative_to(root.resolve()) and output.resolve() != root.resolve()
            and not output.exists() and not output.resolve().is_relative_to(source.resolve())
            and not source.resolve().is_relative_to(output.resolve()), 'NEW_PUBLIC_EXPORT_REQUIRED')
    raw_manifest = read(source/'manifest.json')
    manifest = _manifest(raw_manifest, expected_sha256)
    verify_source(manifest['source'], expected_loader_sha256=expected_loader_sha256, root=root)
    spec = importlib.util.spec_from_file_location('v7_public_export_parent', root/INTEGRATION/'adapter.py')
    parent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parent)
    paths_before, hooks_before = list(sys.path), list(sys.meta_path)
    try:
        ctx = parent_ctx or parent.Context(root)
        cfg = ctx.c.Config(**(dict(config) if isinstance(config, dict) else asdict(config))).checked()
        parent_receipt = parent.validate_bundle(source, expected_sha256=expected_sha256, seed=seed,
                                               config=cfg, excluded=excluded, ctx=ctx)
    finally:
        sys.path[:], sys.meta_path[:] = paths_before, hooks_before
    require(parent_receipt.get('completed') is True and parent_receipt.get('parent_reads_private_test_targets') is True,
            'PARENT_PRIVATE_ADMISSION_REQUIRED')
    raw = {name: read(source/name) for name in PUBLIC_FILES}
    require(all(digest(value) == manifest['sha256'][name] for name, value in raw.items())
            and read(source/'manifest.json') == raw_manifest, 'PUBLIC_EXPORT_SOURCE_CHANGED')
    output.mkdir(parents=True, exist_ok=False)
    for name, value in {**raw, 'manifest.json': raw_manifest}.items():
        with (output/name).open('xb') as stream:
            stream.write(value)
    loaded = load_training_bundle(output, expected_sha256=expected_sha256, seed=seed, config=config,
        excluded=excluded, expected_loader_sha256=expected_loader_sha256, root=root)
    return {**loaded['receipt'], 'parent_validation': parent_receipt, 'parent_reads_private_test_targets': True,
            'export_directory': str(output), 'training_performed': False}
