# -*- coding: utf-8 -*-
"""Final 12: tikz text-width, verbatim comment splits, exact display wraps."""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92)
p = Path('body.tex')
lines = p.read_text(encoding='utf-8').split('\n')
n = 0

RESIZE_PRE = BS + '[' + BS + 'resizebox{' + BS + 'linewidth}{!}{$' + BS + 'displaystyle '
RESIZE_SUF = '$}' + BS + ']'

display_anchors = ['text{Sarah}_{' + BS + 'text{before}}',
                   '5 ' + BS + 'circ ',
                   'text{Priya}_{' + BS + 'text{after}}',
                   'text{Finch ' + BS + '& Rowan}',
                   'text{Dormant} ' + BS + 'to ']

for i, ln in enumerate(lines):
    s = ln.strip()
    if s.startswith(BS + '[') and s.endswith(BS + ']') and any(a in ln for a in display_anchors):
        content = s[2:-2]
        lines[i] = RESIZE_PRE + content + RESIZE_SUF
        n += 1
    # tikz labels
    if 'anchor=north west] at ($(O.south west)' in ln:
        lines[i] = ln.replace('anchor=north west]',
                              'anchor=north west, align=left, text width=80mm]')
        n += 1
    if 'caslabel, align=center] at (0,-34mm)' in ln:
        lines[i] = ln.replace('caslabel, align=center]',
                              'caslabel, align=center, text width=95mm]')
        n += 1
    # verbatim comment splits
    if s.startswith('Reusable typed function: compose two cognitive states'):
        lines[i] = ' Reusable typed function:\n   compose two cognitive states via fractal operator'
        n += 1
    if s.startswith('3. Binary state operators'):
        lines[i] = ' 3. Binary state operators — composition (*, ×)\n    and modular difference (/, ÷)'
        n += 1
    if 'let_stmt' in ln and '::=' in ln:
        lines[i] = ln.replace(' ”=” <expression> ;', '\n             ”=” <expression> ;')
        n += 1
    # long test-reference comments: split at the em dash
    if '// true' in ln and '— ' in ln and len(ln) > 95:
        head, tail = ln.split('— ', 1)
        lines[i] = head.rstrip() + '\n' + '        //   — ' + tail
        n += 1

p.write_text('\n'.join(lines), encoding='utf-8')
print('edits applied:', n)
