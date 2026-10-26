"""Build input.zip for Option B GPU job b1. Standard library only. Files only.

What it does, in plain words:
  1. Opens the sealed input.zip of the job that ran on 2026-10-04, read-only.
     It never writes to it and never extracts it to disk.
  2. Copies the 7 model-B members (999,586,347 bytes) into a new stored zip, in
     pieces of 1 MB. Each member is hashed on the way. The hash must equal the
     contract, the plan and the model inventory of the old job. Model A is left out.
  3. Adds CONTRACT.json, the authority record(s) and source.zip.
  4. Writes input.zip.partial, reopens it, re-hashes every member, then renames it.

It uses a few MB of memory and runs no model code and no project code.
No AWS call. No outside service. It reads about 1 GB three times (copy, re-hash, whole-file hash).

The exact members the guest expects (it refuses anything else):
  CONTRACT.json, source.zip, authority/<each authority file>, models/<each model file>

The pre-check job does not use this file. Its own builder packs the six small model files.

Status: built by Claude, checked by a separate reviewer in one review round, never run before.
"""
import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import zipfile
from pathlib import Path

STUDY_ROOT = 'C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/CASALESCENCE_NOETICS_v0_1'
OLD_CONTROLLER = 'D:/tksCAS-runs/controller_cas_small_op11_claude_c1'
# REAL, measured on 2026-10-05: the sealed input.zip of the 2026-10-04 job and its inventory.
OLD_INPUT_BYTES = 4098779980
OLD_INPUT_MEMBERS = 22
INVENTORY_SHA = '1f80431fe4d510294a6c0af39356180271736b935c350d7ef5c9fd2ebd478766'
STANDING_APPROVAL = 'OWNER_APPROVAL_ALL_STAGES_20261005T0610Z.json'
CONTRACT_SCHEMA = 'cas-optionb-b1-guest-contract/v1'
# The guest accepts at most 4,200,000,000 bytes. The b1 controller accepts at most 1,100,000,000.
MAX_INPUT = 1100000000
CHUNK = 1024 * 1024
ZIP_DATE = (2026, 10, 5, 0, 0, 0)


def stop(code, detail=''):
    raise SystemExit('BUILD_STOPPED ' + code + ((': ' + str(detail)) if detail != '' else ''))


def sha_path(path):
    value = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(CHUNK), b''):
            value.update(chunk)
    return value.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_bytes().decode('utf-8-sig'))


def new_info(name):
    info = zipfile.ZipInfo(name, date_time=ZIP_DATE)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    return info


def copy_stream(incoming, archive, name, expected):
    """Copy one member in 1 MB pieces, hashing on the way. Stops on any difference."""
    value = hashlib.sha256()
    count = 0
    with archive.open(new_info(name), 'w') as outgoing:
        while True:
            chunk = incoming.read(CHUNK)
            if not chunk:
                break
            count += len(chunk)
            if count > expected['bytes']:
                stop('MEMBER_LONGER_THAN_DECLARED', name)
            value.update(chunk)
            outgoing.write(chunk)
    if count != expected['bytes'] or value.hexdigest() != expected['sha256']:
        stop('MEMBER_DIFFERS_FROM_DECLARED', name)


