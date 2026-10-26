#!/usr/bin/env python3
"""Option B job runner. One file, five commands, run in this order by the guest:

  selftest      Gate 0. No model call. Loads the tokenizer only. Works on a CPU-only host in precheck mode.
  run-practice  Practice steps P1, P2, P3 on model B. Does nothing unless selftest.json says SELFTEST_PASS (mode gate0).
  gate          Runs gate_b1.py. Writes GATE.json.
  run-final     The final calls. Does nothing unless GATE.json says "go": true. It is given the prompt folder only.
  score         Runs analysis_b1.py. Writes RESULT.json in every case.

HOW THE GUEST CALLS IT (every option below is accepted under each spelling shown)
  runner_b1.py selftest --mode precheck|gate0 --package DIR --model DIR --out DIR
               [--expect-prompt-list-sha256 HEX --expect-padding-plan-sha256 HEX]     (both needed in mode gate0)
  runner_b1.py run-practice --package DIR --model DIR --out DIR --deadline-unix N
  runner_b1.py gate --package DIR --out DIR --deadline-unix N
  runner_b1.py run-final --constants FILE --prompts DIR --model DIR --out DIR --deadline-unix N
  runner_b1.py score --package DIR --out DIR --model-receipt-before FILE --model-receipt-after-calls FILE
  Other spellings: --package-dir, --model-dir, --output-dir, --out-dir, --prompts-dir, --model-pre, --model-after.
  --model is the snapshot folder of model B, or a folder that holds it at the path in PLAN_CONSTANTS.json.
  --check-args-only on any command: read the arguments, print ARGS_OK, do nothing else.

EXIT CODE
  0 unless the program crashes. A stop is written into a file. It is never an exit code.

FILE RULES (PLAN_CONSTANTS.json, runner_file_rules). The reviewer checks them by reading this file.
  1. Every write goes into the one output folder (--out, work/run_b1/). See create_once, LineFile, StatusLog.
  2. Each output file is created once. Then lines are only added at the end and forced to disk.
  3. Nothing is renamed. Nothing is deleted. No temporary file is used.
  4. File names use only letters, digits, dot, dash and underscore.
  5. Nothing is written under the package folder. Python is told not to write __pycache__ there.
  6. The model is loaded from the snapshot folder with offline settings. No link of any kind is made.

DECODING (PLAN_CONSTANTS.json, decoding). One prompt per call. The single most likely next token at every
step (greedy): no sampling, no beam, and no change to the scores, which is what repetition penalty 1.0 means.
At most 64 new tokens. Stop at an end token. No retry. 32-bit floats. A CPU is refused with GPU_REQUIRED.

Status: SOURCE ONLY. Never run. Not run on the laptop. The self-test is first exercised by the AWS development
test on a made-up package, before seal step 1 (amendment A10); then by the AWS pre-check job on the sealed package.
In both it runs in precheck mode: no GPU is asked for, torch is not imported by this file, no model weights are read.
The model-calling commands are first exercised in the GPU job, on practice tasks, before any final task.
Standard library plus torch and transformers. torch is imported only where a GPU is checked or used.
"""
import sys

sys.dont_write_bytecode = True  # file rule 5: no __pycache__ may appear in the sealed package folder

import argparse
import json
import math
import os
import random
import re
import time
import traceback
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import gate_b1 as plan   # the call plan, the gate decisions, create_once; standard library only

PROGRAM = 'job/runner_b1.py'
SCHEMA_SELFTEST = 'casalescence/optionb/selftest/v1'
SCHEMA_PADDING = 'casalescence/optionb/padding_plan/v1'
CHECK_NAMES = ('scorer_known_examples', 'package_matches_seal', 'every_task_has_every_group', 'gpu_present',
               'tokenizer_loads', 'padding_plan', 'planned_calls_under_cap', 'made_up_sets', 'score_time',
               'precheck_binding')
SETS = ('practice', 'final')
PADDING_STOP = 'GATE_STOP_PADDING'
# The made-up answer sets of the self-test (PLAN_CONSTANTS.json, selftest).
MALFORMED_REPLY = 'I think the answer is probably the second one'
MADE_UP_NOW_UNIX = 0
MADE_UP_CUTOFF_UNIX = 1000000
MADE_UP_WORDING = 1
MADE_UP_UTC = '1970-01-01T00:00:00Z'
OFFLINE_ENVIRONMENT = {'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1', 'HF_HUB_DISABLE_TELEMETRY': '1',
                       'TOKENIZERS_PARALLELISM': 'false'}
DEVICE = 'cuda:0'
_PLACEHOLDER = re.compile(r'<<([A-Z_]+)>>')


class GpuRequired(Exception):
    """No CUDA GPU. The run commands refuse a CPU."""


# =============================================================================================
# Small helpers
# =============================================================================================

def read_json(path):
    with open(path, 'rb') as handle:
        return json.loads(handle.read().decode('utf-8'))


def read_json_or_none(path):
    try:
        return read_json(path)
    except (OSError, ValueError):
        return None


def count_lines(path):
    try:
        with open(path, 'rb') as handle:
            return handle.read().count(b'\n')
    except OSError:
        return 0


def calls_so_far(out):
    """Model calls made in this job so far: one line per call in the two call files."""
    return count_lines(os.path.join(out, 'calls_practice.jsonl')) + count_lines(os.path.join(out, 'calls_final.jsonl'))


def fill(template, values):
    """Plain text replacement of <<NAME>> placeholders, in one pass.

    The text that is put in is never scanned again, so a passage can not be mistaken for a placeholder.
    A placeholder with no value is an error.
    """
    def swap(match):
        name = match.group(1)
        if name not in values or not isinstance(values[name], str):
            raise KeyError('NO_VALUE_FOR_PLACEHOLDER ' + name)
        return values[name]
    return _PLACEHOLDER.sub(swap, template)


class LineFile(object):
    """One output file. Created once. Then one line at a time is added and forced to disk."""

    def __init__(self, out, name):
        if not plan.SAFE_NAME.match(name):
            raise ValueError('UNSAFE_FILE_NAME ' + repr(name))
        self.handle = open(os.path.join(out, name), 'xb')

    def add(self, row):
        self.handle.write(plan.dump_line(row).encode('utf-8'))
        self.handle.flush()
        os.fsync(self.handle.fileno())

    def close(self):
        self.handle.close()


class StatusLog(object):
    """run_status.jsonl: one line per event, added at the end and forced to disk."""

    def __init__(self, out, command):
        self.path = os.path.join(out, 'run_status.jsonl')
        self.command = command

    def event(self, name, calls_done, detail=None):
        row = {'utc': plan.utc_now(), 'command': self.command, 'event': name, 'calls_done': calls_done}
        if detail is not None:
            row['detail'] = detail
        with open(self.path, 'ab') as handle:
            handle.write(plan.dump_line(row).encode('utf-8'))
            handle.flush()
            os.fsync(handle.fileno())
        print('STATUS %s %s calls_done=%d%s' % (self.command, name, calls_done, '' if detail is None else ' ' + detail))
        sys.stdout.flush()


def resolve_snapshot(model_argument, constants):
    """The folder that holds tokenizer_config.json: the given folder, or the snapshot path under it."""
    relative = constants['model_b']['snapshot_path_in_payload'].split('/')
    candidates = [model_argument, os.path.join(model_argument, *relative)]
    if len(relative) > 1:
        candidates.append(os.path.join(model_argument, *relative[1:]))
    for candidate in candidates:
        if os.path.isfile(os.path.join(candidate, 'tokenizer_config.json')):
            return candidate
    raise RuntimeError('MODEL_SNAPSHOT_NOT_FOUND under the folder given with --model')


# =============================================================================================
# Prompts
# =============================================================================================

