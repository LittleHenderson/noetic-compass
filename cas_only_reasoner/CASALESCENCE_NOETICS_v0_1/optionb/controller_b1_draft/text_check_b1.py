"""Build-time text check for Option B GPU job b1. Reads files only. Runs no project code.

It is light enough for the laptop: standard library, a few MB of memory, a few seconds.
It opens zip files read-only. It parses worker_v02.py, aws_control.py, watchdog.py and
controller_common.py to read their plain constants. It never runs any of them.

The builder must pass this check before the launch records are written. One FAIL means: do not launch.

The five checks the design asks for:
  A. The four clock numbers agree in the controller (aws_control.py, controller_common.py),
     the watchdog (watchdog.py) and the guest (worker_v02.py), and with PLAN_CONSTANTS.json.
  B. source.zip: unpacked bytes and file count are under the guest's caps.
  C. The requirements file and BUNDLE_MANIFEST.json are in source.zip with the pinned hashes.
  D. The model file count and bytes equal the guest's numbers.
  E. The guest is within both size limits: raw bytes, and bytes after gzip then base64
     (packed exactly the way aws_control.py packs it).

More checks of the same kind are added (X1 to X8): the guest parses and keeps its sealed
lines; contract against guest; limits against the plan; input.zip members; package against
the seal; the pre-check receipt; other controller numbers; and every word of the runner's
command lines must occur in job/runner_b1.py of the package.

Use:
  python -B text_check_b1.py --dir <controller folder>
Add --hash-models to hash the model files inside input.zip as well (reads about 1 GB).
Add --write to save the result as TEXT_CHECK_B1.json in the folder.

Status: built by Claude, checked by a separate reviewer in one review round.
"""
import argparse
import ast
import base64
import gzip
import hashlib
import json
import os
import re
import sys
import zipfile
from pathlib import Path

STUDY_ROOT = 'C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/CASALESCENCE_NOETICS_v0_1'
# The old guest's own sizes are the limits (REAL: 73,986 raw; 28,420 packed, SSM_SOURCE_BOUND.json).
GUEST_RAW_LIMIT = 73986
GUEST_PACKED_LIMIT = 28420
CONTROLLER_WORKER_CAP = 131072
SSM_LIMIT = 60000
SSM_OVERHEAD = 16384
REQUIREMENTS_NAME = 'contracts/requirements.small-linux.txt'
REQUIREMENTS_SHA = '6d9ee033baf3acbcecfbf8feb735a807025c141cac8e6060e480154c2c1c15b7'
MANIFEST_NAME = 'BUNDLE_MANIFEST.json'
SEAL_NAME = 'SEAL_OPTIONB.jsonl'
# Review round 1: the lines after which a package may be cut, the tool-repair line, and the frozen word program.
PROGRAM_LINES = ('6_PROGRAMS', '6R_PROGRAMS_REPAIRED')
TOOL_REPAIR = 'TR_TOOLS_REPAIRED'
# Amendment A5: the line that closes the window of a tool repair.
FINAL_LINE = '3C_FINAL_QUESTIONS_AND_KEYS'
VERDICT_NAME = 'tools/verdict.py'
RUNNER_NAME = 'job/runner_b1.py'
CONTRACT_SCHEMA = 'cas-optionb-b1-guest-contract/v1'
SEALED_RUNTIME = {'executable': '/opt/pytorch/bin/python', 'python_version': '3.12.3',
                  'dependency_policy': 'OBSERVE_PREINSTALLED_AND_BIND',
                  'expected_versions': {'torch': '2.9.1+cu130', 'numpy': '2.5.3', 'transformers': '4.57.6'}}
PLACEHOLDERS = {name: hashlib.sha256(('UNSTAMPED:' + name).encode('ascii')).hexdigest()
                for name in ('SOURCE_ZIP_SHA', 'SOURCE_SEAL')}
CLOCK_NAMES = ('setup_cutoff_unix', 'work_cutoff_unix', 'force_cutoff_unix', 'termination_unix')
RUNNER_COMMANDS = {'selftest': 'selftest', 'run_practice': 'run-practice', 'gate': 'gate',
                   'run_final': 'run-final', 'score': 'score'}
CHUNK = 1024 * 1024


class Fail(Exception):
    pass


def fail_unless(condition, message):
    if not condition:
        raise Fail(message)


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha_path(path):
    value = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(CHUNK), b''):
            value.update(chunk)
    return value.hexdigest()


def packed_size(data):
    """Exactly how aws_control.py packs the guest: base64 of gzip with mtime 0."""
    return len(base64.b64encode(gzip.compress(data, mtime=0)))


