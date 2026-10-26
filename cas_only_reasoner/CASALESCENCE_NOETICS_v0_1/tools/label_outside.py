"""Label passages with an outside (non-Claude) model service. One passage per call.

Sends: the labeling guide and one passage. Never prints or stores a key. Plain Python, no project code.
Usage: label_outside.py <provider> <model> <guide.md> <passages.json> <output.json> [seconds_between_calls] [workers]
If the output file already exists, passages already labeled are kept and only failed ones are tried again.
"""
import hashlib
import json
import os
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ENDPOINTS = {'deepseek': ('https://api.deepseek.com/chat/completions', 'DEEPSEEK_API_KEY'),
             'gemini': ('https://generativelanguage.googleapis.com/v1beta/openai/chat/completions', 'GEMINI_API_KEY')}
HEAD = ('You are a careful labeler. Work only from the labeling guide below. Never force a label. '
        'Reply with ONE JSON object and nothing else.\n\n')
ASK = ('Label this passage exactly as Part B of the guide says. Reply with one JSON object of this shape and nothing else:\n'
       '{"passage_id": "%s", "none_of_these": false, "entries": [{"noetic": "^8", "words": "...", "mind": "...", '
       '"relative_to": "...", "certainty": "clear"}], "not_enough_information": [], "guide_problem": ""}\n'
       'Rules: "noetic" is one of "^1".."^9". "words", "mind" and "relative_to" are each "" or an exact, unbroken, '
       'case-sensitive copy of text from the passage. "certainty" is "clear" or "ambiguous" (if ambiguous add '
       '"other_candidate"). Add "reached_by": "reasoning" to an entry only where rule 15(b) says so. "guide_problem" is one short sentence if the guide was unclear for this passage, else "".\n\n'
       'Passage %s:\n%s')
NOETICS = ['^%d' % i for i in range(1, 10)]


def key_for(name):
    with open(os.path.join(os.path.expanduser('~'), '.cas_llm_keys.env'), encoding='utf-8') as stream:
        for line in stream:
            if line.strip().startswith(name + '='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    raise SystemExit('missing key ' + name)


def call(url, key, model, guide, passage):
    body = json.dumps({'model': model, 'temperature': 0, 'max_tokens': 6000,
                       'messages': [{'role': 'system', 'content': HEAD + guide},
                                    {'role': 'user', 'content': ASK % (passage['id'], passage['id'], passage['text'])}]}).encode('utf-8')
    request = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    with urllib.request.urlopen(request, timeout=180) as response:
        data = json.loads(response.read())
    return data['choices'][0]['message']['content'], data.get('usage') or {}


def parse(text, passage):
    text = text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1].rsplit('```', 1)[0]
    row = json.loads(text)
    assert row.get('passage_id') == passage['id']
    problems = 0
    for entry in row.get('entries', []):
        assert entry.get('noetic') in NOETICS
        for field in ('words', 'mind', 'relative_to'):
            entry.setdefault(field, '')
            if entry[field] and entry[field] not in passage['text']:
                problems += 1
        entry.setdefault('certainty', 'clear')
    row.setdefault('none_of_these', False)
    row.setdefault('not_enough_information', [])
    row.setdefault('guide_problem', '')
    return row, problems


def main(provider, model, guide_path, passages_path, out_path, pace='0', workers='1'):
    pace, workers = float(pace), int(workers)
    guide = Path(guide_path).read_text(encoding='utf-8')
    url, key_name = ENDPOINTS[provider]
    key = key_for(key_name)
    passages = [{'id': p['id'], 'text': p['text']} for p in json.loads(Path(passages_path).read_text(encoding='utf-8'))]
    out = Path(out_path)
    done, log, tokens, lock = {}, [], {'prompt_tokens': 0, 'completion_tokens': 0}, threading.Lock()
    if out.exists():
        done = {r['passage_id']: r for r in json.loads(out.read_text(encoding='utf-8')) if not r.get('labeler_failed')}
        log = [{'passage': pid, 'kept_from_earlier_run': True} for pid in done]

    def save():
        blank = {'none_of_these': False, 'entries': [], 'not_enough_information': [], 'guide_problem': '', 'labeler_failed': True}
        rows = [done.get(p['id'], dict(blank, passage_id=p['id'])) for p in passages]
        out.write_text(json.dumps(rows, indent=1, ensure_ascii=False) + chr(10), encoding='utf-8', newline=chr(10))
        return rows

    def work(passage):
        row, note = None, None
        for attempt in (1, 2, 3):
            time.sleep(pace)
            try:
                text, usage = call(url, key, model, guide, passage)
                row, quote_problems = parse(text, passage)
                note = {'passage': passage['id'], 'attempt': attempt, 'quote_problems': quote_problems}
                with lock:
                    for name in tokens:
                        tokens[name] += int(usage.get(name, 0) or 0)
                break
            except Exception as error:
                note = {'passage': passage['id'], 'attempt': attempt,
                        'error': (type(error).__name__ + ': ' + str(error)[:120]).replace(key, '[KEY]')}
                # a rate-limit answer means wait, then try the same passage again
                time.sleep(45 if '429' in str(error) else 3)
        with lock:
            if row is not None:
                done[passage['id']] = row
            log.append(note)
            if len(log) % 20 == 0:
                save()

    todo = [p for p in passages if p['id'] not in done]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(work, todo))
    rows = save()
    receipt = {'provider': provider, 'model': model, 'passages': len(rows), 'failed': sum(1 for r in rows if r.get('labeler_failed')),
               'quote_problems': sum(n.get('quote_problems', 0) for n in log), 'tokens': tokens,
               'guide': str(guide_path), 'guide_sha256': hashlib.sha256(Path(guide_path).read_bytes()).hexdigest(), 'log': log}
    out.with_name(out.name + '.receipt.json').write_text(json.dumps(receipt, indent=1) + chr(10), encoding='utf-8', newline=chr(10))
    print(json.dumps({k: receipt[k] for k in ('provider', 'model', 'passages', 'failed', 'quote_problems', 'tokens')}))


if __name__ == '__main__':
    main(*sys.argv[1:8])
