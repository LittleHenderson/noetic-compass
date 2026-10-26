"""Option B, Step 6. Pick the tasks by program, with a seed.

What this tool does, in plain words:
- Per passage it keeps at most two role-step questions. They must have different forms and
  different right things (the looser word test of tools/verdict.py). Different types are preferred.
  A second LAND question needs two agreed ^4 entries. The choice is drawn with a seed.
- It keeps one plain-fact question per passage.
- Length backstop: across the role-step tasks of a set, the right option may be the single longest
  option in at most 35 percent of tasks, and the single shortest in at most 35 percent. Seeded drops
  enforce both. Every drop is logged with its reason code.
- It writes the tasks and the key as text (which option is right). It writes no letters:
  letters are set last, by tools/ob_assemble.py, after the answer-leak screen.
- Practice set: it applies the reserve rule and says GO or gives the stop reason.
- Final set: it reads the launch floor and says GO or gives the stop reason.
- It writes the survival table: how many questions are left after each filter.

No person picks a task. No rule looks at an answer of model B. No outside service is called.

Usage:
  ob_select.py select --set practice [--practice-settings 8..12]
  ob_select.py select --set final
  ob_select.py fix-split        (after seal step 3A; writes select/split_fixed.json once)

Files (FILE_FORMATS.md section 7): select/selection_<set>.json, select/split_fixed.json.
Report file, read by no program: select/survival_<set>.json.

Exit codes (FILE_FORMATS.md section 0). The printed decision is the record; the code never disagrees
with it. 0 = GO: the next step of the run order may start. 1 = not finished:
STOP_RESERVE_TARGET_NOT_MET_MOVE_NEXT_RESERVE_SETTING; the next reserve setting is moved first.
3 = done, and the result says do not launch: STOP_DO_NOT_LAUNCH (select and fix-split).
2 = not started or stopped by a check (the reason is printed).

Dry fixture: --work pointing under optionb/dry/ (never for a real run).
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
import types
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
FILTERS = ['written for an open form', 'form check', 'anchor check', 'option check', 'key check', 'no-passage check', 'selection', 'length backstop']


class Stop(Exception):
    """A clean stop. The first argument is a code, the second a plain sentence."""


# ---------------------------------------------------------------- shared helpers

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


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

    def read_bytes(self, path):
        data = Path(path).read_bytes()
        self.inputs[rel(path)] = sha_bytes(data)
        return data

    def read_json(self, path, schema=None):
        if not Path(path).exists():
            raise Stop('FILE_MISSING', '%s does not exist. Run the program that writes it first.' % rel(path))
        doc = json.loads(self.read_bytes(path).decode('utf-8'))
        made_by = doc.get('made_by') if isinstance(doc, dict) else None
        if not self.dry and isinstance(made_by, dict) and DRY_TAG in str(made_by.get('program', '')):
            raise Stop('DRY_FILE_IN_REAL_RUN', '%s was made by a dry fixture run. It is refused in a real run.' % rel(path))
        if schema and doc.get('schema') != schema:
            raise Stop('WRONG_FILE', '%s does not carry the schema name %s.' % (rel(path), schema))
        return doc

    def write_json(self, path, schema, body):
        doc = {'schema': schema,
               'made_by': {'program': PROGRAM + (DRY_TAG if self.dry else ''), 'sha256': sha_bytes(HERE.read_bytes()), 'utc': utc_now()},
               'inputs': [{'path': p, 'sha256': s} for p, s in sorted(self.inputs.items())]}
        doc.update(body)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_name(path.name + '.partial')
        with open(partial, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
        replace_file(partial, path)


def replace_file(source, target):
    """Rename into place. On Windows a sync or scan tool can hold a file for a moment; wait and try again."""
    for _ in range(40):
        try:
            return os.replace(source, target)
        except PermissionError:
            time.sleep(0.25)
    return os.replace(source, target)


def check_seal(ctx, need, closed_by):
    """Stop unless the needed seal steps exist and every sealed file is unchanged."""
    if ctx.dry:
        return 'not checked: dry fixture'
    path = REAL_WORK / SEAL_NAME
    if not path.exists():
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
    for step in need:
        if step not in steps:
            raise Stop('SEAL_STEP_MISSING', 'Seal step %s must exist before this program runs.' % step)
    if closed_by in steps:
        raise Stop('SET_IS_SEALED', 'Seal step %s exists. These files are sealed and are not written again.' % closed_by)
    return 'checked: %d seal lines, all sealed files unchanged' % len(steps)


def load_frozen_verdict(ctx):
    """Run the hashed bytes of tools/verdict.py as a module. Its functions are used, never copied."""
    source = ctx.constants['sources']['verdict_program']
    data = ctx.read_bytes(ROOT / source['path'])
    if sha_bytes(data) != source['sha256']:
        raise Stop('SOURCE_HASH_MISMATCH', '%s does not have the hash pinned in PLAN_CONSTANTS.json.' % source['path'])
    module = types.ModuleType('ob_frozen_verdict')
    exec(compile(data, str(ROOT / source['path']), 'exec'), module.__dict__)
    return module


def in_practice(role, practice_count, start):
    if role == 'practice':
        return True
    found = re.fullmatch(r'reserve_(\d+)', role)
    return bool(found) and int(found.group(1)) <= practice_count - start


# ---------------------------------------------------------------- the selection rules

def length_flags(right, wrong):
    """(right is the single longest, right is the single shortest), counted in words over all written options."""
    mine, others = len(right.split()), [len(option.split()) for option in wrong]
    return all(mine > other for other in others), all(mine < other for other in others)


def choose(constants, frozen, passage, survivors):
    """The pair rule for one passage. Returns (picked questions, dropped rows)."""
    forms, rules = constants['forms'], constants['form_rules']
    place = {form: index for index, form in enumerate(constants['forms_in_order'])}
    survivors = sorted(survivors, key=lambda c: place[c['form']])

    def kind(c):
        return forms[c['form']]['type']

    def land_blocked(x, y):
        short = any(passage['agreed'].get(noetic, 0) < need for noetic, need in rules['land_second_question_needs_agreed_entries_of'].items())
        return kind(x) == 'LAND' and kind(y) == 'LAND' and short

    def same_thing(x, y):
        return frozen.lenient_span(x['right'], y['right'])

    pairs = [(x, y) for index, x in enumerate(survivors) for y in survivors[index + 1:]
             if x['form'] != y['form'] and not same_thing(x, y) and not land_blocked(x, y)]
    if rules['prefer_different_types'] and any(kind(x) != kind(y) for x, y in pairs):
        pairs = [(x, y) for x, y in pairs if kind(x) != kind(y)]
    rng = random.Random('%d|%s' % (constants['seeds']['selection'], passage['id']))
    if pairs and rules['max_role_step_tasks_per_passage'] >= 2:
        picked = list(rng.choice(pairs))
    elif survivors:
        picked = [rng.choice(survivors)]
    else:
        picked = []
    if len(picked) > passage['max_role_step_tasks']:
        raise Stop('SELECTION_ABOVE_PASSAGE_CEILING', 'Passage %s would carry %d role-step tasks; elig/eligibility.json allows %d.'
                   % (passage['id'], len(picked), passage['max_role_step_tasks']))
    dropped = []
    for c in survivors:
        if any(c is p for p in picked):
            continue
        reason = 'NOT_PICKED_BY_PAIR_RULE'
        if len(picked) == 1:
            reason = 'LAND_RULE' if land_blocked(c, picked[0]) else ('SAME_RIGHT_THING' if same_thing(c, picked[0]) else reason)
        dropped.append({'question_id': c['question_id'], 'reason': reason})
    return picked, dropped


def run_selection(constants, frozen, in_set, candidates, key_rows, anchors_matched):
    """Selection and length backstop for one set of passages. Pure: the same inputs give the same result."""
    forms = constants['forms']
    survives = {row['question_id'] for row in key_rows if row['survives']}
    by_passage = {}
    for c in candidates:
        if c['passage_id'] in in_set and c['question_id'] in survives:
            by_passage.setdefault(c['passage_id'], []).append(c)
    tasks, dropped = [], []
    for pid in sorted(by_passage):
        passage, live = in_set[pid], sorted(by_passage[pid], key=lambda c: c['question_id'])
        if passage['barred'] or not passage['eligible']:
            reason = 'PASSAGE_BARRED' if passage['barred'] else 'PASSAGE_NOT_ELIGIBLE'
            dropped.extend({'question_id': c['question_id'], 'reason': reason} for c in live)
            continue
        picked, out = choose(constants, frozen, passage, [c for c in live if c['family'] == 'role_step'])
        dropped.extend(out)
        for c in picked + [c for c in live if c['family'] == 'plain_fact'][:constants['form_rules']['plain_fact_tasks_per_passage']]:
            longest, shortest = length_flags(c['right'], c['wrong'])
            fact = c['family'] == 'plain_fact'
            tasks.append({'task_id': '%s.%s' % (pid, c['form']), 'passage_id': pid, 'question_id': c['question_id'], 'family': c['family'],
                          'type': 'FACT' if fact else forms[c['form']]['type'], 'form': c['form'], 'question': c['question'], 'right': c['right'],
                          'wrong': list(c['wrong']), 'anchors': list(c['anchors']),
                          'anchors_matched': [a for a in c['anchors'] if a in anchors_matched.get(c['question_id'], ())],
                          'right_is_single_longest': longest, 'right_is_single_shortest': shortest})
    role_before = sum(1 for t in tasks if t['family'] == 'role_step')

    # Length backstop. One seeded source per set. First the longest share is brought to the cap, then the shortest share.
    # A drop for the shortest share makes the set smaller, so the longest share can rise again.
    # The two steps are therefore repeated until both shares are at or under their cap.
    rule = constants['selection']['length_backstop']
    steps = (('right_is_single_longest', rule['single_longest_max_percent'], 'LENGTH_BACKSTOP_LONGEST'),
             ('right_is_single_shortest', rule['single_shortest_max_percent'], 'LENGTH_BACKSTOP_SHORTEST'))
    rng = random.Random(constants['seeds']['length_backstop'])

    def above(flag, cap):
        role = [t for t in tasks if t['family'] == 'role_step']
        flagged = sorted(t['task_id'] for t in role if t[flag])
        return flagged if 100 * len(flagged) > cap * len(role) else []

    while any(above(flag, cap) for flag, cap, _ in steps):
        for flag, cap, reason in steps:
            while above(flag, cap):
                gone = rng.choice(above(flag, cap))
                dropped.extend({'question_id': t['question_id'], 'reason': reason} for t in tasks if t['task_id'] == gone)
                tasks = [t for t in tasks if t['task_id'] != gone]
    role = [t for t in tasks if t['family'] == 'role_step']
    counts = {'role_step_tasks': len(role), 'plain_fact_tasks': len(tasks) - len(role),
              'passages_with_a_task': len({t['passage_id'] for t in tasks}),
              'passages_with_a_role_step_task': len({t['passage_id'] for t in role}),
              'single_longest': [sum(1 for t in role if t['right_is_single_longest']), len(role)],
              'single_shortest': [sum(1 for t in role if t['right_is_single_shortest']), len(role)]}
    return {'tasks': tasks, 'dropped': dropped, 'counts': counts, 'role_step_before_backstop': role_before}


def survival_rows(constants, in_set, form_rows, anchor_rows, option_rows, candidates, key_rows, result):
    """The survival table: one row per filter. Counted per passage and form; a spare stands in where the first question was dropped."""
    passed_form = {r['question_id'] for r in form_rows if r['passed']}
    passed_anchor = {r['question_id'] for r in anchor_rows if r['passed']}
    passed_option = {r['question_id'] for r in option_rows if r['passed']}

    def through(qid, fact, stage):
        if qid is None or qid not in passed_form:
            return False
        return fact or stage == 2 or (qid in passed_anchor and (stage == 3 or qid in passed_option))

    slots = {}
    for row in form_rows:
        pid, pass_name, tag = row['question_id'].split('.')
        if pid in in_set and (row['family'] == 'plain_fact' or tag in constants['forms']):
            slots.setdefault((pid, tag, row['family'] == 'plain_fact'), {})[pass_name] = row['question_id']
    role = [s for (pid, tag, fact), s in slots.items() if not fact and 'p1' in s and in_set[pid]['eligible']
            and not in_set[pid]['barred'] and tag in in_set[pid]['open_forms']]
    facts = [s for (pid, tag, fact), s in slots.items() if fact and 'p1' in s]

    def alive(slot, fact, stage):
        return through(slot.get('p1'), fact, stage) or through(slot.get('p2'), fact, stage)

    rows = [{'filter': FILTERS[0], 'role_step': len(role), 'plain_fact': len(facts)}]
    for name, stage in zip(FILTERS[1:4], (2, 3, 4)):
        rows.append({'filter': name, 'role_step': sum(alive(s, False, stage) for s in role), 'plain_fact': sum(alive(s, True, 2) for s in facts)})
    mine = [c for c in candidates if c['passage_id'] in in_set]
    for family, key in (('role_step', 'role_step'), ('plain_fact', 'plain_fact')):
        if rows[3][key] != sum(1 for c in mine if c['family'] == family):
            raise Stop('CHECK_FILES_DISAGREE', 'The check files and checks/candidates do not give the same number of %s candidates. Run ob_check_questions.py again.' % family)
    family_of = {c['question_id']: c['family'] for c in mine}
    keyed = [r for r in key_rows if r['question_id'] in family_of]
    for name, test in ((FILTERS[4], lambda r: r['key_check_passed']), (FILTERS[5], lambda r: r['survives'])):
        rows.append({'filter': name, 'role_step': sum(1 for r in keyed if r['family'] == 'role_step' and test(r)),
                     'plain_fact': sum(1 for r in keyed if r['family'] == 'plain_fact' and test(r))})
    rows.append({'filter': FILTERS[6], 'role_step': result['role_step_before_backstop'], 'plain_fact': result['counts']['plain_fact_tasks']})
    rows.append({'filter': FILTERS[7], 'role_step': result['counts']['role_step_tasks'], 'plain_fact': result['counts']['plain_fact_tasks']})
    return rows


# ---------------------------------------------------------------- the run

class Run:
    def __init__(self, ctx, set_name):
        self.ctx, self.C, self.set_name = ctx, ctx.constants, set_name
        self.frozen = load_frozen_verdict(ctx)
        eligibility = ctx.read_json(ctx.work / 'elig' / 'eligibility.json', 'casalescence/optionb/eligibility/v1')
        if not ctx.dry and eligibility.get('counts_match_plan') is not True:
            raise Stop('ELIGIBILITY_NOT_CONFIRMED', 'elig/eligibility.json does not say counts_match_plan: true.')
        self.eligibility = eligibility
        self.asked = {row['id']: row for row in eligibility['passages'] if row['writer_asks']}
        self.start, self.most = self.C['split']['practice_setting_count_start'], self.C['split']['practice_setting_count_max']
        self.floor = self.C['launch_floor']

    def load_set(self):
        ctx, name = self.ctx, self.set_name
        self.candidates = ctx.read_json(ctx.work / 'checks' / ('candidates_%s.json' % name), 'casalescence/optionb/candidates/v1')['candidates']
        self.key_rows = ctx.read_json(ctx.work / 'solve' / ('key_check_%s.json' % name), 'casalescence/optionb/key_check/v1')['rows']
        self.form_rows = ctx.read_json(ctx.work / 'checks' / ('form_check_%s.json' % name), 'casalescence/optionb/form_check/v1')['rows']
        self.anchor_rows = ctx.read_json(ctx.work / 'checks' / ('anchor_check_%s.json' % name), 'casalescence/optionb/anchor_check/v1')['rows']
        self.option_rows = ctx.read_json(ctx.work / 'checks' / ('option_check_%s.json' % name), 'casalescence/optionb/option_check/v1')['rows']
        if sorted(c['question_id'] for c in self.candidates) != sorted(r['question_id'] for r in self.key_rows):
            raise Stop('KEY_CHECK_NOT_CURRENT', 'solve/key_check_%s.json does not cover exactly the candidates. Run the decide step of ob_solve_blind.py again.' % name)
        self.anchors_matched = {r['question_id']: {m['anchor'] for m in r['matched']} for r in self.anchor_rows if r['passed']}
        # which passages the writer was asked about, in both passes (ids only; no question text is read here)
        self.written = []
        for pass_name in ctx.constants['outside_services']['gemini_question_writer']['passes']:
            raw = ctx.read_json(ctx.work / 'questions' / ('raw_questions_%s_%s.json' % (name, pass_name)), 'casalescence/optionb/raw_questions/v1')
            self.written.append({row['passage_id'] for row in raw['passages']})

    def must_cover(self, in_set, practice_count):
        """Stop unless both writer passes cover exactly the passages of this set."""
        for asked in self.written:
            if asked != set(in_set):
                raise Stop('WRITER_DOES_NOT_COVER_THIS_SET', 'The written questions cover %d passages; this set has %d with %d practice settings. '
                           'Finish the writer and the checks first, or give the right --practice-settings.' % (len(asked), len(in_set), practice_count))

    def passages(self, practice_count, practice):
        return {pid: row for pid, row in self.asked.items() if in_practice(row['setting_role'], practice_count, self.start) == practice}

    def select(self, in_set):
        return run_selection(self.C, self.frozen, in_set, self.candidates, self.key_rows, self.anchors_matched)

    def practice_blocks(self, counts, practice_count):
        """The floor block and the reserve block of select/selection_practice.json (FILE_FORMATS.md section 7.1).

        The launch floors (36 and 20) decide "launch or not". The reserve targets (45 and 25) only decide
        how many reserve settings move. Both look at role-step tasks and at plain-fact tasks.
        """
        split, floor = self.C['split'], self.floor
        role, fact = counts['role_step_tasks'], counts['plain_fact_tasks']
        role_target, fact_target = split['reserve_target_practice_role_step_tasks'], split['reserve_target_practice_plain_fact_tasks']
        floor_block = {'practice_role_step_min': floor['practice_role_step_tasks_min'], 'practice_plain_fact_min': floor['practice_plain_fact_tasks_min'],
                       'met': role >= floor['practice_role_step_tasks_min'] and fact >= floor['practice_plain_fact_tasks_min']}
        target_met, left = role >= role_target and fact >= fact_target, self.most - practice_count
        reserve = {'role_step_target': role_target, 'plain_fact_target': fact_target, 'target_met': target_met,
                   'settings_left': left, 'finished': target_met or left == 0}
        return floor_block, reserve

    def tier(self, counts):
        rule = self.C['tiers']
        if counts['role_step_tasks'] < rule['no_launch_below_final_role_step_tasks']:
            return 'NO_LAUNCH'
        full = rule['as_it_stands']
        if (counts['role_step_tasks'] >= full['final_role_step_tasks_min']
                and counts['passages_with_a_role_step_task'] >= full['final_passages_with_a_role_step_task_min']):
            return 'AS_IT_STANDS'
        return 'EXPLORATORY'


def step_select(ctx, args):
    set_name = args.set_name
    if set_name == 'practice':
        seal = check_seal(ctx, ['1_PLAN_AND_SOURCES', '2_ROLE_NOTES'], '3A_PRACTICE_QUESTIONS_AND_KEYS')
    else:
        seal = check_seal(ctx, ['1_PLAN_AND_SOURCES', '2_ROLE_NOTES', '3A_PRACTICE_QUESTIONS_AND_KEYS', '3B_PRACTICE_SET_FIXED'],
                          '3C_FINAL_QUESTIONS_AND_KEYS')
    run = Run(ctx, set_name)
    C, floor = run.C, run.floor
    if set_name == 'practice':
        practice_count = run.start if args.practice_settings is None else args.practice_settings
        if not run.start <= practice_count <= run.most:
            raise Stop('BAD_ARGUMENT', '--practice-settings must be %d to %d.' % (run.start, run.most))
    else:
        split = ctx.read_json(ctx.work / 'select' / 'split_fixed.json', 'casalescence/optionb/split_fixed/v1')
        practice_count = split['practice_setting_count']
    run.load_set()
    in_set = run.passages(practice_count, set_name == 'practice')
    run.must_cover(in_set, practice_count)
    outside = sorted({c['passage_id'] for c in run.candidates} - set(in_set))
    if outside:
        raise Stop('CANDIDATES_NOT_OF_THIS_SET', 'checks/candidates_%s.json holds passages that are not in this set with %d practice settings (first: %s).'
                   % (set_name, practice_count, outside[0]))
    result = run.select(in_set)
    counts = result['counts']
    rows = survival_rows(C, in_set, run.form_rows, run.anchor_rows, run.option_rows, run.candidates, run.key_rows, result)

    body = {'set': set_name, 'practice_setting_count': practice_count, 'tasks': result['tasks'], 'dropped': result['dropped'], 'counts': counts}
    reasons, extra = [], {}
    if set_name == 'practice':
        # FILE_FORMATS.md section 7.1. The reserve rule looks at both task families and aims at the two
        # reserve targets, which are above the launch floors: Step 7 comes later and can only remove passages.
        body['floor'], body['reserve'] = run.practice_blocks(counts, practice_count)
        reserve, met = body['reserve'], body['floor']['met']
        said = ('%d practice role-step tasks and %d practice plain-fact tasks survive with %d practice settings'
                % (counts['role_step_tasks'], counts['plain_fact_tasks'], practice_count))
        if not reserve['finished']:
            name = run.eligibility['reserve_settings_in_order'][practice_count - run.start]
            decision = 'STOP_RESERVE_TARGET_NOT_MET_MOVE_NEXT_RESERVE_SETTING'
            reasons.append('%s; the reserve targets are %d and %d.' % (said, reserve['role_step_target'], reserve['plain_fact_target']))
            nxt = ('The reserve rule moves the next reserve setting to practice: "%s". Write its questions (both passes) with '
                   '--practice-settings %d, then run the check, the solvers and this step again with --practice-settings %d. '
                   'Seal step 3A is refused until the reserve rule is finished.'
                   % (name, practice_count + 1, practice_count + 1))
        elif not met:
            decision = 'STOP_DO_NOT_LAUNCH'
            reasons.append('%s, and no reserve setting is left; the launch floors are %d and %d.'
                           % (said, floor['practice_role_step_tasks_min'], floor['practice_plain_fact_tasks_min']))
            nxt = ('Do not launch. Report the survival numbers to the owner. Seal step 3A may still be written, so that the practice questions are kept '
                   'as evidence; seal step 3B will be refused. No brief and no filter is changed without a new reviewed plan version.')
        else:
            decision = 'GO'
            if not reserve['target_met']:
                extra['notes'] = ['%s; a reserve target (%d and %d) is missed with all %d settings. This is not a stop: only the launch floor decides.'
                                  % (said, reserve['role_step_target'], reserve['plain_fact_target'], run.most)]
            nxt = ('Seal step 3A. Then run: ob_select.py fix-split. Then seal step 3B. Then Step 7 runs on the practice set alone (ordinary notes, '
                   'support check, the answer-leak screen with --report-only). Only then are final questions written.')
    else:
        practice = ctx.read_json(ctx.work / 'select' / 'selection_practice.json', 'casalescence/optionb/selection/v1')
        if practice['practice_setting_count'] != practice_count:
            raise Stop('SELECTION_NOT_CURRENT', 'select/selection_practice.json was made with another number of practice settings than select/split_fixed.json.')
        numbers = {'final_role_step_tasks': counts['role_step_tasks'], 'final_plain_fact_tasks': counts['plain_fact_tasks'],
                   'practice_role_step_tasks': practice['counts']['role_step_tasks'], 'practice_plain_fact_tasks': practice['counts']['plain_fact_tasks']}
        for name, value in numbers.items():
            if value < floor[name + '_min']:
                reasons.append('%s is %d; the launch floor is %d.' % (name, value, floor[name + '_min']))
        extra = {'launch_floor_numbers': numbers, 'launch_floor': dict(floor), 'tier_if_nothing_more_is_removed': run.tier(counts)}
        decision = 'STOP_DO_NOT_LAUNCH' if reasons else 'GO'
        nxt = ('Do not launch. Report the survival numbers to the owner.' if reasons else
               'Seal step 3C. Then the ordinary notes are written. The launch floor is read again by tools/ob_assemble.py after the later filters.')

    ctx.write_json(ctx.work / 'select' / ('selection_%s.json' % set_name), 'casalescence/optionb/selection/v1', body)
    report = {'set': set_name, 'practice_setting_count': practice_count, 'rows': rows, 'counts': counts,
              'dropped_by_reason': {reason: sum(1 for d in result['dropped'] if d['reason'] == reason)
                                    for reason in sorted({d['reason'] for d in result['dropped']})},
              'decision': decision, 'stop_reasons': reasons, 'next': nxt,
              'note': 'A report for people. No program reads this file. GO means: go on to the next build step. It is not a result about roles.'}
    report.update(extra)
    ctx.write_json(ctx.work / 'select' / ('survival_%s.json' % set_name), 'casalescence/optionb/survival/v1', report)
    print(json.dumps(dict({'program': PROGRAM, 'dry_fixture': ctx.dry, 'step': 'select', 'seal': seal}, **report), ensure_ascii=False, indent=1))
    return decision


def step_fix_split(ctx, args):
    seal = check_seal(ctx, ['1_PLAN_AND_SOURCES', '2_ROLE_NOTES', '3A_PRACTICE_QUESTIONS_AND_KEYS'], '3B_PRACTICE_SET_FIXED')
    path = ctx.work / 'select' / 'split_fixed.json'
    if path.exists():
        raise Stop('SPLIT_ALREADY_FIXED', 'select/split_fixed.json exists. It is written once.')
    run = Run(ctx, 'practice')
    run.load_set()
    selection = ctx.read_json(ctx.work / 'select' / 'selection_practice.json', 'casalescence/optionb/selection/v1')
    count = selection['practice_setting_count']
    run.must_cover(run.passages(count, True), count)
    # the history is worked out again from the same files: one row per number of practice settings tried
    history, blocks = [], None
    for n in range(run.start, count + 1):
        counts = run.select(run.passages(n, True))['counts']
        blocks = run.practice_blocks(counts, n)
        history.append({'practice_setting_count': n, 'practice_role_step_tasks': counts['role_step_tasks'],
                        'practice_plain_fact_tasks': counts['plain_fact_tasks'], 'target_met': blocks[1]['target_met']})
    if (history[-1]['practice_role_step_tasks'] != selection['counts']['role_step_tasks']
            or history[-1]['practice_plain_fact_tasks'] != selection['counts']['plain_fact_tasks']
            or selection.get('floor') != blocks[0] or selection.get('reserve') != blocks[1]):
        raise Stop('SELECTION_NOT_CURRENT', 'select/selection_practice.json does not match the candidates and the key check. Run the select step again.')
    # FILE_FORMATS.md section 7.2: no setting is moved once both reserve targets are met; the file is not written while the reserve rule is unfinished.
    if any(row['target_met'] for row in history[:-1]):
        raise Stop('RESERVE_RULE_OVERUSED', 'Both reserve targets were already met with fewer practice settings. The reserve rule moves a setting only while a target is missed.')
    reserve_target_met, floor_met = blocks[1]['target_met'], blocks[0]['met']
    if not blocks[1]['finished']:
        raise Stop('RESERVE_RULE_NOT_FINISHED', 'A reserve target is missed and reserve settings are left. Move the next reserve setting first.')
    reserve = run.eligibility['reserve_settings_in_order']
    practice_settings = list(run.eligibility['practice_settings']) + list(reserve[:count - run.start])
    final_settings = sorted({row['setting'] for row in run.eligibility['passages']} - set(practice_settings))
    final_ids = sorted(pid for pid, row in run.asked.items() if row['setting'] in final_settings)
    if set(final_ids) != set(run.passages(count, False)):
        raise Stop('SETTING_ROLES_DISAGREE', 'The setting roles in elig/eligibility.json do not match its practice and reserve setting lists.')
    ctx.write_json(path, 'casalescence/optionb/split_fixed/v1', {
        'practice_setting_count': count, 'practice_settings': practice_settings, 'final_settings': final_settings,
        'history': history, 'reserve_target_met': reserve_target_met, 'floor_met': floor_met, 'final_writer_passage_ids': final_ids})
    print(json.dumps({
        'program': PROGRAM, 'dry_fixture': ctx.dry, 'step': 'fix-split', 'status': 'SPLIT_FIXED', 'seal': seal, 'practice_setting_count': count,
        'history': history, 'reserve_target_met': reserve_target_met, 'floor_met': floor_met, 'launch_floor': blocks[0],
        'final_settings': len(final_settings), 'final_writer_passages': len(final_ids),
        'decision': 'GO' if floor_met else 'STOP_DO_NOT_LAUNCH',
        'next': ('Seal step 3B. Then Step 7 on the practice set alone: the practice ordinary notes, their support check, and the answer-leak screen '
                 'with --report-only. Only then are the final questions written.') if floor_met else
                'Do not launch. A practice launch floor is missed with the reserve rule finished. Seal step 3B will be refused. Report the survival numbers to the owner.'},
        ensure_ascii=False, indent=1))
    return 'GO' if floor_met else 'STOP_DO_NOT_LAUNCH'


# FILE_FORMATS.md section 0: the exit code of each decision. Only code 0 lets the next step of the run order start.
EXIT_CODE_OF_DECISION = {'GO': 0, 'STOP_RESERVE_TARGET_NOT_MET_MOVE_NEXT_RESERVE_SETTING': 1, 'STOP_DO_NOT_LAUNCH': 3}


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):      # FILE_FORMATS.md section 0: a laptop tool prints in UTF-8
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description='Option B Step 6: selection by program.')
    steps = parser.add_subparsers(dest='step', required=True)
    one = steps.add_parser('select')
    one.add_argument('--set', dest='set_name', required=True, choices=['practice', 'final'])
    one.add_argument('--practice-settings', type=int, default=None, help='practice set only: 8 to 12 (default 8)')
    one.add_argument('--work', default=None, help='dry fixture folder under optionb/dry/ (never for a real run)')
    two = steps.add_parser('fix-split')
    two.add_argument('--work', default=None, help='dry fixture folder under optionb/dry/ (never for a real run)')
    args = parser.parse_args(argv)
    ctx = Ctx(args.work)
    decision = (step_select if args.step == 'select' else step_fix_split)(ctx, args)
    return EXIT_CODE_OF_DECISION[decision]


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Stop as stop:
        print(json.dumps({'program': PROGRAM, 'status': 'STOP', 'code': stop.args[0], 'reason': stop.args[1]}, ensure_ascii=False, indent=1))
        sys.exit(2)
