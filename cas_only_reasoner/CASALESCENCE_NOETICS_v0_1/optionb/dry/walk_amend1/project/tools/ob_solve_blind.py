"""Option B, Steps 4 and 5. Two blind solvers check every answer key.

What this tool does, in plain words:
- Step 4, key check. Each solver gets the passage, the question and the options in a shuffled order.
  A question is kept only if both solvers pick the writer's right option and neither raises a flag.
- Step 5, no-passage check. Each solver gets the question and the options with no passage.
  If both pick the right option, the question can be guessed and is dropped.

The two solvers:
- DeepSeek, asked for as deepseek-chat. One item per fresh call. No memory between calls.
- A Claude Sonnet sub-agent that gets text only. This tool writes a plain text sheet for it (export)
  and reads its answer sheet back (import). The no-passage sheet goes to a fresh sub-agent.
  Its model id is pinned in PLAN_CONSTANTS.json (outside_services.claude_solver.model_id;
  amendment A3). A limit, stated plainly: a Claude sub-agent carries the CAS definitions in its
  project instructions. It only picks a letter. It never writes or edits a question, a key or a note.

The model name of every reply (amendment A9). Every DeepSeek call log line holds the model name the
tool asked for and the model name the service put in its reply. For a Claude sheet the operator
reads the model name from the sub-agent's transcript and gives it to the import step with
--transcript-model. The tool stores each name as it is. It does not judge it.

The DeepSeek token limits (amendment A11; outside_services.deepseek.spend_cap_rule). DeepSeek may
cost at most 4.00 USD in total. That is enforced as two token limits, counted over the four DeepSeek
call logs (this tool's two and the two of tools/ob_write_ordinary_notes.py). Before each call this
tool knows both counts. At a limit it makes no call and stops with STOPPED_TOKEN_CAP. A reply with
HTTP status 200 that carries no token count is logged; then the tool stops with
STOPPED_NO_TOKEN_COUNT. The two DeepSeek tools are not run at the same time. A dry folder calls no
service and counts nothing.

What a solver can see: the passage (Step 4 only), the question, the lettered options, a neutral item id.
Never the key, the form name, a label, a note or a real passage id. This tool opens no label file.
The service key is read from the environment at run time. It is never read from a file, printed or stored.

Usage:
  ob_solve_blind.py deepseek --set practice|final --max-calls N [--mode both|with_passage|no_passage] [--workers K]
  ob_solve_blind.py export   --set practice|final --mode with_passage|no_passage [--max-items K]
  ob_solve_blind.py import   --set practice|final --mode with_passage|no_passage --sheet NN --transcript-model NAME
  ob_solve_blind.py decide   --set practice|final

Files (FILE_FORMATS.md section 6), all under solve/:
  solver_items_<set>.json, deepseek_calls_<set>.jsonl, claude_sheet_<set>_<mode>_<nn>.txt,
  claude_answers_<set>_<mode>_<nn>.txt (saved unchanged by the operator), solver_answers_<set>.json, key_check_<set>.json

Dry fixture: --work pointing under optionb/dry/. Then no outside call is ever made;
the deepseek step needs --replay-replies FILE with made-up replies.
"""
import argparse
import datetime
import hashlib
import json
import os
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
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
MODES = ['with_passage', 'no_passage']
FINAL_HTTP = (200,)   # the service gave a reply; readable or not, the item is never asked again
HALT_HTTP = (401, 402, 403, 429)  # stop cleanly; the call log is the checkpoint
# Any other status, and no answer at all, leaves the item open. It is tried again in this run
# (transport_retries) and on a later run. The decide step refuses while an item is open.


class Stop(Exception):
    """A clean stop. The first argument is a code, the second a plain sentence."""


# ---------------------------------------------------------------- shared helpers

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha_text(text):
    return sha_bytes(text.encode('utf-8'))


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


def load_own(path):
    """Read a file this program wrote earlier. The three header fields are dropped; they are written fresh."""
    doc = json.loads(Path(path).read_text(encoding='utf-8'))
    for name in ('schema', 'made_by', 'inputs'):
        doc.pop(name, None)
    return doc


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


def patiently(action):
    """Run a file action. On Windows a sync or scan tool can hold a file for a moment; wait and try again."""
    for _ in range(40):
        try:
            return action()
        except PermissionError:
            time.sleep(0.25)
    return action()


def replace_file(source, target):
    patiently(lambda: os.replace(source, target))


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + '.partial')
    with open(partial, 'w', encoding='utf-8', newline='\n') as stream:
        stream.write(text)
    replace_file(partial, path)


