"""Option B: the append-only seal file optionb/SEAL_OPTIONB.jsonl.

Plan: 08_OPTION_B_PLAN_v1_0.md, sections 11.1, 19.1 and 21. File formats: optionb/FILE_FORMATS.md,
sections 15 and 19.

A seal is one line in the seal file. The line holds the sha256 and the size of every file of one build
step, and the sha256 of the line before it. A line is written before the next build step starts.
Lines are only ever added at the end. This tool never rewrites, shortens or deletes the seal file.

Plain Python, standard library only. No model, no network, no key.

The steps, in the only order this tool allows
  1   1_PLAN_AND_SOURCES              the plan, PLAN_CONSTANTS.json, FILE_FORMATS.md, the six source
                                      files of plan section 3, elig/exclusions.json, elig/eligibility.json,
                                      and the eleven laptop tools tools/ob_*.py. The six sources are the
                                      names under seal.sources_sealed_in_step_1 (amendment A13). The sixth
                                      holds the canonical sayings and lies outside the study folder; its
                                      path is ../../docs/CAS_FOUNDATIONAL_CLARIFICATIONS.md, counted from
                                      the study folder, and its package_path is null.
  2   2_ROLE_NOTES                    notes_role/role_notes.json, notes_role/owner_sample_20.json
  3A  3A_PRACTICE_QUESTIONS_AND_KEYS  every practice file of FILE_FORMATS.md sections 4 to 7.1
  3B  3B_PRACTICE_SET_FIXED           select/split_fixed.json
  3C  3C_FINAL_QUESTIONS_AND_KEYS     every final file of sections 4 to 7.1
  4   4_ORDINARY_NOTES                every file of sections 8 and 9, both sets
  5   5_PROMPT_PARTS_AND_REMOVAL_LOG  the files of sections 10, 11 and 12
  6   6_PROGRAMS                      the five job files of section 13
  7   7_PRECHECK                      the owner's status table, and five values from the pre-check job

Repair lines (review round 1; narrowed by amendment A5; FILE_FORMATS.md section 15.2). Two more kinds
of line may be added. Each has a window. Outside its window this tool writes no repair line and stops
with REPAIR_OUTSIDE_ITS_WINDOW.
  6R_PROGRAMS_REPAIRED   only after a failed pre-check job on the sealed package and before 7_PRECHECK.
                         So before any call to model B. The line 6_PROGRAMS exists. The kept receipt
                         of the failed job says precheck_kind SEALED_PACKAGE and the status
                         PRECHECK_COMPLETE_WITH_FINDINGS or STOPPED_NO_RETRY, and it names another
                         source.zip than the receipt of every earlier 6R line (operator decision C4 of
                         2026-10-05, round 3). At most 2. Only the five job files.
  TR_TOOLS_REPAIRED      only after line 1 and while no final question exists: no final file lies
                         under questions/, checks/, solve/ or select/, and the seal file has no line
                         3C_FINAL_QUESTIONS_AND_KEYS. Only tools/ob_*.py.
After those points a fault means: stop, report, a new reviewed plan version.
A repair line needs the folder optionb/repairs/<repair id>/ with the old copy of each changed file,
diff.txt and review.json (verdict REPAIR_ALLOWED, written by a reviewer who did not write the change).
A repair changes program code only. It never changes the plan, the constants, a brief, a threshold,
a key, a task or a note: any other sealed file that differs is a refusal.

The hash in force. For a path that more than one line lists, the latest line gives the size and the
sha256 in force. Only a repair line may list a path that an earlier line lists. Every check "no
sealed file has changed" compares each path with its values in force.

Every step REFUSES, and writes nothing, when
  - the seal file is damaged, or its chain of line hashes is broken;
  - it is not the next step in the order above. So a step with a missing earlier step is refused,
    and a step that was already written is refused;
  - a sealed file is missing or differs from its values in force (size or sha256);
  - one of its own named files is missing or empty, or a half-written ".partial" file lies beside them;
  - a JSON file of the step names, under "inputs", a file sealed earlier with another sha256.

More refusals, each taken from a rule of the plan
  step 1   a source file does not match the hash pinned in PLAN_CONSTANTS.json; the counts in
           eligibility.json are not the plan's counts; ANY QUESTION FILE ALREADY EXISTS; one of the
           eleven tools is missing, or a tools/ob_*.py file is not in the plan's list; the eligibility
           files were not made by the tools/ob_eligibility.py that this step seals; the Claude model id
           is not pinned (outside_services.claude_solver.model_id is null).
  step 2   any question file already exists (the role notes are sealed before any question exists);
           the role notes were not built from the sealed eligibility file and the sealed guide.
           Amendment A13: canon.sayings_sha256 of the role notes is not the sha256 of the sealed
           source of the sayings, or one of the two files of the step does not name that source
           under "inputs" with that sha256.
  step 3A  a final question file exists; practice ordinary notes exist; the writer is not finished;
           THE RESERVE RULE IS NOT FINISHED (both reserve targets met, or all reserve settings used).
  step 3B  a final question file exists; one of the two practice launch floors is not met.
  step 3C  final ordinary notes exist; the writer is not finished.
  step 4   the support check is not finished: a passage has a status other than ALL_PASS,
           DROPPED_SECOND_FAILURE or the status of ordinary_notes.not_written_status
           (DROPPED_NOTE_NOT_WRITTEN: a note the writer could not produce; amendment A13, small faults).
  step 5   the removal log says the launch floor is not met.
  step 7   the pre-check did not end with the pass status, or it is not a pre-check record; the
           owner's status table is missing or breaks a limit of spec_sheet_status.limits.
           Amendment A8: the job's receipt does not say precheck_kind SEALED_PACKAGE and status
           PRECHECK_COMPLETE_SELFTEST_PASS; its block seal_step_7_values is not the five values this
           step works out; the SEAL_OPTIONB.jsonl inside the given source.zip is not, byte for byte,
           the real seal file up to its last program line. So a rehearsal, or a test on made-up
           data, can never be sealed as step 7.
A failed floor or a failed pre-check is a failure. It is reported. It is not sealed as a go.

"Question file" means any file under optionb/questions/, checks/, solve/, select/, prompts/,
keys_practice/, keys_final/ or review/, and any file elsewhere under optionb/ whose name starts with
raw_questions_, writer_calls_ or writer_state_. The scratch folder optionb/dry/ is not looked at for
this rule; files there with such names are counted and printed, so that the operator sees them.

Usage
  ob_seal.py status                     the lines written so far, the next step, and a full re-hash
  ob_seal.py verify                     re-hash every sealed file; exit 0 only if nothing changed
  ob_seal.py step 1                     write seal step 1 (also: 2, 3A, 3B, 3C, 4, 5, 6)
  ob_seal.py step 7 --receipt FILE --selftest-json FILE --source-zip FILE
                                        --receipt is the job's supervisor_receipt.json, unchanged
  ob_seal.py step N --dry-run           run every check, print the line, write nothing
  ob_seal.py repair 6R1 [--source-zip FILE] [--dry-run]
                                        write a 6R_PROGRAMS_REPAIRED line from optionb/repairs/6R1/
  ob_seal.py repair TR1 [--deleted PATH=SHA256 ...] [--dry-run]
                                        write a TR_TOOLS_REPAIRED line from optionb/repairs/TR1/
  ob_seal.py status-word --result FILE  print the outcome code of RESULT.json and its status word
  ob_seal.py status-word --no-result-file
  ob_seal.py status-word --code RESULT_UNREADABLE

For other programs (FILE_FORMATS.md section 1: "Every program first checks that the seal steps it
depends on exist and that the sealed files have not changed."):
  import ob_seal
  ob_seal.require_steps(project_folder, ['1_PLAN_AND_SOURCES'])      # raises ob_seal.Refused

Exit code 0: done. Exit code 2: REFUSED (or, for status-word, the code is not in the table); the
reason is printed; nothing was written.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True   # leave no cache folder beside the frozen tools

TOOLS = Path(__file__).resolve().parent
PROJECT = TOOLS.parent
PROGRAM = 'tools/ob_seal.py'
SCHEMA = 'casalescence/optionb/seal-step/v1'
REVIEW_SCHEMA = 'casalescence/optionb/repair_review/v1'
TABLE_SCHEMA = 'casalescence/optionb/outcome_status_table/v1'
SEAL_NAME = 'SEAL_OPTIONB.jsonl'
SCRATCH_FOLDER = 'dry'
REPAIR_FOLDER = 'repairs'

ORDER = ('1_PLAN_AND_SOURCES', '2_ROLE_NOTES', '3A_PRACTICE_QUESTIONS_AND_KEYS', '3B_PRACTICE_SET_FIXED',
         '3C_FINAL_QUESTIONS_AND_KEYS', '4_ORDINARY_NOTES', '5_PROMPT_PARTS_AND_REMOVAL_LOG', '6_PROGRAMS', '7_PRECHECK')
SHORT = {name.split('_')[0]: name for name in ORDER}
# The two repair lines of FILE_FORMATS.md section 15.2. The same names stand in PLAN_CONSTANTS.json under
# repairs.seal_steps; check_repair_names() refuses when the two disagree.
REPAIR_JOB = '6R_PROGRAMS_REPAIRED'
REPAIR_TOOLS = 'TR_TOOLS_REPAIRED'
REPAIR_STEPS = (REPAIR_JOB, REPAIR_TOOLS)
REPAIR_KIND = {'6R': ('JOB_PROGRAMS', REPAIR_JOB), 'TR': ('TOOLS', REPAIR_TOOLS)}
REPAIR_ALLOWED = 'REPAIR_ALLOWED'
# Amendment A5: the refusal for a repair line outside its window. The same name stands in PLAN_CONSTANTS.json
# under repairs.outside_the_window_refusal; check_repair_names() refuses when the two disagree.
OUTSIDE_WINDOW = 'REPAIR_OUTSIDE_ITS_WINDOW'
# Operator decision C4 of 2026-10-05, round 3 (FILE_FORMATS.md section 15.2): the two receipt statuses of a failed
# pre-check job. Only a kept receipt with one of them opens the window of a 6R line. A receipt with another status
# does not: RUNNING, for example, is a job that never finished.
FAILED_PRECHECK_STATUSES = ('PRECHECK_COMPLETE_WITH_FINDINGS', 'STOPPED_NO_RETRY')
PROGRAM_LINES = ('6_PROGRAMS', REPAIR_JOB)       # the two kinds of program line (FILE_FORMATS.md section 15.1)
FINAL_QUESTIONS_STEP = '3C_FINAL_QUESTIONS_AND_KEYS'
SEAL_COPY_BYTES_MAX = 16 * 1024 * 1024          # the seal copy inside source.zip is read whole; a real one is far smaller

# FILE_FORMATS.md section 15: "the six source files of plan section 3". Their names are read from PLAN_CONSTANTS.json,
# seal.sources_sealed_in_step_1 (amendment A13). These five were sealed before A13 and must still be among them;
# the source of the sayings (role_notes.sayings_source_key) must be among them too. See sealed_sources().
SOURCES_ALWAYS_SEALED = ('labels_team_a', 'labels_team_b', 'passages', 'labeling_guide', 'verdict_program')
ELIGIBILITY_TOOL = 'tools/ob_eligibility.py'
# FILE_FORMATS.md section 9.5: with these two statuses, and the one named in ordinary_notes.not_written_status,
# the support check of a passage is finished.
SUPPORT_FINISHED = ('ALL_PASS', 'DROPPED_SECOND_FAILURE')
# FILE_FORMATS.md sections 4 to 7.1 live in these folders; a file belongs to a set by the set name in its file name.
QUESTION_FOLDERS = ('questions', 'checks', 'solve', 'select')
# Folders that can only hold something once questions exist.
AFTER_QUESTION_FOLDERS = ('prompts', 'keys_practice', 'keys_final', 'review')
QUESTION_NAME_STARTS = ('raw_questions_', 'writer_calls_', 'writer_state_')
NOTE_FOLDERS = ('notes_ord', 'support')
# Plan v1.1: the writer passes (p1, p2, p3) come from PLAN_CONSTANTS.json; see passes_of(). No pass list is fixed here.
# FILE_FORMATS.md section 13: the five job files.
JOB_FILES = ('runner_b1.py', 'scorer_v0_1_1.py', 'gate_b1.py', 'analysis_b1.py', 'scorer_examples_v0_1_1.json')
# FILE_FORMATS.md section 14: the files the job package holds, by their path under optionb/.
# (tools/verdict.py is the one package file outside optionb/; see package_path().)
PACKAGE_UNDER_WORK = (('PLAN_CONSTANTS.json', 'FILE_FORMATS.md')
                      + tuple('job/' + name for name in JOB_FILES)
                      + ('prompts/prompt_parts_practice.json', 'prompts/prompt_parts_final.json',
                         'keys_practice/keys_practice.json', 'keys_practice/task_meta_practice.json',
                         'keys_final/keys_final.json', 'keys_final/task_meta_final.json'))
SELFTEST_SCHEMA = 'casalescence/optionb/selftest/v1'
# Limit L4 of spec_sheet_status.limits names these two words. check_status_table() refuses when the
# limit text in PLAN_CONSTANTS.json does not name both, so the two can not drift apart unseen.
NEVER_FOR_EXPLORATORY = ('VALIDATED', 'LICENSED')
NO_RESULT_FILE = 'NO_RESULT_FILE'

# The custody note of each step. Plan section 10: this is custody by rule and by record, not by lock.
WHO = {
    '1_PLAN_AND_SOURCES': 'By rule, not by lock: the operator (Claude Code) and the owner. No question, no key and no note exists yet.',
    '2_ROLE_NOTES': 'By rule, not by lock: the operator (Claude Code) and the owner; no outside model; no question writer.',
    '3A_PRACTICE_QUESTIONS_AND_KEYS': 'By rule, not by lock: the operator (Claude Code) and the owner. The question writer got fenced passages and the question brief only. The key solvers got passage, question and options only. No note writer and no note checker.',
    '3B_PRACTICE_SET_FIXED': 'By rule, not by lock: the operator (Claude Code) and the owner.',
    '3C_FINAL_QUESTIONS_AND_KEYS': 'By rule, not by lock: the operator (Claude Code) and the owner. The question writer got fenced passages and the question brief only. The key solvers got passage, question and options only. No note writer and no note checker.',
    '4_ORDINARY_NOTES': 'By rule, not by lock: the operator (Claude Code) and the owner. The ordinary-note writer got one passage and its brief only. The note checker got passage and note only.',
    '5_PROMPT_PARTS_AND_REMOVAL_LOG': 'By rule, not by lock: the operator (Claude Code), the owner and the plan reviewer. In the job, no stage that calls model B on final tasks is given the keys_final folder.',
    '6_PROGRAMS': 'By rule, not by lock: the operator (Claude Code), the owner and the plan reviewer.',
    '7_PRECHECK': 'By rule, not by lock: the operator (Claude Code) and the owner.',
    REPAIR_JOB: 'By rule, not by lock: the operator (Claude Code), the owner and the repair reviewer.',
    REPAIR_TOOLS: 'By rule, not by lock: the operator (Claude Code), the owner and the repair reviewer.',
}


class Refused(Exception):
    """A refusal. main() prints it and exits with code 2. Nothing is written."""

    def __init__(self, code, detail):
        Exception.__init__(self, '%s: %s' % (code, detail))
        self.code = code
        self.detail = detail


# ----------------------------------------------------------------------------- small helpers

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def file_facts(path):
    """(bytes, sha256) of one file, read in pieces."""
    digest, size = hashlib.sha256(), 0
    with open(path, 'rb') as handle:
        while True:
            piece = handle.read(1 << 20)
            if not piece:
                break
            digest.update(piece)
            size += len(piece)
    return size, digest.hexdigest()


def load_constants(project):
    path = Path(project) / 'optionb' / 'PLAN_CONSTANTS.json'
    if not path.is_file():
        raise Refused('CONSTANTS_MISSING', '%s was not found' % path)
    return json.loads(path.read_bytes().decode('utf-8'))


def work_name(constants):
    return constants['work_folder']


def seal_path(project, constants=None):
    constants = constants or load_constants(project)
    return Path(project) / work_name(constants) / SEAL_NAME


def load_json(project, relative):
    path = Path(project) / relative
    try:
        return json.loads(path.read_bytes().decode('utf-8'))
    except (OSError, ValueError) as error:
        raise Refused('FILE_NOT_READABLE', '%s is not readable JSON (%s)' % (relative, type(error).__name__))


def files_under(project, relative_folder):
    """Every file under one folder, as sorted paths relative to the project, with forward slashes."""
    base = Path(project) / relative_folder
    if not base.is_dir():
        return []
    return sorted(p.relative_to(project).as_posix() for p in base.rglob('*') if p.is_file())


def has_set(name, set_name):
    """True when a file name carries the set name as a whole part: ..._practice.json, ..._final_p1.jsonl."""
    return re.search(r'_%s(?=[_.])' % re.escape(set_name), name) is not None


def whole(value):
    """A count read from a JSON file, as a whole number. Anything that is not one counts as 0."""
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


# ----------------------------------------------------------------------------- reading and checking the seal

def read_seal_bytes(project, constants=None):
    path = seal_path(project, constants)
    return path.read_bytes() if path.is_file() else b''


def read_seal(project, constants=None):
    """The parsed lines of the seal file. Refuses when the file is damaged or its chain is broken."""
    return parse_seal(read_seal_bytes(project, constants))


def parse_seal(data):
    """The lines held in the bytes of a seal file, with the chain and the order rule checked.

    Order rule (FILE_FORMATS.md section 15.2): leave the repair lines out; what is left must be the
    nine steps in their order, or a start of that order. A 6R line stands after 6_PROGRAMS and before
    7_PRECHECK. A TR line stands after line 1 and before 3C_FINAL_QUESTIONS_AND_KEYS (amendment A5).
    Only a repair line may list a path again.
    """
    if not data:
        return []
    if not data.endswith(b'\n') or b'\r' in data:
        raise Refused('SEAL_FILE_DAMAGED', 'the seal file does not end with one LF, or it holds a CR')
    lines, previous, plain, listed = [], None, 0, set()
    after_programs = ORDER.index('6_PROGRAMS') + 1
    after_final_questions = ORDER.index(FINAL_QUESTIONS_STEP) + 1
    for place, raw in enumerate(data[:-1].split(b'\n')):
        try:
            line = json.loads(raw.decode('utf-8'))
        except ValueError:
            raise Refused('SEAL_FILE_DAMAGED', 'line %d is not JSON' % (place + 1))
        if not isinstance(line, dict) or line.get('schema') != SCHEMA:
            raise Refused('SEAL_FILE_DAMAGED', 'line %d does not have the schema %s' % (place + 1, SCHEMA))
        step = line.get('step')
        if line.get('n') != place + 1:
            raise Refused('SEAL_CHAIN_BROKEN', 'line %d should carry n=%d' % (place + 1, place + 1))
        if step in REPAIR_STEPS:
            if place == 0:
                raise Refused('SEAL_CHAIN_BROKEN', 'line 1 is a repair line. A repair line stands after line 1.')
            if step == REPAIR_JOB and plain != after_programs:
                raise Refused('SEAL_CHAIN_BROKEN', 'line %d is a %s line. It may stand only after 6_PROGRAMS and before 7_PRECHECK.' % (place + 1, REPAIR_JOB))
            if step == REPAIR_TOOLS and plain >= after_final_questions:
                raise Refused('SEAL_CHAIN_BROKEN', 'line %d is a %s line. It may stand only before %s.' % (place + 1, REPAIR_TOOLS, FINAL_QUESTIONS_STEP))
        else:
            if plain >= len(ORDER) or step != ORDER[plain]:
                raise Refused('SEAL_CHAIN_BROKEN', 'line %d should be step %s or a repair line; it is %r'
                              % (place + 1, ORDER[plain] if plain < len(ORDER) else '(none: every step is written)', step))
            plain += 1
        if line.get('previous_line_sha256') != previous:
            raise Refused('SEAL_CHAIN_BROKEN', 'line %d does not carry the sha256 of the line before it' % (place + 1))
        if not isinstance(line.get('files'), list) or not isinstance(line.get('values'), dict):
            raise Refused('SEAL_FILE_DAMAGED', 'line %d has no files list or no values object' % (place + 1))
        for item in line['files']:
            if not isinstance(item, dict) or not isinstance(item.get('path'), str):
                raise Refused('SEAL_FILE_DAMAGED', 'line %d lists a file without a path' % (place + 1))
            if item['path'] in listed and step not in REPAIR_STEPS:
                raise Refused('SEAL_FILE_DAMAGED', 'line %d lists %s, which an earlier line lists. Only a repair line may do that.' % (place + 1, item['path']))
            listed.add(item['path'])
        previous = sha256_bytes(raw)
        lines.append(line)
    return lines


def plain_steps(lines):
    """The nine-step names written so far, in order. Repair lines are left out."""
    return [line['step'] for line in lines if line['step'] not in REPAIR_STEPS]


def files_in_force(lines):
    """{path: record} of every sealed file. For a path that more than one line lists, the latest line counts.

    The record is the file entry of that line (path, package_path, bytes, sha256) plus the step name.
    """
    force = {}
    for line in lines:
        for item in line['files']:
            force[item['path']] = dict(item, step=line['step'])
    return force


def changed_files(project, lines):
    """Every sealed file that is missing or no longer has its size and sha256 in force."""
    problems = []
    for path, item in sorted(files_in_force(lines).items()):
        target = Path(project) / path
        if not target.is_file():
            problems.append('%s (step %s): MISSING' % (path, item['step']))
            continue
        size, digest = file_facts(target)
        if size != item['bytes'] or digest != item['sha256']:
            problems.append('%s (step %s): CHANGED, sealed %d bytes %s, now %d bytes %s'
                            % (path, item['step'], item['bytes'], item['sha256'], size, digest))
    return problems


def sealed_hashes(lines):
    """{path: sha256 in force} of every file in the given lines."""
    return {path: item['sha256'] for path, item in files_in_force(lines).items()}


def require_steps(project, steps, constants=None):
    """For other programs: the named steps exist and no sealed file has changed. Returns the lines."""
    project = Path(project)
    lines = read_seal(project, constants)
    have = [line['step'] for line in lines]
    for step in steps:
        name = SHORT.get(step, step)
        if name not in have:
            raise Refused('SEAL_STEP_MISSING', 'seal step %s has not been written' % name)
    problems = changed_files(project, lines)
    if problems:
        raise Refused('SEALED_FILE_CHANGED', '; '.join(problems))
    return lines


def has_step(project, step, constants=None):
    name = SHORT.get(step, step)
    return any(line['step'] == name for line in read_seal(Path(project), constants))


def check_repair_names(constants):
    """The repair line names of this tool are the ones PLAN_CONSTANTS.json gives."""
    named = constants.get('repairs', {}).get('seal_steps', {})
    if named.get('job_programs') != REPAIR_JOB or named.get('tools') != REPAIR_TOOLS:
        raise Refused('CONSTANTS_SHAPE', 'PLAN_CONSTANTS.json repairs.seal_steps does not name %s and %s' % (REPAIR_JOB, REPAIR_TOOLS))
    if constants.get('repairs', {}).get('outside_the_window_refusal') != OUTSIDE_WINDOW:
        raise Refused('CONSTANTS_SHAPE', 'PLAN_CONSTANTS.json repairs.outside_the_window_refusal is not %s' % OUTSIDE_WINDOW)


# ----------------------------------------------------------------------------- rules shared by steps

def question_files(project, work):
    """(files that count as question files, look-alikes in the scratch folder that do not count)."""
    counted, scratch = [], []
    scratch_prefix = '%s/%s/' % (work, SCRATCH_FOLDER)
    folders = tuple('%s/%s/' % (work, name) for name in QUESTION_FOLDERS + AFTER_QUESTION_FOLDERS)
    for relative in files_under(project, work):
        name = relative.rsplit('/', 1)[-1]
        if relative.startswith(scratch_prefix):
            if name.startswith(QUESTION_NAME_STARTS):
                scratch.append(relative)
        elif relative.startswith(folders) or name.startswith(QUESTION_NAME_STARTS):
            counted.append(relative)
    return counted, scratch


def refuse_if_questions_exist(ctx, why):
    counted, scratch = question_files(ctx['project'], ctx['work'])
    if counted:
        raise Refused('QUESTION_FILE_EXISTS', '%s Found %d: %s' % (why, len(counted), ', '.join(counted[:12]) + (' ...' if len(counted) > 12 else '')))
    if scratch:
        ctx['notes'].append('NOTE: %d file(s) with question-file names lie in the scratch folder %s/%s/. They are not counted: %s'
                            % (len(scratch), ctx['work'], SCRATCH_FOLDER, ', '.join(scratch[:12]) + (' ...' if len(scratch) > 12 else '')))
    return len(scratch)


def set_files(ctx, folders, set_name):
    """Every file in the given folders (under optionb/) whose name carries the set name."""
    out = []
    for folder in folders:
        out += [f for f in files_under(ctx['project'], '%s/%s' % (ctx['work'], folder)) if has_set(f.rsplit('/', 1)[-1], set_name)]
    return out


def refuse_partials(ctx, folders, also=()):
    partial = [f for f in also if (ctx['project'] / f).exists()]
    for folder in folders:
        partial += [f for f in files_under(ctx['project'], '%s/%s' % (ctx['work'], folder)) if f.endswith('.partial')]
    if partial:
        raise Refused('HALF_WRITTEN_FILE', 'a .partial file means a write did not finish: %s' % ', '.join(partial))


def need_files(ctx, files):
    """Every named file is there and is not empty."""
    for relative in files:
        target = ctx['project'] / relative
        if not target.is_file():
            raise Refused('FILE_MISSING', relative)
        if target.stat().st_size == 0:
            raise Refused('FILE_EMPTY', relative)


def need_inputs(ctx, relative, wanted):
    """A JSON file of this step must name each wanted file under "inputs", with the given sha256."""
    data = load_json(ctx['project'], relative)
    listed = {str(item.get('path', '')).replace('\\', '/'): item.get('sha256') for item in data.get('inputs', []) if isinstance(item, dict)}
    for path, digest in wanted.items():
        if listed.get(path) != digest:
            raise Refused('NOT_BUILT_FROM_SEALED_INPUT', '%s does not name %s with sha256 %s under "inputs" (it names %s)'
                          % (relative, path, digest, listed.get(path)))
    return data


def passes_of(ctx):
    """The writer passes of the plan: outside_services.gemini_question_writer.passes (plan v1.1: p1, p2, p3)."""
    passes = ctx['constants']['outside_services']['gemini_question_writer']['passes']
    if not isinstance(passes, list) or not passes or not all(isinstance(p, str) and p for p in passes):
        raise Refused('CONSTANTS_SHAPE', 'outside_services.gemini_question_writer.passes must be a list of pass names')
    return tuple(passes)


def writer_state_facts(ctx, set_name):
    """The question writer is finished for every pass of a set, and one model wrote the set."""
    models = set()
    for pass_name in passes_of(ctx):
        relative = '%s/questions/writer_state_%s_%s.json' % (ctx['work'], set_name, pass_name)
        state = load_json(ctx['project'], relative)
        if state.get('complete') is not True:
            raise Refused('WRITER_NOT_FINISHED', '%s does not say "complete": true' % relative)
        models.add(state.get('model'))
    if len(models) != 1:
        raise Refused('MORE_THAN_ONE_WRITER_MODEL', 'the %s set names these writer models: %s' % (set_name, sorted(map(str, models))))
    model = models.pop()
    wanted = ctx['constants']['outside_services']['gemini_question_writer']['model_by_set'][set_name]
    if model != wanted:
        raise Refused('WRITER_MODEL_NOT_THE_PLANS', 'the %s set was written by %s; the plan names %s' % (set_name, model, wanted))
    return model


# ----------------------------------------------------------------------------- the owner's status table

def status_table_keys(constants):
    """The keys the owner's table must hold (FILE_FORMATS.md section 19.1), in a fixed order."""
    rule, tiers = constants['spec_sheet_status'], constants['tiers']
    keys = ([row['code'] for row in constants['outcome_codes_in_checking_order']]
            + [code + tiers['exploratory_suffix'] for code in tiers['suffix_applies_to']]
            + list(constants['stop_codes']) + list(rule['extra_keys']))
    if len(set(keys)) != len(keys) or len(keys) != rule['table_keys_count']:
        raise Refused('CONSTANTS_SHAPE', 'PLAN_CONSTANTS.json gives %d different table keys; spec_sheet_status.table_keys_count is %r'
                      % (len(set(keys)), rule['table_keys_count']))
    return keys