class Prompts(object):
    """Builds the user message of one call from the prompt parts and, where given, the padding plan."""

    def __init__(self, constants, parts, padding_document=None):
        self.prompt = constants['prompt']
        self.padding = constants['padding']
        self.groups = constants['groups']
        self.passages = dict((passage['passage_id'], passage) for passage in parts['passages'])
        self.tasks = dict((task['task_id'], task) for task in parts['tasks'])
        self.answer_given = dict(((row['task_id'], str(row['level'])), row['note'])
                                 for row in parts.get('answer_given') or [])
        self.frames = dict((name, '\n'.join(self.prompt[name]))
                           for name in ('frame_with_notes', 'frame_none', 'frame_no_passage'))
        self.plan_passages, self.plan_answer_given = {}, {}
        if padding_document is not None:
            for entry in padding_document['passages']:
                if entry['set'] == parts['set']:
                    self.plan_passages[entry['passage_id']] = entry
            for entry in padding_document.get('answer_given') or []:
                self.plan_answer_given[(entry['task_id'], str(entry['level']))] = entry

    def padding_line(self, k):
        return self.padding['line_prefix'] + self.padding['line_unit'] * k + self.padding['line_suffix']

    def block_text(self, k, notes):
        """The Notes block: the padding line, one line feed, then the notes text."""
        return self.padding_line(k) + '\n' + notes

    def option_lines(self, task, level):
        template = self.prompt['option_line']
        return '\n'.join(fill(template, {'LETTER': option['letter'], 'TEXT': option['text']})
                         for option in plan.options_at(task, level))

    def closing(self, task, level, wording):
        shown = str(len(plan.options_at(task, level)))
        template = self.prompt['closing_wordings_in_order'][wording - 1]
        return fill(template, {'LETTERS_OR': self.prompt['letters_or'][shown],
                               'LETTERS_COMMA': self.prompt['letters_comma'][shown]})

    def notes_for(self, task, group, level, ord_length=None):
        """The notes text of one group, without the padding line."""
        if group == plan.ANSWER_GIVEN:
            return self.answer_given[(task['task_id'], str(level))]
        notes = self.passages[task['passage_id']]['notes'][group]
        if isinstance(notes, dict):
            return notes[ord_length]
        return notes

    def user_text(self, task, group, level, wording, k=None, ord_length=None):
        """Returns (the user message, the Notes block text or None)."""
        values = {'QUESTION': task['question'], 'OPTION_LINES': self.option_lines(task, level),
                  'CLOSING': self.closing(task, level, wording)}
        if group == plan.NO_PASSAGE:
            return fill(self.frames['frame_no_passage'], values), None
        values['PASSAGE'] = self.passages[task['passage_id']]['text']
        if group in self.groups['groups_with_a_notes_block']:
            notes = self.notes_for(task, group, level, ord_length)
            values['PADDING_LINE'] = self.padding_line(k)
            values['NOTES'] = notes
            return fill(self.frames['frame_with_notes'], values), self.block_text(k, notes)
        if group in self.groups['groups_without_a_notes_block']:
            return fill(self.frames['frame_none'], values), None
        raise ValueError('UNKNOWN_GROUP ' + repr(group))   # a struck group has no code path

    def build(self, task, group, level, wording):
        """One prompt, with the padding and the note length taken from the padding plan."""
        k, ord_length = None, None
        if group in self.groups['groups_with_a_notes_block']:
            if group == plan.ANSWER_GIVEN:
                k = self.plan_answer_given[(task['task_id'], str(level))]['k']
            else:
                entry = self.plan_passages[task['passage_id']]
                k = entry['blocks'][group]['k']
                if group in self.groups['ordinary']:
                    ord_length = entry['ord_length_chosen'][group]
        text, block = self.user_text(task, group, level, wording, k, ord_length)
        return {'user_text': text, 'block_text': block, 'padding_k': k, 'ord_length': ord_length}


def set_offline_environment():
    for name, value in OFFLINE_ENVIRONMENT.items():
        os.environ[name] = value


def load_tokenizer(snapshot):
    """Model B's own tokenizer, from the snapshot folder, offline. No model weights are touched."""
    set_offline_environment()
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(snapshot, local_files_only=True, trust_remote_code=False, use_fast=True)


def render(tokenizer, user_text):
    """One user message through the model's own chat template. The default system text is left as it is."""
    return tokenizer.apply_chat_template([{'role': 'user', 'content': user_text}], tokenize=False,
                                         add_generation_prompt=True)


class TokenCounter(object):
    """len(tokenizer.encode(text, add_special_tokens=False)), remembered per text."""

    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
        self.known = {}

    def __call__(self, text):
        count = self.known.get(text)
        if count is None:
            count = len(self.tokenizer.encode(text, add_special_tokens=False))
            self.known[text] = count
        return count


# =============================================================================================
# Gate 0, part: every task has every group
# =============================================================================================

def check_structure(constants, parts_by_set, practice_keys):
    """Returns (problems, sizes). Every task must have every group it should have, and every part it needs."""
    problems = []

    def bad(text):
        if len(problems) < 200:
            problems.append(text)

    groups_c = constants['groups']
    levels_c = constants['levels']
    prompt = constants['prompt']
    with_block = groups_c['groups_with_a_notes_block']
    ordinary = groups_c['ordinary']
    lengths = sorted(constants['ordinary_notes']['lengths_in_order'])
    struck = list(groups_c.get('struck') or [])
    fact_options = constants['task_families']['plain_fact']['options_written']
    sizes, set_of_task, set_of_passage = {}, {}, {}
    for set_name in SETS:
        parts = parts_by_set[set_name]
        if parts.get('set') != set_name:
            bad('%s: the file says it is set %r' % (set_name, parts.get('set')))
        passages = {}
        for passage in parts.get('passages') or []:
            passage_id = passage.get('passage_id')
            if not isinstance(passage_id, str) or not passage_id:
                bad('%s: a passage has no id' % set_name)
                continue
            if passage_id in passages:
                bad('%s: passage %s is listed twice' % (set_name, passage_id))
            if set_of_passage.get(passage_id, set_name) != set_name:
                bad('passage %s is in both sets' % passage_id)
            set_of_passage[passage_id] = set_name
            passages[passage_id] = passage
            if not isinstance(passage.get('text'), str) or not passage['text'].strip():
                bad('%s: passage %s has no text' % (set_name, passage_id))
            if not isinstance(passage.get('notes'), dict):
                bad('%s: passage %s has no notes' % (set_name, passage_id))
            else:
                for name in struck:
                    if name in passage['notes']:
                        bad('%s: passage %s holds notes for the struck group %s' % (set_name, passage_id, name))
        used, seen, role, fact = set(), set(), 0, 0
        for task in parts.get('tasks') or []:
            task_id, family = task.get('task_id'), task.get('family')
            if not isinstance(task_id, str) or not task_id:
                bad('%s: a task has no id' % set_name)
                continue
            if task_id in seen:
                bad('%s: task %s is listed twice' % (set_name, task_id))
            seen.add(task_id)
            if set_of_task.get(task_id, set_name) != set_name:
                bad('task %s is in both sets' % task_id)
            set_of_task[task_id] = set_name
            if family not in ('role_step', 'plain_fact'):
                bad('%s: task %s has family %r' % (set_name, task_id, family))
                continue
            if family == 'role_step':
                role += 1
            else:
                fact += 1
            if task.get('groups') != groups_c['by_family'][family]:
                bad('%s: task %s does not list exactly the groups of its family' % (set_name, task_id))
            passage = passages.get(task.get('passage_id'))
            if passage is None:
                bad('%s: task %s names a passage that is not in the file' % (set_name, task_id))
                continue
            used.add(task['passage_id'])
            if not isinstance(task.get('question'), str) or not task['question'].strip():
                bad('%s: task %s has no question' % (set_name, task_id))
            options = task.get('options')
            wanted_levels = ['1', '2'] if family == 'role_step' else ['1']
            if not isinstance(options, dict) or sorted(options) != wanted_levels:
                bad('%s: task %s does not have exactly the option levels %s' % (set_name, task_id, wanted_levels))
                continue
            for level in wanted_levels:
                shown = levels_c[level]['options_shown'] if family == 'role_step' else fact_options
                rows = options[level]
                if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
                    bad('%s: task %s level %s: the options are not a list' % (set_name, task_id, level))
                    continue
                letters = [row.get('letter') for row in rows]
                if letters != levels_c['letters'][:shown]:
                    bad('%s: task %s level %s: the letters are %r' % (set_name, task_id, level, letters))
                    continue
                if any(not isinstance(row.get('text'), str) or not row['text'].strip() for row in rows):
                    bad('%s: task %s level %s: an option has no text' % (set_name, task_id, level))
                if str(shown) not in prompt['letters_or'] or str(shown) not in prompt['letters_comma']:
                    bad('the plan has no letter list for %d options' % shown)
                if set_name == 'practice':
                    key_letter = (practice_keys.get(task_id) or {}).get(level)
                    if key_letter not in letters:
                        bad('practice: task %s level %s: the key is not one of the letters shown' % (task_id, level))
            notes = passage.get('notes') if isinstance(passage.get('notes'), dict) else {}
            for group in groups_c['by_family'][family]:
                if group not in with_block:
                    continue
                value = notes.get(group)
                if group in ordinary:
                    if (not isinstance(value, dict) or sorted(value) != lengths
                            or any(not isinstance(value[name], str) or not value[name].strip() for name in lengths)):
                        bad('%s: passage %s has no usable %s notes in the three lengths' % (
                            set_name, task['passage_id'], group))
                elif not isinstance(value, str) or not value.strip():
                    bad('%s: passage %s has no %s notes' % (set_name, task['passage_id'], group))
            if notes.get(plan.FILLER) != prompt['filler_sentence']:
                bad('%s: passage %s: the FILLER note is not the filler sentence' % (set_name, task['passage_id']))
        # A passage that carries no task is never used in a call. It is counted, not treated as a fault.
        idle = sum(1 for passage_id in passages if passage_id not in used)
        given = parts.get('answer_given') or []
        if set_name == 'final':
            if given:
                bad('final: the file holds ANSWER-GIVEN notes; they belong to practice only')
        else:
            notes_given = dict(((row.get('task_id'), str(row.get('level'))), row.get('note')) for row in given)
            for task in parts.get('tasks') or []:
                if task.get('family') != 'role_step':
                    continue
                for level in ('1', '2'):
                    key_letter = (practice_keys.get(task.get('task_id')) or {}).get(level)
                    wanted = (fill(prompt['answer_given_note'], {'LETTER': key_letter})
                              if isinstance(key_letter, str) else None)
                    if wanted is None or notes_given.get((task.get('task_id'), level)) != wanted:
                        bad('practice: task %s level %s: the ANSWER-GIVEN note is missing or does not state the key'
                            % (task.get('task_id'), level))
            if len(given) != 2 * role:
                bad('practice: %d ANSWER-GIVEN notes for %d role-step tasks' % (len(given), role))
        sizes[set_name] = {'passages': len(passages), 'passages_without_a_task': idle,
                           'role_step_tasks': role, 'plain_fact_tasks': fact}
        if role + fact == 0:
            bad('%s: the file holds no task' % set_name)
    padding = constants['padding']
    if padding['line_prefix'] + padding['line_unit'] + padding['line_suffix'] != padding['shortest_line']:
        bad('the padding line parts do not build the shortest padding line')
    return problems, sizes