def append_jsonl(path, row):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with patiently(lambda: open(path, 'a', encoding='utf-8', newline='\n')) as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    for number, line in enumerate(path.read_text(encoding='utf-8').split('\n'), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except ValueError:
                raise Stop('LOG_LINE_UNREADABLE', '%s line %d is not readable JSON. Look at the file before going on.' % (rel(path), number))
    return rows


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


# ---------------------------------------------------------------- items: neutral ids and shuffled options

def option_lines(constants, candidate, shown):
    """The lettered option lines in shown order. Letters A, B, C, ... are given in that order."""
    options = [candidate['right']] + list(candidate['wrong'])
    letters = constants['levels']['letters']
    return '\n'.join(fill(constants['prompt']['option_line'], {'LETTER': letters[place], 'TEXT': options[index]})
                     for place, index in enumerate(shown))


def add_items(constants, set_name, items, by_id, question_ids, solver, mode, sheet):
    """Give a neutral item id and a shuffled option order to each question that has none yet for this solver and mode.

    Item numbers go on from the highest number already used with the same prefix in this set,
    so an item id is never used twice within a set.
    """
    seeds, rules, letters = constants['seeds'], constants['solver_rules'], constants['levels']['letters']
    have = {(item['solver'], item['mode'], item['question_id']) for item in items}
    fresh = sorted(qid for qid in question_ids if (solver, mode, qid) not in have)
    random.Random('%d|%s|%s|%s|%s' % (seeds['sheet_item_order'], set_name, solver, mode, sheet)).shuffle(fresh)
    prefix, digits = rules['item_id_prefix'][mode], rules['item_id_digits']
    number = max([int(item['item_id'][len(prefix):]) for item in items if item['item_id'].startswith(prefix)] or [0])
    made = []
    for qid in fresh:
        number += 1
        if number >= 10 ** digits:
            raise Stop('TOO_MANY_ITEMS', 'More items than %d digits can number.' % digits)
        shown = list(range(1 + len(by_id[qid]['wrong'])))
        random.Random('%d|%s|%s|%s' % (seeds['solver_option_shuffle'], qid, solver, mode)).shuffle(shown)
        made.append({'item_id': '%s%0*d' % (prefix, digits, number), 'solver': solver, 'mode': mode, 'sheet': sheet,
                     'question_id': qid, 'shown': shown, 'right_letter': letters[shown.index(0)]})
    items.extend(made)
    return made


# ---------------------------------------------------------------- reading a solver's reply

def read_token(token, letters, mode, flags):
    """(readable, place of the picked letter or None, flag or None). Flags are allowed only with the passage."""
    if token in letters:
        return True, letters.index(token), None
    if mode == 'with_passage' and token in flags:
        return True, None, token
    return False, None, None


def read_json_reply(text, letters, mode, flags):
    """A DeepSeek reply must be one JSON object with the single key answer. A repeated key is unreadable."""
    text = (text or '').strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1] if '\n' in text else ''
        text = text.rsplit('```', 1)[0]

    def pairs(found):
        if len({name for name, _ in found}) != len(found):
            raise ValueError('repeated key')
        return dict(found)
    try:
        value = json.loads(text, object_pairs_hook=pairs)
    except ValueError:
        return False, None, None
    if not isinstance(value, dict) or list(value) != ['answer'] or not isinstance(value['answer'], str):
        return False, None, None
    return read_token(value['answer'], letters, mode, flags)


def answer_row(item, raw, source_sha256, reading, model_in_reply):
    """One row of solver_answers. model_in_reply (amendment A9): for DeepSeek the model name in the reply, as in the call
    log; for a Claude answer the model name the operator read from the sub-agent's transcript."""
    readable, place, flag = reading
    return {'item_id': item['item_id'], 'solver': item['solver'], 'mode': item['mode'], 'question_id': item['question_id'],
            'raw': raw, 'readable': readable, 'picked_option_index': item['shown'][place] if place is not None else None,
            'flag': flag, 'source_sha256': source_sha256, 'model_in_reply': model_in_reply}


# ---------------------------------------------------------------- talking to the service

def scrub(text, key):
    return text.replace(key, '[KEY]') if key and text else text


def reply_model(doc):
    """The model name the service put in its reply (amendment A9): the reply's own field model, as it is, or None."""
    name = doc.get('model') if isinstance(doc, dict) else None
    return name if isinstance(name, str) else None


