import json, sys, re
f = sys.argv[1]; t0 = sys.argv[2]; t1 = sys.argv[3]
pat = re.compile(sys.argv[4], re.I) if len(sys.argv) > 4 else None
with open(f, encoding='utf-8', errors='replace') as fh:
    for ln, line in enumerate(fh, 1):
        try: o = json.loads(line)
        except Exception: continue
        if o.get('type') != 'user': continue
        ts = o.get('timestamp') or ''
        if not (t0 <= ts <= t1): continue
        c = o.get('message', {}).get('content')
        texts = []
        if isinstance(c, str): texts.append(c)
        elif isinstance(c, list):
            for p in c:
                if isinstance(p, dict) and p.get('type') == 'text': texts.append(p.get('text', ''))
        for t in texts:
            s = t.strip()
            if s.startswith('<system-reminder>') or s.startswith('<command') or s.startswith('# Workflow'): continue
            if pat and not pat.search(s): continue
            print('==', ln, ts, 'len', len(s))
            print(s[:2500].replace('\n', ' | '))
