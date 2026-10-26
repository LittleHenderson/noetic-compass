"""Scorer for model B's answers, rules version 0.1 (see 03_SCORER_RULES_v0_1.md).

Status: SOURCE ONLY, NOT RUN, NOT REVIEWED. Standard library only; loads no model.
It never knows which group an answer came from.
"""
import json
import re

CATEGORIES = ('CORRECT', 'WRONG', 'TYPE_MISMATCH', 'FORMAT_FAIL', 'CUT_OFF')
_ONE_FENCE = re.compile(r'^```([A-Za-z]*)\n(.*)\n```$', re.DOTALL)


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
    """Rules 1 to 6. Returns (category, value): category is None when a value was read."""
    if cut_off:
        return 'CUT_OFF', None
    text = raw_text.strip()
    if '```' in text:
        match = _ONE_FENCE.match(text)
        if match is None or '```' in match.group(2):
            return 'FORMAT_FAIL', None
        text = match.group(2).strip()
    try:
        parsed = json.loads(text)
    except ValueError:
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
