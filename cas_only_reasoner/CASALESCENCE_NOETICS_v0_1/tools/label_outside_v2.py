"""Label passages for team B with an outside (non-Claude) model service, under labeling guide v2.0.

One passage per call. Temperature 0. Threads, checkpoint, resume. Plain Python, standard library only.
Modelled on tools/label_outside.py. What is new: the record goes through the format checker
(tools/check_labels_v2.py), and the checker's messages go back to the model for another try, up to
three tries per passage. Team A runs the same loop by hand; its fixed recipe is printed by
`check_labels_v2.py --recipe`. Both teams use the same function (check_labels_v2.take_try), the same
messages and the same three tries.

WHAT THE MODEL IS SENT
  system: one fixed line, then the labeling guide, then the labeler instructions.
  user:   one passage (its id and its text) and one fixed request for ONE JSON object.
  On another try: the model's own earlier reply, then the checker's lines for that reply.
Nothing else. The tool takes only "id" and "text" from the passage file, and it refuses a passage file
that carries any other field, so it never sees the writer's kinds. It has no input for the other team's
labels or for the writer's brief.

THE KEY
  Read from the environment of this process at run time: DEEPSEEK_API_KEY or GEMINI_API_KEY.
  The tool opens no key file. It never prints the key and never stores it. Error texts are scrubbed.
  Only the NAME of the variable is written to the receipt.

THE THREE TRIES (spec design_v2/labeling_final.json, entry_format, sections THE CHECKER and DROPS)
  A try is one answer of the model. A network error is not a try: the call is repeated, and if it keeps
  failing the passage stays open and a later run resumes it at the same try.
  - Accepted on a try: the record is final.
  - After the third try the third record is final. Each entry that still fails C1 to C8 is DROPPED: it
    stays in the record, is listed under "checker" -> "dropped", and the scorer keeps it in its row.
  - An entry that failed a check and that the model then left out is put back by the checker and counted
    as dropped ("removed_after_reask"). See the top of check_labels_v2.py.
  - If the third try gives no usable record (no JSON object, wrong passage_id, bad shape), the passage is
    recorded as NOT LABELED by this team: "labeler_failed": true. The scorer counts those.
  A finished passage is never asked again on resume, so no passage gets more than three tries.

THE TOKEN CAP (--token-cap N; a real run is refused without it)
  The cap is on ALL runs that write this labels file together, not on one run. Counted against it:
  - the tokens of every stored try of every run (prompt plus completion as the service reports them, or
    the service's own total when that is larger);
  - an upper estimate for every call that failed in a way that may still have been billed (a time-out, a
    broken connection, an answer that could not be read). Not counted: an HTTP error answer, a name that
    was not found, a refused connection;
  - an upper estimate for every call that is under way, and for the call about to start.
  The upper estimate for one call is one token for every 3 characters sent, plus MAX_TOKENS for the reply.
  A call is started only if the sum stays at or under the cap. So the reported total never passes the cap.
  When the cap stops a run, open passages stay open and the tool ends with exit code 1. Starting it again
  with the same cap makes no call. A higher cap on a later run is allowed; every cap that was ever given
  is kept in the try log and in the receipt, so a raise cannot be hidden.
  The cap is in tokens. What a token costs is the price sheet's business, not this tool's.

THE SEAL RECORD (--seal SEAL.json, or PRACTICE_SET.json for a practice pass)
  With --seal the tool refuses to start unless the guide, the instructions, the checker, the passage file
  and this tool itself have the sha256 that the record holds. The record's own sha256 goes into the try log
  and the receipt, so one labels file cannot be made under two seals.

FILES WRITTEN
  <output.json>               the labels file: one row per passage, in passage order, with a "checker" block
  <output.json>.tries.json    every try of every passage: the raw reply, the checker's messages, what was
                              sent back, token counts. This is also the checkpoint for resume.
  <output.json>.journal.jsonl only while a run is going: one line per try, written at once, so that a
                              killed run loses no try. The next run reads it and removes it.
  <output.json>.receipt.json  the keys every labels receipt has (see THE RECEIPT in check_labels_v2.py):
                              the sha256 of the labels file, the passage file, the checker, the guide and
                              the instructions, "complete", and the seal record that was compared. Plus:
                              provider, model, this tool's sha256, the fixed frame's sha256, counts, token
                              totals and every token cap that was given.

USAGE
  label_outside_v2.py <provider> <model> <guide.md> <instructions.txt> <passages.json> <output.json>
                      [seconds_between_calls] [workers] --token-cap N [--seal SEAL.json] [--dry-run]
                      [--expect-checker-sha256 HEX]
  provider: deepseek or gemini.
  --token-cap N   the most tokens all runs for this labels file may use together. Needed for a real run.
  --seal FILE     refuse unless guide, instructions, checker, passages and this tool match the record.
  --dry-run       make no call. Print what would be sent for the first passage (sizes and hashes only),
                  and the upper token estimate for one call.
  --expect-checker-sha256 HEX   refuse to run unless tools/check_labels_v2.py has this hash (the frozen one).
Exit codes: 0 every passage is final; 1 some passages are still open (run again to resume); 2 the
command was wrong or a file is missing.

STATUS. Candidate tool for a design PROPOSAL. It labels nothing until it is run, and running it calls a
paid outside service: that needs the owner's existing approval record and a stated cap.
"""
import argparse
import copy
import hashlib
import json
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_labels_v2 as chk  # noqa: E402  (the same checker file both teams use)

