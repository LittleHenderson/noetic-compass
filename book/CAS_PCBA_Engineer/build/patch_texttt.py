# -*- coding: utf-8 -*-
"""Insert \\allowbreak{} after delimiters inside long \\texttt args (KDP margin pass)."""
from pathlib import Path

BREAK_AFTER = ['=', '|', ',', ';', '→', '/', '›']
BS = chr(92)

src = Path('body.tex').read_text(encoding='utf-8')
ALLOW = BS + 'allowbreak{}'


def patch_arg(arg):
    if len(arg) < 22:
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


res = []
i = 0
n = 0
TT = BS + 'texttt{'
while True:
    j = src.find(TT, i)
    if j == -1:
        res.append(src[i:])
        break
    res.append(src[i:j])
    k = j + len(TT)
    depth = 1
    m = k
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
        n += 1
    res.append(TT + new + '}')
    i = m

Path('body.tex').write_text(''.join(res), encoding='utf-8')
print('patched texttt args:', n)
