"""Option B job: the analysis program. It prints every number and exactly one outcome code.

WHAT IT DOES, IN ORDER
  1. Validity V1 to V3. One failure gives INVALID_RUN with its reasons.
  2. Readability R1 to R3. One trip gives that code; no gain or loss is read.
  3. Conditions C1 to C5 and the no-harm check H1 and H2 (HELD, NOT_HELD or NOT_MEASURABLE).
  4. One outcome code, in the checking order of the plan, with the _EXPLORATORY ending where the tier rule adds it.
  5. Extras that have no power to change the code: the number X, four fixed sub-views, tables per type,
     two-by-two tables against NONE, letter counts, near misses, the word-matching rule, the NO-PASSAGE score.
After a stop at a gate it writes the stop code and no table about final tasks.

THE TEST FOR "X BEATS Y" (plan section 13)
  The unit is the passage. d = (tasks CORRECT under X) minus (tasks CORRECT under Y), per passage.
  Sign flips: rng = random.Random(seed). For each of the 100,000 flips, r = rng.getrandbits(n) with n = number
  of passages (sorted by passage id; bit j belongs to passage j). A set bit flips that passage's sign.
  The flipped sum is (real sum) - 2 * (sum of d over the flipped passages). Whole numbers only.
  X beats Y when at most 5,000 flipped sums are at least the real sum.
  Range: rng = random.Random(seed). For each of the 10,000 resamples, rng.choices(passages, k=n).
  The resampled difference is 100 * (sum of d) / (sum of tasks), kept as a whole number of millionths of a point.
  The 95% range is the sorted values at index 250 and index 9749.
  The standard error is the standard deviation of the 10,000 resampled values. That is the bootstrap standard
  error. It is used as it stands: nothing divides it by the number of resamples, by the number of passages or
  by any other count (amendment A4). The standard deviation is taken in its plain form: the square root of the
  average squared distance of the 10,000 values from their average. range_numbers() shows the arithmetic.
  A fresh random source is made for every test and for every range.
  This is the one procedure. PLAN_CONSTANTS.json holds the same text under "tests" (random_source, flip_draw,
  range_95, standard_error), and plan section 13 states it. No numpy is used anywhere.

THE THREE WORD VIEWS (plan section 18; review round 1)
  Sub-view 4 (tasks where the word-matching rule does not pick the right option under ROLE), the word-matching
  rule's score per group, and the share of kept questions whose anchor words appear in each ordinary note need
  content() from tools/verdict.py. That file is in the job package. It is imported after its sha256 is checked.
  So the three views are worked out inside the job, and the pre-check runs their code on the made-up answer sets.

OPERATION COUNT (EXPECTED, not measured; the self-test measures the real seconds)
  One sign-flip test: 100,000 flips, each one getrandbits call plus one mask-and-count per distinct non-zero
  value of d (at most 6). That is at most about 1.5 million small steps, whatever the number of passages.
  One range: 10,000 resamples of n passages, n at most 156: at most 1.56 million draws.
  One full run: 47 sign-flip tests and about 56 ranges (9 comparisons in each of 5 views, 2 format-gap tests,
  9 no-harm ranges). At most about 7 * 10^7 flip steps and 9 * 10^7 draws. EXPECTED: 10 to 20 seconds.

NUMBERS
  Counts are whole numbers. A share is a pair [part, whole]. A decimal is text in a field ending in _text.
  A share with nothing below the line is the text "undefined". The result file is written with allow_nan=False.
  No float is written anywhere, so a not-a-number value can not appear.

Status: SOURCE ONLY. Not run on the laptop. First exercised by the AWS development test on a made-up package,
before seal step 1 (amendment A10), then by the AWS pre-check job
(in both, the runner's self-test runs this program on five made-up answer sets).
Pure standard library. It runs where torch, transformers and numpy are absent.
"""
import sys

sys.dont_write_bytecode = True  # the package folder is sealed: no __pycache__ may appear in it

import argparse
import hashlib
import importlib.util
import json
import math
import os
import random
import time
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import scorer_v0_1_1 as scorer
import gate_b1 as plan

SCHEMA_RESULT = 'casalescence/optionb/result/v1'
PROGRAM = 'job/analysis_b1.py'
SCALE = 1000000          # resampled differences are whole numbers of millionths of a point
UNDEFINED = plan.UNDEFINED

NONE, FILLER, ROLE, MIXED = plan.NONE, plan.FILLER, plan.ROLE, plan.MIXED
ORD_INFORMED, ORD_FREE, QUOTES_ONLY, NO_PASSAGE = plan.ORD_INFORMED, plan.ORD_FREE, plan.QUOTES_ONLY, plan.NO_PASSAGE

# The comparisons made in every view. The first six feed C1, C2, C3 and C5. The seventh feeds R3.
# The last two are always printed and have no rule.
TEST_PAIRS = ((ROLE, NONE), (ROLE, FILLER), (ROLE, ORD_INFORMED), (ROLE, ORD_FREE), (ROLE, MIXED),
              (ROLE, QUOTES_ONLY), (NONE, FILLER), (MIXED, QUOTES_ONLY), (MIXED, FILLER))

# Outcome codes. check_constants() stops the program if PLAN_CONSTANTS.json does not list every one of them.
CODE_INVALID = 'INVALID_RUN'
CODE_NO_HELP = 'NO_ROLE_HELP_SHOWN'
CODE_NOT_TIED = 'HELP_NOT_TIED_TO_CORRECT_ROLES'
CODE_NOT_ABOVE = 'ROLE_HELP_NOT_ABOVE_ORDINARY_HELP'
CODE_BREAKS = 'HELPS_BUT_BREAKS_RIGHT_ANSWERS'
CODE_NOT_MEASURED = 'BEATS_ORDINARY_HELP_NO_HARM_NOT_MEASURED'
CODE_POINTING = 'POINTING_BEATS_ORDINARY_HELP_ROLE_NAMES_NOT_SHOWN'
# The two fixed report sentences that go with a code. The key under report_sentences in PLAN_CONSTANTS.json
# carries the code's number. The codes are numbered 1 to 11, each number once (amendment A7): 7 and 10.
SENTENCE_KEY = {CODE_NOT_ABOVE: 'code_7', CODE_POINTING: 'code_10'}
SENTENCE_NO_HARM_RANGE = 'no_harm_range'

RECEIPT_STATUS = 'EXACT_FILE_MEMBERSHIP_AND_BYTES_VERIFIED'
SEAL_NAME = 'SEAL_OPTIONB.jsonl'
SEAL_STEPS_NEEDED = ('1_PLAN_AND_SOURCES', '2_ROLE_NOTES', '3A_PRACTICE_QUESTIONS_AND_KEYS', '3B_PRACTICE_SET_FIXED',
                     '3C_FINAL_QUESTIONS_AND_KEYS', '4_ORDINARY_NOTES', '5_PROMPT_PARTS_AND_REMOVAL_LOG', '6_PROGRAMS')
# The two steps that close a repair window (amendment A5; FILE_FORMATS.md section 15.2).
SEAL_STEP_FINAL_QUESTIONS = '3C_FINAL_QUESTIONS_AND_KEYS'   # no tool repair line may stand after this line
SEAL_STEP_PRECHECK = '7_PRECHECK'                           # no program repair line may stand after this line
SUB_VIEW_TYPES_LEFT_OUT = ('LAND', 'HABIT')   # sub-view 1 of plan section 18
NEAR_MISS_EDGE = ' \t\r\n()[]{}<>.:'          # brackets, dots, colons and spaces


