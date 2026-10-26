"""Option B, Steps 2 and 3. Check the written questions by program rules.

What this tool does, in plain words:
- Step 2, form check. It drops a question that breaks a format rule or holds a forbidden word.
- Step 3a, anchor check. It keeps a role-step question only if the passage is eligible, the form is
  open, and one of its anchors matches an entry both label teams agree on.
- Step 3b, option check. It sets a role-step question aside when one of its options matches an entry
  that only one team gave.
- Then it writes one candidate per passage and form, and one plain-fact candidate per passage.

Step 3 is the only place where labels touch questions. The writer never learns what was kept.
The candidates file holds no label information. Every drop is logged with its reason code.
This tool calls no outside service and reads no key.

Usage:
  ob_check_questions.py --set practice [--practice-settings 8..12]
  ob_check_questions.py --set final

Files (FILE_FORMATS.md section 5):
  checks/form_check_<set>.json, checks/anchor_check_<set>.json,
  checks/option_check_<set>.json, checks/candidates_<set>.json

It prints how many questions survive each filter.

Exit codes (FILE_FORMATS.md section 0): 0 = checked. 2 = not started or stopped by a check (the
reason is printed).

Dry fixture: --work pointing under optionb/dry/ (never for a real run).
"""
import argparse
import ast
import datetime
import hashlib
import json
import os
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
DRY_MODEL = 'DRY-FIXTURE-NO-MODEL'
OVERRIDES_NAME = 'DRY_CONSTANT_OVERRIDES.json'
SEAL_NAME = 'SEAL_OPTIONB.jsonl'
CURLY = str.maketrans({'‘': "'", '’': "'", '“': '"', '”': '"'})
FORM_REASONS = ['FORM_NAME_UNKNOWN', 'EMPTY_TEXT', 'OPTION_COUNT', 'OPTIONS_NOT_DIFFERENT', 'OPTION_TOO_LONG', 'QUESTION_TOO_LONG',
                'OPTION_LENGTH_SPREAD', 'OPTION_INSIDE_ANOTHER', 'ANCHOR_COUNT', 'ANCHOR_NOT_IN_PASSAGE', 'ANCHOR_TOO_LONG',
                'FORBIDDEN_LIST_A', 'FORBIDDEN_SIGN', 'FORBIDDEN_LIST_B', 'FORBIDDEN_LIST_C', 'FORBIDDEN_PHRASE']


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

    def read_json(self, path):
        doc = json.loads(self.read_bytes(path).decode('utf-8'))
        made_by = doc.get('made_by') if isinstance(doc, dict) else None
        if not self.dry and isinstance(made_by, dict) and DRY_TAG in str(made_by.get('program', '')):
            raise Stop('DRY_FILE_IN_REAL_RUN', '%s was made by a dry fixture run. It is refused in a real run.' % rel(path))
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


def check_list_a(ctx):
    """List A must equal line 19 of the passage writer's tool. The tool is read as text, never run."""
    source = ctx.constants['sources']['passage_writer_tool']
    data = ctx.read_bytes(ROOT / source['path'])
    if sha_bytes(data) != source['sha256']:
        raise Stop('SOURCE_HASH_MISMATCH', '%s does not have the hash pinned in PLAN_CONSTANTS.json.' % source['path'])
    lines = data.decode('utf-8').split('\n')
    found = re.fullmatch(r'FORBIDDEN = (\[.*\])', lines[18].strip()) if len(lines) > 18 else None
    if not found or ast.literal_eval(found.group(1)) != ctx.constants['forbidden_words']['list_a']['words']:
        raise Stop('LIST_A_DIFFERS', 'List A in PLAN_CONSTANTS.json is not the list on line 19 of %s.' % source['path'])


def load_frozen_verdict(ctx):
    """Run the hashed bytes of tools/verdict.py as a module. Its functions are used, never copied."""
    source = ctx.constants['sources']['verdict_program']
    data = ctx.read_bytes(ROOT / source['path'])
    if sha_bytes(data) != source['sha256']:
        raise Stop('SOURCE_HASH_MISMATCH', '%s does not have the hash pinned in PLAN_CONSTANTS.json.' % source['path'])
    module = types.ModuleType('ob_frozen_verdict')
    exec(compile(data, str(ROOT / source['path']), 'exec'), module.__dict__)
    return module


