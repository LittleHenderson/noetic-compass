"""Label the first-look passages with an outside (non-Claude) model service. One passage per call.

Sends: the labeling guide and one passage. Never prints or stores a key. Plain Python, no project code.
Usage: label_with_outside_model.py <provider> <model> <output.json>
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
GUIDE = (HERE.parent / '02_LABELING_GUIDE_v0_1.md').read_text(encoding='utf-8')
ENDPOINTS = {'deepseek': ('https://api.deepseek.com/chat/completions', 'DEEPSEEK_API_KEY'),
             'gemini': ('https://generativelanguage.googleapis.com/v1beta/openai/chat/completions', 'GEMINI_API_KEY')}
SYSTEM = ('You are a careful labeler. Work only from the labeling guide below. Never force a label. '
          'Reply with ONE JSON object and nothing else.\n\n' + GUIDE)
ASK = ('Label this passage exactly as Part B of the guide says. Reply with one JSON object of this shape and nothing else:\n'
       '{"passage_id": "%s", "none_of_these": false, "entries": [{"noetic": "^8", "words": "...", "mind": "...", '
       '"relative_to": "...", "certainty": "clear"}], "not_enough_information": [], "guide_problem": ""}\n'
       'Rules: "noetic" is one of "^1".."^9". "words", "mind" and "relative_to" are each "" or an exact, unbroken, '
       'case-sensitive copy of text from the passage. "certainty" is "clear" or "ambiguous" (if ambiguous add '
       '"other_candidate"). "guide_problem" is one short sentence if the guide was unclear for this passage, else "".\n\n'
       'Passage %s:\n%s')


def key_for(name):
    with open(os.path.join(os.path.expanduser('~'), '.cas_llm_keys.env'), encoding='utf-8') as stream:
        for line in stream:
            if line.strip().startswith(name + '='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    raise SystemExit('missing key ' + name)


def call(url, key, model, passage):
    body = json.dumps({'model': model, 'temperature': 0, 'max_tokens': 1500,
                       'messages': [{'role': 'system', 'content': SYSTEM},
                                    {'role': 'user', 'content': ASK % (passage['id'], passage['id'], passage['text'])}]}).encode('utf-8')
    request = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.loads(response.read())
    return data['choices'][0]['message']['content'], data.get('usage', {})


def parse(text, passage):
    text = text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1].rsplit('```', 1)[0]
    row = json.loads(text)
    assert row.get('passage_id') == passage['id']
    problems = 0
    for entry in row.get('entries', []):
        assert entry.get('noetic') in ['^%d' % i for i in range(1, 10)]
        for field in ('words', 'mind', 'relative_to'):
            entry.setdefault(field, '')
            if entry[field] and entry[field] not in passage['text']:
                problems += 1
        entry.setdefault('certainty', 'clear')
    row.setdefault('none_of_these', False)
    row.setdefault('not_enough_information', [])
    row.setdefault('guide_problem', '')
    return row, problems


def main(provider, model, out_name):
    url, key_name = ENDPOINTS[provider]
    key = key_for(key_name)
    passages = json.loads((HERE / 'passages_for_labelers.json').read_text(encoding='utf-8'))
    rows, log, tokens = [], [], {'prompt_tokens': 0, 'completion_tokens': 0}
    for passage in passages:
        row, note = None, None
        for attempt in (1, 2):
            try:
                text, usage = call(url, key, model, passage)
                for k in tokens:
                    tokens[k] += int(usage.get(k, 0) or 0)
                row, quote_problems = parse(text, passage)
                note = {'passage': passage['id'], 'attempt': attempt, 'quote_problems': quote_problems}
                break
            except Exception as error:
                note = {'passage': passage['id'], 'attempt': attempt, 'error': type(error).__name__ + ': ' + str(error)[:120].replace(key, '[KEY]')}
                time.sleep(2)
        if row is None:
            row = {'passage_id': passage['id'], 'none_of_these': False, 'entries': [], 'not_enough_information': [],
                   'guide_problem': '', 'labeler_failed': True}
        rows.append(row)
        log.append(note)
    (HERE / out_name).write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    receipt = {'provider': provider, 'model': model, 'passages': len(rows), 'failed': sum(1 for r in rows if r.get('labeler_failed')),
               'quote_problems': sum(n.get('quote_problems', 0) for n in log), 'tokens': tokens,
               'guide_sha256': hashlib.sha256(GUIDE.encode('utf-8')).hexdigest(), 'log': log}
    (HERE / (out_name + '.receipt.json')).write_text(json.dumps(receipt, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: receipt[k] for k in ('provider', 'model', 'passages', 'failed', 'quote_problems', 'tokens')}))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