# =============================================================================================
# Gate 0, part: the padding plan and the hash of every prompt
# =============================================================================================

def fit_padding(target, block_count):
    """Pick k (1 or more) so that the block's token count is as near the target as it can be.

    block_count(k) gives the tokens of the block built with k padding units. A tie goes to the smaller k.
    Returns (k, tokens of that block).
    """
    first = block_count(1)
    if first >= target:
        return 1, first
    step = block_count(2) - first
    if step < 1:
        step = 1
    k = 1 + (target - first) // step
    guard = 0
    while block_count(k) < target:
        k += 1
        guard += 1
        if guard > 100000:
            raise RuntimeError('PADDING_FIT_DID_NOT_END')
    while k > 1 and block_count(k - 1) >= target:
        k -= 1
    # Now block_count(k) >= target and block_count(k - 1) < target. k is at least 2 here.
    above, below = block_count(k), block_count(k - 1)
    if target - below <= above - target:
        return k - 1, below
    return k, above


def build_padding_plan(constants, parts_by_set, count):
    """Returns (the padding plan document, problems). count(text) gives tokens.

    Per passage: for each ordinary group take the length nearest the ROLE note in tokens; the target is the
    largest block built with the shortest padding line; every block is padded up to the target at its start.
    """
    padding = constants['padding']
    groups_c = constants['groups']
    with_block = groups_c['groups_with_a_notes_block']
    ordinary = groups_c['ordinary']
    all_lengths = constants['ordinary_notes']['lengths_in_order']
    tie_order = constants['ordinary_notes']['length_pick_tie_order']
    allowed = padding['token_difference_allowed']
    problems, passages_out, answer_out, shares = [], [], [], {}
    for set_name in SETS:
        parts = parts_by_set[set_name]
        prompts = Prompts(constants, parts)
        tasks_of = {}
        for task in parts['tasks']:
            tasks_of.setdefault(task['passage_id'], []).append(task)
        shares[set_name] = {}
        for passage in sorted(parts['passages'], key=lambda item: item['passage_id']):
            passage_id = passage['passage_id']
            tasks_here = sorted(tasks_of.get(passage_id, []), key=lambda item: item['task_id'])
            used = set()
            for task in tasks_here:
                used.update(task['groups'])
            groups_here = [group for group in groups_c['must_run_in_order'] if group in used and group in with_block]
            if not groups_here:
                continue
            notes = passage['notes']
            role_tokens = count(notes[plan.ROLE])
            content_tokens, chosen, texts = {}, {}, {}
            for group in groups_here:
                if group in ordinary:
                    per_length = dict((length, count(notes[group][length])) for length in all_lengths)
                    best_gap, best_length = None, None
                    for length in tie_order:     # 100 first, then 090, then 110: a tie keeps the earlier one
                        gap = abs(per_length[length] - role_tokens)
                        if best_gap is None or gap < best_gap:
                            best_gap, best_length = gap, length
                    content_tokens[group] = per_length
                    chosen[group] = best_length
                    texts[group] = notes[group][best_length]
                else:
                    content_tokens[group] = count(notes[group])
                    texts[group] = notes[group]

            def counter_for(text):
                return lambda k: count(prompts.block_text(k, text))

            target = max(count(prompts.block_text(1, texts[group])) for group in groups_here)
            blocks = {}
            for group in groups_here:
                k, tokens = fit_padding(target, counter_for(texts[group]))
                padding_tokens = count(prompts.padding_line(k))
                blocks[group] = {'k': k, 'block_tokens': tokens, 'padding_tokens': padding_tokens,
                                 'difference': tokens - target}
                if abs(tokens - target) > allowed:
                    problems.append('%s passage %s group %s: the block is %d tokens, the target is %d'
                                    % (set_name, passage_id, group, tokens, target))
                shares[set_name].setdefault(group, []).append(Fraction(padding_tokens, tokens))
            passages_out.append({'passage_id': passage_id, 'set': set_name, 'ord_length_chosen': chosen,
                                 'content_tokens': content_tokens, 'target_tokens': target, 'blocks': blocks})
            if set_name != 'practice':
                continue
            for task in tasks_here:
                if not plan.is_role_step(task):
                    continue
                for level in plan.task_levels(task):
                    note = prompts.notes_for(task, plan.ANSWER_GIVEN, level)
                    k, tokens = fit_padding(target, counter_for(note))
                    padding_tokens = count(prompts.padding_line(k))
                    answer_out.append({'task_id': task['task_id'], 'level': str(level), 'k': k,
                                       'block_tokens': tokens, 'padding_tokens': padding_tokens,
                                       'difference': tokens - target})
                    if abs(tokens - target) > allowed:
                        problems.append('practice task %s level %d ANSWER-GIVEN: the block is %d tokens, the target is %d'
                                        % (task['task_id'], level, tokens, target))
                    shares[set_name].setdefault(plan.ANSWER_GIVEN, []).append(Fraction(padding_tokens, tokens))
    average, stop = {}, False
    limit = Fraction(padding['average_max_percent'], 100)
    for set_name in SETS:
        average[set_name] = {}
        for group in sorted(shares[set_name]):
            values = shares[set_name][group]
            mean = sum(values, Fraction(0)) / len(values)
            average[set_name][group] = {'share': [mean.numerator, mean.denominator],
                                        'percent_text': plan.fraction_text(mean * 100), 'blocks': len(values)}
            if group in padding['groups_under_the_rule'] and mean > limit:
                stop = True
    document = {'schema': SCHEMA_PADDING, 'passages': passages_out, 'answer_given': answer_out,
                'average_padding_share': average,
                'rule': {'max_percent': padding['average_max_percent'],
                         'groups': list(padding['groups_under_the_rule']), 'stop': stop}}
    return document, problems


