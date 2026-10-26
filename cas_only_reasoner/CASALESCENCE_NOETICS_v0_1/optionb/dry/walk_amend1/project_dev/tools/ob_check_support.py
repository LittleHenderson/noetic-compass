"""Option B, Step 7 (second half). The support check of the ordinary notes.

The one question asked about every ordinary note: is every sentence of the note supported by its
passage? The answer is PASS or FAIL. A FAIL is the only thing that can cause a note to be written
again (once, by tools/ob_write_ordinary_notes.py). A second FAIL drops the passage for every group.

What the checker can see: a neutral item id, the passage and the note. Nothing else.
The prompt is built by build_prompt(), which is given a list of (item id, passage text, note text)
only. The checker is not told the group or the length.
From elig/eligibility.json this tool keeps only id and text. It never opens a label file, a role
note, a question, a key, the labeling guide or a key file of an outside service.

The key of the outside service is read from the environment at run time. It is never read from a
file, never printed and never stored. Error texts are scrubbed of the key before they are logged.

Commands:
  gemini --max-calls N   Call the checker (Gemini) batch by batch. A batch is the six notes of two
                         passages: 12 items. When the service refuses, the tool stops cleanly. Run it
                         again later. --max-calls 0 writes the plan and calls nobody.
  decide                 Works out the status of every passage and writes the results file.
  status                 Prints where things stand. Writes nothing.

Rounds: round 1 checks version 1 of every note. Round 2 checks the rewritten notes (version 2), in
batches of up to 12 items in note-id order. Round 2 starts only when round 1 is finished and every
needed second version is written.

One checker (amendment A2; plan section 10 Step 7; FILE_FORMATS.md section 9;
outside_services.gemini_support_checker.one_checker_rule). The Gemini model named in
PLAN_CONSTANTS.json is the only checker of the ordinary notes, for both sets and both rounds.
There is no fallback checker and no Claude checker. This tool has no export step and no import step.
  - A daily-cap refusal is an HTTP 429 reply whose error text matches daily_cap_error_regex. Only such
    a call log line gets the mark "DAILY_CAP_STOP: ". The gemini step then stops with STOPPED_DAILY_CAP.
  - Any other HTTP 429 reply is a rate refusal. It never gets the mark. After the allowed waits the
    gemini step stops with STOPPED_RATE_LIMIT.
  - After either stop the checkpoint is kept. The build waits: the same step is run again later.
    No batch ever moves to another checker. A refused call is not counted as a try.

Every call log line holds the model name the tool asked for and the model name the service put in
its reply (amendment A9). The tool stores the reply's name as it is. It does not judge it.

An item with no readable verdict is asked once more. If it is still unreadable it counts as FAIL.

The record is the call log. The checkpoint, the item map and the results file are rebuilt from it at
every start. So a killed run loses nothing and can not cause an extra try.

Files (FILE_FORMATS.md section 9):
  support/support_state_<set>.json                 the checkpoint
  support/support_items_<set>.json                 the private map item id -> note id
  support/support_calls_<set>.jsonl                one line per Gemini call
  support/support_results_<set>.json               verdicts per note, status per passage

Exit codes: 0 = the command finished and nothing is waiting. 1 = something is still open (the reason
is printed). 2 = not started or stopped by a check.

Dry fixture: with --work pointing under optionb/dry/ the tool never calls an outside service. The
command gemini then needs --replay-replies FILE (made-up replies, in order). --dry-now sets a made-up
clock. Both options are refused outside optionb/dry/. Every output is marked as a dry fixture.
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
import urllib.error
import urllib.request
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
UTC_FORM = '%Y-%m-%dT%H:%M:%SZ'
LF = chr(10)

SEAL_NEED = {'practice': ['1_PLAN_AND_SOURCES', '2_ROLE_NOTES', '3A_PRACTICE_QUESTIONS_AND_KEYS', '3B_PRACTICE_SET_FIXED'],
             'final': ['1_PLAN_AND_SOURCES', '2_ROLE_NOTES', '3A_PRACTICE_QUESTIONS_AND_KEYS', '3B_PRACTICE_SET_FIXED',
                       '3C_FINAL_QUESTIONS_AND_KEYS']}
SEAL_CLOSED_BY = '4_ORDINARY_NOTES'
VERDICTS = ('PASS', 'FAIL')
FAILED_VERDICTS = ('FAIL', 'UNREADABLE')
CAP_STOP_MARK = 'DAILY_CAP_STOP: '
NOTE_ID = re.compile(r'(.+)\|([A-Z-]+)\|([0-9]{3})\|v([0-9]+)')
KEY_REFUSED = (401, 402, 403)
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
    """The work folder, the plan constants, the clock and the list of files this run has read."""

    def __init__(self, work_arg, dry_now=None):
        work = Path(work_arg).resolve() if work_arg else REAL_WORK
        self.dry = work != REAL_WORK
        if self.dry and DRY_BASE not in work.parents:
            raise Stop('WORK_FOLDER_NOT_ALLOWED', 'A work folder other than optionb/ must sit under optionb/dry/.')
        if dry_now and not self.dry:
            raise Stop('DRY_OPTION_OUTSIDE_DRY_FOLDER', '--dry-now is refused outside optionb/dry/.')
        if dry_now:
            parse_utc(dry_now)
        self.dry_now = dry_now
        self.work = work
        self.inputs = {}
        self.constants = self.read_json(REAL_WORK / 'PLAN_CONSTANTS.json')
        over = work / OVERRIDES_NAME
        if self.dry and over.exists():
            merge(self.constants, self.read_json(over))

    def now(self):
        return self.dry_now or datetime.datetime.now(datetime.timezone.utc).strftime(UTC_FORM)

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


def parse_utc(text):
    try:
        return datetime.datetime.strptime(text, UTC_FORM).replace(tzinfo=datetime.timezone.utc)
    except (TypeError, ValueError):
        raise Stop('BAD_TIME', 'A time must look like 2026-10-06T10:00:00Z. Got: %r' % (text,))


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


# ---------------------------------------------------------------- what the checker may see

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


def build_prompt(brief, fence, triples):
    """The whole prompt: the support brief, one empty line, the fenced items with one empty line between them.

    triples is a list of (item id, passage text, note text). This function is given nothing else,
    so a group name, a length, a question, a key or a label can not reach the prompt.
    """
    blocks = [fill(fence, {'ID': item_id, 'PASSAGE': passage, 'NOTE': note}) for item_id, passage, note in triples]
    return brief + LF + LF + (LF + LF).join(blocks)


def parse_verdicts(text, wanted):
    """Read a reply. Returns {item id: PASS or FAIL} for the wanted items that have one clear verdict."""
    text = (text or '').strip()
    if text.startswith('```'):
        text = text.split(LF, 1)[1] if LF in text else ''
        text = text.rsplit('```', 1)[0]
    try:
        value = json.loads(text)
    except ValueError:
        first, last = text.find('['), text.rfind(']')
        try:
            value = json.loads(text[first:last + 1]) if 0 <= first < last else None
        except ValueError:
            value = None
    if not isinstance(value, list):
        return {}
    found, unclear = {}, set()
    for entry in value:
        if not isinstance(entry, dict) or not isinstance(entry.get('item'), str) or not isinstance(entry.get('verdict'), str):
            continue
        item_id, verdict = entry['item'].strip(), entry['verdict'].strip().upper()
        if item_id not in wanted:
            continue
        if verdict not in VERDICTS or found.get(item_id, verdict) != verdict:
            unclear.add(item_id)
        found[item_id] = verdict
    return {item_id: verdict for item_id, verdict in found.items() if item_id not in unclear}


# ---------------------------------------------------------------- talking to the service

def scrub(text, key):
    return text.replace(key, '[KEY]') if key else text


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
        detail = error.read()[:4000].decode('utf-8', 'replace')
        return dict(blank, http_status=error.code, error=scrub('HTTPError %d: %s' % (error.code, detail), key))
    except Exception as error:
        return dict(blank, http_status=0, error=scrub('%s: %s' % (type(error).__name__, str(error)[:300]), key))
    try:
        doc = json.loads(payload)
        content = doc['choices'][0]['message'].get('content') or ''
    except Exception as error:
        return dict(blank, http_status=status, error='REPLY_ENVELOPE_UNREADABLE: ' + type(error).__name__)
    return {'http_status': status, 'content': content, 'error': None, 'usage': doc.get('usage'), 'model_in_reply': reply_model(doc)}


def replay_sender(path):
    """Dry fixture only. Made-up replies are read from a file, in order. No outside call.

    A made-up reply may carry a made-up model name under "model"; it is stored as model_in_reply.
    """
    steps = json.loads(Path(path).read_text(encoding='utf-8'))
    position = [0]

    def send(prompt):
        if position[0] >= len(steps):
            return None
        step = steps[position[0]]
        position[0] += 1
        content = step.get('content')
        if 'content_json' in step:
            content = json.dumps(step['content_json'], ensure_ascii=False)
        return {'http_status': step['http_status'], 'content': content or '', 'error': step.get('error'), 'usage': None,
                'model_in_reply': reply_model(step)}
    return send


def is_daily_cap(pattern, error_text):
    """True when the error text of a refused call names the daily limit. pattern is daily_cap_error_regex of the plan constants."""
    return bool(re.search(pattern, error_text or '', flags=re.I))


def retry_delay(error_text):
    found = re.search(r'retry(?:Delay)?\D{0,12}(\d+(?:\.\d+)?)\s*s', error_text or '', flags=re.I)
    return float(found.group(1)) if found else 60.0


# ---------------------------------------------------------------- the state, rebuilt from the records

class Book:
    """Everything this tool knows about one set, worked out from the records on disk."""

    def __init__(self, ctx, set_name):
        C = ctx.constants
        self.ctx, self.set_name = ctx, set_name
        self.checker = C['outside_services']['gemini_support_checker']
        self.rules = C['ordinary_notes']
        self.model = DRY_MODEL if ctx.dry else self.checker['model']
        self.cap_regex = self.checker['daily_cap_error_regex']
        self.retries = self.checker['unreadable_reply_retries']
        self.per_batch = self.checker['notes_per_call']
        self.prefix = C['solver_rules']['item_id_prefix']['support']
        self.digits = C['solver_rules']['item_id_digits']
        self.brief = LF.join(C['briefs']['support_brief'])
        self.fence = LF.join(C['briefs']['support_item_fence'])
        self.dir = ctx.work / 'support'
        self.state_path = self.dir / ('support_state_%s.json' % set_name)
        self.items_path = self.dir / ('support_items_%s.json' % set_name)
        self.log_path = self.dir / ('support_calls_%s.jsonl' % set_name)
        self.results_path = self.dir / ('support_results_%s.json' % set_name)
        self.texts = passage_texts(ctx)
        self.load_notes()
        self.rebuild()

    # ---- the notes

    def load_notes(self):
        ctx, set_name = self.ctx, self.set_name
        path = ctx.work / 'notes_ord' / ('ordinary_notes_%s.json' % set_name)
        if not path.exists():
            raise Stop('NO_NOTES_YET', 'notes_ord/ordinary_notes_%s.json does not exist. Run tools/ob_write_ordinary_notes.py first.' % set_name)
        doc = ctx.read_json(path)
        if doc.get('schema') != 'casalescence/optionb/ordinary_notes/v1' or doc.get('set') != set_name:
            raise Stop('WRONG_FILE', 'notes_ord/ordinary_notes_%s.json is not the notes file of this set.' % set_name)
        self.note_text, self.passage_ids, missing = {}, [], 0
        groups, lengths = list(self.rules['briefs_in_order']), list(self.rules['lengths_in_order'])
        for passage in doc['passages']:
            pid = passage['passage_id']
            if pid not in self.texts:
                raise Stop('PASSAGE_WITHOUT_TEXT', 'Passage %s has notes and no passage text.' % pid)
            self.passage_ids.append(pid)
            for group in groups:
                for length in lengths:
                    versions = passage['notes'][group][length]['versions']
                    missing += 0 if versions else 1
                    for version in versions:
                        self.note_text['%s|%s|%s|v%d' % (pid, group, length, version['version'])] = version['text']
        if missing:
            raise Stop('NOTES_NOT_ALL_WRITTEN', '%d notes of this set have no first version yet. Run tools/ob_write_ordinary_notes.py --step first.' % missing)
        self.passage_ids.sort()
        self.groups, self.lengths = groups, lengths

    def triples(self, item_ids):
        out = []
        for item_id in item_ids:
            note_id = self.items[item_id]['note_id']
            out.append((item_id, self.texts[NOTE_ID.fullmatch(note_id).group(1)], self.note_text[note_id]))
        return out

    def item_name(self, number):
        return self.prefix + str(number).zfill(self.digits)

    # ---- a daily-cap refusal

    def is_cap_refusal(self, row):
        """A call log line that is a daily-cap refusal: HTTP 429, the mark, and an error text that names the daily limit."""
        error = row.get('error') or ''
        return (row['http_status'] == 429 and error.startswith(CAP_STOP_MARK)
                and is_daily_cap(self.cap_regex, error[len(CAP_STOP_MARK):]))

    # ---- the rebuild

    def rebuild(self):
        self.items, self.rounds, self.verdict = {}, [], {}
        log, in_order = {}, read_jsonl(self.log_path)
        self.cap_stops = []
        for row in in_order:
            log.setdefault((row['round'], row['batch']), []).append(row)
            if self.is_cap_refusal(row):
                self.cap_stops.append(row['utc'])
        if self.log_path.exists():
            self.ctx.inputs[rel(self.log_path)] = sha_bytes(self.log_path.read_bytes())
        self.log = log

        # round 1: passages sorted, shuffled with the fixed seed, cut into groups; six notes per passage
        order = list(self.passage_ids)
        random.Random(self.ctx.constants['seeds']['support_batch_order']).shuffle(order)
        per = self.checker['passages_per_call']
        number, batches = 0, []
        for index in range(0, len(order), per):
            item_ids = []
            for pid in order[index:index + per]:
                for group in self.groups:
                    for length in self.lengths:
                        number += 1
                        item_id = self.item_name(number)
                        self.items[item_id] = {'item_id': item_id, 'note_id': '%s|%s|%s|v1' % (pid, group, length), 'round': 1,
                                               'checker': self.model, 'sheet': '00'}
                        item_ids.append(item_id)
            if len(item_ids) > self.per_batch:
                raise Stop('PLAN_DOES_NOT_MATCH_PROGRAM', 'A batch of %d passages holds more than %d notes.' % (per, self.per_batch))
            batches.append({'batch': len(batches), 'item_ids': item_ids, 'status': 'PENDING', 'attempts': 0})
        self.rounds.append({'round': 1, 'batches': batches})
        for batch in batches:
            self.settle(1, batch)

        # round 2: the rewritten notes, once round 1 is finished and every second version is written.
        # The same checker judges them (amendment A2): there is one checker, for both sets and both rounds.
        self.round_2_waits_for = None
        first_items = list(self.items.values())
        if any(item['item_id'] not in self.verdict for item in first_items):
            self.round_2_waits_for = 'ROUND_1'
        else:
            failed = sorted(item['note_id'] for item in first_items if self.verdict[item['item_id']] in FAILED_VERDICTS)
            second = [note_id[:-1] + '2' for note_id in failed]
            if any(note_id not in self.note_text for note_id in second):
                self.round_2_waits_for = 'REWRITE'
            elif second:
                mine = []
                for note_id in sorted(second):
                    number += 1
                    item_id = self.item_name(number)
                    self.items[item_id] = {'item_id': item_id, 'note_id': note_id, 'round': 2, 'checker': self.model, 'sheet': '00'}
                    mine.append(item_id)
                batches = []
                for index in range(0, len(mine), self.per_batch):
                    batch = {'batch': len(batches), 'item_ids': mine[index:index + self.per_batch], 'status': 'PENDING', 'attempts': 0}
                    batches.append(batch)
                    self.settle(2, batch)
                self.rounds.append({'round': 2, 'batches': batches})
        known = {(r['round'], b['batch']) for r in self.rounds for b in r['batches']}
        if set(log) - known:
            raise Stop('LOG_DOES_NOT_MATCH_PLAN', 'The call log holds a batch that the plan does not know.')

    def settle(self, round_number, batch):
        """Work out the status of one batch from the call log."""
        rows = self.log.get((round_number, batch['batch']), [])
        counted = [row for row in rows if row['http_status'] == 200]
        if len(counted) > 1 + self.retries:
            raise Stop('TOO_MANY_TRIES_IN_LOG', 'Round %d batch %d was asked more often than the plan allows.' % (round_number, batch['batch']))
        open_items = list(batch['item_ids'])
        for row in rows:
            if row['item_ids'] != open_items or row['prompt_sha256'] != sha_text(build_prompt(self.brief, self.fence, self.triples(open_items))):
                if row['http_status'] == 200 or not set(row['item_ids']) <= set(batch['item_ids']):
                    raise Stop('LOG_DOES_NOT_MATCH_PLAN', 'A logged call for round %d batch %d used other items, notes or passages than the plan gives now.' % (round_number, batch['batch']))
            if row['http_status'] != 200:
                continue
            found = parse_verdicts(row['reply'], set(open_items))
            self.verdict.update(found)
            open_items = [item_id for item_id in open_items if item_id not in found]
            batch['attempts'] += 1
        if not open_items:
            batch['status'] = 'DONE'
        elif batch['attempts'] >= 1 + self.retries:
            batch['status'] = 'UNREADABLE'
            for item_id in open_items:
                self.verdict[item_id] = 'UNREADABLE'
        batch['open_items'] = open_items

    # ---- what follows from the verdicts

    def results_body(self):
        rows = [{'note_id': item['note_id'], 'item_id': item_id, 'checker': item['checker'], 'round': item['round'], 'verdict': self.verdict[item_id]}
                for item_id, item in sorted(self.items.items()) if item_id in self.verdict]
        by_note = {row['note_id']: row for row in rows}
        passages, dropped, failed_once, failed_twice = [], 0, 0, 0
        for pid in self.passage_ids:
            first = ['%s|%s|%s|v1' % (pid, group, length) for group in self.groups for length in self.lengths]
            failed = [note_id for note_id in first if note_id in by_note and by_note[note_id]['verdict'] in FAILED_VERDICTS]
            second = [note_id[:-1] + '2' for note_id in failed]
            failed_once += len(failed)
            twice = [note_id for note_id in second if note_id in by_note and by_note[note_id]['verdict'] in FAILED_VERDICTS]
            failed_twice += len(twice)
            if any(note_id not in by_note for note_id in first):
                status = 'UNCHECKED'
            elif any(note_id not in self.note_text for note_id in second):
                status = 'REWRITE_NEEDED'
            elif any(note_id not in by_note for note_id in second):
                status = 'UNCHECKED'
            elif twice:
                status = 'DROPPED_SECOND_FAILURE'
                dropped += 1
            else:
                status = 'ALL_PASS'
            passages.append({'passage_id': pid, 'status': status, 'rewrite_note_ids': failed})
        counts = {'notes_checked': len(rows), 'passed': sum(1 for row in rows if row['verdict'] == 'PASS'),
                  'failed_once': failed_once, 'failed_twice': failed_twice, 'passages_dropped': dropped}
        return {'set': self.set_name, 'results': rows, 'passages': passages, 'counts': counts}

    def state_body(self):
        rounds = [{'round': r['round'], 'batches': [{name: b[name] for name in ('batch', 'item_ids', 'status', 'attempts')} for b in r['batches']]}
                  for r in self.rounds]
        return {'set': self.set_name, 'model': self.model, 'rounds': rounds, 'cap_stops_utc': list(self.cap_stops),
                'first_cap_stop_utc': min(self.cap_stops) if self.cap_stops else None,
                'complete': all(b['status'] != 'PENDING' for r in self.rounds for b in r['batches'])}

    def save(self):
        ctx = self.ctx
        if self.state_path.exists():
            old = load_own(self.state_path)
            if old.get('model') != self.model:
                raise Stop('ONE_CHECKER_MODEL_PER_SET', 'The checkpoint names the checker %s. This run would use %s.' % (old.get('model'), self.model))
        ctx.write_json(self.items_path, 'casalescence/optionb/support_items/v1',
                       {'set': self.set_name, 'items': [self.items[item_id] for item_id in sorted(self.items)]})
        ctx.write_json(self.results_path, 'casalescence/optionb/support_results/v1', self.results_body())
        ctx.write_json(self.state_path, 'casalescence/optionb/support_state/v1', self.state_body())

    def pending(self):
        return [(r['round'], b) for r in self.rounds for b in r['batches'] if b['status'] == 'PENDING']

    def summary(self):
        body = self.results_body()
        by_status = {}
        for passage in body['passages']:
            by_status[passage['status']] = by_status.get(passage['status'], 0) + 1
        batches = [b for r in self.rounds for b in r['batches']]
        ready = bool(body['passages']) and all(p['status'] in ('ALL_PASS', 'DROPPED_SECOND_FAILURE') for p in body['passages'])
        names = sorted({str(row.get('model_in_reply')) for rows in self.log.values() for row in rows if row['http_status'] == 200})
        return {'set': self.set_name, 'checker': self.model, 'model_names_in_the_replies': names,
                'passages': len(self.passage_ids), 'passages_by_status': dict(sorted(by_status.items())),
                'notes': body['counts'],
                'batches': {name: sum(1 for b in batches if b['status'] == name) for name in ('DONE', 'PENDING', 'UNREADABLE')},
                'rounds_planned': [r['round'] for r in self.rounds], 'round_2_waits_for': self.round_2_waits_for,
                'daily_cap_stops': len(self.cap_stops), 'first_cap_stop_utc': min(self.cap_stops) if self.cap_stops else None,
                'ready_for_seal_step_4': ready}


# ---------------------------------------------------------------- the commands

def run_gemini(ctx, book, args):
    checker = book.checker
    book.save()
    if ctx.dry:
        if args.max_calls > 0 and not args.replay_replies:
            raise Stop('DRY_FIXTURE_NEEDS_REPLAY', 'No outside call is ever made from a dry folder. Give --replay-replies.')
        send, key, pace = (replay_sender(args.replay_replies) if args.replay_replies else None), '', 0.0
    else:
        if args.replay_replies:
            raise Stop('REPLAY_ONLY_IN_DRY_FOLDER', '--replay-replies is refused outside optionb/dry/.')
        key, pace = os.environ.get(checker['key_environment_variable'], '').strip(), max(0.0, args.pace)
        if args.max_calls > 0 and book.pending() and not key:
            raise Stop('KEY_NOT_SET', 'The environment variable %s is not set.' % checker['key_environment_variable'])

        def send(prompt):
            body = {'model': book.model, 'temperature': checker['temperature'], 'max_tokens': checker['max_tokens'],
                    'messages': [{'role': 'user', 'content': prompt}]}
            for extra in ('reasoning_effort',):  # sent only if the plan constants name it
                if extra in checker:
                    body[extra] = checker[extra]
            return http_send(checker['endpoint'], key, body, args.timeout)

    calls, waits, failures, status = 0, 0, 0, None
    while status is None:
        todo = book.pending()
        if not todo:
            break
        round_number, batch = todo[0]
        if calls >= args.max_calls:
            status = 'STOPPED_CALL_BUDGET'
            break
        time.sleep(pace)
        item_ids = list(batch['open_items'])
        prompt = build_prompt(book.brief, book.fence, book.triples(item_ids))
        result = send(prompt)
        if result is None:
            status = 'STOPPED_REPLAY_EXHAUSTED'
            break
        calls += 1
        error = result['error']
        # Only a refusal whose error text names the daily limit is a daily-cap stop. Any other HTTP 429 is a rate
        # refusal: it never gets the mark, whatever --rate-waits says.
        cap_stop = result['http_status'] == 429 and is_daily_cap(book.cap_regex, error)
        if cap_stop:
            error = CAP_STOP_MARK + error
        row = {'utc': ctx.now(), 'model': book.model, 'model_in_reply': result['model_in_reply'], 'round': round_number, 'batch': batch['batch'], 'item_ids': item_ids,
               'attempt': batch['attempts'] + 1, 'http_status': result['http_status'], 'ok': result['http_status'] == 200 and result['error'] is None,
               'error': scrub(error, key) if error else None, 'prompt_sha256': sha_text(prompt), 'reply_sha256': sha_text(result['content']),
               'prompt': prompt, 'reply': result['content']}
        append_jsonl(book.log_path, row)
        if result['http_status'] == 200:
            waits, failures = 0, 0
        elif result['http_status'] == 429:
            # a refused call is not counted as a try
            if cap_stop:
                status = 'STOPPED_DAILY_CAP'
            elif waits >= args.rate_waits:
                status = 'STOPPED_RATE_LIMIT'
            else:
                waits += 1
                if not ctx.dry:
                    time.sleep(min(max(retry_delay(result['error']), pace), 120.0))
        elif result['http_status'] in KEY_REFUSED:
            status = 'STOPPED_KEY_OR_ACCOUNT_REFUSED'
        elif result['http_status'] in SAME_CALL_WOULD_FAIL:
            status = 'STOPPED_SERVICE_REFUSED_THE_REQUEST'
        else:
            failures += 1
            if failures >= args.max_transport_failures:
                status = 'STOPPED_NO_ANSWER_FROM_SERVICE'
        book.rebuild()
        book.save()
    if status is None:
        status = 'NOTHING_PENDING'
    return status, {'calls_this_run': calls, 'call_budget': args.max_calls}


NEXT = {
    'NOTHING_PENDING': 'No batch is waiting for the checker.',
    'STOPPED_CALL_BUDGET': 'The call budget of this run is used up. The log is kept. Run the same command again.',
    'STOPPED_DAILY_CAP': 'The daily cap was hit. The log is kept. The build waits: run the same command on a later day. Nobody else judges a note.',
    'STOPPED_RATE_LIMIT': 'The service refused the call for a rate limit that is not the daily cap. This is not a daily-cap stop. The log is kept. The build waits: run the same command again later. Nobody else judges a note.',
    'STOPPED_KEY_OR_ACCOUNT_REFUSED': 'The service refused the key or the account. Check the key.',
    'STOPPED_SERVICE_REFUSED_THE_REQUEST': 'The service refused the request itself. The same call would fail again. Report it.',
    'STOPPED_NO_ANSWER_FROM_SERVICE': 'The service gave no answer several times in a row. The log is kept. Run the same command later.',
    'STOPPED_REPLAY_EXHAUSTED': 'The made-up reply file has no more replies.',
    'DECIDED': 'The results file is written.',
    'STATUS_ONLY': 'Nothing was written.'}


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description='Option B Step 7: the support check of the ordinary notes.')
    parser.add_argument('command', choices=['gemini', 'decide', 'status'])
    parser.add_argument('--set', dest='set_name', required=True, choices=['practice', 'final'])
    parser.add_argument('--max-calls', type=int, default=None, help='gemini: call budget for this run; 0 = write the plan only')
    parser.add_argument('--pace', type=float, default=6.0, help='seconds to wait before each call')
    parser.add_argument('--timeout', type=float, default=180.0, help='seconds to wait for one reply')
    parser.add_argument('--rate-waits', type=int, default=2,
                        help='how often to wait out a rate refusal before stopping with STOPPED_RATE_LIMIT (never a daily-cap stop)')
    parser.add_argument('--max-transport-failures', type=int, default=3, help='stop after this many failed connections in a row')
    parser.add_argument('--work', default=None, help='dry fixture folder under optionb/dry/ (never for a real run)')
    parser.add_argument('--replay-replies', default=None, help='dry fixture only: a file of made-up replies, in order')
    parser.add_argument('--dry-now', default=None, help='dry fixture only: a made-up clock, for example 2026-10-06T10:00:00Z')
    args = parser.parse_args(argv)
    if args.command == 'gemini' and (args.max_calls is None or args.max_calls < 0):
        raise Stop('BAD_ARGUMENT', 'The command gemini needs --max-calls N with N 0 or more.')
    if args.rate_waits < 0:
        raise Stop('BAD_ARGUMENT', '--rate-waits must be 0 or more.')

    ctx = Ctx(args.work, args.dry_now)
    C = ctx.constants
    set_name = args.set_name
    if list(C['ordinary_notes']['briefs_in_order']) != list(C['groups']['ordinary']) or set(C['groups'].get('struck', [])) & set(C['groups']['ordinary']):
        raise Stop('PLAN_DOES_NOT_MATCH_PROGRAM', 'The ordinary groups in PLAN_CONSTANTS.json do not agree with each other.')
    seal, sealed = check_seal(ctx, SEAL_NEED[set_name], None if args.command == 'status' else SEAL_CLOSED_BY)
    must_be_sealed(ctx, sealed, [REAL_WORK / 'PLAN_CONSTANTS.json', ctx.work / 'elig' / 'eligibility.json'])

    book = Book(ctx, set_name)
    extra = {}
    if args.command == 'gemini':
        status, extra = run_gemini(ctx, book, args)
    elif args.command == 'decide':
        book.save()
        status = 'DECIDED'
    else:
        status = 'STATUS_ONLY'

    summary = book.summary()
    out = {'program': PROGRAM, 'dry_fixture': ctx.dry, 'command': args.command, 'status': status, 'seal': seal}
    out.update(extra)
    out.update(summary)
    out['next'] = NEXT[status]
    if summary['ready_for_seal_step_4']:
        out['next'] += ' Every passage of this set is ALL_PASS or DROPPED_SECOND_FAILURE. This set is ready for seal step 4.'
    elif summary['passages_by_status'].get('REWRITE_NEEDED'):
        out['next'] += ' Some notes failed their first check. Run tools/ob_write_ordinary_notes.py --step rewrite, then gemini again.'
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if summary['ready_for_seal_step_4'] else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Stop as stop:
        print(json.dumps({'program': PROGRAM, 'status': 'STOP', 'code': stop.args[0], 'reason': stop.args[1]}, ensure_ascii=False, indent=1))
        sys.exit(2)
