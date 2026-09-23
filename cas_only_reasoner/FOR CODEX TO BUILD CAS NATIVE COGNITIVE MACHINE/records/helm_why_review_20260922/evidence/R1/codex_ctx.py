import json, sys
f = sys.argv[1]
lines = open(f, encoding='utf-8', errors='replace').read().splitlines()
hit = None
for i, line in enumerate(lines):
    if 'COMPLETE AND TOTAL AUTHORIZATION' in line:
        try:
            o = json.loads(line)
        except Exception:
            continue
        p = o.get('payload', {})
        if p.get('type') == 'message' and p.get('role') == 'user':
            hit = i; break
print('hit line', hit)
if hit is None: sys.exit()
# print previous assistant messages (last 2) before the hit
shown = 0
for j in range(hit - 1, max(0, hit - 400), -1):
    try: o = json.loads(lines[j])
    except Exception: continue
    p = o.get('payload', {})
    if p.get('type') == 'message' and p.get('role') == 'assistant':
        texts = [c.get('text', '') for c in p.get('content', []) if isinstance(c, dict)]
        t = ' '.join(texts)
        print('--- assistant line', j, o.get('timestamp'))
        print(t[:3000])
        shown += 1
        if shown >= 1: break
o = json.loads(lines[hit]); p = o['payload']
print('--- user line', hit, o.get('timestamp'))
print(' '.join(c.get('text', '') for c in p.get('content', []) if isinstance(c, dict))[:800])
