"""Blind passage writer for label-agreement attempt 2, version 2.1 (plan: 09_LABEL_AGREEMENT_PLAN_v2_1.md).

A thin variant of tools/write_verdict_passages.py (attempt 1). The same writer model, the same brief, the
same nine kinds K1 to K9, the same forbidden words, 30 passages per call. Only the settings are new: none
was used in any earlier round. The writer never sees the guide, the definitions, a label or a reader.
The label teams are never told the kind of a passage.

Modes
  practice   30 passages: 10 settings, three each; 3 or 4 per kind. For the tool check only.
  verdict    440 passages: 40 settings, eleven each; the count per kind of attempt 1.

Usage
  write_passages_v21.py <practice|verdict> <state.json> [--pace SECONDS] [--daily-cap N] [--ledger PATH]
  write_passages_v21.py <practice|verdict> --dry-run [--show-brief] [--check-earlier]

Key: GEMINI_API_KEY from the environment; if it is not set there, from ~/.cas_llm_keys.env, read at run
time. The key is never printed and never stored. Error text is scrubbed before it is logged.
Checkpoint and resume: the state file is saved after every call (a .partial file, then a rename). Run the
same command again and it goes on where it stopped. It refuses a state file made from another job list.
Clean stop: the free tier allows about 20 requests a day. Every request is written with its time to a small
ledger (no key, no passage text). At --daily-cap requests in 24 hours (default 18) the tool saves and
stops: STOPPED_DAILY_CAP, exit code 0. On HTTP 429 it also saves and stops with exit code 0: at once when
the service says the daily quota is used up, otherwise after one more try 65 seconds later.

The state file stores, for every call, the model name the service put in its reply.
Exit codes: 0 all written, or a clean stop. 1 refused to start. 2 stopped on errors. --dry-run sends nothing
and needs no key; with --check-earlier it reads the earlier tools and passage files and confirms that the
list EARLIER below is every setting they hold.
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

PROVIDER, MODEL, KEY_NAME = 'gemini', 'gemini-2.5-flash', 'GEMINI_API_KEY'
URL = 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions'
STATE_SCHEMA = 'casalescence/label-agreement-v21-writer-state/1'
PER_CALL, DEFAULT_DAILY_CAP = 30, 18
HERE = Path(__file__).resolve().parent

# The same twelve words as attempt 1.
FORBIDDEN = ['cause', 'effect', 'trigger', 'positive', 'negative', 'vibration', 'rhythm', 'idea', 'mind', 'noetic', 'resonate', 'resonance']

# 50 plain workplaces and places, new in this version: 40 for the verdict set, 10 for the practice check.
SETTINGS = {
    'verdict': [
        'a shipyard', 'a garden centre', 'a hat maker\'s workshop', 'a violin maker\'s workshop', 'a bookbinder\'s workshop',
        'a clock repair shop', 'an olive press', 'a salt works', 'a rope factory', 'a tannery', 'a carpet showroom',
        'a second-hand bookshop', 'a newsagent\'s shop', 'a funicular railway', 'a telephone exchange', 'a town hall archive',
        'a village hall', 'a bell foundry', 'a stonemason\'s yard', 'a seaside pier', 'a fairground', 'a concert hall cloakroom',
        'a wallpaper shop', 'a boarding kennel', 'an aquarium', 'a botanical garden', 'a golf course', 'a rowing club',
        'an athletics track', 'a roadside diner', 'an ice cream parlour', 'a recycling centre', 'a tyre fitting bay',
        'a trout hatchery', 'a lifeboat station', 'a hot-air balloon field', 'an orchard at picking time', 'a costume hire shop',
        'a pet shop', 'a potato packing shed'],
    'practice': ['a button factory', 'a sign painter\'s shed', 'a skate park', 'a spice shop', 'a marina', 'an allotment',
                 'a model aeroplane club', 'a sauna', 'a grain silo', 'a pawnshop'],
}
PER_SETTING = {'verdict': 11, 'practice': 3}
SEEDS = {'verdict': 20261021, 'practice': 20261022}

# Every setting of every earlier round: the first look, practice rounds 2 and 3, the first verdict set, and
# the version 2.0 lists (written into a tool, never used). 112 settings. No new setting may be one of them.
EARLIER = (
    'a family home on a weekend; a hospital ward; a long train journey; a rehearsal room for musicians; a '
    "restaurant kitchen; a secondary school; a small farm; a small repair garage; a software team's office; a "
    'street market; a fishing boat; a public library; a construction site; a bakery before dawn; a call centre; a '
    'veterinary clinic; a village bus route; a pottery studio; a laundromat; an airport gate; a lighthouse; a '
    'dental surgery; a night bus depot; a flower stall; a boxing gym; a recording studio; a mountain hut; a post '
    "office sorting room; a hotel laundry; a vineyard at harvest; a tailor's shop; a river ferry; a university "
    'laboratory; a care home; a bicycle workshop; a fish market; a courtroom corridor; a radio newsroom; a '
    "greenhouse; a quarry; a school canteen; a locksmith's van; a harbour crane cabin; a puppet theatre; a cheese "
    'cellar; a customs desk; a chess club; a wind farm control room; a barber shop; a dairy at milking time; a '
    'museum storeroom; a taxi rank at night; a scrapyard; a nursery school; a ski lift station; a print shop; a '
    "beekeeper's yard; a swimming pool; a shoe repair kiosk; a warehouse loading bay; a hardware store; a car "
    "wash; a pharmacy counter; a bowling alley; a paint factory; a sawmill; a blacksmith's forge; a glassblowing "
    'workshop; an upholstery workshop; a candle workshop; a campsite; a registry office; a cinema projection '
    "booth; a zoo's reptile house; an ice rink; a fire station; a lost property office; a railway signal box; a "
    "canal lock; a petrol station; a supermarket checkout; a butcher's shop; a coffee roastery; a brewery; a "
    'flour mill; a mushroom farm; an archaeology dig; a horse stable; a driving school car; a planetarium; a '
    "weather station; a bottling plant; a motorway service station; an optician's shop; a blood donation centre; "
    "a bank branch; a toy shop; a climbing wall; a jeweller's workshop; a brickworks; a chocolate factory; a "
    'furniture removal van; an auction house; a tennis club; a water treatment plant; a tea room; a paper mill; a '
    'picture framing shop; a snooker hall; a soap workshop; a dance school; a youth hostel').split('; ')

# What the writer is told about each kind of moment: the strings of attempt 1, character for character.
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
COUNTS = {
    'verdict': {'K1': 60, 'K2': 60, 'K3': 60, 'K4': 60, 'K5': 60, 'K6': 30, 'K7': 30, 'K8': 60, 'K9': 20},   # attempt 1
    'practice': {'K1': 4, 'K2': 4, 'K3': 3, 'K4': 4, 'K5': 3, 'K6': 3, 'K7': 3, 'K8': 3, 'K9': 3},
}
TOTALS = {'verdict': 440, 'practice': 30}

# The brief of attempt 1, character for character.
BRIEF = ('Write %d short everyday passages in plain English. Each passage is 3 to 5 sentences, 45 to 90 words, third person, '
         'past tense, about ordinary people with ordinary first names (use many different names, ages and jobs; never reuse a name '
         'within this list). No lists, no headings, no moral, no summary sentence, no stock phrases or proverbs. Do not explain what '
         'a passage is about. Make the passages clearly different from each other in wording and in what happens. '
         'Never use these words: %s.\n\n'
         'Write the passages in this order. For each one I give the setting and the kind of moment; never name the kind in the text:\n%s\n\n'
         'Reply with ONE JSON array and nothing else: [{"n": 1, "text": "..."}, ...] with exactly %d objects in the order given.')

# sha256 of the strings in tools/write_verdict_passages.py (attempt 1), taken on 2026-10-05.
ATTEMPT_1_SHA256 = {
    'BRIEF': '9c2e2a16b1ab9a56bb83b0050b3e4a9562db96d2a596b1ee7a189dfaa07ac3db',
    'FORBIDDEN': '77fe649bf045ff861f833186894aa1312e65d8150f9f79ec8f6b7cd0f3b6886e',
    'K1': 'b1c4a5371f676371620a60ca275ffc8eb3ad227cf367f32853031dd42b6ba386', 'K2': '76e286afafcec6ecd45542a007407a5092863eb6751994b69a79b6259dce9e2d',
    'K3': 'a5dffda3c089548dc162f88138047f4b2d697d31630dd245076494c38d30216d', 'K4': '116a820d627285811f65fedc06ca319acb3761998ffcf80b68576c22144ce185',
    'K5': '4ba0a0b429db31fd4b9c86d2e381acbcacdb68703ac9a9f9f73e9851452bec0d', 'K6': '9596b885dff0646291e1cbad4f0f779edd46052864f87ee853437716b1996341',
    'K7': '8d489e67d929337c890b8693925812b7e682b856d225191a1a72ce6adea9d726', 'K8': 'b80bae9a4471014be1730e2177ad9454591745e4c7d09f4821d97c3f49e8201a',
    'K9': '97a50b68e8e111dfdd8ac51d757b8e5f7be7e5e3c2b50380b4d6c4566d9e7d51',
}
# sha256 of each fixed job list (setting and kind of every passage, in order). The plan prints the same values.
EXPECTED_JOBS_SHA256 = {'verdict': 'b72264e963574e6b58930344ec0baf476b2a5a480e7a5b7532e033188b5c7efb',
                        'practice': '29e3075b9ed9b53e7fa94eece0a12bf12b3cfc098d5849dcd91bf3854fb88d2c'}


def sha_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def bare(setting):
    """A setting without its article, in small letters, for comparing two lists."""
    return re.sub(r'^(a|an|the)\s+', '', setting.strip().lower())


def jobs(name):
    """The fixed, seeded job list: one (setting, kind) per passage, kinds mixed, the same count per setting."""
    rng = random.Random(SEEDS[name])
    kinds = [kind for kind, count in COUNTS[name].items() for _ in range(count)]
    rng.shuffle(kinds)
    settings = [setting for setting in SETTINGS[name] for _ in range(PER_SETTING[name])]
    rng.shuffle(settings)
    return list(zip(settings, kinds))


def jobs_sha256(name):
    return sha_text(json.dumps(jobs(name), ensure_ascii=False))


def briefs_sha256(name):
    """One hash over everything that decides what the writer is asked."""
    record = {'provider': PROVIDER, 'model': MODEL, 'brief': BRIEF, 'forbidden': FORBIDDEN, 'kinds': KINDS, 'counts': COUNTS[name],
              'settings': SETTINGS[name], 'per_setting': PER_SETTING[name], 'per_call': PER_CALL, 'seed': SEEDS[name], 'temperature': 1.0}
    return sha_text(json.dumps(record, ensure_ascii=False, sort_keys=True))


def self_check():
    """Refuse to run if a constant no longer says what the plan says."""
    problems = []
    if sha_text(BRIEF) != ATTEMPT_1_SHA256['BRIEF']:
        problems.append('BRIEF differs from attempt 1')
    if sha_text(json.dumps(FORBIDDEN)) != ATTEMPT_1_SHA256['FORBIDDEN']:
        problems.append('FORBIDDEN differs from attempt 1')
    problems += [kind + ' differs from attempt 1' for kind in KINDS if sha_text(KINDS[kind]) != ATTEMPT_1_SHA256[kind]]
    every = SETTINGS['verdict'] + SETTINGS['practice']
    if len({bare(s) for s in every}) != len(every) or [len(SETTINGS[n]) for n in ('verdict', 'practice')] != [40, 10]:
        problems.append('settings: need 40 + 10, all different')
    reused = sorted({bare(s) for s in every} & {bare(s) for s in EARLIER})
    if reused or len(EARLIER) != 112:
        problems.append('a setting was used in an earlier round: %s' % ', '.join(reused))
    for name in ('verdict', 'practice'):
        if sum(COUNTS[name].values()) != TOTALS[name] or len(SETTINGS[name]) * PER_SETTING[name] != TOTALS[name]:
            problems.append(name + ': the counts do not add up to %d' % TOTALS[name])
        if list(COUNTS[name]) != list(KINDS) or jobs_sha256(name) != EXPECTED_JOBS_SHA256[name]:
            problems.append(name + ': the kinds or the job list are not the ones in the plan')
    for word in FORBIDDEN:
        if any(re.search(r'\b' + word + r'\w*\b', text, flags=re.I) for text in list(KINDS.values()) + every):
            problems.append('a kind brief or a setting holds the forbidden word ' + word)
    if problems:
        raise SystemExit('REFUSED: ' + '; '.join(problems))


def earlier_from_files():
    """Read every earlier settings list from the earlier tools and passage files. Returns (settings, files missing)."""
    root, found, missing = HERE.parent, [], []

    def literal(path, name):
        for node in ast.parse(path.read_text(encoding='utf-8')).body:
            if isinstance(node, ast.Assign) and getattr(node.targets[0], 'id', None) == name:
                return ast.literal_eval(node.value)
        raise ValueError('no ' + name)

    for tool in ('write_verdict_passages.py', 'write_passages_outside.py', 'write_passages_v2.py'):
        try:
            value = literal(HERE / tool, 'SETTINGS')
            found += [s for group in (value.values() if isinstance(value, dict) else [value]) for s in group]
        except (OSError, ValueError, SyntaxError):
            missing.append('tools/' + tool)
    for folder in ('first_look', 'practice_round2', 'practice_round3', 'verdict'):
        for path in sorted((root / folder).glob('*.json')) if (root / folder).is_dir() else []:
            try:
                rows = json.loads(path.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                continue
            found += [row['setting'] for row in rows if isinstance(row, dict) and isinstance(row.get('setting'), str)] if isinstance(rows, list) else []
    return found, missing


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


def read_key():
    """The key, from the environment or from the key file, at run time. Never printed, never stored."""
    key = os.environ.get(KEY_NAME, '').strip()
    path = Path.home() / '.cas_llm_keys.env'
    if not key and path.is_file():
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.strip().startswith(KEY_NAME + '='):
                key = line.split('=', 1)[1].strip().strip('"').strip("'")
    if not key:
        raise SystemExit('REFUSED: %s is not in the environment and not in ~/.cas_llm_keys.env' % KEY_NAME)
    return key


def recent_requests(ledger, hours=24):
    """Times of the requests sent in the last `hours` hours."""
    edge, times = now_utc() - datetime.timedelta(hours=hours), []
    for row in ledger.get('requests', []):
        try:
            when = datetime.datetime.fromisoformat(row['utc'])
        except (KeyError, TypeError, ValueError):
            continue
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
    return [item['text'].strip() for item in items]


def summary(state, job_list):
    rows = [row for start in sorted(state['chunks'], key=int) for row in state['chunks'][start]]
    hits = sum(1 for row in rows for word in FORBIDDEN if re.search(r'\b' + word + r'\w*\b', row['text'], flags=re.I))
    lengths = [len(row['text'].split()) for row in rows] or [0]
    models = sorted({str(row.get('reply_model')) for row in state['log'] if row.get('ok')})
    return {'passages': len(rows), 'of': len(job_list), 'forbidden_word_hits': hits,
            'words_min_max': [min(lengths), max(lengths)], 'models_that_answered': models}


def dry_run(name, show_brief, check_earlier):
    job_list, by_kind = jobs(name), {}
    for _, kind in job_list:
        by_kind[kind] = by_kind.get(kind, 0) + 1
    line = {'status': 'DRY_RUN_NOTHING_SENT', 'plan': name, 'writer': PROVIDER + ' ' + MODEL, 'passages': len(job_list),
            'calls': -(-len(job_list) // PER_CALL), 'by_kind': by_kind, 'settings': len(SETTINGS[name]),
            'per_setting': PER_SETTING[name], 'seed': SEEDS[name], 'jobs_sha256': jobs_sha256(name), 'briefs_sha256': briefs_sha256(name)}
    if check_earlier:
        found, missing = earlier_from_files()
        line['earlier_check'] = {'settings_found_in_files': len({bare(s) for s in found}), 'settings_in_EARLIER': len(EARLIER),
                                 'in_files_but_not_in_EARLIER': sorted({bare(s) for s in found} - {bare(s) for s in EARLIER}),
                                 'new_settings_found_in_files': sorted({bare(s) for s in SETTINGS['verdict'] + SETTINGS['practice']} & {bare(s) for s in found}),
                                 'files_not_read': missing}
    print(json.dumps(line, indent=1))
    if show_brief:
        print(brief_for(job_list[:PER_CALL]))


def main(argv):
    parser = argparse.ArgumentParser(description='Blind passage writer for label-agreement attempt 2, version 2.1.')
    parser.add_argument('mode', choices=['practice', 'verdict'])
    parser.add_argument('state', nargs='?', help='state file; saved after every call')
    parser.add_argument('--pace', type=float, default=20.0, help='seconds to wait before each request')
    parser.add_argument('--daily-cap', type=int, default=DEFAULT_DAILY_CAP, help='most requests in any 24 hours')
    parser.add_argument('--ledger', help='request ledger file; default label_v21/writer_request_ledger.json')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--show-brief', action='store_true')
    parser.add_argument('--check-earlier', action='store_true')
    args = parser.parse_args(argv)

    self_check()
    name = args.mode
    if args.dry_run:
        dry_run(name, args.show_brief, args.check_earlier)
        return 0
    if not args.state:
        raise SystemExit('REFUSED: name a state file')
    key = read_key()
    job_list, out = jobs(name), Path(args.state)
    ledger_path = Path(args.ledger) if args.ledger else HERE.parent / 'label_v21' / 'writer_request_ledger.json'
    ledger = json.loads(ledger_path.read_text(encoding='utf-8')) if ledger_path.exists() else {'what': 'time of every request to the writer', 'requests': []}
    if out.exists():
        state = json.loads(out.read_text(encoding='utf-8'))
        if state.get('plan') != name or state.get('jobs_sha256') != jobs_sha256(name) or state.get('briefs_sha256') != briefs_sha256(name):
            raise SystemExit('REFUSED: this state file was made from another job list or another brief. Use a new file name.')
    else:
        state = {'schema': STATE_SCHEMA, 'plan': name, 'provider': PROVIDER, 'model': MODEL, 'seed': SEEDS[name],
                 'jobs_sha256': jobs_sha256(name), 'briefs_sha256': briefs_sha256(name),
                 'tool_sha256_at_start': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'chunks': {}, 'log': []}
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
                return stop('STOPPED_DAILY_CAP', 0, reason='local count', requests_last_24h=len(recent), cap=args.daily_cap,
                            next_slot_utc=(recent[0] + datetime.timedelta(hours=24)).isoformat())
            time.sleep(args.pace)
            ledger.setdefault('requests', []).append({'utc': now_utc().isoformat(), 'plan': name, 'start': start, 'attempt': attempt})
            save(ledger_path, ledger)
            wait = 5
            try:
                request = urllib.request.Request(URL, data=body, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
                with urllib.request.urlopen(request, timeout=300) as response:
                    data = json.loads(response.read())
                texts = read_items(data['choices'][0]['message']['content'], len(chunk))
                state['chunks'][str(start)] = [{'setting': s, 'kind': k, 'text': text} for (s, k), text in zip(chunk, texts)]
                state['log'].append({'utc': now_utc().isoformat(), 'start': start, 'attempt': attempt, 'ok': True,
                                     'reply_model': data.get('model'), 'usage': data.get('usage')})
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
                        return stop('STOPPED_HTTP_429', 0, reason='the service said the daily quota is used up' if daily else 'two 429 answers for this call',
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
