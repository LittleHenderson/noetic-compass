"""Transcript check for team A of attempt 3 (plan 09_LABEL_AGREEMENT_PLAN_v2_2.md, section 10). Read-only.

For each labeler: every tool call by name; runs of the checker's `check` mode; imports of the checker; every file path the
labeler's tool calls name; and the paths outside what it may touch (its prompt file, its chunk file, its working file, its
own chunk labels file and try log, the checker it hands in with, and files it created itself in the session scratch folder).

Usage: scan_team_a_v22.py <set folder> <L> <out.jsonl> NN=AGENT_ID [NN=AGENT_ID ...]
"""
import json
import re
import sys
from pathlib import Path

BS = chr(92)
SESSION = Path('C:/Users/wakil/.claude/projects/C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner-CASALESCENCE-NOETICS-v0-1/'
               '6fbc6595-1bf9-4970-9753-be964ad6ed9c')
SCRATCH = ('C:/Users/wakil/AppData/Local/Temp/claude/C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner-CASALESCENCE-NOETICS-v0-1/'
           '6fbc6595-1bf9-4970-9753-be964ad6ed9c/scratchpad')
CHECK_MODE = re.compile(r'check_labels_v2\d\.py["\s]+check\b')
TAKE = re.compile(r'check_labels_v2\d\.py["\s]+take\b')
IMPORT = re.compile(r'(?:import\s+check_labels|from\s+check_labels|importlib.{0,120}check_labels|runpy.{0,120}check_labels|'
                    r'exec\(\s*open\(.{0,200}check_labels|spec_from_file_location.{0,200}check_labels)', re.S)
PATH = re.compile(r'(?:[A-Za-z]:[/' + re.escape(BS) + r']|/[a-z]/|/tmp/)[^"\s\'<>|;,)]+')


def norm(p):
    p = p.replace(BS, '/').rstrip('/.')
    m = re.match(r'^/([a-z])/(.*)$', p)
    return (m.group(1).upper() + ':/' + m.group(2)) if m else p


def scan(set_folder, labels, chunk, agent):
    f = SESSION / 'subagents' / ('agent-%s.jsonl' % agent)
    if not f.is_file():
        return {'chunk': chunk, 'agent': agent, 'error': 'transcript missing'}
    study = norm(str(Path(set_folder).resolve().parent.parent))
    base = norm(str(Path(set_folder).resolve()))
    allowed = {base + '/' + Path(labels).name + '.chunk_%s.prompt.txt' % chunk, base + '/team_a/chunk_%s.json' % chunk,
               base + '/' + Path(labels).name + '.chunk_%s.work.json' % chunk, base + '/' + Path(labels).name + '.chunk_%s.json' % chunk,
               base + '/' + Path(labels).name + '.chunk_%s.json.tries.jsonl' % chunk, study + '/tools/check_labels_v21.py'}
    folders_ok = {base, base + '/team_a', study, study + '/tools', norm(SCRATCH)}
    names, check_mode, imports, takes, paths, created = {}, 0, 0, 0, set(), set()
    for line in open(f, encoding='utf-8'):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        content = (d.get('message') or {}).get('content')
        if not isinstance(content, list):
            continue
        for b in content:
            if not (isinstance(b, dict) and b.get('type') == 'tool_use'):
                continue
            name, inp = b.get('name'), b.get('input', {})
            names[name] = names.get(name, 0) + 1
            if name in ('Write', 'Edit') and isinstance(inp.get('file_path'), str) and norm(inp['file_path']).startswith(norm(SCRATCH)):
                created.add(norm(inp['file_path']))
            for s in (v for v in inp.values() if isinstance(v, str)):
                check_mode += len(CHECK_MODE.findall(s))
                imports += len(IMPORT.findall(s))
                takes += len(TAKE.findall(s))
                paths.update(norm(p) for p in PATH.findall(s))
    outside = sorted(p for p in paths if p not in allowed and p not in folders_ok and p not in created
                     and not any(p.startswith(c) for c in created))
    return {'chunk': chunk, 'agent': agent, 'tool_calls': names, 'check_mode_runs': check_mode, 'checker_imports': imports,
            'take_runs': takes, 'scratch_files_created': sorted(created), 'paths_outside_allowed': outside}


def main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 2
    set_folder, labels, out = argv[0], argv[1], argv[2]
    rows = []
    for spec in argv[3:]:
        chunk, agent = spec.split('=', 1)
        rows.append(scan(set_folder, labels, chunk, agent))
    with open(out, 'w', encoding='utf-8', newline='\n') as stream:
        for r in rows:
            stream.write(json.dumps(r, ensure_ascii=False) + '\n')
    for r in rows:
        print(json.dumps(r, ensure_ascii=False))
    bad = [r for r in rows if r.get('error') or r.get('check_mode_runs') or r.get('checker_imports') or r.get('paths_outside_allowed')]
    print('labelers checked: %d; with a finding: %d' % (len(rows), len(bad)))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
