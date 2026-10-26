"""Label passages for team B with the DeepSeek service, under labeling guide v2.1.

Plan: 09_LABEL_AGREEMENT_PLAN_v2_1.md. Modelled on tools/label_outside.py (attempt 1). One passage per call,
temperature 0, threads, checkpoint, resume. Plain Python, standard library only.

SENT TO THE MODEL. System: one fixed line, the labeling guide v2.1, the labeler instructions. User: one passage
(id and text) and one fixed request for ONE JSON object. On another try: the model's own earlier reply, then the
checker's messages for it. Nothing else. A passage file with any field but "id" and "text" is refused, so the
tool never sees the writer's kinds. It has no input for the other team's labels.

THREE TRIES. A try is one answer of the model. Its record goes to check_record of tools/check_labels_v21.py,
the checker team A uses too. Where a passage stands is said in the checker's words:
  LABELED      the last try has no message. That record is the final row.
  NOT_LABELED  three tries were made and the third still has a message. The final row is the "could not be
               labeled" row ("labeler_failed": true, no entries).
  OPEN         not final yet. An open passage has no row in the labels file.
A reply that is not a JSON object is a try too; its text is stored as the try. A network error is not a try:
the call is repeated; if it keeps failing the run stops and the passage stays open. The receipt then says
"complete": false. Run the same command again to resume. A final passage is never asked again.

WITHDRAWN ENTRIES. For every labeled passage: per Noetic, how many more entries (different by label, mind or
relative_to) an earlier try held than the final record holds. The checker's own count is used. The receipt
lists the counts per passage and per Noetic. The try log keeps every try, so the entries can be read there.

TOKEN CAP, over ALL runs that write this labels file: --cap-in N (most tokens sent), --cap-out N (most tokens
returned). Both are given on the first run and live in the checkpoint file with the tokens of every try; a
later run reads them there. If a later run gives another number, that number is used, and every cap ever given
stays in the checkpoint and the receipt. A call starts only if both counts stay under their cap at the call's
upper estimate (one token per 3 characters sent; MAX_TOKENS back). A failed call that may have been billed is
counted at that estimate.

FILES. <output>: one final row per finished passage, in passage order, as the checker's own "take" command
writes them. <output>.tries.jsonl: the checkpoint and try log, one line per event, written at once; a try line
holds "event": "try", "passage_id", "n", "record", "messages" as the checker's try log does, plus the raw
reply, the model name in the reply, "reply_has_reasoning" (did the reply hold reasoning text) and the tokens.
<output>.receipt.json: sha256 of guide, instructions, checker, passages and labels; the model name asked for
and every model name the service put in a reply; "tries_with_reasoning_text"; counts; tokens; caps.
KEY. DEEPSEEK_API_KEY from the environment, else from ~/.cas_llm_keys.env, read at run time. Never printed,
never stored. Error text is scrubbed.
USAGE. label_outside_v21.py <model> <guide.md> <instructions.txt> <passages.json> <output.json>
           [--cap-in N --cap-out N] [--pace S] [--workers N] [--checker PATH] [--seal FILE] [--dry-run]
  --seal FILE: SEAL.json or PRACTICE_SET.json; refuse unless guide, instructions, checker, passages and this
  tool have the sha256 the record holds. --dry-run: no call, no key; print sizes, hashes and upper estimates.
  Exit codes: 0 every passage final, 1 some not final, 2 not started.
"""
import argparse
import datetime
import hashlib
import importlib.util
import inspect
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

TOOL = 'label_outside_v21/1'
URL, KEY_NAME = 'https://api.deepseek.com/chat/completions', 'DEEPSEEK_API_KEY'
HEAD = ('You are a careful labeler. Work only from the labeling guide and the labeler instructions below. '
        'Never force a label. Reply with ONE JSON object and nothing else.\n\n')
ASK = ('Passage %(id)s:\n%(text)s\n\n'
       'Label this passage as the guide and the instructions say. Reply with ONE JSON object for passage_id "%(id)s" '
       'and nothing else. A format checker reads your reply. It reads form only. If it finds a problem you get its '
       'messages and may send the record again. You have three tries in all.')
