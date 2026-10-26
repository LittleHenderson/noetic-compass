"""Blind passage writer for label-agreement attempt v2.0 (plan: 09_LABEL_AGREEMENT_PLAN_v2_0.md).

An outside model writes plain everyday passages from a brief that has no CAS words in it. The writer is
not a label team. It never sees the guide, the definitions, the hold table, the checker, a label or a
reader. The label teams are never told the kind of a passage. Modelled on tools/write_verdict_passages.py:
the same writer, the same brief text, the same forbidden-word list, 30 passages per call.

Modes
  practice   120 passages from 6 settings, twenty each. --round 1 (default) or --round 2.
             Round 2 is used only if the first practice pass fails a seal condition. It has its own
             6 settings and its own seed, so its passages are new.
  verdict    760 passages from 40 settings, nineteen each. Kinds K1 to K10; K2 is split into K2a and K2b.

Usage
  write_passages_v2.py <practice|verdict> <state.json> [--round 1|2] [--pace SECONDS]
                       [--daily-cap N] [--ledger PATH] [--wait-until HH:MM]
  write_passages_v2.py <practice|verdict> --dry-run [--round 1|2] [--show-brief]

Key
  The tool reads GEMINI_API_KEY from the environment of the shell that runs it. It opens no key file.
  It never prints or stores the key. Error text is scrubbed before it is logged.

Checkpoint and resume
  The state file is saved after every call (written to a .partial file, then renamed). Run the same
  command again and it goes on where it stopped. It refuses a state file made from another job list.

Daily cap
  The free tier allows about 20 requests per day on this key. Every request, retries too, is written
  with its time to a small ledger file (no key, no passage text). Before each request the tool counts
  the requests of the last 24 hours. At --daily-cap (default 18) it saves and stops cleanly:
  status STOPPED_DAILY_CAP, exit code 0. If the service itself says the quota is used up, the tool
  also saves and stops cleanly. It does not retry against a used-up quota.

Exit codes: 0 = all written, or a clean stop at the daily cap. 1 = refused to start. 2 = stopped on errors.

--dry-run sends nothing and needs no key. It prints the job counts and the hash of the job list.
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

PROVIDER = 'gemini'
MODEL = 'gemini-2.5-flash'
URL = 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions'
KEY_NAME = 'GEMINI_API_KEY'
STATE_SCHEMA = 'casalescence/label-agreement-v2-writer-state/1'
PER_CALL = 30
DEFAULT_DAILY_CAP = 18

# The same twelve words as the first attempt.
FORBIDDEN = ['cause', 'effect', 'trigger', 'positive', 'negative', 'vibration', 'rhythm', 'idea', 'mind', 'noetic', 'resonate', 'resonance']

# 52 plain workplaces and places. None was used in the first look, in practice rounds 2 and 3, or in
# the first verdict set (60 settings; the list is in the plan). 40 for the verdict set, 6 for the
# practice pass, 6 held back for a second practice pass.
SETTINGS = {
    'verdict': [
        'a hardware store', 'a car wash', 'a pharmacy counter', 'a bowling alley', 'a paint factory', 'a sawmill',
        'a blacksmith\'s forge', 'a glassblowing workshop', 'an upholstery workshop', 'a candle workshop', 'a campsite',
        'a registry office', 'a cinema projection booth', 'a zoo\'s reptile house', 'an ice rink', 'a fire station',
        'a lost property office', 'a railway signal box', 'a canal lock', 'a petrol station', 'a supermarket checkout',
        'a butcher\'s shop', 'a coffee roastery', 'a brewery', 'a flour mill', 'a mushroom farm', 'an archaeology dig',
        'a horse stable', 'a driving school car', 'a planetarium', 'a weather station', 'a bottling plant',
        'a motorway service station', 'an optician\'s shop', 'a blood donation centre', 'a bank branch', 'a toy shop',
        'a climbing wall', 'a jeweller\'s workshop', 'a brickworks'],
    'practice1': ['a chocolate factory', 'a furniture removal van', 'an auction house', 'a tennis club',
                  'a water treatment plant', 'a tea room'],
    'practice2': ['a paper mill', 'a picture framing shop', 'a snooker hall', 'a soap workshop', 'a dance school',
                  'a youth hostel'],
}
PER_SETTING = {'verdict': 19, 'practice1': 20, 'practice2': 20}
SEEDS = {'verdict': 20261013, 'practice1': 20261011, 'practice2': 20261012}

# What the writer is told about each kind of moment. K1 and K3 to K9 are the strings of the first
# attempt's tool, character for character. K2a and K2b are the two halves of its K2 string, cut at
# '; and ', character for character. K10 is new. self_check() proves the first two statements by hash.
KINDS = {
    'K1': 'something a person notices (a smell, a sound, an object, a phrase) brings some quite different thing into their thoughts, and the passage says what came to them',
    'K2a': 'a person is plainly drawn toward one thing and plainly put off by another thing, shown through what they do or feel',
    'K2b': 'something lands on them either very strongly or hardly at all',
    'K3': 'what a person has lived through or learned over many years shapes how they take something now',
    'K4': 'someone takes a plan, a dish, a machine fault, a bill or an argument apart into the pieces it is made of, and the passage names the pieces',
    'K5': 'a person has been exposed to the same thing over and over on a regular schedule, and it has changed how they act without thinking',
    'K6': 'an experienced person notices a small sign and knows what it means',
    'K7': 'a person works through several clues step by step and reaches a conclusion',
    'K8': 'a purely physical description of things happening, with no person\'s thoughts, likes, memories or habits in it at all (weather, a machine running, goods being moved)',
    'K9': 'a person does ordinary things in the setting; nothing about their likes, dislikes, memories, habits or thoughts is shown',
    'K10': 'free: a person at work in the setting; the writer chooses what happens',
}
COUNTS = {
    'verdict': {'K1': 140, 'K2a': 120, 'K2b': 80, 'K3': 60, 'K4': 70, 'K5': 100, 'K6': 30, 'K7': 30, 'K8': 80, 'K9': 20, 'K10': 30},
    'practice': {'K1': 18, 'K2a': 18, 'K2b': 18, 'K4': 18, 'K5': 18, 'K7': 15, 'K3': 6, 'K6': 6, 'K8': 3},
}
TOTALS = {'verdict': 760, 'practice1': 120, 'practice2': 120}

# The brief of the first attempt, character for character.
BRIEF = ('Write %d short everyday passages in plain English. Each passage is 3 to 5 sentences, 45 to 90 words, third person, '
         'past tense, about ordinary people with ordinary first names (use many different names, ages and jobs; never reuse a name '
         'within this list). No lists, no headings, no moral, no summary sentence, no stock phrases or proverbs. Do not explain what '
         'a passage is about. Make the passages clearly different from each other in wording and in what happens. '
         'Never use these words: %s.\n\n'
         'Write the passages in this order. For each one I give the setting and the kind of moment; never name the kind in the text:\n%s\n\n'
         'Reply with ONE JSON array and nothing else: [{"n": 1, "text": "..."}, ...] with exactly %d objects in the order given.')

# sha256 of the strings in tools/write_verdict_passages.py (first attempt), taken on 2026-10-05.
V1_2_SHA256 = {
    'BRIEF': '9c2e2a16b1ab9a56bb83b0050b3e4a9562db96d2a596b1ee7a189dfaa07ac3db',
    'FORBIDDEN': '77fe649bf045ff861f833186894aa1312e65d8150f9f79ec8f6b7cd0f3b6886e',
    'K1': 'b1c4a5371f676371620a60ca275ffc8eb3ad227cf367f32853031dd42b6ba386',
    'K2': '76e286afafcec6ecd45542a007407a5092863eb6751994b69a79b6259dce9e2d',
    'K3': 'a5dffda3c089548dc162f88138047f4b2d697d31630dd245076494c38d30216d',
    'K4': '116a820d627285811f65fedc06ca319acb3761998ffcf80b68576c22144ce185',
    'K5': '4ba0a0b429db31fd4b9c86d2e381acbcacdb68703ac9a9f9f73e9851452bec0d',
    'K6': '9596b885dff0646291e1cbad4f0f779edd46052864f87ee853437716b1996341',
    'K7': '8d489e67d929337c890b8693925812b7e682b856d225191a1a72ce6adea9d726',
    'K8': 'b80bae9a4471014be1730e2177ad9454591745e4c7d09f4821d97c3f49e8201a',
    'K9': '97a50b68e8e111dfdd8ac51d757b8e5f7be7e5e3c2b50380b4d6c4566d9e7d51',
}

# sha256 of each fixed job list (setting and kind of every passage, in order). The plan prints the same
# values. If a Python version ever shuffled differently, the tool refuses instead of writing another set.
EXPECTED_JOBS_SHA256 = {
    'verdict': 'a7068c8fc92d1170e87941cb528fe67a3601e545c9170958b196f2f5048898bc',
    'practice1': 'a20aa9af008044a738b9d0b6285493f67fedcec712185974bf6265fe1627f166',
    'practice2': '5b630b4cad9a314bb006227975e9c7199552ee8821aaeb0cf657909544551216',
}


def sha_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def plan_name(mode, round_number):
    """'verdict', 'practice1' or 'practice2'."""
    if mode == 'verdict':
        return 'verdict'
    if mode == 'practice' and int(round_number) in (1, 2):
        return 'practice%d' % int(round_number)
    raise SystemExit('REFUSED: mode must be practice or verdict, and --round 1 or 2')


def jobs(name):
    """The fixed, seeded job list: one (setting, kind) per passage, kinds mixed, the same count per setting."""
    rng = random.Random(SEEDS[name])
    counts = COUNTS['verdict' if name == 'verdict' else 'practice']
    kinds = [kind for kind, count in counts.items() for _ in range(count)]
    rng.shuffle(kinds)
    settings = [setting for setting in SETTINGS[name] for _ in range(PER_SETTING[name])]
    rng.shuffle(settings)
    return list(zip(settings, kinds))


def jobs_sha256(name):
    return sha_text(json.dumps(jobs(name), ensure_ascii=False))


def briefs_record(name):
    """Everything that decides what the writer is asked. seal_v2.py hashes this record."""
    return {'provider': PROVIDER, 'model': MODEL, 'brief': BRIEF, 'forbidden': FORBIDDEN, 'kinds': KINDS,
            'counts': COUNTS['verdict' if name == 'verdict' else 'practice'], 'settings': SETTINGS[name],
            'per_setting': PER_SETTING[name], 'per_call': PER_CALL, 'seed': SEEDS[name], 'temperature': 1.0}


def briefs_sha256(name):
    return sha_text(json.dumps(briefs_record(name), ensure_ascii=False, sort_keys=True))


def self_check():
    """Refuse to run if a constant no longer says what the plan says."""
    problems = []
    if sha_text(BRIEF) != V1_2_SHA256['BRIEF']:
        problems.append('BRIEF differs from the first attempt')
    if sha_text(json.dumps(FORBIDDEN)) != V1_2_SHA256['FORBIDDEN']:
        problems.append('FORBIDDEN differs from the first attempt')
    for kind in ('K1', 'K3', 'K4', 'K5', 'K6', 'K7', 'K8', 'K9'):
        if sha_text(KINDS[kind]) != V1_2_SHA256[kind]:
            problems.append(kind + ' differs from the first attempt')
    if sha_text(KINDS['K2a'] + '; and ' + KINDS['K2b']) != V1_2_SHA256['K2']:
        problems.append('K2a and K2b are not the two halves of the first attempt\'s K2')
    every = SETTINGS['verdict'] + SETTINGS['practice1'] + SETTINGS['practice2']
    if len(set(every)) != len(every) or [len(SETTINGS[n]) for n in ('verdict', 'practice1', 'practice2')] != [40, 6, 6]:
        problems.append('settings: need 40 + 6 + 6, all different')
    for name in ('verdict', 'practice1', 'practice2'):
        counts = COUNTS['verdict' if name == 'verdict' else 'practice']
        if sum(counts.values()) != TOTALS[name] or len(SETTINGS[name]) * PER_SETTING[name] != TOTALS[name]:
            problems.append(name + ': counts do not add up to %d' % TOTALS[name])
        if set(counts) - set(KINDS):
            problems.append(name + ': a kind has no brief')
        if jobs_sha256(name) != EXPECTED_JOBS_SHA256[name]:
            problems.append(name + ': the job list is not the one in the plan (JOB_LIST_CHANGED)')
    for word in FORBIDDEN:
        pattern = r'\b' + word + r'\w*\b'
        if any(re.search(pattern, text, flags=re.I) for text in list(KINDS.values()) + every):
            problems.append('a kind brief or a setting holds the forbidden word ' + word)
    if problems:
        raise SystemExit('REFUSED: ' + '; '.join(problems))


def brief_for(chunk):
    listing = '\n'.join('%d. Setting: %s. Kind of moment: %s.' % (i + 1, s, KINDS[k]) for i, (s, k) in enumerate(chunk))
    return BRIEF % (len(chunk), ', '.join(FORBIDDEN), listing, len(chunk))


def save(path, value):
    """Write to a .partial file, then rename, so a crash never leaves half a file. LF line ends."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + '.partial')
    partial.write_text(json.dumps(value, indent=1, ensure_ascii=False) + chr(10), encoding='utf-8', newline=chr(10))
    os.replace(partial, path)


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def recent_requests(ledger, hours=24):
    """Times of the requests sent in the last `hours` hours."""
    edge = now_utc() - datetime.timedelta(hours=hours)
    times = []
    for row in ledger.get('requests', []):
        try:
            when = datetime.datetime.fromisoformat(row['utc'])
        except (KeyError, TypeError, ValueError):
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=datetime.timezone.utc)
        if when >= edge:
            times.append(when)
    return sorted(times)