def safe_name(name):
    return (isinstance(name, str) and name != '' and '\\' not in name and '\x00' not in name
            and ':' not in name and not name.startswith('/')
            and all(part not in ('', '.', '..') for part in name.split('/')))


def literals(text):
    """Plain module-level constants of a Python text, read by parsing. Nothing is run.

    Handles NAME = literal and A, B = literal, literal.
    """
    found = {}
    for node in ast.parse(text).body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        try:
            if isinstance(target, ast.Name):
                found[target.id] = ast.literal_eval(node.value)
            elif (isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple)
                  and len(target.elts) == len(node.value.elts)
                  and all(isinstance(item, ast.Name) for item in target.elts)):
                for item, value in zip(target.elts, node.value.elts):
                    found[item.id] = ast.literal_eval(value)
        except (ValueError, SyntaxError, TypeError):
            pass
    return found


def resolve(token, names, where):
    """A number written as digits, or as a plain constant of that file."""
    if token.isdigit():
        return int(token)
    fail_unless(type(names.get(token)) is int, '%s: cannot read the number behind %r' % (where, token))
    return names[token]


class Files:
    """Loads each file once. A missing file is a FAIL of the check that needs it."""

    def __init__(self, folder, controller, root):
        self.folder = Path(folder)
        self.controller = Path(controller)
        self.root = Path(root)
        self.cache = {}

    def path(self, name, base=None):
        target = (base or self.folder) / name
        fail_unless(target.is_file(), 'file not found: ' + str(target))
        return target

    def keep(self, key, make):
        if key not in self.cache:
            self.cache[key] = make()
        return self.cache[key]

    def guest_bytes(self):
        return self.keep('guest_bytes', lambda: self.path('worker_v02.py').read_bytes())

    def guest(self):
        return self.keep('guest', lambda: literals(self.guest_bytes().decode('utf-8')))

    def plan(self):
        return self.keep('plan', lambda: json.loads(
            self.path('PLAN_CONSTANTS.json', self.root / 'optionb').read_bytes().decode('utf-8-sig')))

    def contract_bytes(self):
        return self.keep('contract_bytes', lambda: self.path('CONTRACT.json').read_bytes())

    def contract(self):
        return self.keep('contract', lambda: json.loads(self.contract_bytes().decode('utf-8-sig')))

    def source(self):
        def make():
            path = self.path('source.zip')
            with zipfile.ZipFile(path, 'r') as archive:
                infos = archive.infolist()
                data = {info.filename: archive.read(info) for info in infos}
            members = {name: {'bytes': len(blob), 'sha256': sha_bytes(blob)} for name, blob in data.items()}
            return {'sha256': sha_path(path), 'bytes': path.stat().st_size, 'members': members,
                    'names': [info.filename for info in infos], 'data': data,
                    'kinds': sorted({info.compress_type for info in infos})}
        return self.keep('source', make)

    def controller_text(self, name):
        return self.keep('text:' + name, lambda: self.path(name, self.controller).read_bytes().decode('utf-8'))

    def controller_names(self, name):
        return self.keep('names:' + name, lambda: literals(self.controller_text(name)))


def check_guest_parses(files):
    data = files.guest_bytes()
    fail_unless(b'\r' not in data, 'the guest holds CR characters; it must use LF line ends')
    fail_unless(data.endswith(b'\n'), 'the guest does not end with a line feed')
    text = data.decode('utf-8')
    guest = files.guest()
    for name in ('CLOCK', 'LIMITS', 'RUNNER', 'MODEL_FILES', 'MODEL_BYTES', 'MODEL_REVISION', 'SOURCE_ZIP_SHA',
                 'SOURCE_ZIP_BYTES', 'SOURCE_MEMBERS', 'SOURCE_SEAL', 'SOURCE_UNPACKED_CAP', 'SOURCE_FILE_CAP',
                 'REQUIREMENTS_SHA', 'MAX_INPUT', 'MAX_PARTS', 'BUCKET', 'PREFIX'):
        fail_unless(name in guest, 'guest constant not found as a plain literal: ' + name)
    fail_unless("'/system.slice/helm-op11-work.service'" in text, 'the service name was changed in the guest')
    fail_unless("{'torch': '2.9.1+cu130', 'numpy': '2.5.3', 'transformers': '4.57.6'}" in text
                and "runtime['dependency_policy'] == 'OBSERVE_PREINSTALLED_AND_BIND'" in text,
                'the sealed runtime block check was changed in the guest')
    return 'parses as Python; LF line ends; service name and runtime block check as sealed'