def check_constants(constants):
    """Stops the program unless PLAN_CONSTANTS.json lists the outcome codes this program can print.

    Amendment A7: the codes are numbered 1 to 11 in the checking order, no number is used twice, and
    outcome_codes_count says 11. The two report sentences are looked up under the number of their code.
    The self-test runs this check, so a code, a number or a sentence that does not fit is found before any model call.
    """
    rows = constants['outcome_codes_in_checking_order']
    listed = [row['code'] for row in rows]
    numbers = [row.get('n') for row in rows]
    needed = [CODE_INVALID, constants['readability']['R1']['code'], constants['readability']['R2']['code'],
              constants['readability']['R3']['code'], CODE_NO_HELP, CODE_NOT_TIED, CODE_NOT_ABOVE, CODE_BREAKS,
              CODE_NOT_MEASURED, CODE_POINTING, constants['pass_code']]
    if (listed != needed or numbers != list(range(1, len(needed) + 1))
            or constants.get('outcome_codes_count') != len(needed) or constants['validity']['code'] != CODE_INVALID):
        raise ValueError('PLAN_CONSTANTS_OUTCOME_CODES_NOT_AS_EXPECTED')
    sentences = constants['report_sentences']
    for code, key in SENTENCE_KEY.items():
        if key != 'code_%d' % numbers[listed.index(code)] or not isinstance(sentences.get(key), str):
            raise ValueError('PLAN_CONSTANTS_REPORT_SENTENCES_NOT_AS_EXPECTED')
    if not isinstance(sentences.get(SENTENCE_NO_HARM_RANGE), str):
        raise ValueError('PLAN_CONSTANTS_REPORT_SENTENCES_NOT_AS_EXPECTED')
    for name in (NONE, FILLER, ROLE, MIXED, ORD_INFORMED, ORD_FREE, QUOTES_ONLY):
        if name not in constants['groups']['must_run_in_order']:
            raise ValueError('PLAN_CONSTANTS_GROUPS_NOT_AS_EXPECTED')
    if constants['groups']['tested_group'] != ROLE or constants['no_harm']['H2_yardstick'] != FILLER:
        raise ValueError('PLAN_CONSTANTS_GROUPS_NOT_AS_EXPECTED')


# =============================================================================================
# The package against the seal, the model-hash receipts, the frozen content() function
# =============================================================================================

def verdict_package_path(constants):
    """Where the frozen tools/verdict.py sits in the package (FILE_FORMATS.md section 14)."""
    return constants['seal']['verdict_program_package_path']


def package_files_needed(constants):
    """The package files of FILE_FORMATS.md section 14, except the seal file itself.

    tools/verdict.py is one of them (review round 1): three views that are always printed need its content().
    """
    return [constants['plan_file'], 'PLAN_CONSTANTS.json', 'FILE_FORMATS.md', verdict_package_path(constants),
            'job/runner_b1.py', 'job/' + os.path.basename(constants['scorer']['file']), 'job/gate_b1.py',
            'job/analysis_b1.py', 'job/' + os.path.basename(constants['scorer']['examples_file']),
            'prompts/prompt_parts_practice.json', 'prompts/prompt_parts_final.json',
            'keys_practice/keys_practice.json', 'keys_practice/task_meta_practice.json',
            'keys_final/keys_final.json', 'keys_final/task_meta_final.json']


def check_package_against_seal(package, constants):
    """Does every sealed package file sit in the package with the size and sha256 that are in force?

    THE HASH IN FORCE (FILE_FORMATS.md section 15.2, review round 1). A repair line (6R_PROGRAMS_REPAIRED or
    TR_TOOLS_REPAIRED) may list a path that an earlier line lists. Then the latest line gives the size and
    the sha256 in force. Only a repair line may do that. No repair line is line 1.

    THE REPAIR WINDOWS (amendment A5). A repair line outside its window makes the seal a problem here:
      - a 6R line stands after the line 6_PROGRAMS and never after a line 7_PRECHECK, and there are at most as
        many as the plan allows;
      - a TR line never stands after the line 3C_FINAL_QUESTIONS_AND_KEYS: from then on a final question exists.
    This is a check of the form of the seal file only. tools/ob_seal.py is the program that refuses to write such
    a line; it also reads the repair folder, the review record and the receipt of the failed pre-check. The job
    reads none of those.

    Files are hashed as bytes. Nothing is parsed, so hashing the final key file reveals no key.
    Returns {'ok', 'problems', 'files_checked', 'seal_lines', 'repair_lines', 'seal_sha256'}.
    """
    problems = []
    try:
        with open(os.path.join(package, SEAL_NAME), 'rb') as handle:
            raw = handle.read()
    except OSError as error:
        return {'ok': False, 'problems': ['the seal file cannot be read: %s' % type(error).__name__],
                'files_checked': 0, 'seal_lines': 0, 'repair_lines': 0, 'seal_sha256': None}
    repairs = constants['repairs']
    repair_of_programs = repairs['seal_steps']['job_programs']
    repair_of_tools = repairs['seal_steps']['tools']
    repair_steps = tuple(repairs['seal_steps'].values())   # a tuple: a step of any JSON type can be looked up in it
    lines = raw.split(b'\n')
    if lines and lines[-1] == b'':
        lines.pop()
    sealed, steps, previous = {}, [], None
    for number, line in enumerate(lines, 1):
        try:
            row = json.loads(line.decode('utf-8'))
        except ValueError:
            row = None
        if not isinstance(row, dict):
            problems.append('seal line %d is not a JSON object' % number)
            previous = hashlib.sha256(line).hexdigest()
            continue
        if row.get('n') != number:
            problems.append('seal line %d holds n=%r' % (number, row.get('n')))
        if row.get('previous_line_sha256') != previous:
            problems.append('seal line %d does not chain to the line before it' % number)
        previous = hashlib.sha256(line).hexdigest()
        step = row.get('step')
        is_repair = step in repair_steps
        if is_repair and number == 1:
            problems.append('seal line 1 is a repair line')
        if step == repair_of_programs and SEAL_STEPS_NEEDED[-1] not in steps:
            problems.append('seal line %d is a %s line before the line %s' % (number, step, SEAL_STEPS_NEEDED[-1]))
        # Amendment A5: each repair line has a window. A line after its window closed is a problem.
        if step == repair_of_programs and SEAL_STEP_PRECHECK in steps:
            problems.append('seal line %d is a %s line after the line %s: outside its window'
                            % (number, step, SEAL_STEP_PRECHECK))
        if step == repair_of_tools and SEAL_STEP_FINAL_QUESTIONS in steps:
            problems.append('seal line %d is a %s line after the line %s: outside its window'
                            % (number, step, SEAL_STEP_FINAL_QUESTIONS))
        steps.append(step)
        for entry in row.get('files') or []:
            if not isinstance(entry, dict) or entry.get('package_path') is None:
                continue
            target = entry.get('package_path')
            record = (entry.get('bytes'), entry.get('sha256'))
            if (not isinstance(target, str) or target == '' or target.startswith('/') or '\\' in target
                    or ':' in target or any(part in ('', '.', '..') for part in target.split('/'))):
                problems.append('the seal names an unsafe package path: %r' % (target,))
                continue
            if target in sealed and sealed[target] != record and not is_repair:
                problems.append('seal line %d names %s again with other content, and it is not a repair line'
                                % (number, target))
            sealed[target] = record   # the latest line gives the size and the sha256 in force
    for step in SEAL_STEPS_NEEDED:
        if step not in steps:
            problems.append('seal step %s is missing' % step)
    repair_lines = sum(1 for step in steps if step in repair_steps)
    if steps.count(repair_of_programs) > repairs['job_programs']['max_repairs']:
        problems.append('the seal holds %d %s lines; the plan allows %d' % (
            steps.count(repair_of_programs), repair_of_programs, repairs['job_programs']['max_repairs']))
    for name in package_files_needed(constants):
        if name not in sealed:
            problems.append('package file %s is not named in the seal' % name)
    # tools/verdict.py is a frozen source. The seal must name it with the size and sha256 pinned in the plan.
    pinned = constants['sources']['verdict_program']
    verdict_target = verdict_package_path(constants)
    if verdict_target in sealed and sealed[verdict_target] != (pinned['bytes'], pinned['sha256']):
        problems.append('the seal names %s with a size or sha256 that is not the one pinned in the plan'
                        % verdict_target)
    checked = 0
    for target in sorted(sealed):
        size, digest = sealed[target]
        try:
            with open(os.path.join(package, *target.split('/')), 'rb') as handle:
                data = handle.read()
        except OSError:
            problems.append('sealed package file %s is missing' % target)
            continue
        checked += 1
        if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
            problems.append('package file %s does not match the seal' % target)
    return {'ok': not problems, 'problems': problems, 'files_checked': checked, 'seal_lines': len(lines),
            'repair_lines': repair_lines, 'seal_sha256': hashlib.sha256(raw).hexdigest()}