def build_prompt_table(constants, parts_by_set, padding_document, tokenizer, count):
    """Every prompt that could be sent: every set, task, group it has, level it has and closing wording.

    Returns (call id -> facts, the largest prompt token count). No prompt is sent to any model here.
    """
    groups_c = constants['groups']
    table, most_tokens = {}, 0
    for set_name in SETS:
        parts = parts_by_set[set_name]
        prompts = Prompts(constants, parts, padding_document)
        extra = list(groups_c['task_check_role_step'])
        if set_name == 'practice':
            extra = list(groups_c['practice_only_role_step']) + extra
        for task in sorted(parts['tasks'], key=lambda item: item['task_id']):
            groups = list(task['groups']) + (extra if plan.is_role_step(task) else [])
            for level in plan.task_levels(task):
                for wording in plan.wording_numbers(constants):
                    for group in groups:
                        built = prompts.build(task, group, level, wording)
                        rendered = render(tokenizer, built['user_text'])
                        prompt_tokens = len(tokenizer.encode(rendered, add_special_tokens=False))
                        most_tokens = max(most_tokens, prompt_tokens)
                        call_id = plan.make_call_id(set_name, task['task_id'], group, level, wording)
                        if call_id in table:
                            raise ValueError('CALL_ID_BUILT_TWICE ' + call_id)
                        table[call_id] = {
                            'prompt_sha256': plan.sha256_hex(rendered.encode('utf-8')),
                            'prompt_tokens': prompt_tokens,
                            'notes_tokens': count(built['block_text']) if built['block_text'] is not None else None,
                            'padding_k': built['padding_k'], 'ord_length': built['ord_length']}
    return table, most_tokens


# =============================================================================================
# Gate 0, part: the five made-up answer sets
# =============================================================================================

def made_up_reply(set_name, call, key_letter, letters, role_number, seed):
    """The made-up reply of one call. role_number is None for a plain-fact task."""
    def well_formed(letter):
        return '{"answer": "%s"}' % letter

    first_wrong = [letter for letter in letters if letter != key_letter][0]
    if set_name == 'ALL_RIGHT':
        return well_formed(key_letter)
    if set_name == 'ALL_WRONG':
        return well_formed(first_wrong)
    if set_name == 'ALL_MALFORMED':
        return MALFORMED_REPLY
    if set_name == 'RANDOM_LETTERS':
        return well_formed(random.Random('%d|%s' % (seed, call['call_id'])).choice(letters))
    if set_name == 'DESIGNED':
        if role_number is None:
            return well_formed(key_letter)                       # plain-fact tasks: right in every group
        if call['group'] in (plan.ROLE, plan.ANSWER_GIVEN):
            return well_formed(key_letter)                       # right on every task
        if call['group'] == plan.NO_PASSAGE:
            return well_formed(first_wrong)                      # wrong on every task
        return well_formed(key_letter if role_number % 2 == 0 else first_wrong)
    raise ValueError('UNKNOWN_MADE_UP_SET ' + repr(set_name))


def code_matches(printed, expected, listed):
    """expected is one code (then it must be printed exactly) or a sentence (then any listed code will do)."""
    if re.fullmatch(r'[A-Z_]+', expected):
        return printed == expected
    return printed in listed


def run_made_up_set(set_name, constants, package, out, state):
    """Writes the two made-up call files of one set, then runs the gate program and the analysis program on them."""
    import analysis_b1
    parts = state['parts']['practice']
    keys = state['practice_keys']
    table = state['table']
    tasks = dict((task['task_id'], task) for task in parts['tasks'])
    role_number = dict((task_id, number) for number, task_id in enumerate(
        sorted(task_id for task_id in tasks if plan.is_role_step(tasks[task_id]))))
    seed = constants['seeds']['selftest_random_letters']
    made = [0]

    def line(call, table_id):
        task = tasks[call['task_id']]
        letters = plan.letters_at(task, call['level'])
        key_letter = keys[call['task_id']][str(call['level'])]
        facts = table[table_id]
        made[0] += 1
        return {'call_id': call['call_id'], 'n': made[0], 'phase': call['phase'], 'step': call['step'],
                'task_id': call['task_id'], 'passage_id': call['passage_id'], 'family': call['family'],
                'group': call['group'], 'level': call['level'], 'wording': call['wording'],
                'ord_length': facts['ord_length'], 'padding_k': facts['padding_k'], 'prompt': '',
                'prompt_sha256': facts['prompt_sha256'], 'prompt_tokens': facts['prompt_tokens'],
                'notes_tokens': facts['notes_tokens'], 'letters_shown': letters,
                'raw_answer': made_up_reply(set_name, call, key_letter, letters, role_number.get(call['task_id']), seed),
                'answer_token_ids': [], 'new_tokens': 0, 'cut_off': False, 'seconds_text': '1.0', 'utc': MADE_UP_UTC}

    # The practice file, built the way run-practice works: P1, decide, P2, decide, then P3 unless stopped early.
    p1_calls = plan.practice_calls(constants, parts, 'P1')
    rows = [line(call, call['call_id']) for call in p1_calls]
    by_id, _ = plan.index_lines(rows)
    clean_by_wording, _ = plan.p1_counts(p1_calls, by_id, tasks, keys)
    wording = plan.decide_wording(clean_by_wording)
    p2_calls = plan.practice_calls(constants, parts, 'P2', chosen_wording=wording)
    rows.extend(line(call, call['call_id']) for call in p2_calls)
    by_id, _ = plan.index_lines(rows)
    correct_by_level, fact_correct, _ = plan.p2_counts(p1_calls, p2_calls, by_id, tasks, keys, wording)
    level, _, early = plan.decide_after_p2(constants, correct_by_level, fact_correct)
    if early is None:
        rows.extend(line(call, call['call_id'])
                    for call in plan.practice_calls(constants, parts, 'P3', chosen_wording=wording, chosen_level=level))
    practice_name = 'trial_%s_calls_practice.jsonl' % set_name
    plan.create_once(out, practice_name, ''.join(plan.dump_line(row) for row in rows))

    # The final file: the same practice tasks written as phase final, level 1, wording 1.
    made_level = constants['selftest']['made_up_level_for_analysis']
    final_rows = [line(call, 'practice' + call['call_id'][len('final'):])
                  for call in plan.final_calls(constants, parts, made_level, MADE_UP_WORDING,
                                               [plan.BLOCK_MUST_RUN, plan.BLOCK_NO_PASSAGE])]
    final_name = 'trial_%s_calls_final.jsonl' % set_name
    plan.create_once(out, final_name, ''.join(plan.dump_line(row) for row in final_rows))

    started = time.perf_counter()
    gate = plan.gate_files(package, out, MADE_UP_CUTOFF_UNIX, now_unix=MADE_UP_NOW_UNIX, calls_name=practice_name,
                           gate_name='trial_%s_GATE.json' % set_name,
                           trial={'planned_final': state['planned_calls']})
    gate_seconds = time.perf_counter() - started
    started = time.perf_counter()
    result = analysis_b1.run(package, out, trial={'calls_name': final_name,
                                                  'result_name': 'trial_%s_RESULT.json' % set_name,
                                                  'level': made_level, 'wording': MADE_UP_WORDING}, quiet=True)
    analysis_seconds = time.perf_counter() - started

    expected = constants['selftest']['made_up_sets'][set_name]
    gate_printed = plan.gate_word(gate)
    gate_ok = code_matches(gate_printed, expected['gate_must_print'], [plan.GO] + list(constants['stop_codes']))
    must_choose = expected.get('gate_must_choose')
    if must_choose is not None:
        gate_ok = (gate_ok and gate.get('chosen_wording') == must_choose['wording']
                   and gate.get('chosen_level') == must_choose['level'])
    analysis_printed = result['outcome_code']
    suffix = constants['tiers']['exploratory_suffix']
    base = analysis_printed[:-len(suffix)] if analysis_printed.endswith(suffix) else analysis_printed
    listed = [row['code'] for row in constants['outcome_codes_in_checking_order'] if row['code'] != constants['pass_code']]
    analysis_ok = code_matches(analysis_printed, expected['analysis_must_print'], []) or (
        re.fullmatch(r'[A-Z_]+', expected['analysis_must_print']) is None and base in listed)
    view_errors = list(result.get('view_errors') or [])
    return {'gate_printed': gate_printed, 'gate_expected': expected['gate_must_print'],
            'analysis_printed': analysis_printed, 'analysis_expected': expected['analysis_must_print'],
            'ok': bool(gate_ok and analysis_ok and not view_errors),
            'gate_ok': bool(gate_ok), 'analysis_ok': bool(analysis_ok), 'view_errors': view_errors,
            'gate_chose': {'wording': gate.get('chosen_wording'), 'level': gate.get('chosen_level')},
            'gate_seconds_text': '%.2f' % gate_seconds, 'analysis_seconds_text': '%.2f' % analysis_seconds,
            'analysis_seconds': analysis_seconds}


