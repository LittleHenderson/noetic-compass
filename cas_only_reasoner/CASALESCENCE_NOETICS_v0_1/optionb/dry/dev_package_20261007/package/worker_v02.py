"""Option B job b1 guest operator. Source only until separately admitted on AWS.

Derived from the CASalescence v0.2 guest that ran on 2026-10-04. Kept from its
C1 amendment: it builds the accepted package's own pinned isolated overlay from
the official index (binary wheels only) and sends status uploads without a
Content-Type header. The pilot's science stages are removed. This guest starts
the sealed package's runner commands in order, with time limits, and reads back
one outcome code. No other installation, no credentials, cloud SDK, source
modification, scoring, scientific receipt issuance, retry, or alternate
experiment. The controller owns host termination and multipart
completion/abort. All bulk operations stream bounded chunks.
"""
from __future__ import annotations

import hashlib
import http.client
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import resource
import shutil
import signal
import stat
import subprocess
import sys
import time
from urllib.parse import parse_qs, urlsplit
import zipfile


BASE = Path(__file__).resolve().parent
WORK = BASE / 'work'
CONTROL = WORK / 'controller'
STATE = BASE / 'transport-state'
PAYLOAD = BASE / 'payload'
SOURCE = WORK / 'source'
OUT = WORK / 'run_b1'
CACHE = PAYLOAD / 'models'
OVERLAY = BASE / 'overlay'
VENV = OVERLAY / 'venv'
VENV_PYTHON = VENV / 'bin' / 'python'
IMAGE_SITE = '/opt/pytorch/lib/python3.12/site-packages'
REQUIREMENTS_SHA = '6d9ee033baf3acbcecfbf8feb735a807025c141cac8e6060e480154c2c1c15b7'
BUCKET = 'helm-primary-pointer-807562639912-20261001-v4'
PREFIX = 'bridge-control-20260822/helm-pointer-saturation-20261001-v4/'
ARCHIVE_KEY = PREFIX + 'pointer-saturation-deliverable.zip'
# The next four pins are stamped by build_contract_b1.py once source.zip exists.
# Until then they hold placeholders, and validate_contract refuses every package.
SOURCE_ZIP_SHA = '6b36f2cbe918b45a3757f76f9e366ba9006d02873ae1a603afbbdc21a39e89a0'
SOURCE_ZIP_BYTES = 888995
SOURCE_MEMBERS = 18
SOURCE_SEAL = 'dad0a576fa402055e53f98506680679831ffb2cc385110a0ebd6d752bf5fb1ce'
SOURCE_UNPACKED_CAP = 8_388_608
SOURCE_FILE_CAP = 400
MODEL_REVISION = '7ae557604adf67be50417f59c2c2f167def9a775'
MODEL_FILES = 7
MODEL_BYTES = 999_586_347
# Seconds after launch. The controller and the watchdog must use the same numbers.
CLOCK = {'setup_cutoff_unix': 1800, 'work_cutoff_unix': 8100, 'score_cutoff_unix': 8400,
         'force_cutoff_unix': 10500, 'termination_unix': 10800}
LIMITS = {'selftest_seconds': 900, 'model_stage_seconds': 8100, 'gate_seconds': 300,
          'score_seconds_min': 120, 'score_seconds_max': 240, 'scientific_bytes': 80_000_000,
          'archive_bytes': 100_000_000, 'model_calls': 5000}
# The runner's command lines (FILE_FORMATS.md section 16). A {NAME} part is filled in by
# execute_science. The build-time text check looks up every word here in job/runner_b1.py.
RUNNER = {
    'selftest': ('selftest', '--mode', 'gate0', '--package-dir', '{PACKAGE}', '--model-dir', '{MODEL}',
                 '--output-dir', '{OUTPUT}', '--expect-prompt-list-sha256', '{PROMPT_LIST}',
                 '--expect-padding-plan-sha256', '{PADDING_PLAN}'),
    'run_practice': ('run-practice', '--package-dir', '{PACKAGE}', '--model-dir', '{MODEL}',
                     '--output-dir', '{OUTPUT}', '--deadline-unix', '{WORK_CUTOFF}'),
    'gate': ('gate', '--package-dir', '{PACKAGE}', '--output-dir', '{OUTPUT}', '--deadline-unix', '{WORK_CUTOFF}'),
    # The final stage is given the prompt folder only. No key folder is named.
    'run_final': ('run-final', '--constants', '{CONSTANTS}', '--prompts-dir', '{PROMPTS}',
                  '--model-dir', '{MODEL}', '--output-dir', '{OUTPUT}', '--deadline-unix', '{WORK_CUTOFF}'),
    'score': ('score', '--package-dir', '{PACKAGE}', '--output-dir', '{OUTPUT}',
              '--model-receipt-before', '{MODEL_PRE}', '--model-receipt-after-calls', '{MODEL_AFTER}')}
MAX_INPUT = 4_200_000_000
MAX_WORK = LIMITS['scientific_bytes']
MAX_ARCHIVE = LIMITS['archive_bytes']
PART_SIZE = 64 * 1024 ** 2
MAX_PARTS = 269
MAX_SMALL = 65_536
MAX_FILES = 100_000
CHUNK = 1024 * 1024
START_WALL = time.time()
START_MONO = time.monotonic()
CONFIG = {}
CONTRACT = {}
STAGES = {}
FAULTS = []
SETUP_COMPLETE = False
PROGRESS_COUNT = 0
LAST_PROGRESS = 0.0
CGROUP = None
PART_RECORDS = []
OBSERVED_DEPENDENCIES = {}
UPLOAD_ATTEMPTED = False
CURRENT_STAGE = 'STARTUP'
SOURCE_PRE_VERIFIED = False
MODEL_PRE_VERIFIED = False
SOURCE_POST_VERIFIED = False
MODEL_POST_VERIFIED = False


class Refusal(RuntimeError):
    pass


def require(condition, code):
    if not condition:
        raise Refusal(code)


def remaining(epoch):
    # Never extend a launch-relative deadline after a backward clock adjustment.
    return min(epoch - time.time(), epoch - START_WALL - (time.monotonic() - START_MONO))


