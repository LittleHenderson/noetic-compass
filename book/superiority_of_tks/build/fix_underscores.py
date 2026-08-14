# -*- coding: utf-8 -*-
"""Repair heredoc-mangled underscore patch, then apply the real one.

The earlier (mangled) patch replaced runs of PLAIN underscores — which only
exist inside Verbatim blocks — with escaped `\_` runs joined by \allowbreak{}.
Undo that inside Verbatim, then make long ESCAPED `\_` runs in prose breakable.
"""
from pathlib import Path
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92)
ALLOW = BS + 'allowbreak{}'
U = BS + '_'

src = Path('body.tex').read_text(encoding='utf-8')
lines = src.split('\n')
out = []
in_v = False
repaired = 0
for ln in lines:
    if BS + 'begin{Verbatim}' in ln:
        in_v = True
    if BS + 'end{Verbatim}' in ln:
        in_v = False
    if in_v and (ALLOW in ln or U in ln):
        # restore plain underscores: strip allowbreaks, unescape \_
        n_plain = ln.count(U) + 0
        ln2 = ln.replace(ALLOW, '').replace(U, '_')
        if ln2 != ln:
            repaired += 1
            ln = ln2
    out.append(ln)
src = '\n'.join(out)

# real prose patch: escaped \_ runs >= 8 -> breakable every 4
pat = re.compile('(?:' + re.escape(U) + '){8,}')

def breaker(m):
    n = len(m.group(0)) // 2
    chunks = [U * 4] * (n // 4)
    if n % 4:
        chunks.append(U * (n % 4))
    return ALLOW.join(chunks)

src, cnt = pat.subn(breaker, src)

# also give em-dashes explicit break rights in prose (XeLaTeX doesn't)
lines = src.split('\n')
out = []
in_v = False
dash = 0
for ln in lines:
    if BS + 'begin{Verbatim}' in ln:
        in_v = True
    if BS + 'end{Verbatim}' in ln:
        in_v = False
    if not in_v and '—' in ln and ALLOW not in ln and BS + 'section' not in ln \
            and BS + 'chapter' not in ln and BS + 'caption' not in ln:
        ln2 = ln.replace('—', '—' + ALLOW)
        if ln2 != ln:
            dash += 1
            ln = ln2
    out.append(ln)
src = '\n'.join(out)

Path('body.tex').write_text(src, encoding='utf-8')
print(f'verbatim lines repaired: {repaired}, underscore runs patched: {cnt}, dash lines: {dash}')
