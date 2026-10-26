"""Option B, Step 7 (first half). Ask the blind note writer for the ordinary notes: the rival help.

What this tool does, in plain words:
- For every passage that carries a task it asks for six notes: two briefs (ORD-INFORMED, ORD-FREE)
  times three lengths (090, 100, 110). One passage and one brief per call. Temperature 0.
- The word target of a note is N = (percent * C_role * W_p + 50 * M_p) // (100 * M_p).
  C_role is the size count of the passage's ROLE note (every word and every punctuation mark
  counts one). W_p is the number of words of the passage. M_p is the size count of the passage.
- It writes a note again ONCE, and only when tools/ob_check_support.py recorded a failed support
  check for the first version of that note. Nothing else can cause a rewrite. This tool never reads
  the answer-leak screen.

What the writer can see: one brief and one passage. Nothing else.
The prompt is built by build_prompt(), which is given the brief text, the word target and the passage
text only. From elig/eligibility.json this tool keeps only id and text. From notes_role/role_notes.json
it keeps only the three size numbers. From select/selection_<set>.json it keeps only the ids of the
passages that carry a task. It never opens a label file, the labeling guide or a key file.

The key of the outside service is read from the environment at run time. It is never read from a
file, never printed and never stored. Error texts are scrubbed of the key before they are logged.

It refuses to run unless the seal steps for the questions and keys of that set exist:
  practice: 1, 2, 3A, 3B.   final: 1, 2, 3A, 3B, 3C.
It refuses to write once seal step 4 (the ordinary notes) exists.

Usage:
  ob_write_ordinary_notes.py --set practice|final --step first|rewrite --max-calls N
                             [--workers K] [--pace SECONDS] [--timeout SECONDS]
  --step first    writes version 1 of every note that has none yet.
  --step rewrite  writes version 2 of the notes whose version 1 failed the support check.
  --max-calls     the call budget of this run. 0 writes the plan and calls nobody.

Files (FILE_FORMATS.md section 8):
  notes_ord/ordinary_notes_<set>.json   the notes, every version
  notes_ord/ordinary_calls_<set>.jsonl  one line per call; this log is the record
The notes file is rebuilt from the call log at every start. So a killed run loses nothing, and a
note that was written is never asked for again.

Stops: HTTP 429 stops the run cleanly. Run the same command again later. A wrong key or an empty
account (HTTP 401, 402, 403) stops the run. A reply that is empty or cut off is not asked again in
the same run (the plan allows no content retry).

The model name of every reply (amendment A9). Every call log line holds the model name the tool
asked for (deepseek-chat) and the model name the service put in its reply. The tool stores the
reply's name as it is. It does not judge it.

The DeepSeek token limits (amendment A11; outside_services.deepseek.spend_cap_rule). DeepSeek may
cost at most 4.00 USD in total. That is enforced as two token limits, counted over the four DeepSeek
call logs (this tool's two and the two of tools/ob_solve_blind.py). Before each call this tool knows
both counts. At a limit it makes no call and stops with STOPPED_TOKEN_CAP. A reply with HTTP status
200 that carries no token count is logged; then the tool stops with STOPPED_NO_TOKEN_COUNT. The two
DeepSeek tools are not run at the same time. A dry folder calls no service and counts nothing.

Exit codes: 0 = everything due is written. 1 = something is still open; run again.
2 = not started or stopped by a check (the reason is printed).

Dry fixture: with --work pointing under optionb/dry/ the tool never calls an outside service.
It then needs --replay-replies FILE (made-up replies, one per note id) and marks every output as a
dry fixture.
"""
import argparse
import datetime
import hashlib
import json
import os
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
LF = chr(10)

SEAL_NEED = {'practice': ['1_PLAN_AND_SOURCES', '2_ROLE_NOTES', '3A_PRACTICE_QUESTIONS_AND_KEYS', '3B_PRACTICE_SET_FIXED'],
             'final': ['1_PLAN_AND_SOURCES', '2_ROLE_NOTES', '3A_PRACTICE_QUESTIONS_AND_KEYS', '3B_PRACTICE_SET_FIXED',
                       '3C_FINAL_QUESTIONS_AND_KEYS']}