# ---------------------------------------------------------------- Step 2: the form check

def plain(text):
    """Curly quote marks become straight ones. Runs of white space become one space."""
    return ' '.join(text.translate(CURLY).split())


def holds_run(inner, outer):
    """True when the word sequence inner is an unbroken part of the word sequence outer."""
    size = len(inner)
    return any(outer[i:i + size] == inner for i in range(len(outer) - size + 1))


def form_check(question, family, passage_text, constants):
    """Return the list of reason codes. An empty list means the question passed."""
    rules, barred = constants['question_rules'], constants['forbidden_words']
    options = [question['right']] + list(question['wrong'])
    anchors = list(question.get('anchors', [])) if family == 'role_step' else []
    reasons = []
    if family == 'role_step' and question['form'] not in constants['forms']:
        reasons.append('FORM_NAME_UNKNOWN')
    if not question['question'].strip() or any(not o.strip() for o in options) or any(not a.strip() for a in anchors):
        reasons.append('EMPTY_TEXT')
    if len(options) != constants['task_families'][family]['options_written']:
        reasons.append('OPTION_COUNT')
    sequences = [re.findall(rules['word_sequence_regex'], option.lower()) for option in options]
    if len({tuple(sequence) for sequence in sequences}) != len(sequences):
        reasons.append('OPTIONS_NOT_DIFFERENT')
    lengths = [len(option.split()) for option in options]
    if any(length > rules['option_max_words'] for length in lengths):
        reasons.append('OPTION_TOO_LONG')
    if len(question['question'].split()) > rules['question_max_words']:
        reasons.append('QUESTION_TOO_LONG')
    if max(lengths) - min(lengths) > rules['option_length_spread_max_words']:
        reasons.append('OPTION_LENGTH_SPREAD')
    if any(i != j and sequences[i] != sequences[j] and holds_run(sequences[i], sequences[j])
           for i in range(len(sequences)) for j in range(len(sequences))):
        reasons.append('OPTION_INSIDE_ANOTHER')
    if family == 'role_step':
        if not rules['anchors_min'] <= len(anchors) <= rules['anchors_max']:
            reasons.append('ANCHOR_COUNT')
        body = plain(passage_text)
        if any(plain(anchor) not in body for anchor in anchors if anchor.strip()):
            reasons.append('ANCHOR_NOT_IN_PASSAGE')
        if any(len(anchor.split()) > rules['anchor_max_words'] for anchor in anchors):
            reasons.append('ANCHOR_TOO_LONG')
    everywhere = [question['question']] + options
    for word in barred['list_a']['words']:
        if any(re.search(r'\b' + re.escape(word) + r'\w*\b', text, flags=re.I) for text in everywhere):
            reasons.append('FORBIDDEN_LIST_A:' + word)
    if any(barred['sign']['text'] in text for text in everywhere):
        reasons.append('FORBIDDEN_SIGN')
    for word in barred['list_b']['words']:
        if any(re.search(r'\b' + re.escape(word) + r'\b', text, flags=re.I) for text in everywhere):
            reasons.append('FORBIDDEN_LIST_B:' + word)
    for phrase in barred['list_c']['words']:
        if re.search(r'\b' + r'\s+'.join(re.escape(part) for part in phrase.split()) + r'\b', question['question'], flags=re.I):
            reasons.append('FORBIDDEN_LIST_C:' + phrase)
    if any(phrase.lower() in ' '.join(text.lower().split()) for phrase in barred['never_allowed_phrases']['words'] for text in everywhere):
        reasons.append('FORBIDDEN_PHRASE')
    return reasons


# ---------------------------------------------------------------- Step 3: the two label checks

def anchor_check(question, passage, constants, frozen):
    """Return (reason or None, matched). The looser word test of tools/verdict.py decides a match."""
    if passage['barred']:
        return 'PASSAGE_BARRED', []
    if not passage['eligible']:
        return 'PASSAGE_NOT_ELIGIBLE', []
    if question['form'] not in passage['open_forms']:
        return 'FORM_NOT_OPEN', []
    needed = constants['forms'][question['form']]['anchor_noetics']
    printed = constants['eligibility']['fields_printed']
    matched = []
    for anchor in question['anchors']:
        for index, pair in enumerate(passage['entries']['agreed']):
            if pair['noetic'] not in needed:
                continue
            fields = [('words_a', pair['a'].get('words')), ('words_b', pair['b'].get('words'))]
            if 'relative_to' in printed[pair['noetic']]:
                fields += [('relative_a', pair['a'].get('relative_to')), ('relative_b', pair['b'].get('relative_to'))]
            for name, text in fields:
                if text and frozen.lenient_span(anchor, text):
                    matched.append({'anchor': anchor, 'noetic': pair['noetic'], 'agreed_index': index, 'field': name})
    return (None, matched) if matched else ('NO_ANCHOR_MATCHES_AGREED_ENTRY', [])


