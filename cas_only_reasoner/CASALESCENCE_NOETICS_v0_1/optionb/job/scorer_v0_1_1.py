"""Scorer for model B's answers, rules version 0.1.1.

The written rules are 03_SCORER_RULES_v0_1.md. Version 0.1.1 is the same rules with
ONE change (plan section 17.1, operator decision D10):

    A reply whose JSON object repeats a key is FORMAT_FAIL.

Why: version 0.1 read the reply with json.loads, which silently keeps the last of two
repeated keys. So {"answer": "A", "answer": "B"} was read as "B" and could be marked
CORRECT. Rule 5 says the reply must be one object with exactly one key.

Everything else is copied from tools/scorer_v0_1.py without a change of behaviour.

Status: SOURCE ONLY. Not run on the laptop. First exercised by the AWS pre-check job.
Standard library only. It loads no model. It is never told which group an answer came from.
"""
import json
import re

VERSION = '0.1.1'
CATEGORIES = ('CORRECT', 'WRONG', 'TYPE_MISMATCH', 'FORMAT_FAIL', 'CUT_OFF')
_ONE_FENCE = re.compile(r'^```([A-Za-z]*)\n(.*)\n```$', re.DOTALL)


class RepeatedKey(ValueError):
    """One JSON object held the same key twice."""


def _object_without_repeated_keys(pairs):
    """The json module calls this for every JSON object, with its (key, value) pairs in order."""
    out = {}
    for key, value in pairs:
        if key in out:
            raise RepeatedKey('REPEATED_KEY')
        out[key] = value
    return out


def _kind(value):
    """'int', 'str' or 'list' for an allowed value; None for anything else."""
    if type(value) is int:
        return 'int'
    if type(value) is str:
        return 'str' if 0 < len(value) <= 128 else None
    if type(value) is list:
        if len(value) <= 16 and all(type(item) is str and 0 < len(item) <= 128 for item in value):
            return 'list'
    return None


def read_answer(raw_text, cut_off=False):
    """Rules 1 to 6. Returns (category, value). The category is None when a value was read."""
    if cut_off:
        return 'CUT_OFF', None
    text = raw_text.strip()
    if '```' in text:
        match = _ONE_FENCE.match(text)
        if match is None or '```' in match.group(2):
            return 'FORMAT_FAIL', None
        text = match.group(2).strip()
    try:
        parsed = json.loads(text, object_pairs_hook=_object_without_repeated_keys)
    except (ValueError, RecursionError):
        # ValueError: not valid JSON, or a repeated key (the 0.1.1 change).
        # RecursionError: nesting too deep to read. Such a value is not an allowed value anyway (rule 6).
        return 'FORMAT_FAIL', None
    if type(parsed) is not dict or set(parsed) != {'answer'}:
        return 'FORMAT_FAIL', None
    if _kind(parsed['answer']) is None:
        return 'FORMAT_FAIL', None
    return None, parsed['answer']


def categorize(raw_text, task_answer, cut_off=False):
    """Rules 1 to 8: one of CATEGORIES."""
    if _kind(task_answer) is None:
        raise ValueError('TASK_ANSWER_NOT_AN_ALLOWED_VALUE')
    category, value = read_answer(raw_text, cut_off)
    if category is not None:
        return category
    if _kind(value) != _kind(task_answer):
        return 'TYPE_MISMATCH'
    return 'CORRECT' if value == task_answer else 'WRONG'


def primary_score(raw_text, task_answer, cut_off=False):
    return 1 if categorize(raw_text, task_answer, cut_off) == 'CORRECT' else 0


def secondary_category(raw_text, task_answer, cut_off=False):
    """Secondary view only: a string of digits is re-read as a whole number. No pass rule may use this."""
    category = categorize(raw_text, task_answer, cut_off)
    if category != 'TYPE_MISMATCH':
        return category
    _, value = read_answer(raw_text, cut_off)
    if type(value) is str and type(task_answer) is int and re.fullmatch(r'-?[0-9]+', value):
        return 'CORRECT' if int(value) == task_answer else 'WRONG'
    if type(value) is int and type(task_answer) is str and re.fullmatch(r'-?[0-9]+', task_answer):
        return 'CORRECT' if value == int(task_answer) else 'WRONG'
    return category


def tally(rows):
    """rows: iterable of (raw_text, task_answer, cut_off). Returns counts per category."""
    counts = {name: 0 for name in CATEGORIES}
    for raw_text, task_answer, cut_off in rows:
        counts[categorize(raw_text, task_answer, cut_off)] += 1
    return counts


# ---------------------------------------------------------------------------------------------
# Two terms the gates and the analysis use (plan section 14). They add no scoring rule.
# ---------------------------------------------------------------------------------------------

def clean_reply(raw_text, cut_off, letters_shown):
    """CLEAN REPLY: a value was read (rules 1 to 6), it is a string, and it is one of the letters shown.

    With a one-letter task answer this is the same as: scored CORRECT or WRONG, and the value is a shown letter.
    """
    category, value = read_answer(raw_text, cut_off)
    return category is None and type(value) is str and value in letters_shown


def not_clean_reply(raw_text, cut_off, letters_shown):
    """NOT CLEAN: everything else. FORMAT_FAIL, CUT_OFF, TYPE_MISMATCH, and a WRONG reply whose value
    is not one of the letters shown, such as "C. the smell of damp rope"."""
    return not clean_reply(raw_text, cut_off, letters_shown)


# ---------------------------------------------------------------------------------------------
# The known-example check (Gate 0).
# ---------------------------------------------------------------------------------------------

def check_known_examples(examples):
    """examples: the list under "examples" in the known-examples file.

    Returns (number that got the expected category, number of examples, list of failures).
    """
    failures = []
    for example in examples:
        try:
            got = categorize(example['raw_text'], example['task_answer'], example['cut_off'])
        except Exception as error:  # a broken example counts as a failure; it must not stop the check
            got = 'ERROR:' + type(error).__name__
        if got != example.get('expected'):
            failures.append({'id': example.get('id'), 'expected': example.get('expected'), 'got': got})
    return len(examples) - len(failures), len(examples), failures
