"""Capture one externally pinned offline v7 review; never launch a provider."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REVIEW = ROOT / 'records/prototype_v7_stored_review_001'
PACKET = ROOT / 'records/aws_prototype_v7_001/cloud_artifacts.zip'
ARCHIVE = ROOT / 'records/aws_prototype_v7_source_001'
CHECKS = REVIEW / 'checks_004/checks_receipt.json'
JOB = 'cas-meta2-20260906094002-39762c47'
SOURCE = '42f9164754312f12850d9b8789c062fa7fb8069f'
ARCHIVE_SHA256 = 'f9bed05bd582e0796e2c4e78ff0f5174e5e1b6a3f447e5c3eab56ad002d473f9'
CHECKS_SHA256 = '51d7131492406f35e45e70a73b1a4cb2e3bd62f2ab03d8213562f6cd204f6ae6'
REVIEWER_COMMIT = '4885b96ac0a21a03376b320be74ad2bd1d49b40c'
REVIEWER_FILES = frozenset(('common.py', 'dataset.py', 'gpu.py', 'review.py', 'run_checks.py',
                          'summary.py', 'test_dataset.py', 'test_gpu.py', 'test_review.py', 'test_summary.py'))
HEX = re.compile(r'[0-9a-f]{64}\Z')
PASS = 'PROTOTYPE_V7_STORED_REVIEW_PASSED'


def require(value, reason):
    if not value:
        raise ValueError(reason)


def utc():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode() + b'\n'


def decode(raw):
    def unique(items):
        result = {}
        for key, value in items:
            require(key not in result, 'EXECUTION_DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    result = json.loads(raw, object_pairs_hook=unique,
                        parse_constant=lambda _: require(False, 'EXECUTION_NONFINITE_JSON'))
    canonical(result)
    return result


def no_links(path):
    require(not any(p.is_symlink() or getattr(p, 'is_junction', lambda: False)()
                    for p in (path, *path.parents)), 'EXECUTION_PATH_LINK_REFUSED')


def regular(path):
    path = Path(path).absolute()
    no_links(path)
    require(path.is_file(), 'EXECUTION_REGULAR_FILE_REQUIRED:' + str(path))
    return path


def file_hash(path):
    h = sha256()
    with regular(path).open('rb') as stream:
        for raw in iter(lambda: stream.read(1024**2), b''):
            h.update(raw)
    return h.hexdigest()


def pin(path, expected):
    require(type(expected) is str and HEX.fullmatch(expected), 'EXECUTION_EXTERNAL_HASH_REQUIRED')
    require(file_hash(path) == expected, 'EXECUTION_HASH_MISMATCH:' + str(path))


def write_new(path, value):
    with Path(path).open('xb') as stream:
        stream.write(canonical(value))


def new_child(path, parent):
    path = Path(path).absolute()
    require('..' not in path.parts and path.parent.resolve() == parent.resolve()
            and path.resolve() != parent.resolve() and not path.exists(), 'EXECUTION_NEW_CONTAINED_CHILD_REQUIRED')
    no_links(path)
    return path


def git_bound_bytes(files):
    """Bind exact raw files to the fixed reviewer commit, not the current HEAD."""
    repo_result = subprocess.run(['git', 'rev-parse', '--show-toplevel'], cwd=ROOT,
                                 capture_output=True, check=True)
    repo = Path(repo_result.stdout.decode().strip()).resolve()
    requests = [REVIEWER_COMMIT + ':' + path.resolve().relative_to(repo).as_posix() for path in files]
    result = subprocess.run(['git', 'cat-file', '--batch'], cwd=repo,
                            input=('\n'.join(requests) + '\n').encode(), capture_output=True, check=True)
    offset = 0
    for path, expected in files.items():
        end = result.stdout.index(b'\n', offset)
        header = result.stdout[offset:end].split()
        require(len(header) == 3 and header[1] == b'blob', 'EXECUTION_REVIEWER_GIT_BLOB_REQUIRED')
        length = int(header[2]); offset = end + 1
        require(result.stdout[offset:offset+length] == expected, 'EXECUTION_REVIEWER_GIT_BYTES_CHANGED:' + path.name)
        offset += length
        require(result.stdout[offset:offset+1] == b'\n', 'EXECUTION_GIT_BATCH_FORMAT')
        offset += 1
    require(offset == len(result.stdout), 'EXECUTION_GIT_BATCH_EXTRA_BYTES')


def prepared_identity():
    pin(CHECKS, CHECKS_SHA256)
    raw = regular(CHECKS).read_bytes()
    record = decode(raw)
    require(record['completed'] is True and record['source_unchanged'] is True
            and record['actual_packet_review'] is False and record['synthetic_tests'] is True
            and record['source_sha'] == SOURCE and record['source_archive_sha256'] == ARCHIVE_SHA256
            and record['source_files_verified'] == 603 and record['protected_files_verified'] == 316
            and len(record['commands']) == 4
            and all(type(row['returncode']) is int and row['returncode'] == 0 for row in record['commands']),
            'EXECUTION_PREPARATION_RECEIPT_INVALID')
    mapping = record['reviewer_files_sha256']
    require(set(mapping) == REVIEWER_FILES == {p.name for p in REVIEW.glob('*.py')},
            'EXECUTION_EXACT_TEN_REVIEWER_FILES_REQUIRED')
    files = {CHECKS: raw}
    for name in sorted(mapping):
        path = REVIEW / name
        pin(path, mapping[name]); files[path] = regular(path).read_bytes()
    git_bound_bytes(files)
    pin(ARCHIVE, ARCHIVE_SHA256)
    return {'reviewer_commit': REVIEWER_COMMIT, 'checks_sha256': CHECKS_SHA256,
            'reviewer_files_sha256': mapping, 'source_sha': SOURCE,
            'source_archive_sha256': ARCHIVE_SHA256, 'reviewer_git_files_verified': len(files)}


def command(packet, packet_sha256, extracted, review_output):
    return [sys.executable, '-B', str(REVIEW / 'review.py'),
            '--packet', str(packet), '--packet-sha256', packet_sha256,
            '--source-archive', str(ARCHIVE), '--source-archive-sha256', ARCHIVE_SHA256,
            '--source-sha', SOURCE, '--job', JOB, '--extracted', str(extracted),
            '--create-extraction', '--output', str(review_output)]


def completed_review(path, packet_sha256, prepared):
    result_path = path / 'prototype_stored_review.json'
    result = decode(regular(result_path).read_bytes())
    require(result['completed'] is True and result['status'] == PASS and result['errors'] == []
            and result['job'] == JOB and result['source_sha'] == SOURCE
            and result['source_archive_sha256'] == ARCHIVE_SHA256 and result['packet_sha256'] == packet_sha256
            and result['reviewer_files_sha256'] == prepared['reviewer_files_sha256'],
            'EXECUTION_COMPLETED_REVIEW_IDENTITY_MISMATCH')
    require(not (path / 'review_failure.json').exists(), 'EXECUTION_BOTH_PASS_AND_FAILURE_RECEIPTS')
    return {'path': str(result_path), 'sha256': file_hash(result_path),
            'summary_path': str(path / 'SUMMARY.md'), 'summary_sha256': file_hash(path / 'SUMMARY.md')}


def execute(*, packet, packet_sha256, output, review_output, extracted):
    require(type(packet_sha256) is str and HEX.fullmatch(packet_sha256), 'EXECUTION_EXTERNAL_PACKET_HASH_REQUIRED')
    packet = Path(packet).absolute()
    require('..' not in packet.parts and packet.resolve() == PACKET.resolve(), 'EXECUTION_FIXED_PACKET_PATH_REQUIRED')
    output = new_child(output, HERE)
    review_output = new_child(review_output, REVIEW)
    extracted = new_child(extracted, REVIEW)
    require(review_output != extracted, 'EXECUTION_OUTPUT_EXTRACTION_MUST_DIFFER')
    output.mkdir(exist_ok=False)
    cmd = command(packet, packet_sha256, extracted, review_output)
    started, tick = utc(), time.monotonic()
    record = {'schema': 'cas-meta2-v7-review-execution/0.1', 'completed': False,
        'status': 'V7_REVIEW_EXECUTION_FAILED', 'job': JOB, 'source_sha': SOURCE,
        'source_archive_sha256': ARCHIVE_SHA256, 'packet': str(packet), 'packet_sha256': packet_sha256,
        'reviewer_commit': REVIEWER_COMMIT, 'preparation_receipt_sha256': CHECKS_SHA256,
        'command': cmd, 'cwd': str(ROOT), 'wrapper_pid': os.getpid(), 'pid': None,
        'started_utc': started, 'child_started': False, 'returncode': None, 'wrapper_returncode': 1,
        'review_output': str(review_output), 'extracted': str(extracted),
        'independent_review_passed': False, 'errors': [],
        'wrapper_sha256': file_hash(Path(__file__)),
        'boundary': 'One offline review capture. A process exit alone is not a passed review or learning acceptance.'}
    write_new(output / 'command.json', {'command': cmd, 'cwd': str(ROOT), 'started_utc': started,
                                      'packet_sha256': packet_sha256, 'reviewer_commit': REVIEWER_COMMIT})
    process = None
    with (output / 'stdout.txt').open('xb') as stdout, (output / 'stderr.txt').open('xb') as stderr:
        try:
            before = prepared_identity(); record['prepared_before'] = before
            pin(packet, packet_sha256)
            process = subprocess.Popen(cmd, cwd=ROOT, stdout=stdout, stderr=stderr)
            record['pid'], record['child_started'] = process.pid, True
            write_new(output / 'process_started.json', {'pid': process.pid, 'command': cmd,
                'cwd': str(ROOT), 'started_utc': utc(), 'wrapper_pid': os.getpid()})
            record['returncode'] = process.wait()
            record['child_finished_utc'] = utc()
            after = prepared_identity(); record['prepared_after'] = after
            require(before == after, 'EXECUTION_PREPARED_IDENTITY_CHANGED')
            pin(packet, packet_sha256)
            require(type(record['returncode']) is int and record['returncode'] == 0,
                    'EXECUTION_REVIEW_CHILD_NONZERO')
            record['review_receipt'] = completed_review(review_output, packet_sha256, before)
            record.update(completed=True, status='V7_REVIEW_EXECUTION_PASSED',
                          independent_review_passed=True, wrapper_returncode=0)
        except BaseException as error:
            record['errors'].append({'type': type(error).__name__, 'message': str(error),
                                     'traceback': traceback.format_exc()})
            if process is not None and process.poll() is None:
                # On wrapper interruption, stop only its own local audit child.
                record['child_termination_requested'] = True
                try:
                    process.terminate(); record['returncode'] = process.wait(timeout=30)
                    record['child_finished_utc'] = utc()
                except BaseException as stop_error:
                    record['errors'].append({'type': type(stop_error).__name__, 'message': str(stop_error),
                                             'stage': 'stop_own_audit_child'})
    record.update(finished_utc=utc(), wall_seconds=time.monotonic()-tick,
                  stdout_sha256=file_hash(output/'stdout.txt'), stderr_sha256=file_hash(output/'stderr.txt'))
    for name in ('review_failure.json', 'prototype_stored_review.json'):
        path = review_output/name
        if path.is_file():
            try:
                record.setdefault('observed_review_artifacts', {})[name] = file_hash(path)
            except BaseException as error:
                record['errors'].append({'type': type(error).__name__, 'message': str(error),
                                         'stage': 'final_artifact_hash'})
                record.update(completed=False, status='V7_REVIEW_EXECUTION_FAILED',
                              independent_review_passed=False, wrapper_returncode=1)
    receipt = output/'process_receipt.json'
    write_new(receipt, record)
    result = {'status': record['status'], 'completed': record['completed'], 'pid': record['pid'],
        'returncode': record['returncode'], 'wrapper_returncode': record['wrapper_returncode'],
        'process_receipt': str(receipt), 'process_receipt_sha256': file_hash(receipt),
        'review_receipt_sha256': record.get('review_receipt', {}).get('sha256')}
    write_new(output/'execution_result.json', result)
    print(json.dumps(result), flush=True)
    return record['wrapper_returncode']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ('packet', 'output', 'review-output', 'extracted'):
        parser.add_argument('--'+name, required=True, type=Path)
    parser.add_argument('--packet-sha256', required=True)
    args = parser.parse_args(argv)
    return execute(packet=args.packet, packet_sha256=args.packet_sha256, output=args.output,
                   review_output=args.review_output, extracted=args.extracted)


if __name__ == '__main__':
    raise SystemExit(main())
