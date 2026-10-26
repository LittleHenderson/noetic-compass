"""Write CONTRACT.json for Option B GPU job b1, and stamp the guest's four source pins.

What it does, in plain words:
  1. Opens source.zip read-only and hashes every member.
  2. Takes the 7 model-B files from PLAN_CONSTANTS.json and checks them against the
     model inventory of the job that ran on 2026-10-04.
  3. Copies the runtime block from the old sealed CONTRACT.json, word for word.
     The guest checks that block exactly as sealed. It is never retyped here.
  4. Takes the limits and the clock from the guest file itself (by parsing it, not
     by running it) and checks them against PLAN_CONSTANTS.json.
  5. Reads seal step 7 (the pre-check receipt). The pre-check must have passed on
     this exact source.zip. Its two hashes go into the contract.
  6. Writes CONTRACT.json (.partial, then rename).
  7. With --stamp-guest: writes the source.zip hash, size, member count and the
     bundle manifest hash into the guest, then checks the guest's two size limits.

With --stamp-only it does steps 1 and 7 and nothing else. That is for the time
before the pre-check job has run, when the guest must be final for its review.

It runs no project code, no model code, no AWS call and no outside service.

Status: built by Claude, checked by a separate reviewer in one review round, never run before.
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
OLD_CONTROLLER = 'D:/tksCAS-runs/controller_cas_small_op11_claude_c1'
# REAL, hashed on 2026-10-05: the sealed contract and the model inventory of the 2026-10-04 job.
OLD_CONTRACT_SHA = 'a67c1d9d243b72095247f713d7416e3801b91c51a699c4134a172121de00c663'
INVENTORY_SHA = '1f80431fe4d510294a6c0af39356180271736b935c350d7ef5c9fd2ebd478766'
# REAL, hashed on 2026-10-05: the standing owner approval record of this study.
STANDING_APPROVAL = 'OWNER_APPROVAL_ALL_STAGES_20261005T0610Z.json'
STANDING_APPROVAL_SHA = 'd1c052f56b61a6f30a428d25b4530352d6cd6ddb489163734fe6ea6d23b24325'
CONTRACT_SCHEMA = 'cas-optionb-b1-guest-contract/v1'
SEAL_NAME = 'SEAL_OPTIONB.jsonl'
REQUIREMENTS_NAME = 'contracts/requirements.small-linux.txt'
MANIFEST_NAME = 'BUNDLE_MANIFEST.json'
# The guest's two size limits (the old guest's own sizes).
GUEST_RAW_LIMIT = 73986
GUEST_PACKED_LIMIT = 28420
# What the unstamped guest holds: sha256 of the text 'UNSTAMPED:<name>'.
PLACEHOLDERS = {name: hashlib.sha256(('UNSTAMPED:' + name).encode('ascii')).hexdigest()
                for name in ('SOURCE_ZIP_SHA', 'SOURCE_SEAL')}
HEX64 = re.compile(r'[a-f0-9]{64}')


def stop(code, detail=''):
    raise SystemExit('BUILD_STOPPED ' + code + ((': ' + str(detail)) if detail != '' else ''))


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha_path(path):
    value = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_bytes().decode('utf-8-sig'))


def packed_size(data):
    """Exactly how aws_control.py packs the guest for the launch command."""
    return len(base64.b64encode(gzip.compress(data, mtime=0)))


def literals(text):
    """Read plain module-level constants by parsing the text. Nothing is run."""
    found = {}
    for node in ast.parse(text).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                found[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, SyntaxError, TypeError):
                pass
    return found


def write_replace(path, data):
    partial = Path(str(path) + '.partial')
    with open(partial, 'wb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(partial, path)


def source_facts(path):
    """Hash source.zip and every member. Members are a few MB at most."""
    members = {}
    with zipfile.ZipFile(path, 'r') as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            stop('SOURCE_ZIP_DUPLICATE_MEMBER')
        for name in names:
            data = archive.read(name)
            members[name] = {'bytes': len(data), 'sha256': sha_bytes(data)}
        seal_copy = archive.read(SEAL_NAME) if SEAL_NAME in names else None
    return {'zip_sha256': sha_path(path), 'zip_bytes': Path(path).stat().st_size, 'members': members,
            'seal_copy': seal_copy}


def check_plan_against_guest(plan, guest):
    """The plan and the guest must give the same numbers. A difference is a build error."""
    gpu = plan['aws']['gpu_job']
    clock = gpu['clock_seconds']
    want = {'setup_cutoff_unix': clock['setup_must_end'], 'work_cutoff_unix': clock['work_cutoff'],
            'score_cutoff_unix': clock['score_must_end'], 'force_cutoff_unix': clock['forced_shutdown'],
            'termination_unix': clock['hard_limit']}
    if guest['CLOCK'] != want:
        stop('GUEST_CLOCK_DIFFERS_FROM_PLAN', {'guest': guest['CLOCK'], 'plan': want})
    limits = guest['LIMITS']
    gate0 = plan['gates']['gate_0']
    if (limits['model_calls'] != gpu['call_cap'] or limits['archive_bytes'] != gpu['archive_cap_bytes']
            or limits['score_seconds_min'] != gate0['score_time_limit_min_seconds']
            or limits['score_seconds_max'] != gate0['score_time_limit_max_seconds']):
        stop('GUEST_LIMITS_DIFFER_FROM_PLAN', limits)
    model = plan['model_b']
    if ((guest['MODEL_FILES'], guest['MODEL_BYTES']) != (model['file_count'], model['total_bytes'])
            or guest['MODEL_REVISION'] != model['revision']):
        stop('GUEST_MODEL_NUMBERS_DIFFER_FROM_PLAN', (guest['MODEL_FILES'], guest['MODEL_BYTES']))


def model_files(plan, inventory):
    """The 7 model-B files, keyed by their path under payload/models/."""
    model = plan['model_b']
    prefix = 'models/'
    if not model['snapshot_path_in_payload'].startswith(prefix):
        stop('PLAN_SNAPSHOT_PATH_SHAPE')
    snapshot = model['snapshot_path_in_payload'][len(prefix):]
    rows = [row for row in inventory['models'] if row['role'] == 'B']
    if len(rows) != 1 or rows[0]['model_id'] != model['model_id'] or rows[0]['revision'] != model['revision']:
        stop('INVENTORY_MODEL_B_ROW')
    listed = {row['filename']: {'bytes': row['bytes'], 'sha256': row['sha256']} for row in rows[0]['files']}
    if listed != model['files']:
        stop('PLAN_MODEL_FILES_DIFFER_FROM_INVENTORY')
    files = {snapshot + '/' + name: {'bytes': model['files'][name]['bytes'],
                                     'sha256': model['files'][name]['sha256']} for name in sorted(model['files'])}
    if (len(files), sum(row['bytes'] for row in files.values())) != (model['file_count'], model['total_bytes']):
        stop('MODEL_FILES_DO_NOT_ADD_UP')
    return snapshot, files


def precheck_binding(seal_path, source):
    """Seal step 7: the pre-check receipt. It must name this exact source.zip and a pass."""
    raw = Path(seal_path).read_bytes()
    if not raw.endswith(b'\n') or b'\r' in raw:
        stop('SEAL_LINE_ENDS')
    if source['seal_copy'] is None or not raw.startswith(source['seal_copy']):
        stop('PACKAGE_SEAL_COPY_IS_NOT_THE_START_OF_THE_SEAL_FILE')
    lines = raw[:-1].split(b'\n')
    rows = [json.loads(line.decode('utf-8')) for line in lines]
    steps = [row.get('step') for row in rows]
    step7 = [(line, row) for line, row in zip(lines, rows) if row.get('step') == '7_PRECHECK']
    # Amendment A5 (FILE_FORMATS.md 15.2): a tool-repair line stands before the line 3C, and a program-repair
    # line before step 7. So the pre-check line is the last line of the seal file.
    if len(step7) != 1 or steps[-1] != '7_PRECHECK':
        stop('SEAL_MUST_END_WITH_ONE_STEP_7_PRECHECK', steps)
    # The package must hold the seal up to its last program line. A package built before a repair line
    # 6R_PROGRAMS_REPAIRED is stale: the pre-check that passed did not run on it.
    kept = source['seal_copy'].count(b'\n')
    if (kept < 1 or steps[kept - 1] not in ('6_PROGRAMS', '6R_PROGRAMS_REPAIRED')
            or any(step in ('6_PROGRAMS', '6R_PROGRAMS_REPAIRED') for step in steps[kept:])):
        stop('PACKAGE_SEAL_COPY_DOES_NOT_END_AT_THE_LAST_PROGRAM_LINE', steps)
    line, row = step7[0]
    values = row.get('values', {})
    if values.get('source_zip_sha256') != source['zip_sha256']:
        stop('PRECHECK_RAN_ON_ANOTHER_SOURCE_ZIP', values.get('source_zip_sha256'))
    if values.get('selftest_status') != 'SELFTEST_PASS':
        stop('PRECHECK_DID_NOT_PASS_NO_GPU_CONTRACT', values.get('selftest_status'))
    for key in ('prompt_list_sha256', 'padding_plan_sha256', 'selftest_json_sha256'):
        if not isinstance(values.get(key), str) or HEX64.fullmatch(values[key]) is None:
            stop('PRECHECK_VALUE_SHAPE', key)
    return {'prompt_list_sha256': values['prompt_list_sha256'],
            'padding_plan_sha256': values['padding_plan_sha256'],
            'selftest_json_sha256': values['selftest_json_sha256'],
            'source_zip_sha256': values['source_zip_sha256'],
            'seal_step_7_line_sha256': sha_bytes(line)}


def stamp_guest(guest_path, source, manifest_sha, allow):
    """Work out the guest with its four source pins set. Writes nothing.

    Returns (final guest bytes, state). The caller writes the bytes when the state is STAMPED_NOW.
    """
    data = Path(guest_path).read_bytes()
    if b'\r' in data:
        stop('GUEST_HAS_CR_LINE_ENDS')
    text = data.decode('utf-8')
    now = literals(text)
    want = {'SOURCE_ZIP_SHA': source['zip_sha256'], 'SOURCE_ZIP_BYTES': source['zip_bytes'],
            'SOURCE_MEMBERS': len(source['members']), 'SOURCE_SEAL': manifest_sha}
    if all(now.get(name) == value for name, value in want.items()):
        return data, 'ALREADY_STAMPED_WITH_THESE_VALUES'
    unstamped = (now.get('SOURCE_ZIP_SHA') == PLACEHOLDERS['SOURCE_ZIP_SHA']
                 and now.get('SOURCE_SEAL') == PLACEHOLDERS['SOURCE_SEAL']
                 and now.get('SOURCE_ZIP_BYTES') == 0 and now.get('SOURCE_MEMBERS') == 0)
    if not unstamped:
        stop('GUEST_IS_STAMPED_WITH_OTHER_VALUES',
             'a guest stamped for another source.zip is not restamped; start again from the reviewed draft')
    if not allow:
        stop('GUEST_NOT_STAMPED', 'run again with --stamp-guest')
    for name, value in want.items():
        old_line = '%s = %r\n' % (name, now[name])
        new_line = '%s = %r\n' % (name, value)
        if text.count('\n' + old_line) != 1:
            stop('STAMP_LINE_NOT_FOUND_EXACTLY_ONCE', name)
        text = text.replace('\n' + old_line, '\n' + new_line)
    stamped = text.encode('utf-8')
    after = literals(text)
    if any(after.get(name) != value for name, value in want.items()):
        stop('STAMP_DID_NOT_TAKE')
    return stamped, 'STAMPED_NOW'


def main():
    parser = argparse.ArgumentParser(description='Write CONTRACT.json for Option B GPU job b1.')
    parser.add_argument('--out', default=str(Path(__file__).resolve().parent),
                        help='controller folder: holds source.zip and worker_v02.py; receives CONTRACT.json')
    parser.add_argument('--job', default=None,
                        help='job id; default: the JOB constant of <out>/controller_common.py')
    parser.add_argument('--study-root', default=STUDY_ROOT)
    parser.add_argument('--old-contract', default=OLD_CONTROLLER + '/CONTRACT.json')
    parser.add_argument('--inventory', default=OLD_CONTROLLER + '/MODEL_CACHE_FILE_INVENTORY.json')
    parser.add_argument('--authority', action='append', default=None,
                        help='authority record to carry in input.zip; may be given more than once; '
                             'default: the standing owner approval record of the study')
    parser.add_argument('--owner-record', default=None,
                        help='file name of the owner approval record among the authority files '
                             '(default: the first one)')
    parser.add_argument('--stamp-guest', action='store_true',
                        help='write the four source pins into <out>/worker_v02.py if it is still unstamped')
    parser.add_argument('--stamp-only', action='store_true',
                        help='stamp the guest from source.zip and stop; no contract is written')
    args = parser.parse_args()

    out = Path(args.out)
    root = Path(args.study_root)
    plan = read_json(root / 'optionb' / 'PLAN_CONSTANTS.json')
    guest_path = out / 'worker_v02.py'
    guest = literals(guest_path.read_bytes().decode('utf-8'))
    for name in ('CLOCK', 'LIMITS', 'MODEL_FILES', 'MODEL_BYTES', 'MODEL_REVISION', 'REQUIREMENTS_SHA',
                 'SOURCE_UNPACKED_CAP', 'SOURCE_FILE_CAP'):
        if name not in guest:
            stop('GUEST_CONSTANT_MISSING', name)
    check_plan_against_guest(plan, guest)

    # 1. source.zip
    source = source_facts(out / 'source.zip')
    members = source['members']
    unpacked = sum(row['bytes'] for row in members.values())
    if len(members) > guest['SOURCE_FILE_CAP'] or unpacked > guest['SOURCE_UNPACKED_CAP']:
        stop('SOURCE_ZIP_OVER_GUEST_CAPS', {'files': len(members), 'unpacked_bytes': unpacked})
    if members.get(REQUIREMENTS_NAME, {}).get('sha256') != guest['REQUIREMENTS_SHA']:
        stop('REQUIREMENTS_FILE_MISSING_OR_NOT_PINNED')
    if MANIFEST_NAME not in members:
        stop('BUNDLE_MANIFEST_MISSING')
    manifest_sha = members[MANIFEST_NAME]['sha256']

    if args.stamp_only:
        stamped, stamp_state = stamp_guest(guest_path, source, manifest_sha, True)
        if len(stamped) > GUEST_RAW_LIMIT or packed_size(stamped) > GUEST_PACKED_LIMIT:
            stop('GUEST_OVER_SIZE_LIMIT', {'raw': len(stamped), 'packed': packed_size(stamped)})
        if stamp_state == 'STAMPED_NOW':
            write_replace(guest_path, stamped)
        sys.stdout.write(json.dumps({
            'stamp': stamp_state, 'guest_sha256': sha_bytes(stamped), 'raw_bytes': len(stamped),
            'packed_bytes': packed_size(stamped), 'source_zip_sha256': source['zip_sha256'],
            'source_zip_bytes': source['zip_bytes'], 'source_members': len(members),
            'bundle_manifest_sha256': manifest_sha, 'contract_written': False}, indent=1) + '\n')
        return

    # The job id must be the controller's own.
    job = args.job
    common = out / 'controller_common.py'
    if common.exists():
        found = literals(common.read_bytes().decode('utf-8')).get('JOB')
        if not isinstance(found, str):
            stop('CONTROLLER_JOB_CONSTANT_NOT_FOUND')
        if job is not None and job != found:
            stop('JOB_DIFFERS_FROM_CONTROLLER', found)
        job = found
    if job is None or re.fullmatch(r'[A-Za-z0-9_.-]+', job) is None:
        stop('JOB_ID_REQUIRED', 'give --job, or put controller_common.py into the folder first')

    # 2. model files
    if sha_path(args.inventory) != INVENTORY_SHA:
        stop('MODEL_INVENTORY_FILE_CHANGED', args.inventory)
    snapshot, files = model_files(plan, read_json(args.inventory))

    # 3. the sealed runtime block, copied and never retyped
    if sha_path(args.old_contract) != OLD_CONTRACT_SHA:
        stop('OLD_SEALED_CONTRACT_CHANGED', args.old_contract)
    runtime = read_json(args.old_contract)['runtime']

    # 4. authority records
    paths = [Path(item) for item in (args.authority or [str(root / STANDING_APPROVAL)])]
    authority = {}
    for path in paths:
        if re.fullmatch(r'[A-Za-z0-9._-]+', path.name) is None or path.name in authority:
            stop('AUTHORITY_FILE_NAME', path.name)
        data = path.read_bytes()
        authority[path.name] = {'bytes': len(data), 'sha256': sha_bytes(data)}
    if STANDING_APPROVAL in authority and authority[STANDING_APPROVAL]['sha256'] != STANDING_APPROVAL_SHA:
        stop('STANDING_APPROVAL_RECORD_CHANGED')
    owner_record = args.owner_record or paths[0].name
    if owner_record not in authority:
        stop('OWNER_RECORD_NOT_AMONG_AUTHORITY_FILES', owner_record)

    # 5. the pre-check receipt
    bound = precheck_binding(root / 'optionb' / SEAL_NAME, source)

    contract = {
        'schema': CONTRACT_SCHEMA,
        'job': job,
        'purpose': 'Option B usefulness test, GPU job b1: self-test, practice, gate, final, score.',
        'source': {'zip_sha256': source['zip_sha256'], 'zip_bytes': source['zip_bytes'],
                   'manifest_sha256': manifest_sha, 'members': members},
        'model_cache': {'files': files, 'snapshots': {'B': snapshot}},
        'runtime': runtime,
        'limits': guest['LIMITS'],
        'clock_seconds': guest['CLOCK'],
        'precheck': bound,
        'external_authority': {'files': authority, 'owner_record': owner_record},
    }
    data = (json.dumps(contract, indent=1, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
    target = out / 'CONTRACT.json'
    if target.exists() and target.read_bytes() != data:
        stop('CONTRACT_EXISTS_WITH_OTHER_CONTENT', 'delete it on purpose if a new contract is wanted')

    # 6. the guest's four source pins. Every check runs before anything is written.
    stamped, stamp_state = stamp_guest(guest_path, source, manifest_sha, args.stamp_guest)
    if len(stamped) > GUEST_RAW_LIMIT or packed_size(stamped) > GUEST_PACKED_LIMIT:
        stop('GUEST_OVER_SIZE_LIMIT', {'raw': len(stamped), 'packed': packed_size(stamped)})
    if not target.exists():
        write_replace(target, data)
    if stamp_state == 'STAMPED_NOW':
        write_replace(guest_path, stamped)

    report = {
        'schema': 'casalescence/optionb/contract-build-receipt/v1',
        'job': job,
        'contract': {'path': str(target), 'bytes': len(data), 'sha256': sha_bytes(data)},
        'payload_manifest_sha256_for_the_controller': sha_bytes(data),
        'source_zip': {'bytes': source['zip_bytes'], 'sha256': source['zip_sha256'],
                       'members': len(members), 'unpacked_bytes': unpacked},
        'bundle_manifest_sha256': manifest_sha,
        'model_files': len(files),
        'model_bytes': sum(row['bytes'] for row in files.values()),
        'authority_files': sorted(authority),
        'owner_record': owner_record,
        'precheck_binding': bound,
        'guest': {'path': str(guest_path), 'stamp': stamp_state, 'raw_bytes': len(stamped),
                  'raw_limit': GUEST_RAW_LIMIT, 'packed_bytes': packed_size(stamped),
                  'packed_limit': GUEST_PACKED_LIMIT, 'sha256': sha_bytes(stamped)},
        'made_by': {'program': Path(__file__).name, 'sha256': sha_path(__file__)},
    }
    text = json.dumps(report, indent=1, ensure_ascii=False) + '\n'
    write_replace(out / 'CONTRACT_BUILD_RECEIPT.json', text.encode('utf-8'))
    sys.stdout.write(text)


if __name__ == '__main__':
    main()
