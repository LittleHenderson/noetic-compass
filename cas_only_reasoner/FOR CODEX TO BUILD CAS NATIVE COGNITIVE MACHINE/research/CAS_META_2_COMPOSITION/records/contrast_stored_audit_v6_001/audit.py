"""Bound offline stored-trace audit for contrast v6; no neural execution."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import traceback
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = 'cloud_job/campaign/'
NATIVE = BASE+'native/'
ARMS = ('cas_untrained', 'cas_trained', 'generic_untrained', 'generic_trained', 'rule')
FIELDS = ('task_correct', 'procedure_correct', 'binding_correct', 'dependency_correct',
          'actual_output_correct', 'trace_valid')
FORBIDDEN = {'torch', 'casformer', 'cas_cjt', 'tensorflow', 'jax', 'cupy', 'boto3', 'botocore'}


def require(value, reason):
    if not value:
        raise ValueError(reason)


class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        require(fullname.split('.')[0] not in FORBIDDEN, 'NEURAL_OR_PROVIDER_IMPORT_REFUSED')


def regular(path):
    path = Path(path).absolute()
    require(path.is_file() and not any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)()
            for p in (path, *path.parents)), 'NONREGULAR_OR_LINKED_INPUT')
    return path


def file_hash(path):
    result = sha256()
    with regular(path).open('rb') as stream:
        for raw in iter(lambda: stream.read(1024**2), b''):
            result.update(raw)
    return result.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')


def decode(raw):
    require(len(raw) <= 64*1024**2, 'JSON_SIZE_CEILING')
    def pairs(rows):
        result = {}
        for key, value in rows:
            require(key not in result, 'DUPLICATE_JSON_FIELD')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))
    canonical(value)
    return value


def read(path):
    require(regular(path).stat().st_size <= 64*1024**2, 'JSON_SIZE_CEILING')
    return decode(Path(path).read_bytes())


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_source(manifest):
    require(manifest.get('protected_baseline_files') == 316, 'PROTECTED_BASELINE_COUNT_CHANGED')
    for name, expected in manifest['files_sha256'].items():
        require(name.startswith('research/') and '..' not in name.split('/')
                and '\\' not in name and ':' not in name, 'SOURCE_PATH_INVALID')
        path = ROOT.parent.parent/name
        require(file_hash(path) == expected, 'LOCAL_REPLAY_SOURCE_CHANGED:'+name)


def load_bound_source(source_archive, source_hash, source_sha):
    """Check loader/helper bytes against the Git commit BEFORE helper execution."""
    require(file_hash(source_archive) == source_hash, 'SOURCE_ARCHIVE_HASH_MISMATCH')
    repo = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], cwd=ROOT, text=True).strip())
    require(subprocess.check_output(['git', 'rev-parse', source_sha+'^{commit}'], cwd=repo,
                                   text=True).strip() == source_sha, 'EXACT_SOURCE_COMMIT_REQUIRED')
    for relative in ('aws/launch_contrast_v6.py', 'aws/budget.py',
                     'tools/experiment_profiles_contrast_v6.py',
                     'tools/build_launch_bundle_contrast_v6.py', 'aws/launch_plan.json', 'requirements-gpu.txt'):
        path = ROOT/relative
        raw = subprocess.check_output(['git', 'cat-file', 'blob', source_sha+':'+path.relative_to(repo).as_posix()], cwd=repo)
        require(file_hash(path) == sha256(raw).hexdigest(), 'PREIMPORT_SOURCE_MISMATCH:'+relative)
    launcher = load('_contrast_audit_launcher', ROOT/'aws/launch_contrast_v6.py')
    manifest = launcher.validate_archive(source_archive, source_hash, source_sha, read(launcher.PLAN_FILE))
    launcher.verify_launcher_identity(manifest)
    check_source(manifest)
    return manifest, load('_contrast_audit_archive', ROOT/'tools/inspect_cloud_packet.py')


def load_engine(manifest, helper):
    check_source(manifest)
    engine = load('_contrast_stored_semantic_primitives', ROOT/'tools/audit_stored_packet_v3.py')
    # Only frozen pure primitives: never the old v3 acceptance gate or Extracted.
    from jsonschema import Draft202012Validator
    from cas_meta2.campaign_v3 import admission_error
    from cas_meta2.curriculum import check_native_topology, graph_signature, parse_problem
    from cas_meta2.stored import verify_stored_composition
    engine.Draft202012Validator = Draft202012Validator
    engine.admission_error, engine.check_native_topology = admission_error, check_native_topology
    engine.graph_signature, engine.verify_stored_composition = graph_signature, verify_stored_composition
    engine.parse_problem = parse_problem
    engine.safe_name = helper.safe_name
    return engine


def archive_inventory(path, helper, *, job, source_sha, source_hash, experiment):
    require(regular(path).stat().st_size <= 1024**3, 'PACKET_COMPRESSED_SIZE_CEILING')
    with zipfile.ZipFile(path) as archive:
        infos, expanded = helper._safe_infos(archive)
        rows = []
        for name, info in sorted(infos.items()):
            if info.is_dir():
                continue
            state, size = sha256(), 0
            with archive.open(info) as stream:
                for raw in iter(lambda: stream.read(1024**2), b''):
                    size += len(raw)
                    require(size <= info.file_size, 'ARCHIVE_MEMBER_SIZE_EXCEEDED')
                    state.update(raw)
            require(size == info.file_size, 'ARCHIVE_MEMBER_SIZE_MISMATCH')
            rows.append({'path': name, 'bytes': size, 'sha256': state.hexdigest()})
        packet = helper.Packet(archive, infos, rows)
        collection, full_index = helper._collection(packet, job, source_sha, source_hash)
        require(full_index and collection['returncode'] == 0 and collection['partial_evidence'] is False
                and collection.get('experiment') == experiment, 'COMPLETE_BOUND_COLLECTION_REQUIRED')
    return rows, expanded


class Files:
    """Read exactly an externally bound ZIP inventory; never silently re-extract."""
    def __init__(self, root, inventory, helper):
        self.root, self.helper = Path(root).absolute(), helper
        require(self.root.is_dir() and not any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)()
            for p in (self.root, *self.root.parents)), 'EXTRACTION_LINK_OR_MISSING')
        require(type(inventory) is list and 0 < len(inventory) <= 65536, 'INVENTORY_COUNT_INVALID')
        self.inventory, aliases = {}, set()
        for row in inventory:
            require(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'}, 'INVENTORY_ROW_INVALID')
            name = helper.safe_name(row['path'])
            require(name not in self.inventory and name.casefold() not in aliases
                    and type(row['bytes']) is int and row['bytes'] >= 0
                    and type(row['sha256']) is str and re.fullmatch('[a-f0-9]{64}', row['sha256']),
                    'INVENTORY_ROW_INVALID')
            self.inventory[name] = dict(row)
            aliases.add(name.casefold())
        require(sum(r['bytes'] for r in inventory) <= 2*1024**3, 'INVENTORY_SIZE_CEILING')
        self.verify_all()

    def path(self, name):
        require(self.helper.safe_name(name) in self.inventory, 'UNINDEXED_MEMBER:'+name)
        path = regular(self.root.joinpath(*name.split('/')))
        require(path.resolve().is_relative_to(self.root.resolve()), 'MEMBER_ESCAPE')
        row = self.inventory[name]
        require(path.stat().st_size == row['bytes'] and file_hash(path) == row['sha256'], 'MEMBER_CHANGED:'+name)
        return path

    def raw(self, name):
        require(self.inventory[name]['bytes'] <= 64*1024**2, 'MEMBER_JSON_SIZE_CEILING')
        raw = self.path(name).read_bytes()
        require(len(raw) == self.inventory[name]['bytes'] and sha256(raw).hexdigest() == self.inventory[name]['sha256'],
                'MEMBER_CHANGED:'+name)
        return raw

    def json(self, name):
        return decode(self.raw(name))

    def same_hash(self, name, expected):
        require(name in self.inventory and self.inventory[name]['sha256'] == expected, 'MEMBER_SEAL_MISMATCH:'+name)

    def verify_all(self):
        actual = set()
        for directory, directories, files in os.walk(self.root, followlinks=False):
            for name in directories:
                path = Path(directory)/name
                require(not path.is_symlink() and not getattr(path, 'is_junction', lambda: False)(), 'EXTRACTION_LINK_REFUSED')
            for name in files:
                relative = (Path(directory)/name).relative_to(self.root).as_posix()
                self.path(relative)
                actual.add(relative)
        require(actual == set(self.inventory), 'EXTRACTED_INVENTORY_CHANGED')


def recount(cases, saved):
    require(type(cases) is list and cases and set(saved) == set(ARMS), 'AGGREGATE_COVERAGE_INVALID')
    result = {}
    for arm in ARMS:
        rows = [case['arms'][arm] for case in cases]
        counts = {field: sum(row[field] for row in rows)
                  for field in (*FIELDS, 'native_runs', 'reserved_policy_units', 'model_rejection')}
        target = saved[arm]
        for field in (*FIELDS, 'native_runs', 'reserved_policy_units'):
            require(type(target[field]) is int and target[field] == counts[field], 'AGGREGATE_MISMATCH:'+field)
        for field, expected in (('total', len(rows)), ('model_rejections', counts['model_rejection']),
                                ('native_executed', len(rows)-counts['model_rejection']), ('repair_required_total', 0)):
            require(type(target[field]) is int and target[field] == expected, 'AGGREGATE_MISMATCH:'+field)
        require(type(target['task_accuracy']) in (float, int) and target['task_accuracy'] == counts['task_correct']/len(rows)
                and target['all_cases_in_denominator'] is True and target['repair_success'] is None,
                'AGGREGATE_DENOMINATOR_OR_CLAIM_MISMATCH')
        result[arm] = {'total': len(rows), **counts}
    return result


def group_positions(tasks):
    require(len(tasks) == 72, 'TASK_COUNT_INVALID')
    groups = {name: [] for name in ('depth_3', 'depth_4', 'same_depth', 'wording_shift', 'deeper_calls')}
    for index, task in enumerate(tasks):
        depth, side = task['provenance']['depth'], task['contrast_side']
        require(type(depth) is int and depth in (3, 4) and side in ('same_depth', 'wording_shift', 'deeper_calls')
                and task['provenance']['evaluation_group'] == 'test'
                and depth == (4 if side == 'deeper_calls' else 3), 'V6_GROUP_MAPPING_INVALID')
        groups['depth_'+str(depth)].append(index)
        groups[side].append(index)
    require({name: len(rows) for name, rows in groups.items()} ==
            {'depth_3': 48, 'depth_4': 24, 'same_depth': 24, 'wording_shift': 24, 'deeper_calls': 24}, 'GROUP_COUNTS_CHANGED')
    return groups


def validate_exports(packet, validator):
    """Check every native trace export, including diagnostic GPU-test outputs."""
    counts = {}
    for name in sorted(packet.inventory):
        if not name.endswith('/native_traces.json'):
            continue
        values = packet.json(name)
        require(type(values) is list, 'TRACE_EXPORT_LIST_REQUIRED')
        database = name.removesuffix('native_traces.json')+'native.db'
        require(database in packet.inventory, 'TRACE_EXPORT_DATABASE_MISSING')
        connection = sqlite3.connect(packet.path(database).as_uri()+'?mode=ro&immutable=1', uri=True)
        try:
            stored = [decode(raw.encode('utf-8')) for (raw,) in
                      connection.execute('SELECT payload_json FROM trace_events ORDER BY sequence')]
        finally:
            connection.close()
        require(values == stored, 'TRACE_EXPORT_DATABASE_MISMATCH')
        for value in values:
            require(value.get('schema_version') == 'cas.neural-cjt.tick-trace/0.2'
                    and value.get('contract_type') == 'TICK_TRACE', 'PUBLISHED_TRACE_TYPE_REQUIRED')
            validator.validate(value)
        counts[name] = len(values)
    require(counts, 'NO_NATIVE_TRACE_EXPORTS')
    return {'exports': len(counts), 'stored_traces': sum(counts.values()), 'per_export': counts}


def audit_outcomes(packet, engine):
    manifest = packet.json(BASE+'dataset/manifest.json')
    for name in ('test_public.json', 'test_private.json'):
        packet.same_hash(BASE+'dataset/'+name, manifest['sha256'][name])
    tasks, publics = packet.json(BASE+'dataset/test_private.json'), packet.json(BASE+'dataset/test_public.json')
    require(len(tasks) == len(publics) == 72, 'HELD_OUT_CASE_COUNT_INVALID')
    seal = packet.json(NATIVE+'predictions_seal.json')
    require(seal.get('schema') == 'cas-meta2-contrast-evaluation-seal/6' and seal.get('arms') == list(ARMS)
            and type(seal.get('test_examples')) is int and seal['test_examples'] == 72
            and type(seal.get('prediction_count')) is int and seal['prediction_count'] == 360,
            'V6_NATIVE_SEAL_REQUIRED')
    packet.same_hash(NATIVE+'predictions.jsonl', seal['sha256'])
    packet.same_hash(BASE+'training/neural_predictions.jsonl', seal['neural_predictions_sha256'])
    packet.same_hash(BASE+'dataset/manifest.json', seal['manifest_sha256'])
    neural = [decode(raw) for raw in packet.raw(BASE+'training/neural_predictions.jsonl').splitlines()]
    predictions = [decode(raw) for raw in packet.raw(NATIVE+'predictions.jsonl').splitlines()]
    results = packet.json(NATIVE+'evaluation_results.json')
    require(len(predictions) == len(neural) == len(results['cases']) == 72, 'SEALED_MAPPING_COUNT_INVALID')
    cases = []
    for index, (task, public, predicted, neural_row) in enumerate(zip(tasks, publics, predictions, neural, strict=True)):
        require(task['public'] == public and type(predicted['case_index']) is int and predicted['case_index'] == index
                and predicted['public_sha256'] == engine.digest(public) and set(predicted['actions']) == set(ARMS)
                and set(neural_row['actions']) == set(ARMS)-{'rule'}
                and {k: v for k, v in predicted.items() if k != 'actions'} == {k: v for k, v in neural_row.items() if k != 'actions'}
                and all(predicted['actions'][arm] == neural_row['actions'][arm] for arm in ARMS if arm != 'rule'),
                'SEALED_TASK_MAPPING_MISMATCH')
        require(predicted['actions']['rule'] == engine.parse_problem(public), 'RULE_PUBLIC_INPUT_MISMATCH')
        folder = NATIVE+f'evaluation/case_{index:04d}'
        whole = packet.json(folder+'/case_receipt.json')
        require(whole == results['cases'][index] and whole['case_index'] == index and whole['task_id'] == task['task_id']
                and set(whole['arms']) == set(ARMS), 'CASE_SUMMARY_COPY_MISMATCH')
        private_result = packet.json(folder+'/reference_result.json')
        reference = engine._native(packet, private_result, folder+'/reference', public, task['target'], reference=True)
        reference_verdict = engine.reference_verdict(task, reference)
        saved_ref = packet.json(folder+'/reference_verdict.json')
        require(whole['reference_verification'] == saved_ref, 'REFERENCE_VERDICT_COPY_MISMATCH')
        engine.compare_verdict(saved_ref, reference_verdict)
        arms = {}
        for arm in ARMS:
            action = predicted['actions'][arm]
            arm_folder = folder+'/'+arm
            result, saved = packet.json(arm_folder+'/execution_result.json'), packet.json(arm_folder+'/verification.json')
            case = packet.json(arm_folder+'/case_receipt.json')
            require(case == whole['arms'][arm] and case['action'] == action and case['verification'] == saved
                    and case['case_index'] == index and case['arm'] == arm
                    and case['execution_status'] == result['status'] and case['failure'] == result.get('failure'), 'CASE_BINDING_MISMATCH')
            rejected = engine.admission_error(action, public)
            if rejected is not None:
                require(result.get('status') == 'REJECTED' and result.get('action') == action and result.get('failure') == rejected
                        and case.get('model_rejection') is True and type(result.get('reserved_policy_units')) is int
                        and result['reserved_policy_units'] == 0 and type(result.get('native_runs')) is int and result['native_runs'] == 0,
                        'REJECTION_NOT_REPRODUCED')
                require(not any(name.startswith(arm_folder+'/native/') for name in packet.inventory), 'REJECTION_HAS_NATIVE_WRITES')
                derived = {**{field: False for field in FIELDS}, 'native_runs': 0, 'reserved_policy_units': 0}
            else:
                require(case.get('model_rejection') is False and result['runtime_identity'] == private_result['runtime_identity'],
                        'CANDIDATE_REFERENCE_IDENTITY_MISMATCH')
                actual = engine._native(packet, result, arm_folder+'/native', public, action)
                derived = engine.candidate_verdict(task, action, actual, reference)
            engine.compare_verdict(saved, derived)
            arms[arm] = {**derived, 'model_rejection': rejected is not None}
        cases.append({'case_index': index, 'task_id': task['task_id'], 'reference': reference_verdict, 'arms': arms})
    metrics = recount(cases, results['results'])
    positions = group_positions(tasks)
    require(set(results['groups']) == set(positions), 'GROUP_SET_CHANGED')
    groups = {name: recount([cases[i] for i in indices], results['groups'][name]) for name, indices in positions.items()}
    native = packet.json(NATIVE+'native_receipt.json')
    require(native.get('schema') == 'cas-meta2-contrast-native-evaluation/6' and native.get('completed') is True
            and native['cases'] == native['reference_cases'] == 72 and native['arm_verdicts'] == 360
            and native['learning_accepted'] is False and native['seal'] == seal
            and native['results'] == results['results'] and native['groups'] == results['groups'], 'NATIVE_SUMMARY_MISMATCH')
    return {'references_checked': 72, 'arm_choices_checked': 360, 'cases': cases,
            'metrics': metrics, 'group_case_indices': positions, 'groups': groups}


def audit(review, *, review_sha256, source_archive, source_sha256, source_sha,
          packet, packet_sha256, job, extracted, output):
    require(type(source_sha) is str and re.fullmatch('[a-f0-9]{40}', source_sha), 'EXACT_SOURCE_SHA_REQUIRED')
    require(type(job) is str and re.fullmatch('cas-meta2-[0-9]{14}-[a-f0-9]{8}', job), 'EXACT_JOB_REQUIRED')
    require(all(type(value) is str and re.fullmatch('[a-f0-9]{64}', value)
                for value in (review_sha256, source_sha256, packet_sha256)), 'EXTERNAL_HASHES_REQUIRED')
    require(not any(name.split('.')[0] in FORBIDDEN for name in sys.modules), 'NEURAL_OR_PROVIDER_PRELOADED')
    guard = Guard()
    sys.meta_path.insert(0, guard)
    try:
        require(file_hash(review) == review_sha256 and file_hash(packet) == packet_sha256, 'EXTERNAL_INPUT_HASH_MISMATCH')
        manifest, helper = load_bound_source(source_archive, source_sha256, source_sha)
        receipt = read(review)
        require(receipt.get('schema') == 'cas-meta2-offline-contrast-review/6'
                and receipt.get('status') == 'RECORDED_CONTRAST_RECOUNT_PASSED'
                and receipt.get('source_sha') == source_sha and receipt.get('job') == job
                and receipt.get('packet_sha256') == packet_sha256 and receipt.get('source_archive_sha256') == source_sha256
                and receipt.get('source_manifest') == manifest and receipt.get('neural_execution') is False
                and receipt.get('learning_accepted') is False, 'BOUND_SUCCESSFUL_REVIEW_REQUIRED')
        inventory, expanded = archive_inventory(packet, helper, job=job, source_sha=source_sha,
                                                source_hash=source_sha256, experiment=manifest['experiment'])
        require(inventory == receipt['inventory'] and receipt['member_files'] == len(inventory), 'REVIEW_INVENTORY_MISMATCH')
        extraction = receipt['extraction']
        require(Path(extraction['path']).resolve() == Path(extracted).resolve()
                and extraction['all_member_bytes_verified_after_write'] is True
                and extraction['files_verified'] == len(inventory), 'REVIEW_EXTRACTION_MISMATCH')
        files = Files(extracted, inventory, helper)
        destination = helper._new_output(output)
        require(destination.is_relative_to(HERE.resolve()) and not destination.is_relative_to(files.root.resolve())
                and not files.root.resolve().is_relative_to(destination), 'OUTPUT_SCOPE_OR_OVERLAP_INVALID')
        engine = load_engine(manifest, helper)
        code_hash = file_hash(__file__)
        record = {'schema': 'cas-meta2-contrast-stored-audit/6', 'completed': False, 'stage': 'published_schema',
            'source_sha': source_sha, 'source_archive_sha256': source_sha256, 'packet_sha256': packet_sha256,
            'review_receipt_sha256': review_sha256, 'audit_code_sha256': code_hash, 'job': job,
            'member_files': len(inventory), 'expanded_bytes': expanded, 'errors': [],
            'neural_execution_performed': False, 'checkpoint_loading_performed': False,
            'provider_calls': False, 'learning_accepted': False, 'automatic_promotion': False,
            'boundary': 'Offline stored source and SQLite replay. No neural rerun, fresh task generation, restart proof, or automatic learning acceptance.'}
        try:
            validator, schema = engine.protected_schema()
            record['published_schema'] = schema
            record['stage'] = 'all_stored_trace_schemas'
            record['traces'] = engine.validate_all_traces(files, validator)
            record['trace_exports'] = validate_exports(files, validator)
            record['stage'] = 'stored_semantic_verdicts'
            record['outcomes'] = audit_outcomes(files, engine)
            record['stage'] = 'final_immutability'
            files.verify_all()
            require(file_hash(review) == review_sha256 and file_hash(packet) == packet_sha256
                    and file_hash(source_archive) == source_sha256 and file_hash(__file__) == code_hash, 'AUDIT_INPUT_CHANGED')
            check_source(manifest)
            record['completed'] = True
        except Exception as error:
            record['errors'].append({'stage': record['stage'], 'type': type(error).__name__,
                'reason': str(error), 'traceback': traceback.format_exc(limit=20)})
        record.update(status='STORED_CONTRAST_AUDIT_PASSED' if record['completed'] else 'STORED_CONTRAST_AUDIT_REJECTED',
                      utc=datetime.now(timezone.utc).isoformat())
        destination.mkdir(parents=True, exist_ok=False)
        with (destination/'stored_audit_receipt.json').open('x', encoding='utf-8') as stream:
            json.dump(record, stream, sort_keys=True, indent=2, allow_nan=False)
            stream.write('\n')
        return record
    finally:
        sys.meta_path.remove(guard)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('review', 'review-sha256', 'source-archive', 'source-sha256', 'source-sha',
                 'packet', 'packet-sha256', 'job', 'extracted', 'output'):
        parser.add_argument('--'+name, required=True)
    sys.path.insert(0, str(ROOT))
    result = audit(**vars(parser.parse_args()))
    print(json.dumps({key: result[key] for key in ('status', 'completed', 'errors')}))
    raise SystemExit(0 if result['completed'] else 2)
