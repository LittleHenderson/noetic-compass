"""Option B, Step 7 (last part). The answer-leak screen for every note of every group.

What this tool does, in plain words:
- For every passage that carries a task and was not dropped by the support check, it screens the notes
  of every group: FILLER, ROLE, MIXED, QUOTES-ONLY, and both ordinary groups in all three lengths
  (the version in use). Each note is tested against every selected task of that passage.
- A note is HIT if it holds any of these:
    (a) an option letter written as a choice, such as "A.", "(B)" or "answer: C";
    (b) the question, word for word, or any sentence of it that has 5 or more words;
    (c) the full text of an option that the passage does NOT hold;
    (d) the whole word answer, option or correct.
- "Outside passage text" is defined like this. For a program-built note (FILLER, ROLE, MIXED,
  QUOTES-ONLY) only the fixed frame words are tested: the quoted passage parts are blanked first.
  For an ordinary note, (a) and (d) are a hit when the pattern or the word appears more often in the
  note than in the passage.
- A hit drops the passage for EVERY group. The rule is logged. A hit never causes a note to be
  written again: this tool calls nobody, and the note writer never reads this tool's file.
- It prints how many passages and tasks remain, and checks the launch floor again.

Before it trusts the blanked frame texts of the role notes, it checks them: filling the blanked
places with the entry's own label, Mind, related thing and supporting quote must give back the full
note line, letter for letter, and each filled-in part must be text of the passage.

The head of a ROLE or MIXED note (amendment A13; FILE_FORMATS.md sections 3.1 and 18) is, for each
Noetic shown: its canon line, then its sayings line. A head line is frame text. It is never blanked:
a sayings line holds quote marks, but it is not a passage part. So rules (a) to (d) test the word
Sayings and the sayings text like every other frame word. An option whose whole text stands inside
a sayings line, and not in the passage, is a rule (c) hit.

A passage with the support status DROPPED_NOTE_NOT_WRITTEN (a note the writer could not produce;
plan section 10, Step 7) was dropped by the support check, like one with DROPPED_SECOND_FAILURE.
It is not screened.

This tool calls no outside service and needs no key.

It refuses to run unless seal step 4 (the ordinary notes and the support check results) exists.
It refuses to write once seal step 5 exists.

The report-only run (review round 1; FILE_FORMATS.md section 10.2). It is for the practice set only.
It needs seal steps 1, 2, 3A and 3B and a finished practice support check. It does not need seal
step 4. It applies the same rules (a) to (d) to the practice notes as they then stand. It prints the
passages screened, the passages hit, the hits per rule, and the practice tasks that would be left,
beside the two practice launch floors. It writes NO file. It is an early look, so that the hit rate
is known before any final question is written. The screen of record is the later full run. A hit, in
either run, never causes a note to be written again, and no rule is changed because of these numbers
without a new reviewed plan version.

Usage:
  ob_screen_notes.py --set practice|final|both
  ob_screen_notes.py --set practice --report-only

File (FILE_FORMATS.md section 10):
  screen/leak_screen_<set>.json      (not written by a report-only run)

Exit codes: 0 = screened. 2 = not started or stopped by a check. 3 = screened, and the launch floor
is NOT met (do not launch; report the numbers to the owner).

Dry fixture: with --work pointing under optionb/dry/ every output is marked as a dry fixture.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import time
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

SEAL_NEED = {'practice': ['1_PLAN_AND_SOURCES', '2_ROLE_NOTES', '3A_PRACTICE_QUESTIONS_AND_KEYS', '3B_PRACTICE_SET_FIXED', '4_ORDINARY_NOTES'],
             'final': ['1_PLAN_AND_SOURCES', '2_ROLE_NOTES', '3A_PRACTICE_QUESTIONS_AND_KEYS', '3B_PRACTICE_SET_FIXED',
                       '3C_FINAL_QUESTIONS_AND_KEYS', '4_ORDINARY_NOTES']}
SEAL_CLOSED_BY = '5_PROMPT_PARTS_AND_REMOVAL_LOG'
# the report-only run of the practice set: before seal step 4 (FILE_FORMATS.md section 10.2)
SEAL_NEED_REPORT_ONLY = ['1_PLAN_AND_SOURCES', '2_ROLE_NOTES', '3A_PRACTICE_QUESTIONS_AND_KEYS', '3B_PRACTICE_SET_FIXED']
SETS = ('practice', 'final')
# where a program-built group's texts sit in notes_role/role_notes.json
ROLE_TEXT_FIELD = {'ROLE': 'role_text', 'MIXED': 'mixed_text', 'QUOTES-ONLY': 'quotes_only_text'}
ROLE_BLANK_FIELD = {'ROLE': 'role', 'MIXED': 'mixed', 'QUOTES-ONLY': 'quotes_only'}
# FILE_FORMATS.md sections 9.5 and 10.1: the statuses of a finished support check, and those of them that drop the passage.
# NOT_WRITTEN is also named in PLAN_CONSTANTS.json (ordinary_notes.not_written_status); Rules() stops if the two differ.
NOT_WRITTEN = 'DROPPED_NOTE_NOT_WRITTEN'
SUPPORT_DROPPED = ('DROPPED_SECOND_FAILURE', NOT_WRITTEN)
SUPPORT_FINAL = ('ALL_PASS',) + SUPPORT_DROPPED


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

    def need_json(self, path, schema):
        path = Path(path)
        if not path.exists():
            raise Stop('INPUT_MISSING', '%s does not exist.' % rel(path))
        doc = self.read_json(path)
        if doc.get('schema') != schema:
            raise Stop('WRONG_FILE', '%s does not carry the schema name %s.' % (rel(path), schema))
        return doc

    def header(self, schema):
        return {'schema': schema,
                'made_by': {'program': PROGRAM + (DRY_TAG if self.dry else ''), 'sha256': sha_bytes(HERE.read_bytes()), 'utc': self.now()},
                'inputs': [{'path': p, 'sha256': s} for p, s in sorted(self.inputs.items())]}

    def write_json(self, path, schema, body):
        doc = self.header(schema)
        doc.update(body)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_name(path.name + '.partial')
        with open(partial, 'w', encoding='utf-8', newline=LF) as stream:
            stream.write(json.dumps(doc, indent=1, ensure_ascii=False) + LF)
        replace_file(partial, path)


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


# ---------------------------------------------------------------- the rules of the screen

class Rules:
    """The screen's patterns and numbers, all read from PLAN_CONSTANTS.json."""

    def __init__(self, C):
        screen, notes = C['leak_screen'], C['role_notes']
        self.word = re.compile(C['question_rules']['word_sequence_regex'])
        self.letter_patterns = [re.compile(pattern) for pattern in screen['rule_a_patterns']]
        self.words = [(word, re.compile(r'\b' + re.escape(word) + r'\b', flags=re.I)) for word in C['forbidden_words']['leak_screen_words']['words']]
        self.min_words = screen['rule_b_min_words']
        self.sentence_end = re.compile(notes['sentence_end_regex'])
        self.not_after = set(notes['sentence_end_not_after'])
        self.filler = C['prompt']['filler_sentence']
        self.ordinary = list(C['groups']['ordinary'])
        self.lengths = list(C['ordinary_notes']['lengths_in_order'])
        self.screened = list(screen['screened_groups'])
        built = ['FILLER'] + list(ROLE_TEXT_FIELD)
        if sorted(self.screened) != sorted(built + self.ordinary) or set(screen['not_screened']) & set(self.screened):
            raise Stop('PLAN_DOES_NOT_MATCH_PROGRAM', 'The groups to screen in PLAN_CONSTANTS.json are not the six this program knows.')
        if set(C['groups'].get('struck', [])) & set(self.screened):
            raise Stop('PLAN_DOES_NOT_MATCH_PROGRAM', 'A struck group is listed among the groups to screen.')
        if C['ordinary_notes'].get('not_written_status') != NOT_WRITTEN:
            raise Stop('PLAN_DOES_NOT_MATCH_PROGRAM', 'ordinary_notes.not_written_status in PLAN_CONSTANTS.json is not %s.' % NOT_WRITTEN)

    def sequence(self, text):
        """Lower case, then the words. Two texts are compared by their word sequences."""
        return self.word.findall(text.lower())

    def sentences(self, text):
        """The sentences of a text, by the plan's sentence rule."""
        out, start = [], 0
        for found in self.sentence_end.finditer(text):
            marks = re.match(r'[.!?]+', found.group(0)).group(0)
            if marks == '.':
                before = re.search(r'([A-Za-z]+)$', text[:found.start()])
                if before and before.group(1) in self.not_after:
                    continue   # a single full stop right after Mr, Mrs, Dr, ... does not end a sentence
            piece = text[start:found.end()].strip()
            if piece:
                out.append(piece)
            start = found.end()
        tail = text[start:].strip()
        if tail:
            out.append(tail)
        return out


