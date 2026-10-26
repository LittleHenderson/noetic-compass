"""[MADE-UP DATA WALK, NOT A RESULT] A stand-in for the outside services, inside the walk only.

guard_run.py puts urlopen() of this module in the place of urllib.request.urlopen before it runs a
tool. So a tool that "calls a service" gets a made-up reply from this file. Nothing leaves the laptop.
The reply has the envelope of an OpenAI-style chat reply (choices[0].message.content, model, usage),
which is what the four tools read.

What the made-up services do:
  question writer   one object per fenced passage: three what-follows questions and one plain-fact question
  key solver        with the passage: the right letter. Without the passage: a wrong letter.
  note writer       a made-up note of about the asked number of words
  support checker   PASS, or FAIL when the note holds the made-up marker sentence

Modes for probes, read from the environment variable WALK_STUB_MODE (comma list):
  http429_daily   every call is refused with HTTP 429 and an error text that names the daily limit
  http429_rate    every call is refused with HTTP 429 and an error text that names no daily limit
  no_usage        the reply carries no token count
  huge_usage      the reply says it used 3,000,000 input tokens
  no_model        the reply carries no model name
WALK_PASS (p1 or p2) tells the made-up question writer which pass it is in.
"""
import io
import json
import os
import re
import threading
import urllib.error
from pathlib import Path

import walk_fixture as F

HERE = Path(__file__).resolve().parent
LF = chr(10)
MADE_UP_KEY = 'MADE-UP-NOT-A-KEY'
NAMES = {'writer': 'made-up-writer-reply-name', 'solver': 'made-up-solver-reply-name', 'notes': 'made-up-note-writer-reply-name',
         'checker': 'made-up-checker-reply-name'}
_lock = threading.Lock()
_table = None
_by_question = None
_by_text = None


def _load():
    global _table, _by_question, _by_text
    if _table is None:
        _table = F.load_table()['passages']
        _by_question, _by_text = {}, {}
        for pid, p in _table.items():
            _by_text[F.passage_text(p)] = p
            for make in (F.question_goes_for, F.question_keeps_away, F.question_long_break, F.question_fact):
                q = make(p)
                _by_question[q['question']] = (p, q)
    return _table


def _log(row):
    with _lock:
        with open(HERE / 'logs' / 'stub_calls.jsonl', 'a', encoding='utf-8', newline=LF) as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + LF)


class _Reply:
    def __init__(self, payload):
        self.status, self._payload = 200, payload

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _writer(prompt):
    table, objects = _load(), []
    second_pass = os.environ.get('WALK_PASS') == 'p2'
    for pid in re.findall(r'^=== PASSAGE (\S+) ===$', prompt, flags=re.M):
        p = table[pid]
        questions = [F.question_goes_for(p), F.question_keeps_away(p), F.question_long_break(p)]
        if p['special'] == 'SPARE_PASS' and not second_pass:
            questions[0]['wrong'].append('standing still by the gate')      # seven options: the form check drops it; the spare is used
        objects.append({'passage': pid, 'what_follows': questions, 'plain_fact': F.question_fact(p)})
    return 'writer', json.dumps(objects, ensure_ascii=False)


def _solver(prompt):
    _load()
    question = re.search(r'^Question: (.*)$', prompt, flags=re.M).group(1)
    p, q = _by_question[question]
    options = dict((text, letter) for letter, text in re.findall(r'^([A-F])\. (.*)$', prompt, flags=re.M))
    right = options[q['right']]
    with_passage = 'Passage:' in prompt
    if with_passage:
        letter = right
    elif p['special'] == 'GUESSABLE' and q.get('form') == 'KEEPS_AWAY':
        letter = right                                                       # both made-up solvers guess it: the no-passage check drops it
    else:
        letter = sorted(l for l in options.values() if l != right)[0]
    return 'solver', json.dumps({'answer': letter})


