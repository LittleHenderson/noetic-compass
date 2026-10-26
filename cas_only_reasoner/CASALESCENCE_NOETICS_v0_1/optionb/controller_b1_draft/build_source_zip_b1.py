"""Build source.zip for Option B job b1. Standard library only. Files only.

What it does, in plain words:
  1. Reads the seal file optionb/SEAL_OPTIONB.jsonl and checks its hash chain.
  2. Takes exactly the package files listed in FILE_FORMATS.md section 14.
     Each one must be in the seal, and its bytes must equal the hash in force.
     "In force" means: the latest seal line that lists the file (FILE_FORMATS.md 15.2).
  3. Adds the seal file as it stood after seal step 6, or after the last line
     6R_PROGRAMS_REPAIRED if there is one. Later lines are left out, so the
     pre-check job and the GPU job get the same package, byte for byte.
  4. Adds contracts/requirements.small-linux.txt (pinned hash) and a new
     BUNDLE_MANIFEST.json. The guest checks both by path during setup.
  5. Writes source.zip.partial, reopens and re-hashes it, then renames it.

It runs no project code, no model code, no AWS call and no outside service.
It needs a few MB of memory. It never edits a sealed file.

Run order for job b1 (each step on the laptop; no step calls AWS or an outside service):
  1. after seal step 6:   python -B build_source_zip_b1.py --out <package folder> --guest <the reviewed guest>
  2. the guest is final:  python -B build_contract_b1.py   --out <controller folder> --stamp-only
  3. the pre-check job runs on this same source.zip (its own builder and controller);
     its receipt is written to the seal file as step 7
  4. after seal step 7:   python -B build_contract_b1.py   --out <controller folder> --stamp-guest
  5.                      python -B build_input_zip_b1.py  --out <controller folder>
  6.                      python -B text_check_b1.py       --dir <controller folder> --write

Review round 1 (plan section 19.1):
  - After a repair line 6R_PROGRAMS_REPAIRED the package is new. Build it into a NEW folder.
    The old source.zip is evidence of the failed pre-check. This script never overwrites one.
  - Rehearsal, after seal step 5 and before seal step 6: give --seal <scratch copy of the seal file>.
    The scratch copy ends with the line that 'tools/ob_seal.py step 6 --dry-run' prints.
    A rehearsal package is never the package of the GPU job: build_contract_b1.py refuses a
    source.zip whose seal copy is not the start of the real seal file.

Amendments of 2026-10-05:
  - A10, the development test before seal step 1: give --study-root <made-up study folder>.
    That folder has the layout of the study folder and holds made-up data and its own made-up
    seal file. optionb/dry/build_dev_package.py makes it and then calls this script. The receipt
    then says made_up_study_root_never_for_a_seal_or_the_gpu_job: true.
  - A5: a tool-repair line may stand only after seal line 1 and before the line 3C. This script
    stops if the seal file holds one anywhere else.

Status: built by Claude, checked by a separate reviewer in one review round, never run before.
"""
import argparse
import ast
import hashlib
import json
import os
import stat
import sys
import zipfile
from pathlib import Path

STUDY_ROOT = 'C:/Users/wakil/OneDrive/Desktop/tksCAS/cas_only_reasoner/CASALESCENCE_NOETICS_v0_1'
PILOT_REQUIREMENTS = ('C:/Users/wakil/Documents/Codex/2026-10-03/task-2/casalescence_small_v0_2/'
                      'contracts/requirements.small-linux.txt')
# FILE_FORMATS.md section 14, in its own order. The seal file is handled apart.
SEAL_NAME = 'SEAL_OPTIONB.jsonl'
PACKAGE_FILES = (
    '08_OPTION_B_PLAN_v1_0.md',
    'PLAN_CONSTANTS.json',
    'FILE_FORMATS.md',
    SEAL_NAME,
    'tools/verdict.py',
    'job/runner_b1.py',
    'job/scorer_v0_1_1.py',
    'job/gate_b1.py',
    'job/analysis_b1.py',
    'job/scorer_examples_v0_1_1.json',
    'prompts/prompt_parts_practice.json',
    'prompts/prompt_parts_final.json',
    'keys_practice/keys_practice.json',
    'keys_practice/task_meta_practice.json',
    'keys_final/keys_final.json',
    'keys_final/task_meta_final.json',
)
# Review round 1: tools/verdict.py is one of the 16 package files (FILE_FORMATS.md section 14). job/analysis_b1.py
# needs its function content() for three views that the plan says are always printed. Seal step 1 gives the file
# the package path tools/verdict.py. A seal that does not is refused below; nothing is packed "if present".
# What the controller's builder adds beside that list, because the guest needs it.
REQUIREMENTS_NAME = 'contracts/requirements.small-linux.txt'
REQUIREMENTS_SHA = '6d9ee033baf3acbcecfbf8feb735a807025c141cac8e6060e480154c2c1c15b7'
REQUIREMENTS_BYTES = 403
MANIFEST_NAME = 'BUNDLE_MANIFEST.json'
# The package holds the seal as it stood after the last of these steps, or after the last
# program-repair line (FILE_FORMATS.md section 14).
SEAL_STEPS = ('1_PLAN_AND_SOURCES', '2_ROLE_NOTES', '3A_PRACTICE_QUESTIONS_AND_KEYS',
              '3B_PRACTICE_SET_FIXED', '3C_FINAL_QUESTIONS_AND_KEYS', '4_ORDINARY_NOTES',
              '5_PROMPT_PARTS_AND_REMOVAL_LOG', '6_PROGRAMS')