def check_guest_sizes(files):
    data = files.guest_bytes()
    raw = len(data)
    packed = packed_size(data)
    fail_unless(raw <= GUEST_RAW_LIMIT, 'raw %d bytes is over the limit %d' % (raw, GUEST_RAW_LIMIT))
    fail_unless(packed <= GUEST_PACKED_LIMIT, 'packed %d bytes is over the limit %d' % (packed, GUEST_PACKED_LIMIT))
    fail_unless(raw <= CONTROLLER_WORKER_CAP, 'raw size is over the controller cap')
    room = SSM_LIMIT - SSM_OVERHEAD - packed
    return ('raw %d of %d bytes; packed (gzip then base64) %d of %d bytes; room left for the packed '
            'signed links in the launch command: %d bytes; sha256 %s'
            % (raw, GUEST_RAW_LIMIT, packed, GUEST_PACKED_LIMIT, room, sha_bytes(data)))


def check_clock_plan(files):
    clock = files.guest()['CLOCK']
    plan = files.plan()['aws']['gpu_job']['clock_seconds']
    want = {'setup_cutoff_unix': plan['setup_must_end'], 'work_cutoff_unix': plan['work_cutoff'],
            'score_cutoff_unix': plan['score_must_end'], 'force_cutoff_unix': plan['forced_shutdown'],
            'termination_unix': plan['hard_limit']}
    fail_unless(clock == want, 'guest clock %r differs from the plan %r' % (clock, want))
    # The guest needs 30 minutes between the end of scoring and the forced shutdown.
    fail_unless(clock['setup_cutoff_unix'] < clock['work_cutoff_unix'] < clock['score_cutoff_unix']
                <= clock['force_cutoff_unix'] - 1800 and clock['force_cutoff_unix'] < clock['termination_unix'],
                'clock order or the 30-minute hash reserve is broken')
    return 'setup %d, work %d, score %d, forced shutdown %d, hard limit %d seconds: as in PLAN_CONSTANTS.json' % (
        clock['setup_cutoff_unix'], clock['work_cutoff_unix'], clock['score_cutoff_unix'],
        clock['force_cutoff_unix'], clock['termination_unix'])


def check_clock_controller(files):
    text = files.controller_text('aws_control.py')
    names = files.controller_names('aws_control.py')
    clock = files.guest()['CLOCK']
    four = [clock[name] for name in CLOCK_NAMES]
    for name in CLOCK_NAMES:
        found = re.findall(r"'%s'\s*:\s*started\s*\+\s*(\w+)" % name, text)
        fail_unless(len(found) == 1, "aws_control.py: '%s':started+N was found %d times, not once" % (name, len(found)))
        value = resolve(found[0], names, 'aws_control.py')
        fail_unless(value == clock[name], "aws_control.py launch intent: '%s' is started+%d; the guest needs +%d"
                    % (name, value, clock[name]))
    allowed = set(four) | {clock['termination_unix'] - 60}
    used = sorted({resolve(token, names, 'aws_control.py') for token in re.findall(r'started\s*\+\s*(\w+)', text)})
    left = [value for value in used if value not in allowed]
    fail_unless(not left, 'aws_control.py adds other seconds to the launch time: %r (allowed %r)' % (left, sorted(allowed)))
    life = [resolve(token, names, 'aws_control.py') for token in re.findall(r'expires\s*=\s*(\w+)', text)]
    fail_unless(life and all(value == clock['termination_unix'] for value in life),
                'aws_control.py link life %r is not the hard limit %d' % (life, clock['termination_unix']))
    for stale in ('11400', '14100', '14400', '14340'):
        fail_unless(stale not in text, 'aws_control.py still holds the old clock number ' + stale)
    common = files.controller_names('controller_common.py')
    fail_unless(common.get('CLOCK_SECONDS') == four, 'controller_common.py CLOCK_SECONDS %r differs from the guest %r'
                % (common.get('CLOCK_SECONDS'), four))
    return 'launch intent, every started+N, the link life and CLOCK_SECONDS use %r, as the guest does' % four


def check_clock_watchdog(files):
    text = files.controller_text('watchdog.py')
    names = files.controller_names('watchdog.py')
    clock = files.guest()['CLOCK']
    end = re.findall(r"deadline\s*==\s*intent\['launch_unix'\]\s*\+\s*(\w+)", text)
    force = re.findall(r"intent\['force_cutoff_unix'\]\s*==\s*intent\['launch_unix'\]\s*\+\s*(\w+)", text)
    fail_unless(len(end) == 1 and len(force) == 1, 'watchdog.py: the deadline check was not found exactly once')
    end_value = resolve(end[0], names, 'watchdog.py')
    force_value = resolve(force[0], names, 'watchdog.py')
    fail_unless(end_value == clock['termination_unix'], 'watchdog.py hard limit is +%d; the guest needs +%d'
                % (end_value, clock['termination_unix']))
    fail_unless(force_value == clock['force_cutoff_unix'], 'watchdog.py forced shutdown is +%d; the guest needs +%d'
                % (force_value, clock['force_cutoff_unix']))
    other = sorted({resolve(token, names, 'watchdog.py')
                    for token in re.findall(r"launch_unix'\]\s*\+\s*(\w+)", text)} - {end_value, force_value})
    fail_unless(not other, 'watchdog.py adds other seconds to the launch time: %r' % other)
    for stale in ('14100', '14400'):
        fail_unless(stale not in text, 'watchdog.py still holds the old clock number ' + stale)
    return 'hard limit +%d and forced shutdown +%d, as in the guest' % (end_value, force_value)