def http_send(url, key, body, timeout):
    """One request. Returns http_status (0 when no answer came), content, error, usage, model_in_reply."""
    request = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'),
                                     headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    blank = {'content': '', 'usage': None, 'model_in_reply': None}
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status, payload = response.status, response.read()
    except urllib.error.HTTPError as error:
        detail = error.read()[:2000].decode('utf-8', 'replace')
        return dict(blank, http_status=error.code, error=scrub('HTTPError %d: %s' % (error.code, detail), key))
    except Exception as error:
        return dict(blank, http_status=0, error=scrub('%s: %s' % (type(error).__name__, str(error)[:300]), key))
    try:
        doc = json.loads(payload)
        content = doc['choices'][0]['message'].get('content') or ''
    except Exception as error:
        return dict(blank, http_status=status, error='REPLY_ENVELOPE_UNREADABLE: ' + type(error).__name__)
    usage = doc.get('usage')
    return {'http_status': status, 'content': content, 'error': None, 'usage': usage if isinstance(usage, dict) else None,
            'model_in_reply': reply_model(doc)}


# ---------------------------------------------------------------- the DeepSeek token limits (amendment A11)

def usage_pair(usage):
    """(prompt_tokens, completion_tokens) of a usage object, or None when it does not hold both as whole numbers."""
    if not isinstance(usage, dict):
        return None
    pair = (usage.get('prompt_tokens'), usage.get('completion_tokens'))
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 0 for value in pair):
        return None
    return pair


def count_tokens(rows):
    """[input count, output count] over call log lines. A line whose usage holds no token count adds nothing."""
    used = [0, 0]
    for row in rows:
        pair = usage_pair(row.get('usage'))
        if pair:
            used[0] += pair[0]
            used[1] += pair[1]
    return used


def limit_reached(used, service):
    """True when the input count has reached its limit, or the output count has reached its limit."""
    return used[0] >= service['spend_cap_input_tokens'] or used[1] >= service['spend_cap_output_tokens']


def tokens_at_start(ctx, service, own_log):
    """Both counts as the four DeepSeek call logs stand now. A dry folder calls no service and counts nothing: None."""
    logs = list(service['spend_cap_counted_logs'])
    limits = (service['spend_cap_input_tokens'], service['spend_cap_output_tokens'])
    if any(not isinstance(value, int) or isinstance(value, bool) or value < 1 for value in limits):
        raise Stop('PLAN_CONSTANTS_DISAGREE', 'outside_services.deepseek in PLAN_CONSTANTS.json does not give the two token limits as whole numbers.')
    if Path(own_log).resolve() not in [(ctx.work / name).resolve() for name in logs]:
        raise Stop('PLAN_CONSTANTS_DISAGREE', 'outside_services.deepseek.spend_cap_counted_logs does not name the call log of this step.')
    if ctx.dry:
        return None
    used = [0, 0]
    for name in logs:
        part = count_tokens(read_jsonl(ctx.work / name))
        used = [used[0] + part[0], used[1] + part[1]]
    return used


# ---------------------------------------------------------------- the run

