import json, sys, hashlib
p = sys.argv[1]
raw = open(p, 'rb').read()
print('sha256', hashlib.sha256(raw).hexdigest(), 'bytes', len(raw))
d = json.loads(raw)
print('top keys', list(d)[:40])
print('label', d.get('label'), d.get('rule'), d.get('label_rule'))
def walk(o, path=''):
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ('G_LEARN_population',) :
                print(path + '/' + k, json.dumps({kk: vv for kk, vv in v.items() if kk != 'keys'} if isinstance(v, dict) else v)[:900])
            walk(v, path + '/' + k)
    elif isinstance(o, list):
        for i, v in enumerate(o[:10]):
            walk(v, path + '[%d]' % i)
walk(d)
