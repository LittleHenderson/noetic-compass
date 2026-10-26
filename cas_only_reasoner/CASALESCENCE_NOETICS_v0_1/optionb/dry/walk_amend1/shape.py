"""[MADE-UP DATA WALK] Print the shape of JSON / JSONL files: key names and value types, one level per line. Reads only files under walk_amend1."""
import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
def kind(v):
    if isinstance(v, bool): return 'bool'
    if v is None: return 'null'
    if isinstance(v, int): return 'int'
    if isinstance(v, float): return 'FLOAT'
    if isinstance(v, str): return 'str'
    if isinstance(v, list): return 'list[%d]' % len(v)
    return 'obj'
def show(v, pre, depth, out, limit=3):
    if isinstance(v, dict):
        keys = list(v)
        many = len(keys) > 14 and len({kind(x) for x in v.values()}) == 1
        for k in (keys[:2] if many else keys):
            out.append('%s%s: %s' % (pre, k, kind(v[k])))
            if depth < limit: show(v[k], pre + '  ', depth + 1, out, limit)
        if many: out.append('%s... (%d keys of the same kind)' % (pre, len(keys)))
    elif isinstance(v, list) and v:
        kinds = sorted({kind(x) for x in v})
        if isinstance(v[0], (dict, list)):
            out.append('%s[0] of %d (%s):' % (pre, len(v), ','.join(kinds)))
            if depth < limit: show(v[0], pre + '  ', depth + 1, out, limit)
def bytes_ok(path):
    data = Path(path).read_bytes()
    return 'LF only' if b'\r' not in data else 'HAS CR', 'no BOM' if not data.startswith(b'\xef\xbb\xbf') else 'HAS BOM', 'ends with LF' if data.endswith(b'\n') else 'NO LF AT END'
for name in sys.argv[1:]:
    limit = 3
    if name.startswith('-d'):
        continue
    p = Path(name); out = []
    print('=====', name, p.stat().st_size, 'bytes;', '; '.join(bytes_ok(p)))
    if name.endswith('.jsonl'):
        rows = [json.loads(l) for l in p.read_text(encoding='utf-8').split('\n') if l.strip()]
        print('  %d lines; keys of line 1: %s' % (len(rows), [(k, kind(v)) for k, v in rows[0].items()] if rows else None))
        same = all(list(r) == list(rows[0]) for r in rows)
        print('  every line has the same keys in the same order:', same)
    else:
        doc = json.loads(p.read_text(encoding='utf-8'))
        show(doc, '  ', 0, out, limit)
        print('\n'.join(out))