class Run:
    """What every step needs: the constants, the candidates, the private item map and the paths."""

    def __init__(self, args):
        self.ctx = ctx = Ctx(args.work)
        self.C = C = ctx.constants
        self.set_name = set_name = args.set_name
        if set_name == 'practice':
            self.seal = check_seal(ctx, ['1_PLAN_AND_SOURCES', '2_ROLE_NOTES'], '3A_PRACTICE_QUESTIONS_AND_KEYS')
        else:
            self.seal = check_seal(ctx, ['1_PLAN_AND_SOURCES', '2_ROLE_NOTES', '3A_PRACTICE_QUESTIONS_AND_KEYS', '3B_PRACTICE_SET_FIXED'],
                                   '3C_FINAL_QUESTIONS_AND_KEYS')
            if not (ctx.work / 'select' / 'split_fixed.json').exists():
                raise Stop('PRACTICE_SET_NOT_FIXED', 'select/split_fixed.json does not exist. The final set is not handled before the practice set is fixed.')
        doc = ctx.read_json(ctx.work / 'checks' / ('candidates_%s.json' % set_name))
        if (doc.get('schema'), doc.get('set')) != ('casalescence/optionb/candidates/v1', set_name):
            raise Stop('WRONG_FILE', 'checks/candidates_%s.json is not the candidates file of this set.' % set_name)
        self.candidates = doc['candidates']
        self.by_id = {c['question_id']: c for c in self.candidates}
        self.solvers = list(C['solver_rules']['solvers'])
        self.deepseek, self.claude = C['outside_services']['deepseek']['model'], C['outside_services']['claude_solver']['name']
        # Amendment A3: the model id the Claude sub-agents are asked for with. The operator pins it in the plan constants.
        self.claude_model_id = C['outside_services']['claude_solver'].get('model_id')
        if sorted(self.solvers) != sorted([self.deepseek, self.claude]):
            raise Stop('PLAN_CONSTANTS_DISAGREE', 'solver_rules.solvers does not name the DeepSeek model and the Claude solver of outside_services.')
        self.flags = C['briefs']['solver_flags']
        sdir = ctx.work / 'solve'
        self.items_path = sdir / ('solver_items_%s.json' % set_name)
        self.log_path = sdir / ('deepseek_calls_%s.jsonl' % set_name)
        self.answers_path = sdir / ('solver_answers_%s.json' % set_name)
        self.key_check_path = sdir / ('key_check_%s.json' % set_name)
        self.sdir = sdir
        self.items = load_own(self.items_path)['items'] if self.items_path.exists() else []

    def sheet_path(self, kind, mode, sheet):
        return self.sdir / ('claude_%s_%s_%s_%s.txt' % (kind, self.set_name, mode, sheet))

    def letters(self, item):
        return self.C['levels']['letters'][:len(item['shown'])]

    def save_items(self):
        self.ctx.write_json(self.items_path, 'casalescence/optionb/solver_items/v1', {'set': self.set_name, 'items': self.items})

    def save_answers(self, claude_new=None):
        """Write solver_answers. DeepSeek answers come from the call log. Claude answers come from imported sheets."""
        answers = []
        final = {}
        for row in read_jsonl(self.log_path):
            if row['http_status'] in FINAL_HTTP:
                final.setdefault(row['item_id'], row)
        for item in self.items:
            if item['solver'] == self.deepseek and item['item_id'] in final:
                row = final[item['item_id']]
                reading = read_json_reply(row['reply'], self.letters(item), item['mode'], self.flags) if row['http_status'] == 200 else (False, None, None)
                answers.append(answer_row(item, row['reply'], row['reply_sha256'], reading, row.get('model_in_reply')))
        kept = [a for a in load_own(self.answers_path)['answers'] if a['solver'] == self.claude] if self.answers_path.exists() else []
        sheet_of = {(i['mode'], i['item_id']): i['sheet'] for i in self.items if i['solver'] == self.claude}
        hashes = {}
        for answer in kept:
            path = self.sheet_path('answers', answer['mode'], sheet_of[(answer['mode'], answer['item_id'])])
            if path not in hashes:
                hashes[path] = sha_bytes(path.read_bytes()) if path.exists() else None
            if hashes[path] != answer['source_sha256']:
                raise Stop('ANSWER_SHEET_CHANGED', '%s is gone or has changed since it was imported.' % rel(path))
        answers.extend(kept + (claude_new or []))
        answers.sort(key=lambda a: (a['mode'], a['solver'], a['item_id']))
        if self.log_path.exists():
            self.ctx.inputs[rel(self.log_path)] = sha_bytes(self.log_path.read_bytes())
        self.ctx.write_json(self.answers_path, 'casalescence/optionb/solver_answers/v1', {'set': self.set_name, 'answers': answers})
        return answers


