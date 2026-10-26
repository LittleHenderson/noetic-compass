"""Have an outside model write plain everyday practice passages. The brief contains no CAS words.

Sends only the brief below. Never prints or stores a key.
Usage: write_passages_outside.py <provider> <model> <output.json> <id_prefix>
"""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ENDPOINTS = {'deepseek': ('https://api.deepseek.com/chat/completions', 'DEEPSEEK_API_KEY'),
             'gemini': ('https://generativelanguage.googleapis.com/v1beta/openai/chat/completions', 'GEMINI_API_KEY')}
FORBIDDEN = ['cause', 'effect', 'trigger', 'positive', 'negative', 'vibration', 'rhythm', 'idea', 'mind', 'noetic', 'resonate', 'resonance']
SETTINGS = ['a fishing boat', 'a public library', 'a construction site', 'a bakery before dawn', 'a call centre',
            'a veterinary clinic', 'a village bus route', 'a pottery studio', 'a laundromat', 'an airport gate']
KINDS = {
    'K1': 'something a person notices (a smell, a sound, an object, a phrase) brings some quite different thing into their thoughts, and the passage says what came to them',
    'K2': 'a person is plainly drawn toward one thing and plainly put off by another thing, shown through what they do or feel; and something lands on them either very strongly or hardly at all',
    'K3': 'the passage shows how what a person has lived through or learned over years shapes how they take something now; or it shows someone taking a plan, a dish, a machine fault or an argument apart into the pieces it is made of',
    'K4': 'a person has been exposed to the same thing over and over on a regular schedule and it has changed how they act without thinking',
    'K5': 'a purely physical description of things happening, with no person\'s thoughts, likes, memories or habits in it at all (weather, a machine running, goods being moved)',
}
# three passages per setting; kinds rotate so that the 30 passages hold K1 x7, K2 x7, K3 x7, K4 x5, K5 x4
PLAN = ['K1', 'K2', 'K3', 'K4', 'K1', 'K2', 'K3', 'K5', 'K1', 'K2', 'K3', 'K4', 'K1', 'K2', 'K3', 'K5', 'K1', 'K2', 'K3', 'K4',
        'K1', 'K2', 'K3', 'K5', 'K1', 'K2', 'K3', 'K4', 'K4', 'K5']
BRIEF = ('Write %d short everyday passages in plain English. Each passage is 3 to 5 sentences, 45 to 90 words, third person, '
         'past tense, about ordinary people with ordinary first names (vary names, ages and jobs). No lists, no headings, no moral, '
         'no summary sentence, no stock phrases or proverbs. Do not explain what a passage is about. Never use these words: %s.\n\n'
         'Write the passages in this order. For each one I give the setting and the kind of moment; never name the kind in the text:\n%s\n\n'
         'Reply with ONE JSON array and nothing else: [{"n": 1, "text": "..."}, ...] with exactly %d objects in the order given.')


def key_for(name):
    with open(os.path.join(os.path.expanduser('~'), '.cas_llm_keys.env'), encoding='utf-8') as stream:
        for line in stream:
            if line.strip().startswith(name + '='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    raise SystemExit('missing key ' + name)


def main(provider, model, out_path, prefix):
    url, key_name = ENDPOINTS[provider]
    key = key_for(key_name)
    jobs = [(SETTINGS[i // 3], PLAN[i]) for i in range(30)]
    rows, usage_total = [], {}
    for start in range(0, 30, 10):
        chunk = jobs[start:start + 10]
        listing = '\n'.join('%d. Setting: %s. Kind of moment: %s.' % (i + 1, s, KINDS[k]) for i, (s, k) in enumerate(chunk))
        body = json.dumps({'model': model, 'temperature': 1.0, 'max_tokens': 12000,
                           'messages': [{'role': 'user', 'content': BRIEF % (len(chunk), ', '.join(FORBIDDEN), listing, len(chunk))}]}).encode('utf-8')
        request = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
        with urllib.request.urlopen(request, timeout=240) as response:
            data = json.loads(response.read())
        for k, v in (data.get('usage') or {}).items():
            if isinstance(v, int):
                usage_total[k] = usage_total.get(k, 0) + v
        text = data['choices'][0]['message']['content'].strip()
        if text.startswith('```'):
            text = text.split('\n', 1)[1].rsplit('```', 1)[0]
        items = json.loads(text)
        assert len(items) == len(chunk), ('count', len(items))
        for (setting, kind), item in zip(chunk, items):
            rows.append({'id': '%s%02d' % (prefix, len(rows) + 1), 'setting': setting, 'kind': kind,
                         'physical_only': kind == 'K5', 'text': item['text'].strip()})
    bad = [(r['id'], w) for r in rows for w in FORBIDDEN if re.search(r'\b' + w + r'\w*\b', r['text'], flags=re.I)]
    words = [len(r['text'].split()) for r in rows]
    Path(out_path).write_text(json.dumps(rows, indent=1, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'provider': provider, 'model': model, 'passages': len(rows), 'forbidden_hits': bad,
                      'words_min_max': [min(words), max(words)], 'usage': usage_total}))


if __name__ == '__main__':
    main(*sys.argv[1:5])