def holds(big, small):
    """True when the word sequence small is an unbroken part of the word sequence big."""
    size = len(small)
    if size == 0 or size > len(big):
        return False
    return any(big[index:index + size] == small for index in range(len(big) - size + 1))


def screen_note(rules, kind, group, length, note, passage, tasks):
    """All hits of one note. kind is 'frame' (a program-built note: its frame text) or 'free' (an ordinary note).

    In a frame text any match of (a) or (d) is a hit. In an ordinary note (a) and (d) are a hit only
    when the pattern or the word appears more often in the note than in the passage.
    """
    hits = []
    where = 'the frame text' if kind == 'frame' else 'the note'

    def hit(rule, task_id, detail):
        hits.append({'group': group, 'length': length, 'rule': rule, 'task_id': task_id, 'detail': detail})

    for number, pattern in enumerate(rules.letter_patterns, 1):
        in_note = [found.group(0) for found in pattern.finditer(note)]
        in_passage = 0 if kind == 'frame' else sum(1 for _ in pattern.finditer(passage))
        if len(in_note) > in_passage:
            hit('a', None, 'letter pattern %d: %d in %s, %d in the passage; first: %s' % (number, len(in_note), where, in_passage, in_note[0]))
    for word, pattern in rules.words:
        in_note = sum(1 for _ in pattern.finditer(note))
        in_passage = 0 if kind == 'frame' else sum(1 for _ in pattern.finditer(passage))
        if in_note > in_passage:
            hit('d', None, 'the word %s: %d in %s, %d in the passage' % (word, in_note, where, in_passage))
    note_words, passage_words = rules.sequence(note), rules.sequence(passage)
    for task in tasks:
        whole = rules.sequence(task['question'])
        parts = [('the whole question', whole)] if whole else []
        for sentence in rules.sentences(task['question']):
            words = rules.sequence(sentence)
            if len(words) >= rules.min_words and words != whole:
                parts.append(('a sentence of the question', words))
        for name, words in parts:
            if holds(note_words, words):
                hit('b', task['task_id'], 'holds %s: %s' % (name, ' '.join(words)))
                break
        for option in [task['right']] + list(task['wrong']):
            words = rules.sequence(option)
            if not words or holds(passage_words, words):
                continue   # an option that is passage text is not tested: the passage is in every prompt
            if holds(note_words, words):
                hit('c', task['task_id'], 'holds the option text: %s' % option)
    return hits