def step_deepseek(run, args):
    ctx, C = run.ctx, run.C
    service = C['outside_services']['deepseek']
    modes = MODES if args.mode == 'both' else [args.mode]
    for mode in modes:
        add_items(C, run.set_name, run.items, run.by_id, list(run.by_id), run.deepseek, mode, '00')
    run.save_items()
    done = {row['item_id'] for row in read_jsonl(run.log_path) if row['http_status'] in FINAL_HTTP}
    used = tokens_at_start(ctx, service, run.log_path)   # None in a dry folder: nothing is counted there
    asked_model = DRY_MODEL if ctx.dry else service['model']
    todo = sorted((i for i in run.items if i['solver'] == run.deepseek and i['mode'] in modes and i['item_id'] not in done), key=lambda i: i['item_id'])

    if ctx.dry:
        if args.max_calls > 0 and not args.replay_replies:
            raise Stop('DRY_FIXTURE_NEEDS_REPLAY', 'No outside call is ever made from a dry folder. Give --replay-replies.')
        replay = json.loads(Path(args.replay_replies).read_text(encoding='utf-8')) if args.replay_replies else {}
        key, pace = '', 0.0

        def send(item, prompt):
            steps = replay.get(item['item_id'])
            steps = steps if isinstance(steps, list) else [steps]
            step = steps.pop(0) if steps and steps[0] is not None else None
            if step is None:
                return {'http_status': 0, 'content': '', 'error': 'NO_MADE_UP_REPLY_FOR_THIS_ITEM', 'usage': None, 'model_in_reply': None}
            content = json.dumps(step['content_json']) if 'content_json' in step else step.get('content', '')
            # a made-up reply may carry a made-up model name under "model"; it is stored as model_in_reply
            return {'http_status': step['http_status'], 'content': content, 'error': step.get('error'), 'usage': None,
                    'model_in_reply': reply_model(step)}
    else:
        if args.replay_replies:
            raise Stop('REPLAY_ONLY_IN_DRY_FOLDER', '--replay-replies is refused outside optionb/dry/.')
        key, pace = os.environ.get(service['key_environment_variable'], '').strip(), max(0.0, args.pace)
        if args.max_calls > 0 and todo and not key:
            raise Stop('KEY_NOT_SET', 'The environment variable %s is not set.' % service['key_environment_variable'])

        def send(item, prompt):
            body = {'model': service['model'], 'temperature': service['temperature'], 'messages': [{'role': 'user', 'content': prompt}]}
            return http_send(service['endpoint'], key, body, args.timeout)

    lock = threading.Lock()
    state = {'calls': 0, 'halt': None, 'tokens': {'prompt_tokens': 0, 'completion_tokens': 0}}

    def work(item):
        candidate = run.by_id[item['question_id']]
        values = {'QUESTION': candidate['question'], 'OPTION_LINES': option_lines(C, candidate, item['shown'])}
        if item['mode'] == 'with_passage':
            values['PASSAGE'] = candidate['passage']
        prompt = fill('\n'.join(C['briefs']['solver_' + item['mode']]), values)
        for _ in range(1 + service['transport_retries']):
            with lock:
                if state['halt']:
                    return
                if state['calls'] >= args.max_calls:
                    state['halt'] = 'STOPPED_CALL_BUDGET'
                    return
                # Amendment A11: at a token limit no call is made. Calls that are already running still finish.
                if used is not None and limit_reached(used, service):
                    state['halt'] = service['spend_cap_stop_status']
                    return
                state['calls'] += 1
            time.sleep(pace)
            result = send(item, prompt)
            status = result['http_status']
            readable = status == 200 and read_json_reply(result['content'], run.letters(item), item['mode'], run.flags)[0]
            error = result['error'] or (None if readable else 'UNREADABLE_REPLY')
            row = {'utc': utc_now(), 'item_id': item['item_id'], 'mode': item['mode'], 'question_id': item['question_id'],
                   'model': asked_model, 'model_in_reply': result['model_in_reply'], 'usage': result['usage'],
                   'http_status': status, 'ok': bool(readable), 'error': scrub(error, key), 'prompt_sha256': sha_text(prompt),
                   'reply_sha256': sha_text(result['content']), 'prompt': prompt, 'reply': result['content']}
            with lock:
                append_jsonl(run.log_path, row)
                pair = usage_pair(result['usage'])
                if pair:
                    state['tokens']['prompt_tokens'] += pair[0]
                    state['tokens']['completion_tokens'] += pair[1]
                    if used is not None:
                        used[0] += pair[0]
                        used[1] += pair[1]
                elif used is not None and status == 200:
                    # a reply with HTTP status 200 and no token count: it is logged, then the tool stops
                    state['halt'] = state['halt'] or service['spend_cap_no_count_status']
                if status in HALT_HTTP:
                    state['halt'] = state['halt'] or 'STOPPED_BY_SERVICE_HTTP_%d' % status
            if status in FINAL_HTTP or status in HALT_HTTP:
                return
            time.sleep(0.0 if ctx.dry else 3.0)

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        list(pool.map(work, todo))
    answers = run.save_answers()
    mine = [a for a in answers if a['solver'] == run.deepseek]
    want = len([i for i in run.items if i['solver'] == run.deepseek])
    status = state['halt'] or ('ALL_ANSWERED' if len(mine) == want else 'STOPPED_NO_ANSWER_FROM_SERVICE')
    answered = {a['item_id'] for a in mine}
    last_status = {}
    for row in read_jsonl(run.log_path):
        if row['item_id'] not in answered:
            last_status[row['item_id']] = row['http_status']
    print(json.dumps({
        'program': PROGRAM, 'dry_fixture': ctx.dry, 'step': 'deepseek', 'status': status, 'set': run.set_name, 'seal': run.seal,
        'candidates': len(run.candidates), 'items': want, 'items_answered': len(mine), 'items_readable': sum(a['readable'] for a in mine),
        'items_open': want - len(mine), 'last_http_status_of_open_items_that_were_tried': last_status,
        'calls_this_run': state['calls'], 'call_budget': args.max_calls, 'tokens_this_run_REAL': state['tokens'],
        'deepseek_tokens_in_the_four_call_logs': (None if used is None else {'input': used[0], 'output': used[1]}),
        'deepseek_token_limits': {'input': service['spend_cap_input_tokens'], 'output': service['spend_cap_output_tokens']},
        'model_names_in_the_replies': sorted({str(a['model_in_reply']) for a in mine}),
        'next': {service['spend_cap_stop_status']: 'A DeepSeek token limit is reached. No further call is made. The call log is kept. '
                                                   'A limit is never raised without a new reviewed plan version. Report this.',
                 service['spend_cap_no_count_status']: 'A reply came back with no token count. It is logged. The tool stopped, because the '
                                                       'spend can not be counted without it. Report this.'}.get(
            status, 'Run the same command again until status is ALL_ANSWERED. An item with an answer is never asked again.')},
        ensure_ascii=False, indent=1))