SEAL_CLOSED_BY = '4_ORDINARY_NOTES'
BRIEF_OF_GROUP = {'ORD-INFORMED': 'ord_informed_brief', 'ORD-FREE': 'ord_free_brief'}
FRAME_OF_STEP = {'first': 'ordinary_request_frame', 'rewrite': 'ordinary_rewrite_frame'}
VERSION_OF_STEP = {'first': 1, 'rewrite': 2}
FAILED_VERDICTS = ('FAIL', 'UNREADABLE')
NOTE_ID = re.compile(r'(.+)\|([A-Z-]+)\|([0-9]{3})\|v([0-9]+)')
KEY_REFUSED = (401, 402, 403)       # a wrong key or no credit: stop the whole run
SAME_CALL_WOULD_FAIL = (400, 404, 422)


class Stop(Exception):
    """A clean stop. The first argument is a code, the second a plain sentence."""


# ---------------------------------------------------------------- shared helpers

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

    def now(self):
        return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    def read_bytes(self, path):
        data = Path(path).read_bytes()
        self.inputs[rel(path)] = sha_bytes(data)
        return data

    def read_json(self, path):
        return json.loads(self.read_bytes(path).decode('utf-8'))

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


def append_jsonl(path, row):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a', encoding='utf-8', newline=LF) as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + LF)
        stream.flush()
        os.fsync(stream.fileno())


def read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    for number, line in enumerate(path.read_text(encoding='utf-8').split(LF), 1):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except ValueError:
                raise Stop('LOG_LINE_UNREADABLE', '%s line %d is not readable JSON. Look at the file before going on.' % (rel(path), number))
    return rows


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


# ---------------------------------------------------------------- what this tool may take from its inputs

def passage_texts(ctx):
    """Read elig/eligibility.json and keep ONLY the id and the text of each passage.

    Everything else in that file (labels, kinds, eligibility flags, open forms) is dropped here
    and never reaches any other function of this tool.
    """
    doc = ctx.read_json(ctx.work / 'elig' / 'eligibility.json')
    if doc.get('schema') != 'casalescence/optionb/eligibility/v1':
        raise Stop('WRONG_FILE', 'elig/eligibility.json does not carry the eligibility schema name.')
    if not ctx.dry and doc.get('counts_match_plan') is not True:
        raise Stop('ELIGIBILITY_NOT_CONFIRMED', 'elig/eligibility.json does not say counts_match_plan: true.')
    texts = {passage['id']: passage['text'] for passage in doc['passages']}
    del doc
    return texts


def role_sizes(ctx):
    """Read notes_role/role_notes.json and keep ONLY the three size numbers of each passage. No role text is kept."""
    doc = ctx.read_json(ctx.work / 'notes_role' / 'role_notes.json')
    if doc.get('schema') != 'casalescence/optionb/role_notes/v1':
        raise Stop('WRONG_FILE', 'notes_role/role_notes.json does not carry the role-notes schema name.')
    sizes = {passage['id']: {name: passage['size'][name] for name in ('role_size_count', 'passage_words', 'passage_size_count')}
             for passage in doc['passages']}
    del doc
    return sizes


def task_passage_ids(ctx, set_name):
    """Read select/selection_<set>.json and keep ONLY the ids of the passages that carry a task."""
    doc = ctx.read_json(ctx.work / 'select' / ('selection_%s.json' % set_name))
    if doc.get('schema') != 'casalescence/optionb/selection/v1' or doc.get('set') != set_name:
        raise Stop('WRONG_FILE', 'select/selection_%s.json is not the selection file of this set.' % set_name)
    ids = sorted({task['passage_id'] for task in doc['tasks']})
    del doc
    return ids