def check_time(epoch, code='ABSOLUTE_DEADLINE_REACHED'):
    require(remaining(epoch) > 0, code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def write_json(path, value, exclusive=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = canonical(value)
    with path.open('xb' if exclusive else 'wb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return {'path': path.name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def load_json(path, cap=MAX_SMALL):
    require(ordinary(path).st_size <= cap, 'JSON_FILE_TOO_LARGE:' + path.name)
    with path.open('rb') as handle:
        data = handle.read(cap + 1)
    require(len(data) <= cap, 'JSON_READ_CAP')
    return json.loads(data.decode('utf-8-sig'))


def safe_error(exc):
    # Signed transport URLs and their query strings must never enter evidence.
    text = re.sub(r'https?://\S+', '[URL_REDACTED]', str(exc))
    return {'type': type(exc).__name__, 'message': text[:2000], 'stage': CURRENT_STAGE}


def ordinary(path):
    info = path.lstat()
    require(not path.is_symlink(), 'LINK_REFUSED:' + path.name)
    require(stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode), 'SPECIAL_FILE_REFUSED:' + path.name)
    if stat.S_ISREG(info.st_mode):
        require(info.st_nlink == 1, 'HARDLINK_REFUSED:' + path.name)
    return info


def safe_relative(value):
    require(type(value) is str and value and '\\' not in value and '\x00' not in value,
            'UNSAFE_RELATIVE_PATH')
    path = PurePosixPath(value)
    require(not path.is_absolute() and all(part not in ('', '.', '..') for part in value.split('/'))
            and ':' not in value, 'UNSAFE_RELATIVE_PATH')
    return path


def sha_file(path, deadline):
    before = ordinary(path)
    require(stat.S_ISREG(before.st_mode), 'HASH_EXPECTED_FILE')
    value = hashlib.sha256()
    size = 0
    with path.open('rb') as handle:
        while True:
            check_time(deadline, 'HASH_DEADLINE')
            chunk = handle.read(CHUNK)
            if not chunk:
                break
            size += len(chunk)
            value.update(chunk)
    after = ordinary(path)
    require((before.st_size, before.st_mtime_ns, before.st_ino) ==
            (after.st_size, after.st_mtime_ns, after.st_ino) and size == before.st_size,
            'HASH_FILE_CHANGED:' + path.name)
    return {'bytes': size, 'sha256': value.hexdigest()}


def tree_files(root, deadline, cap_bytes=None, cap_files=MAX_FILES):
    require(stat.S_ISDIR(ordinary(root).st_mode), 'TREE_ROOT_NOT_DIRECTORY')
    result = {}
    total = 0
    pending = [root]
    while pending:
        check_time(deadline, 'TREE_SCAN_DEADLINE')
        folder = pending.pop()
        with os.scandir(folder) as items:
            for item in items:
                check_time(deadline, 'TREE_SCAN_DEADLINE')
                path = Path(item.path)
                info = ordinary(path)
                if stat.S_ISDIR(info.st_mode):
                    pending.append(path)
                else:
                    relative = path.relative_to(root).as_posix()
                    safe_relative(relative)
                    require(relative not in result, 'DUPLICATE_TREE_PATH')
                    total += info.st_size
                    require(len(result) < cap_files, 'TREE_FILE_COUNT_CAP')
                    require(cap_bytes is None or total <= cap_bytes, 'SCIENTIFIC_OUTPUT_SIZE_CAP')
                    result[relative] = info.st_size
    return result


def verify_tree(root, declared, deadline, receipt):
    require(type(declared) is dict and declared, 'EMPTY_DECLARED_TREE')
    actual = tree_files(root, deadline)
    require(set(actual) == set(declared), 'IMMUTABLE_TREE_MEMBERSHIP_CHANGED:' + root.name)
    checked = []
    for name in sorted(declared):
        safe_relative(name)
        measured = sha_file(root / name, deadline)
        require(measured == declared[name], 'IMMUTABLE_FILE_CHANGED:' + name)
        checked.append(dict(path=name, **measured))
    write_json(receipt, {'status': 'EXACT_FILE_MEMBERSHIP_AND_BYTES_VERIFIED',
        'root_role': root.name, 'files': checked, 'file_count': len(checked),
        'total_bytes': sum(row['bytes'] for row in checked), 'verified_unix': time.time()})


def transport_url(url, key, part=None):
    parsed = urlsplit(url)
    require(parsed.scheme == 'https' and parsed.hostname in
            (BUCKET + '.s3.amazonaws.com', BUCKET + '.s3.us-west-2.amazonaws.com')
            and parsed.port in (None, 443) and parsed.username is None and parsed.password is None
            and parsed.path == '/' + key and not parsed.fragment, 'TRANSPORT_ENDPOINT_REFUSED')
    if part is not None:
        query = parse_qs(parsed.query, strict_parsing=True)
        require(query.get('partNumber') == [str(part)] and
                query.get('uploadId') == [CONFIG['multipart']['upload_id']], 'MULTIPART_URL_BINDING')
    return parsed


def connection(parsed, deadline):
    check_time(deadline, 'TRANSPORT_DEADLINE')
    return http.client.HTTPSConnection(parsed.hostname, 443, timeout=min(30.0, remaining(deadline)))


def request_target(parsed):
    return parsed.path + ('?' + parsed.query if parsed.query else '')


def put_small(key, value, deadline):
    data = canonical(value)
    require(len(data) <= MAX_SMALL, 'SMALL_TRANSPORT_CAP')
    parsed = transport_url(CONFIG['put_urls'][key], PREFIX + key)
    conn = connection(parsed, deadline)
    try:
        conn.request('PUT', request_target(parsed), body=data,
                     headers={'Content-Length': str(len(data))})
        response = conn.getresponse()
        require(200 <= response.status < 300, 'SMALL_PUT_HTTP_' + str(response.status))
        response.read(4096)
    finally:
        conn.close()


def progress(force=False):
    global PROGRESS_COUNT, LAST_PROGRESS
    if not CONFIG or PROGRESS_COUNT >= 98 or (not force and time.monotonic() - LAST_PROGRESS < 180):
        return
    if remaining(CONFIG['force_cutoff_unix'] - 150) <= 0:
        return
    PROGRESS_COUNT += 1
    LAST_PROGRESS = time.monotonic()
    value = {'job': CONFIG['job'], 'instance': CONFIG['instance'], 'stage': CURRENT_STAGE,
             'setup_complete': SETUP_COMPLETE, 'progress_attempt': PROGRESS_COUNT,
             'time_unix': time.time(), 'fault_count': len(FAULTS), 'completed_parts': len(PART_RECORDS)}
    write_json(STATE / 'progress.json', value)
    try:
        put_small('progress.json', value, min(CONFIG['force_cutoff_unix'] - 150, time.time() + 20))
    except BaseException as exc:
        write_json(STATE / ('progress-failure-' + str(PROGRESS_COUNT) + '.json'), safe_error(exc))


def validate_config():
    global CONFIG
    CONFIG = load_json(BASE / 'guest.json', 1024 * 1024)
    require(re.fullmatch(r'[A-Za-z0-9_.-]+', CONFIG['job']) is not None, 'JOB_ID_INVALID')
    require(re.fullmatch(r'i-[0-9a-f]+', CONFIG['instance']) is not None, 'INSTANCE_ID_INVALID')
    launch = CONFIG['launch_unix']
    require(type(launch) in (int, float) and math.isfinite(launch), 'LAUNCH_TIME_INVALID')
    for name in ('setup_cutoff_unix', 'work_cutoff_unix', 'force_cutoff_unix', 'termination_unix'):
        require(CONFIG[name] == launch + CLOCK[name], 'ABSOLUTE_CLOCK_CONTRACT:' + name)
    check_time(CONFIG['setup_cutoff_unix'], 'SETUP_ALREADY_EXPIRED')
    require(0 < CONFIG['input_bytes'] <= MAX_INPUT and CONFIG['output_key'] == ARCHIVE_KEY,
            'TRANSPORT_LIMIT_OR_KEY')
    for name in ('input_sha256', 'payload_manifest_sha256'):
        require(re.fullmatch(r'[a-f0-9]{64}', CONFIG[name]) is not None, 'CONFIG_HASH_INVALID')
    transport_url(CONFIG['input_url'], PREFIX + 'input.zip')
    require(set(CONFIG['put_urls']) == {'progress.json', 'transport-result.json'}, 'SMALL_KEYS_SCOPE')
    for name, url in CONFIG['put_urls'].items():
        transport_url(url, PREFIX + name)
    multi = CONFIG['multipart']
    require(type(multi['upload_id']) is str and 0 < len(multi['upload_id']) <= 2048
            and multi['part_size'] == PART_SIZE and len(multi['part_urls']) == MAX_PARTS,
            'MULTIPART_CONFIG')
    require(set(multi['part_urls']) == {str(i) for i in range(1, MAX_PARTS + 1)}, 'PART_URL_ROSTER')
    for i in range(1, MAX_PARTS + 1):
        transport_url(multi['part_urls'][str(i)], ARCHIVE_KEY, i)
    # No guest/config copies: credentials and signed URLs remain outside evidence.
    write_json(CONTROL / 'PUBLIC_GUEST_CONTRACT.json', {k: CONFIG[k] for k in
        ('job', 'instance', 'launch_unix', 'setup_cutoff_unix', 'work_cutoff_unix',
         'force_cutoff_unix', 'termination_unix', 'input_bytes', 'input_sha256',
         'payload_manifest_sha256', 'output_key')})


def imds_instance():
    conn = http.client.HTTPConnection('169.254.169.254', timeout=3)
    try:
        conn.request('PUT', '/latest/api/token', body=b'',
                     headers={'X-aws-ec2-metadata-token-ttl-seconds': '60'})
        reply = conn.getresponse()
        require(reply.status == 200, 'IMDSV2_TOKEN_REQUIRED')
        token = reply.read(4097)
        require(0 < len(token) <= 4096, 'IMDSV2_TOKEN_SIZE')
        conn.request('GET', '/latest/meta-data/instance-id',
                     headers={'X-aws-ec2-metadata-token': token.decode('ascii')})
        reply = conn.getresponse()
        require(reply.status == 200 and reply.read(256).decode('ascii') == CONFIG['instance'],
                'IMDS_INSTANCE_MISMATCH')
    finally:
        conn.close()


def download_input():
    deadline = CONFIG['setup_cutoff_unix']
    marker = STATE / 'input-get-attempt.json'
    write_json(marker, {'attempted_unix': time.time(), 'bytes': CONFIG['input_bytes']}, exclusive=True)
    parsed = transport_url(CONFIG['input_url'], PREFIX + 'input.zip')
    conn = connection(parsed, deadline)
    value = hashlib.sha256()
    size = 0
    target = BASE / 'input.zip'
    try:
        conn.request('GET', request_target(parsed))
        reply = conn.getresponse()
        require(reply.status == 200, 'INPUT_GET_HTTP_' + str(reply.status))
        require(reply.getheader('Content-Length') == str(CONFIG['input_bytes']), 'INPUT_LENGTH_MISMATCH')
        with target.open('xb') as handle:
            while True:
                check_time(deadline, 'INPUT_DOWNLOAD_DEADLINE')
                chunk = reply.read(min(CHUNK, CONFIG['input_bytes'] - size + 1))
                if not chunk:
                    break
                size += len(chunk)
                require(size <= CONFIG['input_bytes'], 'INPUT_BYTE_CAP')
                value.update(chunk)
                handle.write(chunk)
                progress()
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        conn.close()
    require(size == CONFIG['input_bytes'] and value.hexdigest() == CONFIG['input_sha256'],
            'INPUT_CUSTODY_FAILURE')
    write_json(CONTROL / 'INPUT_RECEIPT.json', {'bytes': size, 'sha256': value.hexdigest(),
        'single_get_attempt': True, 'status': 'EXACT_TRANSPORT_BYTES_VERIFIED'})
    return target


def zip_records(archive, cap_bytes, cap_files):
    entries = archive.infolist()
    require(0 < len(entries) <= cap_files, 'ZIP_MEMBER_COUNT_CAP')
    names = set()
    total = 0
    for entry in entries:
        name = entry.filename
        safe_relative(name)
        require(name not in names and not entry.is_dir() and not entry.flag_bits & 1,
                'ZIP_DUPLICATE_DIRECTORY_OR_ENCRYPTION')
        mode = entry.external_attr >> 16
        require(stat.S_IFMT(mode) in (0, stat.S_IFREG), 'ZIP_LINK_OR_SPECIAL_FILE')
        require(entry.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), 'ZIP_COMPRESSION_REFUSED')
        names.add(name)
        total += entry.file_size
        require(total <= cap_bytes, 'ZIP_EXPANSION_CAP')
    return entries


def extract_entry(archive, entry, target, expected, deadline):
    require(entry.file_size == expected['bytes'], 'ZIP_MEMBER_SIZE_MISMATCH')
    target.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    value = hashlib.sha256()
    with archive.open(entry, 'r') as incoming, target.open('xb') as outgoing:
        while True:
            check_time(deadline, 'ZIP_EXTRACTION_DEADLINE')
            chunk = incoming.read(CHUNK)
            if not chunk:
                break
            count += len(chunk)
            require(count <= expected['bytes'], 'ZIP_MEMBER_BYTE_CAP')
            value.update(chunk)
            outgoing.write(chunk)
        outgoing.flush()
        os.fsync(outgoing.fileno())
    require(count == expected['bytes'] and value.hexdigest() == expected['sha256'], 'ZIP_MEMBER_HASH_MISMATCH')


def extract_input(path):
    global CONTRACT
    deadline = CONFIG['setup_cutoff_unix']
    with zipfile.ZipFile(path, 'r') as archive:
        entries = zip_records(archive, MAX_INPUT + 4 * 1024 * 1024, 4096)
        record = archive.getinfo('CONTRACT.json')
        require(record.file_size <= 4 * 1024 * 1024, 'CONTRACT_SIZE_CAP')
        raw = archive.read(record)
        require(hashlib.sha256(raw).hexdigest() == CONFIG['payload_manifest_sha256'], 'CONTRACT_HASH_MISMATCH')
        CONTRACT = json.loads(raw.decode('utf-8-sig'))
        validate_contract()
        expected = {'CONTRACT.json': {'bytes': len(raw), 'sha256': CONFIG['payload_manifest_sha256']},
                    'source.zip': {'bytes': CONTRACT['source']['zip_bytes'], 'sha256': SOURCE_ZIP_SHA}}
        expected.update({'models/' + k: v for k, v in CONTRACT['model_cache']['files'].items()})
        expected.update({'authority/' + k: v for k, v in CONTRACT['external_authority']['files'].items()})
        require({entry.filename for entry in entries} == set(expected), 'INPUT_EXACT_MEMBERSHIP_FAILURE')
        for entry in entries:
            target = CONTROL / 'CONTRACT.json' if entry.filename == 'CONTRACT.json' else PAYLOAD / entry.filename
            extract_entry(archive, entry, target, expected[entry.filename], deadline)
            progress()
    with zipfile.ZipFile(PAYLOAD / 'source.zip', 'r') as archive:
        entries = zip_records(archive, SOURCE_UNPACKED_CAP, SOURCE_FILE_CAP)
        members = CONTRACT['source']['members']
        require({entry.filename for entry in entries} == set(members), 'SOURCE_ZIP_EXACT_MEMBERSHIP_FAILURE')
        for entry in entries:
            extract_entry(archive, entry, SOURCE / entry.filename, members[entry.filename], deadline)
    shutil.copytree(PAYLOAD / 'authority', WORK / 'external-authority')


def validate_contract():
    require(CONTRACT['schema'] == 'cas-optionb-b1-guest-contract/v1' and CONTRACT['job'] == CONFIG['job']
            and CONTRACT['clock_seconds'] == CLOCK, 'CONTRACT_SCHEMA_JOB_OR_CLOCK')
    source = CONTRACT['source']
    require(source['zip_sha256'] == SOURCE_ZIP_SHA and source['zip_bytes'] == SOURCE_ZIP_BYTES and
            source['manifest_sha256'] == SOURCE_SEAL and len(source['members']) == SOURCE_MEMBERS,
            'EXACT_B1_SOURCE_REQUIRED')
    cache = CONTRACT['model_cache']
    require(len(cache['files']) == MODEL_FILES and
            sum(row['bytes'] for row in cache['files'].values()) == MODEL_BYTES,
            'EXACT_MODEL_CACHE_ROSTER_REQUIRED')
    for declared in (source['members'], cache['files'], CONTRACT['external_authority']['files']):
        require(type(declared) is dict and declared, 'DECLARED_FILES_REQUIRED')
        for name, row in declared.items():
            safe_relative(name)
            require(set(row) == {'bytes', 'sha256'} and type(row['bytes']) is int and row['bytes'] >= 0
                    and re.fullmatch(r'[a-f0-9]{64}', row['sha256']) is not None, 'FILE_DECLARATION_INVALID')
    require(set(cache['snapshots']) == {'B'}, 'MODEL_SNAPSHOT_ROLES')
    snapshot = cache['snapshots']['B']
    safe_relative(snapshot)
    require(PurePosixPath(snapshot).name == MODEL_REVISION and
            all(name.startswith(snapshot + '/') for name in cache['files']), 'MODEL_REVISION_MISMATCH')
    require(CONTRACT['runtime']['executable'] == '/opt/pytorch/bin/python', 'PREINSTALLED_PYTHON_ONLY')
    require(CONTRACT['limits'] == LIMITS, 'ADMITTED_LIMITS_CHANGED')
    require(CONTRACT['external_authority'].get('owner_record') in CONTRACT['external_authority']['files'],
            'OWNER_APPROVAL_RECORD_ABSENT')
    # The contract must carry the two hashes the pre-check job printed (seal step 7).
    bound = CONTRACT.get('precheck')
    require(type(bound) is dict and all(re.fullmatch(r'[a-f0-9]{64}', str(bound.get(key))) is not None
            for key in ('prompt_list_sha256', 'padding_plan_sha256')), 'PRECHECK_BINDING_REQUIRED')


def cgroup_pids():
    require(CGROUP is not None, 'CGROUP_NOT_VERIFIED')
    text = (CGROUP / 'cgroup.procs').read_text(encoding='ascii')
    return {int(line) for line in text.splitlines() if line}


def runtime_preflight():
    global CGROUP, OBSERVED_DEPENDENCIES
    check_time(CONFIG['setup_cutoff_unix'])
    require(sys.platform == 'linux' and Path(sys.executable).resolve() ==
            Path('/opt/pytorch/bin/python').resolve(), 'PREINSTALLED_LINUX_PYTHON_REQUIRED')
    runtime = CONTRACT['runtime']
    require(sys.version.split()[0] == runtime['python_version'], 'PYTHON_VERSION_MISMATCH')
    require(not any(name.startswith('CAS_FLEET') for name in os.environ), 'FLEET_ENV_REFUSED')
    group_rows = Path('/proc/self/cgroup').read_text(encoding='ascii').splitlines()
    unified = [line[3:] for line in group_rows if line.startswith('0::')]
    require(len(unified) == 1 and unified[0] == '/system.slice/helm-op11-work.service',
            'DEDICATED_CGROUP_REQUIRED')
    CGROUP = Path('/sys/fs/cgroup') / unified[0].lstrip('/')
    actual = {name: (CGROUP / name).read_text(encoding='ascii').strip()
              for name in ('memory.max', 'memory.swap.max', 'pids.max', 'cpu.max')}
    require(actual['memory.max'].isdigit() and 0 < int(actual['memory.max']) <= 28 * 1024 ** 3,
            'MEMORY_CGROUP_NOT_APPLIED')
    require(actual['memory.swap.max'] == '0' and actual['pids.max'].isdigit() and
            0 < int(actual['pids.max']) <= 128, 'SWAP_OR_TASK_CGROUP_NOT_APPLIED')
    quota, period = actual['cpu.max'].split()
    require(quota.isdigit() and period.isdigit() and 0 < int(quota) <= 8 * int(period),
            'CPU_CGROUP_NOT_APPLIED')
    require(cgroup_pids() == {os.getpid()}, 'DEDICATED_CGROUP_HAS_OTHER_WORKLOAD')
    affinity = sorted(os.sched_getaffinity(0))
    require(len(affinity) >= 1, 'NO_CPU_AFFINITY')
    os.sched_setaffinity(0, set(affinity[:8]))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    # C1 runtime amendment. The sealed contract's runtime block is first checked
    # exactly as written (it is not edited); then the accepted package's own
    # pinned requirements are installed into an isolated environment.
    require(runtime['dependency_policy'] == 'OBSERVE_PREINSTALLED_AND_BIND' and runtime['expected_versions'] ==
            {'torch': '2.9.1+cu130', 'numpy': '2.5.3', 'transformers': '4.57.6'}, 'SEALED_RUNTIME_BLOCK_CHANGED')
    setup = CONFIG['setup_cutoff_unix']
    requirements = SOURCE / 'contracts' / 'requirements.small-linux.txt'
    require(sha_file(requirements, setup)['sha256'] == REQUIREMENTS_SHA ==
            CONTRACT['source']['members']['contracts/requirements.small-linux.txt']['sha256'],
            'ACCEPTED_REQUIREMENTS_FILE_CHANGED')
    pins = {}
    for line in requirements.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            name, separator, version = line.partition('==')
            require(separator == '==' and re.fullmatch(r'[a-z0-9-]+', name) is not None and
                    re.fullmatch(r'[0-9.]+', version) is not None and name not in pins, 'REQUIREMENT_PIN_SHAPE')
            pins[name] = version
    require(set(pins) == {'numpy', 'scipy', 'scikit-learn', 'joblib', 'threadpoolctl', 'transformers',
                          'tokenizers', 'safetensors', 'huggingface-hub'} and pins['transformers'] == '4.57.6',
            'TRANSFORMERS_HARD_GATE_REQUIRED')
    OVERLAY.mkdir()
    for name in ('home', 'tmp'):
        (OVERLAY / name).mkdir()
    env = {k: os.environ[k] for k in ('PATH', 'LANG', 'LC_ALL', 'LD_LIBRARY_PATH') if k in os.environ}
    env.update({'HOME': str(OVERLAY / 'home'), 'TMPDIR': str(OVERLAY / 'tmp'), 'PYTHONNOUSERSITE': '1',
        'PIP_DISABLE_PIP_VERSION_CHECK': '1', 'PIP_NO_INPUT': '1'})
    run_stage('overlay_venv', ['/opt/pytorch/bin/python', '-m', 'venv', '--system-site-packages', str(VENV)],
              120, setup, env)
    run_stage('overlay_install', [str(VENV_PYTHON), '-m', 'pip', 'install', '--only-binary=:all:',
        '--no-cache-dir', '--index-url', 'https://pypi.org/simple', '--report', str(CONTROL / 'pip-report.json'),
        '-r', str(requirements)], 600, setup, env)
    run_stage('overlay_freeze', [str(VENV_PYTHON), '-m', 'pip', 'freeze', '--all'], 60, setup, env)
    probe = ('import importlib.metadata as m,importlib.util as u,json,sys\n'
             'n=json.loads(sys.argv[1]);o={"python":sys.version,"packages":{}}\n'
             'for k,v in n.items():\n'
             ' s=u.find_spec(v)\n'
             ' try:w=m.version(k)\n'
             ' except m.PackageNotFoundError:w=None\n'
             ' o["packages"][k]={"version":w,"origin":None if s is None else s.origin}\n'
             'print(json.dumps(o))\n')
    modules = {name: {'scikit-learn': 'sklearn', 'huggingface-hub': 'huggingface_hub'}.get(name, name)
               for name in sorted(set(pins) | {'torch'})}
    run_stage('overlay_observe_literal', [str(VENV_PYTHON), '-c', probe, json.dumps(modules)], 60, setup, env)
    seen = json.loads((CONTROL / 'overlay_observe_literal.stdout.txt').read_text(encoding='utf-8'))
    bridge = seen['packages']['torch']['origin'] is None
    if bridge:
        # /opt/pytorch is itself a virtual environment, so its packages are not the
        # new environment's "system" packages. One path line exposes the image's
        # torch after the overlay's own packages; nothing is copied or installed.
        (VENV / 'lib' / 'python3.12' / 'site-packages' / '_image_pytorch_bridge.pth').write_text(
            IMAGE_SITE + '\n', encoding='ascii')
        run_stage('overlay_observe_bridged', [str(VENV_PYTHON), '-c', probe, json.dumps(modules)], 60, setup, env)
        seen = json.loads((CONTROL / 'overlay_observe_bridged.stdout.txt').read_text(encoding='utf-8'))
    require(seen['python'] == sys.version, 'OVERLAY_INTERPRETER_CHANGED')
    observations = seen['packages']
    for name, row in sorted(observations.items()):
        expected = '2.9.1+cu130' if name == 'torch' else pins[name]
        require(row['version'] == expected and row['origin'] is not None,
                'DEPENDENCY_MISSING_OR_VERSION_CHANGED:' + name)
        origin = Path(row['origin']).resolve()
        home = Path('/opt/pytorch').resolve() if name == 'torch' else VENV.resolve()
        require(origin.is_relative_to(home), 'DEPENDENCY_ORIGIN_UNEXPECTED:' + name)
    OBSERVED_DEPENDENCIES = {name: row['version'] for name, row in observations.items()}
    write_json(CONTROL / 'RUNTIME_PREFLIGHT.json', {'status': 'METADATA_AND_CGROUP_VERIFIED',
        'python': sys.version, 'executable': sys.executable, 'stage_python': str(VENV_PYTHON),
        'dependencies': observations, 'pins_from_accepted_requirements_sha256': REQUIREMENTS_SHA,
        'image_bridge_path_file_written': bridge,
        'cgroup_path': unified[0], 'cgroup_values': actual, 'cpu_affinity': sorted(os.sched_getaffinity(0)),
        'no_dependencies_installed': False, 'overlay_installed_from_official_index_binary_only': True,
        'runtime_amendment': 'C1_ISOLATED_OVERLAY_PER_ACCEPTED_SOURCE_REQUIREMENTS',
        'model_modules_not_imported_by_operator': True})


def child_environment():
    # No proxy, credential, or signed-URL environment inheritance into project children.
    env = {k: os.environ[k] for k in ('PATH', 'LANG', 'LC_ALL', 'LD_LIBRARY_PATH') if k in os.environ}
    home = WORK / 'home'
    temp = WORK / 'temp'
    home.mkdir(exist_ok=True)
    temp.mkdir(exist_ok=True)
    env.update({'HOME': str(home), 'TMPDIR': str(temp), 'TEMP': str(temp), 'TMP': str(temp),
        'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONHASHSEED': '0',
        'PYTHONPATH': str(SOURCE / 'job'),
        'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'HF_DATASETS_OFFLINE': '1',
        'HF_HUB_DISABLE_TELEMETRY': '1', 'HF_HOME': str(WORK / 'hf-home'),
        'TOKENIZERS_PARALLELISM': 'false', 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1',
        'OPENBLAS_NUM_THREADS': '1', 'NUMEXPR_NUM_THREADS': '1',
        'CUDA_VISIBLE_DEVICES': '0', 'CUBLAS_WORKSPACE_CONFIG': ':4096:8'})
    return env


def cleanup_children(deadline):
    if CGROUP is None:
        return
    # CLI descendants can create new sessions. The dedicated cgroup, rather than
    # only the CLI process group, is the authoritative local membership boundary.
    for sig, seconds in ((signal.SIGTERM, 2), (signal.SIGKILL, 5)):
        until = min(deadline, time.time() + seconds)
        while remaining(until) > 0:
            pids = cgroup_pids() - {os.getpid()}
            if not pids:
                return
            for pid in pids:
                try:
                    os.kill(pid, sig)
                except ProcessLookupError:
                    pass
            time.sleep(min(0.1, max(0.0, remaining(until))))
    require(cgroup_pids() == {os.getpid()}, 'CHILD_PROCESS_CUSTODY_NOT_CLOSED')


def run_stage(name, args, seconds, deadline, env=None):
    global CURRENT_STAGE
    require(name not in STAGES, 'STAGE_RETRY_REFUSED:' + name)
    require(cgroup_pids() == {os.getpid()}, 'PRE_STAGE_PROCESS_LEAK')
    stop = min(deadline, time.time() + seconds)
    check_time(stop, 'STAGE_NO_TIME_REMAINS')
    CURRENT_STAGE = name
    stage = {'status': 'STARTED', 'started_unix': time.time(), 'deadline_unix': stop,
             'command': args, 'attempt': 1}
    STAGES[name] = stage
    write_json(CONTROL / (name + '.json'), stage)
    progress()
    process = None
    try:
        with (CONTROL / (name + '.stdout.txt')).open('xb') as out, \
                (CONTROL / (name + '.stderr.txt')).open('xb') as err:
            process = subprocess.Popen(args, cwd=WORK, env=child_environment() if env is None else env,
                stdin=subprocess.DEVNULL,
                stdout=out, stderr=err, start_new_session=True)
            last_scan = 0.0
            while process.poll() is None:
                check_time(stop, 'STAGE_TIMEOUT:' + name)
                if time.monotonic() - last_scan >= 5:
                    tree_files(WORK, min(stop, time.time() + 5), cap_bytes=MAX_WORK)
                    last_scan = time.monotonic()
                progress()
                time.sleep(min(0.25, max(0.0, remaining(stop))))
            stage['exit_code'] = process.returncode
            require(process.returncode == 0, 'STAGE_NONZERO_EXIT:' + name)
            stage['status'] = 'EXIT_ZERO_REQUIRES_AUTHORED_RESULT'
    except BaseException as exc:
        stage['status'] = 'FAILED_OR_STOPPED_NO_RETRY'
        stage['failure'] = safe_error(exc)
        raise
    finally:
        try:
            cleanup_children(min(CONFIG['force_cutoff_unix'] - 180, time.time() + 10))
        finally:
            if process is not None:
                try:
                    stage['exit_code'] = process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    stage['unreaped_process'] = True
            stage['ended_unix'] = time.time()
            write_json(CONTROL / (name + '.json'), stage)
    return stage


def gpu_preflight():
    run_stage('gpu_preflight', ['/usr/bin/nvidia-smi', '--query-gpu=name,memory.total,driver_version',
              '--format=csv,noheader,nounits'], 20, CONFIG['setup_cutoff_unix'])
    text = (CONTROL / 'gpu_preflight.stdout.txt').read_text(encoding='utf-8').strip()
    rows = text.splitlines()
    require(len(rows) == 1, 'EXACTLY_ONE_GPU_REQUIRED')
    fields = [value.strip() for value in rows[0].split(',')]
    require(len(fields) == 3 and fields[0] in ('NVIDIA A10G', 'A10G') and fields[1].isdigit()
            and int(fields[1]) >= 22000, 'A10G_MEMORY_REQUIREMENT')
    write_json(CONTROL / 'GPU_PREFLIGHT.json', {'name': fields[0], 'memory_total_MiB': int(fields[1]),
        'driver_version': fields[2], 'status': 'ONE_A10G_OBSERVED', 'runtime_capacity_proven': False})


def external_authority():
    """Hash the transported authority records; this function never supplies acceptance."""
    external = CONTRACT['external_authority']
    verify_tree(WORK / 'external-authority', external['files'], CONFIG['setup_cutoff_unix'],
                CONTROL / 'EXTERNAL_AUTHORITY_PRE.json')
    name = external['owner_record']
    write_json(CONTROL / 'EXTERNAL_AUTHORITY_GATE.json', {
        'status': 'OWNER_APPROVAL_RECORD_PRESENT_AND_HASHED_NOT_INTERPRETED', 'owner_record': name,
        'owner_record_sha256': external['files'][name]['sha256'],
        'scientific_acceptance_created_by_guest': False})


def runner(name, places):
    return [str(VENV_PYTHON), '-B', str(SOURCE / 'job' / 'runner_b1.py')] + [
        str(places[part[1:-1]]) if part.startswith('{') else part for part in RUNNER[name]]


def execute_science():
    """Start the sealed runner's five commands in order. The guest scores nothing."""
    global SETUP_COMPLETE, CURRENT_STAGE
    setup = CONFIG['setup_cutoff_unix']
    work = CONFIG['work_cutoff_unix']
    score_end = CONFIG['launch_unix'] + CLOCK['score_cutoff_unix']
    bound = CONTRACT['precheck']
    places = {'PACKAGE': SOURCE, 'MODEL': CACHE / CONTRACT['model_cache']['snapshots']['B'], 'OUTPUT': OUT,
              'PROMPT_LIST': bound['prompt_list_sha256'], 'PADDING_PLAN': bound['padding_plan_sha256'],
              'WORK_CUTOFF': int(work), 'CONSTANTS': SOURCE / 'PLAN_CONSTANTS.json',
              'PROMPTS': SOURCE / 'prompts', 'MODEL_PRE': CONTROL / 'MODEL_PRE.json',
              'MODEL_AFTER': CONTROL / 'MODEL_AFTER_CALLS.json'}
    # Gate 0: no model call. The runner makes its one output folder itself, as it did in
    # the pre-check job. A stop is written into selftest.json, not into the exit code.
    run_stage('selftest', runner('selftest', places), LIMITS['selftest_seconds'], setup)
    report = load_json(OUT / 'selftest.json', 4 * 1024 * 1024)
    require(type(report) is dict, 'SELFTEST_JSON_NOT_AN_OBJECT')
    # Runner file rules, checked on what the self-test wrote, before any model call:
    # nothing new under the sealed folders, and plain file names in the output folder.
    for root, declared in ((SOURCE, CONTRACT['source']['members']),
                           (WORK / 'external-authority', CONTRACT['external_authority']['files'])):
        require(set(tree_files(root, setup)) == set(declared), 'RUNNER_WROTE_UNDER_SEALED_FOLDER')
    require(all(re.fullmatch(r'[A-Za-z0-9._/-]+', name) is not None for name in tree_files(OUT, setup)),
            'RUNNER_FILE_NAME_RULE')
    # Setup flag: after the self-test and before the first model call. The
    # controller ends the host at the setup cutoff unless it has seen this flag.
    # After a self-test stop the flag is set too, so that the stop evidence can
    # still be archived and uploaded; the stage text then says so.
    check_time(setup, 'SETUP_CUTOFF_BEFORE_MODEL_CALLS')
    SETUP_COMPLETE = True
    CURRENT_STAGE = ('SETUP_VERIFIED_BEFORE_MODEL_CALLS' if report.get('status') == 'SELFTEST_PASS'
                     else 'SELFTEST_STOP_NO_MODEL_CALLS')
    progress(force=True)
    # The package's commands decide for themselves whether they act: run-practice
    # only after SELFTEST_PASS, run-final only after GATE.json says go. A gate stop
    # is a complete end of the job, not a failure. A crashed or timed-out command
    # ends the model stages at once; the model hash and the score stage still run.
    # Each model stage gets the work cutoff as its deadline, and so does the runner.
    failed = False
    try:
        run_stage('run_practice', runner('run_practice', places), LIMITS['model_stage_seconds'], work)
        run_stage('gate', runner('gate', places), LIMITS['gate_seconds'], work)
        run_stage('run_final', runner('run_final', places), LIMITS['model_stage_seconds'], work)
    except BaseException as exc:
        FAULTS.append(safe_error(exc))
        failed = True
    # After the last model call and before scoring: hash every model file again.
    # A failure here must not skip scoring; the score command then finds no receipt.
    CURRENT_STAGE = 'MODEL_HASH_AFTER_CALLS'
    try:
        verify_tree(CACHE, CONTRACT['model_cache']['files'], min(score_end, time.time() + 300),
                    CONTROL / 'MODEL_AFTER_CALLS.json')
    except BaseException as exc:
        row = safe_error(exc)
        row['custody_failure'] = True
        FAULTS.append(row)
    limit = report.get('score_time_limit_seconds')
    if type(limit) is not int or not LIMITS['score_seconds_min'] <= limit <= LIMITS['score_seconds_max']:
        limit = LIMITS['score_seconds_max']
    # The score stage must end by minute 140. Its time limit is the one the self-test measured.
    run_stage('score', runner('score', places), limit, score_end)
    require(not failed, 'MODEL_STAGE_FAILED_SCORE_STILL_RAN')


def read_result():
    """Small result reader: one code, the file hash, the file size. Never copies tables."""
    path = OUT / 'RESULT.json'
    if not path.exists():
        return {'status': 'NO_RESULT_FILE', 'result_sha256': None, 'result_bytes': None}
    measured = sha_file(path, time.time() + 60)
    code = 'RESULT_UNREADABLE'
    try:
        text = load_json(path, 16 * 1024 * 1024)['outcome_code']
        if type(text) is str and re.fullmatch(r'[A-Z_]{1,80}', text) is not None:
            code = text
    except Exception:
        pass
    return {'status': code, 'result_sha256': measured['sha256'], 'result_bytes': measured['bytes']}


def post_custody():
    global SOURCE_POST_VERIFIED, MODEL_POST_VERIFIED, CURRENT_STAGE
    CURRENT_STAGE = 'POST_CUSTODY'
    deadline = min(CONFIG['force_cutoff_unix'] - 1800, time.time() + 900)
    # Rehash immutable input bytes even after failure; no substitution of hashes
    # from the preflight receipt for actual post-work observations.
    for root, declared, filename, role in (
        (SOURCE, CONTRACT.get('source', {}).get('members'), 'SOURCE_POST.json', 'source'),
        (CACHE, CONTRACT.get('model_cache', {}).get('files'), 'MODEL_POST.json', 'model'),
        (WORK / 'external-authority', CONTRACT.get('external_authority', {}).get('files'),
            'EXTERNAL_AUTHORITY_POST.json', 'authority')):
        if declared and root.exists():
            try:
                verify_tree(root, declared, deadline, CONTROL / filename)
                if role == 'source':
                    SOURCE_POST_VERIFIED = True
                if role == 'model':
                    MODEL_POST_VERIFIED = True
            except BaseException as exc:
                failure = safe_error(exc)
                failure['custody_failure'] = True
                FAULTS.append(failure)
    write_json(CONTROL / 'CUSTODY_STATUS.json', {
        'source_pre_verified': SOURCE_PRE_VERIFIED, 'source_post_verified': SOURCE_POST_VERIFIED,
        'model_pre_verified': MODEL_PRE_VERIFIED, 'model_post_verified': MODEL_POST_VERIFIED,
        'immutable_model_payload_excluded_from_export': True,
        'excluded_model_bytes': MODEL_BYTES,
        'model_hash_receipts_required_for_custody': True})


def archive_files(archive_path, selected, complete, deadline):
    inventory = []
    with zipfile.ZipFile(archive_path, 'x', compression=zipfile.ZIP_STORED,
                         allowZip64=True) as archive:
        for name, path in sorted(selected.items()):
            check_time(deadline, 'ARCHIVE_DEADLINE')
            safe_relative(name)
            before = ordinary(path)
            require(stat.S_ISREG(before.st_mode), 'ARCHIVE_INPUT_NOT_REGULAR')
            value = hashlib.sha256()
            count = 0
            info = zipfile.ZipInfo(name)
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = (stat.S_IFREG | 0o600) << 16
            with path.open('rb') as incoming, archive.open(info, 'w', force_zip64=True) as outgoing:
                while True:
                    check_time(deadline, 'ARCHIVE_WRITE_DEADLINE')
                    chunk = incoming.read(CHUNK)
                    if not chunk:
                        break
                    count += len(chunk)
                    value.update(chunk)
                    outgoing.write(chunk)
                    require(archive.fp.tell() <= MAX_ARCHIVE - 16 * 1024 * 1024, 'ARCHIVE_HARD_SIZE_CAP')
            after = ordinary(path)
            require(count == before.st_size and (before.st_size, before.st_mtime_ns, before.st_ino) ==
                    (after.st_size, after.st_mtime_ns, after.st_ino), 'ARCHIVE_SOURCE_CHANGED:' + name)
            inventory.append({'path': name, 'bytes': count, 'sha256': value.hexdigest()})
            progress()
        record = {'schema': 'cas-optionb-b1-required-evidence-inventory/v1',
            'complete_required_evidence': complete, 'members': inventory,
            'inventory_excludes_itself': True, 'immutable_model_payload_excluded': True,
            'excluded_model_bytes': MODEL_BYTES,
            'model_pre_receipt': 'controller/MODEL_PRE.json',
            'model_after_calls_receipt': 'controller/MODEL_AFTER_CALLS.json',
            'model_post_receipt': 'controller/MODEL_POST.json'}
        encoded = canonical(record)
        require(len(encoded) <= 16 * 1024 * 1024, 'INVENTORY_JSON_SIZE_CAP')
        archive.writestr('controller/REQUIRED_EVIDENCE_INVENTORY.json', encoded)
    require(ordinary(archive_path).st_size <= MAX_ARCHIVE, 'ARCHIVE_FINAL_SIZE_CAP')
    # Reopen every member and independently stream its bytes/CRC/hash. The
    # controller repeats this after retrieval; no bulk member is omitted here.
    declared = {row['path']: {'bytes': row['bytes'], 'sha256': row['sha256']} for row in inventory}
    declared['controller/REQUIRED_EVIDENCE_INVENTORY.json'] = {
        'bytes': len(encoded), 'sha256': hashlib.sha256(encoded).hexdigest()}
    with zipfile.ZipFile(archive_path, 'r') as archive:
        require(set(archive.namelist()) == set(declared) and len(archive.namelist()) == len(declared),
                'ARCHIVE_REOPEN_MEMBERSHIP_MISMATCH')
        for name, expected in declared.items():
            value = hashlib.sha256()
            count = 0
            with archive.open(name) as handle:
                while True:
                    check_time(deadline, 'ARCHIVE_REOPEN_DEADLINE')
                    chunk = handle.read(CHUNK)
                    if not chunk:
                        break
                    value.update(chunk)
                    count += len(chunk)
            require({'bytes': count, 'sha256': value.hexdigest()} == expected, 'ARCHIVE_REOPEN_HASH_MISMATCH')
            progress()
    return sha_file(archive_path, deadline), len(inventory) + 1


def build_archive(outcome):
    deadline = CONFIG['force_cutoff_unix'] - 1200
    check_time(deadline, 'NO_ARCHIVE_RESERVE_REMAINS')
    complete = (SOURCE_PRE_VERIFIED and SOURCE_POST_VERIFIED and MODEL_PRE_VERIFIED and
                MODEL_POST_VERIFIED and not any(row.get('custody_failure') for row in FAULTS))
    # Workload refusal/failure does not by itself mean the retained files are
    # incomplete. A missing result file after the model stages were entered is explicit.
    if ('run_practice' in STAGES or 'run_final' in STAGES) and not outcome.get('result_sha256'):
        complete = False
    result = {'job': CONFIG['job'], 'instance': CONFIG['instance'],
        'payload_manifest_sha256': CONFIG['payload_manifest_sha256'],
        'scientific_outcome': outcome, 'stages': STAGES, 'faults': FAULTS,
        'complete_required_evidence': complete,
        'source_pre_verified': SOURCE_PRE_VERIFIED, 'source_post_verified': SOURCE_POST_VERIFIED,
        'model_pre_verified': MODEL_PRE_VERIFIED, 'model_post_verified': MODEL_POST_VERIFIED,
        'guest_scored_nothing': True, 'no_automatic_retry': True,
        'delivery_status': 'ARCHIVE_PREPARED_BEFORE_MULTIPART_UPLOAD',
        'scientific_output_limit_bytes': MAX_WORK, 'archive_limit_bytes': MAX_ARCHIVE}
    write_json(CONTROL / 'GUEST_RESULT.json', result)
    if not complete:
        write_json(CONTROL / 'RETRIEVAL_INCOMPLETE.json', {
            'complete_required_evidence': False,
            'reason': 'IMMUTABLE_CUSTODY_OR_REQUIRED_SCIENTIFIC_TERMINAL_NOT_ESTABLISHED',
            'faults': FAULTS, 'preserved_workload_outcome': outcome.get('status')})
    sizes = tree_files(WORK, deadline, cap_bytes=MAX_WORK)
    write_json(CONTROL / 'WORK_FILE_MEMBERSHIP.json', {'members': sizes,
        'record_excludes_itself': True, 'model_inputs_outside_export_tree': True})
    sizes = tree_files(WORK, deadline, cap_bytes=MAX_WORK)
    selected = {name: WORK / name for name in sizes}
    path = BASE / 'scientific-deliverable.zip'
    measured, count = archive_files(path, selected, complete, deadline)
    return path, measured, count, complete


def fallback_archive(exc, outcome):
    # Available only before any multipart PUT attempt. It intentionally exports
    # a bounded controller diagnostic instead of pretending to retain bulk data.
    require(not UPLOAD_ATTEMPTED, 'NO_FALLBACK_AFTER_MULTIPART_ATTEMPT')
    deadline = min(CONFIG['force_cutoff_unix'] - 600, time.time() + 180)
    check_time(deadline, 'NO_DIAGNOSTIC_ARCHIVE_TIME')
    failure = safe_error(exc)
    failure['custody_failure'] = True
    FAULTS.append(failure)
    missing = {'scope': 'ALL_NON_CONTROLLER_WORK_MEMBERS', 'reason': 'DIAGNOSTIC_EXPORT_ONLY'}
    try:
        sizes = tree_files(WORK, min(deadline, time.time() + 15))
        missing['members_not_exported'] = {name: size for name, size in sizes.items()
                                         if not name.startswith('controller/')}
    except BaseException as inventory_exc:
        missing['membership_inventory_incomplete'] = safe_error(inventory_exc)
    write_json(CONTROL / 'RETRIEVAL_INCOMPLETE.json', {
        'complete_required_evidence': False, 'reason': 'FALLBACK_CONTROLLER_ONLY_DIAGNOSTIC',
        'failure': failure, 'missing_files': missing})
    write_json(CONTROL / 'GUEST_RESULT.json', {'job': CONFIG['job'], 'instance': CONFIG['instance'],
        'payload_manifest_sha256': CONFIG['payload_manifest_sha256'], 'complete_required_evidence': False,
        'scientific_outcome': outcome, 'stages': STAGES, 'faults': FAULTS,
        'status': 'INCOMPLETE_CONTROLLER_ONLY_EXPORT', 'no_automatic_retry': True})
    sizes = tree_files(CONTROL, deadline, cap_bytes=16 * 1024 * 1024)
    selected = {'controller/' + name: CONTROL / name for name in sizes}
    path = BASE / 'diagnostic-deliverable.zip'
    measured, count = archive_files(path, selected, False, deadline)
    return path, measured, count, False


def upload_parts(path, measured):
    global UPLOAD_ATTEMPTED, CURRENT_STAGE
    CURRENT_STAGE = 'MULTIPART_UPLOAD'
    deadline = CONFIG['force_cutoff_unix'] - 600
    parts = (measured['bytes'] + PART_SIZE - 1) // PART_SIZE
    require(1 <= parts <= MAX_PARTS, 'MULTIPART_COUNT_CAP')
    whole = hashlib.sha256()
    with path.open('rb') as handle:
        for number in range(1, parts + 1):
            check_time(deadline, 'MULTIPART_UPLOAD_DEADLINE')
            size = min(PART_SIZE, measured['bytes'] - (number - 1) * PART_SIZE)
            parsed = transport_url(CONFIG['multipart']['part_urls'][str(number)], ARCHIVE_KEY, number)
            # Durable marker precedes the request: any ambiguous attempt stops
            # without resending this or a subsequent alternative archive.
            write_json(STATE / ('part-' + str(number) + '-attempt.json'),
                {'part_number': number, 'bytes': size, 'attempted_unix': time.time()}, exclusive=True)
            UPLOAD_ATTEMPTED = True
            conn = connection(parsed, deadline)
            value = hashlib.sha256()
            sent = 0
            try:
                conn.putrequest('PUT', request_target(parsed))
                conn.putheader('Content-Length', str(size))
                conn.endheaders()
                while sent < size:
                    check_time(deadline, 'MULTIPART_BODY_DEADLINE')
                    chunk = handle.read(min(CHUNK, size - sent))
                    require(bool(chunk), 'ARCHIVE_TRUNCATED_DURING_UPLOAD')
                    value.update(chunk)
                    whole.update(chunk)
                    conn.send(chunk)
                    sent += len(chunk)
                response = conn.getresponse()
                require(200 <= response.status < 300, 'PART_PUT_HTTP_' + str(response.status))
                etag = response.getheader('ETag')
                require(type(etag) is str and 0 < len(etag) <= 64 and '\n' not in etag and '\r' not in etag,
                        'MULTIPART_ETAG_MISSING_OR_INVALID')
                response.read(4096)
                row = {'part_number': number, 'bytes': sent, 'sha256': value.hexdigest(), 'etag': etag}
                PART_RECORDS.append(row)
                write_json(STATE / ('part-' + str(number) + '-receipt.json'), row, exclusive=True)
            finally:
                conn.close()
            progress()
        require(handle.read(1) == b'' and whole.hexdigest() == measured['sha256'],
                'WHOLE_ARCHIVE_UPLOAD_HASH_MISMATCH')
    return {'parts': PART_RECORDS, 'part_size': PART_SIZE, 'part_count': parts,
            'upload_id': CONFIG['multipart']['upload_id'], 'whole_archive_sha256': whole.hexdigest()}


def terminal(value):
    # Exactly one terminal PUT, including after a partial multipart failure.
    write_json(STATE / 'terminal-attempt.json', {'attempted_unix': time.time()}, exclusive=True)
    write_json(STATE / 'transport-result.json', value, exclusive=True)
    put_small('transport-result.json', value, CONFIG['force_cutoff_unix'] - 570)
    write_json(STATE / 'TERMINAL_DELIVERED.json', {'time_unix': time.time(),
        'status': value['status'], 'controller_must_complete_or_abort_multipart': True}, exclusive=True)


def main():
    global CURRENT_STAGE, SOURCE_PRE_VERIFIED, MODEL_PRE_VERIFIED
    require(not WORK.exists() and not STATE.exists() and not PAYLOAD.exists() and not OVERLAY.exists(),
            'WORKSPACE_REUSE_REFUSED')
    WORK.mkdir()
    CONTROL.mkdir()
    STATE.mkdir()
    PAYLOAD.mkdir()
    # Invalid signed transport configuration cannot safely be used for fallback.
    validate_config()
    outcome = {'status': 'NOT_STARTED', 'result_sha256': None, 'result_bytes': None}
    archive_path = None
    measured = None
    count = 0
    complete = False
    try:
        CURRENT_STAGE = 'INSTANCE_AND_INPUT'
        imds_instance()
        path = download_input()
        extract_input(path)
        CURRENT_STAGE = 'CUSTODY_PREFLIGHT'
        verify_tree(SOURCE, CONTRACT['source']['members'], CONFIG['setup_cutoff_unix'], CONTROL / 'SOURCE_PRE.json')
        SOURCE_PRE_VERIFIED = True
        verify_tree(CACHE, CONTRACT['model_cache']['files'], CONFIG['setup_cutoff_unix'], CONTROL / 'MODEL_PRE.json')
        MODEL_PRE_VERIFIED = True
        require(sha_file(SOURCE / 'BUNDLE_MANIFEST.json', CONFIG['setup_cutoff_unix'])['sha256'] == SOURCE_SEAL,
                'SOURCE_MANIFEST_HASH_MISMATCH')
        external_authority()
        CURRENT_STAGE = 'RUNTIME_PREFLIGHT'
        runtime_preflight()
        gpu_preflight()
        execute_science()
    except BaseException as exc:
        FAULTS.append(safe_error(exc))
        write_json(CONTROL / 'WORKLOAD_FAILURE.json', {'faults': FAULTS, 'stages': STAGES,
            'status': 'STOPPED_NO_RETRY', 'scientific_pass': False})
    finally:
        try:
            cleanup_children(min(CONFIG['force_cutoff_unix'] - 180, time.time() + 10))
        except BaseException as exc:
            row = safe_error(exc)
            row['custody_failure'] = True
            FAULTS.append(row)
        try:
            outcome = read_result()
        except BaseException as exc:
            row = safe_error(exc)
            row['custody_failure'] = True
            FAULTS.append(row)
            outcome = {'status': 'RESULT_READER_FAILED', 'result_sha256': None, 'result_bytes': None}
        try:
            post_custody()
        except BaseException as exc:
            row = safe_error(exc)
            row['custody_failure'] = True
            FAULTS.append(row)
    try:
        CURRENT_STAGE = 'ARCHIVE_FULL_WORK'
        try:
            archive_path, measured, count, complete = build_archive(outcome)
        except BaseException as exc:
            archive_path, measured, count, complete = fallback_archive(exc, outcome)
        manifest = upload_parts(archive_path, measured)
        result = {'status': 'MULTIPART_PARTS_READY_NOT_COMPLETED', 'job': CONFIG['job'],
            'instance': CONFIG['instance'], 'output_key': CONFIG['output_key'],
            'payload_manifest_sha256': CONFIG['payload_manifest_sha256'],
            'output_bytes': measured['bytes'], 'output_sha256': measured['sha256'],
            'complete_required_evidence': complete, 'archive_members': count,
            'scientific_status': outcome.get('status'), 'multipart': manifest,
            'guest_completed_s3_object': False, 'controller_reopen_verification_required': True}
    except BaseException as exc:
        result = {'status': 'TRANSPORT_INCOMPLETE_CONTROLLER_MUST_ABORT', 'job': CONFIG['job'],
            'instance': CONFIG['instance'], 'output_key': CONFIG['output_key'],
            'payload_manifest_sha256': CONFIG['payload_manifest_sha256'],
            'output_bytes': None if measured is None else measured['bytes'],
            'output_sha256': None if measured is None else measured['sha256'],
            'complete_required_evidence': False, 'scientific_status': outcome.get('status'),
            'failure': safe_error(exc), 'multipart': {'upload_id': CONFIG['multipart']['upload_id'],
                'part_size': PART_SIZE, 'parts': PART_RECORDS},
            'output_put_attempted': UPLOAD_ATTEMPTED, 'no_retry_after_ambiguous_part_put': True}
    CURRENT_STAGE = 'TERMINAL_TRANSPORT'
    try:
        terminal(result)
    except BaseException as exc:
        write_json(STATE / 'TERMINAL_DELIVERY_FAILED.json', {'failure': safe_error(exc),
            'controller_must_abort_if_no_verified_terminal': True})
        return 2
    return 0 if result['status'] == 'MULTIPART_PARTS_READY_NOT_COMPLETED' else 2


if __name__ == '__main__':
    require(len(sys.argv) == 1, 'UNRECOGNIZED_WORKER_COMMAND')
    sys.exit(main())
