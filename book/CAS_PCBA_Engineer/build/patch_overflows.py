# -*- coding: utf-8 -*-
"""Second KDP margin pass: texttt threshold 12 + more break chars,
prose arrow breaks, footnotesize natural-width longtables, resize tikz fig."""
from pathlib import Path
import re

BS = chr(92)
ALLOW = BS + 'allowbreak{}'
BREAK_AFTER = ['=', '|', ',', ';', '→', '/', '›', '(', '·']
TT = BS + 'texttt{'

src = Path('body.tex').read_text(encoding='utf-8')

# ---- pass 1: texttt args ----------------------------------------------------
def patch_arg(arg):
    if len(arg) < 12 or ALLOW in arg:
        return arg
    out = []
    i = 0
    while i < len(arg):
        ch = arg[i]
        if ch == BS and i + 1 < len(arg):
            seq = arg[i:i + 2]
            out.append(seq)
            i += 2
            if seq == BS + '_':
                out.append(ALLOW)
            continue
        out.append(ch)
        i += 1
        if ch in BREAK_AFTER:
            out.append(ALLOW)
    return ''.join(out)

res, i, n_tt = [], 0, 0
while True:
    j = src.find(TT, i)
    if j == -1:
        res.append(src[i:])
        break
    res.append(src[i:j])
    k = j + len(TT)
    depth, m = 1, k
    while m < len(src) and depth:
        c = src[m]
        if c == BS:
            m += 2
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
        m += 1
    arg = src[k:m - 1]
    new = patch_arg(arg)
    if new != arg:
        n_tt += 1
    res.append(TT + new + '}')
    i = m
src = ''.join(res)

# ---- pass 2: prose arrows (skip Verbatim + tikzpicture) --------------------
lines = src.split('\n')
out_lines = []
in_verb = in_tikz = False
n_arrow = 0
for ln in lines:
    if BS + 'begin{Verbatim}' in ln:
        in_verb = True
    if BS + 'begin{tikzpicture}' in ln:
        in_tikz = True
    if not in_verb and not in_tikz and '→' in ln and ALLOW not in ln:
        new = ln.replace('→', '→' + ALLOW)
        if new != ln:
            n_arrow += 1
            ln = new
    if BS + 'end{Verbatim}' in ln:
        in_verb = False
    if BS + 'end{tikzpicture}' in ln:
        in_tikz = False
    out_lines.append(ln)
src = '\n'.join(out_lines)

# ---- pass 3: natural-width longtables --> footnotesize group ---------------
pat = re.compile(r'\\begin\{longtable\}\[\]\{@\{\}l+@\{\}\}')
n_lt = 0
pos = 0
chunks = []
for m in pat.finditer(src):
    chunks.append(src[pos:m.start()])
    chunks.append(BS + 'begingroup' + BS + 'footnotesize' + m.group(0))
    pos = m.end()
    n_lt += 1
chunks.append(src[pos:])
src = ''.join(chunks)
# close the groups after their matching \end{longtable}
if n_lt:
    parts = src.split(BS + 'end{longtable}')
    rebuilt = parts[0]
    for p in parts[1:]:
        rebuilt += BS + 'end{longtable}'
        # count opens minus closes so far to know if a group is pending
        opens = rebuilt.count(BS + 'begingroup' + BS + 'footnotesize' + BS + 'begin{longtable}')
        closes = rebuilt.count(BS + 'endgroup% lt')
        if opens > closes:
            rebuilt += BS + 'endgroup% lt' + '\n'
        rebuilt += p
    src = rebuilt

# ---- pass 4: resize the domain-layers tikzpicture --------------------------
anchor = '(O9.east) -- ++(3.0,0) |- (P0.east)'
n_tikz = 0
if anchor in src:
    a = src.rfind(BS + 'begin{tikzpicture}', 0, src.find(anchor))
    b = src.find(BS + 'end{tikzpicture}', src.find(anchor))
    b_end = b + len(BS + 'end{tikzpicture}')
    src = (src[:a] + BS + 'resizebox{' + BS + 'linewidth}{!}{%\n'
           + src[a:b_end] + '}%\n' + src[b_end:])
    n_tikz = 1

Path('body.tex').write_text(src, encoding='utf-8')
print(f'texttt patched: {n_tt}, arrow lines: {n_arrow}, longtables: {n_lt}, tikz: {n_tikz}')