def head_pairs(role_notes):
    """{canon line: its sayings line} of a role-notes file, for the head check of check_blanked (amendment A13)."""
    canon = role_notes.get('canon', {})
    lines, sayings = canon.get('lines'), canon.get('sayings_lines')
    if not isinstance(lines, dict) or not isinstance(sayings, dict) or set(lines) != set(sayings) or len(set(lines.values())) != len(lines):
        raise Stop('ROLE_NOTES_WITHOUT_SAYINGS_LINES', 'notes_role/role_notes.json does not hold one sayings line for each of its canon lines '
                   '(canon.sayings_lines). It was built before amendment A13. Build the role notes again.')
    return {lines[noetic]: sayings[noetic] for noetic in lines}


def check_blanked(passage, text, pairs):
    """Stop unless the blanked frame texts of one passage's role notes are exactly what they must be.

    Filling the blanked places with the entry's own label, Mind, related thing and supporting quote
    must give back the note line. The lines above the entry lines are the head. The head must be
    pairs of lines: a canon line of the file, then the sayings line of the same Noetic, both
    unchanged in the blanked text. pairs is head_pairs() of the file. Each filled-in part must be
    text of the passage.
    """
    pid, entries = passage['id'], passage['entries']
    for group, field in ROLE_TEXT_FIELD.items():
        full = passage[field].split(LF)
        blank = passage['frame_blanked'][ROLE_BLANK_FIELD[group]].split(LF)
        head = len(full) - len(entries)
        if len(full) != len(blank) or head < 0 or head % 2 or (group == 'QUOTES-ONLY' and head != 0):
            raise Stop('BLANKED_TEXT_NOT_SOUND', 'The %s note of %s and its blanked text do not have the lines they must have.' % (group, pid))
        for index in range(0, head, 2):
            if full[index:index + 2] != blank[index:index + 2] or full[index] not in pairs or pairs[full[index]] != full[index + 1]:
                raise Stop('BLANKED_TEXT_NOT_SOUND', 'Lines %d and %d of the %s note of %s are not an unchanged canon line of the role-notes file '
                           'followed by the sayings line of the same Noetic.' % (index + 1, index + 2, group, pid))
        for entry, full_line, blank_line in zip(entries, full[head:], blank[head:]):
            values = [entry['label']]
            if group != 'QUOTES-ONLY':
                values += [entry[name] for name in ('mind', 'relative_to') if entry[name]]
            if entry.get('same_as_label') is not None:
                values.append(entry['same_as_label'])
            elif entry.get('supporting_quote') is not None:
                values.append(entry['supporting_quote'])
            pieces = blank_line.split('""')
            rebuilt = pieces[0] + ''.join('"' + value + '"' + piece for value, piece in zip(values, pieces[1:]))
            if len(pieces) != len(values) + 1 or rebuilt != full_line:
                raise Stop('BLANKED_TEXT_NOT_SOUND', 'A line of the %s note of %s is not its blanked line with the entry\'s own quotes filled in.' % (group, pid))
            for value in values:
                if not value or value not in text:
                    raise Stop('BLANKED_TEXT_NOT_SOUND', 'A blanked part of the %s note of %s is not text of the passage.' % (group, pid))