# =============================================================================================
# Command 1: selftest (Gate 0)
# =============================================================================================

def cmd_selftest(args):
    started = time.perf_counter()
    mode, package, out = args.mode, args.package, args.out
    os.makedirs(out, exist_ok=True)
    inputs = plan.Inputs()
    constants = inputs.read_json(os.path.join(package, 'PLAN_CONSTANTS.json'), 'package/PLAN_CONSTANTS.json')
    if mode not in constants['selftest']['modes'] or PADDING_STOP not in constants['stop_codes']:
        raise ValueError('PLAN_CONSTANTS_SELFTEST_NOT_AS_EXPECTED')
    checks, state = {}, {}

    def record(name, passed, detail):
        checks[name] = {'name': name, 'passed': passed, 'detail': detail}
        print('CHECK %-28s %-11s %s' % (name, {True: 'passed', False: 'FAILED', None: 'not checked'}[passed], detail))
        sys.stdout.flush()

    def attempt(name, function):
        try:
            passed, detail = function()
        except Exception as error:
            traceback.print_exc()
            passed, detail = False, 'error: %s: %s' % (type(error).__name__, str(error)[:300])
        record(name, bool(passed), detail)
        return bool(passed)

    # 1. The scorer gives the hand-decided category on every known example.
    def check_examples():
        import scorer_v0_1_1 as scorer
        name = os.path.basename(constants['scorer']['examples_file'])
        examples = inputs.read_json(os.path.join(package, 'job', name), 'package/job/' + name)['examples']
        good, total, failures = scorer.check_known_examples(examples)
        wanted = constants['scorer']['examples_old_count'] + constants['scorer']['examples_added_count']
        detail = '%d of %d' % (good, total)
        if total != wanted:
            detail += '; the plan asks for %d examples' % wanted
        if scorer.VERSION != constants['scorer']['version']:
            detail += '; the scorer is version %s, the plan names %s' % (scorer.VERSION, constants['scorer']['version'])
        if failures:
            detail += '; first failures: ' + json.dumps(failures[:5], sort_keys=True)
        return good == total == wanted and scorer.VERSION == constants['scorer']['version'], detail

    examples_ok = attempt('scorer_known_examples', check_examples)

    # 2. The package hashes match the seal. Each file is compared with its size and sha256 in force:
    #    where a repair line lists a path again, the latest line counts (FILE_FORMATS.md section 15.2).
    #    A repair line outside its window is a problem (amendment A5): a program repair line after the line
    #    7_PRECHECK, or a tool repair line after the line 3C_FINAL_QUESTIONS_AND_KEYS.
    #    tools/verdict.py is one of the package files that must be there.
    def check_package():
        import analysis_b1
        report = analysis_b1.check_package_against_seal(package, constants)
        if report['seal_sha256'] is not None:
            inputs.note('package/' + analysis_b1.SEAL_NAME, report['seal_sha256'])
        detail = '%d sealed package files checked, %d seal lines, %d of them repair lines' % (
            report['files_checked'], report['seal_lines'], report['repair_lines'])
        if report['problems']:
            detail += '; problems: ' + '; '.join(report['problems'][:8])
        return report['ok'], detail

    package_ok = attempt('package_matches_seal', check_package)

    # 3. Every task has every group it should have. Final keys are not opened here.
    def check_tasks():
        parts_by_set = {}
        for set_name in SETS:
            parts_by_set[set_name] = inputs.read_json(
                os.path.join(package, 'prompts', 'prompt_parts_%s.json' % set_name),
                'package/prompts/prompt_parts_%s.json' % set_name)
        practice_keys = inputs.read_json(os.path.join(package, 'keys_practice', 'keys_practice.json'),
                                         'package/keys_practice/keys_practice.json')['keys']
        problems, sizes = check_structure(constants, parts_by_set, practice_keys)
        state['parts'], state['practice_keys'], state['sizes'] = parts_by_set, practice_keys, sizes
        detail = json.dumps(sizes, sort_keys=True)
        if problems:
            detail += '; %d problem(s), first: %s' % (len(problems), '; '.join(problems[:6]))
        return not problems, detail

    structure_ok = attempt('every_task_has_every_group', check_tasks)

    # 4. The GPU is present (Gate 0 of the GPU job only).
    if mode == 'gate0':
        def check_gpu():
            set_offline_environment()
            import torch
            if not torch.cuda.is_available():
                return False, constants['runner_refusal_code'] + ': no CUDA GPU is present'
            return True, 'a CUDA GPU is present: %s' % torch.cuda.get_device_name(0)
        attempt('gpu_present', check_gpu)
    else:
        record('gpu_present', None, 'not checked in precheck mode')

    # 5. The tokenizer loads. No model weights are loaded.
    def check_tokenizer():
        snapshot = resolve_snapshot(args.model, constants)
        pinned = constants['model_b']['files']
        small = list(constants['model_b']['precheck_files'])
        problems = []
        for name in small:
            try:
                with open(os.path.join(snapshot, name), 'rb') as handle:
                    data = handle.read()
            except OSError:
                problems.append('%s is missing' % name)
                continue
            if len(data) != pinned[name]['bytes'] or plan.sha256_hex(data) != pinned[name]['sha256']:
                problems.append('%s is not the pinned file' % name)
        if mode == 'gate0':
            for name in sorted(pinned):
                if name not in small:
                    path = os.path.join(snapshot, name)
                    if not os.path.isfile(path) or os.path.getsize(path) != pinned[name]['bytes']:
                        problems.append('%s is missing or has the wrong size' % name)
        tokenizer = load_tokenizer(snapshot)
        if not getattr(tokenizer, 'is_fast', False):
            problems.append('the tokenizer is not the fast kind')
        if not getattr(tokenizer, 'chat_template', None):
            problems.append('the tokenizer has no chat template')
        sample = 'Read the passage and answer the question.\n\nPassage:\nA short line for the self-test.'
        rendered = render(tokenizer, sample)
        ids = tokenizer.encode(rendered, add_special_tokens=False)
        direct = tokenizer.apply_chat_template([{'role': 'user', 'content': sample}], tokenize=True,
                                               add_generation_prompt=True)
        if hasattr(direct, 'keys'):
            direct = direct['input_ids']
        if [int(value) for value in direct] != [int(value) for value in ids]:
            problems.append('the two ways of turning a chat prompt into tokens do not agree')
        if rendered.count(sample) != 1:
            problems.append('the chat template does not hold the user message exactly once')
        limit = None
        try:
            limit = read_json(os.path.join(snapshot, 'config.json')).get('max_position_embeddings')
        except (OSError, ValueError):
            problems.append('config.json is not readable')
        state['tokenizer'], state['count'], state['position_limit'] = tokenizer, TokenCounter(tokenizer), limit
        detail = '%d small model files match the pinned hashes; the sample prompt has %d tokens' % (len(small), len(ids))
        if problems:
            detail = '; '.join(problems)
        return not problems, detail

    tokenizer_ok = attempt('tokenizer_loads', check_tokenizer)

    # 6. The padding plan and the hash of every practice and final prompt. No prompt is sent to a model.
    if structure_ok and tokenizer_ok:
        def check_padding():
            document, problems = build_padding_plan(constants, state['parts'], state['count'])
            data = plan.create_once(out, 'padding_plan.json', plan.dump_json(document, sort_keys=True))
            state['padding_plan_sha256'] = plan.sha256_hex(data)
            table, most_tokens = build_prompt_table(constants, state['parts'], document, state['tokenizer'],
                                                    state['count'])
            text = ''.join(plan.dump_line({'call_id': call_id, 'notes_tokens': table[call_id]['notes_tokens'],
                                           'prompt_sha256': table[call_id]['prompt_sha256'],
                                           'prompt_tokens': table[call_id]['prompt_tokens']}, sort_keys=True)
                           for call_id in sorted(table))
            data = plan.create_once(out, 'prompt_hashes.jsonl', text)
            state['prompt_list_sha256'] = plan.sha256_hex(data)
            state['table'] = table
            limit = state['position_limit']
            if isinstance(limit, int) and most_tokens + constants['decoding']['max_new_tokens'] > limit:
                problems.append('the longest prompt (%d tokens) does not fit the model' % most_tokens)
            state['padding_rule_only'] = document['rule']['stop'] and not problems
            shown = []
            for set_name in SETS:
                for group in constants['padding']['groups_under_the_rule']:
                    row = document['average_padding_share'][set_name].get(group)
                    if row is not None:
                        shown.append('%s %s %s%%' % (set_name, group, row['percent_text']))
            detail = '%d prompts hashed; longest prompt %d tokens; average padding: %s' % (
                len(table), most_tokens, ', '.join(shown))
            if document['rule']['stop']:
                detail += '; ABOVE the %d percent line: %s' % (document['rule']['max_percent'], PADDING_STOP)
            if problems:
                detail += '; %d problem(s), first: %s' % (len(problems), '; '.join(problems[:5]))
            return not problems and not document['rule']['stop'], detail
        attempt('padding_plan', check_padding)
    else:
        record('padding_plan', None, 'not reached: an earlier check failed')
    plan_written = 'table' in state

    # 7. The planned number of calls is at most the call cap.
    if structure_ok:
        def check_calls():
            counts = plan.planned_call_counts(constants, state['parts']['practice'], state['parts']['final'])
            state['planned_calls'] = counts
            if constants['gates']['gate_0']['planned_calls_must_not_exceed_call_cap'] is not True:
                return False, 'the plan no longer asks for this check'
            return counts['whole_job'] <= counts['cap'], json.dumps(counts, sort_keys=True)
        attempt('planned_calls_under_cap', check_calls)
    else:
        record('planned_calls_under_cap', None, 'not reached: an earlier check failed')

    # 8. The gate program and the analysis program, from start to end, on the five made-up answer sets.
    made_up = {}
    if examples_ok and package_ok and structure_ok and plan_written and 'planned_calls' in state:
        def check_made_up():
            if MALFORMED_REPLY not in constants['selftest']['made_up_sets']['ALL_MALFORMED']['replies']:
                return False, 'the plan gives another text for the ALL_MALFORMED set'
            everything = True
            for set_name in constants['selftest']['made_up_sets_in_order']:
                made_up[set_name] = run_made_up_set(set_name, constants, package, out, state)
                everything = everything and made_up[set_name]['ok']
            return everything, '; '.join('%s: gate %s, analysis %s%s' % (
                name, row['gate_printed'], row['analysis_printed'], '' if row['ok'] else ' (NOT AS EXPECTED)')
                for name, row in made_up.items())
        attempt('made_up_sets', check_made_up)
    else:
        record('made_up_sets', None, 'not reached: an earlier check failed')

    # 9. The score stage's time limit: 5 times the slowest analysis run, at least 120 s; above 240 s is a stop.
    rule = constants['gates']['gate_0']
    score_limit = rule['score_time_limit_min_seconds']
    slowest_text = plan.UNDEFINED
    if made_up and len(made_up) == len(constants['selftest']['made_up_sets_in_order']):
        slowest = max(row['analysis_seconds'] for row in made_up.values())
        slowest_text = '%.2f' % slowest
        needed = slowest * rule['score_time_factor']
        score_limit = max(rule['score_time_limit_min_seconds'], int(math.ceil(needed)))
        fits = needed <= rule['score_time_limit_max_seconds']
        if not fits:
            score_limit = rule['score_time_limit_max_seconds']
        record('score_time', fits, 'slowest analysis run %s s; %d times that is %.2f s; score stage limit %d s' % (
            slowest_text, rule['score_time_factor'], needed, score_limit))
    else:
        record('score_time', None, 'not reached: the made-up sets did not all run')

    # 10. The two hashes the pre-check printed must come out the same (Gate 0 of the GPU job only).
    if mode != 'gate0':
        record('precheck_binding', None, 'not checked in precheck mode: this job prints the two hashes '
                                         'that Gate 0 of the GPU job must reproduce')
    elif not plan_written:
        record('precheck_binding', None, 'not reached: the padding plan and the prompt list were not written')
    else:
        same = (isinstance(args.expect_prompt_list_sha256, str) and isinstance(args.expect_padding_plan_sha256, str)
                and args.expect_prompt_list_sha256 == state['prompt_list_sha256']
                and args.expect_padding_plan_sha256 == state['padding_plan_sha256'])
        record('precheck_binding', same, 'both hashes equal the pre-check values' if same else
               'the expected hashes were not given, or they differ from this build')

    failed = [name for name in CHECK_NAMES if checks[name]['passed'] is False]
    if not failed:
        status = constants['selftest_pass_status']
    elif failed[0] == 'gpu_present':
        status = constants['runner_refusal_code']
    elif failed[0] == 'padding_plan' and state.get('padding_rule_only'):
        status = PADDING_STOP
    else:
        status = plan.SELFTEST_STOP
    public_rows = {}
    for name, row in made_up.items():
        public_rows[name] = dict((key, value) for key, value in row.items() if key != 'analysis_seconds')
    document = {
        'schema': SCHEMA_SELFTEST, 'made_by': plan.made_by(PROGRAM, os.path.abspath(__file__)), 'inputs': inputs.items,
        'mode': mode, 'status': status, 'checks': [checks[name] for name in CHECK_NAMES],
        'prompt_list_sha256': state.get('prompt_list_sha256'), 'padding_plan_sha256': state.get('padding_plan_sha256'),
        'planned_calls': state.get('planned_calls'),
        'slowest_analysis_seconds_text': slowest_text, 'score_time_limit_seconds': score_limit,
        'made_up_sets': public_rows, 'sizes': state.get('sizes'),
        'seconds_text': '%.2f' % (time.perf_counter() - started),
    }
    plan.create_once(out, 'selftest.json', plan.dump_json(document))
    print('prompt_list_sha256 %s' % state.get('prompt_list_sha256'))
    print('padding_plan_sha256 %s' % state.get('padding_plan_sha256'))
    print('SELFTEST_STATUS %s (mode %s, %s seconds)' % (status, mode, document['seconds_text']))
    sys.stdout.flush()
    return 0


