"""Option B job: the gate program (practice Gates 1 to 7) and the shared call plan.

WHAT THIS FILE DOES
  1. It holds the small rules that the runner, the gate and the analysis must apply the same way:
     how a call id is written, in which order calls are made, how a file is created once.
  2. It decides the practice gates. It reads the practice call lines and the practice keys.
     It writes GATE.json: go or stop, the chosen closing wording, the chosen level,
     the blocks the final phase may run, and each gate's counts.

RULES IT FOLLOWS
  - Every number comes from PLAN_CONSTANTS.json. Percent rules use whole numbers only.
  - A failed gate is a failure. The first gate that fails gives the stop code.
  - Gate 4 (format) counts role-step tasks and plain-fact tasks apart, as validity rule V3 does on the
    final tasks. Both task families must clear both numbers in every must-run group (review round 1).
  - It never reads a final key. It never reads a final call line.
  - It writes only into the output folder it is given. It creates a file once. It never renames or deletes.

Status: SOURCE ONLY. Not run on the laptop. First exercised by the AWS pre-check job
(the runner's self-test runs this program on five made-up answer sets).
Standard library only.
"""
import sys

sys.dont_write_bytecode = True  # the package folder is sealed: no __pycache__ may appear in it

import argparse
import hashlib
import json
import os
import random
import re
import time
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import scorer_v0_1_1 as scorer

SCHEMA_GATE = 'casalescence/optionb/gate/v1'
PROGRAM = 'job/gate_b1.py'

# Group names. They are the names in PLAN_CONSTANTS.json under "groups".
NONE = 'NONE'
FILLER = 'FILLER'
ROLE = 'ROLE'
MIXED = 'MIXED'
ORD_INFORMED = 'ORD-INFORMED'
ORD_FREE = 'ORD-FREE'
QUOTES_ONLY = 'QUOTES-ONLY'
ANSWER_GIVEN = 'ANSWER-GIVEN'
NO_PASSAGE = 'NO-PASSAGE'

BLOCK_MUST_RUN = 'MUST_RUN'
BLOCK_NO_PASSAGE = 'NO-PASSAGE'
LEVEL_EASY = 1   # four options shown
LEVEL_HARD = 2   # six options shown
SELFTEST_STOP = 'GATE_STOP_SELFTEST'
GO = 'GO'
UNDEFINED = 'undefined'
SAFE_NAME = re.compile(r'^[A-Za-z0-9._-]+$')


# =============================================================================================
# Small shared helpers: time, hashes, reading, writing, text for ratios
# =============================================================================================

def utc_now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def sha256_hex(data):
    return hashlib.sha256(data).hexdigest()


class Inputs(object):
    """Reads files and remembers the sha256 of every file that was read."""

    def __init__(self):
        self.items = []
        self._seen = set()

    def note(self, label, digest):
        if label not in self._seen:
            self._seen.add(label)
            self.items.append({'path': label, 'sha256': digest})

    def read_bytes(self, path, label):
        with open(path, 'rb') as handle:
            data = handle.read()
        self.note(label, sha256_hex(data))
        return data

    def read_json(self, path, label):
        return json.loads(self.read_bytes(path, label).decode('utf-8'))

    def read_json_or_none(self, path, label):
        """None when the file is missing or is not readable JSON."""
        try:
            return self.read_json(path, label)
        except (OSError, ValueError):
            return None

    def read_jsonl(self, path, label):
        """Returns (rows, number of lines that were not readable JSON objects). A missing file gives ([], 0)."""
        try:
            data = self.read_bytes(path, label)
        except OSError:
            return [], 0
        rows, bad = [], 0
        for line in data.split(b'\n'):
            if not line.strip():
                continue
            try:
                row = json.loads(line.decode('utf-8'))
            except ValueError:
                bad += 1
                continue
            if isinstance(row, dict):
                rows.append(row)
            else:
                bad += 1
        return rows, bad


def dump_json(value, sort_keys=False):
    """The text of a JSON file: indent 1, no not-a-number value allowed, one LF at the end."""
    return json.dumps(value, indent=1, ensure_ascii=False, allow_nan=False, sort_keys=sort_keys) + '\n'


def dump_line(value, sort_keys=False):
    """The text of one JSONL line, with its LF."""
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=sort_keys) + '\n'