TOOL = 'label_outside_v2/1'
ENDPOINTS = {'deepseek': ('https://api.deepseek.com/chat/completions', 'DEEPSEEK_API_KEY'),
             'gemini': ('https://generativelanguage.googleapis.com/v1beta/openai/chat/completions', 'GEMINI_API_KEY')}
HEAD = ('You are a careful labeler. Work only from the labeling guide and the labeler instructions below. '
        'Never force a label. Reply with ONE JSON object and nothing else.\n\n')
ASK = ('Passage %(id)s:\n%(text)s\n\n'
       'Label this passage as the guide and the instructions say. Reply with ONE JSON object for passage_id "%(id)s" '
       'and nothing else.\n'
       'A format checker reads your reply. It reads form only. If it finds a problem you get its messages and may send '
       'the record again. You have three tries in all.')
AGAIN = 'Then send the whole record again as ONE JSON object and nothing else.'
MAX_TOKENS = 8000
CHARACTERS_PER_TOKEN_FLOOR = 3     # for the upper estimate of one call: at least this many characters make one token
CALL_TIMEOUT = 180
TRANSPORT_ATTEMPTS = 4
WAIT_AFTER_RATE_LIMIT = 45
WAIT_AFTER_ERROR = 5
SAVE_EVERY = 10
STOP_CODES = (401, 402, 403)       # a wrong key or no credit: stop the whole run
NO_RETRY_CODES = (400, 404, 422)   # the same call would fail again


class Refused(Exception):
    """The run cannot start. The command line turns it into exit code 2."""


def sha256_of(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scrub(text, key):
    text = str(text)
    return text.replace(key, '[KEY]') if key else text


def call_tokens(usage):
    """The tokens one answered call used, as the service reports them: prompt plus completion, or the service's own
    total when that is larger (some services count thinking tokens only in the total)."""
    def number(name):
        value = (usage or {}).get(name)
        return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0
    return max(number('prompt_tokens') + number('completion_tokens'), number('total_tokens'))


def most_tokens(messages):
    """An upper estimate of what one call can use, made before the call: one token for every 3 characters sent, plus
    the most the reply may hold. English text has about 4 characters to a token, so this is on the high side."""
    return sum(len(m['content']) for m in messages) // CHARACTERS_PER_TOKEN_FLOOR + 1 + MAX_TOKENS


def never_reached_the_service(error):
    """True for a failure that cannot have been billed: the name was not found, or the connection was refused."""
    reason = getattr(error, 'reason', None)
    return isinstance(error, urllib.error.URLError) and isinstance(reason, (socket.gaierror, ConnectionRefusedError))


def load_passages_strict(path):
    """The passages as a list of (id, text). Refuses a file that holds anything but id and text."""
    name = Path(path).name.upper()
    if 'HIDDEN' in name or 'KIND' in name or 'BRIEF' in name:
        raise Refused('%s looks like a file that label teams must not see. Give the sealed passage file that holds '
                      'only id and text.' % Path(path).name)
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data, list) or not all(isinstance(p, dict) for p in data):
        raise Refused('The passage file must be a JSON list of {"id": ..., "text": ...}.')
    extra = sorted({k for p in data for k in p} - {'id', 'text'})
    if extra:
        raise Refused('The passage file has other fields than id and text (%s). This tool must never see the writer\'s '
                      'kinds or brief. Give the sealed passage file that holds only id and text.' % ', '.join(extra))
    if not all(isinstance(p.get('id'), str) and isinstance(p.get('text'), str) for p in data):
        raise Refused('Every passage needs a text "id" and a text "text".')
    ids = [p['id'] for p in data]
    if len(set(ids)) != len(ids):
        raise Refused('The passage file repeats a passage id.')
    return [(p['id'], p['text']) for p in data]