# =============================================================================================
# Model B: loading and one greedy call
# =============================================================================================

def load_model(constants, snapshot):
    """Loads model B on the GPU, frozen, in 32-bit floats, offline. Raises GpuRequired on a CPU-only host."""
    set_offline_environment()
    import torch
    if not torch.cuda.is_available():
        raise GpuRequired()
    from transformers import AutoModelForCausalLM
    decoding = constants['decoding']
    if (decoding['do_sample'] is not False or decoding['num_beams'] != 1 or decoding['repetition_penalty'] != 1.0
            or decoding['prompts_per_call'] != 1 or decoding['retries'] != 0 or decoding['float_type'] != 'float32'
            or decoding['stop_at_end_token'] is not True):
        raise ValueError('PLAN_CONSTANTS_DECODING_IS_NOT_WHAT_THIS_RUNNER_DOES')
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    tokenizer = load_tokenizer(snapshot)
    model = AutoModelForCausalLM.from_pretrained(snapshot, local_files_only=True, trust_remote_code=False,
                                                 use_safetensors=True, torch_dtype=torch.float32,
                                                 attn_implementation='eager')
    model.to(DEVICE)
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    end = model.generation_config.eos_token_id
    if end is None:
        end = tokenizer.eos_token_id
    end_ids = [int(end)] if isinstance(end, int) else [int(value) for value in (end or [])]
    if not end_ids:
        raise ValueError('NO_END_TOKEN_KNOWN')
    return torch, tokenizer, model, end_ids, getattr(model.config, 'max_position_embeddings', None)


