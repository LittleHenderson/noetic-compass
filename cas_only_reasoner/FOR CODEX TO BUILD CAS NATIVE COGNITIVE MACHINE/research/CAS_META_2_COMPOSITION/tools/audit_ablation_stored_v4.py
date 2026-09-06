"""Stored execution audit for a bound retrospective comparison; no neural work.

Reuses frozen source replay and verdict primitives, not the old v3 campaign's
acceptance gate. This is documentary replay, not independent neural execution.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import traceback

from tools import inspect_ablation_packet_v5 as inspection

ROOT = Path(__file__).resolve().parents[1]
BASE = 'cloud_job/campaign/'
MODES = ('v3', 'viability_v4')
ARMS = inspection.ARMS
FIELDS = ('task_correct', 'procedure_correct', 'binding_correct',
          'dependency_correct', 'actual_output_correct', 'trace_valid')
require = inspection.require
file_hash = inspection.file_hash


def checked_json(path):
    require(Path(path).stat().st_size <= 64 * 1024**2, 'AUDIT_JSON_CEILING')
    file_hash(path)
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'DUPLICATE_JSON_FIELD')
            result[key] = value
        return result
    return json.loads(Path(path).read_bytes(), object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NONFINITE_JSON')))


def check_source(manifest):
    """Check all packaged local bytes before importing the source-replay engine."""
    result = {}
    for name, expected in manifest['files_sha256'].items():
        require(name.startswith('research/') and '..' not in name.split('/'), 'SOURCE_PATH_INVALID')
        path = ROOT.parent / name.removeprefix('research/')
        require(file_hash(path) == expected, 'LOCAL_REPLAY_SOURCE_CHANGED:' + name)
        result[name] = expected
    require(manifest['protected_baseline_files'] == 316, 'PROTECTED_BASELINE_COUNT_CHANGED')
    return result


def load_engine(manifest, helper):
    check_source(manifest)
    path = ROOT / 'tools/audit_stored_packet_v3.py'
    raw = path.read_bytes()
    require(sha256(raw).hexdigest() == manifest['files_sha256'][
        'research/CAS_META_2_COMPOSITION/tools/audit_stored_packet_v3.py'], 'REPLAY_HELPER_CHANGED')
    spec = importlib.util.spec_from_file_location('_retrospective_semantic_primitives', path)
    engine = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(path), 'exec'), engine.__dict__)
    # Explicit primitive wiring. Never call its old Extracted/_configure gate
    # or fabricate a learning_v3 success receipt for a retrospective packet.
    from jsonschema import Draft202012Validator
    from cas_meta2.campaign_v3 import admission_error
    from cas_meta2.curriculum import check_native_topology, graph_signature
    from cas_meta2.stored import verify_stored_composition
    engine.admission_error = admission_error
    engine.check_native_topology = check_native_topology
    engine.graph_signature = graph_signature
    engine.verify_stored_composition = verify_stored_composition
    engine.Draft202012Validator = Draft202012Validator
    engine.safe_name = helper.safe_name
    return engine


class Files:
    """Exactly the inspected extraction, with hashes rechecked on every read."""
    def __init__(self, receipt, index, helper):
        require(receipt.get('status') == 'RETROSPECTIVE_RECEIPT_CHECKS_PASSED'
                and receipt.get('schema') == 'cas-meta2-retrospective-inspection/0.2'
                and receipt.get('issues') == []
                and receipt.get('original_full_index_verified') is True
                and receipt.get('archive_safety_and_all_included_bytes_checked') is True,
                'SUCCESSFUL_RETROSPECTIVE_INSPECTION_REQUIRED')
        extraction = receipt.get('extraction')
        require(type(extraction) is dict and extraction.get('all_member_bytes_verified_after_write') is True,
                'VERIFIED_EXTRACTION_REQUIRED')
        self.root = Path(extraction['path']).absolute()
        require(self.root.is_dir(), 'EXTRACTION_MISSING')
        require(index.get('schema') == 'cas-meta2-full-packet-index/1'
                and index.get('packet_sha256') == receipt['packet_sha256'], 'INDEX_PACKET_MISMATCH')
        rows = index['entries']
        require(type(rows) is list and 0 < len(rows) <= 65536, 'INVENTORY_COUNT_INVALID')
        self.inventory, aliases = {}, set()
        self.helper = helper
        for row in rows:
            require(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'}, 'INVENTORY_ROW_INVALID')
            name = helper.safe_name(row['path'])
            require(name not in self.inventory and name.casefold() not in aliases
                    and type(row['bytes']) is int and row['bytes'] >= 0
                    and type(row['sha256']) is str and re.fullmatch('[a-f0-9]{64}', row['sha256']),
                    'INVENTORY_ROW_INVALID')
            self.inventory[name] = row
            aliases.add(name.casefold())
        require(len(rows) == receipt['member_files'] == extraction['files_verified']
                and sum(row['bytes'] for row in rows) <= 2 * 1024**3, 'INVENTORY_COVERAGE_INVALID')
        self.verify_all()

    def path(self, name):
        require(self.helper.safe_name(name) in self.inventory, 'UNINDEXED_MEMBER:' + name)
        path = self.root.joinpath(*name.split('/'))
        require(path.resolve().is_relative_to(self.root.resolve()), 'MEMBER_ESCAPE')
        file_hash(path)  # Also rejects links in any ancestor.
        return path

    def raw(self, name):
        row = self.inventory[name]
        require(row['bytes'] <= 64 * 1024**2, 'MEMBER_JSON_SIZE_CEILING')
        raw = self.path(name).read_bytes()
        require(len(raw) == row['bytes'] and sha256(raw).hexdigest() == row['sha256'], 'MEMBER_CHANGED')
        return raw

    def json(self, name):
        return self.helper.json_bytes(self.raw(name))

    def same_hash(self, name, expected):
        require(self.inventory[name]['sha256'] == expected, 'MEMBER_SEAL_MISMATCH')

    def verify_all(self):
        actual = set()
        for directory, directories, files in os.walk(self.root, followlinks=False):
            for name in directories:
                path = Path(directory) / name
                require(not path.is_symlink() and not getattr(path, 'is_junction', lambda: False)(),
                        'EXTRACTION_LINK_REFUSED')
            for name in files:
                path = Path(directory) / name
                relative = path.relative_to(self.root).as_posix()
                require(relative in self.inventory, 'UNINDEXED_EXTRACTED_FILE')
                row = self.inventory[relative]
                require(path.stat().st_size == row['bytes'] and file_hash(path) == row['sha256'],
                        'EXTRACTED_FILE_CHANGED')
                actual.add(relative)
        require(actual == set(self.inventory), 'EXTRACTED_INVENTORY_CHANGED')


def audit_mode(packet, engine, mode, tasks):
    require(mode in MODES and len(tasks) == 72, 'MODE_OR_TASK_COUNT_INVALID')
    base = BASE + 'prediction/' + mode + '/'
    seal = packet.json(base + 'predictions_seal.json')
    packet.same_hash(base + 'predictions.jsonl', seal['sha256'])
    predictions = [packet.helper.json_bytes(raw) for raw in packet.raw(base + 'predictions.jsonl').splitlines()]
    publics = packet.json(BASE + 'dataset/test_public.json')
    require(len(predictions) == len(publics) == 72, 'SEALED_MAPPING_COUNT_INVALID')
    cases = []
    for index, (task, public, predicted) in enumerate(zip(tasks, publics, predictions, strict=True)):
        require(task['public'] == public and predicted['case_index'] == index
                and predicted['public_sha256'] == engine.digest(public)
                and set(predicted['actions']) == set(ARMS), 'SEALED_TASK_MAPPING_MISMATCH')
        folder = base + f'evaluation/case_{index:04d}'
        private_result = packet.json(folder + '/reference_result.json')
        reference = engine._native(packet, private_result, folder + '/reference',
                                   public, task['target'], reference=True)
        reference_verdict = engine.reference_verdict(task, reference)
        engine.compare_verdict(packet.json(folder + '/reference_verdict.json'), reference_verdict)
        arms = {}
        for arm in ARMS:
            action = predicted['actions'][arm]
            arm_folder = folder + '/' + arm
            result = packet.json(arm_folder + '/execution_result.json')
            saved = packet.json(arm_folder + '/verification.json')
            case = packet.json(arm_folder + '/case_receipt.json')
            require(case['action'] == action and case['verification'] == saved
                    and case['case_index'] == index and case['arm'] == arm, 'CASE_BINDING_MISMATCH')
            rejected = engine.admission_error(action, public)
            if rejected is not None:
                require(result.get('status') == 'REJECTED' and result.get('action') == action
                        and result.get('failure') == rejected and case.get('model_rejection') is True
                        and result.get('reserved_policy_units') == 0 and result.get('native_runs') == 0,
                        'REJECTION_NOT_REPRODUCED')
                require(not any(name.startswith(arm_folder + '/native/') for name in packet.inventory),
                        'REJECTION_HAS_NATIVE_WRITES')
                derived = {**{field: False for field in FIELDS}, 'native_runs': 0, 'reserved_policy_units': 0}
            else:
                require(case.get('model_rejection') is False
                        and result['runtime_identity'] == private_result['runtime_identity'],
                        'CANDIDATE_REFERENCE_IDENTITY_MISMATCH')
                actual = engine._native(packet, result, arm_folder + '/native', public, action)
                derived = engine.candidate_verdict(task, action, actual, reference)
            engine.compare_verdict(saved, derived)
            arms[arm] = {**derived, 'model_rejection': rejected is not None}
        cases.append({'case_index': index, 'reference': reference_verdict, 'arms': arms})
    metrics = recount(cases, packet.json(base + 'evaluation_results.json')['results'])
    groups = packet.json(base + 'evaluation_groups.json')
    names = ('same_depth', 'wording_shift', 'deeper_calls')
    positions = {name: [i for i, task in enumerate(tasks)
                       if task['provenance']['evaluation_group'] == name] for name in names}
    require(all(len(rows) == 24 for rows in positions.values())
            and groups['schema'] == 'cas-meta2-group-results/3'
            and groups['group_case_indices'] == positions and set(groups['groups']) == set(names),
            'GROUP_MAPPING_MISMATCH')
    group_metrics = {name: recount([cases[i] for i in indices], groups['groups'][name])
                     for name, indices in positions.items()}
    native = packet.json(base + 'native_receipt.json')
    require(native['cases'] == 72 and native['arm_verdicts'] == 360
            and native['groups'] == groups['groups'], 'NATIVE_SUMMARY_MISMATCH')
    return {'references_checked': 72, 'arm_choices_checked': 360,
            'cases': cases, 'metrics': metrics, 'groups': group_metrics}


def recount(cases, saved):
    require(type(cases) is list and len(cases) > 0, 'NONEMPTY_CASES_REQUIRED')
    require(set(saved) == set(ARMS), 'AGGREGATE_ARM_SET_CHANGED')
    result = {}
    for arm in ARMS:
        rows = [case['arms'][arm] for case in cases]
        counts = {field: sum(row[field] for row in rows)
                  for field in (*FIELDS, 'native_runs', 'reserved_policy_units', 'model_rejection')}
        target = saved[arm]
        for field in (*FIELDS, 'native_runs', 'reserved_policy_units'):
            require(type(target[field]) is int and target[field] == counts[field], 'AGGREGATE_MISMATCH:' + field)
        require(type(target['total']) is int and target['total'] == len(rows)
                and target['model_rejections'] == counts['model_rejection']
                and target['native_executed'] == len(rows) - counts['model_rejection']
                and target['task_accuracy'] == counts['task_correct'] / len(rows)
                and target['all_cases_in_denominator'] is True
                and target['repair_required_total'] == 0 and target['repair_success'] is None,
                'AGGREGATE_DENOMINATOR_OR_CLAIM_MISMATCH')
        result[arm] = {'total': len(rows), **counts}
    return result


def audit(path, *, inspection_sha256, source_archive, source_sha256, source_sha, job, packet_sha256, output):
    require(type(source_sha) is str and re.fullmatch('[a-f0-9]{40}', source_sha), 'EXACT_SOURCE_SHA_REQUIRED')
    require(type(job) is str and re.fullmatch('cas-meta2-[0-9]{14}-[a-f0-9]{8}', job), 'EXACT_JOB_REQUIRED')
    require(all(type(value) is str and re.fullmatch('[a-f0-9]{64}', value)
                for value in (inspection_sha256, source_sha256, packet_sha256)), 'EXTERNAL_HASHES_REQUIRED')
    require(not any(name.split('.')[0] in inspection.FORBIDDEN for name in sys.modules),
            'NEURAL_OR_PROVIDER_PRELOADED')
    require(file_hash(path) == inspection_sha256, 'EXTERNAL_INSPECTION_HASH_MISMATCH')
    guard = inspection.NoNeuralOrProvider()
    sys.meta_path.insert(0, guard)
    try:
        helper, manifest, _, _ = inspection.load_helpers(source_archive, source_sha, source_sha256)
        output = helper._new_output(output)
        receipt = checked_json(path)
        require(receipt['source_sha'] == source_sha and receipt['job'] == job
                and receipt['packet_sha256'] == packet_sha256
                and receipt['source_archive_sha256'] == source_sha256
                and receipt['source_manifest'] == manifest, 'EXTERNAL_AUDIT_IDENTITY_MISMATCH')
        index_path = Path(path).with_name('full_member_index.json')
        require(file_hash(index_path) == receipt['full_member_index_sha256'], 'INSPECTION_INDEX_CHANGED')
        packet = Files(receipt, checked_json(index_path), helper)
        require(not output.is_relative_to(packet.root.resolve()) and not packet.root.resolve().is_relative_to(output),
                'AUDIT_OUTPUT_EVIDENCE_OVERLAP')
        engine = load_engine(manifest, helper)
        code_before = {str(item): file_hash(item) for item in (Path(__file__), Path(inspection.__file__))}
        record = {'schema': 'cas-meta2-retrospective-stored-audit/0.1', 'completed': False,
            'job': job, 'source_sha': source_sha, 'packet_sha256': packet_sha256,
            'inspection_receipt_sha256': inspection_sha256, 'source_archive_sha256': source_sha256,
            'neural_execution_performed': False, 'checkpoint_loading_performed': False,
            'fresh_held_out_claim_permitted': False, 'learning_accepted': False,
            'modes': {}, 'errors': [], 'stage': 'published_schema',
            'boundary': 'Frozen stored source replay, not independent neural re-execution, restart proof or learning acceptance.'}
        try:
            validator, schema = engine.protected_schema()
            record['published_schema'] = schema
            record['stage'] = 'stored_trace_schemas'
            record['traces'] = engine.validate_all_traces(packet, validator)
            tasks = packet.json(BASE + 'dataset/test_private.json')
            for mode in MODES:
                record['stage'] = 'stored_outcomes_' + mode
                record['modes'][mode] = audit_mode(packet, engine, mode, tasks)
            record['stage'] = 'final_immutability'
            packet.verify_all()
            require(file_hash(path) == inspection_sha256
                    and file_hash(index_path) == receipt['full_member_index_sha256']
                    and file_hash(source_archive) == source_sha256, 'AUDIT_INPUT_CHANGED')
            check_source(manifest)
            require(all(file_hash(name) == digest for name, digest in code_before.items()), 'AUDITOR_CHANGED')
            record['completed'] = True
        except Exception as error:
            record['errors'].append({'stage': record['stage'], 'type': type(error).__name__,
                'reason': str(error), 'traceback': traceback.format_exc(limit=20)})
        record.update(status='STORED_COMPARISON_AUDIT_PASSED' if record['completed'] else 'STORED_COMPARISON_AUDIT_REJECTED',
                      utc=datetime.now(timezone.utc).isoformat(), audit_code_sha256=code_before)
        output.mkdir(parents=True, exist_ok=False)
        (output / 'stored_audit_receipt.json').write_text(json.dumps(record, sort_keys=True, indent=2) + '\n', encoding='utf-8')
        return record
    finally:
        sys.meta_path.remove(guard)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('inspection', 'inspection-sha256', 'source-archive', 'source-sha256',
                 'source-sha', 'job', 'packet-sha256', 'output'):
        parser.add_argument('--' + name, required=True)
    args = vars(parser.parse_args())
    path = args.pop('inspection')
    result = audit(path, **args)
    print(json.dumps({key: result[key] for key in ('status', 'completed', 'errors')}))
    raise SystemExit(0 if result['completed'] else 2)