# ---------------------------------------------------------------- one set

def passage_texts(ctx):
    """Read elig/eligibility.json and keep ONLY the id and the text of each passage."""
    doc = ctx.need_json(ctx.work / 'elig' / 'eligibility.json', 'casalescence/optionb/eligibility/v1')
    if not ctx.dry and doc.get('counts_match_plan') is not True:
        raise Stop('ELIGIBILITY_NOT_CONFIRMED', 'elig/eligibility.json does not say counts_match_plan: true.')
    texts = {passage['id']: passage['text'] for passage in doc['passages']}
    del doc
    return texts


def load_set(ctx, set_name):
    """The selected tasks, the support status and the notes in use of one set."""
    selection = ctx.need_json(ctx.work / 'select' / ('selection_%s.json' % set_name), 'casalescence/optionb/selection/v1')
    notes = ctx.need_json(ctx.work / 'notes_ord' / ('ordinary_notes_%s.json' % set_name), 'casalescence/optionb/ordinary_notes/v1')
    support = ctx.need_json(ctx.work / 'support' / ('support_results_%s.json' % set_name), 'casalescence/optionb/support_results/v1')
    for name, doc in (('selection', selection), ('ordinary notes', notes), ('support results', support)):
        if doc.get('set') != set_name:
            raise Stop('WRONG_FILE', 'The %s file is not the file of the %s set.' % (name, set_name))
    tasks = {}
    for task in selection['tasks']:
        tasks.setdefault(task['passage_id'], []).append(task)
    status = {passage['passage_id']: passage['status'] for passage in support['passages']}
    passed = {row['note_id'] for row in support['results'] if row['verdict'] == 'PASS'}
    in_use = {}
    for passage in notes['passages']:
        for group, by_length in passage['notes'].items():
            for length, slot in by_length.items():
                version = slot['current']
                if slot.get('not_written') and not slot['versions']:
                    continue   # a note that was given up at its first writing; its passage is dropped and is not screened
                if not 1 <= version <= len(slot['versions']) or slot['versions'][version - 1]['version'] != version:
                    raise Stop('NOTES_NOT_SOUND', 'The note %s|%s|%s names a version in use that it does not hold.' % (passage['passage_id'], group, length))
                in_use[(passage['passage_id'], group, length)] = (version, slot['versions'][version - 1]['text'])
    open_passages = sorted(pid for pid in tasks if status.get(pid) not in SUPPORT_FINAL)
    if open_passages:
        raise Stop('SUPPORT_CHECK_NOT_FINISHED', 'The support check of the %s set is not finished: %d passages that carry a task are neither '
                   'ALL_PASS nor dropped (%s) (first: %s).' % (set_name, len(open_passages), ' or '.join(SUPPORT_DROPPED), open_passages[0]))
    # FILE_FORMATS.md section 9.5: the status DROPPED_NOTE_NOT_WRITTEN means exactly "a note of this passage has not_written set"
    gone = {passage['passage_id'] for passage in notes['passages'] for by_length in passage['notes'].values() for slot in by_length.values()
            if slot.get('not_written')}
    said = {pid for pid, word in status.items() if word == NOT_WRITTEN}
    if gone != said:
        raise Stop('SUPPORT_RESULTS_DO_NOT_MATCH_NOTES', 'For the %s set the passages with the status %s are not the passages that have a note with '
                   'not_written set (first that differs: %s). Run tools/ob_check_support.py decide again.' % (set_name, NOT_WRITTEN, sorted(gone ^ said)[0]))
    return {'tasks': tasks, 'status': status, 'passed': passed, 'in_use': in_use}


