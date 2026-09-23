import json, sys, re, glob, os
pat = re.compile(r'\bhelm\b', re.I)
files = sys.argv[1:]
for f in files:
    with open(f, encoding='utf-8', errors='replace') as fh:
        for ln, line in enumerate(fh, 1):
            try:
                o = json.loads(line)
            except Exception:
                continue
            if o.get('type') != 'user':
                continue
            msg = o.get('message', {})
            c = msg.get('content')
            texts = []
            if isinstance(c, str):
                texts.append(c)
            elif isinstance(c, list):
                for p in c:
                    if isinstance(p, dict) and p.get('type') == 'text':
                        texts.append(p.get('text', ''))
            for t in texts:
                if pat.search(t) or re.search(r'\bname (it|the brain)|call it\b', t, re.I):
                    if t.startswith('<') and 'system-reminder' in t[:40]:
                        continue
                    print('==', os.path.basename(f), ln, o.get('timestamp'))
                    print(t[:1500].replace('\n', ' | '))
