"""Option B, Step 1. Ask the blind question writer for questions, in batches.

What this tool does, in plain words:
- It sends the question brief and up to 4 fenced passages to the question writer (Gemini).
  One model writes the practice set, the final set and the spare pass (amendment A1). The name
  comes from PLAN_CONSTANTS.json. This tool has no option that names another model.
- It keeps a checkpoint. A refused call (HTTP 429) stops it cleanly. Run it again later.
- It logs every call: the model asked for, the model name the service put in its reply
  (amendment A9), batch, passage ids, prompt hash, reply hash, full prompt, raw reply.
- For the practice set it adds the wave of a reserve setting only as the reserve rule allows. It
  reads the block reserve of select/selection_practice.json, as tools/ob_select.py and
  tools/ob_seal.py do (amendment A8).

What the writer can see: the question brief and the fenced passages. Nothing else.
The prompt is built by build_prompt(), which is given a list of (passage id, passage text) pairs only.
This tool never opens the label files, a note file, the labeling guide or a key file.
It opens elig/eligibility.json, which also holds label entries. It keeps only id, text, setting,
setting_role and writer_asks, and drops everything else at once (writer_view()).
Every prompt is also tested: a prompt that holds a Noetic tag or a kind tag stops the run.

The key of the outside service is read from the environment at run time. It is never read from a
file, never printed and never stored. Error texts are scrubbed of the key before they are logged.

Usage:
  ob_write_questions.py --set practice|final --pass p1|p2|p3 --max-calls N
                        [--batch-size K] [--practice-settings 8..12] [--pace SECONDS]
  --pass p1 is the first pass. --pass p2 and --pass p3 are the later passes (same brief, different
  seeded batch order). The pass names come from outside_services.gemini_question_writer.passes in
  PLAN_CONSTANTS.json (plan v1.1); the seed of a pass is seeds.writer_batch_order_<pass>.
  --max-calls is the call budget for this run (for the day). 0 writes the plan and calls nobody.

Files (FILE_FORMATS.md section 4):
  questions/writer_state_<set>_<pass>.json   the checkpoint
  questions/writer_calls_<set>_<pass>.jsonl  one line per call
  questions/raw_questions_<set>_<pass>.json  the questions as returned

A real run does not give --batch-size (FILE_FORMATS.md section 4): the plan value is used.
The final question writer is not run, not even with --max-calls 0, before the practice set is fully
done: its first run already writes two files of the final set, and from then on a tool repair is
refused (plan section 11.1; FILE_FORMATS.md section 15.2).

Exit codes (FILE_FORMATS.md section 0): 0 = this pass of this set is written (ALL_WRITTEN).
1 = not finished: every STOPPED_ status, also a run with --max-calls 0 that leaves batches open;
run the same command again. 2 = not started or stopped by a check (the reason is printed).

Dry fixture: with --work pointing under optionb/dry/ the tool never calls an outside service.
It then needs --replay-replies FILE (made-up replies) and marks every output as a dry fixture.
"""
import argparse
import ast
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
ID_RULE = re.compile(r'[A-Za-z0-9_-]+')


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

    def header(self, schema):
        return {'schema': schema,
                'made_by': {'program': PROGRAM + (DRY_TAG if self.dry else ''), 'sha256': sha_bytes(HERE.read_bytes()), 'utc': utc_now()},
                'inputs': [{'path': p, 'sha256': s} for p, s in sorted(self.inputs.items())]}

    def write_json(self, path, schema, body):
        doc = self.header(schema)
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


# ---------------------------------------------------------------- what the writer may see

def writer_view(ctx):
    """Read elig/eligibility.json and keep ONLY the fields the writer tool may use.

    Everything else in that file (labels, kinds, eligibility flags, open forms) is dropped here
    and never reaches any other function of this tool.
    """
    doc = ctx.read_json(ctx.work / 'elig' / 'eligibility.json')
    if doc.get('schema') != 'casalescence/optionb/eligibility/v1':
        raise Stop('WRONG_FILE', 'elig/eligibility.json does not carry the eligibility schema name.')
    if not ctx.dry and doc.get('counts_match_plan') is not True:
        raise Stop('ELIGIBILITY_NOT_CONFIRMED', 'elig/eligibility.json does not say counts_match_plan: true.')
    rows = {}
    for passage in doc['passages']:
        pid, text = passage['id'], passage['text']
        if not ID_RULE.fullmatch(pid) or not isinstance(text, str) or not text.strip() or '===' in text:
            raise Stop('PASSAGE_NOT_USABLE', 'Passage %r has an id or a text that can not be fenced safely.' % pid)
        rows[pid] = {'text': text, 'setting': passage['setting'], 'setting_role': passage['setting_role'],
                     'writer_asks': passage['writer_asks'] is True}
    view = {'rows': rows, 'practice_settings': list(doc['practice_settings']), 'reserve': list(doc['reserve_settings_in_order'])}
    del doc
    return view