def check_status_table(project, constants):
    """The owner's table, with every limit of spec_sheet_status.limits checked. Returns {code: status word}."""
    rule, tiers = constants['spec_sheet_status'], constants['tiers']
    relative = rule['table_file']
    path = Path(project) / relative
    if not path.is_file():
        raise Refused('STATUS_TABLE_MISSING', '%s was not found. The owner signs one table before the GPU launch (plan section 21). '
                      'No program writes it and nobody fills it in for the owner.' % relative)
    limit_4 = [text for text in rule['limits'] if text.startswith('L4.')]
    if len(limit_4) != 1 or any(word not in limit_4[0] for word in NEVER_FOR_EXPLORATORY) or NO_RESULT_FILE not in rule['extra_keys']:
        raise Refused('CONSTANTS_SHAPE', 'spec_sheet_status in PLAN_CONSTANTS.json does not have the limit L4 or the extra key this tool knows')
    repeated = []

    def pairs(items):
        seen = {}
        for name, value in items:
            if name in seen:
                repeated.append(name)
            seen[name] = value
        return seen

    try:
        doc = json.loads(path.read_bytes().decode('utf-8'), object_pairs_hook=pairs)
    except (OSError, ValueError) as error:
        raise Refused('FILE_NOT_READABLE', '%s is not readable JSON (%s)' % (relative, type(error).__name__))
    if not isinstance(doc, dict) or doc.get('schema') != TABLE_SCHEMA:
        raise Refused('STATUS_TABLE_NOT_SOUND', '%s does not carry the schema name %s' % (relative, TABLE_SCHEMA))
    for name in ('owner_words_verbatim', 'received_utc', 'channel'):
        value = doc.get(name)
        if not isinstance(value, str) or not value.strip() or value.strip().startswith('<'):
            raise Refused('STATUS_TABLE_NOT_SOUND', '%s: the field %s is missing, empty or still a placeholder' % (relative, name))
    sheet = doc.get('spec_sheet')
    if (not isinstance(sheet, dict) or not isinstance(sheet.get('path'), str) or not sheet['path']
            or not isinstance(sheet.get('sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', sheet['sha256'])):
        raise Refused('STATUS_TABLE_NOT_SOUND', '%s: spec_sheet must give the path and the sha256 of the spec sheet as it stood when the owner signed' % relative)
    legend, table = doc.get('legend_words'), doc.get('table')
    if (not isinstance(legend, list) or not legend or len(set(map(str, legend))) != len(legend)
            or any(not isinstance(word, str) or not word.strip() or re.search('[<>…]', word) for word in legend)):
        raise Refused('STATUS_TABLE_NOT_SOUND', '%s: legend_words must be a list of different status words, copied from the sheet' % relative)
    if not isinstance(table, dict):
        raise Refused('STATUS_TABLE_NOT_SOUND', '%s: table must be an object' % relative)
    keys = status_table_keys(constants)
    missing, extra = [key for key in keys if key not in table], sorted(key for key in table if key not in keys)
    if repeated or missing or extra:
        raise Refused('STATUS_TABLE_BREAKS_LIMIT_L1', '%s: every one of the %d keys stands in the table once, and there is no other key. '
                      'Repeated: %s. Missing: %s. Not a key: %s' % (relative, len(keys), sorted(set(repeated)), missing, extra))
    not_legend = sorted(key for key, word in table.items() if not isinstance(word, str) or word not in legend)
    if not_legend:
        raise Refused('STATUS_TABLE_BREAKS_LIMIT_L2', '%s: the word of these keys does not stand in legend_words: %s' % (relative, not_legend))
    suffix, pass_words = tiers['exploratory_suffix'], set(rule['pass_words'])
    may_pass = (constants['pass_code'], constants['pass_code'] + suffix)
    never_pass = set(tiers['suffix_never_on']) | set(constants['stop_codes']) | set(rule['extra_keys'])
    for key in keys:
        word = table[key]
        if word in pass_words and key not in may_pass:
            limit = 'L3' if key in never_pass else 'L5'
            raise Refused('STATUS_TABLE_BREAKS_LIMIT_' + limit, '%s: %s gets the pass word %s. Only %s, with or without the ending %s, may get a pass word'
                          % (relative, key, word, constants['pass_code'], suffix))
        if key.endswith(suffix) and word in NEVER_FOR_EXPLORATORY:
            raise Refused('STATUS_TABLE_BREAKS_LIMIT_L4', '%s: %s ends in %s and gets %s. Such a code never gets %s'
                          % (relative, key, suffix, word, ' or '.join(NEVER_FOR_EXPLORATORY)))
    return table


def status_word(project, args):
    """Print the outcome code and its status word (FILE_FORMATS.md section 19.2). Writes no file."""
    project = Path(project).resolve()
    constants = load_constants(project)
    require_steps(project, ['7_PRECHECK'], constants)      # the table is a file of that line, so it is unchanged
    table = check_status_table(project, constants)
    unreadable = constants['result_unreadable_text']
    given = [args.result is not None, bool(args.no_result_file), args.code is not None]
    if sum(given) != 1:
        raise Refused('ARGUMENTS_MISSING', 'status-word needs exactly one of --result FILE, --no-result-file, --code %s' % unreadable)
    if args.no_result_file:
        code = NO_RESULT_FILE
    elif args.code is not None:
        if args.code != unreadable:
            raise Refused('CODE_NOT_ALLOWED', '--code takes only %s. Every other code is read from the result file with --result.' % unreadable)
        code = unreadable
    else:
        result_path = Path(args.result)
        if not result_path.is_file():
            raise Refused('FILE_MISSING', '%s. If the job returned no RESULT.json, use --no-result-file.' % result_path)
        try:
            code = json.loads(result_path.read_bytes().decode('utf-8')).get('outcome_code')
        except (ValueError, AttributeError):
            code = None
        # code_format in PLAN_CONSTANTS.json: capital letters and underscores only, at most 80 characters;
        # anything else is RESULT_UNREADABLE, as the guest's own result reader does it.
        if not isinstance(code, str) or not re.fullmatch(r'[A-Z_]{1,80}', code):
            code = unreadable
    if code not in table:
        print('%s NOT_IN_TABLE' % code)
        return 2
    print('%s %s' % (code, table[code]))
    return 0


# ----------------------------------------------------------------------------- the steps

def sealed_sources(c):
    """The names of the source files that seal step 1 seals, read from the plan constants (amendment A13: six).

    Refuses when the list names a source twice, a source that is not pinned, or two sources with one
    path; when one of the five older sources is missing from it; or when the source of the sayings
    (role_notes.sayings_source_key) is missing from it.
    """
    names = c.get('seal', {}).get('sources_sealed_in_step_1')
    sayings = c.get('role_notes', {}).get('sayings_source_key')
    if (not isinstance(names, list) or len(set(names)) != len(names) or any(name not in c['sources'] for name in names)
            or len({c['sources'][name]['path'] for name in names}) != len(names)):
        raise Refused('CONSTANTS_SHAPE', 'seal.sources_sealed_in_step_1 in PLAN_CONSTANTS.json is not a list of different pinned sources')
    missing = [name for name in SOURCES_ALWAYS_SEALED + (sayings,) if name not in names]
    if missing:
        raise Refused('CONSTANTS_SHAPE', 'seal.sources_sealed_in_step_1 in PLAN_CONSTANTS.json does not name %s' % ', '.join(map(str, missing)))
    return names


def step_1(ctx):
    project, work, c = ctx['project'], ctx['work'], ctx['constants']
    sources = sealed_sources(c)
    for name, pin in c['sources'].items():
        path = project / pin['path']
        if not path.is_file():
            raise Refused('SOURCE_MISSING', '%s (%s) was not found' % (name, pin['path']))
        size, digest = file_facts(path)
        if size != pin['bytes'] or digest != pin['sha256']:
            raise Refused('SOURCE_CHANGED', '%s is %d bytes %s; PLAN_CONSTANTS.json pins %d bytes %s' % (pin['path'], size, digest, pin['bytes'], pin['sha256']))
    scratch = refuse_if_questions_exist(ctx, 'The plan is sealed before any question exists.')
    refuse_partials(ctx, ['elig'])
    exclusions_path = '%s/elig/exclusions.json' % work
    eligibility_path = '%s/elig/eligibility.json' % work
    constants_path = '%s/PLAN_CONSTANTS.json' % work
    # the eleven laptop tools (plan section 11.1, "The tools are sealed too")
    tools = list(c['seal']['tools_sealed_in_step_1'])
    on_disk = sorted('tools/' + path.name for path in (project / 'tools').glob('ob_*.py'))
    if len(set(tools)) != len(tools) or sorted(tools) != on_disk:
        raise Refused('TOOLS_DO_NOT_MATCH_THE_PLAN', 'seal.tools_sealed_in_step_1 names %s; the files tools/ob_*.py are %s. Every such tool is sealed, and no other.'
                      % (sorted(tools), on_disk))
    if PROGRAM not in tools or ELIGIBILITY_TOOL not in tools:
        raise Refused('CONSTANTS_SHAPE', 'seal.tools_sealed_in_step_1 does not name %s and %s' % (PROGRAM, ELIGIBILITY_TOOL))
    model_id = c['outside_services']['claude_solver'].get('model_id')
    if not isinstance(model_id, str) or not model_id.strip():
        raise Refused('CLAUDE_MODEL_ID_NOT_PINNED', 'outside_services.claude_solver.model_id in PLAN_CONSTANTS.json is %r. '
                      'The operator writes the exact model id of the Claude Sonnet sub-agents there before seal step 1.' % (model_id,))
    need_files(ctx, [c['plan_file'], constants_path, '%s/FILE_FORMATS.md' % work, exclusions_path, eligibility_path] + tools)
    wanted = {c['sources'][name]['path']: c['sources'][name]['sha256'] for name in ('labels_team_a', 'labels_team_b', 'passages', 'verdict_program')}
    wanted[constants_path] = file_facts(project / constants_path)[1]
    exclusions = need_inputs(ctx, exclusions_path, wanted)
    eligibility = need_inputs(ctx, eligibility_path, wanted)
    tool_sha = file_facts(project / ELIGIBILITY_TOOL)[1]
    for relative, doc in ((exclusions_path, exclusions), (eligibility_path, eligibility)):
        made_by = doc.get('made_by') if isinstance(doc.get('made_by'), dict) else {}
        if made_by.get('sha256') != tool_sha:
            raise Refused('NOT_MADE_BY_THE_SEALED_TOOL', '%s names made_by.sha256 %s; %s, which this step seals, has sha256 %s. Run the tool again.'
                          % (relative, made_by.get('sha256'), ELIGIBILITY_TOOL, tool_sha))
    real = {k: v for k, v in c['counts_real'].items() if k != 'note'}
    counted = {k: v for k, v in eligibility.get('counts', {}).items() if k != 'note'}
    if eligibility.get('counts_match_plan') is not True or counted != real:
        raise Refused('COUNTS_DO_NOT_MATCH_PLAN', '%s does not hold the counts of counts_real' % eligibility_path)
    if exclusions.get('count') != real['excluded_passages'] or len(exclusions.get('passages', [])) != real['excluded_passages']:
        raise Refused('COUNTS_DO_NOT_MATCH_PLAN', '%s does not list %d passages' % (exclusions_path, real['excluded_passages']))
    if (eligibility.get('practice_settings') != c['split']['practice_settings']
            or eligibility.get('reserve_settings_in_order') != c['split']['reserve_settings_in_order']):
        raise Refused('SPLIT_DOES_NOT_MATCH_PLAN', '%s does not hold the settings of the plan' % eligibility_path)
    files = ([c['plan_file'], constants_path, '%s/FILE_FORMATS.md' % work]
             + [c['sources'][name]['path'] for name in sources] + [exclusions_path, eligibility_path] + tools)
    not_null = [tool for tool in tools if package_path(c, tool) is not None]
    if not_null or package_path(c, c['sources']['verdict_program']['path']) != c['seal']['verdict_program_package_path']:
        raise Refused('CONSTANTS_SHAPE', 'a tool would get a package path (%s), or tools/verdict.py would not get the one the plan gives' % not_null)
    sayings_path = c['sources'][c['role_notes']['sayings_source_key']]['path']
    if package_path(c, sayings_path) is not None:
        raise Refused('CONSTANTS_SHAPE', 'the source of the sayings (%s) would get a package path. The job does not need it; its package_path is null' % sayings_path)
    values = {'practice_settings': eligibility['practice_settings'],
              'reserve_settings_in_order': eligibility['reserve_settings_in_order'],
              'scorer_version': c['scorer']['version'],
              'excluded_passages': exclusions['count'],
              'eligible_passages': real['eligible_passages'],
              'pinned_sources_checked': len(c['sources']),
              'sources_sealed': len(sources),
              'tools_sealed': len(tools),
              'claude_model_id': model_id,
              'question_like_files_in_scratch_folder': scratch}
    return files, values


def step_2(ctx):
    project, work, c = ctx['project'], ctx['work'], ctx['constants']
    scratch = refuse_if_questions_exist(ctx, 'The role notes are sealed before any question exists.')
    refuse_partials(ctx, ['notes_role'])
    notes_path = '%s/notes_role/role_notes.json' % work
    sample_path = '%s/notes_role/owner_sample_20.json' % work
    need_files(ctx, [notes_path, sample_path])
    sealed = ctx['sealed']
    # Amendment A13 (FILE_FORMATS.md section 15.1, step 2): the source of the sayings was sealed in step 1. Both files
    # of this step must name it under "inputs" with the sealed sha256, next to the guide.
    sayings = c['sources'][c['role_notes']['sayings_source_key']]
    if sayings['path'] not in sealed:
        raise Refused('SAYINGS_SOURCE_NOT_SEALED', '%s is not named in seal step 1. The role notes print lines from it (amendment A13)' % sayings['path'])
    wanted = {path: sealed[path] for path in ('%s/elig/eligibility.json' % work, c['sources']['labeling_guide']['path'], sayings['path'],
                                              '%s/PLAN_CONSTANTS.json' % work)}
    notes = need_inputs(ctx, notes_path, wanted)
    sample = need_inputs(ctx, sample_path, wanted)
    if notes.get('canon', {}).get('sha256') != c['sources']['labeling_guide']['sha256']:
        raise Refused('CANON_NOT_FROM_THE_SEALED_GUIDE', '%s names another guide hash' % notes_path)
    if notes.get('canon', {}).get('sayings_sha256') != sayings['sha256'] or sealed[sayings['path']] != sayings['sha256']:
        raise Refused('SAYINGS_NOT_FROM_THE_SEALED_SOURCE', '%s names the sayings hash %s under canon.sayings_sha256; sources.%s pins %s'
                      % (notes_path, notes.get('canon', {}).get('sayings_sha256'), c['role_notes']['sayings_source_key'], sayings['sha256']))
    count = len(notes.get('passages', []))
    if count != c['counts_real']['eligible_passages']:
        raise Refused('COUNTS_DO_NOT_MATCH_PLAN', '%s holds %d passages; the plan counts %d eligible' % (notes_path, count, c['counts_real']['eligible_passages']))
    if len(sample.get('passages', [])) != c['role_notes']['owner_sample_size']:
        raise Refused('COUNTS_DO_NOT_MATCH_PLAN', '%s does not hold %d passages' % (sample_path, c['role_notes']['owner_sample_size']))
    values = {'passages_with_a_role_note': count, 'owner_sample_size': len(sample['passages']),
              'question_like_files_in_scratch_folder': scratch}
    return [notes_path, sample_path], values


def questions_step(ctx, set_name):
    """Steps 3A and 3C: every file of FILE_FORMATS.md sections 4 to 7.1 that belongs to one set."""
    work = ctx['work']
    refuse_partials(ctx, QUESTION_FOLDERS)
    early_notes = set_files(ctx, NOTE_FOLDERS, set_name)
    if early_notes:
        raise Refused('NOTES_BEFORE_QUESTIONS_SEALED', 'ordinary notes of a set are written only after its questions are sealed. Found: %s' % ', '.join(early_notes[:12]))
    required = (['%s/questions/%s_%s_%s.%s' % (work, kind, set_name, pass_name, ext)
                 for pass_name in passes_of(ctx) for kind, ext in (('writer_state', 'json'), ('writer_calls', 'jsonl'), ('raw_questions', 'json'))]
                + ['%s/checks/%s_%s.json' % (work, kind, set_name) for kind in ('form_check', 'anchor_check', 'option_check', 'candidates')]
                + ['%s/solve/%s_%s.json' % (work, kind, set_name) for kind in ('solver_items', 'solver_answers', 'key_check')]
                + ['%s/solve/deepseek_calls_%s.jsonl' % (work, set_name), '%s/select/selection_%s.json' % (work, set_name)])
    need_files(ctx, required)
    found = set_files(ctx, QUESTION_FOLDERS, set_name)
    files = sorted(set(required) | set(found))
    model = writer_state_facts(ctx, set_name)
    selection = load_json(ctx['project'], '%s/select/selection_%s.json' % (work, set_name))
    counts = selection.get('counts', {})
    sheets = [f for f in found if '/solve/claude_sheet_' in f]
    answers = [f for f in found if '/solve/claude_answers_' in f]
    for mode in ('with_passage', 'no_passage'):
        if not any('_%s_' % mode in f for f in sheets) or not any('_%s_' % mode in f for f in answers):
            ctx['notes'].append('NOTE: the %s set has no Claude sheet or no Claude answer file for mode %s.' % (set_name, mode))
    values = {'set': set_name, 'writer_model': model,
              'practice_setting_count': selection.get('practice_setting_count'),
              'role_step_tasks': counts.get('role_step_tasks'), 'plain_fact_tasks': counts.get('plain_fact_tasks'),
              'claude_sheets': len(sheets), 'claude_answer_files': len(answers)}
    return files, values, selection


def practice_numbers(c, selection):
    """What the practice selection means under the reserve rule and the launch floor. Worked out here from its counts."""
    split, floor, counts = c['split'], c['launch_floor'], selection.get('counts', {})
    role, fact, count = whole(counts.get('role_step_tasks')), whole(counts.get('plain_fact_tasks')), selection.get('practice_setting_count')
    if not isinstance(count, int) or not split['practice_setting_count_start'] <= count <= split['practice_setting_count_max']:
        raise Refused('SELECTION_DOES_NOT_MATCH_PLAN', 'select/selection_practice.json names %r practice settings; the plan allows %d to %d'
                      % (count, split['practice_setting_count_start'], split['practice_setting_count_max']))
    target_met = role >= split['reserve_target_practice_role_step_tasks'] and fact >= split['reserve_target_practice_plain_fact_tasks']
    left = split['practice_setting_count_max'] - count
    return {'role_step_tasks': role, 'plain_fact_tasks': fact, 'practice_setting_count': count,
            'target_met': target_met, 'settings_left': left, 'finished': target_met or left == 0,
            'floor_met': role >= floor['practice_role_step_tasks_min'] and fact >= floor['practice_plain_fact_tasks_min']}


def step_3a(ctx):
    c = ctx['constants']
    final_early = set_files(ctx, QUESTION_FOLDERS, 'final')
    if final_early:
        raise Refused('FINAL_FILE_BEFORE_PRACTICE_IS_FIXED', 'no final question file may exist before step 3B. Found: %s' % ', '.join(final_early[:12]))
    files, values, selection = questions_step(ctx, 'practice')
    # FILE_FORMATS.md section 7.1: the practice set is final only when the reserve rule is finished.
    now = practice_numbers(c, selection)
    reserve = selection.get('reserve') if isinstance(selection.get('reserve'), dict) else {}
    if not now['finished'] or reserve.get('finished') is not True:
        raise Refused('RESERVE_RULE_NOT_FINISHED', 'the practice selection holds %d role-step and %d plain-fact tasks with %d practice settings; the reserve targets are %d and %d, '
                      'and %d reserve setting(s) are left. Move the next reserve setting first. After seal step 3A no practice question file is written again.'
                      % (now['role_step_tasks'], now['plain_fact_tasks'], now['practice_setting_count'], c['split']['reserve_target_practice_role_step_tasks'],
                         c['split']['reserve_target_practice_plain_fact_tasks'], now['settings_left']))
    if reserve.get('target_met') is not now['target_met'] or reserve.get('settings_left') != now['settings_left']:
        raise Refused('SELECTION_DOES_NOT_MATCH_PLAN', 'the reserve block of select/selection_practice.json (%s) does not follow from its counts and the plan (%s)'
                      % (json.dumps(reserve, ensure_ascii=False), json.dumps({k: now[k] for k in ('target_met', 'settings_left', 'finished')})))
    values['practice_floor'] = selection.get('floor')
    values['reserve'] = reserve
    if not now['floor_met']:
        ctx['notes'].append('NOTE: the reserve rule is finished and a practice launch floor is NOT met. Seal step 3A keeps the practice questions as evidence. '
                            'Seal step 3B will be refused: do not launch; report the survival numbers to the owner.')
    return files, values


def step_3b(ctx):
    work, c = ctx['work'], ctx['constants']
    final_early = set_files(ctx, QUESTION_FOLDERS, 'final')
    if final_early:
        raise Refused('FINAL_FILE_BEFORE_PRACTICE_IS_FIXED', 'no final question file may exist before step 3B. Found: %s' % ', '.join(final_early[:12]))
    refuse_partials(ctx, ['select'])
    split_path = '%s/select/split_fixed.json' % work
    need_files(ctx, [split_path])
    split = load_json(ctx['project'], split_path)
    selection = load_json(ctx['project'], '%s/select/selection_practice.json' % work)
    if split.get('practice_setting_count') != selection.get('practice_setting_count'):
        raise Refused('SPLIT_DOES_NOT_MATCH_SELECTION', 'split_fixed.json says %r practice settings; the sealed practice selection says %r'
                      % (split.get('practice_setting_count'), selection.get('practice_setting_count')))
    now = practice_numbers(c, selection)
    history = split.get('history') if isinstance(split.get('history'), list) else []
    last = history[-1] if history and isinstance(history[-1], dict) else {}
    if (last.get('practice_setting_count') != now['practice_setting_count'] or last.get('practice_role_step_tasks') != now['role_step_tasks']
            or last.get('practice_plain_fact_tasks') != now['plain_fact_tasks'] or split.get('reserve_target_met') is not now['target_met']):
        raise Refused('SPLIT_DOES_NOT_MATCH_SELECTION', 'the last history row of split_fixed.json, or its reserve_target_met, does not match the sealed practice selection')
    if any(isinstance(row, dict) and row.get('target_met') for row in history[:-1]):
        raise Refused('RESERVE_RULE_OVERUSED', 'an earlier history row of split_fixed.json already met both reserve targets. No setting is moved once both targets are met.')
    if not now['finished']:
        raise Refused('RESERVE_RULE_NOT_FINISHED', 'the reserve targets are missed and reserve settings are left')
    # FILE_FORMATS.md section 7.2: both practice launch floors, role-step and plain-fact.
    if split.get('floor_met') is not True or not now['floor_met']:
        raise Refused('PRACTICE_FLOOR_NOT_MET', 'the practice set holds %d role-step and %d plain-fact tasks; the launch floors are %d and %d (split_fixed.json says "floor_met": %r). '
                      'The plan says: do not launch; report the survival numbers to the owner.'
                      % (now['role_step_tasks'], now['plain_fact_tasks'], c['launch_floor']['practice_role_step_tasks_min'],
                         c['launch_floor']['practice_plain_fact_tasks_min'], split.get('floor_met')))
    values = {'practice_setting_count': split.get('practice_setting_count'), 'practice_settings': split.get('practice_settings'),
              'floor_met': True, 'practice_role_step_min': c['launch_floor']['practice_role_step_tasks_min'],
              'practice_plain_fact_min': c['launch_floor']['practice_plain_fact_tasks_min'],
              'reserve_target_met': now['target_met'], 'history': split.get('history')}
    return [split_path], values


def step_3c(ctx):
    files, values, selection = questions_step(ctx, 'final')
    split = load_json(ctx['project'], '%s/select/split_fixed.json' % ctx['work'])
    if selection.get('practice_setting_count') != split.get('practice_setting_count'):
        raise Refused('SPLIT_DOES_NOT_MATCH_SELECTION', 'the final selection says %r practice settings; the sealed split says %r'
                      % (selection.get('practice_setting_count'), split.get('practice_setting_count')))
    return files, values


def step_4(ctx):
    work = ctx['work']
    refuse_partials(ctx, NOTE_FOLDERS)
    # A note the writer could not produce (plan section 10, Step 7; FILE_FORMATS.md sections 8.1 and 9.5): its passage
    # is dropped with this status, and the support check of that passage is finished.
    not_written = ctx['constants']['ordinary_notes']['not_written_status']
    finished = SUPPORT_FINISHED + (not_written,)
    files, values = [], {}
    for set_name in ('practice', 'final'):
        required = ['%s/notes_ord/ordinary_notes_%s.json' % (work, set_name), '%s/notes_ord/ordinary_calls_%s.jsonl' % (work, set_name)]
        required += ['%s/support/%s_%s.json' % (work, kind, set_name) for kind in ('support_state', 'support_items', 'support_results')]
        files += sorted(set(required) | set(set_files(ctx, NOTE_FOLDERS, set_name)))
        need_files(ctx, required)
        results = load_json(ctx['project'], '%s/support/support_results_%s.json' % (work, set_name))
        statuses = [p.get('status') for p in results.get('passages', [])]
        open_ones = [s for s in statuses if s not in finished]
        if open_ones:
            raise Refused('SUPPORT_CHECK_NOT_FINISHED', 'the %s set has %d passage(s) with status %s' % (set_name, len(open_ones), sorted(set(map(str, open_ones)))))
        notes = load_json(ctx['project'], '%s/notes_ord/ordinary_notes_%s.json' % (work, set_name))
        values[set_name] = {'passages_with_ordinary_notes': len(notes.get('passages', [])),
                            'passages_all_pass': statuses.count('ALL_PASS'),
                            'passages_dropped_second_failure': statuses.count('DROPPED_SECOND_FAILURE'),
                            'passages_dropped_note_not_written': statuses.count(not_written)}
    return files, values


def step_5(ctx):
    work = ctx['work']
    refuse_partials(ctx, ['screen', 'prompts', 'keys_practice', 'keys_final', 'review'], also=['%s/removal_log.json.partial' % work])
    files = (['%s/screen/leak_screen_%s.json' % (work, s) for s in ('practice', 'final')]
             + ['%s/removal_log.json' % work]
             + ['%s/prompts/prompt_parts_%s.json' % (work, s) for s in ('practice', 'final')]
             + ['%s/keys_practice/keys_practice.json' % work, '%s/keys_practice/task_meta_practice.json' % work,
                '%s/keys_final/keys_final.json' % work, '%s/keys_final/task_meta_final.json' % work,
                '%s/review/review_pack.json' % work])
    need_files(ctx, files)
    log = load_json(ctx['project'], '%s/removal_log.json' % work)
    if log.get('launch_floor_met') is not True or log.get('tier') == 'NO_LAUNCH':
        raise Refused('LAUNCH_FLOOR_NOT_MET', 'removal_log.json says launch_floor_met %r and tier %r. This is reported to the owner. It is not sealed as a go.'
                      % (log.get('launch_floor_met'), log.get('tier')))
    values = {'final_counts': log.get('final_counts'), 'launch_floor_met': True, 'tier': log.get('tier')}
    return files, values


def step_6(ctx):
    work, c = ctx['work'], ctx['constants']
    refuse_partials(ctx, ['job'])
    files = ['%s/job/%s' % (work, name) for name in JOB_FILES]
    for key in ('file', 'examples_file'):
        if c['scorer'][key] not in files:
            raise Refused('CONSTANTS_SHAPE', 'PLAN_CONSTANTS.json names the scorer file %s; it is not one of the five job files' % c['scorer'][key])
    if sorted(c['repairs']['job_programs']['files_that_may_change']) != sorted(files):
        raise Refused('CONSTANTS_SHAPE', 'repairs.job_programs.files_that_may_change in PLAN_CONSTANTS.json is not the five job files of this step')
    extra = [f for f in files_under(ctx['project'], '%s/job' % work) if f not in files]
    if extra:
        ctx['notes'].append('NOTE: %d more file(s) lie in %s/job/ and are not sealed: %s' % (len(extra), work, ', '.join(extra[:12])))
    return files, {'scorer_version': c['scorer']['version']}


def seal_up_to_last_program_line(seal_bytes, lines):
    """The bytes of the seal file from its first line to its last program line (6_PROGRAMS or 6R_PROGRAMS_REPAIRED).

    No program line follows that line. Returns None when the seal file holds no program line.
    """
    places = [place for place, line in enumerate(lines) if line['step'] in PROGRAM_LINES]
    if not places:
        return None
    raw = seal_bytes[:-1].split(b'\n')
    return b''.join(line + b'\n' for line in raw[:places[-1] + 1])


def seal_copy_in_zip(zip_path):
    """The member SEAL_OPTIONB.jsonl of a source.zip, read with the standard zipfile module. Only this one member is read."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as archive:
            if archive.namelist().count(SEAL_NAME) != 1:
                raise Refused('SOURCE_ZIP_IS_NOT_THE_SEALED_PACKAGE', '%s does not hold exactly one member %s' % (zip_path, SEAL_NAME))
            if archive.getinfo(SEAL_NAME).file_size > SEAL_COPY_BYTES_MAX:
                raise Refused('SOURCE_ZIP_IS_NOT_THE_SEALED_PACKAGE', 'the member %s of %s is larger than %d bytes' % (SEAL_NAME, zip_path, SEAL_COPY_BYTES_MAX))
            return archive.read(SEAL_NAME)
    except (zipfile.BadZipFile, OSError, KeyError, RuntimeError, NotImplementedError) as error:
        raise Refused('FILE_NOT_READABLE', '%s is not a readable zip file (%s)' % (zip_path, type(error).__name__))


def step_7(ctx):
    c, args = ctx['constants'], ctx['args']
    if not args.receipt or not args.selftest_json or not args.source_zip:
        raise Refused('ARGUMENTS_MISSING', 'step 7 needs --receipt FILE (the supervisor_receipt.json of the pre-check job), '
                      '--selftest-json FILE and --source-zip FILE')
    receipt_path, selftest_path, zip_path = Path(args.receipt), Path(args.selftest_json), Path(args.source_zip)
    for path in (receipt_path, selftest_path, zip_path):
        if not path.is_file():
            raise Refused('FILE_MISSING', str(path))
    raw = selftest_path.read_bytes()
    try:
        selftest = json.loads(raw.decode('utf-8'))
    except ValueError:
        raise Refused('FILE_NOT_READABLE', '%s is not JSON' % selftest_path)
    if selftest.get('schema') != SELFTEST_SCHEMA or selftest.get('mode') != 'precheck':
        raise Refused('NOT_A_PRECHECK_RECORD', 'schema %r, mode %r' % (selftest.get('schema'), selftest.get('mode')))
    if selftest.get('status') != c['selftest_pass_status']:
        raise Refused('PRECHECK_DID_NOT_PASS', 'the pre-check ended with status %r. A failed pre-check stops the launch. It is reported, not sealed. '
                      'What may follow is fixed in plan section 19.1' % selftest.get('status'))
    package_check = [x for x in selftest.get('checks', []) if isinstance(x, dict) and x.get('name') == 'package_matches_seal']
    if len(package_check) != 1 or package_check[0].get('passed') is not True:
        raise Refused('PRECHECK_DID_NOT_PASS', 'the check package_matches_seal is not recorded as passed')
    hashes = {}
    for key in ('prompt_list_sha256', 'padding_plan_sha256'):
        value = selftest.get(key)
        if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
            raise Refused('NOT_A_PRECHECK_RECORD', '%s is not a sha256' % key)
        hashes[key] = value
    # Plan section 21: the owner's signed table of status words is hashed in this step. Without it there is no GPU launch.
    check_status_table(ctx['project'], c)
    values = {'source_zip_sha256': file_facts(zip_path)[1], 'selftest_status': selftest['status'],
              'prompt_list_sha256': hashes['prompt_list_sha256'], 'padding_plan_sha256': hashes['padding_plan_sha256'],
              'selftest_json_sha256': sha256_bytes(raw)}
    # Amendment A8 (FILE_FORMATS.md section 15.1). The pre-check kit builds three kinds of job: SEALED_PACKAGE,
    # REHEARSAL and DEVELOPMENT_TEST. All three return a selftest.json in precheck mode, and a seal step is never
    # written twice. So this step reads the job's receipt and the seal copy inside the given source.zip.
    kind, passed = c['seal'].get('step_7_receipt_kind'), c['seal'].get('step_7_receipt_status')
    if not isinstance(kind, str) or not kind or not isinstance(passed, str) or not passed:
        raise Refused('CONSTANTS_SHAPE', 'seal.step_7_receipt_kind or seal.step_7_receipt_status is missing in PLAN_CONSTANTS.json')
    try:
        receipt = json.loads(receipt_path.read_bytes().decode('utf-8'))
    except (OSError, ValueError):
        raise Refused('FILE_NOT_READABLE', '%s is not JSON' % receipt_path)
    if not isinstance(receipt, dict):
        raise Refused('FILE_NOT_READABLE', '%s is not a JSON object' % receipt_path)
    if receipt.get('precheck_kind') != kind:
        raise Refused('RECEIPT_IS_NOT_OF_A_JOB_ON_THE_SEALED_PACKAGE', 'the receipt says precheck_kind %r. Seal step 7 is written only from a job of kind %s. '
                      'A rehearsal or a test on made-up data is never sealed' % (receipt.get('precheck_kind'), kind))
    if receipt.get('status') != passed:
        raise Refused('PRECHECK_DID_NOT_PASS', 'the receipt says status %r; seal step 7 needs %s. A failed pre-check stops the launch. It is reported, not sealed. '
                      'What may follow is fixed in plan section 19.1' % (receipt.get('status'), passed))
    if receipt.get('seal_step_7_values') != values:
        raise Refused('RECEIPT_DOES_NOT_MATCH', 'the block seal_step_7_values of the receipt (%s) is not the five values worked out from the given selftest.json and source.zip (%s)'
                      % (json.dumps(receipt.get('seal_step_7_values'), sort_keys=True), json.dumps(values, sort_keys=True)))
    wanted = seal_up_to_last_program_line(ctx['seal_bytes'], ctx['lines'])
    if wanted is None or seal_copy_in_zip(zip_path) != wanted:
        raise Refused('SOURCE_ZIP_IS_NOT_THE_SEALED_PACKAGE', 'the member %s of the given source.zip is not, byte for byte, the real seal file from its first line '
                      'to its last program line (6_PROGRAMS or the last 6R_PROGRAMS_REPAIRED). This source.zip is not the package of the seal file as it stands' % SEAL_NAME)
    return [c['spec_sheet_status']['table_file']], values


STEPS = {'1_PLAN_AND_SOURCES': step_1, '2_ROLE_NOTES': step_2, '3A_PRACTICE_QUESTIONS_AND_KEYS': step_3a,
         '3B_PRACTICE_SET_FIXED': step_3b, '3C_FINAL_QUESTIONS_AND_KEYS': step_3c, '4_ORDINARY_NOTES': step_4,
         '5_PROMPT_PARTS_AND_REMOVAL_LOG': step_5, '6_PROGRAMS': step_6, '7_PRECHECK': step_7}


# ----------------------------------------------------------------------------- writing one line

def package_path(constants, relative):
    """Where the file sits in the job package (FILE_FORMATS.md section 14), or None."""
    work = work_name(constants)
    if relative == constants['plan_file']:
        return relative
    if relative == constants['sources']['verdict_program']['path']:
        # review round 1: the analysis program needs content() of this frozen file for three views
        return constants['seal']['verdict_program_package_path']
    if relative.startswith(work + '/') and relative[len(work) + 1:] in PACKAGE_UNDER_WORK:
        return relative[len(work) + 1:]
    return None


def stale_inputs(project, files, sealed):
    """JSON files of this step that name, under "inputs", a file sealed earlier with another sha256."""
    problems = []
    for relative in files:
        if not relative.endswith('.json'):
            continue
        try:
            data = json.loads((Path(project) / relative).read_bytes().decode('utf-8'))
        except (OSError, ValueError):
            raise Refused('FILE_NOT_READABLE', '%s is not readable JSON' % relative)
        if not isinstance(data, dict):
            continue
        for item in data.get('inputs', []) or []:
            if not isinstance(item, dict):
                continue
            path = str(item.get('path', '')).replace('\\', '/')
            if path in sealed and item.get('sha256') != sealed[path]:
                problems.append('%s was built from %s with sha256 %s; the sealed one is %s' % (relative, path, item.get('sha256'), sealed[path]))
    return problems


def add_line(project, constants, start_bytes, lines, step, records, values, notes, dry_run):
    """Builds one line and appends it unless dry_run. The bytes already in the seal file are never touched."""
    path = seal_path(project, constants)
    now = utc_now()
    previous = sha256_bytes(start_bytes[:-1].split(b'\n')[-1]) if lines else None
    line = {'schema': SCHEMA, 'n': len(lines) + 1, 'step': step, 'utc': now, 'files': records, 'values': values,
            'who_could_open': WHO[step], 'previous_line_sha256': previous,
            'made_by': {'program': PROGRAM, 'sha256': file_facts(Path(__file__).resolve())[1], 'utc': now}}
    text = json.dumps(line, ensure_ascii=False)
    if chr(10) in text or chr(13) in text:
        raise Refused('LINE_NOT_ONE_LINE', 'the seal line would hold a line break')
    added = text.encode('utf-8') + b'\n'
    parse_seal(start_bytes + added)            # the file with this line must still be a sound seal file
    for note in notes:
        print(note)
    if dry_run:
        print('DRY RUN. %s passed every check. This line would be added (nothing was written):' % step)
        print(text)
        return line
    if read_seal_bytes(project, constants) != start_bytes:
        raise Refused('SEAL_FILE_MOVED', 'the seal file changed while this step ran')
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'ab') as handle:          # append only: the bytes already there are never touched
        handle.write(added)
        handle.flush()
        os.fsync(handle.fileno())
    if read_seal_bytes(project, constants) != start_bytes + added or parse_seal(start_bytes + added)[-1] != line:
        raise Refused('SEAL_WRITE_NOT_CONFIRMED', 'the seal file does not read back as expected. Do not go on. Report this')
    print('SEALED %s as line %d of %s: %d file(s). Line sha256 %s'
          % (step, line['n'], path.relative_to(project).as_posix(), len(records), sha256_bytes(text.encode('utf-8'))))
    return line


def write_step(project, step, args):
    """Runs every check of one step. Appends one line unless --dry-run. Returns the line."""
    project = Path(project).resolve()
    constants = load_constants(project)
    check_repair_names(constants)
    work = work_name(constants)
    start_bytes = read_seal_bytes(project, constants)
    lines = parse_seal(start_bytes)
    done = plain_steps(lines)
    if step in done:
        raise Refused('STEP_ALREADY_WRITTEN', 'step %s is already in the seal file. A step is never repeated. '
                      'A fault in a job program or in a tool is repaired with a repair line (ob_seal.py repair), under the rule of plan section 11.1.' % step)
    if len(done) >= len(ORDER):
        raise Refused('ALL_STEPS_WRITTEN', 'the seal file already holds every step')
    expected = ORDER[len(done)]
    if step != expected:
        raise Refused('STEP_OUT_OF_ORDER', 'the next step is %s. Step %s needs every step before it.' % (expected, step))
    problems = changed_files(project, lines)
    if problems:
        raise Refused('SEALED_FILE_CHANGED', '; '.join(problems))
    sealed = sealed_hashes(lines)
    ctx = {'project': project, 'work': work, 'constants': constants, 'sealed': sealed, 'lines': lines, 'seal_bytes': start_bytes,
           'args': args, 'notes': []}
    files, values = STEPS[step](ctx)
    if len(set(files)) != len(files):
        raise Refused('FILE_NAMED_TWICE', 'step %s names a file twice' % step)
    records = []
    for relative in files:
        if relative in sealed:
            raise Refused('FILE_ALREADY_SEALED', '%s was sealed by an earlier step' % relative)
        target = project / relative
        if not target.is_file():
            raise Refused('FILE_MISSING', relative)
        size, digest = file_facts(target)
        if size == 0:
            raise Refused('FILE_EMPTY', relative)
        records.append({'path': relative, 'package_path': package_path(constants, relative), 'bytes': size, 'sha256': digest})
    stale = stale_inputs(project, files, sealed)
    if stale:
        raise Refused('NOT_BUILT_FROM_SEALED_INPUT', '; '.join(stale))
    return add_line(project, constants, start_bytes, lines, step, records, values, ctx['notes'], args.dry_run)


# ----------------------------------------------------------------------------- repair lines

def check_review(project, constants, folder, repair_id, kind, changed, diff_sha, force):
    """The review record of FILE_FORMATS.md section 15.3. Returns it. Refuses unless it allows this very repair."""
    relative = '%s/review.json' % folder
    doc = load_json(project, relative)

    def bad(what):
        raise Refused('REVIEW_RECORD_NOT_SOUND', '%s: %s' % (relative, what))

    if not isinstance(doc, dict) or doc.get('schema') != REVIEW_SCHEMA:
        bad('it does not carry the schema name %s' % REVIEW_SCHEMA)
    if doc.get('repair_id') != repair_id or doc.get('kind') != kind:
        bad('it names repair %r of kind %r; this repair is %s of kind %s' % (doc.get('repair_id'), doc.get('kind'), repair_id, kind))
    for name in ('reviewer', 'author_of_change', 'fault_file', 'fault', 'evidence', 'utc'):
        if not isinstance(doc.get(name), str) or not doc[name].strip():
            bad('the field %s is missing or empty' % name)
    if doc['reviewer'].strip().lower() == doc['author_of_change'].strip().lower():
        bad('the reviewer and the author of the change are the same. A repair is read by a reviewer who did not write the change.')
    if not isinstance(doc.get('files_changed'), list) or sorted(map(str, doc['files_changed'])) != sorted(changed):
        bad('files_changed is %r; the sealed files that differ now are %r' % (doc.get('files_changed'), sorted(changed)))
    if doc['fault_file'] not in changed:
        bad('fault_file %s is not one of the changed files' % doc['fault_file'])
    if doc.get('diff_sha256') != diff_sha:
        bad('diff_sha256 is %r; %s/diff.txt has sha256 %s' % (doc.get('diff_sha256'), folder, diff_sha))
    if REPAIR_ALLOWED not in constants['repairs']['review_verdicts']:
        raise Refused('CONSTANTS_SHAPE', 'repairs.review_verdicts in PLAN_CONSTANTS.json does not name %s' % REPAIR_ALLOWED)
    if kind == 'TOOLS':
        rows = doc.get('sealed_outputs_checked')
        if not isinstance(rows, list) or any(not isinstance(row, dict) or not isinstance(row.get('path'), str)
                                              or not isinstance(row.get('could_the_fault_have_changed_it'), bool) for row in rows):
            bad('sealed_outputs_checked must be a list of rows with path and could_the_fault_have_changed_it (true or false)')
        # one row per file that is already sealed and that a changed tool wrote
        wrote = []
        for path, item in sorted(force.items()):
            if not path.endswith('.json'):
                continue
            try:
                made_by = json.loads((Path(project) / path).read_bytes().decode('utf-8')).get('made_by')
            except (OSError, ValueError, AttributeError):
                continue
            if isinstance(made_by, dict) and made_by.get('program') in changed:
                wrote.append(path)
        unlisted = [path for path in wrote if path not in {row['path'] for row in rows}]
        if unlisted:
            bad('sealed_outputs_checked has no row for these sealed files, which a changed tool wrote: %s' % unlisted)
        could = sorted(row['path'] for row in rows if row['could_the_fault_have_changed_it'])
        if could:
            raise Refused('REPAIR_REFUSED_A_SEALED_OUTPUT_COULD_HAVE_CHANGED', 'the review record says the fault could have changed these sealed files: %s. '
                          'The plan says: no repair, no launch, a new plan version.' % could)
    for name in ('changes_only_the_listed_files', 'brings_the_code_in_line_with_the_sealed_plan', 'changes_no_rule_number_or_wording_of_the_plan'):
        if doc.get(name) is not True:
            raise Refused('REPAIR_NOT_ALLOWED_BY_THE_REVIEW', '%s does not say "%s": true' % (relative, name))
    if doc.get('verdict') != REPAIR_ALLOWED:
        raise Refused('REPAIR_NOT_ALLOWED_BY_THE_REVIEW', '%s carries the verdict %r. Without %s no line is added.' % (relative, doc.get('verdict'), REPAIR_ALLOWED))
    return doc


def failed_precheck_facts(project, constants, folder, args, lines=()):
    """6R only: what the kept records of the failed pre-check say. lines: the seal lines written so far."""
    receipt_path = '%s/failed_precheck/supervisor_receipt.json' % folder
    selftest_path = '%s/failed_precheck/selftest.json' % folder
    if not (project / receipt_path).is_file():
        raise Refused('FILE_MISSING', '%s. A program repair follows a failed pre-check; a copy of its receipt is kept in the repair folder.' % receipt_path)
    receipt = load_json(project, receipt_path)
    if not isinstance(receipt, dict):
        raise Refused('FILE_NOT_READABLE', '%s is not a JSON object' % receipt_path)
    # Amendment A5: the window of a program repair opens only after a failed pre-check job on the sealed package.
    # A rehearsal or a development test never opens it.
    kind, passed = constants['seal'].get('step_7_receipt_kind'), constants['seal'].get('step_7_receipt_status')
    if not isinstance(kind, str) or not kind or not isinstance(passed, str) or not passed:
        raise Refused('CONSTANTS_SHAPE', 'seal.step_7_receipt_kind or seal.step_7_receipt_status is missing in PLAN_CONSTANTS.json')
    # Operator decision C4 (round 3): only the two statuses of a failed job open the window. Before C4 every status but the
    # pass status (seal.step_7_receipt_status) did, so the receipt of a job that never finished (status RUNNING) got past this test.
    if receipt.get('precheck_kind') != kind or receipt.get('status') not in FAILED_PRECHECK_STATUSES:
        raise Refused(OUTSIDE_WINDOW, '%s says precheck_kind %r and status %r. A %s line is allowed only after a failed pre-check job on the sealed package: '
                      'precheck_kind %s and the status %s' % (receipt_path, receipt.get('precheck_kind'), receipt.get('status'), REPAIR_JOB, kind,
                                                              ' or '.join(FAILED_PRECHECK_STATUSES)))
    job_id = receipt.get('job_id') or receipt.get('job')
    step_7 = receipt.get('seal_step_7_values') if isinstance(receipt.get('seal_step_7_values'), dict) else {}
    zip_sha = receipt.get('source_zip_sha256') or step_7.get('source_zip_sha256')
    if args.source_zip:
        if not Path(args.source_zip).is_file():
            raise Refused('FILE_MISSING', str(args.source_zip))
        given = file_facts(Path(args.source_zip))[1]
        if zip_sha is not None and zip_sha != given:
            raise Refused('RECEIPT_DOES_NOT_MATCH', 'the receipt names source.zip %s; the file given with --source-zip has %s' % (zip_sha, given))
        zip_sha = given
    if not isinstance(job_id, str) or not job_id or not isinstance(zip_sha, str) or not re.fullmatch(r'[0-9a-f]{64}', zip_sha):
        raise Refused('RECEIPT_NOT_SOUND', '%s does not give the job id and the sha256 of source.zip. Give --source-zip FILE (the source.zip the failed pre-check ran on) if the receipt lacks the hash.' % receipt_path)
    # Operator decision C4 (round 3): one failed pre-check job opens the window once. After a program repair a new
    # source.zip is built, so the next failed job ran on another source.zip. A receipt that names the source.zip of an
    # earlier 6R line is the receipt of an old job, copied again; it opens no window.
    for line in lines:
        earlier = line['values'].get('failed_precheck') if line['step'] == REPAIR_JOB else None
        if isinstance(earlier, dict) and earlier.get('source_zip_sha256') == zip_sha:
            raise Refused(OUTSIDE_WINDOW, 'the failed pre-check of %s ran on the source.zip %s (as the receipt, or --source-zip, gives it). '
                          'Seal line %s, an earlier %s line, already names that source.zip. '
                          'A %s line is allowed only after a new failed pre-check job on the sealed package'
                          % (receipt_path, zip_sha, line.get('n'), REPAIR_JOB, REPAIR_JOB))
    facts = receipt.get('after_a_failure_facts') if isinstance(receipt.get('after_a_failure_facts'), dict) else {}
    selftest_status = step_7.get('selftest_status') or facts.get('selftest_status')
    if (project / selftest_path).is_file():
        selftest = load_json(project, selftest_path)
        selftest_status = selftest.get('status') if isinstance(selftest, dict) else None
    if selftest_status == constants['selftest_pass_status']:
        raise Refused('PRECHECK_DID_NOT_FAIL', 'the kept self-test record ends with %s. A program repair is allowed only after a failed pre-check.' % selftest_status)
    return {'job_id': job_id, 'source_zip_sha256': zip_sha, 'receipt_status': receipt.get('status'), 'selftest_status': selftest_status}


def expected_categories(data):
    """{example id: expected category} of a known-examples file."""
    doc = json.loads(data.decode('utf-8'))
    return {str(example['id']): example['expected'] for example in doc['examples']}


def write_repair(project, repair_id, args):
    """Runs every check of one repair line (FILE_FORMATS.md section 15.2). Appends it unless --dry-run."""
    project = Path(project).resolve()
    constants = load_constants(project)
    check_repair_names(constants)
    work, rules = work_name(constants), constants['repairs']
    found = re.fullmatch(r'(6R|TR)([1-9][0-9]*)', repair_id)
    if not found:
        raise Refused('UNKNOWN_REPAIR_ID', '%r is not a repair id. The form is: %s' % (repair_id, rules['repair_id_form']))
    kind, step = REPAIR_KIND[found.group(1)]
    start_bytes = read_seal_bytes(project, constants)
    lines = parse_seal(start_bytes)
    done = plain_steps(lines)
    if not lines:
        raise Refused('SEAL_STEP_MISSING', 'no seal step has been written. Before seal step 1 nothing is sealed, so there is nothing to repair.')
    earlier = sum(1 for line in lines if line['step'] == step)
    if int(found.group(2)) != earlier + 1:
        raise Refused('REPAIR_ID_OUT_OF_ORDER', 'the next repair id of this kind is %s%d' % (found.group(1), earlier + 1))
    force = files_in_force(lines)
    folder = '%s/%s/%s' % (work, REPAIR_FOLDER, repair_id)
    # Amendment A5: each repair line has a window. Outside it nothing is written; the refusal is REPAIR_OUTSIDE_ITS_WINDOW.
    # After the window a fault means: stop, report, a new reviewed plan version.
    if kind == 'JOB_PROGRAMS':
        if '6_PROGRAMS' not in done or '7_PRECHECK' in done:
            raise Refused(OUTSIDE_WINDOW, 'a %s line may stand only after 6_PROGRAMS and before 7_PRECHECK, so before any call to model B. '
                          'Before seal step 6 a job program is simply corrected. After seal step 7 a fault in a job program means: stop, report, '
                          'a new reviewed plan version' % step)
        if earlier >= rules['job_programs']['max_repairs']:
            raise Refused('NO_PROGRAM_REPAIR_LEFT', 'the seal file already holds %d %s line(s); the plan allows %d. No launch; report to the owner.'
                          % (earlier, step, rules['job_programs']['max_repairs']))
        failed_precheck_facts(project, constants, folder, args, lines)      # refuses unless a failed pre-check on the sealed package is on record
        may = [path for path in rules['job_programs']['files_that_may_change'] if path in force]
    else:
        final_files = [f for name in QUESTION_FOLDERS for f in files_under(project, '%s/%s' % (work, name))
                       if has_set(f.rsplit('/', 1)[-1], 'final')]
        if FINAL_QUESTIONS_STEP in done or final_files:
            raise Refused(OUTSIDE_WINDOW, 'a %s line may be written only while no final question exists: the practice set is still being processed. '
                          'The seal file %s the line %s, and %d final file(s) lie under %s%s. A fault in a tool after the first final question exists means: '
                          'stop, report, a new reviewed plan version'
                          % (step, 'holds' if FINAL_QUESTIONS_STEP in done else 'does not hold', FINAL_QUESTIONS_STEP, len(final_files),
                             ', '.join('%s/%s/' % (work, name) for name in QUESTION_FOLDERS),
                             (': ' + ', '.join(final_files[:8]) + (' ...' if len(final_files) > 8 else '')) if final_files else ''))
        may = [path for path in constants['seal']['tools_sealed_in_step_1'] if path in force]
    changed, other = [], []
    for path, item in sorted(force.items()):
        target = project / path
        if not target.is_file():
            other.append('%s (step %s): MISSING' % (path, item['step']))
            continue
        size, digest = file_facts(target)
        if size != item['bytes'] or digest != item['sha256']:
            if path in may:
                changed.append(path)
            else:
                other.append('%s (step %s): CHANGED' % (path, item['step']))
    if other:
        raise Refused('SEALED_FILE_CHANGED', 'a repair of this kind may change only %s. A repair never changes the plan, the constants, a brief, a threshold, '
                      'a key, a task or a note. These other sealed files are missing or changed: %s' % (may, '; '.join(other)))
    if not changed:
        raise Refused('NOTHING_TO_REPAIR', 'no file that this repair may change differs from its values in force')
    in_folder = files_under(project, folder)
    partial = [f for f in in_folder if f.endswith('.partial')]
    if partial:
        raise Refused('HALF_WRITTEN_FILE', 'a .partial file means a write did not finish: %s' % ', '.join(partial))
    names = [path.rsplit('/', 1)[-1] for path in changed]
    if len(set(names)) != len(names):
        raise Refused('FILE_NAMED_TWICE', 'two changed files have the same file name; their old copies would collide')
    repaired, old_data = [], {}
    for path in changed:
        old_copy = '%s/old/%s' % (folder, path.rsplit('/', 1)[-1])
        if not (project / old_copy).is_file():
            raise Refused('FILE_MISSING', '%s (the old copy of %s)' % (old_copy, path))
        old_data[path] = (project / old_copy).read_bytes()
        if len(old_data[path]) != force[path]['bytes'] or sha256_bytes(old_data[path]) != force[path]['sha256']:
            raise Refused('OLD_COPY_NOT_THE_SEALED_FILE', '%s does not have the sha256 that was in force for %s (%s)' % (old_copy, path, force[path]['sha256']))
        repaired.append({'path': path, 'old_sha256': force[path]['sha256'], 'new_sha256': file_facts(project / path)[1], 'old_copy': old_copy})
    extra_old = [f for f in in_folder if f.startswith(folder + '/old/') and f not in {row['old_copy'] for row in repaired}]
    if extra_old:
        raise Refused('OLD_COPY_OF_AN_UNCHANGED_FILE', 'these old copies belong to no changed file: %s. A file that did not change is not listed.' % extra_old)
    diff_path = '%s/diff.txt' % folder
    if not (project / diff_path).is_file() or (project / diff_path).stat().st_size == 0:
        raise Refused('FILE_MISSING', '%s (a unified diff, old against new, of every changed file)' % diff_path)
    diff = (project / diff_path).read_bytes()
    if b'\r' in diff:
        raise Refused('DIFF_NOT_SOUND', '%s holds a CR. It is written with LF line ends.' % diff_path)
    review = check_review(project, constants, folder, repair_id, kind, changed, sha256_bytes(diff), force)
    values = {'repair_id': repair_id, 'repaired': repaired, 'fault': review['fault'], 'reviewer': review['reviewer'], 'review_verdict': review['verdict']}
    if kind == 'JOB_PROGRAMS':
        examples = constants['scorer']['examples_file']
        if examples in changed:
            try:
                before, after = expected_categories(old_data[examples]), expected_categories((project / examples).read_bytes())
            except (ValueError, KeyError, TypeError):
                raise Refused('FILE_NOT_READABLE', '%s or its old copy is not a readable known-examples file' % examples)
            moved = sorted(name for name, category in before.items() if after.get(name) != category)
            if moved:
                raise Refused('KNOWN_EXAMPLE_CHANGED', 'the expected category of these known examples differs from the old copy, or the example is gone: %s. '
                              'No expected category may change in a repair.' % moved)
        values['failed_precheck'] = failed_precheck_facts(project, constants, folder, args, lines)
    else:
        deleted = []
        for text in args.deleted or []:
            path, _, digest = text.partition('=')
            path = path.replace('\\', '/')
            if not path.startswith(work + '/') or '..' in path.split('/') or not re.fullmatch(r'[0-9a-f]{64}', digest):
                raise Refused('BAD_ARGUMENT', '--deleted takes PATH=SHA256, with a path under %s/ and the sha256 the file had before it was deleted. Got: %r' % (work, text))
            if path in force:
                raise Refused('SEALED_FILE_IS_NEVER_DELETED', '%s is a sealed file' % path)
            if (project / path).exists():
                raise Refused('FILE_STILL_THERE', '%s is named as deleted and still exists. A derived file that the fault could have changed is deleted first; the repaired tool derives it again after this line.' % path)
            deleted.append({'path': path, 'sha256': digest})
        values['could_have_changed_a_sealed_output'] = False
        values['unsealed_files_deleted'] = deleted
    records = []
    for path in changed:
        size, digest = file_facts(project / path)
        if size == 0:
            raise Refused('FILE_EMPTY', path)
        records.append({'path': path, 'package_path': force[path].get('package_path'), 'bytes': size, 'sha256': digest})
    for path in files_under(project, folder):
        if path in force:
            raise Refused('FILE_ALREADY_SEALED', '%s was sealed by an earlier line' % path)
        size, digest = file_facts(project / path)
        if size == 0:
            raise Refused('FILE_EMPTY', path)
        records.append({'path': path, 'package_path': None, 'bytes': size, 'sha256': digest})
    return add_line(project, constants, start_bytes, lines, step, records, values, [], args.dry_run)


# ----------------------------------------------------------------------------- status

def show_status(project, verify_only):
    project = Path(project).resolve()
    constants = load_constants(project)
    lines = read_seal(project, constants)
    path = seal_path(project, constants)
    if not lines:
        print('No seal step has been written. %s does not exist or is empty. The next step is %s.' % (path.relative_to(project).as_posix(), ORDER[0]))
        return 0
    for line in lines:
        print('line %d  %-32s %s  %d file(s)' % (line['n'], line['step'], line['utc'], len(line['files'])))
        if not verify_only and line['values']:
            print('        values: %s' % json.dumps(line['values'], ensure_ascii=False))
    problems = changed_files(project, lines)
    total = len(files_in_force(lines))
    if problems:
        print('SEALED FILES THAT ARE MISSING OR CHANGED: %d of %d' % (len(problems), total))
        for problem in problems:
            print('  ' + problem)
        print('The way out is to put the sealed bytes back, or a repair line under the rule of plan section 11.1 (ob_seal.py repair).')
        return 2
    done = plain_steps(lines)
    print('The chain of %d line(s) is whole (%d repair line(s)). All %d sealed file(s) have their size and sha256 in force.'
          % (len(lines), len(lines) - len(done), total))
    print('The next step is %s.' % (ORDER[len(done)] if len(done) < len(ORDER) else 'none; every step is written'))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description='Option B: the append-only seal file.')
    parser.add_argument('--project', default=str(PROJECT), help='the CASALESCENCE_NOETICS_v0_1 folder')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status', help='the lines written so far, with a full re-hash')
    sub.add_parser('verify', help='re-hash every sealed file')
    step = sub.add_parser('step', help='write one seal step')
    step.add_argument('name', help='1, 2, 3A, 3B, 3C, 4, 5, 6 or 7 (or the full step name)')
    step.add_argument('--dry-run', action='store_true', help='run every check, print the line, write nothing')
    step.add_argument('--receipt', default=None, help='step 7: the supervisor_receipt.json the pre-check job returned, unchanged')
    step.add_argument('--selftest-json', default=None, help='step 7: the selftest.json the pre-check job returned')
    step.add_argument('--source-zip', default=None, help='step 7: the source.zip the pre-check job ran on')
    repair = sub.add_parser('repair', help='write one repair line from optionb/repairs/<repair id>/')
    repair.add_argument('repair_id', help='6R1 or 6R2 for the job programs; TR1, TR2, ... for the tools')
    repair.add_argument('--dry-run', action='store_true', help='run every check, print the line, write nothing')
    repair.add_argument('--source-zip', default=None, help='6R: the source.zip the failed pre-check ran on, if its receipt lacks the hash')
    repair.add_argument('--deleted', action='append', default=None, metavar='PATH=SHA256',
                        help='TR: a derived, unsealed file that was deleted to be derived again, with the sha256 it had; may be given more than once')
    word = sub.add_parser('status-word', help='print the outcome code and its status word from the owner\'s table')
    word.add_argument('--result', default=None, help='the RESULT.json the job returned')
    word.add_argument('--no-result-file', action='store_true', help='the job returned no RESULT.json')
    word.add_argument('--code', default=None, help='only RESULT_UNREADABLE')
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):      # FILE_FORMATS.md section 0: a laptop tool prints in UTF-8
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', newline=chr(10))
    try:
        if args.command in ('status', 'verify'):
            return show_status(args.project, args.command == 'verify')
        if args.command == 'status-word':
            return status_word(args.project, args)
        if args.command == 'repair':
            write_repair(args.project, args.repair_id.upper(), args)
            return 0
        name = SHORT.get(args.name.upper(), args.name)
        if name not in STEPS:
            raise Refused('UNKNOWN_STEP', '%r is not one of %s' % (args.name, ', '.join(SHORT)))
        write_step(args.project, name, args)
        return 0
    except Refused as refusal:
        print('REFUSED: %s: %s. Nothing was written.' % (refusal.code, str(refusal.detail).rstrip('.')))
        return 2


if __name__ == '__main__':
    sys.exit(main())