AGAIN = 'Fix what these messages name. Then send the whole record again as ONE JSON object and nothing else.'
MAX_TRIES, MAX_TOKENS, TIMEOUT, TRANSPORT_ATTEMPTS = 3, 4000, 180, 4
STOP_CODES = (400, 401, 402, 403, 404, 422)   # a wrong key, no credit or a rejected model name: stop the whole run
SEALED = (('guide', 'guide_sha256'), ('instructions', 'instructions_sha256'), ('checker', 'checker_sha256'),
          ('passages', 'passages_sha256'), ('team_b_tool', 'tool_sha256'))   # node in the seal record, key in the receipt
LOCK = threading.Lock()


def refuse(message):
    """The run cannot start: say why and end with exit code 2."""
    print('not started: ' + message)
    sys.exit(2)


def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write_json(path, value):
    """Write to a .partial file, then rename. LF line ends."""
    partial = Path(path).with_name(Path(path).name + '.partial')
    partial.write_text(json.dumps(value, indent=1, ensure_ascii=False) + chr(10), encoding='utf-8', newline=chr(10))
    os.replace(partial, path)


def read_key():
    key, path = os.environ.get(KEY_NAME, '').strip(), Path.home() / '.cas_llm_keys.env'
    if not key and path.is_file():
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.strip().startswith(KEY_NAME + '='):
                key = line.split('=', 1)[1].strip().strip('"').strip("'")
    return key or refuse('%s is not in the environment and not in ~/.cas_llm_keys.env' % KEY_NAME)


def load_passages(path):
    """The passages as a list of (id, text). Refuses a file that holds anything but id and text."""
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(data, list) or not all(isinstance(p, dict) and set(p) == {'id', 'text'} for p in data):
        refuse('The passage file must be a JSON list of {"id", "text"} and nothing else. This tool must never see the writer\'s kinds.')
    if len({p['id'] for p in data}) != len(data) or not all(isinstance(p['id'], str) and isinstance(p['text'], str) for p in data):
        refuse('Every passage needs its own text "id" and a text "text".')
    return [(p['id'], p['text']) for p in data]


