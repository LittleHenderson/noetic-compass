"""Scan the team A labelers' transcripts for checker runs other than 'take', checker imports, and other files named.
Read-only. Prints one JSON line per chunk and writes the same to the output path given as argv[2]."""
import json
import os
import re
import sys

BS = chr(92)
BASE = ("C:/Users/wakil/.claude/projects/C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner-CASALESCENCE-NOETICS-v0-1/"
        "6fbc6595-1bf9-4970-9753-be964ad6ed9c/subagents/")
sessions_file, out_path = sys.argv[1], sys.argv[2]
ids = {}
practice = {}
for line in open(sessions_file, encoding='utf-8'):
    line = line.strip()
    m = re.match(r'^(\d\d)=(\w+)$', line)
    if m:
        ids[m.group(1)] = m.group(2)
    m = re.match(r'^Practice labeler: (\d\d)=(\w+)$', line)
    if m:
        practice['practice_' + m.group(1)] = m.group(2)

CHECK_MODE = re.compile(r'check_labels_v21\.py["\s]+check\b')
TAKE = re.compile(r'check_labels_v21\.py["\s]+take\b')
IMPORT = re.compile(r'(?:import\s+check_labels|from\s+check_labels|importlib.{0,120}check_labels|runpy.{0,120}check_labels|'
                    r'exec\(\s*open\(.{0,200}check_labels|spec_from_file_location.{0,200}check_labels)', re.S)
PATH = re.compile(r'(?:[A-Za-z]:[/' + re.escape(BS) + r']|/[a-z]/|/tmp/)[^"\s\'<>|;,)]+')


def scan(ch, aid, verdict):
    f = BASE + 'agent-' + aid + '.jsonl'
    if not os.path.exists(f):
        return {'chunk': ch, 'agent': aid, 'error': 'transcript missing'}
    calls = []
    for line in open(f, encoding='utf-8'):
        try:
            d = json.loads(line)
        except Exception:
            continue
        c = (d.get('message') or {}).get('content')
        if not isinstance(c, list):
            continue
        for b in c:
            if isinstance(b, dict) and b.get('type') == 'tool_use':
                calls.append((b.get('name'), b.get('input', {})))
    names, check_mode, imports, takes, paths = {}, 0, 0, 0, set()
    for name, inp in calls:
        names[name] = names.get(name, 0) + 1
        texts = [v for v in inp.values() if isinstance(v, str)]
        for s in texts:
            check_mode += len(CHECK_MODE.findall(s))
            imports += len(IMPORT.findall(s))
            takes += len(TAKE.findall(s))
            for p in PATH.findall(s):
                paths.add(p.replace(BS, '/'))
    folder = 'label_v21/verdict/' if verdict else 'label_v21/practice/'
    own = ('team_a/chunk_' + ch + '.json', 'labels_team_a.json.chunk_' + ch + '.')
    other = sorted(p for p in paths
                   if not any(o in p for o in own) and 'tools/check_labels_v21.py' not in p
                   and not p.rstrip('/').endswith('CASALESCENCE_NOETICS_v0_1') and not p.rstrip('/').endswith(folder.rstrip('/')))
    return {'chunk': ch, 'agent': aid, 'tool_calls': names, 'check_mode_runs': check_mode, 'checker_imports': imports,
            'take_runs': takes, 'other_paths_named': other}


rows = [scan(ch, aid, True) for ch, aid in sorted(ids.items())]
rows += [scan(k.split('_')[1], aid, False) | {'set': 'practice'} for k, aid in practice.items()]
with open(out_path, 'w', encoding='utf-8', newline='\n') as fh:
    for r in rows:
        fh.write(json.dumps(r, ensure_ascii=False) + '\n')
for r in rows:
    print(json.dumps(r, ensure_ascii=False))