def http_call(url, key, model, messages):
    """One call to the service. Returns (reply text, usage, finish reason). The key goes only into the request."""
    body = json.dumps({'model': model, 'temperature': 0, 'max_tokens': MAX_TOKENS, 'messages': messages}).encode('utf-8')
    request = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json',
                                                              'Authorization': 'Bearer ' + key})
    with urllib.request.urlopen(request, timeout=CALL_TIMEOUT) as response:
        data = json.loads(response.read())
    choice = data['choices'][0]
    return choice['message'].get('content') or '', data.get('usage') or {}, choice.get('finish_reason')


def parse_reply(text):
    """The JSON object in a reply, or (None, why). Code fences and words around the object are tolerated."""
    text = (text or '').strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1] if '\n' in text else ''
        text = text.rsplit('```', 1)[0].strip()
    try:
        value = json.loads(text)
    except ValueError:
        first, last = text.find('{'), text.rfind('}')
        try:
            value = json.loads(text[first:last + 1]) if 0 <= first < last else None
        except ValueError:
            value = None
    if not isinstance(value, dict):
        return None, ('The reply is not one complete JSON object. Send ONE JSON object and nothing else: no words before '
                      'it, none after it. If the reply was cut off, write shorter notes.')
    return value, None


def build_messages(system, passage_id, text, state):
    """The conversation for the next try: the request, then each earlier reply with the checker's lines for it."""
    messages = [{'role': 'system', 'content': system},
                {'role': 'user', 'content': ASK % {'id': passage_id, 'text': text}}]
    for attempt in state['tries']:
        messages.append({'role': 'assistant', 'content': attempt.get('reply') or '(empty reply)'})
        messages.append({'role': 'user', 'content': attempt.get('sent_back') or AGAIN})
    return messages


def stored_tokens(log):
    """The tokens of every stored try of every run, as the service reported them."""
    return sum(call_tokens(attempt.get('usage')) for state in log['passages'].values() for attempt in state['tries'])