def main():
    parser = argparse.ArgumentParser(description='Build input.zip for Option B GPU job b1.')
    parser.add_argument('--out', default=str(Path(__file__).resolve().parent),
                        help='controller folder: holds CONTRACT.json and source.zip; receives input.zip')
    parser.add_argument('--study-root', default=STUDY_ROOT)
    parser.add_argument('--old-input-zip', default=OLD_CONTROLLER + '/input.zip')
    parser.add_argument('--inventory', default=OLD_CONTROLLER + '/MODEL_CACHE_FILE_INVENTORY.json')
    parser.add_argument('--authority', action='append', default=None,
                        help='the same authority file(s) that were given to build_contract_b1.py')
    args = parser.parse_args()

    out = Path(args.out)
    root = Path(args.study_root)
    contract_path = out / 'CONTRACT.json'
    contract = read_json(contract_path)
    if contract.get('schema') != CONTRACT_SCHEMA:
        stop('CONTRACT_SCHEMA', contract.get('schema'))
    plan = read_json(root / 'optionb' / 'PLAN_CONSTANTS.json')['model_b']

    # What the new zip must hold: name -> (where it comes from, declared size and hash).
    wanted = {}
    wanted['CONTRACT.json'] = ('file', contract_path,
                               {'bytes': contract_path.stat().st_size, 'sha256': sha_path(contract_path)})
    source_path = out / 'source.zip'
    declared_source = {'bytes': contract['source']['zip_bytes'], 'sha256': contract['source']['zip_sha256']}
    if {'bytes': source_path.stat().st_size, 'sha256': sha_path(source_path)} != declared_source:
        stop('SOURCE_ZIP_DIFFERS_FROM_CONTRACT')
    wanted['source.zip'] = ('file', source_path, declared_source)

    given = {Path(item).name: Path(item) for item in (args.authority or [str(root / STANDING_APPROVAL)])}
    declared_authority = contract['external_authority']['files']
    if set(given) != set(declared_authority):
        stop('AUTHORITY_FILES_DIFFER_FROM_CONTRACT', {'given': sorted(given), 'contract': sorted(declared_authority)})
    for name in sorted(declared_authority):
        wanted['authority/' + name] = ('file', given[name], declared_authority[name])

    # Model files: the contract, the plan and the old job's inventory must all agree.
    if sha_path(args.inventory) != INVENTORY_SHA:
        stop('MODEL_INVENTORY_FILE_CHANGED', args.inventory)
    rows = [row for row in read_json(args.inventory)['models'] if row['role'] == 'B']
    if len(rows) != 1 or rows[0]['revision'] != plan['revision']:
        stop('INVENTORY_MODEL_B_ROW')
    inventory = {row['filename']: {'bytes': row['bytes'], 'sha256': row['sha256']} for row in rows[0]['files']}
    snapshot = contract['model_cache']['snapshots']['B']
    if 'models/' + snapshot != plan['snapshot_path_in_payload']:
        stop('SNAPSHOT_PATH_DIFFERS_FROM_PLAN')
    names = sorted(plan['files'])
    declared_models = contract['model_cache']['files']
    if set(declared_models) != {snapshot + '/' + name for name in names}:
        stop('MODEL_FILE_LIST_DIFFERS_FROM_PLAN')
    for name in names:
        row = declared_models[snapshot + '/' + name]
        if not (row == plan['files'][name] == inventory.get(name)):
            stop('MODEL_FILE_PIN_DISAGREEMENT', name)
        wanted['models/' + snapshot + '/' + name] = ('old_zip', 'models/' + snapshot + '/' + name, row)
    model_bytes = sum(row['bytes'] for row in declared_models.values())
    if (len(declared_models), model_bytes) != (plan['file_count'], plan['total_bytes']):
        stop('MODEL_FILES_DO_NOT_ADD_UP_TO_THE_PLAN', (len(declared_models), model_bytes))

    total = sum(entry[2]['bytes'] for entry in wanted.values())
    if total + 1024 * 1024 > MAX_INPUT:
        stop('INPUT_OVER_THE_LIMIT', total)

    old_path = Path(args.old_input_zip)
    if old_path.stat().st_size != OLD_INPUT_BYTES:
        stop('OLD_INPUT_ZIP_SIZE_CHANGED', old_path.stat().st_size)
    target = out / 'input.zip'
    partial = out / 'input.zip.partial'
    if target.exists():
        stop('INPUT_ZIP_EXISTS', 'an input.zip is never overwritten; delete it on purpose first')
    if shutil.disk_usage(out).free < total + 64 * 1024 * 1024:
        stop('NOT_ENOUGH_FREE_DISK', shutil.disk_usage(out).free)
    if partial.exists():
        partial.unlink()

    done = False
    try:
        with zipfile.ZipFile(old_path, 'r') as old, \
                zipfile.ZipFile(partial, 'x', compression=zipfile.ZIP_STORED, allowZip64=True) as new:
            if len(old.infolist()) != OLD_INPUT_MEMBERS:
                stop('OLD_INPUT_ZIP_MEMBER_COUNT_CHANGED', len(old.infolist()))
            for name in wanted:
                kind, origin, expected = wanted[name]
                if kind == 'file':
                    with open(origin, 'rb') as incoming:
                        copy_stream(incoming, new, name, expected)
                else:
                    record = old.getinfo(origin)
                    if record.compress_type != zipfile.ZIP_STORED or record.file_size != expected['bytes']:
                        stop('OLD_MEMBER_NOT_STORED_OR_SIZE_DIFFERS', origin)
                    with old.open(record, 'r') as incoming:
                        copy_stream(incoming, new, name, expected)
        # Reopen the new zip and hash every member again, independently of the copy.
        with zipfile.ZipFile(partial, 'r') as new:
            entries = new.infolist()
            if [entry.filename for entry in entries] != list(wanted):
                stop('REOPEN_MEMBERSHIP_MISMATCH')
            for entry in entries:
                expected = wanted[entry.filename][2]
                value = hashlib.sha256()
                count = 0
                if entry.compress_type != zipfile.ZIP_STORED or entry.flag_bits & 1:
                    stop('REOPEN_MEMBER_NOT_STORED', entry.filename)
                with new.open(entry, 'r') as handle:
                    for chunk in iter(lambda: handle.read(CHUNK), b''):
                        count += len(chunk)
                        value.update(chunk)
                if count != expected['bytes'] or value.hexdigest() != expected['sha256']:
                    stop('REOPEN_MEMBER_DIFFERS', entry.filename)
        size = partial.stat().st_size
        if size > MAX_INPUT:
            stop('INPUT_OVER_THE_LIMIT', size)
        digest = sha_path(partial)
        os.replace(partial, target)
        done = True
    finally:
        if not done and partial.exists():
            partial.unlink()

    report = {
        'schema': 'casalescence/optionb/input-zip-build-receipt/v1',
        'job': contract.get('job'),
        'input_zip': {'path': str(target), 'bytes': size, 'sha256': digest},
        'input_zip_bytes_for_the_controller': size,
        'input_zip_sha256_for_the_controller': digest,
        'payload_manifest_sha256_for_the_controller': wanted['CONTRACT.json'][2]['sha256'],
        'members': {name: wanted[name][2] for name in wanted},
        'member_count': len(wanted),
        'model_files': len(declared_models),
        'model_bytes': model_bytes,
        'model_a_left_out': True,
        'old_input_zip': {'path': str(old_path), 'bytes': OLD_INPUT_BYTES, 'opened': 'read-only'},
        'made_by': {'program': Path(__file__).name, 'sha256': sha_path(__file__)},
    }
    text = json.dumps(report, indent=1, ensure_ascii=False) + '\n'
    receipt = out / 'INPUT_ZIP_BUILD_RECEIPT.json'
    with open(str(receipt) + '.partial', 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(text)
    os.replace(str(receipt) + '.partial', receipt)
    sys.stdout.write(text)


if __name__ == '__main__':
    main()