def load_checker(path):
    spec = importlib.util.spec_from_file_location('check_labels_v21', str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module if callable(getattr(module, 'check_record', None)) else refuse('%s has no function check_record' % path)


def checker_messages(module, record, passage_id, text):
    """Run check_record(record, passage_text, passage_id). Its arguments are matched by name. An empty list = the record passes."""
    values = []
    for name, parameter in inspect.signature(module.check_record).parameters.items():
        low = name.lower()
        if parameter.default is not inspect.Parameter.empty and not (low.endswith('id') or 'record' in low or 'text' in low):
            break
        values.append(passage_id if low.endswith('id') else record if 'record' in low else text)
    return [str(message) for message in module.check_record(*values)]


def parse_reply(text):
    """The JSON object in a reply. If there is none, the reply text itself is the try, and the checker says so."""
    text = (text or '').strip()
    first, last = text.find('{'), text.rfind('}')
    try:
        value = json.loads(text[first:last + 1]) if 0 <= first < last else None
    except ValueError:
        value = None
    return value if isinstance(value, dict) else text[:2000]


def count_by_noetic(record):
    """How many different entries (by label, mind and relative_to) a try holds for each Noetic."""
    entries = record.get('entries') if isinstance(record, dict) else None
    seen = {tuple(str(e.get(f)) for f in ('noetic', 'label', 'mind', 'relative_to')) for e in (entries if isinstance(entries, list) else []) if isinstance(e, dict)}
    return {noetic: sum(1 for item in seen if item[0] == noetic) for noetic in {item[0] for item in seen}}


def withdrawn(module, records):
    """Per Noetic: how many more entries an earlier try held than the last try holds. The checker's own count when it has one."""
    if callable(getattr(module, 'withdrawn', None)):
        return dict(module.withdrawn(records))
    last, out = count_by_noetic(records[-1]), {}
    for earlier in records[:-1]:
        for noetic, count in count_by_noetic(earlier).items():
            out[noetic] = max(out.get(noetic, 0), count - last.get(noetic, 0))
    return {noetic: gone for noetic, gone in out.items() if gone > 0}


def status_of(tries):
    """The checker's words: 'LABELED', 'NOT_LABELED', or 'OPEN' while the passage is not final."""
    if tries and not tries[-1]['messages']:
        return 'LABELED'
    return 'NOT_LABELED' if len(tries) >= MAX_TRIES else 'OPEN'


def load_checkpoint(path):
    """Replay the checkpoint: the run events, the try events of every passage, and the tokens used so far."""
    state = {'runs': [], 'tries': {}, 'used_in': 0, 'used_out': 0}
    for line in Path(path).read_text(encoding='utf-8').splitlines() if Path(path).exists() else []:
        try:
            event = json.loads(line)
        except ValueError:
            continue   # a last line that was cut off while it was written
        state['used_in'] += event.get('in', 0)
        state['used_out'] += event.get('out', 0)
        if event.get('event') == 'run':
            state['runs'].append(event)
        elif event.get('event') == 'try':
            state['tries'].setdefault(event['passage_id'], []).append(event)
    return state


def build_messages(system, passage_id, text, tries):
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': ASK % {'id': passage_id, 'text': text}}]
    for attempt in tries:
        messages.append({'role': 'assistant', 'content': attempt['reply'] or '(empty reply)'})
        messages.append({'role': 'user', 'content': '\n'.join(attempt['messages'] + [AGAIN])})
    return messages


def http_call(key, model, messages):
    """One call. Returns (reply text, usage, finish reason, the model name the service put in its reply, and
    whether the reply held reasoning text)."""
    body = json.dumps({'model': model, 'temperature': 0, 'max_tokens': MAX_TOKENS, 'messages': messages}).encode('utf-8')
    request = urllib.request.Request(URL, data=body, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        data = json.loads(response.read())
    choice = data['choices'][0]
    return (choice['message'].get('content') or '', data.get('usage') or {}, choice.get('finish_reason'), data.get('model'),
            bool(choice['message'].get('reasoning_content')))


def finish(args, header, passages, checker, state, out, stopped_for):
    """Write the labels file and the receipt from the checkpoint state. Returns the number of passages that are not final."""
    rows, not_final, withdrawn_by_passage = [], [], {}
    tally = {'states': {}, 'tries': {}, 'models': {}, 'entries': {}, 'withdrawn': {}}
    count = getattr(checker, 'count_by_noetic', count_by_noetic)   # the checker's own count when it has one
    reasoned = sum(1 for tries in state['tries'].values() for attempt in tries if attempt.get('reply_has_reasoning'))

    def bump(table, name, by=1):
        tally[table][str(name)] = tally[table].get(str(name), 0) + by

    for passage_id, _ in passages:
        tries = state['tries'].get(passage_id, [])
        for attempt in tries:
            bump('models', attempt.get('reply_model'))
        status = status_of(tries)
        bump('states', status if tries else 'NOT_STARTED')
        if status == 'OPEN':
            not_final.append(passage_id)
            continue
        bump('tries', len(tries))
        if status == 'LABELED':
            rows.append(tries[-1]['record'])
            for noetic, number in count(tries[-1]['record']).items():
                bump('entries', noetic, number)
            gone = withdrawn(checker, [attempt['record'] for attempt in tries])
            for noetic, number in gone.items():
                bump('withdrawn', noetic, number)
            if gone:
                withdrawn_by_passage[passage_id] = gone
        else:   # the same row as failed_row() of the checker
            rows.append({'passage_id': passage_id, 'none_of_these': False, 'entries': [], 'not_enough_information': [],
                         'labeler_failed': True, 'tries': len(tries)})
    write_json(out, rows)
    receipt = dict(header, written_utc=now_utc(), labels_file=out.name, labels_sha256=sha_file(out), guide=str(args.guide),
                   instructions=str(args.instructions), passages_file=str(args.passages), complete=not not_final,
                   passages=len(passages), passages_by_state=tally['states'], passages_not_final=not_final,
                   passages_by_number_of_tries=tally['tries'], entries_in_final_records=sum(tally['entries'].values()),
                   entries_by_noetic=dict(sorted(tally['entries'].items())),
                   entries_withdrawn_between_tries=sum(tally['withdrawn'].values()),
                   entries_withdrawn_by_noetic=dict(sorted(tally['withdrawn'].items())), withdrawn_by_passage=withdrawn_by_passage,
                   model_asked_for=args.model, models_that_answered=tally['models'], tries_with_reasoning_text=reasoned,
                   one_passage_per_call=True, temperature=0,
                   tokens_sent=state['used_in'], tokens_returned=state['used_out'], stopped_for=stopped_for,
                   cap_in=state['runs'][-1]['cap_in'], cap_out=state['runs'][-1]['cap_out'],
                   caps_given_in_all_runs=[{k: r[k] for k in ('utc', 'cap_in', 'cap_out')} for r in state['runs']])
    write_json(out.with_name(out.name + '.receipt.json'), receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k not in header and k not in ('passages_not_final', 'withdrawn_by_passage', 'caps_given_in_all_runs')}))
    return len(not_final)