# Review round 1 (FILE_FORMATS.md section 15.2): the two repair lines, and how many program repairs may exist.
PROGRAM_REPAIR, TOOL_REPAIR = '6R_PROGRAMS_REPAIRED', 'TR_TOOLS_REPAIRED'
MAX_PROGRAM_REPAIRS = 2
# Amendment A5: the line that closes the window of a tool repair.
FINAL_LINE = '3C_FINAL_QUESTIONS_AND_KEYS'
ZIP_DATE = (2026, 10, 5, 0, 0, 0)


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


def safe_name(name):
    """The same path rule the guest applies to every zip member."""
    return (isinstance(name, str) and name != '' and '\\' not in name and '\x00' not in name
            and ':' not in name and not name.startswith('/')
            and all(part not in ('', '.', '..') for part in name.split('/')))


def guest_literals(path):
    """Read plain constants from the guest by parsing it. The guest is never run."""
    tree = ast.parse(Path(path).read_bytes().decode('utf-8'))
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                found[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, SyntaxError, TypeError):
                pass
    return found


def read_seal(path):
    """Return (lines as bytes without LF, parsed lines). Checks numbering and the hash chain."""
    raw = Path(path).read_bytes()
    if not raw.endswith(b'\n') or b'\r' in raw:
        stop('SEAL_LINE_ENDS', 'the seal file must use LF line ends and end with one LF')
    lines = raw[:-1].split(b'\n')
    rows = []
    previous = None
    for number, line in enumerate(lines, 1):
        try:
            row = json.loads(line.decode('utf-8'))
        except ValueError as error:
            stop('SEAL_LINE_NOT_JSON', 'line %d: %s' % (number, error))
        if row.get('n') != number:
            stop('SEAL_NUMBERING', 'line %d holds n=%r' % (number, row.get('n')))
        if row.get('previous_line_sha256') != previous:
            stop('SEAL_CHAIN_BROKEN', 'line %d' % number)
        previous = sha_bytes(line)
        rows.append(row)
    return lines, rows