def step_export(run, args):
    C, mode = run.C, args.mode
    have = {(i['solver'], i['mode'], i['question_id']) for i in run.items}
    fresh = sorted(qid for qid in run.by_id if (run.claude, mode, qid) not in have)
    if not fresh:
        raise Stop('NOTHING_TO_EXPORT', 'Every candidate already sits on a Claude sheet for this mode.')
    if not isinstance(run.claude_model_id, str) or not run.claude_model_id.strip():
        raise Stop('CLAUDE_MODEL_ID_NOT_PINNED', 'outside_services.claude_solver.model_id in PLAN_CONSTANTS.json is not set. '
                   'No sheet is written for a sub-agent whose model id is not pinned.')
    size = args.max_items or len(fresh)
    used = [int(i['sheet']) for i in run.items if i['solver'] == run.claude and i['mode'] == mode]
    number = max(used or [0])
    forms = '|'.join(re.escape(form) for form in C['forms_in_order'])
    written = []
    for at in range(0, len(fresh), size):
        number += 1
        sheet = '%02d' % number
        path = run.sheet_path('sheet', mode, sheet)
        if path.exists():
            raise Stop('SHEET_EXISTS', '%s exists already. A sheet is never written twice.' % rel(path))
        made = add_items(C, run.set_name, run.items, run.by_id, fresh[at:at + size], run.claude, mode, sheet)
        blocks = []
        for item in made:
            candidate = run.by_id[item['question_id']]
            values = {'ID': item['item_id'], 'QUESTION': candidate['question'], 'OPTION_LINES': option_lines(C, candidate, item['shown'])}
            if mode == 'with_passage':
                values['PASSAGE'] = candidate['passage']
            blocks.append(fill('\n'.join(C['briefs']['solver_sheet_item_' + mode]), values))
        header = fill('\n'.join(C['briefs']['solver_sheet_header_' + mode]), {'SHEET_ID': '%s-%s-%s' % (run.set_name, mode, sheet)})
        text = header + '\n\n' + '\n\n'.join(blocks) + '\n'
        if re.search(r'\.p[12]\.|\b(?:%s)\b' % forms, text) or any(item['question_id'] in text for item in made):
            raise Stop('SHEET_NOT_BLIND', 'The sheet text would hold a question id or a form name. Nothing was written.')
        write_text(path, text)
        written.append({'sheet': sheet, 'file': rel(path), 'items': len(made), 'sha256': sha_text(text),
                        'answers_go_to': rel(run.sheet_path('answers', mode, sheet))})
    run.save_items()
    print(json.dumps({
        'program': PROGRAM, 'dry_fixture': run.ctx.dry, 'step': 'export', 'status': 'SHEETS_WRITTEN', 'set': run.set_name, 'mode': mode,
        'seal': run.seal, 'sheets': written, 'ask_for_the_sub_agent_with_model_id': run.claude_model_id,
        'next': ['Give each sheet, as text only, to a Claude Sonnet sub-agent with no file access. Ask for it with the pinned model id %s. Give it nothing else.'
                 % run.claude_model_id,
                 'A no_passage sheet goes to a fresh sub-agent that never saw a with_passage sheet.',
                 'Save the reply, unchanged, to the answers file named above. Read the model name from the sub-agent transcript.',
                 'Then run the import step for that sheet with --transcript-model NAME, the name exactly as the transcript shows it.']},
        ensure_ascii=False, indent=1))