def run(args, caller=None):
    caller = caller or http_call
    for path in (args.guide, args.instructions, args.passages, args.checker):
        if not Path(path).is_file():
            refuse('cannot find %s' % path)
    passages, checker = load_passages(args.passages), load_checker(args.checker)
    system = (HEAD + '=== LABELING GUIDE ===\n' + Path(args.guide).read_text(encoding='utf-8').strip()
              + '\n\n=== LABELER INSTRUCTIONS ===\n' + Path(args.instructions).read_text(encoding='utf-8').strip() + '\n')
    header = {'tool': TOOL, 'provider': 'deepseek', 'model': args.model, 'guide_sha256': sha_file(args.guide),
              'instructions_sha256': sha_file(args.instructions), 'checker_sha256': sha_file(args.checker),
              'passages_sha256': sha_file(args.passages), 'tool_sha256': sha_file(__file__),
              'frame_sha256': hashlib.sha256((HEAD + ASK + AGAIN).encode('utf-8')).hexdigest(), 'seal_sha256': None}
    if args.seal:
        seal = json.loads(Path(args.seal).read_text(encoding='utf-8'))
        wrong = [role for role, name in SEALED if not isinstance(seal.get(role), dict) or seal[role].get('sha256') != header[name]]
        if wrong:
            refuse('these files do not have the sha256 in %s: %s' % (Path(args.seal).name, ', '.join(wrong)))
        header['seal_sha256'] = sha_file(args.seal)
    if args.dry_run:
        need = sum(len(m['content']) for m in build_messages(system, passages[0][0], passages[0][1], [])) // 3 + 1
        print(json.dumps(dict(header, dry_run=True, calls_made=0, passages=len(passages), system_characters=len(system),
                              upper_tokens_sent_for_one_first_try=need, upper_tokens_returned_for_one_try=MAX_TOKENS,
                              upper_tokens_sent_if_every_passage_takes_one_try=need * len(passages)), indent=1))
        return 0
    out = Path(args.output)
    log_path = out.with_name(out.name + '.tries.jsonl')
    state = load_checkpoint(log_path)
    cap_in, cap_out = args.cap_in, args.cap_out
    if state['runs']:
        changed = [k for k, v in header.items() if state['runs'][0]['header'].get(k) != v]
        if changed:
            refuse('%s was started with another %s. One labels file, one set of files. Use a new output name.' % (log_path.name, ', '.join(changed)))
        cap_in, cap_out = cap_in or state['runs'][-1]['cap_in'], cap_out or state['runs'][-1]['cap_out']
    if cap_in <= 0 or cap_out <= 0:
        refuse('The first run needs --cap-in N and --cap-out N. Take the numbers from the plan.')
    key = read_key()
    journal = open(log_path, 'a', encoding='utf-8', newline=chr(10))
    stop, held, why = threading.Event(), {'in': 0, 'out': 0}, {'stopped_for': None}

    def record_event(event):
        """Count an event's tokens and write it to the checkpoint at once. Call it with LOCK held."""
        state['used_in'] += event.get('in', 0)
        state['used_out'] += event.get('out', 0)
        journal.write(json.dumps(event, ensure_ascii=False) + chr(10))
        journal.flush()

    def halt(reason):
        why['stopped_for'] = why['stopped_for'] or reason
        stop.set()

    def spent(passage_id, tokens_in, tokens_out, note):
        """Tokens used outside a stored try: a failed call (upper estimate) or a try the checker could not read."""
        with LOCK:
            record_event({'event': 'spent', 'passage_id': passage_id, 'utc': now_utc(), 'in': tokens_in, 'out': tokens_out, 'why': note.replace(key, '[KEY]')})

    state['runs'].append({'event': 'run', 'utc': now_utc(), 'header': header, 'cap_in': cap_in, 'cap_out': cap_out})
    record_event(state['runs'][-1])

    def transport(passage_id, messages):
        """One answer of the model, or None. Starts a call only if both caps hold at the call's upper estimate."""
        need = sum(len(m['content']) for m in messages) // 3 + 1
        for _ in range(TRANSPORT_ATTEMPTS):
            with LOCK:
                if state['used_in'] + held['in'] + need > cap_in or state['used_out'] + held['out'] + MAX_TOKENS > cap_out:
                    halt('a token cap would be passed: sent %d of %d, returned %d of %d' % (state['used_in'], cap_in, state['used_out'], cap_out))
                if stop.is_set():
                    return None
                held['in'] += need
                held['out'] += MAX_TOKENS
            time.sleep(args.pace)
            wait, answer = 5, None
            try:
                answer = caller(key, args.model, messages)
            except urllib.error.HTTPError as error:
                if error.code in STOP_CODES:
                    halt('the service refused the call: HTTP %d %s' % (error.code, str(error.reason)[:80].replace(key, '[KEY]')))
                wait = 45 if error.code == 429 else 5
            except Exception as error:   # a time-out or a broken answer may still have been billed; an unreached service not
                if not isinstance(getattr(error, 'reason', None), (socket.gaierror, ConnectionRefusedError)):
                    spent(passage_id, need, MAX_TOKENS, 'upper estimate for a failed call: %s %s' % (type(error).__name__, str(error)[:100]))
            with LOCK:
                held['in'] -= need
                held['out'] -= MAX_TOKENS
            if answer is not None or stop.is_set():
                return answer
            time.sleep(wait)
        halt('the service did not answer %d calls in a row for %s' % (TRANSPORT_ATTEMPTS, passage_id))
        return None

    def work(passage):
        passage_id, text = passage
        tries = state['tries'][passage_id]
        while status_of(tries) == 'OPEN' and not stop.is_set():
            answer = transport(passage_id, build_messages(system, passage_id, text, tries))
            if answer is None:
                return
            reply, usage, finish_reason, reply_model = answer[:4]
            used_in = int(usage.get('prompt_tokens') or 0)
            used_out = max(int(usage.get('completion_tokens') or 0), int(usage.get('total_tokens') or 0) - used_in)
            record = parse_reply(reply)
            try:
                messages = checker_messages(checker, record, passage_id, text)
            except Exception as error:   # the checker itself failed: a tool fault, not a try
                spent(passage_id, used_in, used_out, 'the checker raised %s: %s' % (type(error).__name__, str(error)[:160]))
                return halt('the checker raised an error on %s' % passage_id)
            event = {'event': 'try', 'passage_id': passage_id, 'n': len(tries) + 1, 'utc': now_utc(), 'record': record,
                     'messages': messages, 'reply': reply, 'reply_model': reply_model, 'finish_reason': finish_reason,
                     'reply_has_reasoning': answer[4] if len(answer) > 4 else None, 'usage': usage, 'in': used_in, 'out': used_out}
            with LOCK:
                record_event(event)
                tries.append(event)

    todo = [p for p in passages if status_of(state['tries'].setdefault(p[0], [])) == 'OPEN']
    try:
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            list(pool.map(work, todo))
    finally:
        journal.close()
    return 1 if finish(args, header, passages, checker, state, out, why['stopped_for']) else 0


def main(argv=None, caller=None):
    parser = argparse.ArgumentParser(description='Label passages for team B with DeepSeek, guide v2.1, checker and three tries.')
    for name in ('model', 'guide', 'instructions', 'passages', 'output'):
        parser.add_argument(name)
    parser.add_argument('--cap-in', type=int, default=0, help='most tokens sent, over all runs')
    parser.add_argument('--cap-out', type=int, default=0, help='most tokens returned, over all runs')
    parser.add_argument('--pace', type=float, default=0.0, help='seconds to wait before each call')
    parser.add_argument('--workers', type=int, default=1)
    parser.add_argument('--checker', default=str(Path(__file__).resolve().parent / 'check_labels_v21.py'))
    parser.add_argument('--seal', default='', help='SEAL.json or PRACTICE_SET.json')
    parser.add_argument('--dry-run', action='store_true', help='make no call; print sizes, hashes and estimates')
    return run(parser.parse_args(argv), caller)


if __name__ == '__main__':
    sys.exit(main())