def main():
    parser = argparse.ArgumentParser(description='Build source.zip for Option B job b1.')
    parser.add_argument('--out', default=str(Path(__file__).resolve().parent),
                        help='folder that receives source.zip (default: the folder of this script)')
    parser.add_argument('--study-root', default=STUDY_ROOT)
    parser.add_argument('--requirements', default=PILOT_REQUIREMENTS,
                        help='the pinned requirements file of the pilot package')
    parser.add_argument('--guest', default=None, help='worker_v02.py (default: <out>/worker_v02.py)')
    parser.add_argument('--seal', default=None,
                        help='rehearsal only: a scratch copy of the seal file that ends with the line that '
                             "'tools/ob_seal.py step 6 --dry-run' prints (default: the real seal file)")
    args = parser.parse_args()

    out = Path(args.out)
    root = Path(args.study_root)
    guest_path = Path(args.guest) if args.guest else out / 'worker_v02.py'
    caps = guest_literals(guest_path)
    for name in ('SOURCE_UNPACKED_CAP', 'SOURCE_FILE_CAP', 'REQUIREMENTS_SHA'):
        if name not in caps:
            stop('GUEST_CONSTANT_MISSING', name)
    if caps['REQUIREMENTS_SHA'] != REQUIREMENTS_SHA:
        stop('REQUIREMENTS_PIN_DIFFERS_FROM_GUEST')

    # 1. The seal, up to and including step 6 or the last program-repair line.
    real_seal = root / 'optionb' / SEAL_NAME
    seal_path = Path(args.seal) if args.seal else real_seal
    rehearsal = seal_path.resolve() != real_seal.resolve()
    lines, rows = read_seal(seal_path)
    steps = [row.get('step') for row in rows]
    # Order rule of FILE_FORMATS.md 15.2: leave the repair lines out. What is left must be steps 1 to 6
    # in order, each once, and after them nothing but one step 7 line at most.
    plain = [step for step in steps if step not in (PROGRAM_REPAIR, TOOL_REPAIR)]
    if SEAL_STEPS[-1] not in steps:
        stop('SEAL_STEP_6_PROGRAMS_NOT_WRITTEN_YET', steps)
    if (steps[0] != SEAL_STEPS[0] or plain[:len(SEAL_STEPS)] != list(SEAL_STEPS)
            or plain[len(SEAL_STEPS):] not in ([], ['7_PRECHECK'])):
        stop('SEAL_STEPS_NOT_AS_IN_FILE_FORMATS_15', steps)
    six = steps.index(SEAL_STEPS[-1])
    seven = steps.index('7_PRECHECK') if '7_PRECHECK' in steps else len(steps)
    repairs = [index for index, step in enumerate(steps) if step == PROGRAM_REPAIR]
    # A program repair stands after step 6 and before step 7, at most twice.
    if len(repairs) > MAX_PROGRAM_REPAIRS or any(not six < index < seven for index in repairs):
        stop('PROGRAM_REPAIR_LINES_NOT_AS_IN_FILE_FORMATS_15_2', steps)
    # Amendment A5: a tool repair is allowed only while no final question exists. So a tool-repair line
    # stands after line 1 and before the line 3C.
    final = steps.index(FINAL_LINE)
    if any(not 0 < index < final for index, step in enumerate(steps) if step == TOOL_REPAIR):
        stop('TOOL_REPAIR_LINE_OUTSIDE_ITS_WINDOW_FILE_FORMATS_15_2', steps)
    if rehearsal:
        # Plan section 19.1: a rehearsal runs after seal step 5 and before seal step 6. Its seal is the real
        # seal file as it stands, plus exactly one line: the step 6 line of the dry run.
        real_raw = real_seal.read_bytes()
        scratch_raw = seal_path.read_bytes()
        if (repairs or seven != len(steps) or six != len(steps) - 1 or not scratch_raw.startswith(real_raw)
                or scratch_raw[len(real_raw):].count(b'\n') != 1):
            stop('REHEARSAL_SEAL_MUST_BE_THE_REAL_SEAL_FILE_PLUS_THE_STEP_6_DRY_RUN_LINE', steps)
    kept = (repairs[-1] if repairs else six) + 1
    seal_bytes = b''.join(line + b'\n' for line in lines[:kept])

    # 2. The sealed package files: every one must be in the seal, and its bytes must be the ones in force.
    in_force = {}
    for row in rows[:kept]:
        for entry in row.get('files', []):
            record = (entry.get('package_path'), entry['bytes'], entry['sha256'])
            earlier = in_force.get(entry['path'])
            if earlier is not None:
                # Only a repair line may give a path other bytes, and it may not move the file inside the package.
                if row.get('step') not in (PROGRAM_REPAIR, TOOL_REPAIR) and earlier != record:
                    stop('PATH_SEALED_AGAIN_WITH_OTHER_CONTENT_OUTSIDE_A_REPAIR_LINE', entry['path'])
                if earlier[0] != record[0]:
                    stop('REPAIR_LINE_CHANGED_A_PACKAGE_PATH', entry['path'])
            in_force[entry['path']] = record
    sealed = {}
    for relative, (target, size, digest) in in_force.items():
        if target is None:
            continue
        if target in sealed:
            stop('TWO_SEALED_FILES_SHARE_ONE_PACKAGE_PATH', target)
        sealed[target] = (relative, size, digest)
    wanted = set(PACKAGE_FILES) - {SEAL_NAME}
    if set(sealed) != wanted:
        stop('SEALED_PACKAGE_LIST_DIFFERS_FROM_FILE_FORMATS_14',
             {'in_seal_not_in_list': sorted(set(sealed) - wanted),
              'in_list_not_in_seal': sorted(wanted - set(sealed))})
    members = {}
    for target in sorted(wanted):
        relative, size, digest = sealed[target]
        data = (root / relative).read_bytes()
        if len(data) != size or sha_bytes(data) != digest:
            stop('FILE_DIFFERS_FROM_SEAL', relative)
        members[target] = data
    members[SEAL_NAME] = seal_bytes

    # 3. The pinned requirements file.
    requirements = Path(args.requirements).read_bytes()
    if len(requirements) != REQUIREMENTS_BYTES or sha_bytes(requirements) != REQUIREMENTS_SHA:
        stop('REQUIREMENTS_FILE_DIFFERS_FROM_PIN', args.requirements)
    members[REQUIREMENTS_NAME] = requirements

    # 4. The bundle manifest. No time and no machine path, so its bytes can be rebuilt.
    manifest = {
        'schema': 'casalescence/optionb/bundle-manifest/v1',
        'what': 'Every other file of source.zip for Option B job b1, with its size and sha256.',
        'seal': {'lines': kept, 'last_step': steps[kept - 1], 'last_line_sha256': sha_bytes(lines[kept - 1])},
        'requirements_sha256': REQUIREMENTS_SHA,
        'files': [{'path': name, 'bytes': len(members[name]), 'sha256': sha_bytes(members[name])}
                  for name in sorted(members)],
    }
    members[MANIFEST_NAME] = (json.dumps(manifest, indent=1, ensure_ascii=False) + '\n').encode('utf-8')

    # 5. The guest's caps and path rule.
    unpacked = sum(len(data) for data in members.values())
    for name in members:
        if not safe_name(name):
            stop('UNSAFE_MEMBER_NAME', name)
    if len(members) > caps['SOURCE_FILE_CAP'] or unpacked > caps['SOURCE_UNPACKED_CAP']:
        stop('SOURCE_ZIP_OVER_GUEST_CAPS', {'files': len(members), 'unpacked_bytes': unpacked,
                                            'file_cap': caps['SOURCE_FILE_CAP'],
                                            'byte_cap': caps['SOURCE_UNPACKED_CAP']})

    # 6. Write .partial, reopen, re-hash, then rename. Stored, fixed date: same bytes every time.
    target = out / 'source.zip'
    partial = out / 'source.zip.partial'
    if partial.exists():
        partial.unlink()
    with zipfile.ZipFile(partial, 'x', compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(members):
            info = zipfile.ZipInfo(name, date_time=ZIP_DATE)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, members[name])
    with zipfile.ZipFile(partial, 'r') as archive:
        names = archive.namelist()
        if sorted(names) != sorted(members) or len(names) != len(set(names)):
            stop('REOPEN_MEMBERSHIP_MISMATCH')
        for name in names:
            if archive.read(name) != members[name]:
                stop('REOPEN_CONTENT_MISMATCH', name)
    digest = sha_path(partial)
    size = partial.stat().st_size
    if target.exists():
        if sha_path(target) != digest:
            partial.unlink()
            stop('SOURCE_ZIP_EXISTS_WITH_OTHER_CONTENT',
                 'delete it on purpose if a new package is wanted; the pre-check job and the GPU job must share one')
        partial.unlink()
        state = 'UNCHANGED_SAME_BYTES_ALREADY_THERE'
    else:
        os.replace(partial, target)
        state = 'WRITTEN'

    report = {
        'schema': 'casalescence/optionb/source-zip-build-receipt/v1',
        'state': state,
        'source_zip': {'path': str(target), 'bytes': size, 'sha256': digest},
        'members': len(members),
        'unpacked_bytes': unpacked,
        'guest_caps': {'files': caps['SOURCE_FILE_CAP'], 'unpacked_bytes': caps['SOURCE_UNPACKED_CAP']},
        'bundle_manifest_sha256': sha_bytes(members[MANIFEST_NAME]),
        'requirements_sha256': REQUIREMENTS_SHA,
        'seal_lines_in_package': kept,
        'seal_lines_on_disk': len(lines),
        'seal_file_read': str(seal_path),
        'rehearsal_package_never_for_the_gpu_job': rehearsal,
        # Amendment A10: true when --study-root named another folder than the study folder (a development-test package).
        'made_up_study_root_never_for_a_seal_or_the_gpu_job': root.resolve() != Path(STUDY_ROOT).resolve(),
        'program_repair_lines_in_package': len(repairs),
        'last_seal_step_in_package': steps[kept - 1],
        'member_sizes': {name: len(members[name]) for name in sorted(members)},
        'made_by': {'program': Path(__file__).name, 'sha256': sha_path(__file__)},
    }
    text = json.dumps(report, indent=1, ensure_ascii=False) + '\n'
    receipt = out / 'SOURCE_ZIP_BUILD_RECEIPT.json'
    with open(str(receipt) + '.partial', 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(text)
    os.replace(str(receipt) + '.partial', receipt)
    sys.stdout.write(text)


if __name__ == '__main__':
    main()