def remaining(tasks, dropped_by_support, hit):
    """How many passages and tasks are left after the support check and the screen."""
    left = {pid: rows for pid, rows in tasks.items() if pid not in dropped_by_support and pid not in hit}
    return {'passages_that_carry_a_task': len(tasks),
            'passages_dropped_by_the_support_check': len([pid for pid in tasks if pid in dropped_by_support]),
            'passages_dropped_by_the_screen': len([pid for pid in tasks if pid in hit and pid not in dropped_by_support]),
            'passages_left': len(left),
            'passages_left_with_a_role_step_task': sum(1 for rows in left.values() if any(t['family'] == 'role_step' for t in rows)),
            'role_step_tasks_left': sum(1 for rows in left.values() for t in rows if t['family'] == 'role_step'),
            'plain_fact_tasks_left': sum(1 for rows in left.values() for t in rows if t['family'] == 'plain_fact')}


def screen_set(ctx, rules, set_name, texts, role_notes, report_only=False):
    data = load_set(ctx, set_name)
    if report_only:
        # FILE_FORMATS.md section 10.2: a finished support check means no passage at all is still open
        still_open = sorted(pid for pid, status in data['status'].items() if status not in SUPPORT_FINAL)
        if still_open:
            raise Stop('SUPPORT_CHECK_NOT_FINISHED', 'The support check of the %s set is not finished: %d passages have the status REWRITE_NEEDED or '
                       'UNCHECKED (first: %s).' % (set_name, len(still_open), still_open[0]))
    role_by_id = {passage['id']: passage for passage in role_notes['passages']}
    pairs = head_pairs(role_notes)
    dropped = {pid for pid in data['tasks'] if data['status'][pid] in SUPPORT_DROPPED}
    rows, by_rule = [], {'a': 0, 'b': 0, 'c': 0, 'd': 0}
    for pid in sorted(data['tasks']):
        if pid in dropped:
            continue
        if pid not in texts or pid not in role_by_id:
            raise Stop('PASSAGE_WITHOUT_ROLE_NOTE', 'Passage %s carries a task and has no passage text or no role note.' % pid)
        text, role, tasks = texts[pid], role_by_id[pid], data['tasks'][pid]
        check_blanked(role, text, pairs)
        hits = []
        for group in rules.screened:
            if group == 'FILLER':
                hits += screen_note(rules, 'frame', group, None, rules.filler, text, tasks)
            elif group in ROLE_BLANK_FIELD:
                hits += screen_note(rules, 'frame', group, None, role['frame_blanked'][ROLE_BLANK_FIELD[group]], text, tasks)
            else:
                for length in rules.lengths:
                    if (pid, group, length) not in data['in_use']:
                        raise Stop('NOTES_NOT_SOUND', 'Passage %s has no %s note of length %s.' % (pid, group, length))
                    version, note = data['in_use'][(pid, group, length)]
                    if '%s|%s|%s|v%d' % (pid, group, length, version) not in data['passed']:
                        raise Stop('NOTE_IN_USE_NOT_PASSED', 'The note in use %s|%s|%s|v%d has no PASS from the support check.' % (pid, group, length, version))
                    hits += screen_note(rules, 'free', group, length, note, text, tasks)
        for one in hits:
            by_rule[one['rule']] += 1
        rows.append({'passage_id': pid, 'hit': bool(hits), 'hits': hits})
    hit = {row['passage_id'] for row in rows if row['hit']}
    body = {'set': set_name, 'passages': rows,
            'counts': {'passages_screened': len(rows), 'passages_hit': len(hit), 'hits_by_rule': by_rule}}
    return body, remaining(data['tasks'], dropped, hit)