def check_source_caps(files):
    guest = files.guest()
    source = files.source()
    names = source['names']
    unpacked = sum(row['bytes'] for row in source['members'].values())
    fail_unless(len(names) == len(set(names)), 'source.zip holds a member name twice')
    fail_unless(all(safe_name(name) and not name.endswith('/') for name in names),
                'source.zip holds a member name the guest refuses')
    fail_unless(all(kind in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) for kind in source['kinds']),
                'source.zip uses a compression the guest refuses')
    fail_unless(0 < len(names) <= guest['SOURCE_FILE_CAP'], 'source.zip has %d files; the guest cap is %d'
                % (len(names), guest['SOURCE_FILE_CAP']))
    fail_unless(unpacked <= guest['SOURCE_UNPACKED_CAP'], 'source.zip unpacks to %d bytes; the guest cap is %d'
                % (unpacked, guest['SOURCE_UNPACKED_CAP']))
    return '%d files of at most %d; %d unpacked bytes of at most %d' % (
        len(names), guest['SOURCE_FILE_CAP'], unpacked, guest['SOURCE_UNPACKED_CAP'])


def check_requirements(files):
    guest = files.guest()
    members = files.source()['members']
    fail_unless(REQUIREMENTS_NAME in members, REQUIREMENTS_NAME + ' is not in source.zip')
    got = members[REQUIREMENTS_NAME]['sha256']
    fail_unless(got == REQUIREMENTS_SHA == guest['REQUIREMENTS_SHA'],
                'requirements file sha256 %s is not the pinned %s' % (got, REQUIREMENTS_SHA))
    return REQUIREMENTS_NAME + ' is in source.zip with the pinned sha256 ' + got


def check_manifest(files):
    guest = files.guest()
    source = files.source()
    members = source['members']
    fail_unless(MANIFEST_NAME in members, MANIFEST_NAME + ' is not in source.zip')
    got = members[MANIFEST_NAME]['sha256']
    fail_unless(guest['SOURCE_SEAL'] != PLACEHOLDERS['SOURCE_SEAL'],
                'the guest is not stamped yet (SOURCE_SEAL holds the placeholder)')
    fail_unless(got == guest['SOURCE_SEAL'], 'BUNDLE_MANIFEST.json sha256 %s is not the guest pin %s'
                % (got, guest['SOURCE_SEAL']))
    listed = json.loads(source['data'][MANIFEST_NAME].decode('utf-8'))['files']
    actual = [{'path': name, 'bytes': members[name]['bytes'], 'sha256': members[name]['sha256']}
              for name in sorted(members) if name != MANIFEST_NAME]
    fail_unless(listed == actual, 'BUNDLE_MANIFEST.json does not list exactly the other members of source.zip')
    return 'BUNDLE_MANIFEST.json sha256 %s equals the guest pin and lists all %d other members' % (got, len(actual))


def check_source_pins(files):
    guest = files.guest()
    source = files.source()
    fail_unless(guest['SOURCE_ZIP_SHA'] != PLACEHOLDERS['SOURCE_ZIP_SHA'],
                'the guest is not stamped yet (SOURCE_ZIP_SHA holds the placeholder)')
    fail_unless(guest['SOURCE_ZIP_SHA'] == source['sha256'], 'guest pin SOURCE_ZIP_SHA is not the sha256 of source.zip')
    fail_unless(guest['SOURCE_ZIP_BYTES'] == source['bytes'], 'guest pin SOURCE_ZIP_BYTES is not the size of source.zip')
    fail_unless(guest['SOURCE_MEMBERS'] == len(source['names']), 'guest pin SOURCE_MEMBERS is not the member count')
    return 'source.zip sha256 %s, %d bytes, %d members: all three equal the guest pins' % (
        source['sha256'], source['bytes'], len(source['names']))


def input_listing(files):
    def make():
        path = files.path('input.zip')
        with zipfile.ZipFile(path, 'r') as archive:
            return [(info.filename, info.file_size, info.compress_type, info.flag_bits) for info in archive.infolist()]
    return files.keep('input_listing', make)