def step_import(run, args):
    mode, sheet = args.mode, args.sheet
    # Amendments A3 and A9: the operator reads the model name from the sub-agent's transcript. It is stored with every
    # answer of this sheet, exactly as given. The tool does not judge the name.
    transcript_model = args.transcript_model
    if not isinstance(transcript_model, str) or not transcript_model.strip() or transcript_model != transcript_model.strip():
        raise Stop('TRANSCRIPT_MODEL_MISSING', 'The import step needs --transcript-model NAME: the model name of the sub-agent, exactly as its '
                   'transcript shows it, with no space before or after.')
    on_sheet = [i for i in run.items if i['solver'] == run.claude and i['mode'] == mode and i['sheet'] == sheet]
    if not on_sheet:
        raise Stop('UNKNOWN_SHEET', 'No Claude sheet %s was exported for this set and mode.' % sheet)
    path = run.sheet_path('answers', mode, sheet)
    if not path.exists():
        raise Stop('ANSWER_FILE_MISSING', '%s does not exist. Save the sub-agent reply there, unchanged.' % rel(path))
    data = run.ctx.read_bytes(path)
    source = sha_bytes(data)
    ids = {i['item_id'] for i in on_sheet}
    old = [a for a in load_own(run.answers_path)['answers'] if a['solver'] == run.claude and a['mode'] == mode and a['item_id'] in ids] \
        if run.answers_path.exists() else []
    if old:
        if any(a['source_sha256'] != source for a in old):
            raise Stop('SHEET_ALREADY_IMPORTED', 'Sheet %s was imported before from another answer file. An answer sheet is read once.' % sheet)
        raise Stop('NOTHING_TO_IMPORT', 'Sheet %s was imported before from this same answer file.' % sheet)
    seen, stray = {}, []
    for line in data.decode('utf-8-sig', 'replace').split('\n'):
        line = line.strip()
        if not line:
            continue
        first = line.split()[0]
        if first in ids:
            seen.setdefault(first, []).append(line)
        else:
            stray.append(line[:80])
    if not seen:
        raise Stop('ANSWER_FILE_DOES_NOT_FIT_SHEET', 'No line of %s starts with an item id of sheet %s. Nothing was imported.' % (rel(path), sheet))
    new, problems = [], {'missing': 0, 'repeated': 0, 'line_does_not_fit': 0, 'reply_not_allowed': 0}
    for item in sorted(on_sheet, key=lambda i: i['item_id']):
        lines = seen.get(item['item_id'], [])
        raw, reading = ' | '.join(lines), (False, None, None)
        if not lines:
            problems['missing'] += 1
        elif len(lines) > 1:
            problems['repeated'] += 1
        else:
            fits = re.fullmatch(r'(\S+) (\S+)', lines[0])
            if not fits:
                problems['line_does_not_fit'] += 1
            else:
                raw = fits.group(2)
                reading = read_token(raw, run.letters(item), mode, run.flags)
                problems['reply_not_allowed'] += not reading[0]
        new.append(answer_row(item, raw, source, reading, transcript_model))
    run.save_answers(claude_new=new)
    print(json.dumps({
        'program': PROGRAM, 'dry_fixture': run.ctx.dry, 'step': 'import', 'status': 'SHEET_IMPORTED', 'set': run.set_name, 'mode': mode,
        'sheet': sheet, 'seal': run.seal, 'answer_file': rel(path), 'answer_file_sha256': source, 'items_on_sheet': len(on_sheet),
        'model_name_from_the_transcript': transcript_model, 'model_id_pinned_in_the_plan': run.claude_model_id,
        'readable': sum(a['readable'] for a in new), 'unreadable': sum(not a['readable'] for a in new),
        'unreadable_by_cause': {name: int(count) for name, count in problems.items()},
        'lines_that_name_no_item_of_this_sheet': len(stray), 'first_such_lines': stray[:20],
        'note': 'An unreadable reply counts as not picked. It is not asked again.'}, ensure_ascii=False, indent=1))