def _notes(prompt):
    _load()
    text = prompt.split(LF + 'Passage:' + LF, 1)[1]
    p = _by_text[text]
    target = int(re.search(r'About (\d+) words\.', prompt).group(1))
    informed = 'They may ask what brought what' in prompt
    rewrite = 'failed a check' in prompt
    extra = None
    if p['special'] == 'SUPPORT_FAILS_ONCE' and not informed and not rewrite:
        extra = F.MARKER_NOT_SUPPORTED
    if p['special'] == 'SUPPORT_FAILS_TWICE' and informed:
        extra = F.MARKER_NOT_SUPPORTED
    if p['special'] == 'LEAK_WORD' and informed:
        extra = F.LEAK_SENTENCE
    return 'notes', F.made_up_note(p, target, shift=(3 if informed else 0) + (5 if rewrite else 0), extra=extra)


def _checker(prompt):
    verdicts = []
    for item_id, body in re.findall(r'^=== ITEM (\S+) ===$(.*?)^=== END \1 ===$', prompt, flags=re.M | re.S):
        note = body.split(LF + 'Note:' + LF, 1)[1]
        verdicts.append({'item': item_id, 'verdict': 'FAIL' if F.MARKER_NOT_SUPPORTED in note else 'PASS'})
    return 'checker', json.dumps(verdicts)


def urlopen(request, timeout=None, **more):
    """Stands in for urllib.request.urlopen. It never opens a connection."""
    url = request.full_url
    body = json.loads(request.data.decode('utf-8'))
    prompt = body['messages'][0]['content']
    modes = [m for m in os.environ.get('WALK_STUB_MODE', '').split(',') if m]
    key_ok = request.get_header('Authorization') == 'Bearer ' + MADE_UP_KEY
    row = {'url': url, 'model_asked': body.get('model'), 'temperature': body.get('temperature'), 'max_tokens': body.get('max_tokens'),
           'other_body_keys': sorted(k for k in body if k not in ('model', 'temperature', 'max_tokens', 'messages')),
           'prompt_chars': len(prompt), 'made_up_key_was_sent': key_ok, 'modes': modes}
    if not key_ok:
        _log(dict(row, kind='REFUSED_BY_THE_STUB_A_KEY_THAT_IS_NOT_THE_MADE_UP_ONE'))
        raise RuntimeError('WALK STUB: the request does not carry the made-up key. Nothing was sent anywhere.')
    for mode, text in (('http429_daily', 'Quota exceeded, made-up text. quotaId GenerateRequestsPerDayPerProjectPerModel-FreeTier. Please retry in 1s.'),
                       ('http429_rate', 'Resource has been exhausted. Please retry in 1s.')):
        if mode in modes:
            _log(dict(row, kind='HTTP_429'))
            raise urllib.error.HTTPError(url, 429, 'Too Many Requests', {}, io.BytesIO(json.dumps({'error': {'code': 429, 'message': text}}).encode('utf-8')))
    if 'deepseek' in url:
        kind, content = _solver(prompt) if prompt.startswith(('Read the passage. Then answer', 'Answer the multiple-choice question.')) else _notes(prompt)
    else:
        kind, content = _writer(prompt) if '=== PASSAGE ' in prompt else _checker(prompt)
    doc = {'id': 'made-up', 'object': 'chat.completion', 'model': NAMES[kind],
           'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': content}, 'finish_reason': 'stop'}],
           'usage': {'prompt_tokens': len(prompt.split()), 'completion_tokens': len(content.split()), 'total_tokens': len(prompt.split()) + len(content.split())}}
    if 'no_usage' in modes:
        del doc['usage']
    if 'huge_usage' in modes:
        doc['usage'] = {'prompt_tokens': 3000000, 'completion_tokens': 5, 'total_tokens': 3000005}
    if 'no_model' in modes:
        del doc['model']
    _log(dict(row, kind=kind, reply_chars=len(content)))
    return _Reply(json.dumps(doc).encode('utf-8'))