def check_model_numbers(files):
    guest = files.guest()
    model = files.plan()['model_b']
    want = (guest['MODEL_FILES'], guest['MODEL_BYTES'])
    plan = (model['file_count'], model['total_bytes'])
    fail_unless(want == plan, 'guest numbers %r differ from the plan %r' % (want, plan))
    declared = files.contract()['model_cache']['files']
    contract = (len(declared), sum(row['bytes'] for row in declared.values()))
    fail_unless(want == contract, 'guest numbers %r differ from CONTRACT.json %r' % (want, contract))
    snapshot = files.contract()['model_cache']['snapshots']['B']
    fail_unless(set(files.contract()['model_cache']['snapshots']) == {'B'}
                and 'models/' + snapshot == model['snapshot_path_in_payload']
                and snapshot.rsplit('/', 1)[-1] == guest['MODEL_REVISION'] == model['revision'],
                'the snapshot path or the revision differs between contract, plan and guest')
    fail_unless(declared == {snapshot + '/' + name: model['files'][name] for name in model['files']},
                'CONTRACT.json model files differ from PLAN_CONSTANTS.json model_b.files')
    listing = [row for row in input_listing(files) if row[0].startswith('models/')]
    packed = (len(listing), sum(row[1] for row in listing))
    fail_unless(want == packed, 'guest numbers %r differ from the model members of input.zip %r' % (want, packed))
    fail_unless({row[0]: row[1] for row in listing} == {'models/' + key: row['bytes'] for key, row in declared.items()},
                'the model members of input.zip do not have the declared names and sizes')
    return '%d model files, %d bytes: the same in the guest, the plan, CONTRACT.json and input.zip' % want


def check_contract(files):
    guest = files.guest()
    contract = files.contract()
    source = files.source()
    fail_unless(contract.get('schema') == CONTRACT_SCHEMA, 'contract schema is not what the guest requires')
    fail_unless(contract['limits'] == guest['LIMITS'], 'contract limits differ from the guest LIMITS')
    fail_unless(contract['clock_seconds'] == guest['CLOCK'], 'contract clock differs from the guest clock')
    fail_unless(contract['runtime'] == SEALED_RUNTIME, 'the runtime block is not the sealed one')
    declared = contract['source']
    fail_unless(declared['zip_sha256'] == source['sha256'] and declared['zip_bytes'] == source['bytes']
                and declared['manifest_sha256'] == source['members'].get(MANIFEST_NAME, {}).get('sha256')
                and declared['members'] == source['members'],
                'contract source block differs from source.zip')
    external = contract['external_authority']
    fail_unless(isinstance(external.get('files'), dict) and external['files']
                and external.get('owner_record') in external['files'],
                'contract authority block has no files or no owner record')
    for group in (declared['members'], contract['model_cache']['files'], external['files']):
        for name, row in group.items():
            fail_unless(safe_name(name) and set(row) == {'bytes', 'sha256'} and type(row['bytes']) is int
                        and re.fullmatch(r'[a-f0-9]{64}', row['sha256']) is not None,
                        'a file declaration has the wrong shape: ' + name)
    job = files.controller_names('controller_common.py').get('JOB')
    fail_unless(contract.get('job') == job and isinstance(job, str),
                'contract job %r differs from the controller JOB %r' % (contract.get('job'), job))
    return ('schema, limits, clock, sealed runtime block, source block and authority block agree; '
            'job id %s equals the controller JOB' % job)


def check_limits_plan(files):
    limits = files.guest()['LIMITS']
    plan = files.plan()
    gpu = plan['aws']['gpu_job']
    gate0 = plan['gates']['gate_0']
    fail_unless(limits['model_calls'] == gpu['call_cap'], 'call cap differs from the plan')
    fail_unless(limits['archive_bytes'] == gpu['archive_cap_bytes'], 'archive cap differs from the plan')
    fail_unless(limits['score_seconds_min'] == gate0['score_time_limit_min_seconds']
                and limits['score_seconds_max'] == gate0['score_time_limit_max_seconds'],
                'score time limits differ from the plan')
    fail_unless(limits['scientific_bytes'] + 16 * 1024 * 1024 <= limits['archive_bytes'],
                'the work-folder cap leaves no room for the archive inventory')
    return 'call cap %d, archive cap %d bytes, score limit %d to %d s: as in PLAN_CONSTANTS.json' % (
        limits['model_calls'], limits['archive_bytes'], limits['score_seconds_min'], limits['score_seconds_max'])


