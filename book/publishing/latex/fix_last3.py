# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
p = Path('body.tex')
lines = p.read_text(encoding='utf-8').split('\n')
n = 0
out = []
for ln in lines:
    s = ln.rstrip()
    # EBNF let_stmt line (straight quotes)
    if s.startswith('<let_stmt>') and '"=" <expression> ;' in s:
        s = s.replace(' "=" <expression> ;', '\n                       "=" <expression> ;')
        n += 1
    # long test-reference continuations: split token paths
    elif s.strip().startswith('//') and len(s) > 78:
        if '.rs::' in s:
            head, tail = s.split('.rs::', 1)
            s = head + '.rs::' + '\n        //       ' + tail
            n += 1
        elif 'via ' in s:
            head, tail = s.split('via ', 1)
            s = head + 'via' + '\n        //       ' + tail
            n += 1
    # p764: split at em dash
    elif 'Domain, not a Drive' in s and len(s) > 60:
        s = s.replace(' — same (P is a Domain, not a Drive)',
                      '\n                                       // — same (P is a Domain, not a Drive)')
        n += 1
    out.append(s)
p.write_text('\n'.join(out), encoding='utf-8')
print('split:', n)
