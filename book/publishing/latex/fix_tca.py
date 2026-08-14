# -*- coding: utf-8 -*-
"""TCA pass 2: convert lowercase verbatim to breaking Verbatim; TOC widths."""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92)

# 1. verbatim -> Verbatim with breaking
b = Path('body.tex')
src = b.read_text(encoding='utf-8')
n = src.count(BS + 'begin{verbatim}')
src = src.replace(
    BS + 'begin{verbatim}',
    BS + 'begin{Verbatim}[breaklines=true,breakanywhere=true,fontsize=' + BS + 'footnotesize]')
src = src.replace(BS + 'end{verbatim}', BS + 'end{Verbatim}')
b.write_text(src, encoding='utf-8')
print('verbatim blocks converted:', n)

# 2. memoir TOC page-number widths
p = Path('preamble.tex')
t = p.read_text(encoding='utf-8')
if 'setpnumwidth' not in t:
    t += ('\n' + BS + 'setpnumwidth{2.55em}\n' + BS + 'setrmarg{3.55em}\n')
    p.write_text(t, encoding='utf-8')
    print('TOC widths set')