def read_items(text, expected):
    """Turn the writer's reply into `expected` passage texts, in the order asked for."""
    text = text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1].rsplit('```', 1)[0]
    items = json.loads(text)
    assert isinstance(items, list) and len(items) == expected, ('count', len(items) if isinstance(items, list) else 'not a list')
    assert all(isinstance(item, dict) and isinstance(item.get('text'), str) and item['text'].strip() for item in items), 'an item has no text'
    numbers = [item.get('n') for item in items]
    if all(isinstance(n, int) and not isinstance(n, bool) for n in numbers):
        assert sorted(numbers) == list(range(1, expected + 1)), 'the numbers are not 1 to %d' % expected
        items = sorted(items, key=lambda item: item['n'])
        order = 'by n'
    else:
        assert all(n is None for n in numbers), 'some items have a number and some do not'
        order = 'by position'
    return [item['text'].strip() for item in items], order


def summary(state, job_list):
    rows = [row for start in sorted(state['chunks'], key=int) for row in state['chunks'][start]]
    hits = sum(1 for row in rows for word in FORBIDDEN if re.search(r'\b' + word + r'\w*\b', row['text'], flags=re.I))
    lengths = [len(row['text'].split()) for row in rows] or [0]
    by_kind = {}
    for row in rows:
        by_kind[row['kind']] = by_kind.get(row['kind'], 0) + 1
    return {'passages': len(rows), 'of': len(job_list), 'forbidden_word_hits': hits,
            'words_min_max': [min(lengths), max(lengths)], 'written_by_kind': dict(sorted(by_kind.items()))}