def word_targets(rules, size):
    """N = (percent * C_role * W_p + 50 * M_p) // (100 * M_p), and never below the plan's lowest target."""
    c_role, w_p, m_p = size['role_size_count'], size['passage_words'], size['passage_size_count']
    out = {}
    for length in rules['lengths_in_order']:
        percent = rules['length_percent'][length]
        out[length] = max((percent * c_role * w_p + 50 * m_p) // (100 * m_p), rules['target_words_min'])
    return out


def build_prompt(briefs, group, step, target, passage_text):
    """The whole prompt: one brief and one passage.

    This function is given the plan's brief texts, the group name, the word target and the passage
    text. It is given nothing else, so a question, an option, a key, a label or a role note can not
    reach the prompt.
    """
    brief = fill(LF.join(briefs[BRIEF_OF_GROUP[group]]), {'N': str(target)})
    return fill(LF.join(briefs[FRAME_OF_STEP[step]]), {'BRIEF': brief, 'PASSAGE': passage_text})


def clean_note(rules, reply):
    """Strip white space at both ends. Turn CR LF into LF. Change nothing else."""
    return (reply or '').replace('\r\n', LF).strip()


# ---------------------------------------------------------------- talking to the service

def scrub(text, key):
    return text.replace(key, '[KEY]') if key else text


def reply_model(doc):
    """The model name the service put in its reply (amendment A9): the reply's own field model, as it is, or None."""
    name = doc.get('model') if isinstance(doc, dict) else None
    return name if isinstance(name, str) else None


def http_send(url, key, body, timeout):
    """One request. Returns http_status (0 when no answer came), content, error, usage, finish_reason, model_in_reply."""
    request = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'),
                                     headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    blank = {'content': '', 'usage': None, 'finish_reason': None, 'model_in_reply': None}
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
        choice = doc['choices'][0]
        content = choice['message'].get('content') or ''
    except Exception as error:
        return dict(blank, http_status=status, error='REPLY_ENVELOPE_UNREADABLE: ' + type(error).__name__)
    usage = doc.get('usage')
    return {'http_status': status, 'content': content, 'error': None, 'usage': usage if isinstance(usage, dict) else None,
            'finish_reason': choice.get('finish_reason'), 'model_in_reply': reply_model(doc)}


def replay_sender(path):
    """Dry fixture only. Made-up replies are read from a file, one per note id. No outside call.

    A made-up reply may carry a made-up model name under "model"; it is stored as model_in_reply.
    """
    table = json.loads(Path(path).read_text(encoding='utf-8'))

    def send(note_id, prompt):
        step = table.get(note_id)
        if step is None:
            return None
        return {'http_status': step['http_status'], 'content': step.get('content') or '', 'error': step.get('error'),
                'usage': None, 'finish_reason': step.get('finish_reason'), 'model_in_reply': reply_model(step)}
    return send


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
        raise Stop('PLAN_DOES_NOT_MATCH_PROGRAM', 'outside_services.deepseek in PLAN_CONSTANTS.json does not give the two token limits as whole numbers.')
    if Path(own_log).resolve() not in [(ctx.work / name).resolve() for name in logs]:
        raise Stop('PLAN_DOES_NOT_MATCH_PROGRAM', 'outside_services.deepseek.spend_cap_counted_logs does not name the call log of this tool.')
    if ctx.dry:
        return None
    used = [0, 0]
    for name in logs:
        part = count_tokens(read_jsonl(ctx.work / name))
        used = [used[0] + part[0], used[1] + part[1]]
    return used


# ---------------------------------------------------------------- the run

def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description='Option B Step 7: the blind writer of the ordinary notes.')
    parser.add_argument('--set', dest='set_name', required=True, choices=['practice', 'final'])
    parser.add_argument('--step', required=True, choices=['first', 'rewrite'], help='first = version 1; rewrite = version 2 after a failed support check')
    parser.add_argument('--max-calls', type=int, required=True, help='call budget for this run; 0 = write the plan only')
    parser.add_argument('--workers', type=int, default=4, help='how many calls run at once')
    parser.add_argument('--pace', type=float, default=0.0, help='seconds to wait before each call')
    parser.add_argument('--timeout', type=float, default=180.0, help='seconds to wait for one reply')
    parser.add_argument('--wait-after-error', type=float, default=5.0, help='seconds to wait before a call is sent again after no answer')
    parser.add_argument('--max-transport-failures', type=int, default=6, help='stop after this many failed connections in a row')
    parser.add_argument('--work', default=None, help='dry fixture folder under optionb/dry/ (never for a real run)')
    parser.add_argument('--replay-replies', default=None, help='dry fixture only: a file of made-up replies, one per note id')
    args = parser.parse_args(argv)

    ctx = Ctx(args.work)
    C = ctx.constants
    service, rules, briefs = C['outside_services']['deepseek'], C['ordinary_notes'], C['briefs']
    set_name, step = args.set_name, args.step
    if args.max_calls < 0 or args.workers < 1:
        raise Stop('BAD_ARGUMENT', 'The call budget must be 0 or more and the number of workers 1 or more.')
    groups, lengths = list(rules['briefs_in_order']), list(rules['lengths_in_order'])
    if groups != list(BRIEF_OF_GROUP) or groups != list(C['groups']['ordinary']):
        raise Stop('PLAN_DOES_NOT_MATCH_PROGRAM', 'The ordinary groups in PLAN_CONSTANTS.json are not the two this program knows.')
    if set(C['groups'].get('struck', [])) & set(groups):
        raise Stop('PLAN_DOES_NOT_MATCH_PROGRAM', 'A struck group is listed as an ordinary group.')
    model = DRY_MODEL if ctx.dry else service['model']

    seal, sealed = check_seal(ctx, SEAL_NEED[set_name], SEAL_CLOSED_BY)
    must_be_sealed(ctx, sealed, [REAL_WORK / 'PLAN_CONSTANTS.json', ctx.work / 'elig' / 'eligibility.json',
                                 ctx.work / 'notes_role' / 'role_notes.json', ctx.work / 'select' / ('selection_%s.json' % set_name)])

    texts, sizes, ids = passage_texts(ctx), role_sizes(ctx), task_passage_ids(ctx, set_name)
    word_rule = re.compile(C['question_rules']['word_sequence_regex'])
    size_rule = re.compile(C['role_notes']['size_count_regex'])

    out_dir = ctx.work / 'notes_ord'
    notes_path = out_dir / ('ordinary_notes_%s.json' % set_name)
    log_path = out_dir / ('ordinary_calls_%s.jsonl' % set_name)
    results_path = ctx.work / 'support' / ('support_results_%s.json' % set_name)
    used = tokens_at_start(ctx, service, log_path)   # None in a dry folder: nothing is counted there

    # the plan: one object per passage that carries a task, six empty note slots each
    passages, slots, prompts = [], {}, {}
    for pid in ids:
        if pid not in texts or pid not in sizes:
            raise Stop('PASSAGE_WITHOUT_ROLE_NOTE', 'Passage %s carries a task and has no passage text or no role note sizes.' % pid)
        text, size = texts[pid], sizes[pid]
        if not isinstance(text, str) or not text.strip():
            raise Stop('PASSAGE_NOT_USABLE', 'Passage %s has no text.' % pid)
        if size['passage_size_count'] < 1 or size['role_size_count'] < 1:
            raise Stop('SIZE_NOT_USABLE', 'Passage %s has a size count below 1.' % pid)
        if len(word_rule.findall(text)) != size['passage_words'] or len(size_rule.findall(text)) != size['passage_size_count']:
            raise Stop('SIZE_DOES_NOT_MATCH_PASSAGE', 'The passage counts stored with the role note of %s are not the counts of its passage text.' % pid)
        targets = word_targets(rules, size)
        row = {'passage_id': pid, 'role_size_count': size['role_size_count'], 'passage_words': size['passage_words'],
               'passage_size_count': size['passage_size_count'], 'notes': {}}
        for group in groups:
            row['notes'][group] = {}
            for length in lengths:
                slot = {'target_words': targets[length], 'current': 1, 'versions': []}
                row['notes'][group][length] = slot
                slots[(pid, group, length)] = slot
                for name in FRAME_OF_STEP:
                    prompts[(pid, group, length, name)] = build_prompt(briefs, group, name, targets[length], text)
        passages.append(row)

    # the support check results say which notes may be written again; nothing else can
    results = ctx.read_json(results_path) if results_path.exists() else None
    failed_first = set()
    if results is not None:
        if results.get('set') != set_name:
            raise Stop('WRONG_FILE', 'support/support_results_%s.json is not the results file of this set.' % set_name)
        failed_first = {row['note_id'] for row in results['results'] if row['round'] == 1 and row['verdict'] in FAILED_VERDICTS}

    # the call log is the record; the notes file is rebuilt from it
    content_failures = {}
    for row in read_jsonl(log_path):
        found = NOTE_ID.fullmatch(row['note_id'])
        key = (found.group(1), found.group(2), found.group(3)) if found else None
        if key not in slots or row.get('frame') not in FRAME_OF_STEP or int(found.group(4)) != VERSION_OF_STEP[row['frame']]:
            raise Stop('LOG_DOES_NOT_MATCH_PLAN', 'The call log holds the note %s, which this set does not plan.' % row['note_id'])
        if row['prompt_sha256'] != sha_text(prompts[key + (row['frame'],)]):
            raise Stop('LOG_DOES_NOT_MATCH_PLAN', 'A logged call for %s used another brief, target or passage than the plan gives now.' % row['note_id'])
        if not row['ok']:
            if row['http_status'] == 200:
                content_failures[row['note_id']] = content_failures.get(row['note_id'], 0) + 1
            continue
        slot, version = slots[key], int(found.group(4))
        if version != len(slot['versions']) + 1:
            raise Stop('LOG_OUT_OF_ORDER', 'The call log holds version %d of %s twice or out of order.' % (version, row['note_id']))
        if version == 2 and '%s|%s|%s|v1' % key not in failed_first:
            raise Stop('REWRITE_WITHOUT_FAILED_CHECK', 'The call log holds a second version of %s, and no failed support check is on record for its first version.' % row['note_id'])
        text = clean_note(rules, row['reply'])
        slot['versions'].append({'version': version, 'text': text, 'words': len(word_rule.findall(text)), 'size_count': len(size_rule.findall(text)),
                                 'prompt_sha256': row['prompt_sha256'], 'reply_sha256': row['reply_sha256'], 'utc': row['utc']})
        slot['current'] = version

    # a notes file from an earlier run may hold less than the log (a killed run), never anything else
    if notes_path.exists():
        old = load_own(notes_path)
        old_slots = {(p['passage_id'], g, n): p['notes'][g][n] for p in old['passages'] for g in p['notes'] for n in p['notes'][g]}
        if old.get('set') != set_name or set(old_slots) != set(slots):
            raise Stop('NOTES_FILE_DOES_NOT_MATCH_PLAN', 'notes_ord/ordinary_notes_%s.json was started for other passages. The selection changed since then.' % set_name)
        for key, old_slot in old_slots.items():
            if old_slot['target_words'] != slots[key]['target_words'] or old_slot['versions'] != slots[key]['versions'][:len(old_slot['versions'])]:
                raise Stop('NOTES_FILE_DOES_NOT_MATCH_LOG', 'The stored note %s|%s|%s is not what the call log gives. Look at both files before going on.' % key)

    def save():
        if log_path.exists():
            ctx.inputs[rel(log_path)] = sha_bytes(log_path.read_bytes())
        ctx.write_json(notes_path, 'casalescence/optionb/ordinary_notes/v1', {'set': set_name, 'writer': model, 'passages': passages})

    save()

    # what is due in this step
    jobs = []
    if step == 'first':
        for key, slot in slots.items():
            if not slot['versions']:
                jobs.append(key + (1,))
    else:
        if results is None:
            raise Stop('NO_SUPPORT_RESULTS', 'support/support_results_%s.json does not exist. A note is written again only after a failed support check.' % set_name)
        for passage in results['passages']:
            if passage['status'] != 'REWRITE_NEEDED':
                continue
            for note_id in passage['rewrite_note_ids']:
                found = NOTE_ID.fullmatch(note_id)
                key = (found.group(1), found.group(2), found.group(3)) if found else None
                if key not in slots or found.group(4) != '1' or found.group(1) != passage['passage_id'] or note_id not in failed_first:
                    raise Stop('RESULTS_DO_NOT_MATCH_PLAN', 'The support results list %s for a rewrite, and no failed first check of that note is on record.' % note_id)
                if len(slots[key]['versions']) == 1:
                    jobs.append(key + (2,))
    jobs.sort()
    due_at_start = len(jobs)

    if ctx.dry:
        if args.max_calls > 0 and not args.replay_replies:
            raise Stop('DRY_FIXTURE_NEEDS_REPLAY', 'No outside call is ever made from a dry folder. Give --replay-replies.')
        send, key_text, pace, wait_after_error = (replay_sender(args.replay_replies) if args.replay_replies else None), '', 0.0, 0.0
    else:
        if args.replay_replies:
            raise Stop('REPLAY_ONLY_IN_DRY_FOLDER', '--replay-replies is refused outside optionb/dry/.')
        key_text, pace, wait_after_error = os.environ.get(service['key_environment_variable'], '').strip(), max(0.0, args.pace), max(0.0, args.wait_after_error)
        if args.max_calls > 0 and jobs and not key_text:
            raise Stop('KEY_NOT_SET', 'The environment variable %s is not set.' % service['key_environment_variable'])

        def send(note_id, prompt):
            body = {'model': model, 'temperature': service['temperature'], 'messages': [{'role': 'user', 'content': prompt}]}
            if 'max_tokens' in service:  # sent only if the plan constants name it
                body['max_tokens'] = service['max_tokens']
            return http_send(service['endpoint'], key_text, body, args.timeout)

    lock, halt = threading.Lock(), threading.Event()
    run = {'calls': 0, 'written': 0, 'status': None, 'failures_in_a_row': 0, 'tokens': {}, 'new_content_failures': []}

    def stop_run(status):
        with lock:
            run['status'] = run['status'] or status
        halt.set()

    def work(job):
        pid, group, length, version = job
        frame = 'first' if version == 1 else 'rewrite'
        note_id = '%s|%s|%s|v%d' % job
        prompt = prompts[(pid, group, length, frame)]
        content_tries = 0
        for attempt in range(1 + service['transport_retries'] + service['content_retries']):
            with lock:
                if halt.is_set():
                    return
                if run['calls'] >= args.max_calls:
                    run['status'] = run['status'] or 'STOPPED_CALL_BUDGET'
                    halt.set()
                    return
                # Amendment A11: at a token limit no call is made. Calls that are already running still finish.
                if used is not None and limit_reached(used, service):
                    run['status'] = run['status'] or service['spend_cap_stop_status']
                    halt.set()
                    return
                run['calls'] += 1
            time.sleep(pace)
            result = send(note_id, prompt)
            if result is None:
                with lock:
                    run['calls'] -= 1
                stop_run('STOPPED_REPLAY_EXHAUSTED')
                return
            status, error = result['http_status'], result['error']
            text = clean_note(rules, result['content'])
            if error is None and status == 200:
                if result.get('finish_reason') == 'length':
                    error = 'REPLY_CUT_OFF'
                elif not text:
                    error = 'REPLY_EMPTY'
            ok = error is None and status == 200
            row = {'utc': ctx.now(), 'note_id': note_id, 'frame': frame, 'model': model, 'model_in_reply': result.get('model_in_reply'),
                   'usage': result.get('usage'), 'http_status': status, 'ok': ok,
                   'error': scrub(error, key_text) if error else None, 'prompt_sha256': sha_text(prompt),
                   'reply_sha256': sha_text(result['content']), 'prompt': prompt, 'reply': result['content']}
            with lock:
                append_jsonl(log_path, row)
                for name, value in (result.get('usage') or {}).items():
                    if isinstance(value, int) and not isinstance(value, bool):
                        run['tokens'][name] = run['tokens'].get(name, 0) + value
                if used is not None:
                    pair = usage_pair(result.get('usage'))
                    if pair:
                        used[0] += pair[0]
                        used[1] += pair[1]
                    elif status == 200:
                        # a reply with HTTP status 200 and no token count: it is logged, then the tool stops
                        run['status'] = run['status'] or service['spend_cap_no_count_status']
                        halt.set()
                if ok:
                    slot = slots[(pid, group, length)]
                    slot['versions'].append({'version': version, 'text': text, 'words': len(word_rule.findall(text)),
                                             'size_count': len(size_rule.findall(text)), 'prompt_sha256': row['prompt_sha256'],
                                             'reply_sha256': row['reply_sha256'], 'utc': row['utc']})
                    slot['current'] = version
                    run['written'] += 1
                    run['failures_in_a_row'] = 0
                    if run['written'] % 10 == 0:
                        save()
            if ok:
                return
            if status == 429:
                stop_run('STOPPED_HTTP_429')
                return
            if status in KEY_REFUSED:
                stop_run('STOPPED_KEY_OR_ACCOUNT_REFUSED')
                return
            if status == 200 or status in SAME_CALL_WOULD_FAIL:
                content_tries += 1
                if content_tries > service['content_retries']:
                    with lock:
                        run['new_content_failures'].append(note_id)
                    return
                continue
            with lock:
                run['failures_in_a_row'] += 1
                too_many = run['failures_in_a_row'] >= args.max_transport_failures
            if too_many:
                stop_run('STOPPED_NO_ANSWER_FROM_SERVICE')
                return
            time.sleep(wait_after_error)

    if args.max_calls > 0 and jobs:
        with ThreadPoolExecutor(max_workers=1 if ctx.dry else args.workers) as pool:
            list(pool.map(work, jobs))
    save()

    still_open = [job for job in jobs if len(slots[job[:3]]['versions']) < job[3]]
    status = run['status']
    if status is None:
        status = 'ALL_WRITTEN' if not still_open else ('PLAN_ONLY' if args.max_calls == 0 else 'STOPPED_NOTES_NOT_WRITTEN')
    elif not still_open and status != service['spend_cap_no_count_status']:
        status = 'ALL_WRITTEN'

    written = [slot for slot in slots.values() if slot['versions']]
    by_length = {}
    for (pid, group, length), slot in sorted(slots.items()):
        if slot['versions']:
            part = by_length.setdefault('%s %s' % (group, length), [0, 0])
            part[0] += slot['versions'][slot['current'] - 1]['words']
            part[1] += slot['target_words']
    print(json.dumps({
        'program': PROGRAM, 'dry_fixture': ctx.dry, 'status': status, 'set': set_name, 'step': step, 'writer': model, 'seal': seal,
        'passages_that_carry_a_task': len(ids), 'notes_planned': len(slots),
        'notes_with_version_1': len(written), 'notes_with_version_2': sum(1 for slot in slots.values() if len(slot['versions']) == 2),
        'due_in_this_step_at_start': due_at_start, 'still_open_in_this_step': len(still_open),
        'calls_this_run': run['calls'], 'call_budget': args.max_calls, 'notes_written_this_run': run['written'],
        'tokens_this_run_as_the_service_reported': run['tokens'],
        'deepseek_tokens_in_the_four_call_logs': (None if used is None else {'input': used[0], 'output': used[1]}),
        'deepseek_token_limits': {'input': service['spend_cap_input_tokens'], 'output': service['spend_cap_output_tokens']},
        'model_names_in_the_replies': sorted({str(row.get('model_in_reply')) for row in read_jsonl(log_path) if row['http_status'] == 200}),
        'empty_or_cut_off_replies_this_run': sorted(run['new_content_failures']),
        'empty_or_cut_off_replies_in_the_log': dict(sorted(content_failures.items())),
        'words_written_and_words_asked_for_per_brief_and_length': by_length,
        'next': {'ALL_WRITTEN': 'Everything due in this step is written. Next: tools/ob_check_support.py.',
                 'PLAN_ONLY': 'No call was made. The plan is written. Run again with a call budget.',
                 'STOPPED_CALL_BUDGET': 'The call budget of this run is used up. The log is kept. Run the same command again.',
                 'STOPPED_HTTP_429': 'The service answered HTTP 429 (too many requests). The log is kept. Run the same command later.',
                 'STOPPED_KEY_OR_ACCOUNT_REFUSED': 'The service refused the key or the account. Nothing else was sent. Check the key and the credit.',
                 'STOPPED_NO_ANSWER_FROM_SERVICE': 'The service gave no answer several times in a row. The log is kept. Run the same command later.',
                 'STOPPED_NOTES_NOT_WRITTEN': 'Some notes are still not written (no answer, or an empty or cut-off reply). Run the same command again. '
                                              'If the same note fails again, report it: the plan has no rule for a note the writer can not produce.',
                 service['spend_cap_stop_status']: 'A DeepSeek token limit is reached. No further call is made. The log is kept. '
                                                   'A limit is never raised without a new reviewed plan version. Report this.',
                 service['spend_cap_no_count_status']: 'A reply came back with no token count. It is logged. The tool stopped, because the '
                                                       'spend can not be counted without it. Report this.',
                 'STOPPED_REPLAY_EXHAUSTED': 'The made-up reply file has no reply for the next note.'}[status]}, ensure_ascii=False, indent=1))
    return 0 if status == 'ALL_WRITTEN' else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Stop as stop:
        print(json.dumps({'program': PROGRAM, 'status': 'STOP', 'code': stop.args[0], 'reason': stop.args[1]}, ensure_ascii=False, indent=1))
        sys.exit(2)
