"""Recheck saved recovery evidence with JSON, hashes, SQLite and struct only.

This is a byte/semantic evidence audit, not neural reproduction. Model
construction, model calls, tensor operations and checkpoint loading are blocked.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.inspect_cloud_packet import ARMS, RECOVERY, inspect_packet, json_bytes


class AuditInvalid(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise AuditInvalid(reason)


def file_hash(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1024*1024), b''):
            value.update(part)
    return value.hexdigest()


def read(path):
    return json_bytes(Path(path).read_bytes())


def owned_records(path):
    resolved = Path(path).resolve()
    records = (ROOT/'records').resolve()
    require(resolved.is_relative_to(records) and resolved != records, 'OWNED_RECORDS_SUBDIRECTORY_REQUIRED')
    return resolved


def verify_extraction(archive_path, extracted):
    """Bind every extracted byte to the already inspected packet; no new files."""
    extracted = owned_records(extracted)
    actual = {}
    for path in extracted.rglob('*'):
        require(not path.is_symlink(), 'EXTRACTION_SYMLINK_REFUSED')
        if path.is_file():
            require(path.resolve().is_relative_to(extracted), 'EXTRACTION_PATH_ESCAPE')
            actual[path.relative_to(extracted).as_posix()] = file_hash(path)
    with zipfile.ZipFile(archive_path) as archive:
        expected = {}
        for info in archive.infolist():
            if info.is_dir():
                continue
            with archive.open(info) as stream:
                value = hashlib.sha256()
                for part in iter(lambda: stream.read(1024*1024), b''):
                    value.update(part)
            expected[info.filename] = value.hexdigest()
    require(actual == expected, 'EXTRACTION_FILE_SET_OR_BYTES_MISMATCH')
    return actual


@contextmanager
def prohibit_neural_work(torch_module=None, dispatch_type=None):
    # Dependency injection is used only by pure guard tests.
    if torch_module is None:
        import torch as torch_module
    if dispatch_type is None:
        from torch.utils._python_dispatch import TorchDispatchMode as dispatch_type
    state = {'torch_version': str(torch_module.__version__), 'blocked_attempts': []}
    def forbidden(name):
        def fail(*args, **kwargs):
            state['blocked_attempts'].append(name)
            raise AuditInvalid('NEURAL_OR_TENSOR_WORK_FORBIDDEN:'+name)
        return fail
    module = torch_module.nn.Module
    originals = (module.__init__, module.__call__, torch_module.load)
    class NoTensorOperations(dispatch_type):
        def __torch_dispatch__(self, func, types, args=(), kwargs=None):
            return forbidden('tensor_operation')()
    module.__init__, module.__call__, torch_module.load = (
        forbidden('Module.__init__'), forbidden('Module.__call__'), forbidden('torch.load'))
    try:
        with NoTensorOperations():
            yield state
    finally:
        module.__init__, module.__call__, torch_module.load = originals


def rebound(result, directory):
    directory = owned_records(directory)
    return {**result, 'output_dir': str(directory), 'native_database': str(directory/'native.db'),
            'semantic_projection_path': str(directory/'semantic_projection.json')}


def verify_cases(recovery, tasks, verifier):
    require(type(tasks) is list and len(tasks) == 72, 'EXACTLY_72_IMMUTABLE_TASKS_REQUIRED')
    rows = {arm: read(recovery/(arm+'_case_results.json')) for arm in ARMS}
    for arm in ARMS:
        require(len(rows[arm]) == 72 and all(type(row.get('case_index')) is int and row['case_index'] == index
                    for index, row in enumerate(rows[arm])), 'MISSING_DUPLICATE_OR_REORDERED_CASES')
    checked, successes = 0, {arm: 0 for arm in ARMS}
    for index, task in enumerate(tasks):
        case = recovery/'cases'/f'case_{index:04d}'
        reference = rebound(read(case/'reference'/'result.json'), case/'reference')
        require(verifier(task, reference, reference).get('success') is True, 'SAVED_REFERENCE_SEMANTICS_INVALID:'+str(index))
        for arm in ARMS:
            result = rebound(read(case/arm/'result.json'), case/arm)
            verdict = verifier(task, result, reference)
            require(verdict == rows[arm][index]['verification'], 'RECORDED_VERDICT_MISMATCH:'+arm+':'+str(index))
            require(not any(reason.startswith(('INVALID_DURABLE_EVIDENCE', 'PRIVATE_REFERENCE_UNAVAILABLE'))
                            for reason in verdict.get('reasons', [])), 'DURABLE_EVIDENCE_UNAVAILABLE')
            checked += 1
            successes[arm] += verdict['success'] is True
    return {'references_reverified': 72, 'arm_executions_reverified': checked,
            'recorded_verdicts_equal': True, 'success_counts': successes}


def source_snapshot():
    from cas_meta1.baseline import verify_baseline, verify_installed_wheels
    paths = ('cas_meta1/execution.py', 'cas_meta1/baseline.py', 'tools/inspect_cloud_packet.py',
             'tools/audit_recovery_semantics.py', 'data/test_public.json', 'data/test_private.json')
    return {'files_sha256': {name: file_hash(ROOT/name) for name in paths},
            'baseline': verify_baseline(), 'installed_wheels': verify_installed_wheels()}


def audit(run_dir, extracted, predecessor, output):
    run_dir, extracted, predecessor, output = map(owned_records, (run_dir, extracted, predecessor, output))
    require(not output.exists(), 'NEW_AUDIT_OUTPUT_DIRECTORY_REQUIRED')
    require(all(not output.is_relative_to(path) and not path.is_relative_to(output)
                for path in (run_dir, extracted, predecessor)), 'AUDIT_OUTPUT_MUST_NOT_OVERLAP_INPUTS')
    packet = inspect_packet(run_dir/'cloud_artifacts.zip', run_dir/'launch_receipt.json', predecessor_run_dir=predecessor)
    require(packet['status'] == 'VERIFIED_COMPLETED_RECOVERY_PACKET'
            and packet['predecessor_bytes_independently_rechecked'], 'COMPLETE_RECOVERY_AND_PREDECESSOR_REQUIRED')
    extraction_before = verify_extraction(run_dir/'cloud_artifacts.zip', extracted)
    recovery = extracted/RECOVERY
    receipt = read(recovery/'receipt.json')
    require(receipt.get('status') == 'CAS_META_1_EVALUATION_RECOVERY_COMPLETED'
            and set(receipt.get('results', {})) == set(ARMS), 'RECOVERY_COMPLETION_REQUIRED')
    launch = read(run_dir/'launch_receipt.json')
    helper_key = launch['manifest']['pilot_dir']+'/cas_meta1/execution.py'
    require(file_hash(ROOT/'cas_meta1/execution.py') == launch['manifest']['files_sha256'].get(helper_key),
            'VERIFIER_DIFFERS_FROM_CLOUD_EXECUTION_HELPER')
    opening, predictions = read(recovery/'test_gold_opening_receipt.json'), read(recovery/'predictions.json')
    require(file_hash(ROOT/'data/test_private.json') == opening['test_private_sha256']
            and file_hash(ROOT/'data/test_public.json') == predictions['test_public_sha256'], 'IMMUTABLE_DATASET_BYTES_CHANGED')
    tasks, publics = read(ROOT/'data/test_private.json'), read(ROOT/'data/test_public.json')
    require(len(tasks) == len(publics) == 72 and all(task['public'] == public for task, public in zip(tasks, publics)),
            'IMMUTABLE_PUBLIC_PRIVATE_MAPPING_CHANGED')
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    audit_receipt = {'schema': 'cas-meta1-recovery-semantic-audit/1', 'status': 'AUDIT_INCOMPLETE',
        'utc': datetime.now(timezone.utc).isoformat(), 'command_argv': [sys.executable, *sys.argv],
        'runtime': {'python': sys.version, 'executable': sys.executable, 'platform': platform.platform()},
        'run_source_sha': packet['source_sha'], 'packet_sha256': packet['archive_sha256'],
        'predecessor_packet_sha256': read(recovery/'predecessor_inspection.json')['archive_sha256'],
        'paths': {'run_dir': str(run_dir), 'extracted': str(extracted), 'predecessor': str(predecessor), 'output': str(output)},
        'boundary': 'Byte/semantic audit of stored SQLite evidence with the pinned verifier; not neural reproduction. No model construction, calls, tensor operations, or checkpoint loading.'}
    try:
        before = source_snapshot()
        audit_receipt['source_before'] = before
        audit_receipt['audit_git_sha'] = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
            text=True, capture_output=True, check=True, timeout=5).stdout.strip()
        with prohibit_neural_work() as guard:
            audit_receipt['guard'] = guard
            from cas_meta1.execution import verify_task
            audit_receipt['counts'] = verify_cases(recovery, tasks, verify_task)
        after = source_snapshot()
        require(before == after, 'AUDIT_SOURCE_OR_BASELINE_CHANGED')
        require(extraction_before == verify_extraction(run_dir/'cloud_artifacts.zip', extracted), 'EXTRACTION_CHANGED_DURING_AUDIT')
        require(file_hash(run_dir/'cloud_artifacts.zip') == packet['archive_sha256']
                and file_hash(predecessor/'cloud_artifacts.zip') == audit_receipt['predecessor_packet_sha256'],
                'PACKET_BYTES_CHANGED_DURING_AUDIT')
        audit_receipt.update(status='RECOVERY_BYTE_SEMANTIC_AUDIT_PASSED', source_after=after,
                             source_hashes_unchanged=True, extracted_files_unchanged=True,
                             local_neural_execution=False, checkpoint_loading_performed=False,
                             tensor_operations_performed=False)
    except BaseException as exc:
        audit_receipt['failure'] = {'type': type(exc).__name__, 'message': str(exc)}
        raise
    finally:
        audit_receipt['wall_seconds'] = time.monotonic()-started
        (output/'audit_receipt.json').write_text(json.dumps(audit_receipt, indent=2, sort_keys=True, allow_nan=False)+'\n', encoding='utf-8')
    return audit_receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run-dir', 'extracted', 'predecessor', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = audit(args.run_dir, args.extracted, args.predecessor, args.output)
        print(json.dumps({'status': result['status'], 'output': str(args.output), 'counts': result['counts']}))
        return 0
    except Exception as exc:
        print(json.dumps({'status': 'AUDIT_INCOMPLETE', 'type': type(exc).__name__, 'message': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