def greedy_answer(torch, model, prompt_ids, end_ids, max_new_tokens):
    """The single most likely next token, again and again, until an end token or the cap. One prompt, no retry.

    Returns (the new token ids, cut_off). cut_off is true when the cap was reached with no end token.
    """
    ids = torch.tensor([prompt_ids], dtype=torch.long, device=DEVICE)
    new_ids, ended = [], False
    with torch.inference_mode():
        for _ in range(max_new_tokens):
            output = model(input_ids=ids, attention_mask=torch.ones_like(ids), use_cache=False,
                           logits_to_keep=1, return_dict=True)
            scores = output.logits[0, -1, :]
            if not bool(torch.isfinite(scores).all().item()):
                raise RuntimeError('NONFINITE_MODEL_SCORES')
            token = int(torch.argmax(scores).item())
            new_ids.append(token)
            if token in end_ids:
                ended = True
                break
            ids = torch.cat((ids, torch.tensor([[token]], dtype=torch.long, device=DEVICE)), dim=1)
    return new_ids, (not ended) and len(new_ids) >= max_new_tokens


def load_dry_build(out, selftest):
    """The padding plan and the prompt hash list of the self-test. Both must still have the recorded sha256."""
    with open(os.path.join(out, 'padding_plan.json'), 'rb') as handle:
        plan_bytes = handle.read()
    with open(os.path.join(out, 'prompt_hashes.jsonl'), 'rb') as handle:
        list_bytes = handle.read()
    if (plan.sha256_hex(plan_bytes) != selftest.get('padding_plan_sha256')
            or plan.sha256_hex(list_bytes) != selftest.get('prompt_list_sha256')):
        raise RuntimeError('DRY_BUILD_FILES_CHANGED_SINCE_THE_SELFTEST')
    dry = {}
    for line in list_bytes.split(b'\n'):
        if line.strip():
            row = json.loads(line.decode('utf-8'))
            dry[row['call_id']] = row
    return json.loads(plan_bytes.decode('utf-8')), dry


