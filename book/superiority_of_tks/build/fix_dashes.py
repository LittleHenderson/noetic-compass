# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92)
ALLOW = BS + 'allowbreak{}'

src = Path('body.tex').read_text(encoding='utf-8')
i = src.find('repeated experiences')
print('context:', repr(src[i - 80:i + 60]))
print('em-dash U+2014 count in file:', src.count('—'))
print('en-dash U+2013 count in file:', src.count('–'))
print('TeX --- count:', src.count('---'))

# patch: make --- and -- breakable in prose lines (skip Verbatim)
lines = src.split('\n')
out = []
in_v = False
n = 0
for ln in lines:
    if BS + 'begin{Verbatim}' in ln:
        in_v = True
    if BS + 'end{Verbatim}' in ln:
        in_v = False
    if not in_v and '---' in ln and BS + 'section' not in ln and BS + 'chapter' not in ln:
        ln2 = ln.replace('---', '---' + ALLOW)
        if ln2 != ln:
            n += 1
            ln = ln2
    out.append(ln)
Path('body.tex').write_text('\n'.join(out), encoding='utf-8')
print('dash lines patched:', n)
