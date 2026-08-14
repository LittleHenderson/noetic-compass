# -*- coding: utf-8 -*-
"""Wrap overflowing display-math blocks in resizebox; fix wide tikz label."""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92)
src = Path('body.tex').read_text(encoding='utf-8')

# show env around line 26425 (language_conformance)
lines = src.split('\n')
i = next((k for k, l in enumerate(lines) if 'set_theory_meta_logic' in l), None)
if i is not None:
    for j in range(max(0, i - 12), min(len(lines), i + 3)):
        mark = '>' if j == i else ' '
        print(f'{mark}{j+1}: {lines[j][:100]}')

# anchors that identify display blocks to shrink
ANCHORS = ['Sarah', 'Meridian', 'Knowing', 'per second', 'substrate',
           'together', '÷', 'authority']
OPEN, CLOSE = BS + '[', BS + ']'
n = 0
pos = 0
out = []
while True:
    a = src.find(OPEN, pos)
    if a == -1:
        out.append(src[pos:])
        break
    b = src.find(CLOSE, a)
    if b == -1:
        out.append(src[pos:])
        break
    content = src[a + 2:b]
    hit = any(x in content for x in ANCHORS)
    long_enough = len(content.replace('\n', ' ')) > 90
    out.append(src[pos:a])
    if hit and long_enough and 'resizebox' not in content:
        out.append(OPEN + BS + 'resizebox{' + BS + 'linewidth}{!}{$'
                   + BS + 'displaystyle ' + content + '$}' + CLOSE)
        n += 1
    else:
        out.append(src[a:b + 2])
    pos = b + 2
src = ''.join(out)
print('display blocks wrapped:', n)

Path('body.tex').write_text(src, encoding='utf-8')