def option_check(question, passage, constants, frozen):
    """Return the hits: options that match an entry of the needed Noetics that only one team gave."""
    needed = constants['forms'][question['form']]['option_check_noetics']
    also_related = constants['form_rules']['option_check_also_compares_related_thing_for']
    hits = []
    for option_index, option in enumerate([question['right']] + list(question['wrong'])):
        for team in ('a', 'b'):
            for entry in passage['entries']['only_' + team]:
                if entry['noetic'] not in needed:
                    continue
                fields = [('words', entry.get('words'))]
                if entry['noetic'] in also_related:
                    fields.append(('relative_to', entry.get('relative_to')))
                for name, text in fields:
                    if text and frozen.lenient_span(option, text):
                        hits.append({'option_index': option_index, 'option': option, 'noetic': entry['noetic'], 'team': team,
                                     'entry_index': entry['index'], 'field': name})
    return hits


# ---------------------------------------------------------------- the run

def in_practice(role, practice_count, start):
    if role == 'practice':
        return True
    found = re.fullmatch(r'reserve_(\d+)', role)
    return bool(found) and int(found.group(1)) <= practice_count - start


def count_reasons(rows, key):
    """Questions dropped per reason code. A question counts once per code, also when two words of one list hit."""
    counts = {}
    for row in rows:
        reasons = [row[key]] if isinstance(row[key], str) else (row[key] or [])
        for name in sorted({reason.split(':', 1)[0] for reason in reasons}):
            counts[name] = counts.get(name, 0) + 1
    return counts


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):      # FILE_FORMATS.md section 0: a laptop tool prints in UTF-8
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description='Option B Steps 2 and 3: form check, anchor check, option check, candidates.')
    parser.add_argument('--set', dest='set_name', required=True, choices=['practice', 'final'])
    parser.add_argument('--practice-settings', type=int, default=None, help='practice set only: 8 to 12 (default 8)')
    parser.add_argument('--work', default=None, help='dry fixture folder under optionb/dry/ (never for a real run)')
    args = parser.parse_args(argv)

    ctx = Ctx(args.work)
    C = ctx.constants
    set_name = args.set_name
    start, most = C['split']['practice_setting_count_start'], C['split']['practice_setting_count_max']
    if set_name == 'practice':
        seal = check_seal(ctx, ['1_PLAN_AND_SOURCES', '2_ROLE_NOTES'], '3A_PRACTICE_QUESTIONS_AND_KEYS')
    else:
        seal = check_seal(ctx, ['1_PLAN_AND_SOURCES', '2_ROLE_NOTES', '3A_PRACTICE_QUESTIONS_AND_KEYS', '3B_PRACTICE_SET_FIXED'],
                          '3C_FINAL_QUESTIONS_AND_KEYS')
    check_list_a(ctx)
    frozen = load_frozen_verdict(ctx)

    eligibility = ctx.read_json(ctx.work / 'elig' / 'eligibility.json')
    if eligibility.get('schema') != 'casalescence/optionb/eligibility/v1':
        raise Stop('WRONG_FILE', 'elig/eligibility.json does not carry the eligibility schema name.')
    if not ctx.dry and eligibility.get('counts_match_plan') is not True:
        raise Stop('ELIGIBILITY_NOT_CONFIRMED', 'elig/eligibility.json does not say counts_match_plan: true.')
    passages = {row['id']: row for row in eligibility['passages']}

    if set_name == 'practice':
        practice_count = start if args.practice_settings is None else args.practice_settings
        if not start <= practice_count <= most:
            raise Stop('BAD_ARGUMENT', '--practice-settings must be %d to %d.' % (start, most))
        expected = {pid for pid, row in passages.items() if row['writer_asks'] and in_practice(row['setting_role'], practice_count, start)}
    else:
        split_path = ctx.work / 'select' / 'split_fixed.json'
        if not split_path.exists():
            raise Stop('PRACTICE_SET_NOT_FIXED', 'select/split_fixed.json does not exist. The final set is not handled before the practice set is fixed.')
        split = ctx.read_json(split_path)
        practice_count = split['practice_setting_count']
        expected = set(split['final_writer_passage_ids'])
        if any(pid not in passages or in_practice(passages[pid]['setting_role'], practice_count, start) for pid in expected):
            raise Stop('SPLIT_DOES_NOT_MATCH', 'select/split_fixed.json lists a final passage that elig/eligibility.json puts in the practice set.')

    # read both passes; both must be complete and written by the one model of the set
    model = DRY_MODEL if ctx.dry else C['outside_services']['gemini_question_writer']['model_by_set'][set_name]
    questions = []
    for pass_name in C['outside_services']['gemini_question_writer']['passes']:
        path = ctx.work / 'questions' / ('raw_questions_%s_%s.json' % (set_name, pass_name))
        if not path.exists():
            raise Stop('WRITER_NOT_COMPLETE', 'questions/%s does not exist. Both passes must be written before the check.' % path.name)
        raw = ctx.read_json(path)
        if (raw.get('schema'), raw.get('set'), raw.get('pass')) != ('casalescence/optionb/raw_questions/v1', set_name, pass_name):
            raise Stop('WRONG_FILE', 'questions/%s is not the raw question file of this set and pass.' % path.name)
        if raw.get('model') != model:
            raise Stop('ONE_MODEL_PER_SET', 'questions/%s names model %s. This set is written by %s only.' % (path.name, raw.get('model'), model))
        asked = {row['passage_id'] for row in raw['passages']}
        if asked != expected:
            raise Stop('WRITER_NOT_COMPLETE', 'questions/%s covers %d passages; this set has %d (%d not asked yet, %d not of this set). '
                       'Finish the writer first, or give the right --practice-settings.'
                       % (path.name, len(asked), len(expected), len(expected - asked), len(asked - expected)))
        for row in raw['passages']:
            for item in row['what_follows']:
                questions.append(dict(item, passage_id=row['passage_id'], pass_name=pass_name, family='role_step'))
            if row['plain_fact']:
                questions.append(dict(row['plain_fact'], passage_id=row['passage_id'], pass_name=pass_name, family='plain_fact', form='FACT', anchors=[]))
    questions.sort(key=lambda q: q['question_id'])

    # Step 2
    form_rows = []
    for q in questions:
        q['reasons'] = form_check(q, q['family'], passages[q['passage_id']]['text'], C)
        q['ok2'] = not q['reasons']
        form_rows.append({'question_id': q['question_id'], 'family': q['family'], 'passed': q['ok2'], 'reasons': q['reasons']})
    # Step 3a
    anchor_rows = []
    for q in questions:
        q['ok3a'] = q['ok3b'] = False
        if q['family'] == 'role_step' and q['ok2']:
            reason, matched = anchor_check(q, passages[q['passage_id']], C, frozen)
            q['ok3a'] = reason is None
            anchor_rows.append({'question_id': q['question_id'], 'passed': q['ok3a'], 'reason': reason, 'matched': matched})
    # Step 3b
    option_rows = []
    for q in questions:
        if q['ok3a']:
            hits = option_check(q, passages[q['passage_id']], C, frozen)
            q['ok3b'] = not hits
            option_rows.append({'question_id': q['question_id'], 'passed': q['ok3b'], 'hits': hits})

    # candidates: the p1 question if it passed; else the p2 spare, only where a p1 question existed and was dropped
    def through(q, stage):
        if q is None:
            return False
        return q['ok2'] if q['family'] == 'plain_fact' or stage == 2 else (q['ok3a'] if stage == 3 else q['ok3b'])

    order = {form: i for i, form in enumerate(list(C['forms_in_order']) + ['FACT'])}
    slots = {}
    for q in questions:
        if q['family'] == 'plain_fact' or q['form'] in C['forms']:
            slots.setdefault((q['passage_id'], q['form']), {})[q['pass_name']] = q
    candidates, spares = [], 0
    for (pid, form) in sorted(slots, key=lambda key: (key[0], order[key[1]])):
        first, spare = slots[(pid, form)].get('p1'), slots[(pid, form)].get('p2')
        if first is None:
            continue
        chosen = first if through(first, 4) else (spare if through(spare, 4) else None)
        if chosen is None:
            continue
        spares += chosen is spare
        candidates.append({'question_id': chosen['question_id'], 'passage_id': pid, 'family': chosen['family'], 'form': form,
                           'pass': chosen['pass_name'], 'passage': passages[pid]['text'], 'question': chosen['question'],
                           'right': chosen['right'], 'wrong': list(chosen['wrong']), 'anchors': list(chosen['anchors'])})

    cdir = ctx.work / 'checks'
    ctx.write_json(cdir / ('form_check_%s.json' % set_name), 'casalescence/optionb/form_check/v1', {
        'set': set_name, 'rows': form_rows,
        'counts': {'checked': len(form_rows), 'passed': sum(r['passed'] for r in form_rows), 'dropped_by_reason': count_reasons(form_rows, 'reasons')}})
    ctx.write_json(cdir / ('anchor_check_%s.json' % set_name), 'casalescence/optionb/anchor_check/v1', {
        'set': set_name, 'rows': anchor_rows,
        'counts': {'checked': len(anchor_rows), 'passed': sum(r['passed'] for r in anchor_rows), 'dropped_by_reason': count_reasons(anchor_rows, 'reason')}})
    ctx.write_json(cdir / ('option_check_%s.json' % set_name), 'casalescence/optionb/option_check/v1', {
        'set': set_name, 'rows': option_rows, 'counts': {'checked': len(option_rows), 'passed': sum(r['passed'] for r in option_rows)}})
    counts = {'role_step': sum(1 for c in candidates if c['family'] == 'role_step'),
              'plain_fact': sum(1 for c in candidates if c['family'] == 'plain_fact'), 'spares_used': int(spares)}
    ctx.write_json(cdir / ('candidates_%s.json' % set_name), 'casalescence/optionb/candidates/v1', {'set': set_name, 'candidates': candidates, 'counts': counts})

    # survival per filter, counted per passage and form (a spare stands in where the first question was dropped)
    def alive(slot, stage):
        return through(slot.get('p1'), stage) or through(slot.get('p2'), stage)

    role_slots = [slot for (pid, form), slot in slots.items() if form != 'FACT' and slot.get('p1') is not None
                  and passages[pid]['eligible'] and not passages[pid]['barred'] and form in passages[pid]['open_forms']]
    fact_slots = [slot for (pid, form), slot in slots.items() if form == 'FACT' and slot.get('p1') is not None]
    survival = [{'filter': 'written for an open form', 'role_step': len(role_slots), 'plain_fact': len(fact_slots)}]
    for name, stage in (('form check', 2), ('anchor check', 3), ('option check', 4)):
        survival.append({'filter': name, 'role_step': sum(alive(s, stage) for s in role_slots), 'plain_fact': sum(alive(s, 2) for s in fact_slots)})
    print(json.dumps({
        'program': PROGRAM, 'dry_fixture': ctx.dry, 'status': 'CHECKED', 'set': set_name, 'practice_setting_count': practice_count, 'seal': seal,
        'questions_read': {'role_step': sum(1 for q in questions if q['family'] == 'role_step'),
                           'plain_fact': sum(1 for q in questions if q['family'] == 'plain_fact')},
        'form_check': {'checked': len(form_rows), 'passed': sum(r['passed'] for r in form_rows), 'dropped_by_reason': count_reasons(form_rows, 'reasons')},
        'anchor_check': {'checked': len(anchor_rows), 'passed': sum(r['passed'] for r in anchor_rows), 'dropped_by_reason': count_reasons(anchor_rows, 'reason')},
        'option_check': {'checked': len(option_rows), 'passed': sum(r['passed'] for r in option_rows)},
        'candidates': counts,
        'survival_after_each_filter': survival,
        'note': 'Survival counts one per passage and form. The plain-fact column has no label check; its anchor and option rows repeat the form-check count.'},
        ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Stop as stop:
        print(json.dumps({'program': PROGRAM, 'status': 'STOP', 'code': stop.args[0], 'reason': stop.args[1]}, ensure_ascii=False, indent=1))
        sys.exit(2)