def fill_brief(constants):
    words, briefs = constants['forbidden_words'], constants['briefs']
    join, quote = briefs['question_brief_list_join'], briefs['question_brief_phrase_quote']
    text = fill('\n'.join(briefs['question_brief']), {
        'LIST_A': join.join(words['list_a']['words']),
        'LIST_B': join.join(words['list_b']['words']),
        'NEVER_ALLOWED_PHRASES': join.join(quote + w + quote for w in words['never_allowed_phrases']['words']),
        'LIST_C': join.join(words['list_c']['words'])})
    return text


def build_prompt(brief, fence, pairs):
    """The whole prompt: the brief, one empty line, the fenced passages with one empty line between them.

    pairs is a list of (passage id, passage text). This function is given nothing else,
    so a label, a note, a kind tag or an eligibility flag can not reach the prompt.
    """
    blocks = [fill(fence, {'ID': pid, 'PASSAGE': text}) for pid, text in pairs]
    prompt = brief + '\n\n' + '\n\n'.join(blocks)
    if re.search(r'\^[0-9]|\bK[1-9]\b', prompt):
        raise Stop('PROMPT_NOT_BLIND', 'A prompt would hold a Noetic tag or a kind tag. Nothing was sent.')
    return prompt


# ---------------------------------------------------------------- the plan of waves and batches

def planned_waves(view, set_name, practice_count, start, split):
    """A list of (wave number, setting names, sorted passage ids)."""
    rows = view['rows']
    if set_name == 'practice':
        waves = []
        for k in range(practice_count - start + 1):
            role = 'practice' if k == 0 else 'reserve_%d' % k
            ids = sorted(pid for pid, row in rows.items() if row['writer_asks'] and row['setting_role'] == role)
            waves.append((k, list(view['practice_settings']) if k == 0 else [view['reserve'][k - 1]], ids))
        return waves
    settings = list(split['final_settings'])
    ids = sorted(split['final_writer_passage_ids'])
    mine = sorted(pid for pid, row in rows.items() if row['writer_asks'] and row['setting'] in settings)
    if ids != mine:
        raise Stop('SPLIT_DOES_NOT_MATCH', 'select/split_fixed.json lists other final writer passages than elig/eligibility.json gives.')
    return [(0, settings, ids)]


def cut_batches(ids, seed, size):
    order = sorted(ids)
    random.Random(seed).shuffle(order)
    return [order[i:i + size] for i in range(0, len(order), size)]


# ---------------------------------------------------------------- reading a reply

def parse_reply(text):
    """Return the JSON array of a reply, or None when the reply is not a readable JSON array."""
    text = (text or '').strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1] if '\n' in text else ''
        text = text.rsplit('```', 1)[0]
    try:
        value = json.loads(text)
    except ValueError:
        return None
    return value if isinstance(value, list) else None


def _text(value):
    return value.strip() if isinstance(value, str) else ''


def _texts(value):
    return [_text(item) for item in value] if isinstance(value, list) else []


def passage_object(array, pid, wave, batch, pass_name, forms):
    """One raw_questions row. Texts are kept as returned, with outer white space removed."""
    row = {'passage_id': pid, 'wave': wave, 'batch': batch, 'status': 'OK', 'what_follows': [], 'plain_fact': None, 'extra_dropped': []}
    if array is None:
        row['status'] = 'BAD_OBJECT'
        return row
    found = [item for item in array if isinstance(item, dict) and _text(item.get('passage')) == pid]
    if not found:
        row['status'] = 'MISSING'
        return row
    what_follows = found[0].get('what_follows')
    what_follows = [] if what_follows is None else what_follows
    fact = found[0].get('plain_fact')
    if len(found) > 1 or not isinstance(what_follows, list) or not (fact is None or isinstance(fact, dict)):
        row['status'] = 'BAD_OBJECT'
        return row
    seen, unknown = set(), 0
    for item in what_follows:
        item = item if isinstance(item, dict) else {}
        form = _text(item.get('form'))
        question = {'form': form, 'question': _text(item.get('question')), 'right': _text(item.get('right')),
                    'wrong': _texts(item.get('wrong')), 'anchors': _texts(item.get('anchors'))}
        if form in forms:
            if form in seen:
                row['extra_dropped'].append(question)
                continue
            seen.add(form)
            tag = form
        else:
            unknown += 1
            tag = 'UNKNOWN%d' % unknown
        row['what_follows'].append(dict({'question_id': '%s.%s.%s' % (pid, pass_name, tag)}, **question))
    if fact is not None:
        row['plain_fact'] = {'question_id': '%s.%s.FACT' % (pid, pass_name), 'question': _text(fact.get('question')),
                             'right': _text(fact.get('right')), 'wrong': _texts(fact.get('wrong'))}
    return row


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


