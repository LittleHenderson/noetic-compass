"""Option B, last build step before seal step 5. Assemble the prompt parts the AWS job reads.

What this tool does, in plain words:
- It keeps a passage only if it carries a task, passed the support check and was not hit by the
  answer-leak screen.
- It sets the letters of the options, last of all, by the plan's seeded rule. The letters are dealt
  in turn over the whole task family, type after type, without starting again at A for a new type.
  So each letter is right equally often, to within one task, inside every type and over the whole
  family, at each level. The option order is the same in every group.
- It writes the prompt parts as two large files (practice and final). Per passage: the text and the
  notes text of every group (FILLER, ROLE, MIXED, QUOTES-ONLY, and three lengths for each ordinary
  group). Per task: the question, the options with letters at level 1 and, for a role-step task, at
  level 2, and the must-run groups. The practice file also holds the ANSWER-GIVEN notes of the
  practice role-step tasks. Padding is NOT applied here. The job applies it with model B's tokenizer.
- The NO-PASSAGE condition needs no part of its own: the job builds it from the question and the
  options. Its calls are in the list of planned calls.
- It NEVER writes a key into the prompt parts of the final set. The lettered keys go to their own
  folders: keys_practice/ and keys_final/. The only place a prompt part names a right letter is the
  practice-only ANSWER-GIVEN note.
- It writes the removal log: every dropped question, note or passage with the program and the rule
  that removed it, the survival count per filter, the final counts, the launch floor and the tier.
- It writes the list of planned calls and checks the total against the call cap.
- It ends by writing a manifest with a sha256 per file, for seal step 5.

Canon check: the canon definition lines inside the ROLE and MIXED notes are compared, letter for
letter, with the lines of Part A of the labeling guide. This tool reads the guide for that. It does
not retype or reword a line. The struck group ROLE-PLAIN has no code path here.
Amendment A13: the sayings lines are checked in the same way. This tool reads the table of the
canonical sayings from its pinned file (sources.canonical_sayings; it lies outside the study folder),
checks that every definition cell of the table equals the guide, and compares every sayings line,
letter for letter. The head of a ROLE or MIXED note must be, for each of its Noetics in number
order: its canon line, then its sayings line.

A passage with a note the writer could not produce (the status DROPPED_NOTE_NOT_WRITTEN of the
support results; plan section 10, Step 7) did not pass the support check. It is dropped like a
passage with DROPPED_SECOND_FAILURE and logged under STEP_7_SUPPORT_CHECK.

This tool calls no outside service and needs no key.

It refuses to run unless seal steps 1, 2, 3A, 3B, 3C and 4 exist. It refuses to write once seal
step 5 exists.

Usage:
  ob_assemble.py

Files (FILE_FORMATS.md sections 11 and 12):
  removal_log.json
  prompts/prompt_parts_practice.json     prompts/prompt_parts_final.json
  keys_practice/keys_practice.json       keys_practice/task_meta_practice.json
  keys_final/keys_final.json             keys_final/task_meta_final.json
  review/review_pack.json
Two more files that FILE_FORMATS.md does not name yet (reported as an open issue):
  assemble/planned_calls.json            the list of planned calls and the cap check
  assemble/manifest_step5.json           one sha256 per file, for seal step 5

If the launch floor is not met, or the planned calls are above the cap, ONLY removal_log.json is
written. No prompt part, no key file and no manifest is written. So seal step 5 can not be made.

Exit codes: 0 = assembled. 2 = not started or stopped by a check. 3 = the removal log is written and
nothing else: do not launch.

Dry fixture: with --work pointing under optionb/dry/ every output is marked as a dry fixture.
"""
import argparse
import datetime
import hashlib
import json
import os
import random
import re
import sys
import time
from fractions import Fraction
from pathlib import Path

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve()
ROOT = HERE.parent.parent
REAL_WORK = (ROOT / 'optionb').resolve()
DRY_BASE = REAL_WORK / 'dry'
PROGRAM = 'tools/' + HERE.name
DRY_TAG = ' [DRY FIXTURE, NOT A RESULT]'
OVERRIDES_NAME = 'DRY_CONSTANT_OVERRIDES.json'
SEAL_NAME = 'SEAL_OPTIONB.jsonl'
LF = chr(10)

SEAL_NEED = ['1_PLAN_AND_SOURCES', '2_ROLE_NOTES', '3A_PRACTICE_QUESTIONS_AND_KEYS', '3B_PRACTICE_SET_FIXED',
             '3C_FINAL_QUESTIONS_AND_KEYS', '4_ORDINARY_NOTES']
SEAL_STEP = '5_PROMPT_PARTS_AND_REMOVAL_LOG'
SETS = ('practice', 'final')
BASE_GROUP = 'NONE'
ROLE_TEXT_FIELD = {'ROLE': 'role_text', 'MIXED': 'mixed_text', 'QUOTES-ONLY': 'quotes_only_text'}
ROLE_TAG_FIELD = {'ROLE': 'noetic', 'MIXED': 'mixed_noetic'}
TASK_FIELDS = ['task_id', 'passage_id', 'family', 'question', 'options', 'groups']
# FILE_FORMATS.md section 9.5: the statuses of a finished support check, and those of them that drop the passage.
# NOT_WRITTEN is also named in PLAN_CONSTANTS.json (ordinary_notes.not_written_status); main() stops if the two differ.
NOT_WRITTEN = 'DROPPED_NOTE_NOT_WRITTEN'
SUPPORT_DROPPED = ('DROPPED_SECOND_FAILURE', NOT_WRITTEN)
SUPPORT_FINAL = ('ALL_PASS',) + SUPPORT_DROPPED
NOTE_WRITER = 'tools/ob_write_ordinary_notes.py'
STEPS = ['STEP_1_WRITER', 'STEP_2_FORM_CHECK', 'STEP_3A_ANCHOR_CHECK', 'STEP_3B_OPTION_CHECK', 'STEP_4_KEY_CHECK',
         'STEP_5_NO_PASSAGE_CHECK', 'STEP_6_SELECTION', 'STEP_6_LENGTH_BACKSTOP', 'STEP_7_SUPPORT_CHECK', 'STEP_7_LEAK_SCREEN']
FILTERS = ['written for an open form', 'form check', 'anchor check', 'option check', 'key check', 'no-passage check',
           'selection', 'length backstop', 'support check', 'answer-leak screen']
# the files of FILE_FORMATS.md section 14 that travel in the job package, by their path under optionb/
IN_PACKAGE = ['prompts/prompt_parts_practice.json', 'prompts/prompt_parts_final.json', 'keys_practice/keys_practice.json',
              'keys_practice/task_meta_practice.json', 'keys_final/keys_final.json', 'keys_final/task_meta_final.json']


class Stop(Exception):
    """A clean stop. The first argument is a code, the second a plain sentence."""


# ---------------------------------------------------------------- shared helpers

def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def rel(path):
    path = Path(path).resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def merge(base, extra):
    for name, value in extra.items():
        if name == 'note':
            continue
        if isinstance(value, dict) and isinstance(base.get(name), dict):
            merge(base[name], value)
        else:
            base[name] = value


def fill(template, values):
    """Fill <<NAME>> placeholders in one pass. Filled-in text is never scanned again."""
    def one(match):
        if match.group(1) not in values:
            raise Stop('UNKNOWN_PLACEHOLDER', 'A plan text holds the placeholder <<%s>> and this program has no value for it.' % match.group(1))
        return values[match.group(1)]
    return re.sub(r'<<([A-Z_]+)>>', one, template)