class CallMaker(object):
    """Makes model calls in the planned order and writes one flushed line per call."""

    def __init__(self, constants, engine, prompts, dry, lines, deadline_unix, calls_done):
        self.torch, self.tokenizer, self.model, self.end_ids, self.position_limit = engine
        self.prompts, self.dry, self.lines = prompts, dry, lines
        self.deadline_unix = deadline_unix
        self.calls_done = calls_done
        self.cap = constants['aws']['gpu_job']['call_cap']
        self.max_new_tokens = constants['decoding']['max_new_tokens']
        self.stop_cap, self.stop_cutoff = constants['run_stop_reasons']
        self.rows = []

    def run(self, calls):
        """Returns None when every call was made, or the name of the stop event."""
        for call in calls:
            if self.calls_done >= self.cap:
                return self.stop_cap
            if time.time() >= self.deadline_unix:      # checked before each call, against the work cutoff
                return self.stop_cutoff
            self.one(call)
            if self.calls_done % 100 == 0:
                print('calls done: %d (%s)' % (self.calls_done, call['step']))
                sys.stdout.flush()
        return None

    def one(self, call):
        started = time.perf_counter()
        task = self.prompts.tasks[call['task_id']]
        built = self.prompts.build(task, call['group'], call['level'], call['wording'])
        rendered = render(self.tokenizer, built['user_text'])
        digest = plan.sha256_hex(rendered.encode('utf-8'))
        facts = self.dry.get(call['call_id'])
        if facts is None or facts['prompt_sha256'] != digest:
            raise RuntimeError('PROMPT_HASH_IS_NOT_THE_DRY_BUILD_HASH ' + call['call_id'])
        prompt_ids = self.tokenizer.encode(rendered, add_special_tokens=False)
        if isinstance(self.position_limit, int) and len(prompt_ids) + self.max_new_tokens > self.position_limit:
            raise RuntimeError('PROMPT_DOES_NOT_FIT_THE_MODEL ' + call['call_id'])
        new_ids, cut_off = greedy_answer(self.torch, self.model, prompt_ids, self.end_ids, self.max_new_tokens)
        raw = self.tokenizer.decode(new_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        seconds = time.perf_counter() - started
        self.calls_done += 1
        row = {'call_id': call['call_id'], 'n': self.calls_done, 'phase': call['phase'], 'step': call['step'],
               'task_id': call['task_id'], 'passage_id': call['passage_id'], 'family': call['family'],
               'group': call['group'], 'level': call['level'], 'wording': call['wording'],
               'ord_length': built['ord_length'], 'padding_k': built['padding_k'], 'prompt': rendered,
               'prompt_sha256': digest, 'prompt_tokens': len(prompt_ids), 'notes_tokens': facts['notes_tokens'],
               'letters_shown': plan.letters_at(task, call['level']), 'raw_answer': raw,
               'answer_token_ids': [int(value) for value in new_ids], 'new_tokens': len(new_ids),
               'cut_off': bool(cut_off), 'seconds_text': '%.3f' % seconds, 'utc': plan.utc_now()}
        self.lines.add(row)
        self.rows.append(row)


# =============================================================================================
# Command 2: run-practice
# =============================================================================================

def cmd_run_practice(args):
    out = args.out
    status = StatusLog(out, 'run-practice')
    constants = read_json(os.path.join(args.package, 'PLAN_CONSTANTS.json'))
    selftest = read_json_or_none(os.path.join(out, 'selftest.json'))
    if not (isinstance(selftest, dict) and selftest.get('status') == constants['selftest_pass_status']
            and selftest.get('mode') == 'gate0'):
        status.event('SKIPPED_NO_SELFTEST_PASS', 0, 'selftest.json does not say %s in mode gate0'
                     % constants['selftest_pass_status'])
        return 0
    try:
        engine = load_model(constants, resolve_snapshot(args.model, constants))
    except GpuRequired:
        status.event(constants['runner_refusal_code'], 0, 'no CUDA GPU; this command refuses a CPU')
        return 0
    status.event('START', 0)
    parts = read_json(os.path.join(args.package, 'prompts', 'prompt_parts_practice.json'))
    keys = read_json(os.path.join(args.package, 'keys_practice', 'keys_practice.json'))['keys']
    padding_document, dry = load_dry_build(out, selftest)
    prompts = Prompts(constants, parts, padding_document)
    tasks = prompts.tasks
    lines = LineFile(out, 'calls_practice.jsonl')
    decisions = LineFile(out, 'practice_decisions.jsonl')
    maker = CallMaker(constants, engine, prompts, dry, lines, args.deadline_unix, 0)

    # P1: group NONE, level 1, every practice task, once under each closing wording.
    p1_calls = plan.practice_calls(constants, parts, 'P1')
    stopped = maker.run(p1_calls)
    if stopped is not None:
        status.event(stopped, maker.calls_done, 'during P1')
        return 0
    by_id, _ = plan.index_lines(maker.rows)
    clean_by_wording, _ = plan.p1_counts(p1_calls, by_id, tasks, keys)
    wording = plan.decide_wording(clean_by_wording)
    decisions.add({'after': 'P1', 'chosen_wording': wording, 'clean_by_wording': clean_by_wording})

    # P2: group NONE, level 2, every practice role-step task, under the chosen wording.
    p2_calls = plan.practice_calls(constants, parts, 'P2', chosen_wording=wording)
    stopped = maker.run(p2_calls)
    if stopped is not None:
        status.event(stopped, maker.calls_done, 'during P2')
        return 0
    by_id, _ = plan.index_lines(maker.rows)
    correct_by_level, plain_fact_correct, _ = plan.p2_counts(p1_calls, p2_calls, by_id, tasks, keys, wording)
    level, _, early = plan.decide_after_p2(constants, correct_by_level, plain_fact_correct)
    decisions.add({'after': 'P2', 'chosen_level': level, 'correct_by_level': correct_by_level,
                   'plain_fact_correct': plain_fact_correct, 'early_stop': early})

    # P3: every other condition at the chosen level. It does not start if Gate 2 or Gate 3 already fails.
    if early is None:
        stopped = maker.run(plan.practice_calls(constants, parts, 'P3', chosen_wording=wording, chosen_level=level))
        if stopped is not None:
            status.event(stopped, maker.calls_done, 'during P3')
            return 0
    lines.close()
    decisions.close()
    status.event('END', maker.calls_done, None if early is None else 'P3 not run: ' + early)
    return 0


# =============================================================================================
# Command 3: gate
# =============================================================================================

def cmd_gate(args):
    status = StatusLog(args.out, 'gate')
    status.event('START', calls_so_far(args.out))
    plan.gate_files(args.package, args.out, args.deadline_unix)
    status.event('END', calls_so_far(args.out))
    return 0


# =============================================================================================
# Command 4: run-final. It is given the constants file and the prompt folder. It opens no key file.
# =============================================================================================

def cmd_run_final(args):
    out = args.out
    status = StatusLog(out, 'run-final')
    constants = read_json(args.constants)
    gate = read_json_or_none(os.path.join(out, 'GATE.json'))
    if not (isinstance(gate, dict) and gate.get('go') is True):
        status.event('SKIPPED_NO_GO', calls_so_far(out), 'GATE.json does not say go')
        return 0
    selftest = read_json_or_none(os.path.join(out, 'selftest.json'))
    if not isinstance(selftest, dict):
        raise RuntimeError('SELFTEST_FILE_MISSING_BEFORE_FINAL_CALLS')
    level, wording, blocks = gate.get('chosen_level'), gate.get('chosen_wording'), gate.get('final_blocks')
    if (level not in (plan.LEVEL_EASY, plan.LEVEL_HARD) or wording not in plan.wording_numbers(constants)
            or not isinstance(blocks, list) or plan.BLOCK_MUST_RUN not in blocks):
        raise RuntimeError('GATE_FILE_SAYS_GO_BUT_IS_NOT_USABLE')
    try:
        engine = load_model(constants, resolve_snapshot(args.model, constants))
    except GpuRequired:
        status.event(constants['runner_refusal_code'], calls_so_far(out), 'no CUDA GPU; this command refuses a CPU')
        return 0
    parts = read_json(os.path.join(args.prompts, 'prompt_parts_final.json'))
    padding_document, dry = load_dry_build(out, selftest)
    prompts = Prompts(constants, parts, padding_document)
    # Block 1, must-run: every final task in the seeded order, its groups back to back.
    # Block 2: NO-PASSAGE on role-step tasks, only if GATE.json lists it.
    calls = plan.final_calls(constants, parts, level, wording, blocks)
    done_before = calls_so_far(out)
    lines = LineFile(out, 'calls_final.jsonl')
    maker = CallMaker(constants, engine, prompts, dry, lines, args.deadline_unix, done_before)
    status.event('START', done_before, '%d final calls planned in blocks %s' % (len(calls), ', '.join(blocks)))
    stopped = maker.run(calls)
    lines.close()
    status.event('END' if stopped is None else stopped, maker.calls_done)
    return 0


# =============================================================================================
# Command 5: score
# =============================================================================================

def cmd_score(args):
    import analysis_b1
    status = StatusLog(args.out, 'score')
    status.event('START', calls_so_far(args.out))
    document = analysis_b1.run(args.package, args.out, args.receipt_before, args.receipt_after)
    status.event('END', calls_so_far(args.out), 'outcome code ' + str(document.get('outcome_code')))
    return 0


# =============================================================================================
# The command line
# =============================================================================================

COMMANDS = {'selftest': cmd_selftest, 'run-practice': cmd_run_practice, 'gate': cmd_gate,
            'run-final': cmd_run_final, 'score': cmd_score}
NEEDED = {'selftest': ('mode', 'package', 'model', 'out'),
          'run-practice': ('package', 'model', 'out', 'deadline_unix'),
          'gate': ('package', 'out', 'deadline_unix'),
          'run-final': ('constants', 'prompts', 'model', 'out', 'deadline_unix'),
          'score': ('package', 'out')}


def build_parser():
    parser = argparse.ArgumentParser(prog='runner_b1.py',
                                     description='Option B job runner: selftest, run-practice, gate, run-final, score.')
    commands = parser.add_subparsers(dest='command')
    for name in ('selftest', 'run-practice', 'gate', 'run-final', 'score'):
        sub = commands.add_parser(name)
        sub.add_argument('--out', '--output-dir', '--out-dir', dest='out', help='the one output folder, work/run_b1')
        sub.add_argument('--check-args-only', dest='check_args_only', action='store_true',
                         help='read the arguments, print ARGS_OK, do nothing else')
        if name != 'run-final':
            sub.add_argument('--package', '--package-dir', dest='package', help='the unpacked package folder')
        if name in ('selftest', 'run-practice', 'run-final'):
            sub.add_argument('--model', '--model-dir', dest='model', help='the snapshot folder of model B')
        if name in ('run-practice', 'gate', 'run-final'):
            sub.add_argument('--deadline-unix', dest='deadline_unix', type=int, help='the work cutoff, in Unix seconds')
        if name == 'selftest':
            sub.add_argument('--mode', dest='mode', choices=('precheck', 'gate0'))
            sub.add_argument('--expect-prompt-list-sha256', dest='expect_prompt_list_sha256')
            sub.add_argument('--expect-padding-plan-sha256', dest='expect_padding_plan_sha256')
        if name == 'run-final':
            sub.add_argument('--constants', dest='constants', help='PLAN_CONSTANTS.json')
            sub.add_argument('--prompts', '--prompts-dir', dest='prompts', help='the folder prompts/ only; no key folder')
        if name == 'score':
            sub.add_argument('--model-receipt-before', '--model-pre', dest='receipt_before',
                             help='controller/MODEL_PRE.json')
            sub.add_argument('--model-receipt-after-calls', '--model-after', dest='receipt_after',
                             help='controller/MODEL_AFTER_CALLS.json')
    return parser


def main(argv=None):
    parser = build_parser()
    args, unused = parser.parse_known_args(argv)
    if args.command is None:
        parser.print_help()
        return 2
    if unused:
        print('NOTE: these arguments are not used by %s: %s' % (args.command, ' '.join(unused)), file=sys.stderr)
    missing = [name for name in NEEDED[args.command] if getattr(args, name, None) is None]
    if missing:
        parser.error('%s needs: %s' % (args.command, ', '.join('--' + name.replace('_', '-') for name in missing)))
    if args.check_args_only:
        print('ARGS_OK %s' % args.command)
        return 0
    try:
        return COMMANDS[args.command](args)
    except Exception as error:
        traceback.print_exc()
        try:
            if os.path.isdir(args.out):
                StatusLog(args.out, args.command).event('CRASH', calls_so_far(args.out),
                                                        '%s: %s' % (type(error).__name__, str(error)[:300]))
        except Exception:
            pass
        return 1


if __name__ == '__main__':
    sys.exit(main())