def other_set_numbers(ctx, set_name):
    """The numbers of a set that was screened in an earlier run, or None when it has no screen file that is still current."""
    path = ctx.work / 'screen' / ('leak_screen_%s.json' % set_name)
    if not path.exists():
        return None
    screen = json.loads(path.read_text(encoding='utf-8'))
    try:
        data = load_set(ctx, set_name)
    except Stop:
        return None
    then = {item['path']: item['sha256'] for item in screen.get('inputs', [])}
    for name in ('select/selection_%s.json', 'notes_ord/ordinary_notes_%s.json', 'support/support_results_%s.json'):
        key = rel(ctx.work / (name % set_name))
        if then.get(key) != ctx.inputs.get(key):
            return None
    dropped = {pid for pid in data['tasks'] if data['status'][pid] in SUPPORT_DROPPED}
    hit = {row['passage_id'] for row in screen['passages'] if row['hit']}
    return remaining(data['tasks'], dropped, hit)


def floor_check(C, numbers):
    """The launch floor of the plan, on the numbers that are left. numbers maps a set name to its numbers or to None."""
    floor, tiers = C['launch_floor'], C['tiers']
    lines, met, complete = [], True, True
    for set_name in SETS:
        left = numbers.get(set_name)
        for family, name in (('role_step', '%s_role_step_tasks_min'), ('plain_fact', '%s_plain_fact_tasks_min')):
            need = floor[name % set_name]
            if left is None:
                complete = False
                lines.append({'what': '%s %s tasks' % (set_name, family), 'left': None, 'floor': need, 'met': None})
                continue
            have = left['%s_tasks_left' % family]
            met = met and have >= need
            lines.append({'what': '%s %s tasks' % (set_name, family), 'left': have, 'floor': need, 'met': have >= need})
    tier = None
    if complete:
        final = numbers['final']
        if not met or final['role_step_tasks_left'] < tiers['no_launch_below_final_role_step_tasks']:
            tier = 'NO_LAUNCH'
        elif (final['role_step_tasks_left'] >= tiers['as_it_stands']['final_role_step_tasks_min']
              and final['passages_left_with_a_role_step_task'] >= tiers['as_it_stands']['final_passages_with_a_role_step_task_min']):
            tier = 'AS_IT_STANDS'
        else:
            tier = 'EXPLORATORY'
    return {'lines': lines, 'checked_on_both_sets': complete, 'met': (met if complete else (False if not met else None)), 'tier': tier}