def dry_run(name, show_brief):
    job_list = jobs(name)
    by_kind, by_setting = {}, {}
    for setting, kind in job_list:
        by_kind[kind] = by_kind.get(kind, 0) + 1
        by_setting[setting] = by_setting.get(setting, 0) + 1
    print(json.dumps({'status': 'DRY_RUN_NOTHING_SENT', 'plan': name, 'writer': PROVIDER + ' ' + MODEL, 'passages': len(job_list),
                      'calls': -(-len(job_list) // PER_CALL), 'by_kind': {kind: by_kind[kind] for kind in KINDS if kind in by_kind},
                      'settings': len(by_setting),
                      'per_setting_min_max': [min(by_setting.values()), max(by_setting.values())], 'seed': SEEDS[name],
                      'jobs_sha256': jobs_sha256(name), 'briefs_sha256': briefs_sha256(name)}, indent=1))
    if show_brief:
        print(brief_for(job_list[:PER_CALL]))


def main(argv):
    parser = argparse.ArgumentParser(description='Blind passage writer for label-agreement attempt v2.0.')
    parser.add_argument('mode', choices=['practice', 'verdict'])
    parser.add_argument('state', nargs='?', help='state file; saved after every call')
    parser.add_argument('--round', type=int, default=1, choices=[1, 2], help='practice pass 1 or 2')
    parser.add_argument('--pace', type=float, default=20.0, help='seconds to wait before each request')
    parser.add_argument('--daily-cap', type=int, default=DEFAULT_DAILY_CAP, help='most requests in any 24 hours')
    parser.add_argument('--ledger', help='request ledger file; default label_v2/writer_request_ledger.json')
    parser.add_argument('--wait-until', help='local HH:MM to start at')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--show-brief', action='store_true')
    args = parser.parse_args(argv)

    self_check()
    name = plan_name(args.mode, args.round)
    if args.dry_run:
        dry_run(name, args.show_brief)
        return 0
    if not args.state:
        raise SystemExit('REFUSED: name a state file')
    key = os.environ.get(KEY_NAME, '').strip()
    if not key:
        raise SystemExit('REFUSED: %s is not set in the environment. This tool opens no key file.' % KEY_NAME)

    if args.wait_until:
        hour, minute = (int(part) for part in args.wait_until.split(':'))
        now = datetime.datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += datetime.timedelta(days=1)
        time.sleep((target - now).total_seconds())

    job_list = jobs(name)
    out = Path(args.state)
    ledger_path = Path(args.ledger) if args.ledger else Path(__file__).resolve().parent.parent / 'label_v2' / 'writer_request_ledger.json'
    ledger = json.loads(ledger_path.read_text(encoding='utf-8')) if ledger_path.exists() else {'what': 'time of every request sent to the passage writer; no key, no passage text', 'requests': []}
    this_tool = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if out.exists():
        state = json.loads(out.read_text(encoding='utf-8'))
        if state.get('plan') != name or state.get('jobs_sha256') != jobs_sha256(name) or state.get('briefs_sha256') != briefs_sha256(name):
            raise SystemExit('REFUSED: this state file was made from another job list or another brief. Use a new file name.')
    else:
        state = {'schema': STATE_SCHEMA, 'plan': name, 'mode': args.mode, 'round': args.round if args.mode == 'practice' else None,
                 'provider': PROVIDER, 'model': MODEL, 'seed': SEEDS[name], 'jobs_sha256': jobs_sha256(name),
                 'briefs_sha256': briefs_sha256(name), 'tool_sha256_at_start': this_tool, 'chunks': {}, 'log': []}
    calls_total = -(-len(job_list) // PER_CALL)

    def stop(status, code, **more):
        save(out, state)
        line = {'status': status, 'plan': name, 'chunks_done': len(state['chunks']), 'of': calls_total}
        line.update(more)
        print(json.dumps(line)[:1200])
        return code

    for start in range(0, len(job_list), PER_CALL):
        if str(start) in state['chunks']:
            continue
        chunk = job_list[start:start + PER_CALL]
        body = json.dumps({'model': MODEL, 'temperature': 1.0, 'max_tokens': 30000,
                           'messages': [{'role': 'user', 'content': brief_for(chunk)}]}).encode('utf-8')
        done, rate_limited = False, 0
        for attempt in (1, 2, 3):
            recent = recent_requests(ledger)
            if len(recent) >= args.daily_cap:
                next_slot = (recent[0] + datetime.timedelta(hours=24)).isoformat()
                return stop('STOPPED_DAILY_CAP', 0, reason='local count', requests_last_24h=len(recent), cap=args.daily_cap, next_slot_utc=next_slot)
            time.sleep(args.pace)
            ledger.setdefault('requests', []).append({'utc': now_utc().isoformat(), 'plan': name, 'start': start, 'attempt': attempt})
            save(ledger_path, ledger)
            wait = 5
            try:
                request = urllib.request.Request(URL, data=body, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
                with urllib.request.urlopen(request, timeout=300) as response:
                    data = json.loads(response.read())
                texts, order = read_items(data['choices'][0]['message']['content'], len(chunk))
                state['chunks'][str(start)] = [{'setting': s, 'kind': k, 'text': text} for (s, k), text in zip(chunk, texts)]
                state['log'].append({'utc': now_utc().isoformat(), 'start': start, 'attempt': attempt, 'ok': True, 'order': order, 'usage': data.get('usage')})
                done = True
            except Exception as error:
                detail, code = '', None
                if isinstance(error, urllib.error.HTTPError):
                    code = error.code
                    detail = error.read()[:6000].decode('utf-8', 'replace')
                shown = (type(error).__name__ + ': ' + str(error)[:120] + ' ' + detail[:400]).replace(key, '[KEY]')
                state['log'].append({'utc': now_utc().isoformat(), 'start': start, 'attempt': attempt, 'ok': False, 'http': code, 'error': shown})
                if code == 429:
                    rate_limited += 1
                    daily = re.search(r'per ?day|daily', detail, flags=re.I) is not None
                    if daily or rate_limited >= 2:
                        return stop('STOPPED_DAILY_CAP', 0, reason='the service said the quota is used up' if daily else 'the service refused two requests for this call (429)',
                                    requests_last_24h=len(recent) + 1, last_error=shown[:300])
                    wait = 65
                elif code == 503:
                    wait = 30
            save(out, state)
            if done:
                break
            time.sleep(wait)
        if not done:
            return stop('STOPPED_ERROR', 2, last_error=state['log'][-1].get('error', '')[:300])

    save(out, state)
    line = {'status': 'ALL_WRITTEN', 'plan': name}
    line.update(summary(state, job_list))
    print(json.dumps(line))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
