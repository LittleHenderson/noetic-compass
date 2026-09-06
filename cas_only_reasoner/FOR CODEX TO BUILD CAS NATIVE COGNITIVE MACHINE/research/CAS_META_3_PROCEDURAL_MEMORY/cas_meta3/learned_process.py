"""AWS-only writer-exit -> fresh reader process coordinator; not a launcher."""
from datetime import datetime, timezone
from hashlib import sha256
import os
from pathlib import Path
import subprocess
import sys

from . import learned_writer as writer
from . import learned_reuse as reuse
from . import learning_evidence as evidence


def source_identity():
    return {'writer': writer.source_identity(), 'reader': reuse.source_identity(),
            'coordinator_sha256': sha256(Path(__file__).read_bytes()).hexdigest()}


def check_binding(saved_request, reader_request):
    """The new reader must receive exactly the saved candidate and trust scope."""
    required = {'job', 'store_path', 'expected_digest', 'trust_inputs', 'source_public',
                'public_cases', 'output', 'native_output'}
    writer.require(type(reader_request) is dict and required <= set(reader_request)
                   <= required | {'call_count', 'return_call'}, 'READER_REQUEST_SCHEMA')
    trust = dict(saved_request['trust'])
    digest = trust.pop('expected_digest')
    writer.require(reader_request['expected_digest'] == digest
                   and reader_request['trust_inputs'] == trust
                   and writer.scoped(reader_request['store_path']) == writer.scoped(saved_request['store_path']),
                   'READER_MUST_MATCH_WRITER_CANDIDATE_AND_TRUST')


def run_process_pair(*, writer_request_path, writer_request_sha256,
                     reader_request, process_output, expected_source_identity):
    # No local neural path. A later paid launcher must also bind real AWS identity,
    # source archive, budget reservation and independent termination deadline.
    reuse.native_support.aws_guard(reader_request.get('job'))
    writer.require(os.name == 'posix', 'PROCESS_PAIR_AWS_LINUX_REQUIRED')
    writer.require(source_identity() == expected_source_identity, 'PROCESS_PAIR_SOURCE_MISMATCH')
    saved_request, _, store_path, _ = writer.read_request(writer_request_path, writer_request_sha256)
    check_binding(saved_request, reader_request)
    reader_output, _ = reuse.native_support.checked_paths(reader_request['output'],
        reader_request['native_output'], reader_request['job'], new=True)
    output = writer.scoped(process_output)
    writer.require(not output.exists() and not reader_output.is_relative_to(output)
        and not output.is_relative_to(reader_output) and not store_path.is_relative_to(output),
        'DISJOINT_NEW_PROCESS_OUTPUT_REQUIRED')
    output.mkdir(parents=True)
    exited = writer.run_writer(writer_request_path, writer_request_sha256, output / 'writer')
    writer.require(source_identity() == expected_source_identity, 'PROCESS_PAIR_SOURCE_CHANGED')
    writer.require(sha256(store_path.read_bytes()).hexdigest() == exited['store_sha256'],
                   'STORE_CHANGED_AFTER_WRITER_EXIT')
    request_path = output / 'reader_request.json'
    writer.save_new(request_path, reader_request)
    request_hash = sha256(request_path.read_bytes()).hexdigest()
    command = [sys.executable, '-B', '-m', 'cas_meta3.learned_reuse',
               '--request', str(request_path), '--request-sha256', request_hash]
    started = datetime.now(timezone.utc).isoformat()
    writer.require(datetime.fromisoformat(started) >= datetime.fromisoformat(exited['finished_utc']),
                   'READER_START_PRECEDES_WRITER_EXIT')
    paths = reuse.native_support.child_source_paths()
    with (output / 'reader.stdout.txt').open('xb') as stdout, (output / 'reader.stderr.txt').open('xb') as stderr:
        child = subprocess.Popen(command, cwd=writer.ROOT, stdout=stdout, stderr=stderr,
            env={**os.environ, 'PYTHONPATH': os.pathsep.join(map(str, paths)), 'PYTHONDONTWRITEBYTECODE': '1'})
        timed_out = False
        try:
            code = child.wait(timeout=1200)
        except subprocess.TimeoutExpired:
            timed_out = True
            child.kill()
            code = child.wait(timeout=10)
        except BaseException:
            child.kill()
            child.wait(timeout=10)
            raise
    record = {'schema': 'cas-meta3-learned-process-pair/0.1', 'job': reader_request['job'],
        'command': command, 'writer_pid': exited['pid'], 'reader_pid': child.pid,
        'reader_started_utc': started, 'reader_finished_utc': datetime.now(timezone.utc).isoformat(),
        'writer_finished_utc': exited['finished_utc'], 'reader_returncode': code,
        'timed_out': timed_out, 'automatic_retries': 0, 'fresh_reader_verified': False,
        'writer_exit_receipt_sha256': sha256((output / 'writer/process_receipt.json').read_bytes()).hexdigest(),
        'reader_request_sha256': request_hash, 'source_identity': expected_source_identity,
        'qualification_status': 'UNQUALIFIED', 'learning_performed': False,
        'promotion_granted': False, 'retention_tested': False, 'rollback_tested': False}
    try:
        writer.require(code == 0 and not timed_out and child.pid != exited['pid'], 'FRESH_READER_PROCESS_FAILED')
        raw = writer.read_bytes(reader_output / 'reuse_receipt.json', evidence.MAX_BYTES)
        result = evidence._json(raw)
        writer.require(result['schema'] == 'cas-meta3-learned-native-reuse/0.1'
            and result['status'] == 'NATIVE_REUSE_EXECUTED' and result['pid'] == child.pid
            and result['job'] == reader_request['job']
            and result['package_sha256'] == reader_request['expected_digest']
            and result['store_sha256'] == exited['store_sha256'] == sha256(store_path.read_bytes()).hexdigest()
            and result['source_identity_sha256'] == sha256((reader_output / 'source_identity.json').read_bytes()).hexdigest()
            and evidence._json((reader_output / 'source_identity.json').read_bytes()) == expected_source_identity['reader']
            and source_identity() == expected_source_identity, 'FRESH_READER_RESULT_BINDING_FAILED')
        record.update(fresh_reader_verified=True, reader_receipt_sha256=sha256(raw).hexdigest(),
                      store_sha256=exited['store_sha256'])
    except Exception as error:
        record['error'] = {'type': type(error).__name__, 'message': str(error)}
    writer.save_new(output / 'process_pair_receipt.json', record)
    writer.require(record['fresh_reader_verified'], 'PROCESS_PAIR_NOT_VERIFIED')
    return record
