"""Print the Grep / Glob / PowerShell calls of the named labelers, and any Bash or Read call that names a path in the
filter list. Read-only."""
import json
import sys

BASE = ("C:/Users/wakil/.claude/projects/C--Users-wakil-OneDrive-Desktop-tksCAS-cas-only-reasoner-CASALESCENCE-NOETICS-v0-1/"
        "6fbc6595-1bf9-4970-9753-be964ad6ed9c/subagents/")
agents = sys.argv[1].split(',')
needles = sys.argv[2].split('|') if len(sys.argv) > 2 else []
for aid in agents:
    for line in open(BASE + 'agent-' + aid + '.jsonl', encoding='utf-8'):
        try:
            d = json.loads(line)
        except Exception:
            continue
        c = (d.get('message') or {}).get('content')
        if not isinstance(c, list):
            continue
        for b in c:
            if not (isinstance(b, dict) and b.get('type') == 'tool_use'):
                continue
            name, inp = b.get('name'), b.get('input', {})
            s = json.dumps({k: v for k, v in inp.items() if k != 'content'}, ensure_ascii=False)
            if name in ('Grep', 'Glob', 'PowerShell') or any(n and n in s for n in needles):
                print(aid[:6], name, s[:500])
