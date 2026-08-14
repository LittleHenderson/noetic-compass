# -*- coding: utf-8 -*-
"""Invert fix_displays.py: unwrap resizebox display blocks."""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92)
src = Path('body.tex').read_text(encoding='utf-8')
PRE = BS + '[' + BS + 'resizebox{' + BS + 'linewidth}{!}{$' + BS + 'displaystyle '
SUF = '$}' + BS + ']'
n = 0
while True:
    a = src.find(PRE)
    if a == -1:
        break
    b = src.find(SUF, a)
    content = src[a + len(PRE):b]
    src = src[:a] + BS + '[' + content + BS + ']' + src[b + len(SUF):]
    n += 1
Path('body.tex').write_text(src, encoding='utf-8')
print('reverted:', n)
