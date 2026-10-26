"""Have an outside model write the verdict passages from a plain brief with no CAS words.

Sends only the brief below. Never prints or stores a key. Saves after every call and resumes if run again.
Usage: write_verdict_passages.py <provider> <model> <output.json> <seconds_between_calls> [wait_until_HH:MM]
"""
import datetime
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ENDPOINTS = {'deepseek': ('https://api.deepseek.com/chat/completions', 'DEEPSEEK_API_KEY'),
             'gemini': ('https://generativelanguage.googleapis.com/v1beta/openai/chat/completions', 'GEMINI_API_KEY')}
FORBIDDEN = ['cause', 'effect', 'trigger', 'positive', 'negative', 'vibration', 'rhythm', 'idea', 'mind', 'noetic', 'resonate', 'resonance']
SETTINGS = [
    'a lighthouse', 'a dental surgery', 'a night bus depot', 'a flower stall', 'a boxing gym', 'a recording studio',
    'a mountain hut', 'a post office sorting room', 'a hotel laundry', 'a vineyard at harvest', 'a tailor\'s shop',
    'a river ferry', 'a university laboratory', 'a care home', 'a bicycle workshop', 'a fish market', 'a courtroom corridor',
    'a radio newsroom', 'a greenhouse', 'a quarry', 'a school canteen', 'a locksmith\'s van', 'a harbour crane cabin',
    'a puppet theatre', 'a cheese cellar', 'a customs desk', 'a chess club', 'a wind farm control room', 'a barber shop',
    'a dairy at milking time', 'a museum storeroom', 'a taxi rank at night', 'a scrapyard', 'a nursery school',
    'a ski lift station', 'a print shop', 'a beekeeper\'s yard', 'a swimming pool', 'a shoe repair kiosk', 'a warehouse loading bay']
KINDS = {
    'K1': 'something a person notices (a smell, a sound, an object, a phrase) brings some quite different thing into their thoughts, and the passage says what came to them',
    'K2': 'a person is plainly drawn toward one thing and plainly put off by another thing, shown through what they do or feel; and something lands on them either very strongly or hardly at all',
    'K3': 'what a person has lived through or learned over many years shapes how they take something now',
    'K4': 'someone takes a plan, a dish, a machine fault, a bill or an argument apart into the pieces it is made of, and the passage names the pieces',
    'K5': 'a person has been exposed to the same thing over and over on a regular schedule, and it has changed how they act without thinking',
    'K6': 'an experienced person notices a small sign and knows what it means',
    'K7': 'a person works through several clues step by step and reaches a conclusion',
    'K8': 'a purely physical description of things happening, with no person\'s thoughts, likes, memories or habits in it at all (weather, a machine running, goods being moved)',
    'K9': 'a person does ordinary things in the setting; nothing about their likes, dislikes, memories, habits or thoughts is shown',
}
COUNTS = {'K1': 60, 'K2': 60, 'K3': 60, 'K4': 60, 'K5': 60, 'K6': 30, 'K7': 30, 'K8': 60, 'K9': 20}
PER_CALL = 30
BRIEF = ('Write %d short everyday passages in plain English. Each passage is 3 to 5 sentences, 45 to 90 words, third person, '
         'past tense, about ordinary people with ordinary first names (use many different names, ages and jobs; never reuse a name '
         'within this list). No lists, no headings, no moral, no summary sentence, no stock phrases or proverbs. Do not explain what '
         'a passage is about. Make the passages clearly different from each other in wording and in what happens. '
         'Never use these words: %s.\n\n'
         'Write the passages in this order. For each one I give the setting and the kind of moment; never name the kind in the text:\n%s\n\n'
         'Reply with ONE JSON array and nothing else: [{"n": 1, "text": "..."}, ...] with exactly %d objects in the order given.')


def key_for(name):
    with open(os.path.join(os.path.expanduser('~'), '.cas_llm_keys.env'), encoding='utf-8') as stream:
        for line in stream:
            if line.strip().startswith(name + '='):
                return line.split('=', 1)[1].strip().strip('"').strip("'")
    raise SystemExit('missing key ' + name)


def plan():
    """Fixed, seeded order: 440 (setting, kind) jobs, kinds mixed, eleven per setting."""
    rng = random.Random(20261005)
    kinds = [kind for kind, count in COUNTS.items() for _ in range(count)]
    rng.shuffle(kinds)
    settings = [setting for setting in SETTINGS for _ in range(11)]
    rng.shuffle(settings)
    return list(zip(settings, kinds))


def main(provider, model, out_path, pace, wait_until=None):
    if wait_until:
        hour, minute = (int(x) for x in wait_until.split(':'))
        now = datetime.datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += datetime.timedelta(days=1)
        time.sleep((target - now).total_seconds())
    url, key_name = ENDPOINTS[provider]
    key = key_for(key_name)
    out = Path(out_path)
    jobs = plan()
    state = json.loads(out.read_text(encoding='utf-8')) if out.exists() else {'provider': provider, 'model': model, 'chunks': {}, 'log': []}
    for start in range(0, len(jobs), PER_CALL):
        if str(start) in state['chunks']:
            continue
        chunk = jobs[start:start + PER_CALL]
        listing = '\n'.join('%d. Setting: %s. Kind of moment: %s.' % (i + 1, s, KINDS[k]) for i, (s, k) in enumerate(chunk))
        body = json.dumps({'model': model, 'temperature': 1.0, 'max_tokens': 30000,
                           'messages': [{'role': 'user', 'content': BRIEF % (len(chunk), ', '.join(FORBIDDEN), listing, len(chunk))}]}).encode('utf-8')
        done = False
        for attempt in (1, 2, 3):
            time.sleep(float(pace))
            try:
                request = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
                with urllib.request.urlopen(request, timeout=300) as response:
                    data = json.loads(response.read())
                text = data['choices'][0]['message']['content'].strip()
                if text.startswith('```'):
                    text = text.split('\n', 1)[1].rsplit('```', 1)[0]
                items = json.loads(text)
                assert len(items) == len(chunk), ('count', len(items))
                state['chunks'][str(start)] = [{'setting': s, 'kind': k, 'text': item['text'].strip()} for (s, k), item in zip(chunk, items)]
                state['log'].append({'start': start, 'attempt': attempt, 'ok': True, 'usage': data.get('usage')})
                done = True
                break
            except Exception as error:
                detail = ''
                if isinstance(error, urllib.error.HTTPError):
                    detail = error.read()[:400].decode('utf-8', 'replace')
                state['log'].append({'start': start, 'attempt': attempt, 'ok': False,
                                     'error': (type(error).__name__ + ': ' + str(error)[:100] + ' ' + detail).replace(key, '[KEY]')})
                time.sleep(60 if '429' in str(error) else 5)
        out.write_text(json.dumps(state, indent=1, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
        if not done:
            print(json.dumps({'status': 'STOPPED', 'chunks_done': len(state['chunks']), 'of': -(-len(jobs) // PER_CALL), 'last_error': state['log'][-1]})[:900])
            return
    rows = [row for start in sorted(state['chunks'], key=int) for row in state['chunks'][start]]
    bad = sum(1 for r in rows for w in FORBIDDEN if re.search(r'\b' + w + r'\w*\b', r['text'], flags=re.I))
    words = [len(r['text'].split()) for r in rows]
    print(json.dumps({'status': 'ALL_WRITTEN', 'passages': len(rows), 'forbidden_word_hits': bad, 'words_min_max': [min(words), max(words)]}))


if __name__ == '__main__':
    main(*sys.argv[1:6])