# ---------------------------------------------------------------- the run

def pass_choices(argv):
    """The pass names of PLAN_CONSTANTS.json (outside_services.gemini_question_writer.passes), read before the options are parsed.

    A dry fixture (--work under optionb/dry/) may override the list in its DRY_CONSTANT_OVERRIDES.json, as Ctx does later.
    The list is used only for the --pass choices; the run checks the pass again against the constants it loads.
    """
    try:
        constants = json.loads((REAL_WORK / 'PLAN_CONSTANTS.json').read_text(encoding='utf-8'))
        argv = list(sys.argv[1:] if argv is None else argv)
        if '--work' in argv and argv.index('--work') + 1 < len(argv):
            over = Path(argv[argv.index('--work') + 1]) / OVERRIDES_NAME
            if over.exists():
                merge(constants, json.loads(over.read_text(encoding='utf-8')))
        passes = constants['outside_services']['gemini_question_writer']['passes']
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return list(passes) if isinstance(passes, list) and all(isinstance(p, str) for p in passes) else None


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):      # FILE_FORMATS.md section 0: a laptop tool prints in UTF-8
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description='Option B Step 1: the blind question writer, in batches.')
    parser.add_argument('--set', dest='set_name', required=True, choices=['practice', 'final'])
    passes = pass_choices(argv)
    parser.add_argument('--pass', dest='pass_name', required=True, choices=passes,
                        help='a pass name of PLAN_CONSTANTS.json: p1 = first pass; p2, p3 = later passes with another seeded batch order')
    parser.add_argument('--max-calls', type=int, required=True, help='call budget for this run; 0 = write the plan only')
    parser.add_argument('--batch-size', type=int, default=None, help='passages per call (default and upper limit: the plan value)')
    parser.add_argument('--practice-settings', type=int, default=None, help='practice set only: 8 to 12 (default 8)')
    parser.add_argument('--pace', type=float, default=7.0, help='seconds to wait before each call')
    parser.add_argument('--timeout', type=float, default=300.0, help='seconds to wait for one reply')
    parser.add_argument('--max-transport-failures', type=int, default=3, help='stop after this many failed connections in a row')
    parser.add_argument('--work', default=None, help='dry fixture folder under optionb/dry/ (never for a real run)')
    parser.add_argument('--replay-replies', default=None, help='dry fixture only: a file of made-up replies')
    args = parser.parse_args(argv)

    ctx = Ctx(args.work)
    C = ctx.constants
    G = C['outside_services']['gemini_question_writer']
    set_name, pass_name = args.set_name, args.pass_name
    if pass_name not in G['passes'] or args.max_calls < 0:
        raise Stop('BAD_ARGUMENT', 'Unknown pass, or a call budget below 0.')
    # Amendment A1: one model writes the practice set, the final set and the spare pass. The name comes from the
    # plan constants only. This tool has no option that names another model.
    names = set(G['model_by_set'].values())
    if sorted(G['model_by_set']) != ['final', 'practice'] or len(names) != 1 or not all(isinstance(n, str) and n.strip() for n in names):
        raise Stop('ONE_MODEL_RULE', 'outside_services.gemini_question_writer.model_by_set in PLAN_CONSTANTS.json must name one and the same '
                   'model for the practice set and the final set. It says: %s' % json.dumps(G['model_by_set'], sort_keys=True))
    model = DRY_MODEL if ctx.dry else G['model_by_set'][set_name]
    seed = C['seeds']['writer_batch_order_' + pass_name]
    size = G['passages_per_call'] if args.batch_size is None else args.batch_size
    if not 1 <= size <= G['passages_per_call']:
        raise Stop('BAD_ARGUMENT', 'The batch size must be 1 to %d.' % G['passages_per_call'])
    start, most = C['split']['practice_setting_count_start'], C['split']['practice_setting_count_max']

    if set_name == 'practice':
        seal = check_seal(ctx, ['1_PLAN_AND_SOURCES', '2_ROLE_NOTES'], '3A_PRACTICE_QUESTIONS_AND_KEYS')
    else:
        seal = check_seal(ctx, ['1_PLAN_AND_SOURCES', '2_ROLE_NOTES', '3A_PRACTICE_QUESTIONS_AND_KEYS', '3B_PRACTICE_SET_FIXED'],
                          '3C_FINAL_QUESTIONS_AND_KEYS')
    check_list_a(ctx)
    view = writer_view(ctx)

    qdir = ctx.work / 'questions'
    state_path = qdir / ('writer_state_%s_%s.json' % (set_name, pass_name))
    log_path = qdir / ('writer_calls_%s_%s.jsonl' % (set_name, pass_name))
    raw_path = qdir / ('raw_questions_%s_%s.json' % (set_name, pass_name))
    # plan v1.1: there may be more than one other pass. Every other pass that has a checkpoint is read.
    other_passes = [p for p in G['passes'] if p != pass_name]
    other_state_paths = [qdir / ('writer_state_%s_%s.json' % (set_name, p)) for p in other_passes]
    split_path = ctx.work / 'select' / 'split_fixed.json'

    split = ctx.read_json(split_path) if split_path.exists() else None
    if set_name == 'final':
        if split is None:
            raise Stop('PRACTICE_SET_NOT_FIXED', 'select/split_fixed.json does not exist. No final question is written before the practice set is fixed.')
        if split.get('floor_met') is not True:
            raise Stop('DO_NOT_LAUNCH', 'select/split_fixed.json says the practice floor was not met. No final question is written.')
        practice_count = split['practice_setting_count']
    else:
        practice_count = start if args.practice_settings is None else args.practice_settings
        if not start <= practice_count <= most:
            raise Stop('BAD_ARGUMENT', '--practice-settings must be %d to %d.' % (start, most))

    state = load_own(state_path) if state_path.exists() else None
    other_states = [load_own(path) for path in other_state_paths if path.exists()]
    if state is None:
        state = {'set': set_name, 'pass': pass_name, 'model': model, 'seed': seed, 'waves': [], 'cap_stops_utc': [], 'complete': False}
    if (state['set'], state['pass'], state['seed']) != (set_name, pass_name, seed):
        raise Stop('CHECKPOINT_DOES_NOT_MATCH', 'The checkpoint was made for another set, pass or seed.')
    for name, doc in [('this pass', state)] + [('pass %s' % doc['pass'], doc) for doc in other_states]:
        if doc is not None and doc['model'] != model:
            raise Stop('ONE_MODEL_PER_SET', 'The checkpoint of %s names model %s. This set is written by one model only (%s).' % (name, doc['model'], model))

    # add the waves that are not in the checkpoint yet; a wave already batched is never batched again
    have = {wave['wave'] for wave in state['waves']}
    for number, settings, ids in planned_waves(view, set_name, practice_count, start, split):
        if number in have:
            continue
        if set_name == 'practice':
            if split is not None:
                raise Stop('PRACTICE_SET_IS_FIXED', 'select/split_fixed.json exists. No practice wave is added after that.')
            if number > 0 and not any(number in {w['wave'] for w in other['waves']} for other in other_states):
                # The reserve rule (amendment A8; FILE_FORMATS.md sections 4 and 7.1). This tool reads the block reserve of
                # select/selection_practice.json, exactly as tools/ob_select.py and tools/ob_seal.py do. It does not read
                # floor.met for this rule. A file with no reserve block also stops it.
                selection_path = ctx.work / 'select' / 'selection_practice.json'
                selection = ctx.read_json(selection_path) if selection_path.exists() else None
                reserve = selection.get('reserve') if isinstance(selection, dict) else None
                if (selection is None or selection.get('practice_setting_count') != start + number - 1
                        or not isinstance(reserve, dict) or reserve.get('finished') is not False):
                    raise Stop('RESERVE_RULE_NOT_MET', 'Reserve setting %d may move to practice only when select/selection_practice.json, made with %d '
                               'practice settings, says "finished": false in its block reserve. That means: a reserve target is missed (%d practice '
                               'role-step tasks and %d practice plain-fact tasks) and a reserve setting is left.'
                               % (number, start + number - 1, C['split']['reserve_target_practice_role_step_tasks'],
                                  C['split']['reserve_target_practice_plain_fact_tasks']))
        batches = [{'batch': i, 'passage_ids': ids_i, 'status': 'PENDING', 'attempts': 0} for i, ids_i in enumerate(cut_batches(ids, seed, size))]
        state['waves'].append({'wave': number, 'settings': settings, 'batches': batches})
    state['waves'].sort(key=lambda wave: wave['wave'])

    brief = fill_brief(C)
    fence = '\n'.join(C['briefs']['question_passage_fence'])
    forms = list(C['forms_in_order'])
    retries = G['unreadable_reply_retries']
    prompts = {}
    for wave in state['waves']:
        for batch in wave['batches']:
            pairs = [(pid, view['rows'][pid]['text']) for pid in batch['passage_ids']]
            prompts[(wave['wave'], batch['batch'])] = build_prompt(brief, fence, pairs)

    # the call log is the record; the checkpoint is rebuilt from it so that a crash can not cause an extra try
    by_batch = {}
    for row in read_jsonl(log_path):
        by_batch.setdefault((row['wave'], row['batch']), []).append(row)
    if set(by_batch) - set(prompts):
        raise Stop('LOG_DOES_NOT_MATCH_PLAN', 'The call log holds a batch that the checkpoint does not know.')
    arrays = {}

    def settle(wave, batch):
        key = (wave['wave'], batch['batch'])
        rows = by_batch.get(key, [])
        for row in rows:
            if row['passage_ids'] != batch['passage_ids'] or row['prompt_sha256'] != sha_text(prompts[key]):
                raise Stop('LOG_DOES_NOT_MATCH_PLAN', 'A logged call for wave %d batch %d used other passages or another prompt.' % key)
        counted = [row for row in rows if row['http_status'] == 200]
        if len(counted) > 1 + retries:
            raise Stop('TOO_MANY_TRIES_IN_LOG', 'Wave %d batch %d was asked more often than the plan allows.' % key)
        batch['attempts'], batch['status'] = len(counted), 'PENDING'
        for row in counted:
            array = parse_reply(row['reply'])
            if array is not None:
                arrays[key], batch['status'] = array, 'DONE'
                return
        if len(counted) >= 1 + retries:
            arrays[key], batch['status'] = None, 'UNREADABLE'

    def save():
        state['complete'] = all(b['status'] != 'PENDING' for w in state['waves'] for b in w['batches'])
        passages = []
        for wave in state['waves']:
            for batch in wave['batches']:
                key = (wave['wave'], batch['batch'])
                if batch['status'] != 'PENDING':
                    passages.extend(passage_object(arrays[key], pid, key[0], key[1], pass_name, forms) for pid in batch['passage_ids'])
        if log_path.exists():
            ctx.inputs[rel(log_path)] = sha_bytes(log_path.read_bytes())
        ctx.write_json(raw_path, 'casalescence/optionb/raw_questions/v1', {'set': set_name, 'pass': pass_name, 'model': model, 'passages': passages})
        ctx.write_json(state_path, 'casalescence/optionb/writer_state/v1', state)
        return passages

    for wave in state['waves']:
        for batch in wave['batches']:
            settle(wave, batch)
    save()

    if ctx.dry:
        if args.max_calls > 0 and not args.replay_replies:
            raise Stop('DRY_FIXTURE_NEEDS_REPLAY', 'No outside call is ever made from a dry folder. Give --replay-replies.')
        send, key, pace = (replay_sender(args.replay_replies) if args.replay_replies else None), '', 0.0
    else:
        if args.replay_replies:
            raise Stop('REPLAY_ONLY_IN_DRY_FOLDER', '--replay-replies is refused outside optionb/dry/.')
        key, pace = os.environ.get(G['key_environment_variable'], '').strip(), max(0.0, args.pace)
        if args.max_calls > 0 and not key:
            raise Stop('KEY_NOT_SET', 'The environment variable %s is not set.' % G['key_environment_variable'])

        def send(prompt):
            body = {'model': model, 'temperature': G['temperature'], 'max_tokens': G['max_tokens'], 'messages': [{'role': 'user', 'content': prompt}]}
            for extra in ('reasoning_effort',):  # sent only if the plan constants name it
                if extra in G:
                    body[extra] = G[extra]
            return http_send(G['endpoint'], key, body, args.timeout)

    calls, failures, status = 0, 0, None
    todo = [(w, b) for w in state['waves'] for b in w['batches'] if b['status'] == 'PENDING']
    for wave, batch in todo:
        key_id = (wave['wave'], batch['batch'])
        while batch['status'] == 'PENDING' and status is None:
            if calls >= args.max_calls:
                status = 'STOPPED_CALL_BUDGET'
                break
            time.sleep(pace)
            prompt = prompts[key_id]
            result = send(prompt)
            if result is None:
                status = 'STOPPED_REPLAY_EXHAUSTED'
                break
            calls += 1
            array = parse_reply(result['content']) if result['http_status'] == 200 else None
            error = result['error'] or (None if array is not None else 'REPLY_NOT_A_READABLE_JSON_ARRAY')
            row = {'utc': utc_now(), 'set': set_name, 'pass': pass_name, 'model': model, 'model_in_reply': result['model_in_reply'],
                   'wave': key_id[0], 'batch': key_id[1],
                   'attempt': batch['attempts'] + 1, 'http_status': result['http_status'], 'passage_ids': batch['passage_ids'],
                   'prompt_sha256': sha_text(prompt), 'reply_sha256': sha_text(result['content']), 'ok': array is not None,
                   'error': scrub(error, key) if error else None, 'usage': result['usage'], 'prompt': prompt, 'reply': result['content']}
            append_jsonl(log_path, row)
            by_batch.setdefault(key_id, []).append(row)
            if result['http_status'] == 200:
                failures = 0
                settle(wave, batch)
            elif result['http_status'] == 429:
                # Amendment A1: a refused call is not counted as a try. The tool stops cleanly at once, keeps the
                # checkpoint, and resumes when it is run again later. It does not wait and try again by itself.
                state['cap_stops_utc'].append(row['utc'])
                status = 'STOPPED_HTTP_429'
            else:
                failures += 1
                if failures >= args.max_transport_failures:
                    status = 'STOPPED_NO_ANSWER_FROM_SERVICE'
            save()
        if status is not None:
            break
    passages = save()
    if status is None:
        status = 'ALL_WRITTEN' if state['complete'] else 'STOPPED_CALL_BUDGET'

    batches = [b for w in state['waves'] for b in w['batches']]
    print(json.dumps({
        'program': PROGRAM, 'dry_fixture': ctx.dry, 'status': status, 'set': set_name, 'pass': pass_name, 'model': model,
        'seal': seal, 'practice_setting_count': practice_count, 'waves': len(state['waves']),
        'batches': {name: sum(1 for b in batches if b['status'] == name) for name in ('DONE', 'PENDING', 'UNREADABLE')},
        'calls_this_run': calls, 'call_budget': args.max_calls, 'stops_after_http_429': len(state['cap_stops_utc']),
        'model_names_in_the_replies': sorted({str(row.get('model_in_reply')) for rows in by_batch.values() for row in rows
                                              if row['http_status'] == 200}),
        'passages_asked': len(passages),
        'passages_by_status': {name: sum(1 for p in passages if p['status'] == name) for name in ('OK', 'MISSING', 'BAD_OBJECT')},
        'what_follows_questions': sum(len(p['what_follows']) for p in passages),
        'plain_fact_questions': sum(1 for p in passages if p['plain_fact']),
        'next': {'ALL_WRITTEN': 'This pass of this set is written.',
                 'STOPPED_HTTP_429': 'The service refused a call (HTTP 429). The refused call is not counted as a try. The checkpoint is kept. '
                                     'Run the same command again later. The daily cap of this model is not known.',
                 'STOPPED_CALL_BUDGET': 'The call budget of this run is used up. The checkpoint is kept. Run the same command again.',
                 'STOPPED_NO_ANSWER_FROM_SERVICE': 'The service gave no answer several times in a row. The checkpoint is kept. Run the same command later.',
                 'STOPPED_REPLAY_EXHAUSTED': 'The made-up reply file has no more replies.'}[status]}, ensure_ascii=False, indent=1))
    # FILE_FORMATS.md section 0: only code 0 lets the next step start. Every STOPPED_ status leaves batches open: code 1.
    return 0 if status == 'ALL_WRITTEN' else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Stop as stop:
        print(json.dumps({'program': PROGRAM, 'status': 'STOP', 'code': stop.args[0], 'reason': stop.args[1]}, ensure_ascii=False, indent=1))
        sys.exit(2)