class Ctx:
    """The work folder, the plan constants and the list of files this run has read."""

    def __init__(self, work_arg):
        work = Path(work_arg).resolve() if work_arg else REAL_WORK
        self.dry = work != REAL_WORK
        if self.dry and DRY_BASE not in work.parents:
            raise Stop('WORK_FOLDER_NOT_ALLOWED', 'A work folder other than optionb/ must sit under optionb/dry/.')
        self.work = work
        self.inputs = {}
        self.constants = self.read_json(REAL_WORK / 'PLAN_CONSTANTS.json')
        over = work / OVERRIDES_NAME
        if self.dry and over.exists():
            merge(self.constants, self.read_json(over))

    def now(self):
        return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    def read_bytes(self, path):
        data = Path(path).read_bytes()
        self.inputs[rel(path)] = sha_bytes(data)
        return data

    def read_json(self, path):
        return json.loads(self.read_bytes(path).decode('utf-8'))

    def need_json(self, name, schema, set_name=None):
        path = self.work / name
        if not path.exists():
            raise Stop('INPUT_MISSING', '%s does not exist.' % rel(path))
        doc = self.read_json(path)
        if doc.get('schema') != schema:
            raise Stop('WRONG_FILE', '%s does not carry the schema name %s.' % (rel(path), schema))
        if set_name is not None and doc.get('set') != set_name:
            raise Stop('WRONG_FILE', '%s is not a file of the %s set.' % (rel(path), set_name))
        return doc

    def header(self, schema):
        return {'schema': schema,
                'made_by': {'program': PROGRAM + (DRY_TAG if self.dry else ''), 'sha256': sha_bytes(HERE.read_bytes()), 'utc': self.now()},
                'inputs': [{'path': p, 'sha256': s} for p, s in sorted(self.inputs.items())]}

    def write_json(self, name, schema, body):
        doc = self.header(schema)
        doc.update(body)
        path = self.work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_name(path.name + '.partial')
        with open(partial, 'w', encoding='utf-8', newline=LF) as stream:
            stream.write(json.dumps(doc, indent=1, ensure_ascii=False, allow_nan=False) + LF)
        replace_file(partial, path)
        return path


def replace_file(partial, path):
    """Rename with a few tries. A file-sync program may hold the target for a moment."""
    for attempt in range(6):
        try:
            os.replace(partial, path)
            return
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(0.3)


def check_seal(ctx, need, closed_by):
    """Stop unless the needed seal steps exist and every sealed file is unchanged.

    Returns a sentence for the report and the map {sealed path: sha256} (None when nothing was checked).
    """
    path = ctx.work / SEAL_NAME
    if not path.exists():
        if ctx.dry:
            return 'not checked: this dry folder has no seal file', None
        raise Stop('SEAL_FILE_MISSING', 'optionb/%s does not exist. Seal steps %s are needed first.' % (SEAL_NAME, ', '.join(need)))
    lines = [line for line in ctx.read_bytes(path).split(b'\n') if line.strip()]
    # The hash in force (FILE_FORMATS.md section 15.2): for a path that more than one seal line lists, the
    # latest line counts. Only a repair line may list a path again. The eleven tools are sealed in step 1,
    # so this check also stops a tool that was changed without a repair line.
    repair_steps = set(ctx.constants['repairs']['seal_steps'].values())
    steps, in_force = [], {}
    for index, line in enumerate(lines):
        row = json.loads(line.decode('utf-8'))
        if row.get('n') != index + 1:
            raise Stop('SEAL_FILE_BROKEN', 'Seal line %d does not carry n = %d.' % (index + 1, index + 1))
        if row.get('previous_line_sha256') != (sha_bytes(lines[index - 1]) if index else None):
            raise Stop('SEAL_FILE_BROKEN', 'Seal line %d does not chain to the line before it.' % (index + 1))
        for item in row.get('files', []):
            if item['path'] in in_force and row.get('step') not in repair_steps:
                raise Stop('SEAL_FILE_BROKEN', 'Seal line %d lists %s again and is not a repair line.' % (index + 1, item['path']))
            in_force[item['path']] = (item['bytes'], item['sha256'], row.get('step'))
        steps.append(row.get('step'))
    for name, (size, digest, step) in sorted(in_force.items()):
        target = ROOT / name
        if not target.exists():
            raise Stop('SEALED_FILE_MISSING', '%s was sealed in step %s and is gone.' % (name, step))
        data = target.read_bytes()
        if len(data) != size or sha_bytes(data) != digest:
            raise Stop('SEALED_FILE_CHANGED', '%s was sealed in step %s and has changed.' % (name, step))
    sealed = {name: digest for name, (size, digest, step) in in_force.items()}
    for step in need:
        if step not in steps:
            raise Stop('SEAL_STEP_MISSING', 'Seal step %s must exist before this program runs.' % step)
    if closed_by and closed_by in steps:
        raise Stop('SET_IS_SEALED', 'Seal step %s exists. These files are sealed and are not written again.' % closed_by)
    return 'checked: %d seal lines, all sealed files unchanged' % len(steps), sealed


def must_be_sealed(ctx, sealed, paths):
    """Every listed input must be named in a seal line. (A dry folder checks only its own files.)"""
    if sealed is None:
        return
    for path in paths:
        path = Path(path).resolve()
        if ctx.dry and ctx.work not in path.parents:
            continue
        if rel(path) not in sealed:
            raise Stop('INPUT_NOT_SEALED', '%s is read by this program and is not named in any seal line.' % rel(path))