def check_input_zip(files, hash_models):
    contract = files.contract()
    source = files.source()
    guest = files.guest()
    listing = input_listing(files)
    path = files.path('input.zip')
    names = [row[0] for row in listing]
    expected = {'CONTRACT.json': len(files.contract_bytes()), 'source.zip': source['bytes']}
    expected.update({'models/' + key: row['bytes'] for key, row in contract['model_cache']['files'].items()})
    expected.update({'authority/' + key: row['bytes'] for key, row in contract['external_authority']['files'].items()})
    fail_unless(len(names) == len(set(names)) and set(names) == set(expected),
                'input.zip members are not exactly the ones the guest expects: extra %r, missing %r'
                % (sorted(set(names) - set(expected)), sorted(set(expected) - set(names))))
    for name, size, kind, flags in listing:
        fail_unless(size == expected[name], 'input.zip member has the wrong size: ' + name)
        fail_unless(kind in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED) and not flags & 1 and safe_name(name),
                    'input.zip member is not acceptable to the guest: ' + name)
    size = path.stat().st_size
    cap = files.controller_names('controller_common.py').get('INPUT_CAP_BYTES')
    fail_unless(size <= guest['MAX_INPUT'], 'input.zip is over the guest input limit')
    fail_unless(type(cap) is int and size <= cap <= guest['MAX_INPUT'],
                'input.zip (%d bytes) is over the controller cap INPUT_CAP_BYTES %r' % (size, cap))
    hashes = {'CONTRACT.json': sha_bytes(files.contract_bytes()), 'source.zip': source['sha256']}
    hashes.update({'authority/' + key: row['sha256'] for key, row in contract['external_authority']['files'].items()})
    if hash_models:
        hashes.update({'models/' + key: row['sha256'] for key, row in contract['model_cache']['files'].items()})
    with zipfile.ZipFile(path, 'r') as archive:
        for name in sorted(hashes):
            value = hashlib.sha256()
            with archive.open(name, 'r') as handle:
                for chunk in iter(lambda: handle.read(CHUNK), b''):
                    value.update(chunk)
            fail_unless(value.hexdigest() == hashes[name], 'input.zip member has the wrong sha256: ' + name)
    return ('%d members, exactly the expected names and sizes; %d bytes; sha256 checked for %d members%s; '
            'input.zip sha256 %s' % (len(names), size, len(hashes),
                                     '' if hash_models else ' (model files by size only; use --hash-models)',
                                     sha_path(path)))


def seal_rows(files):
    def make():
        raw = files.path(SEAL_NAME, files.root / 'optionb').read_bytes()
        fail_unless(raw.endswith(b'\n') and b'\r' not in raw, 'the seal file must use LF line ends')
        lines = raw[:-1].split(b'\n')
        rows = [json.loads(line.decode('utf-8')) for line in lines]
        previous = None
        for number, (line, row) in enumerate(zip(lines, rows), 1):
            fail_unless(row.get('n') == number and row.get('previous_line_sha256') == previous,
                        'the seal chain is broken at line %d' % number)
            previous = sha_bytes(line)
        return raw, lines, rows
    return files.keep('seal', make)


def check_seal_package(files):
    source = files.source()
    raw, lines, rows = seal_rows(files)
    fail_unless(SEAL_NAME in source['data'], 'the seal file is not in source.zip')
    copy = source['data'][SEAL_NAME]
    fail_unless(raw.startswith(copy), 'the seal copy in source.zip is not the start of the seal file on disk')
    kept = copy.count(b'\n')
    # Review round 1 (FILE_FORMATS.md 14 and 15.2): the copy ends with step 6, or with the last program-repair
    # line. No program line may follow it in the seal file, or the package is older than a repair.
    fail_unless(kept >= 1 and copy.endswith(b'\n') and rows[kept - 1].get('step') in PROGRAM_LINES,
                'the seal copy in source.zip does not end with step 6_PROGRAMS or a line 6R_PROGRAMS_REPAIRED')
    fail_unless(all(row.get('step') not in PROGRAM_LINES for row in rows[kept:]),
                'the seal file holds a program line after the seal copy in source.zip: the package is stale')
    # The hash in force: for a path that more than one line lists, the latest line counts.
    in_force = {}
    for row in rows[:kept]:
        for entry in row.get('files', []):
            in_force[entry['path']] = entry
    sealed = {entry['package_path']: {'bytes': entry['bytes'], 'sha256': entry['sha256']}
              for entry in in_force.values() if entry.get('package_path') is not None}
    extra = {SEAL_NAME, REQUIREMENTS_NAME, MANIFEST_NAME}
    packed = {name: row for name, row in source['members'].items() if name not in extra}
    fail_unless(packed == sealed, 'the package files differ from the seal: only in zip %r, only in seal %r, changed %r'
                % (sorted(set(packed) - set(sealed)), sorted(set(sealed) - set(packed)),
                   sorted(name for name in set(packed) & set(sealed) if packed[name] != sealed[name])))
    fail_unless(extra <= set(source['members']), 'source.zip lacks the seal, the requirements file or the manifest')
    # Plan section 18: three views that are always printed need content() from tools/verdict.py inside the package.
    pin = files.plan()['sources']['verdict_program']
    fail_unless(packed.get(VERDICT_NAME) == {'bytes': pin['bytes'], 'sha256': pin['sha256']},
                VERDICT_NAME + ' is not in source.zip with the size and sha256 pinned in PLAN_CONSTANTS.json')
    return ('%d sealed package files equal the seal in force (sizes and sha256); %s is among them with its pinned '
            'sha256; seal copy holds %d lines, ends at %s' % (len(sealed), VERDICT_NAME, kept, rows[kept - 1].get('step')))