def create_once(folder, name, text):
    """Creates folder/name, writes the text, and forces it to disk. Returns the bytes written.

    The file must not exist yet. Nothing is renamed, deleted or written to a temporary file.
    """
    if not SAFE_NAME.match(name):
        raise ValueError('UNSAFE_FILE_NAME ' + repr(name))
    data = text.encode('utf-8')
    with open(os.path.join(folder, name), 'xb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    return data


def made_by(program, program_path):
    with open(program_path, 'rb') as handle:
        digest = sha256_hex(handle.read())
    return {'program': program, 'sha256': digest, 'utc': utc_now()}


def fraction_text(value, places=2):
    """A Fraction as decimal text, rounded half away from zero. No float is used, so no not-a-number can appear."""
    scale = 10 ** places
    numerator = abs(value.numerator) * scale
    denominator = value.denominator
    rounded = (2 * numerator + denominator) // (2 * denominator)
    sign = '-' if (value < 0 and rounded != 0) else ''
    return '%s%d.%0*d' % (sign, rounded // scale, places, rounded % scale)


def points_text(part, whole):
    """100 * part / whole as text with two decimals. The text 'undefined' when whole is 0."""
    if whole == 0:
        return UNDEFINED
    return fraction_text(Fraction(100 * part, whole))


def at_least_percent(part, whole, percent):
    return whole > 0 and 100 * part >= percent * whole


def at_most_percent(part, whole, percent):
    return whole > 0 and 100 * part <= percent * whole


# =============================================================================================
# The call plan: call ids, levels, call order
# =============================================================================================

def make_call_id(phase, task_id, group, level, wording):
    return '%s|%s|%s|L%d|W%d' % (phase, task_id, group, level, wording)


def options_at(task, level):
    return task['options'][str(level)]


def letters_at(task, level):
    return [option['letter'] for option in options_at(task, level)]


def task_levels(task):
    return sorted(int(name) for name in task['options'])


def level_used(task, chosen_level):
    """A role-step task uses the chosen level. A plain-fact task has level 1 only."""
    return chosen_level if str(chosen_level) in task['options'] else LEVEL_EASY


def is_role_step(task):
    return task['family'] == 'role_step'


def seeded_task_order(tasks, seed):
    """Task ids sorted, then shuffled with random.Random(seed)."""
    ids = sorted(task['task_id'] for task in tasks)
    random.Random(seed).shuffle(ids)
    return ids


def _call(phase, step, task, group, level, wording):
    return {'call_id': make_call_id(phase, task['task_id'], group, level, wording), 'phase': phase, 'step': step,
            'task_id': task['task_id'], 'passage_id': task['passage_id'], 'family': task['family'],
            'group': group, 'level': level, 'wording': wording}


def wording_numbers(constants):
    return list(range(1, len(constants['prompt']['closing_wordings_in_order']) + 1))


def practice_calls(constants, parts, step, chosen_wording=None, chosen_level=None):
    """The planned calls of one practice step, in call order.

    P1: group NONE, level 1, every practice task, once under each closing wording.
    P2: group NONE, level 2, every practice role-step task, under the chosen wording.
    P3: at the chosen level and wording: every other must-run group of the task, then, for a
        role-step task, ANSWER-GIVEN and NO-PASSAGE.
    Tasks come in the seeded order; a task's calls sit back to back.
    """
    groups = constants['groups']
    by_id = dict((task['task_id'], task) for task in parts['tasks'])
    calls = []
    for task_id in seeded_task_order(parts['tasks'], constants['seeds']['practice_call_order']):
        task = by_id[task_id]
        if step == 'P1':
            for wording in wording_numbers(constants):
                calls.append(_call('practice', step, task, NONE, LEVEL_EASY, wording))
        elif step == 'P2':
            if is_role_step(task):
                calls.append(_call('practice', step, task, NONE, LEVEL_HARD, chosen_wording))
        elif step == 'P3':
            level = level_used(task, chosen_level)
            for group in task['groups']:
                if group != NONE:
                    calls.append(_call('practice', step, task, group, level, chosen_wording))
            if is_role_step(task):
                for group in list(groups['practice_only_role_step']) + list(groups['task_check_role_step']):
                    calls.append(_call('practice', step, task, group, level, chosen_wording))
        else:
            raise ValueError('UNKNOWN_PRACTICE_STEP ' + repr(step))
    return calls


def final_calls(constants, parts, chosen_level, chosen_wording, blocks):
    """The planned final calls, in call order.

    Block MUST_RUN: every task in the seeded order, its must-run groups back to back.
    Block NO-PASSAGE: group NO-PASSAGE on every role-step task, in the same task order.
    The call id always starts with 'final'.
    """
    by_id = dict((task['task_id'], task) for task in parts['tasks'])
    order = seeded_task_order(parts['tasks'], constants['seeds']['final_call_order'])
    calls = []
    if BLOCK_MUST_RUN in blocks:
        for task_id in order:
            task = by_id[task_id]
            for group in task['groups']:
                calls.append(_call('final', BLOCK_MUST_RUN, task, group, level_used(task, chosen_level), chosen_wording))
    if BLOCK_NO_PASSAGE in blocks:
        for task_id in order:
            task = by_id[task_id]
            if is_role_step(task):
                calls.append(_call('final', BLOCK_NO_PASSAGE, task, NO_PASSAGE, level_used(task, chosen_level), chosen_wording))
    return calls


def planned_call_counts(constants, practice_parts, final_parts):
    """Whole-number call counts for the whole job. One call is one task in one group."""
    def split(parts):
        role = sum(1 for task in parts['tasks'] if is_role_step(task))
        return role, len(parts['tasks']) - role
    groups = constants['groups']
    wordings = len(wording_numbers(constants))
    role_p, fact_p = split(practice_parts)
    role_f, fact_f = split(final_parts)
    role_groups = len(groups['by_family']['role_step'])
    fact_groups = len(groups['by_family']['plain_fact'])
    extra = len(groups['practice_only_role_step']) + len(groups['task_check_role_step'])
    practice = (wordings * (role_p + fact_p)            # P1
                + role_p                                # P2
                + (role_groups - 1 + extra) * role_p    # P3, role-step tasks
                + (fact_groups - 1) * fact_p)           # P3, plain-fact tasks
    must_run = role_groups * role_f + fact_groups * fact_f
    no_passage = role_f
    return {'practice': practice, 'final_must_run': must_run, 'final_no_passage': no_passage,
            'whole_job': practice + must_run + no_passage,
            'cap': constants['aws']['gpu_job']['call_cap']}


# =============================================================================================
# Reading practice call lines against the practice keys
# =============================================================================================

def index_lines(rows):
    """call id -> first line with that id. Also returns how many later lines repeated an id."""
    by_id, repeated = {}, 0
    for row in rows:
        call_id = row.get('call_id')
        if not isinstance(call_id, str):
            continue
        if call_id in by_id:
            repeated += 1
            continue
        by_id[call_id] = row
    return by_id, repeated


def judge(line, key_letter, letters):
    """One call line against its key. Returns (category, clean)."""
    raw = line.get('raw_answer')
    cut_off = bool(line.get('cut_off'))
    if not isinstance(raw, str):
        raw = ''   # cannot happen with the runner's lines; an empty reply is FORMAT_FAIL
    category = scorer.categorize(raw, key_letter, cut_off)
    return category, scorer.clean_reply(raw, cut_off, letters)


def tally_calls(calls, by_id, tasks, keys):
    """Counts over a list of planned calls. A planned call with no line is counted as missing."""
    counts = {'planned': len(calls), 'present': 0, 'correct': 0, 'clean': 0, 'format_fail_plus_cut_off': 0}
    for call in calls:
        line = by_id.get(call['call_id'])
        if line is None:
            continue
        task = tasks[call['task_id']]
        key_letter = keys[call['task_id']][str(call['level'])]
        category, clean = judge(line, key_letter, letters_at(task, call['level']))
        counts['present'] += 1
        if category == 'CORRECT':
            counts['correct'] += 1
        if clean:
            counts['clean'] += 1
        if category in ('FORMAT_FAIL', 'CUT_OFF'):
            counts['format_fail_plus_cut_off'] += 1
    counts['missing'] = counts['planned'] - counts['present']
    return counts


def p1_counts(p1_calls, by_id, tasks, keys):
    """Gate 1 input: clean replies per closing wording. Returns ({'1': [clean, replies], ...}, missing lines)."""
    by_wording = {}
    for call in p1_calls:
        by_wording.setdefault(str(call['wording']), []).append(call)
    clean_by_wording, missing = {}, 0
    for name in sorted(by_wording, key=int):
        counts = tally_calls(by_wording[name], by_id, tasks, keys)
        clean_by_wording[name] = [counts['clean'], counts['planned']]
        missing += counts['missing']
    return clean_by_wording, missing


def p2_counts(p1_calls, p2_calls, by_id, tasks, keys, wording):
    """Gate 2 and Gate 3 input, under the chosen wording.

    Returns (correct_by_level, plain_fact_correct, missing P2 lines).
    Level 1 comes from the P1 lines. Level 2 comes from the P2 lines.
    """
    level_1 = [call for call in p1_calls if call['wording'] == wording and is_role_step(tasks[call['task_id']])]
    facts = [call for call in p1_calls if call['wording'] == wording and not is_role_step(tasks[call['task_id']])]
    one = tally_calls(level_1, by_id, tasks, keys)
    two = tally_calls(p2_calls, by_id, tasks, keys)
    fact = tally_calls(facts, by_id, tasks, keys)
    correct_by_level = {str(LEVEL_EASY): [one['correct'], one['planned']],
                        str(LEVEL_HARD): [two['correct'], two['planned']]}
    return correct_by_level, [fact['correct'], fact['planned']], two['missing']


# =============================================================================================
# The decisions of Gates 1, 2 and 3. The runner uses the same functions during practice.
# =============================================================================================

def decide_wording(clean_by_wording):
    """Gate 1: the wording with the most clean replies. A tie goes to the wording listed first."""
    best, best_count = None, -1
    for name in sorted(clean_by_wording, key=int):
        count = clean_by_wording[name][0]
        if count > best_count:
            best, best_count = int(name), count
    return best


def inside_window(part, whole, window):
    low, high = window
    return whole > 0 and low * whole <= 100 * part <= high * whole


def decide_level(correct_by_level, windows):
    """Gate 2. Returns (chosen level or None, {'1': inside?, '2': inside?}).

    Both inside: the level nearer 50 percent; a tie goes to level 1. One inside: that one. None: no level.
    """
    inside = {}
    for name in sorted(correct_by_level, key=int):
        part, whole = correct_by_level[name]
        inside[name] = inside_window(part, whole, windows[name])
    names = [name for name in sorted(inside, key=int) if inside[name]]
    if not names:
        return None, inside

    def distance(name):
        part, whole = correct_by_level[name]
        return abs(Fraction(part, whole) - Fraction(1, 2))

    best = names[0]
    for name in names[1:]:
        if distance(name) < distance(best):   # strictly nearer; on a tie the lower level stays
            best = name
    return int(best), inside


def decide_after_p2(constants, correct_by_level, plain_fact_correct):
    """Gates 2 and 3 together. Returns (chosen level or None, inside, early stop code or None)."""
    gates = constants['gates']
    level, inside = decide_level(correct_by_level, gates['gate_2']['window_percent'])
    early = None
    if level is None:
        early = gates['gate_2']['stop_code']
    elif not at_least_percent(plain_fact_correct[0], plain_fact_correct[1], gates['gate_3']['min_percent']):
        early = gates['gate_3']['stop_code']
    return level, inside, early


def compare_decisions(decisions, wording, clean_by_wording, level, correct_by_level, plain_fact_correct, early):
    """The gate must reach the decisions that run-practice wrote down. Returns a problem text, or None."""
    after = {}
    for row in decisions:
        after[row.get('after')] = row
    first, second = after.get('P1'), after.get('P2')
    if first is None:
        return 'practice_decisions.jsonl has no line for P1'
    if first.get('chosen_wording') != wording or first.get('clean_by_wording') != clean_by_wording:
        return 'the P1 decision differs'
    if second is None:
        return 'practice_decisions.jsonl has no line for P2'
    if (second.get('chosen_level') != level or second.get('correct_by_level') != correct_by_level
            or second.get('plain_fact_correct') != plain_fact_correct or second.get('early_stop') != early):
        return 'the P2 decision differs'
    return None


# =============================================================================================
# The gate itself
# =============================================================================================

def run_gate(constants, parts, keys, rows, decisions, run_status, selftest, planned_final, now_unix, deadline_unix):
    """Applies Gates 0 to 7 in order. Returns the body of GATE.json (without the three header fields).

    constants      PLAN_CONSTANTS.json
    parts          prompt_parts_practice.json
    keys           the "keys" object of keys_practice.json
    rows           the practice call lines
    decisions      the lines of practice_decisions.jsonl, or None in a self-test trial
    run_status     the lines of run_status.jsonl, or None
    selftest       selftest.json, or a stand-in with "status"
    planned_final  {'final_must_run': n, 'final_no_passage': n}
    now_unix, deadline_unix   whole seconds; the work cutoff is the deadline
    """
    gates = constants['gates']
    order = gates['order']
    if len(order) != 8 or SELFTEST_STOP not in constants['stop_codes']:
        raise ValueError('PLAN_CONSTANTS_GATE_LIST_NOT_AS_EXPECTED')
    g0, g1, g2, g3, g4, g5, g6, g7 = order
    # Gate 4 counts the task families apart. The plan must name every task family, and no other.
    groups_of_family = constants['groups']['by_family']
    families = list(gates['gate_4']['families_counted_apart'])
    if sorted(families) != sorted(groups_of_family) or len(set(families)) != len(families):
        raise ValueError('PLAN_CONSTANTS_GATE_4_FAMILIES_NOT_AS_EXPECTED')
    time_stop = gates['gate_7']['stop_code']
    result = {
        'go': False, 'stop_code': None, 'first_failing_gate': None,
        'chosen_wording': None, 'chosen_level': None, 'final_blocks': [],
        'gates': dict((name, {'passed': None}) for name in order),
        'printed_no_rule': {'role_vs_ord_informed_differ': None, 'clean_gap_points_text': {}},
        'seconds_per_call_text': UNDEFINED, 'decided_unix': int(now_unix), 'detail': None,
    }
    tasks = dict((task['task_id'], task) for task in parts['tasks'])
    by_id, repeated = index_lines(rows)

    def stop(code, gate_name, detail=None):
        result['stop_code'] = code
        result['first_failing_gate'] = gate_name
        result['detail'] = detail
        result['gates'][gate_name]['passed'] = False
        return result

    def stop_missing(gate_name, step, missing):
        """Practice lines are missing, so the gate cannot be worked out. That is a stop, never a pass."""
        events = [row.get('event') for row in (run_status or []) if row.get('command') == 'run-practice']
        detail = 'step %s: %d planned practice call(s) have no output line; run-practice events: %s' % (
            step, missing, ', '.join(str(event) for event in events) or 'none recorded')
        code = time_stop if 'STOP_WORK_CUTOFF' in events else SELFTEST_STOP
        return stop(code, gate_name, detail)

    # ---- Gate 0: the self-test must have passed -------------------------------------------------
    status = selftest.get('status') if isinstance(selftest, dict) else None
    result['gates'][g0] = {'status': status, 'passed': status == constants['selftest_pass_status']}
    if status != constants['selftest_pass_status']:
        code = status if status in constants['stop_codes'] else SELFTEST_STOP
        return stop(code, g0, 'the self-test status is %r' % (status,))
    if repeated:
        return stop(SELFTEST_STOP, g0, '%d practice call line(s) repeat a call id' % repeated)

    # ---- Gate 1: closing wording (no stop code of its own) ---------------------------------------
    p1_calls = practice_calls(constants, parts, 'P1')
    clean_by_wording, missing = p1_counts(p1_calls, by_id, tasks, keys)
    if missing or not p1_calls:
        return stop_missing(g1, 'P1', missing)
    wording = decide_wording(clean_by_wording)
    result['chosen_wording'] = wording
    result['gates'][g1] = {'clean_by_wording': clean_by_wording, 'passed': True}

    # ---- Gate 2: difficulty, and Gate 3: no-harm base -------------------------------------------
    p2_calls = practice_calls(constants, parts, 'P2', chosen_wording=wording)
    correct_by_level, plain_fact_correct, missing = p2_counts(p1_calls, p2_calls, by_id, tasks, keys, wording)
    if missing:
        return stop_missing(g2, 'P2', missing)
    level, inside, early = decide_after_p2(constants, correct_by_level, plain_fact_correct)
    if decisions is not None:
        problem = compare_decisions(decisions, wording, clean_by_wording, level, correct_by_level,
                                    plain_fact_correct, early)
        if problem is not None:
            return stop(SELFTEST_STOP, g1, 'the gate and run-practice do not agree: ' + problem)
    result['gates'][g2] = {'correct_by_level': correct_by_level, 'inside_window': inside, 'passed': level is not None}
    if level is None:
        return stop(gates['gate_2']['stop_code'], g2)
    result['chosen_level'] = level
    g3_passed = at_least_percent(plain_fact_correct[0], plain_fact_correct[1], gates['gate_3']['min_percent'])
    result['gates'][g3] = {'correct': plain_fact_correct, 'passed': g3_passed}
    if not g3_passed:
        return stop(gates['gate_3']['stop_code'], g3)

    # ---- P3 must be complete before Gates 4 to 7 -------------------------------------------------
    p3_calls = practice_calls(constants, parts, 'P3', chosen_wording=wording, chosen_level=level)
    missing = sum(1 for call in p3_calls if call['call_id'] not in by_id)
    if missing or not p3_calls:
        return stop_missing(g4, 'P3', missing)

    # Every practice call at the chosen level under the chosen wording.
    chosen_calls = [call for call in p1_calls
                    if call['wording'] == wording and level_used(tasks[call['task_id']], level) == LEVEL_EASY]
    if level == LEVEL_HARD:
        chosen_calls.extend(p2_calls)
    chosen_calls.extend(p3_calls)

    def group_counts(group):
        return tally_calls([call for call in chosen_calls if call['group'] == group], by_id, tasks, keys)

    must_run = constants['groups']['must_run_in_order']

    # ---- Printed with no rule attached ------------------------------------------------------------
    differ, role_tasks = 0, 0
    for task_id in sorted(tasks):
        task = tasks[task_id]
        if not is_role_step(task):
            continue
        used = level_used(task, level)
        key_letter = keys[task_id][str(used)]
        line_role = by_id.get(make_call_id('practice', task_id, ROLE, used, wording))
        line_ord = by_id.get(make_call_id('practice', task_id, ORD_INFORMED, used, wording))
        if line_role is None or line_ord is None:
            continue
        role_tasks += 1
        right_role = judge(line_role, key_letter, letters_at(task, used))[0] == 'CORRECT'
        right_ord = judge(line_ord, key_letter, letters_at(task, used))[0] == 'CORRECT'
        if right_role != right_ord:
            differ += 1
    result['printed_no_rule']['role_vs_ord_informed_differ'] = [differ, role_tasks]
    role_counts = group_counts(ROLE)
    for group in constants['groups']['ordinary']:
        counts = group_counts(group)
        if role_counts['planned'] and counts['planned']:
            gap = (Fraction(role_counts['clean'], role_counts['planned'])
                   - Fraction(counts['clean'], counts['planned'])) * 100
            result['printed_no_rule']['clean_gap_points_text'][group] = fraction_text(gap)
        else:
            result['printed_no_rule']['clean_gap_points_text'][group] = UNDEFINED

    # ---- Gate 4: format. Role-step tasks and plain-fact tasks are counted apart ---------------------
    # Validity rule V3 counts the final tasks the same way. Counted together, a group could pass practice
    # with a format problem on one task family only, and that problem would then void the run after the
    # final tasks were spent. A family passes when its clean replies reach the plan's least share and its
    # FORMAT_FAIL plus CUT_OFF replies stay at or under the plan's largest share. A family with no call is
    # not a pass.
    rule = gates['gate_4']

    def format_ok(counts):
        return (at_least_percent(counts['clean'], counts['planned'], rule['clean_min_percent'])
                and at_most_percent(counts['format_fail_plus_cut_off'], counts['planned'],
                                    rule['format_fail_plus_cut_off_max_percent']))

    def family_counts(group, family):
        return tally_calls([call for call in chosen_calls if call['group'] == group and call['family'] == family],
                           by_id, tasks, keys)

    by_group, g4_passed = {}, True
    for group in must_run:
        row, counted, group_passed = {}, 0, True
        for family in families:
            if group not in groups_of_family[family]:
                continue   # the group has no task of this family: QUOTES-ONLY has role-step tasks only
            counts = family_counts(group, family)
            passed = format_ok(counts)
            row[family] = {'clean': [counts['clean'], counts['planned']],
                           'format_fail_plus_cut_off': [counts['format_fail_plus_cut_off'], counts['planned']],
                           'passed': passed}
            counted += 1
            group_passed = group_passed and passed
        group_passed = group_passed and counted > 0   # a group that was counted in no family never passes
        row['passed'] = group_passed
        by_group[group] = row
        g4_passed = g4_passed and group_passed
    no_passage_counts = group_counts(NO_PASSAGE)   # NO-PASSAGE runs on role-step tasks only
    no_passage_dropped = not format_ok(no_passage_counts)
    result['gates'][g4] = {
        'by_group': by_group,
        'no_passage': {'clean': [no_passage_counts['clean'], no_passage_counts['planned']],
                       'format_fail_plus_cut_off': [no_passage_counts['format_fail_plus_cut_off'],
                                                    no_passage_counts['planned']]},
        'no_passage_dropped': no_passage_dropped, 'passed': g4_passed}
    if not g4_passed:
        under = ['%s on %s tasks' % (group, family) for group in must_run for family in families
                 if family in by_group[group] and not by_group[group][family]['passed']]
        return stop(rule['stop_code'], g4, 'under the format bar: ' + (', '.join(under) or 'a group with no counted family'))

    # ---- Gate 5: the notes are read ---------------------------------------------------------------
    rule = gates['gate_5']
    counts = group_counts(ANSWER_GIVEN)
    g5_passed = (counts['clean'] >= rule['min_clean_replies']
                 and at_least_percent(counts['correct'], counts['clean'], rule['min_percent']))
    result['gates'][g5] = {'clean_replies': counts['clean'], 'correct_among_clean': counts['correct'],
                           'replies': counts['planned'], 'passed': g5_passed}
    if not g5_passed:
        return stop(rule['stop_code'], g5)

    # ---- Gate 6: the passage is needed -------------------------------------------------------------
    rule = gates['gate_6']
    shown = constants['levels'][str(level)]['options_shown']
    part, whole = no_passage_counts['correct'], no_passage_counts['planned']
    # "above chance plus points" with k options: 100 * part * k > (100 + points * k) * whole
    guessable = whole > 0 and 100 * part * shown > (100 + rule['stop_if_above_chance_plus_points'] * shown) * whole
    none_part, none_whole = correct_by_level[str(level)]
    if whole > 0 and none_whole > 0:
        difference = fraction_text((Fraction(part, whole) - Fraction(none_part, none_whole)) * 100)
    else:
        difference = UNDEFINED
    result['gates'][g6] = {'correct': [part, whole], 'options_shown': shown,
                           'no_passage_minus_none_points_text': difference, 'passed': not guessable}
    if guessable:
        return stop(rule['stop_code'], g6)

    # ---- Gate 7: time -------------------------------------------------------------------------------
    rule = gates['gate_7']
    total, count = Fraction(0), 0
    for call in chosen_calls:
        if call['group'] not in must_run:
            continue
        line = by_id[call['call_id']]
        try:
            seconds = Fraction(str(line.get('seconds_text')))
        except (ValueError, ZeroDivisionError):
            return stop(SELFTEST_STOP, g7, 'call %s has no readable seconds_text' % call['call_id'])
        if seconds < 0:
            return stop(SELFTEST_STOP, g7, 'call %s has negative seconds' % call['call_id'])
        total += seconds
        count += 1
    if count == 0:
        return stop(SELFTEST_STOP, g7, 'no practice call to measure seconds per call')
    seconds_per_call = total / count
    result['seconds_per_call_text'] = fraction_text(seconds_per_call)
    seconds_left = int(deadline_unix) - int(now_unix)
    must_run_calls = int(planned_final['final_must_run'])
    no_passage_calls = int(planned_final['final_no_passage'])
    margin = Fraction(rule['margin_percent'], 100)
    spare = rule['spare_seconds']
    must_run_fits = must_run_calls * seconds_per_call * margin + spare <= seconds_left
    no_passage_fits = (must_run_calls + no_passage_calls) * seconds_per_call * margin + spare <= seconds_left
    result['gates'][g7] = {'must_run_calls': must_run_calls, 'no_passage_calls': no_passage_calls,
                           'seconds_left': seconds_left, 'must_run_fits': must_run_fits,
                           'no_passage_fits': no_passage_fits, 'passed': must_run_fits}
    if not must_run_fits:
        return stop(rule['stop_code'], g7)

    # ---- Every gate passed ---------------------------------------------------------------------------
    result['go'] = True
    result['final_blocks'] = [BLOCK_MUST_RUN]
    if no_passage_fits and not no_passage_dropped:
        result['final_blocks'].append(BLOCK_NO_PASSAGE)
    return result


def gate_word(result):
    """What the gate program 'prints': GO, or the stop code."""
    return GO if result.get('go') is True else str(result.get('stop_code'))


def gate_files(package, out, deadline_unix, now_unix=None, calls_name='calls_practice.jsonl',
               gate_name='GATE.json', trial=None):
    """Reads the files, decides, writes the gate file once, prints a short report. Returns the gate body.

    Real run: trial is None. The self-test passes trial = {'planned_final': {...}} and a made-up clock;
    then no decision file, no status file and no selftest.json are read.
    """
    inputs = Inputs()
    constants = inputs.read_json(os.path.join(package, 'PLAN_CONSTANTS.json'), 'package/PLAN_CONSTANTS.json')
    parts = inputs.read_json(os.path.join(package, 'prompts', 'prompt_parts_practice.json'),
                             'package/prompts/prompt_parts_practice.json')
    keys = inputs.read_json(os.path.join(package, 'keys_practice', 'keys_practice.json'),
                            'package/keys_practice/keys_practice.json')['keys']
    rows, unreadable = inputs.read_jsonl(os.path.join(out, calls_name), 'out/' + calls_name)
    if trial is None:
        selftest = inputs.read_json_or_none(os.path.join(out, 'selftest.json'), 'out/selftest.json')
        decisions, _ = inputs.read_jsonl(os.path.join(out, 'practice_decisions.jsonl'), 'out/practice_decisions.jsonl')
        run_status, _ = inputs.read_jsonl(os.path.join(out, 'run_status.jsonl'), 'out/run_status.jsonl')
        planned = (selftest or {}).get('planned_calls') or {'final_must_run': 0, 'final_no_passage': 0}
    else:
        selftest = {'status': constants['selftest_pass_status']}
        decisions, run_status = None, None
        planned = trial['planned_final']
    if now_unix is None:
        now_unix = int(time.time()) + 1   # rounded up, so the time left is never overstated
    result = run_gate(constants, parts, keys, rows, decisions, run_status, selftest, planned, now_unix, deadline_unix)
    document = {'schema': SCHEMA_GATE, 'made_by': made_by(PROGRAM, os.path.abspath(__file__)), 'inputs': inputs.items}
    document.update(result)
    document['unreadable_practice_lines'] = unreadable
    create_once(out, gate_name, dump_json(document))
    print('GATE %s' % gate_word(result))
    print('  chosen wording: %s   chosen level: %s   final blocks: %s' % (
        result['chosen_wording'], result['chosen_level'], ', '.join(result['final_blocks']) or 'none'))
    if result['first_failing_gate'] is not None:
        print('  first failing gate: %s   detail: %s' % (result['first_failing_gate'], result['detail']))
    extras = result['printed_no_rule']
    print('  printed, no rule attached: ROLE and ORD-INFORMED differ on %s practice role-step tasks; '
          'clean-reply gap ROLE minus ordinary, in points: %s' % (
              extras['role_vs_ord_informed_differ'], json.dumps(extras['clean_gap_points_text'], sort_keys=True)))
    print('  seconds per call: %s' % result['seconds_per_call_text'])
    sys.stdout.flush()
    return document


def main(argv=None):
    parser = argparse.ArgumentParser(description='Option B practice gates. Writes GATE.json once.')
    parser.add_argument('--package', '--package-dir', dest='package', required=True)
    parser.add_argument('--out', '--output-dir', dest='out', required=True)
    parser.add_argument('--deadline-unix', dest='deadline_unix', type=int, required=True)
    args = parser.parse_args(argv)
    gate_files(args.package, args.out, args.deadline_unix)
    return 0


if __name__ == '__main__':
    sys.exit(main())