def one_decimal(value):
    """A fraction as text with one decimal, for example 4.1. No decimal number is stored."""
    tenths = (value.numerator * 20 + value.denominator) // (2 * value.denominator)
    return '%d.%d' % (tenths // 10, tenths % 10)


# ---------------------------------------------------------------- the canon lines

def canon_from_guide(ctx):
    """Read the canon lines from Part A of the labeling guide, as the plan's rule says. Nothing is retyped."""
    C = ctx.constants
    rule, source = C['role_notes'], C['sources']['labeling_guide']
    data = ctx.read_bytes(ROOT / source['path'])
    if len(data) != source['bytes'] or sha_bytes(data) != source['sha256']:
        raise Stop('SOURCE_HASH_MISMATCH', '%s does not have the hash pinned in PLAN_CONSTANTS.json.' % source['path'])
    text = data.decode('utf-8').replace('\r\n', LF)
    start = text.find(rule['canon_section_start'])
    end = text.find(rule['canon_section_end'], start + 1)
    if start < 0 or end < 0:
        raise Stop('CANON_NOT_FOUND', 'Part A of the labeling guide was not found.')
    pattern, found = re.compile(rule['canon_line_regex']), {}
    for line in text[start:end].split(LF):
        match = pattern.match(line)
        if match:
            if match.group(1) in found:
                raise Stop('CANON_NOT_FOUND', 'Part A of the labeling guide holds two lines for %s.' % match.group(1))
            found[match.group(1)] = (match.group(2), match.group(3))
    if len(found) != rule['canon_lines_expected'] or any(noetic not in found for noetic in rule['canon_noetics_used']):
        raise Stop('CANON_NOT_FOUND', 'Part A of the labeling guide does not hold the %d canon lines the plan expects.' % rule['canon_lines_expected'])
    lines = {noetic: fill(rule['canon_note_line'], {'NOETIC': noetic, 'NAME': found[noetic][0], 'DEFINITION': found[noetic][1]})
             for noetic in rule['canon_noetics_used']}
    return lines, {noetic: definition for noetic, (name, definition) in found.items()}


def sayings_from_table(ctx, definitions):
    """Read the sayings lines from the table of the canonical sayings, as the plan's rule says (amendment A13). Nothing is retyped.

    definitions maps each Noetic of guide Part A to its definition text. The table must give one row
    for each of them, and each definition cell must equal the guide, letter for letter.
    """
    rule = ctx.constants['role_notes']
    source = ctx.constants['sources'][rule['sayings_source_key']]
    path = ROOT / source['path']          # the file lies outside the study folder; its pinned path is counted from the study folder
    if not path.is_file():
        raise Stop('SOURCE_MISSING', '%s was not found.' % source['path'])
    data = path.read_bytes()
    ctx.inputs[source['path']] = sha_bytes(data)      # listed under its pinned path, not under a path of this machine
    if len(data) != source['bytes'] or sha_bytes(data) != source['sha256']:
        raise Stop('SOURCE_HASH_MISMATCH', '%s does not have the hash pinned in PLAN_CONSTANTS.json.' % source['path'])
    rows = data.decode('utf-8').replace('\r\n', LF).split(LF)
    starts = [index for index, row in enumerate(rows) if row.startswith(rule['sayings_section_start'])]
    ends = [index for index, row in enumerate(rows) if starts and index > starts[0] and row.startswith(rule['sayings_section_end'])]
    if len(starts) != 1 or not ends:
        raise Stop('SAYINGS_NOT_FOUND', 'The table of the canonical sayings was not found in %s.' % source['path'])
    pattern, group, found = re.compile(rule['sayings_row_regex']), rule['sayings_row_groups'], {}
    for row in rows[starts[0]:ends[0]]:
        match = pattern.match(row)
        if match:
            if match.group(group['noetic']) in found:
                raise Stop('SAYINGS_NOT_FOUND', 'The table of the canonical sayings holds two rows for %s.' % match.group(group['noetic']))
            found[match.group(group['noetic'])] = (match.group(group['definition']), match.group(group['sayings']))
    if len(found) != rule['sayings_rows_expected'] or set(found) != set(definitions) or any(noetic not in found for noetic in rule['sayings_noetics_used']):
        raise Stop('SAYINGS_NOT_FOUND', 'The table of the canonical sayings does not hold the %d rows the plan expects, one for each Noetic of guide Part A.'
                   % rule['sayings_rows_expected'])
    differ = sorted(noetic for noetic in found if found[noetic][0] != definitions[noetic])
    if differ:
        raise Stop('SAYINGS_DEFINITION_DIFFERS_FROM_THE_GUIDE', 'For %s the definition cell of the table of the sayings is not the definition of the labeling guide, '
                   'letter for letter. The two must agree. Nobody picks one of the two texts.' % ', '.join(differ))
    return {noetic: fill(rule['sayings_note_line'], {'SAYINGS': found[noetic][1]}) for noetic in rule['sayings_noetics_used']}


def check_canon(ctx, role_notes, kept_ids):
    """Stop unless the head of every kept ROLE or MIXED note is the guide's lines and the table's sayings, letter for letter.

    Returns (canon lines read from the guide, sayings lines read from the table).
    """
    C = ctx.constants
    lines, definitions = canon_from_guide(ctx)
    sayings = sayings_from_table(ctx, definitions)
    canon = role_notes['canon']
    if canon.get('sha256') != C['sources']['labeling_guide']['sha256']:
        raise Stop('CANON_SOURCE_DIFFERS', 'notes_role/role_notes.json names another labeling guide hash than PLAN_CONSTANTS.json.')
    for noetic, line in canon['lines'].items():
        if lines.get(noetic) != line:
            raise Stop('CANON_LINE_NOT_WORD_FOR_WORD', 'The canon line for %s in notes_role/role_notes.json is not the line of the labeling guide.' % noetic)
    source = C['sources'][C['role_notes']['sayings_source_key']]
    if canon.get('sayings_sha256') != source['sha256'] or canon.get('sayings_source') != source['path']:
        raise Stop('SAYINGS_SOURCE_DIFFERS', 'notes_role/role_notes.json does not name the source of the sayings and its hash as PLAN_CONSTANTS.json gives them.')
    if canon.get('sayings_lines') != sayings:
        raise Stop('SAYINGS_LINE_NOT_WORD_FOR_WORD', 'A sayings line in notes_role/role_notes.json is not the line built from the table of the canonical sayings, '
                   'or a line is missing.')
    swap = C['role_notes']['mixed_swap_table']
    by_id = {passage['id']: passage for passage in role_notes['passages']}
    for pid in kept_ids:
        passage = by_id[pid]
        entries = passage['entries']
        if any(entry['mixed_noetic'] != swap[entry['noetic']] for entry in entries):
            raise Stop('MIXED_TAGS_NOT_BY_THE_TABLE', 'The MIXED tags of %s are not the plan\'s swap table applied to the ROLE tags.' % pid)
        for group, tag in ROLE_TAG_FIELD.items():
            full = passage[ROLE_TEXT_FIELD[group]].split(LF)
            # the head (FILE_FORMATS.md section 18): for each Noetic shown, in number order, its canon line, then its sayings line
            expect = [line for noetic in sorted({entry[tag] for entry in entries}, key=lambda name: int(name[1:]))
                      for line in (lines[noetic], sayings[noetic])]
            if full[:len(full) - len(entries)] != expect:
                raise Stop('CANON_LINES_IN_NOTE_NOT_AS_PLANNED', 'The %s note of %s does not open with exactly the canon line and the sayings line of each of '
                           'its Noetics, in number order.' % (group, pid))
        if len(passage['quotes_only_text'].split(LF)) != len(entries):
            raise Stop('QUOTES_ONLY_NOT_AS_PLANNED', 'The QUOTES-ONLY note of %s does not have one line per entry and nothing else.' % pid)
    return len(lines), len(sayings)


# ---------------------------------------------------------------- one set: what is kept

def in_practice(role, count, start):
    """Whether a setting role belongs to the practice set, for a given number of practice settings."""
    if role == 'practice':
        return True
    found = re.fullmatch(r'reserve_([0-9]+)', role)
    return bool(found) and int(found.group(1)) <= count - start


def load_set(ctx, set_name, passes):
    S = 'casalescence/optionb/'
    data = {
        'raw': {p: ctx.need_json('questions/raw_questions_%s_%s.json' % (set_name, p), S + 'raw_questions/v1', set_name) for p in passes},
        'form': ctx.need_json('checks/form_check_%s.json' % set_name, S + 'form_check/v1', set_name),
        'anchor': ctx.need_json('checks/anchor_check_%s.json' % set_name, S + 'anchor_check/v1', set_name),
        'option': ctx.need_json('checks/option_check_%s.json' % set_name, S + 'option_check/v1', set_name),
        'candidates': ctx.need_json('checks/candidates_%s.json' % set_name, S + 'candidates/v1', set_name),
        'key_check': ctx.need_json('solve/key_check_%s.json' % set_name, S + 'key_check/v1', set_name),
        'selection': ctx.need_json('select/selection_%s.json' % set_name, S + 'selection/v1', set_name),
        'notes': ctx.need_json('notes_ord/ordinary_notes_%s.json' % set_name, S + 'ordinary_notes/v1', set_name),
        'support': ctx.need_json('support/support_results_%s.json' % set_name, S + 'support_results/v1', set_name),
        'screen': ctx.need_json('screen/leak_screen_%s.json' % set_name, S + 'leak_screen/v1', set_name)}
    sealed_names = ['questions/raw_questions_%s_%s.json' % (set_name, p) for p in passes]
    sealed_names += [name % set_name for name in ('checks/form_check_%s.json', 'checks/anchor_check_%s.json', 'checks/option_check_%s.json',
                                                  'checks/candidates_%s.json', 'solve/key_check_%s.json', 'select/selection_%s.json',
                                                  'notes_ord/ordinary_notes_%s.json', 'support/support_results_%s.json')]
    return data, sealed_names


def kept_of_set(ctx, set_name, data):
    """The passages and tasks that are kept: they carry a task, passed the support check and were not hit by the screen."""
    tasks = data['selection']['tasks']
    carry = sorted({task['passage_id'] for task in tasks})
    status = {passage['passage_id']: passage['status'] for passage in data['support']['passages']}
    not_final = [pid for pid in carry if status.get(pid) not in SUPPORT_FINAL]
    if not_final:
        raise Stop('SUPPORT_CHECK_NOT_FINISHED', 'The support check of the %s set is not finished (first open passage: %s).' % (set_name, not_final[0]))
    dropped = {pid for pid in carry if status[pid] in SUPPORT_DROPPED}
    then = {item['path']: item['sha256'] for item in data['screen'].get('inputs', [])}
    for name in ('select/selection_%s.json', 'notes_ord/ordinary_notes_%s.json', 'support/support_results_%s.json'):
        key = rel(ctx.work / (name % set_name))
        if then.get(key) != ctx.inputs[key]:
            raise Stop('SCREEN_IS_STALE', 'screen/leak_screen_%s.json was made from another version of %s. Run tools/ob_screen_notes.py again.' % (set_name, key))
    key = rel(ctx.work / 'notes_role' / 'role_notes.json')
    if then.get(key) != ctx.inputs[key]:
        raise Stop('SCREEN_IS_STALE', 'screen/leak_screen_%s.json was made from another version of the role notes.' % set_name)
    screened = {row['passage_id']: row for row in data['screen']['passages']}
    if set(screened) != set(carry) - dropped:
        raise Stop('SCREEN_DOES_NOT_MATCH', 'screen/leak_screen_%s.json does not list exactly the passages that carry a task and passed the support check.' % set_name)
    hit = {pid for pid, row in screened.items() if row['hit']}
    kept = [pid for pid in carry if pid not in dropped and pid not in hit]
    return {'carry': carry, 'dropped': dropped, 'hit': hit, 'kept': kept,
            'tasks': sorted((task for task in tasks if task['passage_id'] in kept), key=lambda task: task['task_id'])}


# ---------------------------------------------------------------- the removal log

def removal_of_set(C, set_name, data, kept, elig, passes):
    """The log entries of one set and its survival rows."""
    entries = []

    def add(step, program, thing, ident, rule, detail=''):
        entries.append({'set': set_name, 'step': step, 'program': program, 'object': thing, 'id': ident, 'rule': rule, 'detail': detail})

    form = {row['question_id']: row for row in data['form']['rows']}
    anchor = {row['question_id']: row for row in data['anchor']['rows']}
    option = {row['question_id']: row for row in data['option']['rows']}

    def ok_form(qid):
        return qid in form and form[qid]['passed'] is True

    def ok_anchor(qid):
        return ok_form(qid) and qid in anchor and anchor[qid]['passed'] is True

    def ok_option(qid):
        return ok_anchor(qid) and qid in option and option[qid]['passed'] is True

    # Step 1: what the writer did not give in a usable form
    for name in passes:
        for passage in data['raw'][name]['passages']:
            if passage['status'] != 'OK':
                add('STEP_1_WRITER', 'tools/ob_write_questions.py', 'passage', passage['passage_id'], passage['status'],
                    'pass %s: the writer gave no usable object for this passage' % name)
            for extra in passage.get('extra_dropped', []):
                add('STEP_1_WRITER', 'tools/ob_write_questions.py', 'question', '%s.%s.%s' % (passage['passage_id'], name, extra.get('form')),
                    'EXTRA_QUESTION_FOR_A_FORM_ALREADY_USED', 'pass %s: a later question for a form the writer already used on this passage' % name)
    # Steps 2 and 3
    for row in data['form']['rows']:
        for reason in ([] if row['passed'] else row['reasons']):
            add('STEP_2_FORM_CHECK', 'tools/ob_check_questions.py', 'question', row['question_id'], reason.split(':', 1)[0], reason)
    for row in data['anchor']['rows']:
        if not row['passed']:
            add('STEP_3A_ANCHOR_CHECK', 'tools/ob_check_questions.py', 'question', row['question_id'], row['reason'])
    for row in data['option']['rows']:
        if not row['passed']:
            add('STEP_3B_OPTION_CHECK', 'tools/ob_check_questions.py', 'question', row['question_id'], 'OPTION_MATCHES_AN_ENTRY_ONLY_ONE_TEAM_GAVE',
                '; '.join('option %d matches the %s of a %s entry only team %s gave' % (h['option_index'], h['field'], h['noetic'], h['team'].upper()) for h in row['hits']))
    # Steps 4 and 5
    keys = {row['question_id']: row for row in data['key_check']['rows']}
    candidates = data['candidates']['candidates']
    for candidate in candidates:
        row = keys.get(candidate['question_id'])
        if row is None:
            raise Stop('KEY_CHECK_NOT_COMPLETE', 'solve/key_check_%s.json has no row for the candidate %s.' % (set_name, candidate['question_id']))
        if not row['key_check_passed']:
            add('STEP_4_KEY_CHECK', 'tools/ob_solve_blind.py', 'question', row['question_id'], 'NOT_BOTH_SOLVERS_RIGHT_WITH_THE_PASSAGE',
                '; '.join('%s: %s' % pair for pair in sorted(row['with_passage'].items())))
        elif not row['no_passage_passed']:
            add('STEP_5_NO_PASSAGE_CHECK', 'tools/ob_solve_blind.py', 'question', row['question_id'], 'BOTH_SOLVERS_RIGHT_WITHOUT_THE_PASSAGE',
                '; '.join('%s: %s' % pair for pair in sorted(row['no_passage'].items())))
    # Step 6
    selection = data['selection']
    backstop = [row for row in selection['dropped'] if row['reason'].startswith('LENGTH_BACKSTOP')]
    listed = {row['question_id'] for row in selection['dropped']}
    for row in selection['dropped']:
        if row in backstop:
            parts = row['question_id'].split('.')
            add('STEP_6_LENGTH_BACKSTOP', 'tools/ob_select.py', 'task', '%s.%s' % (parts[0], parts[-1]), row['reason'], 'question %s' % row['question_id'])
        else:
            add('STEP_6_SELECTION', 'tools/ob_select.py', 'question', row['question_id'], row['reason'])
    selected = {task['question_id'] for task in selection['tasks']}
    for candidate in candidates:
        qid = candidate['question_id']
        if keys[qid]['survives'] and qid not in selected and qid not in listed:
            passage = elig.get(candidate['passage_id'])
            if passage is None or not passage['eligible']:
                add('STEP_6_SELECTION', 'tools/ob_select.py', 'question', qid, 'PASSAGE_NOT_ELIGIBLE', 'no role note exists for this passage, so it carries no task')
            else:
                add('STEP_6_SELECTION', 'tools/ob_select.py', 'question', qid, 'NOT_SELECTED_NO_REASON_LOGGED',
                    'the question passed every check, is not a task, and select/selection_%s.json gives no reason' % set_name)
    # Step 7
    given_up = {}      # passage id -> the notes the writer gave up, with the logged reasons (FILE_FORMATS.md section 8.1, not_written)
    for passage in data['notes']['passages']:
        for group, by_length in passage['notes'].items():
            for length, slot in by_length.items():
                gone = slot.get('not_written')
                if gone:
                    given_up.setdefault(passage['passage_id'], []).append('%s|%s|%s|v%s (%s)' % (
                        passage['passage_id'], group, length, gone.get('version'), ', '.join(map(str, gone.get('errors', [])))))
    for passage in data['support']['passages']:
        for note_id in passage['rewrite_note_ids']:
            add('STEP_7_SUPPORT_CHECK', 'tools/ob_check_support.py', 'note', note_id, 'FIRST_VERSION_FAILED_WRITTEN_AGAIN_ONCE')
        if passage['status'] == 'DROPPED_SECOND_FAILURE':
            add('STEP_7_SUPPORT_CHECK', 'tools/ob_check_support.py', 'passage', passage['passage_id'], 'DROPPED_SECOND_FAILURE',
                'a rewritten note failed the support check again; the passage is dropped for every group')
        if passage['status'] == NOT_WRITTEN:
            # FILE_FORMATS.md section 11.1: logged under this step, with the program whose rule removed it
            add('STEP_7_SUPPORT_CHECK', NOTE_WRITER, 'passage', passage['passage_id'], NOT_WRITTEN,
                'the note writer could not produce a note (an empty or cut-off reply each time it was asked): %s; the passage is dropped for every group'
                % '; '.join(given_up.get(passage['passage_id'], ['the notes file names no such note'])))
    for row in data['screen']['passages']:
        for rule in sorted({hit['rule'] for hit in row['hits']}):
            mine = [hit for hit in row['hits'] if hit['rule'] == rule]
            where = mine[0]['group'] + (' ' + mine[0]['length'] if mine[0]['length'] else '')
            add('STEP_7_LEAK_SCREEN', 'tools/ob_screen_notes.py', 'passage', row['passage_id'], rule,
                '%d hit(s) of rule (%s); first: %s: %s' % (len(mine), rule, where, mine[0]['detail']))

    # survival (plan v1.1, counted as tools/ob_select.py counts it): role-step counts are per passage and form, plain-fact counts
    # are per passage; a pair counts at a filter when the question of ANY pass passes it (a later pass stands in where an
    # earlier one was dropped). Every pass is read alike; there is no first pass and no spare.
    role = {name: 0 for name in FILTERS}
    fact = {name: 0 for name in FILTERS}
    role_slots, fact_slots = {}, {}
    for name in passes:
        for passage in data['raw'][name]['passages']:
            pid, known = passage['passage_id'], elig.get(passage['passage_id'])
            for question in passage['what_follows']:
                if known and known['eligible'] and not known.get('barred') and question['form'] in known['open_forms']:
                    role_slots.setdefault((pid, question['form']), []).append(question['question_id'])
            if passage.get('plain_fact'):
                fact_slots.setdefault(pid, []).append(passage['plain_fact']['question_id'])
    for ids in role_slots.values():
        role['written for an open form'] += 1
        role['form check'] += any(ok_form(q) for q in ids)
        role['anchor check'] += any(ok_anchor(q) for q in ids)
        role['option check'] += any(ok_option(q) for q in ids)
    for ids in fact_slots.values():
        fact['written for an open form'] += 1
        fact['form check'] += any(ok_form(q) for q in ids)
    fact['anchor check'] = fact['option check'] = fact['form check']   # a plain-fact question has no label check
    by_family = {'role_step': role, 'plain_fact': fact}
    for family, counts in by_family.items():
        mine = [c for c in candidates if c['family'] == family]
        # the candidates are exactly the questions that passed the checks (the option check for role-step, the form check for plain-fact),
        # and the number of passage-and-form pairs with a candidate equals the option-check row
        ids = sorted(c['question_id'] for c in mine)
        expected = sorted(qid for qid, row in (option if family == 'role_step' else form).items()
                          if (ok_option(qid) if family == 'role_step' else (ok_form(qid) and row['family'] == 'plain_fact')))
        pairs = len({(c['passage_id'], c['form']) for c in mine})
        if ids != expected or pairs != counts['option check']:
            raise Stop('SURVIVAL_COUNT_DOES_NOT_MATCH', 'For the %s set this program counts %d %s passage-and-form pairs after the option check and %d questions that '
                       'passed the checks; checks/candidates_%s.json holds %d pairs and %d candidates.'
                       % (set_name, counts['option check'], family, len(expected), set_name, pairs, len(mine)))
        pair_of = {c['question_id']: (c['passage_id'], c['form']) for c in mine}
        counts['key check'] = len({pair_of[c['question_id']] for c in mine if keys[c['question_id']]['key_check_passed']})
        counts['no-passage check'] = len({pair_of[c['question_id']] for c in mine if keys[c['question_id']]['survives']})
        tasks = [task for task in selection['tasks'] if task['family'] == family]
        counts['length backstop'] = len(tasks)
        counts['selection'] = len(tasks) + (len(backstop) if family == 'role_step' else 0)
        counts['support check'] = sum(1 for task in tasks if task['passage_id'] not in kept['dropped'])
        counts['answer-leak screen'] = sum(1 for task in tasks if task['passage_id'] in kept['kept'])
    survival = [{'filter': name, 'role_step': role[name], 'plain_fact': fact[name]} for name in FILTERS]
    return entries, survival


def estimate_padding(C, kept_passages):
    """An estimate of the padding share per group, from size counts. Not from the tokenizer. No rule uses it."""
    size_rule = re.compile(C['role_notes']['size_count_regex'])
    order = C['ordinary_notes']['length_pick_tie_order']
    shortest = len(size_rule.findall(C['padding']['shortest_line']))
    total, count = {}, 0
    for notes in kept_passages:
        sizes = {group: len(size_rule.findall(notes[group])) for group in ('FILLER', 'ROLE', 'MIXED', 'QUOTES-ONLY')}
        for group in C['groups']['ordinary']:
            by_length = {length: len(size_rule.findall(text)) for length, text in notes[group].items()}
            sizes[group] = by_length[min(order, key=lambda length: (abs(by_length[length] - sizes['ROLE']), order.index(length)))]
        target = max(sizes.values()) + shortest
        for group, size in sizes.items():
            total[group] = total.get(group, Fraction(0)) + Fraction(target - size, target)
        count += 1
    out = {'note': 'an estimate from size counts, not from the tokenizer; no rule uses it; percent of the Notes block, mean over the kept passages of both sets'}
    for group in C['groups']['groups_with_a_notes_block']:
        if group in total:
            out[group] = one_decimal(total[group] * 100 / count)
    return out


# ---------------------------------------------------------------- letters, prompt parts, keys

def set_letters(C, set_name, tasks):
    """The plan's letters rule. Returns {task id: {level: [{'letter', 'text'}]}} and {task id: {level: right letter}}."""
    seed, letters = C['seeds']['letters'], C['levels']['letters']
    fact_type = C['task_families']['plain_fact']['type']
    by_id = {task['task_id']: task for task in tasks}
    options, keys, balance = {tid: {} for tid in by_id}, {tid: {} for tid in by_id}, {}
    unknown = sorted({task['type'] for task in tasks} - set(C['types_in_order']) - {fact_type})
    if unknown:
        raise Stop('TYPE_NOT_KNOWN', 'A selected task has the type %s, which the plan does not name.' % unknown[0])
    # selection.letters.rule in PLAN_CONSTANTS.json (review round 1): per set, per task family and per level, the
    # tasks are shuffled inside each type, the types are joined in their fixed order, and the letters are dealt in
    # turn over the whole joined list. The count does NOT start again at A for a new type. So no letter piles up
    # a surplus over the types, and "always answer A" scores chance to within one task.
    families = (('role_step', list(C['types_in_order']), ('1', '2')),
                ('plain_fact', [fact_type], ('1',)))   # a plain-fact task always shows its four options: level 1 only
    for family, types, levels in families:
        for level in levels:
            shown = C['task_families']['plain_fact']['options_written'] if family == 'plain_fact' else C['levels'][level]['options_shown']
            whole, place = {letter: 0 for letter in letters[:shown]}, 0
            for type_name in types:
                order = sorted(tid for tid, task in by_id.items() if task['type'] == type_name)
                random.Random('%d|%s|%s|%s' % (seed, set_name, type_name, level)).shuffle(order)
                count = {letter: 0 for letter in letters[:shown]}
                for tid in order:
                    task = by_id[tid]
                    others = list(task['wrong'][:shown - 1])
                    if len(others) != shown - 1 or not task['right']:
                        raise Stop('TASK_NOT_USABLE', 'The task %s does not have the options that level %s needs.' % (tid, level))
                    right_letter = letters[place % shown]   # the place in the joined list of the whole family
                    place += 1
                    random.Random('%d|%s|%s' % (seed, tid, level)).shuffle(others)
                    free = [letter for letter in letters[:shown] if letter != right_letter]
                    text_of = dict(zip(free, others))
                    text_of[right_letter] = task['right']
                    options[tid][level] = [{'letter': letter, 'text': text_of[letter]} for letter in letters[:shown]]
                    keys[tid][level] = right_letter
                    count[right_letter] += 1
                    whole[right_letter] += 1
                if order and max(count.values()) - min(count.values()) > 1:
                    raise Stop('LETTERS_NOT_BALANCED', 'The right letters of type %s at level %s are not balanced to within one task.' % (type_name, level))
                if order:
                    balance['%s level %s' % (type_name, level)] = count
            if place and max(whole.values()) - min(whole.values()) > 1:
                raise Stop('LETTERS_NOT_BALANCED', 'The right letters of the %s family at level %s are not balanced to within one task.' % (family, level))
            if place:
                balance['%s family level %s' % (family, level)] = whole
    return options, keys, balance


def notes_of_passage(C, pid, role_by_id, in_use):
    notes = {'FILLER': C['prompt']['filler_sentence']}
    for group, field in ROLE_TEXT_FIELD.items():
        notes[group] = role_by_id[pid][field]
    for group in C['groups']['ordinary']:
        notes[group] = {length: in_use[(pid, group, length)] for length in C['ordinary_notes']['lengths_in_order']}
    return notes


def check_parts(C, set_name, body, keys):
    """Stop if a prompt-parts file would hold a key outside the practice-only ANSWER-GIVEN notes."""
    stem = C['prompt']['answer_given_note'].split('<<')[0]
    allowed = {'set', 'passages', 'tasks'} | ({'answer_given'} if set_name == 'practice' else set())
    if set(body) != allowed:
        raise Stop('PROMPT_PARTS_NOT_SOUND', 'The %s prompt parts hold other top fields than the format names.' % set_name)
    for task in body['tasks']:
        if list(task) != TASK_FIELDS:
            raise Stop('PROMPT_PARTS_NOT_SOUND', 'The task %s in the prompt parts holds other fields than the format names.' % task['task_id'])
        for level, shown in task['options'].items():
            texts = [option['text'] for option in shown]
            if [option['letter'] for option in shown] != C['levels']['letters'][:len(shown)] or len(set(texts)) != len(texts):
                raise Stop('PROMPT_PARTS_NOT_SOUND', 'The options of %s at level %s are not in letter order or repeat a text.' % (task['task_id'], level))
            if sorted(task['options']) != sorted(keys[task['task_id']]):
                raise Stop('PROMPT_PARTS_NOT_SOUND', 'The task %s does not have a key for exactly the levels it shows.' % task['task_id'])
    plain = json.dumps({'passages': body['passages'], 'tasks': body['tasks']}, ensure_ascii=False)
    if stem and stem in plain:
        raise Stop('KEY_IN_PROMPT_PARTS', 'The %s prompt parts hold the ANSWER-GIVEN sentence outside the answer_given list.' % set_name)
    if set(C['groups'].get('struck', [])) & {group for task in body['tasks'] for group in task['groups']}:
        raise Stop('STRUCK_GROUP_IN_PROMPT_PARTS', 'A struck group is listed for a task.')
    for passage in body['passages']:
        if set(passage['notes']) & set(C['groups'].get('struck', [])):
            raise Stop('STRUCK_GROUP_IN_PROMPT_PARTS', 'A struck group has a notes text.')


def plan_calls(C, kept):
    """Every planned call of the job, as rows, and the totals. One call is one task in one group."""
    G = C['groups']
    wordings = len(C['prompt']['closing_wordings_in_order'])
    after = {family: [group for group in G['by_family'][family] if group != BASE_GROUP] for family in G['by_family']}
    extra = list(G['practice_only_role_step']) + list(G['task_check_role_step'])
    rows, totals = [], {'practice': 0, 'final_must_run': 0, 'final_no_passage': 0}

    def add(phase, step, task, level, wording, groups, calls, total):
        rows.append({'phase': phase, 'step': step, 'task_id': task['task_id'], 'level': level, 'wording': wording, 'groups': groups, 'calls': calls})
        totals[total] += calls

    for task in kept['practice']['tasks']:
        role_step = task['family'] == 'role_step'
        add('practice', 'P1', task, '1', 'each of the %d closing wordings' % wordings, [BASE_GROUP], wordings, 'practice')
        if role_step:
            add('practice', 'P2', task, '2', 'the chosen wording', [BASE_GROUP], 1, 'practice')
        groups = after[task['family']] + (extra if role_step else [])
        add('practice', 'P3', task, 'the chosen level', 'the chosen wording', groups, len(groups), 'practice')
    for task in kept['final']['tasks']:
        groups = list(G['by_family'][task['family']])
        add('final', 'MUST_RUN', task, 'the chosen level', 'the chosen wording', groups, len(groups), 'final_must_run')
    for block in G['final_secondary_blocks_in_order']:
        for task in kept['final']['tasks']:
            if task['family'] == 'role_step':
                add('final', block, task, 'the chosen level', 'the chosen wording', [block], 1, 'final_no_passage')
    totals['whole_job'] = totals['practice'] + totals['final_must_run'] + totals['final_no_passage']
    totals['cap'] = C['aws']['gpu_job']['call_cap']
    return rows, totals


# ---------------------------------------------------------------- the run

def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description='Option B: assemble the prompt parts, the keys, the removal log and the manifest for seal step 5.')
    parser.add_argument('--work', default=None, help='dry fixture folder under optionb/dry/ (never for a real run)')
    args = parser.parse_args(argv)

    ctx = Ctx(args.work)
    C = ctx.constants
    G = C['groups']
    struck = set(G.get('struck', []))
    if BASE_GROUP not in G['must_run_in_order'] or struck & (set(G['must_run_in_order']) | set(G['groups_with_a_notes_block']) | set(G['by_family']['role_step'])):
        raise Stop('PLAN_DOES_NOT_MATCH_PROGRAM', 'The groups in PLAN_CONSTANTS.json are not usable: no NONE group, or a struck group is listed to run.')
    if sorted(['FILLER'] + list(ROLE_TEXT_FIELD) + list(G['ordinary'])) != sorted(g for g in G['groups_with_a_notes_block'] if g not in G['practice_only_role_step']):
        raise Stop('PLAN_DOES_NOT_MATCH_PROGRAM', 'The groups with a Notes block in PLAN_CONSTANTS.json are not the six this program knows.')
    passes = list(C['outside_services']['gemini_question_writer']['passes'])
    if C['ordinary_notes'].get('not_written_status') != NOT_WRITTEN:
        raise Stop('PLAN_DOES_NOT_MATCH_PROGRAM', 'ordinary_notes.not_written_status in PLAN_CONSTANTS.json is not %s.' % NOT_WRITTEN)

    seal, sealed = check_seal(ctx, SEAL_NEED, SEAL_STEP)
    S = 'casalescence/optionb/'
    eligibility = ctx.need_json('elig/eligibility.json', S + 'eligibility/v1')
    if not ctx.dry and eligibility.get('counts_match_plan') is not True:
        raise Stop('ELIGIBILITY_NOT_CONFIRMED', 'elig/eligibility.json does not say counts_match_plan: true.')
    exclusions = ctx.need_json('elig/exclusions.json', S + 'exclusions/v1')
    role_notes = ctx.need_json('notes_role/role_notes.json', S + 'role_notes/v1')
    split = ctx.need_json('select/split_fixed.json', S + 'split_fixed/v1')
    sealed_names = ['elig/eligibility.json', 'elig/exclusions.json', 'notes_role/role_notes.json', 'select/split_fixed.json']
    data = {}
    for set_name in SETS:
        data[set_name], names = load_set(ctx, set_name, passes)
        sealed_names += names
    must_be_sealed(ctx, sealed, [REAL_WORK / 'PLAN_CONSTANTS.json'] + [ctx.work / name for name in sealed_names])

    if split.get('floor_met') is not True:
        raise Stop('DO_NOT_LAUNCH', 'select/split_fixed.json says the practice floor was not met. Nothing is assembled.')
    if data['practice']['selection'].get('practice_setting_count') != split['practice_setting_count']:
        raise Stop('SPLIT_DOES_NOT_MATCH', 'select/selection_practice.json and select/split_fixed.json name different numbers of practice settings.')

    elig = {passage['id']: passage for passage in eligibility['passages']}
    excluded = {passage['id'] for passage in exclusions['passages']}
    barred = set(C['eligibility']['barred_passage_ids'])
    role_by_id = {passage['id']: passage for passage in role_notes['passages']}
    start = C['split']['practice_setting_count_start']

    # what is kept, per set, with the checks that guard the split and the custody rules
    kept, in_use = {}, {}
    for set_name in SETS:
        kept[set_name] = kept_of_set(ctx, set_name, data[set_name])
        for passage in data[set_name]['notes']['passages']:
            for group, by_length in passage['notes'].items():
                for length, slot in by_length.items():
                    if slot['versions']:      # a note that was given up at its first writing has no version; its passage is dropped
                        in_use[(passage['passage_id'], group, length)] = slot['versions'][slot['current'] - 1]['text']
        for pid in kept[set_name]['kept']:
            missing = [(group, length) for group in G['ordinary'] for length in C['ordinary_notes']['lengths_in_order'] if (pid, group, length) not in in_use]
            if missing:
                raise Stop('NOTES_NOT_SOUND', 'The kept passage %s has no %s note of length %s.' % ((pid,) + missing[0]))
        # FILE_FORMATS.md section 9.5: the status DROPPED_NOTE_NOT_WRITTEN means exactly "a note of this passage has not_written set"
        gone = {passage['passage_id'] for passage in data[set_name]['notes']['passages']
                for by_length in passage['notes'].values() for slot in by_length.values() if slot.get('not_written')}
        said = {passage['passage_id'] for passage in data[set_name]['support']['passages'] if passage['status'] == NOT_WRITTEN}
        if gone != said:
            raise Stop('SUPPORT_RESULTS_DO_NOT_MATCH_NOTES', 'For the %s set the passages with the status %s are not the passages that have a note with '
                       'not_written set (first that differs: %s). Run tools/ob_check_support.py decide again.' % (set_name, NOT_WRITTEN, sorted(gone ^ said)[0]))
        for pid in kept[set_name]['carry']:
            known = elig.get(pid)
            if known is None or not known['eligible'] or known['excluded'] or known['barred'] or pid in excluded or pid in barred or pid not in role_by_id:
                raise Stop('TASK_ON_A_PASSAGE_THAT_MAY_NOT_CARRY_ONE', 'Passage %s carries a task and is excluded, barred, not eligible or has no role note.' % pid)
            if in_practice(known['setting_role'], split['practice_setting_count'], start) != (set_name == 'practice'):
                raise Stop('TASK_IN_THE_WRONG_SET', 'Passage %s carries a %s task and its setting does not belong to the %s set.' % (pid, set_name, set_name))
        for task in kept[set_name]['tasks']:
            family = 'plain_fact' if task['type'] == C['task_families']['plain_fact']['type'] else 'role_step'
            if task['family'] != family or task['task_id'] != '%s.%s' % (task['passage_id'], task['form']) or task['family'] not in G['by_family']:
                raise Stop('TASK_NOT_USABLE', 'The task %s does not have the id, family and type the formats give.' % task['task_id'])
    both = set(kept['practice']['carry']) & set(kept['final']['carry'])
    if both:
        raise Stop('PASSAGE_IN_BOTH_SETS', 'Passage %s carries a practice task and a final task.' % sorted(both)[0])

    canon_lines_checked, sayings_lines_checked = check_canon(ctx, role_notes, kept['practice']['kept'] + kept['final']['kept'])
    if ctx.dry:
        source_check = 'not checked: dry fixture'
    else:
        source = C['sources']['passages']
        raw = ctx.read_bytes(ROOT / source['path'])
        if len(raw) != source['bytes'] or sha_bytes(raw) != source['sha256']:
            raise Stop('SOURCE_HASH_MISMATCH', '%s does not have the hash pinned in PLAN_CONSTANTS.json.' % source['path'])
        sealed_text = {passage['id']: passage['text'] for passage in json.loads(raw.decode('utf-8'))}
        for set_name in SETS:
            for pid in kept[set_name]['kept']:
                if sealed_text.get(pid) != elig[pid]['text']:
                    raise Stop('PASSAGE_TEXT_DIFFERS', 'The text of %s in elig/eligibility.json is not the sealed passage text.' % pid)
        source_check = 'checked: every kept passage text equals the sealed passage text'

    # the removal log, the counts, the floor and the tier
    entries, survival = [], {}
    for set_name in SETS:
        rows, survival[set_name] = removal_of_set(C, set_name, data[set_name], kept[set_name], elig, passes)
        entries += rows
    entries.sort(key=lambda row: (SETS.index(row['set']), STEPS.index(row['step']), row['id'], row['rule']))
    by_step = {}
    for row in entries:
        by_step.setdefault(row['step'], {})
        by_step[row['step']][row['rule']] = by_step[row['step']].get(row['rule'], 0) + 1

    def count(set_name, family):
        return sum(1 for task in kept[set_name]['tasks'] if task['family'] == family)

    final_counts = {'final_role_step_tasks': count('final', 'role_step'), 'final_plain_fact_tasks': count('final', 'plain_fact'),
                    'final_passages_with_a_role_step_task': len({t['passage_id'] for t in kept['final']['tasks'] if t['family'] == 'role_step'}),
                    'practice_role_step_tasks': count('practice', 'role_step'), 'practice_plain_fact_tasks': count('practice', 'plain_fact')}
    floor, tiers = C['launch_floor'], C['tiers']
    floor_met = (final_counts['final_role_step_tasks'] >= floor['final_role_step_tasks_min']
                 and final_counts['final_plain_fact_tasks'] >= floor['final_plain_fact_tasks_min']
                 and final_counts['practice_role_step_tasks'] >= floor['practice_role_step_tasks_min']
                 and final_counts['practice_plain_fact_tasks'] >= floor['practice_plain_fact_tasks_min'])
    if not floor_met or final_counts['final_role_step_tasks'] < tiers['no_launch_below_final_role_step_tasks']:
        tier = 'NO_LAUNCH'
    elif (final_counts['final_role_step_tasks'] >= tiers['as_it_stands']['final_role_step_tasks_min']
          and final_counts['final_passages_with_a_role_step_task'] >= tiers['as_it_stands']['final_passages_with_a_role_step_task_min']):
        tier = 'AS_IT_STANDS'
    else:
        tier = 'EXPLORATORY'

    notes_by_set = {set_name: {pid: notes_of_passage(C, pid, role_by_id, in_use) for pid in kept[set_name]['kept']} for set_name in SETS}
    all_notes = [notes for set_name in SETS for notes in notes_by_set[set_name].values()]
    calls, planned = plan_calls(C, kept)
    under_cap = planned['whole_job'] <= planned['cap']

    written = [ctx.write_json('removal_log.json', S + 'removal_log/v1', {
        'entries': entries, 'counts_by_step_and_rule': {step: by_step[step] for step in STEPS if step in by_step},
        'survival': survival, 'final_counts': final_counts, 'launch_floor_met': floor_met, 'tier': tier,
        'estimated_padding': estimate_padding(C, all_notes) if all_notes else {'note': 'no passage is kept'}})]

    report = {'program': PROGRAM, 'dry_fixture': ctx.dry, 'seal': seal, 'canon_lines_read_from_the_guide': canon_lines_checked,
              'sayings_lines_read_from_the_table': sayings_lines_checked,
              'passage_text_check': source_check, 'final_counts': final_counts,
              'launch_floor': dict(floor), 'launch_floor_met': floor_met, 'tier': tier, 'planned_calls': planned, 'planned_calls_under_the_cap': under_cap,
              'survival': survival, 'removal_log_entries': len(entries)}
    if not floor_met or tier == 'NO_LAUNCH' or not under_cap:
        stale = [name for name in IN_PACKAGE if (ctx.work / name).exists()]
        report.update({'status': 'DO_NOT_LAUNCH_FLOOR_NOT_MET' if under_cap else 'DO_NOT_LAUNCH_PLANNED_CALLS_ABOVE_THE_CAP',
                       'files_written': [rel(path) for path in written],
                       'older_files_still_on_disk_that_are_now_stale': stale,
                       'next': 'DO NOT LAUNCH. Only the removal log was written. No prompt part, no key and no manifest exists for seal step 5. '
                               'Report the numbers to the owner.'})
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return 3

    # letters last, then the parts, the keys and the task facts
    balance = {}
    for set_name in SETS:
        tasks = kept[set_name]['tasks']
        options, keys, balance[set_name] = set_letters(C, set_name, tasks)
        body = {'set': set_name,
                'passages': [{'passage_id': pid, 'text': elig[pid]['text'], 'notes': notes_by_set[set_name][pid]} for pid in kept[set_name]['kept']],
                'tasks': [{'task_id': t['task_id'], 'passage_id': t['passage_id'], 'family': t['family'], 'question': t['question'],
                           'options': options[t['task_id']], 'groups': list(G['by_family'][t['family']])} for t in tasks]}
        if set_name == 'practice':
            body['answer_given'] = [{'task_id': t['task_id'], 'level': level, 'note': fill(C['prompt']['answer_given_note'], {'LETTER': keys[t['task_id']][level]})}
                                    for t in tasks if t['family'] == 'role_step' for level in sorted(keys[t['task_id']])]
        check_parts(C, set_name, body, keys)
        meta = {t['task_id']: {'passage_id': t['passage_id'], 'family': t['family'], 'type': t['type'], 'form': t['form'],
                               'kind': elig[t['passage_id']]['kind'], 'setting': elig[t['passage_id']]['setting'], 'right_text': t['right'],
                               'anchors_matched': list(t['anchors_matched']),
                               'type_has_leftover': bool(elig[t['passage_id']]['leftover_on_type'].get(t['type'], False)) if t['family'] == 'role_step' else False,
                               'passage_any_leftover_2_to_9': bool(elig[t['passage_id']]['any_leftover_2_to_9'])} for t in tasks}
        kept[set_name].update({'options': options, 'keys': keys})
        written.append(ctx.write_json('prompts/prompt_parts_%s.json' % set_name, S + 'prompt_parts/v1', body))
        written.append(ctx.write_json('keys_%s/keys_%s.json' % (set_name, set_name), S + 'keys/v1', {'set': set_name, 'keys': keys}))
        written.append(ctx.write_json('keys_%s/task_meta_%s.json' % (set_name, set_name), S + 'task_meta/v1', {'set': set_name, 'tasks': meta}))

    # the review pack: all practice tasks and a seeded share of the final tasks, with the right option
    def review_item(set_name, task):
        pid = task['passage_id']
        return {'set': set_name, 'task_id': task['task_id'], 'passage_id': pid, 'family': task['family'], 'type': task['type'], 'form': task['form'],
                'passage': elig[pid]['text'], 'question': task['question'], 'options': kept[set_name]['options'][task['task_id']],
                'right_option': task['right'], 'right_letter': kept[set_name]['keys'][task['task_id']], 'notes': notes_by_set[set_name][pid]}

    final_ids = sorted(task['task_id'] for task in kept['final']['tasks'])
    percent = C['review_round']['final_sample_percent']
    sample = set(random.Random(C['seeds']['review_sample']).sample(final_ids, (len(final_ids) * percent + 99) // 100))
    written.append(ctx.write_json('review/review_pack.json', S + 'review_pack/v1', {
        'seed': C['seeds']['review_sample'], 'final_sample_percent': percent,
        'counts': {'practice_tasks': len(kept['practice']['tasks']), 'final_tasks': len(final_ids), 'final_tasks_in_the_sample': len(sample)},
        'practice_tasks': [review_item('practice', task) for task in kept['practice']['tasks']],
        'final_tasks_sample': [review_item('final', task) for task in kept['final']['tasks'] if task['task_id'] in sample]}))

    written.append(ctx.write_json('assemble/planned_calls.json', S + 'planned_calls/v1', {
        'practice_setting_count': split['practice_setting_count'], 'planned_calls': planned, 'under_cap': under_cap,
        'how_to_read': 'One row per phase, step and task. calls is the number of model calls of that row. The chosen level and the chosen '
                       'closing wording are fixed by the practice gates inside the job. The job counts its own planned calls again in Gate 0.',
        'calls': calls}))

    # the manifest for seal step 5: the files of FILE_FORMATS.md sections 10, 11 and 12, and the list of planned calls
    listed = [ctx.work / 'screen' / ('leak_screen_%s.json' % set_name) for set_name in SETS] + written
    files = []
    for path in listed:
        raw = Path(path).read_bytes()
        under_work = Path(path).resolve().relative_to(ctx.work).as_posix()
        files.append({'path': rel(path), 'package_path': under_work if under_work in IN_PACKAGE else None, 'bytes': len(raw), 'sha256': sha_bytes(raw)})
    manifest = ctx.write_json('assemble/manifest_step5.json', S + 'assemble_manifest/v1', {
        'seal_step': SEAL_STEP, 'files': files,
        'values': dict(final_counts, launch_floor_met=floor_met, tier=tier, planned_calls_whole_job=planned['whole_job'], call_cap=planned['cap'],
                       practice_setting_count=split['practice_setting_count'])})

    report.update({'status': 'ASSEMBLED', 'right_letter_counts': balance,
                   'answer_given_notes_in_the_practice_file': sum(1 for t in kept['practice']['tasks'] if t['family'] == 'role_step') * 2,
                   'files_written': [rel(path) for path in written] + [rel(manifest)],
                   'manifest': rel(manifest), 'manifest_sha256': sha_bytes(Path(manifest).read_bytes()),
                   'next': 'Next: seal step 5 (tools/ob_seal.py) over the files named in the manifest. Then the owner checkpoint: the real counts and the detection table.'})
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Stop as stop:
        print(json.dumps({'program': PROGRAM, 'status': 'STOP', 'code': stop.args[0], 'reason': stop.args[1]}, ensure_ascii=False, indent=1))
        sys.exit(2)