def check_precheck_binding(files):
    bound = files.contract().get('precheck')
    fail_unless(isinstance(bound, dict), 'CONTRACT.json has no pre-check block')
    raw, lines, rows = seal_rows(files)
    steps = [row.get('step') for row in rows]
    step7 = [row for row in rows if row.get('step') == '7_PRECHECK']
    # Amendment A5 (FILE_FORMATS.md 15.2): a tool-repair line stands after line 1 and before the line 3C, and a
    # program-repair line before step 7. So the pre-check line is the last line of the seal file.
    fail_unless(len(step7) == 1 and steps[-1] == '7_PRECHECK',
                'the seal file must hold step 7_PRECHECK exactly once, as its last line')
    final = steps.index(FINAL_LINE) if FINAL_LINE in steps else 0
    fail_unless(all(0 < index < final for index, step in enumerate(steps) if step == TOOL_REPAIR),
                'a tool-repair line stands outside its window: it must stand after line 1 and before the line 3C')
    values = step7[0].get('values', {})
    fail_unless(values.get('selftest_status') == 'SELFTEST_PASS', 'the pre-check did not pass: %r'
                % values.get('selftest_status'))
    fail_unless(values.get('source_zip_sha256') == files.source()['sha256'] == bound.get('source_zip_sha256'),
                'the pre-check ran on another source.zip')
    for key in ('prompt_list_sha256', 'padding_plan_sha256', 'selftest_json_sha256'):
        fail_unless(isinstance(values.get(key), str) and re.fullmatch(r'[a-f0-9]{64}', values[key]) is not None
                    and bound.get(key) == values[key], 'pre-check value differs or is missing: ' + key)
    return 'the two pre-check hashes in CONTRACT.json equal seal step 7; same source.zip; SELFTEST_PASS'


def check_controller_extras(files):
    text = files.controller_text('aws_control.py')
    common = files.controller_names('controller_common.py')
    guest = files.guest()
    fail_unless('worker_v02.py' in text and 'helm-op11-work' in text,
                'aws_control.py no longer names worker_v02.py or the service helm-op11-work')
    parts = re.findall(r'for n in range\(1,\s*(\d+)\)', text)
    fail_unless(parts and all(int(value) - 1 == guest['MAX_PARTS'] for value in parts),
                'aws_control.py signs %r part links; the guest requires exactly %d' % (parts, guest['MAX_PARTS']))
    fail_unless('18000000000' not in text.replace('_', ''), 'aws_control.py still holds the old archive cap 18000000000')
    fail_unless(common.get('ARCHIVE_CAP_BYTES') == guest['LIMITS']['archive_bytes'],
                'controller ARCHIVE_CAP_BYTES %r differs from the guest %d'
                % (common.get('ARCHIVE_CAP_BYTES'), guest['LIMITS']['archive_bytes']))
    fail_unless(common.get('MODEL_CALLS') == guest['LIMITS']['model_calls'],
                'controller MODEL_CALLS differs from the guest call cap')
    fail_unless(common.get('BUCKET') == guest['BUCKET'] and common.get('PREFIX') == guest['PREFIX'],
                'controller bucket or prefix differs from the guest')
    return 'guest file name, service name, %d part links, archive cap %d, call cap %d, bucket and prefix agree' % (
        guest['MAX_PARTS'], guest['LIMITS']['archive_bytes'], guest['LIMITS']['model_calls'])