def run(args, caller=None):
    caller = caller or http_call
    if args.provider not in ENDPOINTS:
        raise Refused('provider must be one of: %s' % ', '.join(sorted(ENDPOINTS)))
    url, key_name = ENDPOINTS[args.provider]
    for path in (args.guide, args.instructions, args.passages):
        if not Path(path).is_file():
            raise Refused('cannot find %s' % path)
    checker_hash = chk.checker_sha256()
    if args.expect_checker_sha256 and args.expect_checker_sha256.lower() != checker_hash:
        raise Refused('check_labels_v2.py has sha256 %s, not the expected %s.' % (checker_hash, args.expect_checker_sha256))
    seal_info = None
    if args.seal:
        try:
            problems, seal_info = chk.check_against_seal(args.seal, {
                'guide': args.guide, 'instructions': args.instructions, 'checker': chk.__file__,
                'passages': args.passages, 'team_b_tool': __file__})
        except chk.UsageError as error:
            raise Refused(str(error))
        if problems:
            raise Refused('the files do not match the seal record %s: %s.' % (Path(args.seal).name, '; '.join(problems)))
    passages = load_passages_strict(args.passages)
    guide = Path(args.guide).read_text(encoding='utf-8')
    instructions = Path(args.instructions).read_text(encoding='utf-8')
    system = (HEAD + '=== LABELING GUIDE ===\n' + guide.strip() + '\n\n=== LABELER INSTRUCTIONS ===\n'
              + instructions.strip() + '\n')
    frame_hash = hashlib.sha256((HEAD + ASK + AGAIN).encode('utf-8')).hexdigest()
    header = {'tool': TOOL, 'provider': args.provider, 'model': args.model, 'temperature': 0, 'max_tokens': MAX_TOKENS,
              'guide_sha256': sha256_of(args.guide), 'instructions_sha256': sha256_of(args.instructions),
              'passages_sha256': sha256_of(args.passages), 'frame_sha256': frame_hash,
              'checker_sha256': checker_hash, 'tool_sha256': sha256_of(__file__),
              'seal_sha256': seal_info['sha256'] if seal_info else None}
    key = os.environ.get(key_name, '').strip()

    if args.dry_run:
        first_id, first_text = passages[0]
        request = build_messages(system, first_id, first_text, chk.new_state())
        print(json.dumps({'dry_run': True, 'calls_made': 0, 'provider': args.provider, 'model': args.model,
                          'endpoint': url, 'key_variable': key_name, 'key_is_set': bool(key),
                          'passages': len(passages), 'most_calls_possible': chk.MAX_TRIES * len(passages),
                          'system_characters': len(system), 'system_sha256': hashlib.sha256(system.encode('utf-8')).hexdigest(),
                          'first_request_characters': sum(len(m['content']) for m in request),
                          'upper_token_estimate_for_the_first_call': most_tokens(request),
                          'upper_token_estimate_if_every_passage_takes_one_try': most_tokens(request) * len(passages),
                          'note_on_the_estimates': 'ESTIMATE, not a count: one token for every %d characters sent plus %d '
                                                   'for the reply. A second or third try sends more.'
                                                   % (CHARACTERS_PER_TOKEN_FLOOR, MAX_TOKENS),
                          'token_cap_given': args.token_cap, 'seal_record': seal_info,
                          'checker': chk.CHECKER, **header}, indent=1))
        return 0
    if args.token_cap <= 0:
        raise Refused('No token cap was given. A real run needs --token-cap N: the most tokens that all runs for this '
                      'labels file may use together. Take the number from the plan.')
    if not key:
        raise Refused('The environment variable %s is not set. Set it in the shell that starts this tool. '
                      'This tool reads no key file.' % key_name)

    out = Path(args.output)
    if not out.parent.is_dir():
        raise Refused('the folder for the output does not exist: %s' % out.parent)
    tries_path = out.with_name(out.name + '.tries.json')
    journal_path = out.with_name(out.name + '.journal.jsonl')
    if journal_path.exists() and not tries_path.exists():
        raise Refused('%s is there without its try log. Move it away first.' % journal_path.name)
    try:
        log = chk.load_log(tries_path)
    except chk.UsageError as error:
        raise Refused(str(error))
    if log.get('run'):
        changed = [k for k, v in header.items() if log['run'].get(k) != v]
        if changed:
            raise Refused('%s was started with another %s. One labels file is made with one guide, one model, one '
                          'passage file, one checker, one tool and one seal record. Use a new output name.'
                          % (tries_path.name, ', '.join(changed)))
    else:
        log['run'] = dict(header, started_utc=chk.now_utc(), tokens={}, calls=0)
    log['run'].setdefault('token_caps_given', []).append({'utc': chk.now_utc(), 'token_cap': args.token_cap})
    log['run'].setdefault('tokens_possibly_used_by_failed_calls', 0)
    known = {p for p, _ in passages}
    replayed = 0
    if journal_path.exists():
        # a run that was killed: every try it had taken is in the journal, one line per try
        for line in journal_path.read_text(encoding='utf-8').splitlines():
            try:
                item = json.loads(line)
            except ValueError:
                continue  # a last line that was cut off while it was written
            if len(item['state']['tries']) >= len((log['passages'].get(item['passage_id']) or {'tries': []})['tries']):
                log['passages'][item['passage_id']] = item['state']
                replayed += 1
    if set(log['passages']) - known:
        raise Refused('%s holds passages that are not in the passage file.' % tries_path.name)

    lock, stop = threading.Lock(), threading.Event()
    run_tokens, counters = {}, {'calls': 0, 'finished': 0, 'transport_errors': 0, 'stopped_for': None}
    # The cap is on all runs together: every stored try counts, whichever run took it.
    spent = {'before_this_run': stored_tokens(log), 'this_run': 0, 'under_way': 0}

    def save():
        chk.write_json(tries_path, log)
        chk.write_json(out, chk.export_rows(passages, [log]))

    save()  # the try log with its run header is on disk before the first call
    if journal_path.exists():
        journal_path.unlink()
    journal = open(journal_path, 'a', encoding='utf-8', newline=chr(10))

    def commit(passage_id, state):
        """Put the state of a passage in the log and on disk at once, so that a killed run loses no try."""
        with lock:
            log['passages'][passage_id] = copy.deepcopy(state)
            journal.write(json.dumps({'passage_id': passage_id, 'state': state}, ensure_ascii=False) + chr(10))
            journal.flush()

    def transport(messages):
        """One answer of the model, or (None, kind, note). A network error is not a try: the call is repeated.
        A call is started only if the token cap holds even when this call uses its upper estimate."""
        note = None
        need = most_tokens(messages)
        for attempt in range(1, TRANSPORT_ATTEMPTS + 1):
            with lock:
                used = spent['before_this_run'] + spent['this_run'] + log['run']['tokens_possibly_used_by_failed_calls']
                if not stop.is_set() and used + spent['under_way'] + need > args.token_cap:
                    counters['stopped_for'] = ('the token cap of %d would be passed: %d counted in all runs, %d held for '
                                               'calls under way, up to %d for the next call'
                                               % (args.token_cap, used, spent['under_way'], need))
                    stop.set()
                if stop.is_set():
                    return None, 'stopped', note
                spent['under_way'] += need
            released = False
            time.sleep(args.pace)
            wait = WAIT_AFTER_ERROR
            try:
                reply, usage, finish = caller(url, key, args.model, messages)
                with lock:
                    spent['under_way'] -= need
                    released = True
                    spent['this_run'] += call_tokens(usage)
                    counters['calls'] += 1
                    for name, value in usage.items():
                        if isinstance(value, int) and not isinstance(value, bool):
                            run_tokens[name] = run_tokens.get(name, 0) + value
                return (reply, usage, finish), 'ok', None
            except urllib.error.HTTPError as error:
                note = scrub('HTTP %d %s' % (error.code, str(error.reason)[:120]), key)
                if error.code in STOP_CODES:
                    with lock:
                        counters['stopped_for'] = 'the service refused the key or the account (%s)' % note
                    stop.set()
                    return None, 'error', note
                if error.code in NO_RETRY_CODES:
                    return None, 'error', note
                wait = WAIT_AFTER_RATE_LIMIT if error.code == 429 else WAIT_AFTER_ERROR
            except Exception as error:  # a network fault, a time-out, an answer that is not the expected JSON
                note = scrub('%s: %s' % (type(error).__name__, str(error)[:160]), key)
                if not never_reached_the_service(error):
                    with lock:          # the service may have billed this call: count its upper estimate
                        log['run']['tokens_possibly_used_by_failed_calls'] += need
            finally:
                if not released:
                    with lock:
                        spent['under_way'] -= need
            if attempt < TRANSPORT_ATTEMPTS:
                time.sleep(wait)
        return None, 'error', note

    def work(passage):
        passage_id, text = passage
        with lock:
            state = copy.deepcopy(log['passages'].get(passage_id) or chk.new_state())
        while not state.get('final') and not stop.is_set():
            answer, kind, note = transport(build_messages(system, passage_id, text, state))
            if answer is None:
                if kind == 'error':
                    state.setdefault('transport_errors', []).append(
                        {'utc': chk.now_utc(), 'before_try': len(state['tries']) + 1, 'error': note})
                    with lock:
                        counters['transport_errors'] += 1
                    commit(passage_id, state)
                break
            reply, usage, finish = answer
            record, problem = parse_reply(reply)
            outcome = chk.take_try(state, passage_id, text, record, problem,
                                   extra={'reply': reply, 'usage': usage, 'finish_reason': finish, 'utc': chk.now_utc()})
            if outcome['status'] == 'TRY_AGAIN':
                state['tries'][-1]['sent_back'] = '\n'.join(chk.describe(passage_id, outcome, again=AGAIN))
            commit(passage_id, state)
        with lock:
            counters['finished'] += 1
            if counters['finished'] % SAVE_EVERY == 0:
                save()

    todo = [p for p in passages if not (log['passages'].get(p[0]) or {}).get('final')]
    kept = len(passages) - len(todo)
    try:
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            list(pool.map(work, todo))
    finally:
        journal.close()

    # totals over every run are read from the stored tries, so a killed run cannot lose them
    totals, answered = {}, 0
    for state in log['passages'].values():
        for attempt in state['tries']:
            answered += 1
            for name, value in (attempt.get('usage') or {}).items():
                if isinstance(value, int) and not isinstance(value, bool):
                    totals[name] = totals.get(name, 0) + value
    counted = stored_tokens(log) + log['run']['tokens_possibly_used_by_failed_calls']
    log['run'].update(tokens=totals, calls=answered, last_run_utc=chk.now_utc(), tokens_counted_against_the_cap=counted)
    save()
    journal_path.unlink()  # every line of it is now in the try log
    rows = chk.export_rows(passages, [log])
    receipt = chk.receipt_core('label_outside_v2.py', out, args.passages, rows, args.guide, args.instructions, seal_info)
    summary, open_ids = receipt['summary'], receipt['open_passages']
    receipt.update(header)
    receipt.update(key_read_from_environment_variable=key_name, one_passage_per_call=True,
                   guide=str(args.guide), instructions=str(args.instructions), passages_file_given=str(args.passages),
                   tries_file=tries_path.name, tries_sha256=sha256_of(tries_path),
                   started_utc=log['run'].get('started_utc'), finished_utc=chk.now_utc(),
                   pace_seconds=args.pace, workers=args.workers,
                   token_cap=args.token_cap, token_cap_is_on_all_runs_together=True,
                   token_caps_given_in_all_runs=log['run']['token_caps_given'],
                   tokens_counted_against_the_cap=counted,
                   tokens_possibly_used_by_failed_calls=log['run']['tokens_possibly_used_by_failed_calls'],
                   passages_kept_from_earlier_run=kept, journal_lines_recovered=replayed,
                   calls_this_run=counters['calls'], calls_all_runs=answered,
                   tokens_this_run=run_tokens, tokens_all_runs=totals, transport_errors_this_run=counters['transport_errors'],
                   stopped_for=counters['stopped_for'], tries=chk.count_tries([log]))
    chk.write_json(out.with_name(out.name + '.receipt.json'), receipt)
    print(json.dumps({k: receipt[k] for k in ('provider', 'model', 'complete', 'calls_this_run', 'tokens_this_run',
                                              'token_cap', 'tokens_counted_against_the_cap',
                                              'transport_errors_this_run', 'stopped_for')}))
    print(json.dumps({'passages': summary['passages'], 'by_final': summary['by_final'], 'entries': summary['entries'],
                      'dropped': summary['dropped'], 'removed_after_reask': summary['removed_after_reask'],
                      'dropped_share': round(summary['dropped_share'], 4),
                      'not_labeled_share': round(summary['not_labeled_share'], 4)}))
    if open_ids:
        print('%d passage%s still open. Run the same command again to resume.' % (len(open_ids), '' if len(open_ids) == 1 else 's'))
    return 1 if open_ids else 0