def made_up_receipt(constants):
    """For the self-test only: a receipt in the guest's form that lists the pinned files."""
    snapshot = constants['model_b']['snapshot_path_in_payload']
    files = [{'path': snapshot.split('/', 1)[-1] + '/' + name, 'bytes': facts['bytes'], 'sha256': facts['sha256']}
             for name, facts in sorted(constants['model_b']['files'].items())]
    return {'status': RECEIPT_STATUS, 'root_role': 'models', 'files': files, 'file_count': len(files),
            'total_bytes': sum(row['bytes'] for row in files), 'made_up_for_self_test': True}


def check_receipts(before, after, constants):
    """Rule V2, the model part. Returns (ok, list of reasons, detail text)."""
    if not isinstance(before, dict) or not isinstance(after, dict):
        missing = [name for name, receipt in (('before the first call', before), ('after the last model call', after))
                   if not isinstance(receipt, dict)]
        return False, ['MODEL_HASH_RECEIPT_MISSING'], 'receipt missing or unreadable: ' + ', '.join(missing)
    pinned = constants['model_b']['files']
    problems = []
    for name, receipt in (('before', before), ('after', after)):
        if receipt.get('status') != RECEIPT_STATUS:
            problems.append('the receipt %s has status %r' % (name, receipt.get('status')))
        files = receipt.get('files')
        if not isinstance(files, list):
            problems.append('the receipt %s lists no files' % name)
            continue
        seen = {}
        for entry in files:
            if isinstance(entry, dict):
                base = str(entry.get('path', '')).replace('\\', '/').split('/')[-1]
                seen[base] = (entry.get('bytes'), entry.get('sha256'))
        for file_name in sorted(pinned):
            if seen.get(file_name) != (pinned[file_name]['bytes'], pinned[file_name]['sha256']):
                problems.append('the receipt %s does not show %s with the pinned size and sha256' % (name, file_name))
        if len(files) != len(pinned):
            problems.append('the receipt %s lists %d files, not %d' % (name, len(files), len(pinned)))
    if before.get('files') != after.get('files'):
        problems.append('the two receipts list different files or hashes')
    if problems:
        return False, ['MODEL_HASH_CHANGED'], '; '.join(problems[:8])
    return True, [], 'both receipts list the %d pinned files with the pinned sizes and hashes' % len(pinned)