def report_only_run(ctx, rules, set_name):
    """The early look at the practice set (FILE_FORMATS.md section 10.2). It prints its counts and writes no file."""
    if set_name != 'practice':
        raise Stop('REPORT_ONLY_IS_FOR_THE_PRACTICE_SET', '--report-only is refused with --set %s. It is for the practice set only.' % set_name)
    # no "closed by" step: nothing is written, so a later seal step can not be harmed
    seal, sealed = check_seal(ctx, SEAL_NEED_REPORT_ONLY, None)
    # the practice notes and the support results are sealed later, in step 4; the files below are sealed already
    must_be_sealed(ctx, sealed, [REAL_WORK / 'PLAN_CONSTANTS.json', ctx.work / 'elig' / 'eligibility.json',
                                 ctx.work / 'notes_role' / 'role_notes.json', ctx.work / 'select' / 'selection_practice.json'])
    texts = passage_texts(ctx)
    role_notes = ctx.need_json(ctx.work / 'notes_role' / 'role_notes.json', 'casalescence/optionb/role_notes/v1')
    body, left = screen_set(ctx, rules, set_name, texts, role_notes, report_only=True)
    floor = floor_check(ctx.constants, {'practice': left, 'final': None})
    lines = [line for line in floor['lines'] if line['what'].startswith('practice ')]
    under = any(line['met'] is False for line in lines)
    print(json.dumps({
        'program': PROGRAM, 'dry_fixture': ctx.dry, 'status': 'REPORT_ONLY_PRACTICE_FLOOR_NOT_MET' if under else 'REPORT_ONLY',
        'set': set_name, 'seal': seal, 'files_written': [],
        'screen_counts': body['counts'],
        'passages_hit': [{'passage_id': row['passage_id'], 'rules': sorted({one['rule'] for one in row['hits']})} for row in body['passages'] if row['hit']],
        'what_would_be_left': left, 'practice_launch_floor': lines,
        'what_this_run_is': 'An early look. It wrote no file. The screen of record is the later full run after seal step 4. '
                            'A hit never causes a note to be written again. No brief, no filter and no screen rule is changed because of '
                            'these numbers without a new reviewed plan version.',
        'next': ('DO NOT LAUNCH. The practice set is under the launch floor. No final question is written. Report these numbers to the owner.' if under else
                 'The practice set is at or above both practice launch floors. The final questions may now be written.')}, ensure_ascii=False, indent=1))
    return 3 if under else 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description='Option B Step 7: the answer-leak screen for every note of every group.')
    parser.add_argument('--set', dest='set_name', required=True, choices=['practice', 'final', 'both'])
    parser.add_argument('--report-only', action='store_true',
                        help='practice set only: screen the practice notes as they stand, print the counts, write no file (needs seal steps 3A and 3B, not 4)')
    parser.add_argument('--work', default=None, help='dry fixture folder under optionb/dry/ (never for a real run)')
    args = parser.parse_args(argv)

    ctx = Ctx(args.work)
    C = ctx.constants
    rules = Rules(C)
    sets = list(SETS) if args.set_name == 'both' else [args.set_name]
    if args.report_only:
        return report_only_run(ctx, rules, args.set_name)
    need = SEAL_NEED['final'] if 'final' in sets else SEAL_NEED['practice']
    seal, sealed = check_seal(ctx, need, SEAL_CLOSED_BY)
    paths = [REAL_WORK / 'PLAN_CONSTANTS.json', ctx.work / 'elig' / 'eligibility.json', ctx.work / 'notes_role' / 'role_notes.json']
    for set_name in sets:
        paths += [ctx.work / 'select' / ('selection_%s.json' % set_name), ctx.work / 'notes_ord' / ('ordinary_notes_%s.json' % set_name),
                  ctx.work / 'support' / ('support_results_%s.json' % set_name)]
    must_be_sealed(ctx, sealed, paths)

    texts = passage_texts(ctx)
    role_notes = ctx.need_json(ctx.work / 'notes_role' / 'role_notes.json', 'casalescence/optionb/role_notes/v1')

    numbers, counts, bodies = {}, {}, {}
    for set_name in sets:
        bodies[set_name], numbers[set_name] = screen_set(ctx, rules, set_name, texts, role_notes)
        counts[set_name] = bodies[set_name]['counts']
    for set_name in sets:
        ctx.write_json(ctx.work / 'screen' / ('leak_screen_%s.json' % set_name), 'casalescence/optionb/leak_screen/v1', bodies[set_name])
    for set_name in SETS:
        if set_name not in numbers:
            numbers[set_name] = other_set_numbers(ctx, set_name)

    floor = floor_check(C, numbers)
    stop_launch = floor['met'] is False
    print(json.dumps({
        'program': PROGRAM, 'dry_fixture': ctx.dry, 'status': 'SCREENED_LAUNCH_FLOOR_NOT_MET' if stop_launch else 'SCREENED',
        'sets_screened_in_this_run': sets, 'seal': seal,
        'screen_counts': counts, 'what_is_left': numbers, 'launch_floor': floor,
        'a_hit_never_causes_a_rewrite': 'This program calls nobody. The note writer reads only the support check results.',
        'next': ('DO NOT LAUNCH. The launch floor is not met. Report these numbers to the owner.' if stop_launch else
                 'Next: tools/ob_assemble.py.' if floor['checked_on_both_sets'] else
                 'Screen the other set as well. The launch floor can be checked only on both sets.')}, ensure_ascii=False, indent=1))
    return 3 if stop_launch else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Stop as stop:
        print(json.dumps({'program': PROGRAM, 'status': 'STOP', 'code': stop.args[0], 'reason': stop.args[1]}, ensure_ascii=False, indent=1))
        sys.exit(2)
