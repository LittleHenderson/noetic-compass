# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
BS = chr(92)
src = Path('body.tex').read_text(encoding='utf-8')

# each: (anchor to find, text to insert immediately before anchor)
edits = [
    ("\\textbf{Introduce new 5}: Consciously expose his Mind",
     "\\sloppy "),
    ("These Ideas (10) compose (5) what attracts (2) her---unavailability.",
     "\\sloppy "),
    ("This formal specification demonstrates that TKS isn't philosophy---it's",
     "\\sloppy "),
    ("What's Actually Happening\\index{What's Actually Happening}: Debt isn't just a financial problem---it's",
     "\\sloppy "),
]
n = 0
for anchor, ins in edits:
    i = src.find(anchor)
    if i == -1:
        print('NOT FOUND:', anchor[:50])
        continue
    src = src[:i] + ins + src[i:]
    n += 1
Path('body.tex').write_text(src, encoding='utf-8')
print('sloppy inserted:', n)