def check_runner_words(files):
    table = files.guest()['RUNNER']
    source = files.source()
    fail_unless(RUNNER_NAME in source['data'], RUNNER_NAME + ' is not in source.zip')
    text = source['data'][RUNNER_NAME].decode('utf-8')
    fail_unless(set(table) == set(RUNNER_COMMANDS), 'the guest RUNNER table does not hold exactly the five commands')
    guest_text = files.guest_bytes().decode('utf-8')
    # Every quoted word of the runner's own text: option names such as '--output-dir', and plain words.
    known = set(re.findall(r"'([A-Za-z0-9-]+)'", text))
    missing = []
    unfilled = []
    count = 0
    for key, command in RUNNER_COMMANDS.items():
        words = table[key]
        fail_unless(words[0] == command, 'the guest starts %r for stage %s; FILE_FORMATS.md names %r'
                    % (words[0], key, command))
        for word in words:
            if word.startswith('{'):
                # every {NAME} part must have a value in execute_science
                if not word.endswith('}') or ("'" + word[1:-1] + "':") not in guest_text:
                    unfilled.append(key + ': ' + word)
                continue
            count += 1
            if word not in known:
                missing.append(key + ': ' + word)
    fail_unless(not unfilled, 'the guest gives no value for these parts of its command lines: %r' % unfilled)
    fail_unless(not missing, 'job/runner_b1.py does not hold these words of the guest command lines, '
                'as whole quoted words: %r' % missing)
    fail_unless('keys' not in ' '.join(table['run_final']).lower() and '{PACKAGE}' not in table['run_final'],
                'the final stage must not be given the package folder or a key folder')
    return ('all %d fixed words of the five command lines occur in job/runner_b1.py as whole quoted words; '
            'run-final names no key folder' % count)


def main():
    parser = argparse.ArgumentParser(description='Build-time text check for Option B GPU job b1.')
    parser.add_argument('--dir', default=str(Path(__file__).resolve().parent),
                        help='folder with worker_v02.py, CONTRACT.json, source.zip and input.zip')
    parser.add_argument('--controller-dir', default=None,
                        help='folder with aws_control.py, watchdog.py and controller_common.py (default: --dir)')
    parser.add_argument('--study-root', default=STUDY_ROOT)
    parser.add_argument('--hash-models', action='store_true')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()

    files = Files(args.dir, args.controller_dir or args.dir, args.study_root)
    plan = [
        ('A1 clock: guest against the plan', lambda: check_clock_plan(files)),
        ('A2 clock: controller against the guest', lambda: check_clock_controller(files)),
        ('A3 clock: watchdog against the guest', lambda: check_clock_watchdog(files)),
        ('B1 source.zip under the guest caps', lambda: check_source_caps(files)),
        ('C1 requirements file pinned', lambda: check_requirements(files)),
        ('C2 bundle manifest pinned', lambda: check_manifest(files)),
        ('C3 source.zip equals the guest pins', lambda: check_source_pins(files)),
        ('D1 model file count and bytes', lambda: check_model_numbers(files)),
        ('E1 guest within both size limits', lambda: check_guest_sizes(files)),
        ('X1 guest parses; sealed lines kept', lambda: check_guest_parses(files)),
        ('X2 contract agrees with the guest', lambda: check_contract(files)),
        ('X3 guest limits agree with the plan', lambda: check_limits_plan(files)),
        ('X4 input.zip members', lambda: check_input_zip(files, args.hash_models)),
        ('X5 package equals the seal', lambda: check_seal_package(files)),
        ('X6 pre-check receipt bound', lambda: check_precheck_binding(files)),
        ('X7 other controller numbers', lambda: check_controller_extras(files)),
        ('X8 runner command words', lambda: check_runner_words(files)),
    ]
    results = []
    for name, check in plan:
        try:
            results.append({'check': name, 'status': 'PASS', 'detail': check()})
        except Fail as reason:
            results.append({'check': name, 'status': 'FAIL', 'detail': str(reason)})
        except Exception as error:
            results.append({'check': name, 'status': 'FAIL',
                            'detail': 'could not be checked: %s: %s' % (type(error).__name__, error)})
    failed = [row for row in results if row['status'] == 'FAIL']
    verdict = 'TEXT_CHECK_PASS' if not failed else 'TEXT_CHECK_FAIL'
    print('Text check for GPU job b1, folder %s' % args.dir)
    for row in results:
        print('%-5s %s' % (row['status'], row['check']))
        print('      ' + row['detail'])
    print('%s: %d of %d checks failed' % (verdict, len(failed), len(results)))
    if args.write:
        report = {'schema': 'casalescence/optionb/text-check/v1', 'verdict': verdict, 'checks': results,
                  'made_by': {'program': Path(__file__).name, 'sha256': sha_path(__file__)}}
        target = Path(args.dir) / 'TEXT_CHECK_B1.json'
        with open(str(target) + '.partial', 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(json.dumps(report, indent=1, ensure_ascii=False) + '\n')
        os.replace(str(target) + '.partial', target)
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