def main(argv=None, caller=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8')
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(description='Label passages for team B with an outside model, guide v2.0, with the '
                                                 'format checker and up to three tries per passage.')
    parser.add_argument('provider', help='deepseek or gemini')
    parser.add_argument('model', help='the model name, for example deepseek-chat')
    parser.add_argument('guide', help='the labeling guide v2.0 (markdown)')
    parser.add_argument('instructions', help='label_v2/LABELER_INSTRUCTIONS.txt')
    parser.add_argument('passages', help='the passage file: a JSON list of {"id", "text"} and nothing else')
    parser.add_argument('output', help='the labels file to write')
    parser.add_argument('pace', nargs='?', type=float, default=0.0, help='seconds to wait before each call')
    parser.add_argument('workers', nargs='?', type=int, default=1, help='how many passages to work on at once')
    parser.add_argument('--token-cap', type=int, default=0,
                        help='the most tokens all runs for this labels file may use together; needed for a real run')
    parser.add_argument('--seal', default='', help='SEAL.json or PRACTICE_SET.json; refuse unless the files match it')
    parser.add_argument('--dry-run', action='store_true', help='make no call; print sizes, hashes and estimates only')
    parser.add_argument('--expect-checker-sha256', default='', help='the sha256 of the frozen checker')
    args = parser.parse_args(argv)
    try:
        return run(args, caller)
    except Refused as error:
        print('not started: %s' % error)
        return 2


if __name__ == '__main__':
    sys.exit(main())