def step_decide(run, args):
    answers = run.save_answers()
    by_key = {(a['solver'], a['mode'], a['question_id']): a for a in answers}
    missing = {}
    for candidate in run.candidates:
        for solver in run.solvers:
            for mode in MODES:
                if (solver, mode, candidate['question_id']) not in by_key:
                    missing['%s %s' % (solver, mode)] = missing.get('%s %s' % (solver, mode), 0) + 1
    if missing:
        raise Stop('SOLVERS_NOT_COMPLETE', 'Some candidates have no answer yet: %s. Finish the deepseek step and import every Claude sheet first.'
                   % json.dumps(missing, sort_keys=True))

    def word(answer, mode):
        if not answer['readable']:
            return 'UNREADABLE'
        if answer['flag']:
            return 'FLAG_' + answer['flag'] if mode == 'with_passage' else 'UNREADABLE'
        return 'RIGHT' if answer['picked_option_index'] == 0 else 'WRONG'

    rows = []
    for candidate in run.candidates:
        qid = candidate['question_id']
        with_passage = {solver: word(by_key[(solver, 'with_passage', qid)], 'with_passage') for solver in run.solvers}
        no_passage = {solver: word(by_key[(solver, 'no_passage', qid)], 'no_passage') for solver in run.solvers}
        key_ok = all(value == 'RIGHT' for value in with_passage.values())
        guess_ok = not all(value == 'RIGHT' for value in no_passage.values())
        rows.append({'question_id': qid, 'family': candidate['family'], 'with_passage': with_passage, 'key_check_passed': key_ok,
                     'no_passage': no_passage, 'no_passage_passed': guess_ok, 'survives': key_ok and guess_ok})
    families = ['role_step', 'plain_fact']

    def split(test):
        return {family: sum(1 for row in rows if row['family'] == family and test(row)) for family in families}
    counts = {'checked': split(lambda r: True), 'key_check_passed': split(lambda r: r['key_check_passed']),
              'no_passage_passed': split(lambda r: r['no_passage_passed']), 'survive': split(lambda r: r['survives'])}
    run.ctx.write_json(run.key_check_path, 'casalescence/optionb/key_check/v1', {'set': run.set_name, 'rows': rows, 'counts': counts})
    print(json.dumps({
        'program': PROGRAM, 'dry_fixture': run.ctx.dry, 'step': 'decide', 'status': 'KEY_CHECK_WRITTEN', 'set': run.set_name, 'seal': run.seal,
        'counts': counts,
        'survival_after_each_filter': [
            {'filter': 'option check', 'role_step': counts['checked']['role_step'], 'plain_fact': counts['checked']['plain_fact']},
            {'filter': 'key check', 'role_step': counts['key_check_passed']['role_step'], 'plain_fact': counts['key_check_passed']['plain_fact']},
            {'filter': 'no-passage check', 'role_step': counts['survive']['role_step'], 'plain_fact': counts['survive']['plain_fact']}],
        'note': 'The no-passage check row counts questions that passed both checks.'}, ensure_ascii=False, indent=1))


def main(argv=None):
    parser = argparse.ArgumentParser(description='Option B Steps 4 and 5: key check and no-passage check by two blind solvers.')
    steps = parser.add_subparsers(dest='step', required=True)
    for name in ('deepseek', 'export', 'import', 'decide'):
        sub = steps.add_parser(name)
        sub.add_argument('--set', dest='set_name', required=True, choices=['practice', 'final'])
        sub.add_argument('--work', default=None, help='dry fixture folder under optionb/dry/ (never for a real run)')
        if name == 'deepseek':
            sub.add_argument('--max-calls', type=int, required=True, help='call budget for this run; 0 = make the item map only')
            sub.add_argument('--mode', default='both', choices=['both'] + MODES)
            sub.add_argument('--workers', type=int, default=4)
            sub.add_argument('--pace', type=float, default=0.2, help='seconds to wait before each call')
            sub.add_argument('--timeout', type=float, default=120.0)
            sub.add_argument('--replay-replies', default=None, help='dry fixture only: a file of made-up replies by item id')
        if name in ('export', 'import'):
            sub.add_argument('--mode', required=True, choices=MODES)
        if name == 'export':
            sub.add_argument('--max-items', type=int, default=None, help='split the export into sheets of at most this many items')
        if name == 'import':
            sub.add_argument('--sheet', required=True, help='the two-digit sheet number, for example 01')
            sub.add_argument('--transcript-model', required=True,
                             help="the model name of the sub-agent, exactly as its transcript shows it; stored with every answer of the sheet")
    args = parser.parse_args(argv)
    run = Run(args)
    {'deepseek': step_deepseek, 'export': step_export, 'import': step_import, 'decide': step_decide}[args.step](run, args)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Stop as stop:
        print(json.dumps({'program': PROGRAM, 'status': 'STOP', 'code': stop.args[0], 'reason': stop.args[1]}, ensure_ascii=False, indent=1))
        sys.exit(2)