def load_content_function(package, constants, verdict_path=None):
    """The three word views need content() from tools/verdict.py. That function is frozen:
    it is imported after its sha256 is checked, never copied. Returns (function or None, note).

    The file is in the job package at its sealed package path (review round 1), so the views are worked out
    inside the job and the pre-check runs their code. When the function can not be loaded, the note says why,
    and analyse() lists that under view_errors: the self-test then fails that made-up set. A fault here
    never stops the scoring and never changes the outcome code.
    """
    wanted = constants['sources']['verdict_program']['sha256']
    relative = verdict_package_path(constants)
    path = verdict_path if verdict_path else os.path.join(package, *relative.split('/'))
    where = 'the path given with --verdict-py' if verdict_path else 'the package path %s' % relative
    if not os.path.isfile(path):
        return None, 'content() NOT loaded: there is no file at %s; the three word views are not worked out' % where
    try:
        with open(path, 'rb') as handle:
            digest = hashlib.sha256(handle.read()).hexdigest()
        if digest != wanted:
            return None, ('content() NOT loaded: the sha256 of the file at %s is not the one pinned in the plan; '
                          'the three word views are not worked out' % where)
        spec = importlib.util.spec_from_file_location('frozen_verdict_program', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        function = module.content
    except Exception as error:
        return None, 'content() NOT loaded: %s: %s; the three word views are not worked out' % (
            type(error).__name__, str(error)[:200])
    return function, 'content() imported from the file at %s after its sha256 was checked' % where


# =============================================================================================
# The sign-flip test and the resampled range (pure standard library, whole numbers)
# =============================================================================================

if hasattr(int, 'bit_count'):
    def _ones(value):
        return value.bit_count()
else:
    def _ones(value):
        return bin(value).count('1')


def sign_flip_counts(d_values, flips, seed):
    """d_values: one whole number per passage, in passage-id order.

    Returns (flips whose flipped sum is at least the real sum,
             flips whose flipped sum is at least as far from zero as the real sum).
    """
    count = len(d_values)
    real = sum(d_values)
    if count == 0 or not any(d_values):
        return flips, flips            # every flipped sum is 0, and so is the real sum
    masks = {}
    for index, d in enumerate(d_values):
        if d != 0:
            masks[d] = masks.get(d, 0) | (1 << index)
    items = sorted(masks.items())
    far_line = abs(real)
    rng = random.Random(seed)
    at_least = far = 0
    for _ in range(flips):
        bits = rng.getrandbits(count)
        flipped_part = 0               # the sum of d over the passages whose sign is flipped
        for d, mask in items:
            flipped_part += d * _ones(bits & mask)
        flipped_sum = real - 2 * flipped_part
        if flipped_sum >= real:
            at_least += 1
        if abs(flipped_sum) >= far_line:
            far += 1
    return at_least, far


def bootstrap_points(pairs, resamples, seed):
    """pairs: one (d, tasks) per passage, tasks at least 1.

    Returns the sorted resampled differences, each 100 * sum(d) / sum(tasks) as a whole number of
    millionths of a point (rounded down). Returns None when there is no passage.
    """
    count = len(pairs)
    if count == 0:
        return None
    if any(tasks < 1 for _, tasks in pairs):
        raise ValueError('BOOTSTRAP_UNIT_WITHOUT_TASKS')
    offset = max(abs(d) for d, _ in pairs)
    big = count * max(tasks for _, tasks in pairs) + 1
    # One whole number per passage carries both d (shifted to be 0 or more) and the task count.
    codes = [(d + offset) * big + tasks for d, tasks in pairs]
    rng = random.Random(seed)
    values = []
    for _ in range(resamples):
        total = sum(rng.choices(codes, k=count))
        d_sum = total // big - count * offset
        task_sum = total % big
        values.append((100 * SCALE * d_sum) // task_sum)
    values.sort()
    return values


class TestConfig(object):
    def __init__(self, constants):
        tests = constants['tests']
        self.flips = int(tests['sign_flips'])
        self.p_max = int(tests['p_max_count_one_sided'])
        self.resamples = int(tests['bootstrap_resamples'])
        self.flip_seed = int(constants['seeds']['sign_flip_test'])
        self.boot_seed = int(constants['seeds']['bootstrap'])
        self.low_index = (self.resamples * 25) // 1000            # 250 of 10,000
        self.high_index = (self.resamples * 975) // 1000 - 1      # 9749 of 10,000
        self.upper_index = int(tests['one_sided_upper_95_index'])  # 9499 of 10,000
        for index in (self.low_index, self.high_index, self.upper_index):
            if not 0 <= index < self.resamples:
                raise ValueError('PLAN_CONSTANTS_RANGE_INDEX_OUT_OF_RANGE')


def range_numbers(values, config):
    """values: sorted resampled differences, in millionths of a point. Returns the range ends and the standard error.

    THE STANDARD ERROR (amendment A4) is the bootstrap standard error: the standard deviation of the resampled
    values themselves, in points. It is used as it stands. Nothing divides it by the number of resamples, by the
    number of passages or by any other count.

    The plain standard deviation is the square root of the average squared distance from the average. In whole
    numbers, with count values, their sum "total" and the sum of their squares "squares":
        average squared distance = (count * squares - total * total) / (count * count)
        standard deviation       = sqrt(count * squares - total * total) / count
    The "/ count" in the last line is the average inside the square root, brought outside it. It is not a second
    division. The square root is taken to three decimal places (10 ** 6 under the root, 1000 below the line)
    and rounded down. Dividing by SCALE turns millionths of a point into points.
    Hand check: the two values 1 point and 3 points give exactly 1 point.

    The three range ends are values picked from the sorted list. Nothing is divided there.
    """
    count = len(values)
    total = sum(values)
    squares = sum(value * value for value in values)
    spread = count * squares - total * total     # count * count * (average squared distance); never below zero
    standard_error = Fraction(math.isqrt(spread * 10 ** 6), count * 1000 * SCALE)   # the standard deviation, in points
    return {'low': values[config.low_index], 'high': values[config.high_index],
            'upper': values[config.upper_index], 'se': standard_error}


def scaled_text(value):
    return plan.fraction_text(Fraction(value, SCALE))


def range_texts(numbers):
    if numbers is None:
        return [UNDEFINED, UNDEFINED]
    return [scaled_text(numbers['low']), scaled_text(numbers['high'])]


def make_view(task_ids, tasks):
    by_passage = {}
    for task_id in task_ids:
        by_passage.setdefault(tasks[task_id]['passage_id'], []).append(task_id)
    return {'tasks': list(task_ids), 'passages': sorted(by_passage), 'by_passage': by_passage}


def compare(view, cells, x, y, field, config):
    """The passage-level test of group x against group y on one view. field is 'correct' or 'not_clean'."""
    d_values, pairs = [], []
    count_x = count_y = 0
    for passage_id in view['passages']:
        task_ids = view['by_passage'][passage_id]
        sum_x = sum(cells[(task_id, x)][field] for task_id in task_ids)
        sum_y = sum(cells[(task_id, y)][field] for task_id in task_ids)
        count_x += sum_x
        count_y += sum_y
        d_values.append(sum_x - sum_y)
        pairs.append((sum_x - sum_y, len(task_ids)))
    task_count = len(view['tasks'])
    at_least, far = sign_flip_counts(d_values, config.flips, config.flip_seed)
    values = bootstrap_points(pairs, config.resamples, config.boot_seed)
    numbers = range_numbers(values, config) if values is not None else None
    test = {'x': x, 'y': y, 'passages': len(view['passages']), 'tasks': task_count,
            'correct_x': count_x, 'correct_y': count_y, 'sum_d': count_x - count_y,
            'flips': config.flips, 'flips_at_least': at_least, 'two_sided_flips_at_least': far,
            'holds': at_least <= config.p_max,
            'difference_points_text': plan.points_text(count_x - count_y, task_count),
            'range95_points_text': range_texts(numbers),
            'se_points_text': plan.fraction_text(numbers['se']) if numbers is not None else UNDEFINED}
    return test, numbers


def missed_gain_points(standard_error, constants):
    """The number X: the larger of (2.485 * SE) and (5 + 0.84 * SE), rounded up to a whole point.

    SE is the bootstrap standard error from range_numbers(): the standard deviation of the resampled
    ROLE-minus-better-rival differences, in points. It is passed in as it stands (amendment A4).
    """
    rule = constants['missed_gain_x']
    value = max(Fraction(rule['factor_a']) * standard_error,
                rule['base_points'] + Fraction(rule['factor_b']) * standard_error)
    return -((-value.numerator) // value.denominator)


# =============================================================================================
# One reply, one cell
# =============================================================================================

def near_miss(category, clean, value, options):
    """A WRONG reply that is not clean, and is a shown letter with punctuation or a shown option's text."""
    if category != 'WRONG' or clean or type(value) is not str:
        return False
    letters = [option['letter'] for option in options]
    stripped = value.strip(NEAR_MISS_EDGE)
    if stripped and stripped[0] in letters and (len(stripped) == 1 or not stripped[1].isalpha()):
        return True
    lowered = value.strip().lower()
    return any(lowered == option['text'].strip().lower() for option in options)


def make_cell(line, key_letter, task, level):
    options = plan.options_at(task, level)
    letters = [option['letter'] for option in options]
    raw = line.get('raw_answer')
    cut_off = bool(line.get('cut_off'))
    if not isinstance(raw, str):
        raw = ''   # cannot happen with the runner's lines; an empty reply is FORMAT_FAIL
    category = scorer.categorize(raw, key_letter, cut_off)
    _, value = scorer.read_answer(raw, cut_off)
    clean = scorer.clean_reply(raw, cut_off, letters)
    return {'category': category, 'correct': 1 if category == 'CORRECT' else 0, 'clean': clean,
            'not_clean': 0 if clean else 1, 'letter': value if clean else None,
            'near_miss': near_miss(category, clean, value, options),
            'digit_view': scorer.secondary_category(raw, key_letter, cut_off)}


def build_cells(calls, by_id, tasks, keys):
    """(task id, group) -> cell, for every planned call that has an output line. Also the missing call ids."""
    cells, missing = {}, []
    for call in calls:
        line = by_id.get(call['call_id'])
        if line is None:
            missing.append(call['call_id'])
            continue
        task = tasks[call['task_id']]
        cells[(call['task_id'], call['group'])] = make_cell(line, keys[call['task_id']][str(call['level'])],
                                                            task, call['level'])
    return cells, missing


def group_table(task_ids, group, cells):
    row = {'tasks': len(task_ids), 'outputs': 0}
    for name in scorer.CATEGORIES:
        row[name] = 0
    row.update({'clean': 0, 'not_clean': 0, 'near_miss': 0})
    letters = {}
    for task_id in task_ids:
        cell = cells.get((task_id, group))
        if cell is None:
            continue
        row['outputs'] += 1
        row[cell['category']] += 1
        row['clean' if cell['clean'] else 'not_clean'] += 1
        if cell['near_miss']:
            row['near_miss'] += 1
        if cell['letter'] is not None:
            letters[cell['letter']] = letters.get(cell['letter'], 0) + 1
    row['letters'] = dict(sorted(letters.items()))
    return row


# =============================================================================================
# The analysis
# =============================================================================================

def analyse(constants, parts, keys, meta, rows, unreadable_lines, dry_hashes, prompt_list_ok, padding_plan,
            level, wording, blocks, receipt_before, receipt_after, package_check, content_function, content_note,
            dry_phase='final', padding_set='final', check_prompt_text=True):
    """Returns the body of RESULT.json for a run whose gate said go (kind OUTCOME).

    dry_hashes       call id -> prompt sha256 from prompt_hashes.jsonl, or None when that file is missing
    prompt_list_ok   False when prompt_hashes.jsonl no longer has the sha256 the self-test recorded
    dry_phase        'final'; the self-test passes 'practice' because its made-up final lines are practice tasks
    """
    check_constants(constants)
    config = TestConfig(constants)
    groups_c = constants['groups']
    must_run = list(groups_c['must_run_in_order'])
    ordinary = list(groups_c['ordinary'])
    tasks = dict((task['task_id'], task) for task in parts['tasks'])
    passages = dict((passage['passage_id'], passage) for passage in parts['passages'])
    role_ids = sorted(task_id for task_id in tasks if plan.is_role_step(tasks[task_id]))
    fact_ids = sorted(task_id for task_id in tasks if not plan.is_role_step(tasks[task_id]))
    family_ids = {'role_step': role_ids, 'plain_fact': fact_ids}
    view_errors = []

    def ids_with(group, family):
        return [task_id for task_id in family_ids[family] if group in tasks[task_id]['groups']]

    # ---- planned calls and the lines that exist -----------------------------------------------------
    must_calls = plan.final_calls(constants, parts, level, wording, [plan.BLOCK_MUST_RUN])
    no_passage_ran = plan.BLOCK_NO_PASSAGE in blocks
    extra_calls = plan.final_calls(constants, parts, level, wording, [plan.BLOCK_NO_PASSAGE]) if no_passage_ran else []
    # Every planned call needs a key that is one of the letters shown. A key file without one is a build
    # fault; the program stops with a clear message instead of scoring against a broken key.
    without_key = [call['call_id'] for call in must_calls + extra_calls
                   if not isinstance(keys.get(call['task_id']), dict)
                   or keys[call['task_id']].get(str(call['level'])) not in plan.letters_at(tasks[call['task_id']],
                                                                                            call['level'])]
    if without_key:
        raise ValueError('KEY_FILE_NOT_USABLE: %d planned call(s) have no key that is a shown letter; first: %s'
                         % (len(without_key), without_key[0]))
    by_id, repeated = plan.index_lines(rows)
    planned_ids = set(call['call_id'] for call in must_calls + extra_calls)
    unplanned = sum(1 for call_id in by_id if call_id not in planned_ids)
    cells, missing = build_cells(must_calls, by_id, tasks, keys)
    extra_cells, extra_missing = build_cells(extra_calls, by_id, tasks, keys)
    cells.update(extra_cells)

    # ---- V1: every planned must-run call has an output ----------------------------------------------
    v1 = (not missing) and repeated == 0 and len(must_calls) > 0

    # ---- V2: model hashes, package, prompt hashes -----------------------------------------------------
    receipts_ok, receipt_reasons, receipt_detail = check_receipts(receipt_before, receipt_after, constants)
    hash_problems = 0
    if dry_hashes is not None:
        for call in must_calls + extra_calls:
            line = by_id.get(call['call_id'])
            if line is None:
                continue
            dry_id = dry_phase + call['call_id'][len('final'):]
            recorded = line.get('prompt_sha256')
            good = isinstance(recorded, str) and dry_hashes.get(dry_id) == recorded
            if good and check_prompt_text:
                prompt = line.get('prompt')
                good = isinstance(prompt, str) and hashlib.sha256(prompt.encode('utf-8')).hexdigest() == recorded
            if not good:
                hash_problems += 1
    prompts_ok = dry_hashes is not None and hash_problems == 0 and prompt_list_ok is not False
    v2 = receipts_ok and package_check['ok'] and prompts_ok

    # ---- V3: no must-run group at format floor; the two task families are counted apart ---------------
    floor_percent = constants['validity']['format_floor_percent']
    format_floor, v3 = {}, True
    for group in must_run:
        format_floor[group] = {}
        for family in ('role_step', 'plain_fact'):
            ids = ids_with(group, family)
            if not ids:
                continue
            bad = sum(1 for task_id in ids if (task_id, group) in cells
                      and cells[(task_id, group)]['category'] in ('FORMAT_FAIL', 'CUT_OFF'))
            at_floor = 100 * bad > floor_percent * len(ids)
            format_floor[group][family] = {'format_fail_plus_cut_off': [bad, len(ids)], 'at_floor': at_floor}
            if at_floor:
                v3 = False

    found = set(receipt_reasons)
    if not v1:
        found.add('MISSING_FINAL_OUTPUTS')
    if not package_check['ok']:
        found.add('PACKAGE_DOES_NOT_MATCH_SEAL')
    if not prompts_ok:
        found.add('PROMPT_HASH_MISMATCH')
    if not v3:
        found.add('FORMAT_FLOOR')
    invalid_reasons = [reason for reason in constants['validity']['reasons'] if reason in found]
    if found and not invalid_reasons:
        raise ValueError('PLAN_CONSTANTS_VALIDITY_REASONS_NOT_AS_EXPECTED')

    # ---- sizes and the tier ----------------------------------------------------------------------------
    role_passages = sorted(set(tasks[task_id]['passage_id'] for task_id in role_ids))
    sizes = {'final_role_step_tasks': len(role_ids), 'final_plain_fact_tasks': len(fact_ids),
             'final_passages_with_a_role_step_task': len(role_passages)}
    tier = constants['tiers']['as_it_stands']
    small = (len(role_ids) < tier['final_role_step_tasks_min']
             or len(role_passages) < tier['final_passages_with_a_role_step_task_min'])

    # ---- the five category counts per group ---------------------------------------------------------------
    groups_out = {}
    for group in must_run:
        groups_out[group] = {}
        for family in ('role_step', 'plain_fact'):
            ids = ids_with(group, family)
            if ids:
                groups_out[group][family] = group_table(ids, group, cells)
    if no_passage_ran:
        groups_out[NO_PASSAGE] = {'role_step': group_table(role_ids, NO_PASSAGE, cells)}

    result = {
        'kind': 'OUTCOME', 'outcome_code': None, 'base_code': None, 'exploratory': False,
        'invalid_reasons': invalid_reasons, 'sizes': sizes, 'chosen': {'wording': wording, 'level': level},
        'final_blocks': list(blocks), 'groups': groups_out,
        'validity': {'V1': v1, 'V2': v2, 'V3': v3, 'format_floor': format_floor,
                     'details': {'planned_must_run_calls': len(must_calls), 'must_run_calls_without_output': len(missing),
                                 'planned_no_passage_calls': len(extra_calls),
                                 'no_passage_calls_without_output': len(extra_missing),
                                 'lines_repeating_a_call_id': repeated, 'lines_not_planned': unplanned,
                                 'lines_not_readable': unreadable_lines,
                                 'model_receipts': receipt_detail,
                                 'package_matches_seal': package_check['ok'],
                                 'package_problems': package_check['problems'][:10],
                                 'package_files_checked': package_check['files_checked'],
                                 'prompt_hash_list_present': dry_hashes is not None,
                                 'prompt_hash_list_unchanged_since_self_test': prompt_list_ok,
                                 'prompt_hash_problems': hash_problems,
                                 'prompt_text_rehashed': check_prompt_text}},
        'readability': {'R1': {'tripped': None}, 'R2': {'tripped': None}, 'R3': {'tripped': None}},
        'tests': {},
        'conditions': {'C1': None, 'C2': None, 'C3': None, 'C4': None, 'C5': None,
                       'better_rival': None, 'c2_margin_met': None},
        'no_harm': {'status': None, 'H1': None, 'H2': None, 'by_group': {}, 'sentence': None},
        'x_points': None, 'sentences': [], 'sub_views': {}, 'extra_views': {},
        'tier': {'rule': tier, 'smaller_than_the_as_it_stands_tier': small},
        'random_procedure': {'used': 'random.Random(seed) of the Python standard library; getrandbits for the sign '
                                     'flips; choices for the resamples; a fresh source for every test and range',
                             'plan_text': constants['tests'].get('random_source'),
                             # A recount uses the same Python version as the job (plan section 13).
                             'python_version': '%d.%d.%d' % tuple(sys.version_info[:3])},
        'word_views_note': content_note, 'view_errors': view_errors,
    }

    padding_average = None
    if isinstance(padding_plan, dict):
        padding_average = (padding_plan.get('average_padding_share') or {}).get(padding_set)
    result['extra_views']['padding_average'] = padding_average

    if not v1:
        # Outputs are missing. No comparison is worked out on a part of the tasks.
        result['base_code'] = result['outcome_code'] = CODE_INVALID
        result['no_harm']['note'] = 'not worked out: final outputs are missing'
        return result

    # ================= From here on every must-run cell exists. =================
    role_count = len(role_ids)

    def total(group, field='correct', ids=None):
        return sum(cells[(task_id, group)][field] for task_id in (role_ids if ids is None else ids))

    def tests_for_view(view):
        out, numbers = {}, {}
        for x, y in TEST_PAIRS:
            test, extra = compare(view, cells, x, y, 'correct', config)
            out['%s_beats_%s' % (x, y)] = test
            numbers[(x, y)] = extra
        return out, numbers

    main_view = make_view(role_ids, tasks)
    tests, test_numbers = tests_for_view(main_view)
    result['tests'] = tests

    def holds(x, y):
        return tests['%s_beats_%s' % (x, y)]['holds']

    # ---- readability ------------------------------------------------------------------------------------
    readability = constants['readability']
    shown = constants['levels'][str(level)]['options_shown']
    none_right = total(NONE)
    above = 100 * none_right > readability['R1']['above_percent'] * role_count
    # "below chance plus points" with k options: 100 * part * k < (100 + points * k) * whole
    below = 100 * none_right * shown < (100 + readability['R1']['below_chance_plus_points'] * shown) * role_count
    r1 = above or below
    result['readability']['R1'] = {'tripped': r1, 'none_correct': [none_right, role_count], 'options_shown': shown,
                                   'above_the_upper_line': above, 'below_chance_plus_points': below}

    role_not_clean = total(ROLE, 'not_clean')
    r2, r2_rows = False, {}
    for group in ordinary:
        other_not_clean = total(group, 'not_clean')
        gap = 100 * abs(role_not_clean - other_not_clean) > readability['R2']['points'] * role_count
        gap_test, _ = compare(main_view, cells, ROLE, group, 'not_clean', config)
        test_holds = gap_test['two_sided_flips_at_least'] <= config.p_max
        r2_rows[group] = {'not_clean_role': [role_not_clean, role_count],
                          'not_clean_other': [other_not_clean, role_count],
                          'role_minus_other_points_text': plan.points_text(role_not_clean - other_not_clean, role_count),
                          'gap_is_above_the_points_line': gap, 'flips': config.flips,
                          'two_sided_flips_at_least': gap_test['two_sided_flips_at_least'],
                          'two_sided_test_holds': test_holds, 'tripped': gap and test_holds}
        r2 = r2 or (gap and test_holds)
    result['readability']['R2'] = {'tripped': r2, 'by_group': r2_rows}

    filler_right = total(FILLER)
    drop = 100 * (none_right - filler_right) >= readability['R3']['points'] * role_count
    r3 = drop and holds(NONE, FILLER)
    result['readability']['R3'] = {'tripped': r3, 'none_correct': [none_right, role_count],
                                   'filler_correct': [filler_right, role_count],
                                   'filler_is_points_or_more_below_none': drop,
                                   'none_beats_filler': holds(NONE, FILLER)}

    # ---- the better rival, the margin, the number X ------------------------------------------------------
    role_right = total(ROLE)
    informed_right, free_right = total(ORD_INFORMED), total(ORD_FREE)
    better = ORD_INFORMED if informed_right >= free_right else ORD_FREE   # a tie goes to ORD-INFORMED
    better_right = informed_right if better == ORD_INFORMED else free_right
    margin = 100 * (role_right - better_right) >= constants['conditions']['C2_margin_points'] * role_count
    result['conditions']['better_rival'] = better
    result['conditions']['c2_margin_met'] = margin
    numbers = test_numbers[(ROLE, better)]
    x_points = missed_gain_points(numbers['se'], constants) if numbers is not None else None
    result['x_points'] = x_points

    # ---- the no-harm check ---------------------------------------------------------------------------------
    rule = constants['no_harm']
    fact_count = len(fact_ids)
    kept_base = [task_id for task_id in role_ids + fact_ids if cells[(task_id, NONE)]['correct']]
    kept_base_role = [task_id for task_id in kept_base if plan.is_role_step(tasks[task_id])]

    def units(task_ids):
        by_passage = {}
        for task_id in task_ids:
            by_passage.setdefault(tasks[task_id]['passage_id'], []).append(task_id)
        return [by_passage[passage_id] for passage_id in sorted(by_passage)]

    def h1(group):
        none_fact = total(NONE, ids=fact_ids)
        group_fact = total(group, ids=fact_ids)
        pairs = [(sum(cells[(task_id, NONE)]['correct'] - cells[(task_id, group)]['correct'] for task_id in unit),
                  len(unit)) for unit in units(fact_ids)]
        values = bootstrap_points(pairs, config.resamples, config.boot_seed)
        extra = range_numbers(values, config) if values is not None else None
        row = {'plain_fact_tasks': fact_count, 'correct_none': none_fact, 'correct_group': group_fact,
               'loss_points_text': plan.points_text(none_fact - group_fact, fact_count),
               'holds': 100 * (none_fact - group_fact) <= rule['H1_max_loss_points'] * fact_count,
               'loss_range95_points_text': range_texts(extra),
               'loss_one_sided_upper95_points_text': scaled_text(extra['upper']) if extra is not None else UNDEFINED}
        return row, extra

    def h2(group, base, scope):
        kept = total(group, ids=base)
        kept_filler = total(FILLER, ids=base)
        pairs = [(sum(cells[(task_id, group)]['correct'] - cells[(task_id, FILLER)]['correct'] for task_id in unit),
                  len(unit)) for unit in units(base)]
        values = bootstrap_points(pairs, config.resamples, config.boot_seed)
        extra = range_numbers(values, config) if values is not None else None
        return {'scope': scope, 'tasks_correct_under_none': len(base), 'kept': [kept, len(base)],
                'kept_under_filler': [kept_filler, len(base)],
                'kept_minus_filler_points_text': plan.points_text(kept - kept_filler, len(base)),
                'holds': 100 * (kept_filler - kept) <= rule['H2_max_gap_points'] * len(base),
                'kept_minus_filler_range95_points_text': range_texts(extra)}

    role_h1, role_h1_numbers = h1(ROLE)
    role_h2 = h2(ROLE, kept_base, 'both task families')
    measurable = (fact_count >= rule['not_measurable_if_final_plain_fact_tasks_below']
                  and len(kept_base) >= rule['not_measurable_if_final_tasks_correct_under_none_below'])
    if not measurable:
        no_harm_status = 'NOT_MEASURABLE'
    elif role_h1['holds'] and role_h2['holds']:
        no_harm_status = 'HELD'
    else:
        no_harm_status = 'NOT_HELD'
    if no_harm_status not in rule['values']:
        raise ValueError('PLAN_CONSTANTS_NO_HARM_VALUES_NOT_AS_EXPECTED')
    sentence, loss_upper = None, None
    if role_h1_numbers is not None:
        upper = Fraction(role_h1_numbers['upper'], SCALE)
        loss_upper = max(0, -((-upper.numerator) // upper.denominator))   # rounded up to a whole point, never below 0
        sentence = constants['report_sentences'][SENTENCE_NO_HARM_RANGE].replace('<<X>>', str(loss_upper))
    by_group = {ROLE: {'H1': role_h1, 'H2': role_h2}}
    for group in rule['also_printed_for']:
        if group == QUOTES_ONLY:
            by_group[group] = {'H1': None, 'H1_note': 'QUOTES-ONLY has no plain-fact tasks',
                               'H2': h2(group, kept_base_role, 'role-step tasks only')}
        else:
            by_group[group] = {'H1': h1(group)[0], 'H2': h2(group, kept_base, 'both task families')}
    result['no_harm'] = {'status': no_harm_status, 'H1': role_h1, 'H2': role_h2, 'by_group': by_group,
                         'sentence': sentence, 'loss_upper_points': loss_upper,
                         'measurable': {'final_plain_fact_tasks': fact_count,
                                        'final_tasks_correct_under_none': len(kept_base),
                                        'enough': measurable}}

    # ---- the one outcome code, in the checking order of the plan -----------------------------------------
    conditions = result['conditions']
    if invalid_reasons:
        base = CODE_INVALID
    elif r1:
        base = readability['R1']['code']
    elif r2:
        base = readability['R2']['code']
    elif r3:
        base = readability['R3']['code']
    else:
        conditions['C1'] = holds(ROLE, NONE) and holds(ROLE, FILLER)
        if not conditions['C1']:
            base = CODE_NO_HELP
        else:
            conditions['C3'] = holds(ROLE, MIXED)
            if not conditions['C3']:
                base = CODE_NOT_TIED
            else:
                conditions['C2'] = holds(ROLE, ORD_INFORMED) and holds(ROLE, ORD_FREE) and margin
                if not conditions['C2']:
                    base = CODE_NOT_ABOVE
                else:
                    conditions['C4'] = no_harm_status == 'HELD'
                    if no_harm_status == 'NOT_MEASURABLE':
                        base = CODE_NOT_MEASURED
                    elif no_harm_status == 'NOT_HELD':
                        base = CODE_BREAKS
                    else:
                        conditions['C5'] = holds(ROLE, QUOTES_ONLY)
                        base = constants['pass_code'] if conditions['C5'] else CODE_POINTING
    tiers = constants['tiers']
    exploratory = small and base in tiers['suffix_applies_to']
    result['base_code'] = base
    result['exploratory'] = exploratory
    result['outcome_code'] = base + tiers['exploratory_suffix'] if exploratory else base
    fixed_sentences = constants['report_sentences']
    if base == CODE_NOT_ABOVE and x_points is not None:      # code 7; X comes from the bootstrap standard error
        result['sentences'].append(fixed_sentences[SENTENCE_KEY[CODE_NOT_ABOVE]].replace('<<X>>', str(x_points)))
    if base == CODE_POINTING:                                # code 10 (amendment A7: its key was code_9 before)
        result['sentences'].append(fixed_sentences[SENTENCE_KEY[CODE_POINTING]])

    # ================= Extras. They can not change the code. Each one is guarded on its own. =================
    if content_function is None:
        # The three word views are always printed (plan section 18). A run that can not work them out has
        # an error in its views. It is listed, so the self-test fails that made-up set before any model call.
        # The outcome code is fixed above this line and is not touched.
        view_errors.append('word views: %s' % (content_note,))

    def guarded(name, function):
        try:
            return function()
        except Exception as error:
            view_errors.append('%s: %s: %s' % (name, type(error).__name__, error))
            return {'error': '%s: %s' % (type(error).__name__, error)}

    chosen_length = {}
    if isinstance(padding_plan, dict):
        for entry in padding_plan.get('passages') or []:
            chosen_length[entry.get('passage_id')] = entry.get('ord_length_chosen') or {}

    def notes_text(task_id, group):
        passage_id = tasks[task_id]['passage_id']
        notes = passages[passage_id]['notes'][group]
        if isinstance(notes, dict):
            return notes[chosen_length[passage_id][group]]
        return notes

    def word_pick(task_id, group):
        """The word-matching rule: the one option that shares most content words with the notes, or None."""
        task = tasks[task_id]
        options = plan.options_at(task, plan.level_used(task, level))
        note_words = set(content_function(notes_text(task_id, group)))
        scores = [len(set(content_function(option['text'])) & note_words) for option in options]
        best = max(scores)
        if scores.count(best) != 1:
            return None
        return options[scores.index(best)]['letter']

    def right_letter(task_id):
        return keys[task_id][str(plan.level_used(tasks[task_id], level))]

    def sub_view(task_ids):
        view = make_view(task_ids, tasks)
        return {'sizes': {'tasks': len(view['tasks']), 'passages': len(view['passages'])},
                'tests': tests_for_view(view)[0]}

    def word_misses_view():
        if content_function is None:
            return {'available': False, 'note': content_note}
        out = sub_view([task_id for task_id in role_ids if word_pick(task_id, ROLE) != right_letter(task_id)])
        out['available'] = True
        return out

    result['sub_views'] = {
        'without_LAND_and_HABIT': guarded('sub_view without_LAND_and_HABIT', lambda: sub_view(
            [task_id for task_id in role_ids if meta[task_id]['type'] not in SUB_VIEW_TYPES_LEFT_OUT])),
        'type_without_leftover': guarded('sub_view type_without_leftover', lambda: sub_view(
            [task_id for task_id in role_ids if meta[task_id]['type_has_leftover'] is False])),
        'passage_without_leftover': guarded('sub_view passage_without_leftover', lambda: sub_view(
            [task_id for task_id in role_ids if meta[task_id]['passage_any_leftover_2_to_9'] is False])),
        'word_rule_misses_under_ROLE': guarded('sub_view word_rule_misses_under_ROLE', word_misses_view),
    }

    def word_matching_view():
        if content_function is None:
            return {'available': False, 'note': content_note}
        out = {'available': True}
        for group in must_run:
            if group not in groups_c['groups_with_a_notes_block']:
                continue
            out[group] = {}
            for family in ('role_step', 'plain_fact'):
                ids = ids_with(group, family)
                if not ids:
                    continue
                right = wrong = nothing = 0
                for task_id in ids:
                    picked = word_pick(task_id, group)
                    if picked is None:
                        nothing += 1
                    elif picked == right_letter(task_id):
                        right += 1
                    else:
                        wrong += 1
                out[group][family] = {'picks_the_right_option': [right, len(ids)], 'picks_a_wrong_option': wrong,
                                      'picks_nothing': nothing}
        return out

    def anchor_view():
        if content_function is None:
            return {'available': False, 'note': content_note}
        out = {'available': True}
        for group in ordinary:
            hits = 0
            for task_id in role_ids:
                note_words = set(content_function(notes_text(task_id, group)))
                for anchor in meta[task_id]['anchors_matched']:
                    words = content_function(anchor)
                    if words and 2 * sum(1 for word in words if word in note_words) >= len(words):
                        hits += 1
                        break
            out[group] = [hits, role_count]
        return out

    def no_passage_view():
        if not no_passage_ran:
            return {'ran': False}
        table = group_table(role_ids, NO_PASSAGE, cells)
        return {'ran': True, 'correct': [table['CORRECT'], table['tasks']], 'outputs': table['outputs'],
                'correct_points_text': plan.points_text(table['CORRECT'], table['tasks'])}

    def by_type_view():
        out = {}
        for task_id in role_ids + fact_ids:
            kind = meta[task_id]['type']
            for group in tasks[task_id]['groups']:
                pair = out.setdefault(kind, {}).setdefault(group, [0, 0])
                pair[0] += cells[(task_id, group)]['correct']
                pair[1] += 1
        return dict((kind, out[kind]) for kind in sorted(out))

    def two_by_two_view():
        out = {}
        for group in must_run:
            if group == NONE:
                continue
            out[group] = {}
            for family in ('role_step', 'plain_fact'):
                ids = ids_with(group, family)
                if not ids:
                    continue
                table = {'both_correct': 0, 'none_only': 0, 'group_only': 0, 'neither': 0}
                for task_id in ids:
                    with_none = cells[(task_id, NONE)]['correct']
                    with_group = cells[(task_id, group)]['correct']
                    if with_none and with_group:
                        table['both_correct'] += 1
                    elif with_none:
                        table['none_only'] += 1
                    elif with_group:
                        table['group_only'] += 1
                    else:
                        table['neither'] += 1
                out[group][family] = table
        return out

    def digit_view():
        out = {}
        for group in must_run:
            out[group] = {}
            for family in ('role_step', 'plain_fact'):
                ids = ids_with(group, family)
                if not ids:
                    continue
                counts = dict((name, 0) for name in scorer.CATEGORIES)
                for task_id in ids:
                    counts[cells[(task_id, group)]['digit_view']] += 1
                out[group][family] = counts
        return out

    def not_clean_gap_view():
        out = {}
        for group in must_run:
            other = total(group, 'not_clean')
            out[group] = {'not_clean': [other, role_count],
                          'group_minus_role_points_text': plan.points_text(other - role_not_clean, role_count)}
        return out

    extra_views = result['extra_views']
    extra_views['word_matching_rule'] = guarded('word_matching_rule', word_matching_view)
    extra_views['anchor_in_ordinary_note'] = guarded('anchor_in_ordinary_note', anchor_view)
    extra_views['no_passage'] = guarded('no_passage', no_passage_view)
    extra_views['by_type'] = guarded('by_type', by_type_view)
    extra_views['two_by_two_vs_NONE'] = guarded('two_by_two_vs_NONE', two_by_two_view)
    extra_views['digit_view'] = guarded('digit_view', digit_view)
    extra_views['not_clean_gap_from_ROLE'] = guarded('not_clean_gap_from_ROLE', not_clean_gap_view)
    return result


def stop_result(constants, gate, selftest, run_status):
    """The gate did not say go. The result holds the stop code and no table about final tasks."""
    stop_codes = constants['stop_codes']
    gate = gate if isinstance(gate, dict) else {}
    selftest = selftest if isinstance(selftest, dict) else {}
    if gate.get('stop_code') in stop_codes:
        code, reason = gate['stop_code'], 'GATE.json holds this stop code'
    elif selftest.get('status') in stop_codes:
        code, reason = selftest['status'], 'selftest.json holds this stop code and there is no usable GATE.json'
    else:
        code = plan.SELFTEST_STOP
        reason = ('there is no usable GATE.json and no stop code in selftest.json; '
                  'this is reported as a failed check before any final call')
    return {'kind': 'STOP', 'outcome_code': code, 'base_code': code, 'exploratory': False,
            'stop_details': {'reason': reason, 'gate_file_present': bool(gate), 'gate_go': gate.get('go'),
                             'gate_stop_code': gate.get('stop_code'),
                             'first_failing_gate': gate.get('first_failing_gate'), 'gate_detail': gate.get('detail'),
                             'selftest_status': selftest.get('status'), 'selftest_mode': selftest.get('mode'),
                             'run_status_events': ['%s:%s' % (row.get('command'), row.get('event'))
                                                   for row in run_status][:60]}}


# =============================================================================================
# Reading the files, writing RESULT.json
# =============================================================================================

def default_receipt_path(out, name):
    """Used only when no receipt path is given: the controller folder beside the output folder, or one level up."""
    beside = os.path.join(out, os.pardir, 'controller', name)
    if os.path.isfile(beside):
        return beside
    return os.path.join(out, os.pardir, os.pardir, 'controller', name)


def run(package, out, receipt_before_path=None, receipt_after_path=None, trial=None, verdict_path=None,
        result_name='RESULT.json', quiet=False):
    """Real run: trial is None; reads GATE.json, the final call lines, the final keys and the two receipts.

    Self-test trial: trial = {'calls_name', 'result_name', 'level', 'wording'}. Then the practice tasks are
    treated as if they were final tasks, with two equal made-up receipts, and the gate file is not read.
    Returns the document that was written.
    """
    started = time.perf_counter()
    inputs = plan.Inputs()
    constants = inputs.read_json(os.path.join(package, 'PLAN_CONSTANTS.json'), 'package/PLAN_CONSTANTS.json')
    document = {'schema': SCHEMA_RESULT, 'made_by': plan.made_by(PROGRAM, os.path.abspath(__file__)),
                'inputs': inputs.items}

    def finish(body):
        document.update(body)
        document['seconds_text'] = '%.2f' % (time.perf_counter() - started)
        plan.create_once(out, result_name, plan.dump_json(document))
        if quiet:
            print('ANALYSIS %s -> %s (%s seconds)' % (result_name, document['outcome_code'], document['seconds_text']))
        else:
            print_report(document)
        sys.stdout.flush()
        return document

    if trial is None:
        selftest = inputs.read_json_or_none(os.path.join(out, 'selftest.json'), 'out/selftest.json')
        gate = inputs.read_json_or_none(os.path.join(out, 'GATE.json'), 'out/GATE.json')
        run_status, _ = inputs.read_jsonl(os.path.join(out, 'run_status.jsonl'), 'out/run_status.jsonl')
        usable = (isinstance(gate, dict) and gate.get('go') is True
                  and gate.get('chosen_level') in (plan.LEVEL_EASY, plan.LEVEL_HARD)
                  and gate.get('chosen_wording') in plan.wording_numbers(constants)
                  and isinstance(gate.get('final_blocks'), list) and plan.BLOCK_MUST_RUN in gate['final_blocks'])
        if not usable:
            return finish(stop_result(constants, gate, selftest, run_status))
        set_name, calls_name = 'final', 'calls_final.jsonl'
        level, wording, blocks = gate['chosen_level'], gate['chosen_wording'], gate['final_blocks']
        keys_folder = 'keys_final'
        dry_phase, check_prompt_text = 'final', True
        if receipt_before_path is None:
            receipt_before_path = default_receipt_path(out, 'MODEL_PRE.json')
        if receipt_after_path is None:
            receipt_after_path = default_receipt_path(out, 'MODEL_AFTER_CALLS.json')
        receipt_before = inputs.read_json_or_none(receipt_before_path, 'controller/MODEL_PRE.json')
        receipt_after = inputs.read_json_or_none(receipt_after_path, 'controller/MODEL_AFTER_CALLS.json')
    else:
        selftest = None
        set_name, calls_name, result_name = 'practice', trial['calls_name'], trial['result_name']
        level, wording = trial['level'], trial['wording']
        blocks = [plan.BLOCK_MUST_RUN, plan.BLOCK_NO_PASSAGE]
        keys_folder = 'keys_practice'
        dry_phase, check_prompt_text = 'practice', False
        receipt_before = made_up_receipt(constants)
        receipt_after = made_up_receipt(constants)

    parts = inputs.read_json(os.path.join(package, 'prompts', 'prompt_parts_%s.json' % set_name),
                             'package/prompts/prompt_parts_%s.json' % set_name)
    keys = inputs.read_json(os.path.join(package, keys_folder, 'keys_%s.json' % set_name),
                            'package/%s/keys_%s.json' % (keys_folder, set_name))['keys']
    meta = inputs.read_json(os.path.join(package, keys_folder, 'task_meta_%s.json' % set_name),
                            'package/%s/task_meta_%s.json' % (keys_folder, set_name))['tasks']
    rows, unreadable = inputs.read_jsonl(os.path.join(out, calls_name), 'out/' + calls_name)

    dry_hashes, prompt_list_ok = None, None
    try:
        dry_bytes = inputs.read_bytes(os.path.join(out, 'prompt_hashes.jsonl'), 'out/prompt_hashes.jsonl')
    except OSError:
        dry_bytes = None
    if dry_bytes is not None:
        dry_hashes = {}
        for line in dry_bytes.split(b'\n'):
            if not line.strip():
                continue
            try:
                row = json.loads(line.decode('utf-8'))
                dry_hashes[row['call_id']] = row['prompt_sha256']
            except (ValueError, KeyError, TypeError):
                dry_hashes = None    # a broken line: the dry build can not be trusted
                break
        if isinstance(selftest, dict):
            prompt_list_ok = selftest.get('prompt_list_sha256') == hashlib.sha256(dry_bytes).hexdigest()
    padding_plan = inputs.read_json_or_none(os.path.join(out, 'padding_plan.json'), 'out/padding_plan.json')
    package_check = check_package_against_seal(package, constants)
    if package_check['seal_sha256'] is not None:
        inputs.note('package/' + SEAL_NAME, package_check['seal_sha256'])
    content_function, content_note = load_content_function(package, constants, verdict_path)

    body = analyse(constants, parts, keys, meta, rows, unreadable, dry_hashes, prompt_list_ok, padding_plan,
                   level, wording, blocks, receipt_before, receipt_after, package_check,
                   content_function, content_note, dry_phase=dry_phase, padding_set=set_name,
                   check_prompt_text=check_prompt_text)
    return finish(body)


def print_report(document):
    """Prints the outcome code first, then a short summary, then every number (the whole result as JSON)."""
    print('OUTCOME_CODE %s' % document['outcome_code'])
    print('kind: %s   base code: %s   exploratory: %s' % (document['kind'], document['base_code'],
                                                         document['exploratory']))
    if document['kind'] == 'OUTCOME':
        print('sizes: %s' % json.dumps(document['sizes'], sort_keys=True))
        print('chosen: %s   validity: V1 %s, V2 %s, V3 %s   invalid reasons: %s' % (
            json.dumps(document['chosen'], sort_keys=True), document['validity']['V1'], document['validity']['V2'],
            document['validity']['V3'], ', '.join(document['invalid_reasons']) or 'none'))
        for name in sorted(document['tests']):
            test = document['tests'][name]
            print('test %-28s holds %-5s  correct %d vs %d of %d tasks on %d passages  flips at least %d of %d  '
                  'difference %s points, 95%% range %s to %s' % (
                      name, test['holds'], test['correct_x'], test['correct_y'], test['tasks'], test['passages'],
                      test['flips_at_least'], test['flips'], test['difference_points_text'],
                      test['range95_points_text'][0], test['range95_points_text'][1]))
        print('conditions: %s' % json.dumps(document['conditions'], sort_keys=True))
        print('no-harm: %s   %s' % (document['no_harm'].get('status'), document['no_harm'].get('sentence') or ''))
        print('X (points): %s' % document['x_points'])
        for sentence in document['sentences']:
            print(sentence)
        if document.get('view_errors'):
            print('extra views with an error: %s' % '; '.join(document['view_errors']))
    else:
        print('stop details: %s' % json.dumps(document['stop_details'], sort_keys=True))
    print('--- every number: the result file follows ---')
    print(json.dumps(document, indent=1, ensure_ascii=True, allow_nan=False))
    print('OUTCOME_CODE %s' % document['outcome_code'])


def main(argv=None):
    parser = argparse.ArgumentParser(description='Option B analysis. Writes the result file once.')
    parser.add_argument('--package', '--package-dir', dest='package', required=True)
    parser.add_argument('--out', '--output-dir', dest='out', required=True)
    parser.add_argument('--model-receipt-before', '--model-pre', dest='before', default=None)
    parser.add_argument('--model-receipt-after-calls', '--model-after', dest='after', default=None)
    parser.add_argument('--verdict-py', dest='verdict', default=None,
                        help='not needed in the job: the package holds tools/verdict.py. Another copy of that file, '
                             'for when a result is worked out again later; its sha256 must be the pinned one')
    parser.add_argument('--result-name', dest='result_name', default='RESULT.json',
                        help='a new file name when the result is worked out again beside an existing RESULT.json')
    args = parser.parse_args(argv)
    run(args.package, args.out, args.before, args.after, verdict_path=args.verdict, result_name=args.result_name)
    return 0


if __name__ == '__main__':
    sys.exit(main())
